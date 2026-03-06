from collections import Counter
from ast import literal_eval
from typing import Any
from uuid import uuid4
from enum import Enum

from gdm.quantities import ApparentPower, Voltage
from gdm.distribution.common import SequencePair
from gdm.distribution.components import (
    DistributionTransformer,
    DistributionBus,
)
from gdm.distribution.equipment import (
    DistributionTransformerEquipment,
    WindingEquipment,
)
from gdm.distribution.enums import (
    ConnectionType,
    VoltageTypes,
    Phase,
)
from infrasys.system import System
import opendssdirect as odd
from loguru import logger

from ditto.readers.opendss.common import PHASE_MAPPER, get_equipment_from_catalog

SEQUENCE_PAIRS = [SequencePair(1, 2), SequencePair(1, 3), SequencePair(2, 3)]


class XfmrModelTypes(str, Enum):
    TRANSFORMERS = "Transformer"
    XFMRCODE = "XfmrCode"


def _build_xfmr_equipment(
    model_type: str,
    distribution_transformer_equipment_catalog: dict[int, DistributionTransformerEquipment],
    winding_equipment_catalog: dict[int, WindingEquipment],
) -> tuple[DistributionTransformerEquipment, list[DistributionBus], list[Phase]]:
    """Helper function to build a DistributionTransformerEquipment instance

    Args:
        model_type (str): Opendss model type e.g. Transformer, XfmrCode
        distribution_transformer_equipment_catalog (dict[int, DistributionTransformerEquipment]): mapping of model hash to DistributionTransformerEquipment instance
        winding_equipment_catalog (dict[int, WindingEquipment]): mapping of model hash to WindingEquipment instance

    Returns:
        DistributionTransformerEquipment: instance of DistributionTransformerEquipment
        list[DistributionBus]: List of DistributionBus
        list[Phase]: List of Phase
    """

    model_name = odd.Element.Name().lower().split(".")[1]
    if model_type == XfmrModelTypes.XFMRCODE.value:
        equipment_uuid = model_name
    else:
        equipment_uuid = str(uuid4())

    def query(property: str, dtype: type):
        command = f"? {model_type}.{model_name}.{property}"
        odd.Text.Command(command)
        result = odd.Text.Result()

        if result is None:
            if dtype in [float, int]:
                return 0
            elif dtype is str:
                return ""
            else:
                return None
        else:
            if dtype is list:
                return literal_eval(result)
            else:
                return dtype(result)

    def set_ppty(property: str, value: Any):
        return odd.Text.Command(f"{model_type}.{model_name}.{property}={value}")

    all_reactances = [
        query("xhl", float),
        query("xht", float),
        query("xlt", float),
    ]

    number_windings = query("windings", int)
    wdg_nom_voltages = []
    windings = []

    for wdg_index in range(number_windings):
        set_ppty("Wdg", wdg_index + 1)
        num_phase = query("phases", int)
        if query("conn", str).lower() == "delta":
            rated_voltage = query("kv", float) / 1.732
        else:
            rated_voltage = query("kv", float) / 1.732 if num_phase == 3 else query("kv", float)
        wdg_nom_voltages.append(rated_voltage)
        min_tap_pu = query("mintap", float)
        max_tap_pu = query("maxtap", float)
        num_taps = query("numtaps", int)
        taps = query("taps", list)
        tap = [taps[wdg_index]] * num_phase
        winding = WindingEquipment.model_construct(
            rated_power=ApparentPower(query("kva", float), "kilova"),
            num_phases=num_phase,
            connection_type=ConnectionType.DELTA
            if query("conn", str).lower() == "delta"
            else ConnectionType.STAR,
            rated_voltage=Voltage(rated_voltage, "kilovolt"),
            resistance=query("%r", float),
            is_grounded=False,  # TODO: Should be moved to the transformer model. Only known once the transformer is installed
            voltage_type=VoltageTypes.LINE_TO_GROUND,
            tap_positions=tap,
            total_taps=num_taps,
            min_tap_pu=min_tap_pu,
            max_tap_pu=max_tap_pu,
        )
        winding = get_equipment_from_catalog(winding, winding_equipment_catalog)
        windings.append(winding)

    coupling_sequences = SEQUENCE_PAIRS[:1] if number_windings == 2 else SEQUENCE_PAIRS
    reactances = all_reactances[:1] if number_windings == 2 else all_reactances

    dist_transformer = DistributionTransformerEquipment.model_construct(
        name=equipment_uuid,
        pct_no_load_loss=query(r"%noloadloss", float),
        pct_full_load_loss=query(r"%loadloss", float),
        windings=windings,
        coupling_sequences=coupling_sequences,
        winding_reactances=reactances,
        is_center_tapped=_is_center_tapped(wdg_nom_voltages),
    )
    dist_transformer = get_equipment_from_catalog(
        dist_transformer, distribution_transformer_equipment_catalog
    )
    return dist_transformer


def get_transformer_equipments(system: System) -> list[DistributionTransformerEquipment]:
    """Function to return list of all DistributionTransformerEquipment in Opendss model.

    Args:
        system (System): Instance of infrasys System

    Returns:
        list[DistributionTransformerEquipment]: List of DistributionTransformerEquipment objects
    """
    logger.debug("parsing transformer equipment...")
    distribution_transformer_equipment_catalog = {}
    winding_equipment_catalog = {}
    odd_model_types = [v.value for v in XfmrModelTypes]
    for odd_model_type in odd_model_types:
        odd.Circuit.SetActiveClass(odd_model_type)
        flag = odd.ActiveClass.First()
        while flag > 0:
            _build_xfmr_equipment(
                odd_model_type,
                distribution_transformer_equipment_catalog,
                winding_equipment_catalog,
            )
            flag = odd.ActiveClass.Next()
    return distribution_transformer_equipment_catalog, winding_equipment_catalog


def get_transformers(
    system: System,
    distribution_transformer_equipment_catalog: dict[int, DistributionTransformerEquipment],
    winding_equipment_catalog: dict[int, WindingEquipment],
) -> list[DistributionTransformer]:
    """Method returns a list of DistributionTransformer objects

    Args:
        system (System):  Instance of System
        distribution_transformer_equipment_catalog (dict[int, DistributionTransformerEquipment]): mapping of model hash to DistributionTransformerEquipment instance
        winding_equipment_catalog (dict[int, WindingEquipment]): mapping of model hash to WindingEquipment instance

     Returns:
        list[DistributionTransformer]: list of distribution transformers
    """

    logger.debug("parsing transformer components...")

    transformers = []
    flag = odd.Transformers.First()
    while flag > 0:
        logger.debug(f"building transformer {odd.Transformers.Name()}")
        bus_names = odd.CktElement.BusNames()
        buses = []
        phases = []
        for bus_name in bus_names:
            bus_name_clean = bus_name.split(".")[0]
            bus_phases = bus_name.split(".")[1:] if "." in bus_name else ["1", "2", "3"]
            bus_phases = [PHASE_MAPPER[ph] for ph in bus_phases]
            phases.append([Phase(phase) for phase in bus_phases])
            buses.append(system.get_component(DistributionBus, bus_name_clean))
        xfmr_equipment = _build_xfmr_equipment(
            XfmrModelTypes.TRANSFORMERS.value,
            distribution_transformer_equipment_catalog,
            winding_equipment_catalog,
        )
        transformer = DistributionTransformer.model_construct(
            name=odd.Transformers.Name().lower(),
            buses=buses,
            winding_phases=phases,
            equipment=xfmr_equipment,
        )
        transformers.append(transformer)
        flag = odd.Transformers.Next()

    return transformers


def _is_center_tapped(wdg_nom_voltages: list[float]) -> bool:
    """The flag is true if the transformer is center tapped

    Args:
        wdg_nom_voltages (list[float]): list of nomimal voltage for each bus

    Returns:
        bool: True if the transfomer equpment is split phase else False
    """

    is_split_phase = False
    if len(wdg_nom_voltages) == 3:
        max_secondary_voltage_kv = 0.6
        counts = Counter(wdg_nom_voltages)
        for nom_voltage in counts:
            if nom_voltage < max_secondary_voltage_kv and counts[nom_voltage] == 2:
                is_split_phase = True
    return is_split_phase
