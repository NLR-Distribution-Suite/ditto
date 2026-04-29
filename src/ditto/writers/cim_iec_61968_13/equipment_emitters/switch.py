from __future__ import annotations

import xml.etree.ElementTree as ET


def emit_switch(
    writer,
    root: ET.Element,
    switch,
    bus_node_ids: dict[str, str],
    bus_location_ids: dict[str, str],
    base_voltage_cache: dict[str, str],
) -> None:
    buses = list(getattr(switch, "buses", []))
    if len(buses) < 2:
        return
    if buses[0].name not in bus_node_ids or buses[1].name not in bus_node_ids:
        return

    switch_id = writer._deterministic_id("load_break_switch", switch.name)
    switch_element = writer._create_identified_object(
        root, "LoadBreakSwitch", switch_id, switch.name
    )

    rated_current = writer._quantity(getattr(switch.equipment, "ampacity", 0.0), "ampere")
    writer._add_literal(switch_element, "ProtectedSwitch.breakingCapacity", rated_current)
    writer._add_literal(switch_element, "Switch.ratedCurrent", rated_current)

    states = list(getattr(switch, "is_closed", []))
    is_open = not all(states) if states else False
    state_text = "true" if is_open else "false"
    writer._add_literal(switch_element, "Switch.normalOpen", state_text)
    writer._add_literal(switch_element, "Switch.open", state_text)

    base_voltage_id = writer._create_base_voltage(
        root,
        writer._bus_nominal_voltage(buses[0]),
        base_voltage_cache,
    )
    writer._add_ref(switch_element, "ConductingEquipment.BaseVoltage", base_voltage_id)
    writer._add_ref(
        switch_element, "PowerSystemResource.Location", bus_location_ids[buses[0].name]
    )

    writer._create_terminal(root, switch_id, bus_node_ids[buses[0].name], f"{switch.name}:1")
    writer._create_terminal(root, switch_id, bus_node_ids[buses[1].name], f"{switch.name}:2")
