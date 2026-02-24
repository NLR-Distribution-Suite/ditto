from __future__ import annotations

import xml.etree.ElementTree as ET


def emit_capacitor(
    writer,
    root: ET.Element,
    capacitor,
    bus_node_ids: dict[str, str],
    bus_location_ids: dict[str, str],
    base_voltage_cache: dict[str, str],
) -> None:
    bus = getattr(capacitor, "bus", None)
    if bus is None or bus.name not in bus_node_ids:
        return

    capacitor_id = writer._deterministic_id("linear_shunt_compensator", capacitor.name)
    capacitor_element = writer._create_identified_object(
        root,
        "LinearShuntCompensator",
        capacitor_id,
        capacitor.name,
    )

    rated_voltage = writer._quantity(getattr(capacitor.equipment, "rated_voltage", 0.0), "volt")
    if rated_voltage <= 0:
        rated_voltage = writer._bus_nominal_voltage(bus)

    base_voltage_id = writer._create_base_voltage(root, rated_voltage, base_voltage_cache)
    writer._add_ref(capacitor_element, "ConductingEquipment.BaseVoltage", base_voltage_id)
    writer._add_ref(capacitor_element, "PowerSystemResource.Location", bus_location_ids[bus.name])

    conn_text = writer._safe_text(getattr(capacitor.equipment, "connection_type", "STAR"))
    conn_code = "D" if "DELTA" in conn_text else "Y"
    writer._add_literal(capacitor_element, "ShuntCompensator.phaseConnection", conn_code)

    phase_caps = list(getattr(capacitor.equipment, "phase_capacitors", []))
    total_var = 0.0
    for phase_cap in phase_caps:
        total_var += writer._quantity(getattr(phase_cap, "rated_reactive_power", 0.0), "var")
    b1 = total_var / (rated_voltage**2) if rated_voltage > 0 else 0.0

    steps = 1
    if phase_caps:
        steps = int(getattr(phase_caps[0], "num_banks", 1) or 1)

    writer._add_literal(capacitor_element, "LinearShuntCompensator.bPerSection", b1)
    writer._add_literal(capacitor_element, "LinearShuntCompensator.gPerSection", 0.0)
    writer._add_literal(capacitor_element, "LinearShuntCompensator.b0PerSection", 0.0)
    writer._add_literal(capacitor_element, "LinearShuntCompensator.g0PerSection", 0.0)
    writer._add_literal(capacitor_element, "ShuntCompensator.sections", steps)

    for index, phase in enumerate(getattr(capacitor, "phases", []), start=1):
        phase_id = writer._deterministic_id(
            "linear_shunt_compensator_phase", f"{capacitor.name}:{index}"
        )
        phase_element = writer._create_identified_object(
            root,
            "LinearShuntCompensatorPhase",
            phase_id,
            f"{capacitor.name}_phase_{index}",
        )
        writer._add_ref(phase_element, "ShuntCompensatorPhase.ShuntCompensator", capacitor_id)
        writer._add_literal(
            phase_element, "ShuntCompensatorPhase.phase", writer._phase_text(phase)
        )

    writer._create_terminal(root, capacitor_id, bus_node_ids[bus.name], f"{capacitor.name}:1")
