from uuid import uuid4

from gdm.quantities import ActivePower, ReactivePower
from gdm.distribution.enums import ConnectionType
from gdm.distribution.components import (
    DistributionBus,
    DistributionLoad,
)
from gdm.distribution.equipment import (
    PhaseLoadEquipment,
    LoadEquipment,
)
from infrasys.system import System
import opendssdirect as odd
from loguru import logger

from ditto.readers.opendss.components.loadshapes import build_profiles, ObjectsWithProfile
from ditto.readers.opendss.common import PHASE_MAPPER, LoadTypes


def _build_load_equipment() -> tuple[LoadEquipment, list[str], str, list[str]]:
    """Helper function to build a LoadEquipment instance

    Returns:
        LoadEquipment: instance of LoadEquipment
        list[str]: List of buses
        list[str]: List of phases
    """

    equipment_uuid = uuid4()
    buses = odd.CktElement.BusNames()
    num_phase = odd.CktElement.NumPhases()
    kvar_ = odd.Loads.kvar()
    kw_ = odd.Loads.kW()
    zip_params = odd.Loads.ZipV()
    model = odd.Loads.Model()
    nodes = buses[0].split(".")[1:] if num_phase != 3 else ["1", "2", "3"]
    ph_loads = []
    zip_param_keys = ["z_real", "i_real", "p_real", "z_imag", "i_imag", "p_imag"]
    for el in nodes:
        kw_per_phase = kw_ / len(nodes)
        kvar_per_phase = kvar_ / len(nodes)
        zip_params_dict = {param: 0 for param in zip_param_keys}
        if model == LoadTypes.CONST_POWER:
            zip_params_dict.update({"p_imag": 1, "p_real": 1})
        elif model == LoadTypes.CONST_CURRENT:
            zip_params_dict.update({"i_imag": 1, "i_real": 1})
        elif model == LoadTypes.CONST_IMPEDANCE:
            zip_params_dict.update({"z_imag": 1, "z_real": 1})
        elif model == LoadTypes.ZIP:
            zip_params_dict = dict(zip(zip_param_keys, zip_params))
        elif model == LoadTypes.CONST_P__QUARDRATIC_Q:
            zip_params_dict.update({"p_real": 1, "z_imag": 1})
        elif model == LoadTypes.LINEAR_P__QUARDRATIC_Q:
            zip_params_dict.update({"i_real": 1, "z_imag": 1})
        else:
            msg = f"Invalid load model type {model} passed. valid options are {LoadTypes}"
            raise ValueError(msg)
        load = PhaseLoadEquipment.model_construct(
            name=f"{equipment_uuid}_{el}",
            real_power=ActivePower(kw_per_phase, "kilowatt"),
            reactive_power=ReactivePower(kvar_per_phase, "kilovar"),
            **zip_params_dict,
        )
        ph_loads.append(load)
    load_equipment = LoadEquipment.model_construct(
        name=str(uuid4()),
        phase_loads=ph_loads,
        connection_type=ConnectionType.DELTA if odd.Loads.IsDelta() else ConnectionType.STAR,
    )
    return load_equipment, buses, nodes


# def get_load_equipments(odd:Opendssdirect) -> list[LoadEquipment]:
#     """Function to return list of all LoadEquipment in Opendss model.

#     Args:
#         odd (Opendssdirect): Instance of Opendss simulator

#     Returns:
#         list[LoadEquipment]: List of LoadEquipment objects
#     """


def get_loads(system: System) -> list[DistributionLoad]:
    """Function to return list of DistributionLoad in Opendss model.

    Args:
        system (System): Instance of System

    Returns:
        List[DistributionLoad]: List of DistributionLoad objects
    """

    logger.debug("parsing load components...")

    profile_catalog = {}
    loads = []
    flag = odd.Loads.First()
    while flag > 0:
        load_name = odd.Loads.Name().lower()
        load_equipment, buses, nodes = _build_load_equipment()
        bus1 = buses[0].split(".")[0]
        profile_names = [odd.Loads.Daily(), odd.Loads.Yearly(), odd.Loads.Duty()]
        profiles = build_profiles(profile_names, ObjectsWithProfile.LOAD, profile_catalog)
        distribution_load = DistributionLoad.model_construct(
            name=load_name,
            bus=system.get_component(DistributionBus, bus1),
            phases=[PHASE_MAPPER[el] for el in nodes],
            equipment=load_equipment,
        )
        for profile_name in profile_names:
            if profile_name in profiles:
                for profile_type, ts_profile in profiles[profile_name].items():
                    system.add_time_series(
                        ts_profile["data"],
                        distribution_load,
                        profile_type=profile_type,
                        profile_name=profile_name,
                        use_actual=ts_profile["use_actual"],
                    )
                    logger.debug(
                        f"Adding timeseries profile '{profile_name} / {profile_type}' to load '{load_name}'"
                    )
        loads.append(distribution_load)
        flag = odd.Loads.Next()
    return loads
