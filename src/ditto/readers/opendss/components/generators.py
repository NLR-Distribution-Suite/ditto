"""Read OpenDSS generators into distribution generator components."""

from __future__ import annotations

from typing import TYPE_CHECKING

import opendssdirect as odd
from loguru import logger

from gdm.quantities import ActivePower, ApparentPower, ReactivePower, Voltage
from gdm.systems.distribution.components import DistributionBus
from gdm.systems.distribution.enums import ConnectionType
from infrasys import System

from ditto.readers.opendss.common import PHASE_MAPPER, query_model_data

if TYPE_CHECKING:
    from gdm.systems.distribution.components import DistributionGenerator


GENERATOR_MODES = {
    1: "constant-pq",
    2: "constant-impedance",
    3: "constant-pv",
    4: "constant-p-fixed-q",
    5: "constant-p-fixed-reactance",
    7: "approximate-inverter",
}


def _generator_nodes(name: str, bus: str, enabled: bool) -> list[str]:
    explicit_nodes = bus.split(".")[1:]
    phase_count = odd.Generators.Phases()
    if enabled:
        nodes = [str(node) for node in odd.CktElement.NodeOrder()[:phase_count]]
    elif not explicit_nodes:
        nodes = [str(node) for node in range(1, phase_count + 1)]
    elif len(explicit_nodes) >= phase_count:
        nodes = explicit_nodes[:phase_count]
    else:
        raise ValueError(f"Disabled generator {name!r} has incomplete terminal nodes")
    if any(node != "0" for node in explicit_nodes[phase_count:]):
        raise ValueError(
            f"Generator {name!r} has extra terminal nodes {explicit_nodes!r} "
            "that cannot be represented"
        )
    if any(node not in PHASE_MAPPER for node in nodes):
        raise ValueError(f"Generator {name!r} has unsupported node connections {nodes!r}")
    return nodes


def get_generators(system: System) -> list[DistributionGenerator]:
    generators = []
    if not odd.Generators.Count():
        return generators
    try:
        from gdm.systems.distribution.components import (
            DistributionGenerator,
            GeneratorOperatingMode,
        )
        from gdm.systems.distribution.equipment import GeneratorEquipment
    except ImportError as exc:
        raise ImportError(
            "OpenDSS generator conversion requires a grid-data-models version "
            "with DistributionGenerator and GeneratorEquipment"
        ) from exc
    for name in odd.Generators.AllNames():
        name = name.lower()
        odd.Generators.Name(name)
        mode = odd.Generators.Model()
        if mode not in GENERATOR_MODES:
            raise ValueError(f"Generator {name!r} has unsupported OpenDSS model {mode}")

        def query(prop: str) -> float:
            return query_model_data("Generator", name, prop, float)

        buses = odd.CktElement.BusNames()
        enabled = odd.CktElement.Enabled()
        nodes = _generator_nodes(name, buses[0], enabled)
        if any((odd.Generators.Yearly(), odd.Generators.daily(), odd.Generators.duty())):
            logger.warning(f"Generator {name!r} load shapes are not supported and will be omitted")
        equipment = GeneratorEquipment(
            name=f"{name}_equipment",
            rated_apparent_power=ApparentPower(odd.Generators.kVARated(), "kVA"),
            rated_voltage=Voltage(odd.Generators.kV(), "kV"),
            connection_type=ConnectionType.DELTA
            if odd.Generators.IsDelta()
            else ConnectionType.STAR,
            synchronous_reactance_pu=query("xd"),
            transient_reactance_pu=query("xdp"),
            subtransient_reactance_pu=query("xdpp"),
            inertia_seconds=query("h"),
            damping=query("d"),
        )
        generators.append(
            DistributionGenerator(
                name=name,
                bus=system.get_component(DistributionBus, buses[0].split(".")[0].lower()),
                phases=[PHASE_MAPPER[node] for node in nodes],
                equipment=equipment,
                in_service=enabled,
                active_power=ActivePower(odd.Generators.kW(), "kW"),
                reactive_power=ReactivePower(odd.Generators.kvar(), "kvar"),
                operating_mode=GeneratorOperatingMode(GENERATOR_MODES[mode]),
                voltage_setpoint_pu=query("vpu"),
                min_voltage_pu=odd.Generators.Vminpu(),
                max_voltage_pu=odd.Generators.Vmaxpu(),
                min_reactive_power=ReactivePower(query("minkvar"), "kvar"),
                max_reactive_power=ReactivePower(query("maxkvar"), "kvar"),
            )
        )
    return generators
