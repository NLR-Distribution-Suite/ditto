from uuid import uuid4

from gdm.distribution.equipment import PhaseVoltageSourceEquipment, VoltageSourceEquipment
from gdm.distribution.components import (
    DistributionVoltageSource,
    DistributionBus,
)
from gdm.distribution.enums import VoltageTypes

from infrasys.quantities import Angle, Resistance, Voltage
from gdm.quantities import Reactance
import opendssdirect as odd
from infrasys import System
from loguru import logger

from ditto.readers.opendss.common import PHASE_MAPPER, get_equipment_from_catalog
from ditto.readers.opendss.components.loadshapes import build_profiles, ObjectsWithProfile


def _build_voltage_source_equipment(
    phase_voltage_source_equipment_catalog: dict[int, PhaseVoltageSourceEquipment],
    voltage_source_equipment_catalog: dict[int, VoltageSourceEquipment],
) -> tuple[VoltageSourceEquipment, list[str], str, list[str]]:
    """Helper function to build a VoltageSourceEquipment instance

    Args:
        phase_voltage_source_equipment_catalog (dict[int, PhaseVoltageSourceEquipment]): mapping of model hash to PhaseVoltageSourceEquipment instance
        voltage_source_equipment_catalog (dict[int, VoltageSourceEquipment]): mapping of model hash to VoltageSourceEquipment instance


    Returns:
        VoltageSourceEquipment: instance of VoltageSourceEquipment
        list[str]: List of buses
        str:  Voltage source name
        list[str]: List of phases
    """

    equipment_uuid = uuid4()
    soure_name = odd.Vsources.Name().lower()
    buses = odd.CktElement.BusNames()
    num_phase = odd.CktElement.NumPhases()
    nodes = buses[0].split(".")[1:] if "." in buses[0] else ["1", "2", "3"]
    angle = odd.Vsources.AngleDeg()
    angles = [Angle(angle + i * (360.0 / num_phase), "degree") for i in range(num_phase)]
    phase_slacks = []
    phase_src_properties = {}

    for ppty in ["r0", "r1", "x0", "x1"]:
        command_str = f"? vsource.{soure_name}.{ppty}"
        odd.Text.Command(command_str)
        phase_src_properties[ppty] = float(odd.Text.Result())

    for node, angle in zip(nodes, angles):
        voltage = Voltage(odd.Vsources.BasekV() * odd.Vsources.PU(), "kilovolt")
        phase_slack = PhaseVoltageSourceEquipment.model_construct(
            name=f"{equipment_uuid}_{node}",
            r0=Resistance(phase_src_properties["r0"], "ohm"),
            r1=Resistance(phase_src_properties["r1"], "ohm"),
            x0=Reactance(phase_src_properties["x0"], "ohm"),
            x1=Reactance(phase_src_properties["x1"], "ohm"),
            angle=angle,
            voltage=voltage / 1.732 if num_phase == 3 else voltage,
            voltage_type=VoltageTypes.LINE_TO_GROUND,
        )
        phase_slack = get_equipment_from_catalog(
            phase_slack, phase_voltage_source_equipment_catalog
        )

        phase_slacks.append(phase_slack)

    slack_equipment = VoltageSourceEquipment.model_construct(
        name=str(equipment_uuid),
        sources=phase_slacks,
    )

    slack_equipment = get_equipment_from_catalog(slack_equipment, voltage_source_equipment_catalog)
    return slack_equipment, buses, soure_name, nodes


def get_voltage_sources(system: System) -> list[DistributionVoltageSource]:
    """Function to return list of all voltage sources in Opendss model.

    Args:
        system (System): Instance of System

    Returns:
        list[DistributionVoltageSource]: List of DistributionVoltageSource objects
    """

    logger.debug("parsing voltage sources components...")
    phase_voltage_source_equipment_catalog = {}
    voltage_source_equipment_catalog = {}
    profile_catalog = {}
    voltage_sources = []
    flag = odd.Vsources.First()
    while flag:
        equipment, buses, soure_name, nodes = _build_voltage_source_equipment(
            phase_voltage_source_equipment_catalog, voltage_source_equipment_catalog
        )
        bus1 = buses[0].split(".")[0]

        def query(property: str):
            odd.Text.Command(f"? vsource.{soure_name}.{property}")
            return odd.Text.Result()

        profile_names = [query("yearly"), query("daily"), query("duty")]
        profiles = build_profiles(profile_names, ObjectsWithProfile.SOURCE, profile_catalog)
        voltage_source = DistributionVoltageSource.model_construct(
            name=soure_name,
            bus=system.get_component(DistributionBus, bus1),
            phases=[PHASE_MAPPER[el] for el in nodes],
            equipment=equipment,
        )

        for profile_name in profile_names:
            if profile_name in profiles:
                for profile_type, ts_profile in profiles[profile_name].items():
                    system.add_time_series(
                        ts_profile,
                        voltage_source,
                        profile_type=profile_type,
                        profile_name=profile_name,
                    )
                    logger.debug(
                        f"Adding timeseries profile '{profile_name} / {profile_type}' to voltage source '{soure_name}'"
                    )

        voltage_sources.append(voltage_source)
        flag = odd.Vsources.Next()
    return voltage_sources
