from __future__ import annotations

import math
import xml.etree.ElementTree as ET


def emit_energy_source(
    writer,
    root: ET.Element,
    source,
    bus_node_ids: dict[str, str],
    bus_location_ids: dict[str, str],
    base_voltage_cache: dict[str, str],
) -> None:
    bus = source.bus
    source_id = writer._deterministic_id("energy_source", source.name)
    source_element = writer._create_identified_object(root, "EnergySource", source_id, source.name)

    nominal_voltage = writer._bus_nominal_voltage(bus)
    base_voltage_id = writer._create_base_voltage(root, nominal_voltage, base_voltage_cache)
    writer._add_ref(source_element, "ConductingEquipment.BaseVoltage", base_voltage_id)
    writer._add_ref(source_element, "PowerSystemResource.Location", bus_location_ids[bus.name])

    source_phase = source.equipment.sources[0] if source.equipment.sources else None
    r1 = writer._quantity(getattr(source_phase, "r1", 0.0), "ohm")
    x1 = writer._quantity(getattr(source_phase, "x1", 0.0), "ohm")
    r0 = writer._quantity(getattr(source_phase, "r0", 0.0), "ohm")
    x0 = writer._quantity(getattr(source_phase, "x0", 0.0), "ohm")
    phase_voltage = writer._quantity(getattr(source_phase, "voltage", 0.0), "volt")
    angle_deg = writer._quantity(getattr(source_phase, "angle", 0.0), "degree")

    writer._add_literal(source_element, "EnergySource.nominalVoltage", nominal_voltage)
    writer._add_literal(source_element, "EnergySource.voltageMagnitude", phase_voltage * 1.732)
    writer._add_literal(source_element, "EnergySource.voltageAngle", angle_deg * math.pi / 180.0)
    writer._add_literal(source_element, "EnergySource.r", r1)
    writer._add_literal(source_element, "EnergySource.x", x1)
    writer._add_literal(source_element, "EnergySource.r0", r0)
    writer._add_literal(source_element, "EnergySource.x0", x0)

    writer._create_terminal(root, source_id, bus_node_ids[bus.name], f"{source.name}:1")
