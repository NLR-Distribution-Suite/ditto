from __future__ import annotations

import xml.etree.ElementTree as ET


def emit_fuse(
    writer,
    root: ET.Element,
    fuse,
    bus_node_ids: dict[str, str],
    bus_location_ids: dict[str, str],
    base_voltage_cache: dict[str, str],
) -> None:
    buses = list(getattr(fuse, "buses", []))
    if len(buses) < 2:
        return
    if buses[0].name not in bus_node_ids or buses[1].name not in bus_node_ids:
        return

    fuse_id = writer._deterministic_id("fuse", fuse.name)
    fuse_element = writer._create_identified_object(root, "Fuse", fuse_id, fuse.name)

    rated_current = writer._quantity(getattr(fuse.equipment, "ampacity", 0.0), "ampere")
    writer._add_literal(fuse_element, "Switch.ratedCurrent", rated_current)

    states = list(getattr(fuse, "is_closed", []))
    is_open = not all(states) if states else False
    state_text = "true" if is_open else "false"
    writer._add_literal(fuse_element, "Switch.normalOpen", state_text)
    writer._add_literal(fuse_element, "Switch.open", state_text)

    base_voltage_id = writer._create_base_voltage(
        root,
        writer._bus_nominal_voltage(buses[0]),
        base_voltage_cache,
    )
    writer._add_ref(fuse_element, "ConductingEquipment.BaseVoltage", base_voltage_id)
    writer._add_ref(fuse_element, "PowerSystemResource.Location", bus_location_ids[buses[0].name])

    writer._create_terminal(root, fuse_id, bus_node_ids[buses[0].name], f"{fuse.name}:1")
    writer._create_terminal(root, fuse_id, bus_node_ids[buses[1].name], f"{fuse.name}:2")
