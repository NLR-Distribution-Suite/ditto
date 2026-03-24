from uuid import uuid4

from gdm.distribution.enums import VoltageTypes, ConnectionType
from gdm.distribution.components import DistributionCapacitor, DistributionBus
from gdm.distribution.equipment import PhaseCapacitorEquipment, CapacitorEquipment
from gdm.quantities import (
    ReactivePower,
    Resistance,
    Reactance,
    Voltage,
)
from infrasys.system import System
import opendssdirect as odd
from loguru import logger

from ditto.readers.opendss.common import PHASE_MAPPER, get_equipment_from_catalog


def _build_capacitor_source_equipment(
    phase_capacitor_equipment_catalog: dict[int, PhaseCapacitorEquipment],
    capacitor_equipment_catalog: dict[int, CapacitorEquipment],
) -> tuple[CapacitorEquipment, list[str], list[str]]:
    """Helper function to build a CapacitorEquipment instance

    Args:
        phase_capacitor_equipment_catalog (dict[int, PhaseCapacitorEquipment]): mapping of model hash to PhaseCapacitorEquipment instance
        capacitor_equipment_catalog (dict[int, CapacitorEquipment]):  mapping of model hash to CapacitorEquipment instance

    Returns:
        CapacitorEquipment: Instance of CapacitorEquipment
        list[str]: List of buses
        list[str]: List of phases
    """

    equipment_uuid = uuid4()
    buses = odd.CktElement.BusNames()
    num_phase = odd.CktElement.NumPhases()
    kvar_ = odd.Capacitors.kvar()

    ph_caps = []
    nodes = buses[0].split(".")[1:] if num_phase != 3 else ["1", "2", "3"]
    live_nodes = [node for node in nodes if node != "0"]

    voltage_type = (
        VoltageTypes.LINE_TO_GROUND
        if num_phase == 1 and len(live_nodes)
        else VoltageTypes.LINE_TO_LINE
    )

    for el in nodes:
        phase_capacitor = PhaseCapacitorEquipment.model_construct(
            name=f"{equipment_uuid}_{el}",
            rated_reactive_power=ReactivePower(kvar_ / len(nodes), "kilovar"),
            num_banks=odd.Capacitors.NumSteps(),
            num_banks_on=sum(odd.Capacitors.States()),
            resistance=Resistance(0, "ohm"),
            reactance=Reactance(0, "ohm"),
        )
        phase_capacitor = get_equipment_from_catalog(
            phase_capacitor, phase_capacitor_equipment_catalog
        )
        ph_caps.append(phase_capacitor)

    capacitor_equipment = CapacitorEquipment.model_construct(
        name=str(equipment_uuid),
        phase_capacitors=ph_caps,
        connection_type=ConnectionType.DELTA if odd.Capacitors.IsDelta() else ConnectionType.STAR,
        rated_voltage=Voltage(odd.Capacitors.kV(), "kilovolt"),
        voltage_type=voltage_type,
    )

    capacitor_equipment = get_equipment_from_catalog(
        capacitor_equipment, capacitor_equipment_catalog
    )

    return capacitor_equipment, buses, nodes


def get_capacitors(system: System) -> list[DistributionCapacitor]:
    """Function to return list of all capacitors in Opendss model.

    Args:
        system (System): Instance of System

    Returns:
        List[DistributionCapacitor]: List of DistributionCapacitor objects
    """

    logger.debug("parsing capacitor components...")
    phase_capacitor_equipment_catalog = {}
    capacitor_equipment_catalog = {}
    capacitors = []
    flag = odd.Capacitors.First()
    while flag > 0:
        equipment, buses, nodes = _build_capacitor_source_equipment(
            phase_capacitor_equipment_catalog, capacitor_equipment_catalog
        )
        bus1 = buses[0].split(".")[0]
        capacitors.append(
            DistributionCapacitor.model_construct(
                name=odd.Capacitors.Name().lower(),
                bus=system.get_component(DistributionBus, bus1),
                phases=[PHASE_MAPPER[el] for el in nodes],
                controllers=[],
                equipment=equipment,
            )
        )
        flag = odd.Capacitors.Next()
    return capacitors
