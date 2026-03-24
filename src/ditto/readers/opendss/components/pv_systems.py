from uuid import uuid4

from gdm.distribution.enums import VoltageTypes
from gdm.quantities import Voltage
from gdm.distribution.components import DistributionSolar, DistributionBus
from gdm.distribution.equipment import (
    InverterEquipment,
    SolarEquipment,
)
from gdm.quantities import (
    ApparentPower,
    ActivePower,
    ReactivePower,
    Irradiance,
)


from infrasys.system import System
import opendssdirect as odd
from loguru import logger

from ditto.readers.opendss.common import PHASE_MAPPER, get_equipment_from_catalog
from ditto.readers.opendss.components.loadshapes import build_profiles, ObjectsWithProfile


def _build_pv_equipment(
    solar_equipment_catalog: dict[int, SolarEquipment],
) -> tuple[SolarEquipment, list[str], str, list[str]]:
    """Helper function to build a SolarEquipment instance

    Args:
        solar_equipment_catalog (dict[int, SolarEquipment]): mapping of model hash to SolarEquipment instance

    Returns:
        SolarEquipment: instance of SolarEquipment
        list[str]: List of buses
        list[str]: List of phases
    """

    logger.debug("parsing pvsystem equipment...")
    pv_name = odd.PVsystems.Name()

    def query(ppty):
        odd.Text.Command(f"? pvsystem.{pv_name}.{ppty}")
        return odd.Text.Result()

    equipment_uuid = uuid4()
    buses = odd.CktElement.BusNames()
    num_phase = odd.CktElement.NumPhases()
    # kva_ac = odd.PVsystems.kVARated()
    kw_dc = odd.PVsystems.Pmpp()
    nodes = buses[0].split(".")[1:] if num_phase != 3 else ["1", "2", "3"]
    live_nodes = [node for node in nodes if node != "0"]

    voltage_type = (
        VoltageTypes.LINE_TO_GROUND
        if num_phase == 1 and len(live_nodes)
        else VoltageTypes.LINE_TO_LINE
    )

    solar_equipment = SolarEquipment.model_construct(
        name=str(equipment_uuid),
        rated_power=ActivePower(kw_dc, "kilova"),
        resistance=float(query(r"%r")),
        reactance=float(query(r"%x")),
        rated_voltage=Voltage(float(query(r"kv")), "kilovolt"),
        voltage_type=voltage_type,
    )
    solar_equipment = get_equipment_from_catalog(solar_equipment, solar_equipment_catalog)
    return solar_equipment, buses, nodes


def get_pvsystems(system: System) -> list[DistributionSolar]:
    """Function to return list of DistributionSolar in Opendss model.

    Args:
        system (System): Instance of System

    Returns:
        List[DistributionSolar]: List of DistributionSolar objects
    """

    logger.debug("parsing pvsystem components...")
    solar_equipment_catalog = {}
    profile_catalog = {}
    pv_systems = []
    flag = odd.PVsystems.First()
    while flag > 0:
        logger.debug(f"building pvsystem {odd.PVsystems.Name()}...")
        solar_name = odd.PVsystems.Name().lower()

        def query(ppty):
            odd.Text.Command(f"? pvsystem.{solar_name}.{ppty}")
            return odd.Text.Result()

        solar_equipment, buses, nodes = _build_pv_equipment(solar_equipment_catalog)
        bus1 = buses[0].split(".")[0]
        distribution_solar = DistributionSolar.model_construct(
            name=solar_name,
            bus=system.get_component(DistributionBus, bus1),
            phases=[PHASE_MAPPER[el] for el in nodes],
            irradiance=Irradiance(odd.PVsystems.Irradiance(), "kilowatt/meter**2"),
            active_power=ActivePower(odd.PVsystems.kW(), "kilowatt"),
            reactive_power=ReactivePower(odd.PVsystems.kvar(), "kilovar"),
            inverter=InverterEquipment.model_construct(
                name=str(uuid4()),
                rated_apparent_power=ApparentPower(odd.PVsystems.kVARated(), "kilova"),
                rise_limit=None,
                fall_limit=None,
                eff_curve=None,
                cutout_percent=float(query(r"%cutout")),
                cutin_percent=float(query(r"%cutin")),
                dc_to_ac_efficiency=float(query(r"%pmpp")),
            ),
            controller=None,
            equipment=solar_equipment,
        )
        profile_names = [odd.PVsystems.daily(), odd.PVsystems.yearly(), odd.PVsystems.duty()]
        profiles = build_profiles(profile_names, ObjectsWithProfile.PV_SYSTEM, profile_catalog)

        for profile_name in profile_names:
            if profile_name in profiles:
                for profile_type, ts_data in profiles[profile_name].items():
                    system.add_time_series(
                        ts_data["data"],
                        distribution_solar,
                        profile_type=profile_type,
                        profile_name=profile_name,
                        use_actual=ts_data["use_actual"],
                    )
                    logger.debug(
                        f"Adding timeseries profile '{profile_name} / {profile_type}' to solar '{solar_name}'"
                    )
        pv_systems.append(distribution_solar)
        flag = odd.PVsystems.Next()
    return pv_systems
