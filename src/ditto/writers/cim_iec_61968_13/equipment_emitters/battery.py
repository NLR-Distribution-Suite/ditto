from __future__ import annotations

import xml.etree.ElementTree as ET


def emit_battery(
    writer,
    root: ET.Element,
    battery,
    bus_node_ids: dict[str, str],
    bus_location_ids: dict[str, str],
    base_voltage_cache: dict[str, str],
) -> None:
    bus = getattr(battery, "bus", None)
    if bus is None or bus.name not in bus_node_ids:
        return

    unit_id = writer._deterministic_id("battery_unit", battery.name)
    unit = writer._create_identified_object(root, "BatteryUnit", unit_id, battery.name)
    writer._add_literal(
        unit,
        "BatteryUnit.ratedE",
        writer._quantity(getattr(battery.equipment, "rated_energy", 0.0), "watthour"),
    )
    writer._add_literal(
        unit,
        "BatteryUnit.storedE",
        writer._quantity(getattr(battery.equipment, "rated_energy", 0.0), "watthour"),
    )

    connection_id = writer._deterministic_id(
        "power_electronics_connection", f"battery:{battery.name}"
    )
    connection = writer._create_identified_object(
        root,
        "PowerElectronicsConnection",
        connection_id,
        battery.name,
    )

    nominal_voltage = writer._bus_nominal_voltage(bus)
    base_voltage_id = writer._create_base_voltage(root, nominal_voltage, base_voltage_cache)
    writer._add_ref(connection, "ConductingEquipment.BaseVoltage", base_voltage_id)
    writer._add_ref(connection, "PowerSystemResource.Location", bus_location_ids[bus.name])
    writer._add_ref(connection, "PowerElectronicsConnection.PowerElectronicsUnit", unit_id)

    writer._add_literal(
        connection,
        "PowerElectronicsConnection.maxP",
        writer._quantity(getattr(battery.equipment, "rated_power", 0.0), "watt"),
    )
    writer._add_literal(
        connection,
        "PowerElectronicsConnection.p",
        writer._quantity(getattr(battery, "active_power", 0.0), "watt"),
    )
    writer._add_literal(
        connection,
        "PowerElectronicsConnection.q",
        writer._quantity(getattr(battery, "reactive_power", 0.0), "var"),
    )

    inverter = getattr(battery, "inverter", None)
    if inverter is not None:
        writer._add_literal(
            connection,
            "PowerElectronicsConnection.ratedS",
            writer._quantity(getattr(inverter, "rated_apparent_power", 0.0), "VA"),
        )

    for index, phase in enumerate(getattr(battery, "phases", []), start=1):
        phase_id = writer._deterministic_id(
            "power_electronics_connection_phase",
            f"battery:{battery.name}:{index}",
        )
        phase_element = writer._create_identified_object(
            root,
            "PowerElectronicsConnectionPhase",
            phase_id,
            f"{battery.name}_phase_{index}",
        )
        writer._add_ref(
            phase_element,
            "PowerElectronicsConnectionPhase.PowerElectronicsConnection",
            connection_id,
        )
        writer._add_literal(
            phase_element,
            "PowerElectronicsConnectionPhase.phase",
            writer._phase_text(phase),
        )

    writer._create_terminal(root, connection_id, bus_node_ids[bus.name], f"{battery.name}:1")
