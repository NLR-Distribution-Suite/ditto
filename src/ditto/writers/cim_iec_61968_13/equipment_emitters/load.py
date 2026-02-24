from __future__ import annotations

import xml.etree.ElementTree as ET


def emit_energy_consumer(
    writer,
    root: ET.Element,
    load,
    bus_node_ids: dict[str, str],
    bus_location_ids: dict[str, str],
    base_voltage_cache: dict[str, str],
) -> None:
    bus = load.bus
    load_id = writer._deterministic_id("energy_consumer", load.name)
    load_element = writer._create_identified_object(root, "EnergyConsumer", load_id, load.name)

    nominal_voltage = writer._bus_nominal_voltage(bus)
    base_voltage_id = writer._create_base_voltage(root, nominal_voltage, base_voltage_cache)
    writer._add_ref(load_element, "ConductingEquipment.BaseVoltage", base_voltage_id)
    writer._add_ref(load_element, "PowerSystemResource.Location", bus_location_ids[bus.name])

    total_p = 0.0
    total_q = 0.0
    z_p = 0.0
    i_p = 0.0
    p_p = 0.0
    z_q = 0.0
    i_q = 0.0
    p_q = 0.0
    phase_loads = getattr(load.equipment, "phase_loads", [])
    if phase_loads:
        for phase_load in phase_loads:
            total_p += writer._quantity(getattr(phase_load, "real_power", 0.0), "watt")
            total_q += writer._quantity(getattr(phase_load, "reactive_power", 0.0), "var")
        lead = phase_loads[0]
        z_p = float(getattr(lead, "z_real", 0.0)) * 100.0
        i_p = float(getattr(lead, "i_real", 0.0)) * 100.0
        p_p = float(getattr(lead, "p_real", 0.0)) * 100.0
        z_q = float(getattr(lead, "z_imag", 0.0)) * 100.0
        i_q = float(getattr(lead, "i_imag", 0.0)) * 100.0
        p_q = float(getattr(lead, "p_imag", 0.0)) * 100.0

    conn_type = writer._safe_text(getattr(load.equipment, "connection_type", "STAR"))
    conn_code = "D" if "DELTA" in conn_type else "Y"
    grounded = "false" if conn_code == "D" else "true"

    writer._add_literal(load_element, "EnergyConsumer.p", total_p)
    writer._add_literal(load_element, "EnergyConsumer.q", total_q)
    writer._add_literal(load_element, "EnergyConsumer.phaseConnection", conn_code)
    writer._add_literal(load_element, "EnergyConsumer.grounded", grounded)

    zip_id = writer._deterministic_id("load_response", load.name)
    zip_element = writer._create_identified_object(
        root,
        "LoadResponseCharacteristic",
        zip_id,
        f"ZIP_{load.name}",
    )
    writer._add_literal(zip_element, "LoadResponseCharacteristic.pConstantImpedance", z_p)
    writer._add_literal(zip_element, "LoadResponseCharacteristic.pConstantCurrent", i_p)
    writer._add_literal(zip_element, "LoadResponseCharacteristic.pConstantPower", p_p)
    writer._add_literal(zip_element, "LoadResponseCharacteristic.qConstantImpedance", z_q)
    writer._add_literal(zip_element, "LoadResponseCharacteristic.qConstantCurrent", i_q)
    writer._add_literal(zip_element, "LoadResponseCharacteristic.qConstantPower", p_q)
    writer._add_literal(zip_element, "LoadResponseCharacteristic.pVoltageExponent", 1.0)
    writer._add_literal(zip_element, "LoadResponseCharacteristic.qVoltageExponent", 2.0)
    writer._add_ref(load_element, "EnergyConsumer.LoadResponse", zip_id)

    for index, phase in enumerate(getattr(load, "phases", []), start=1):
        phase_id = writer._deterministic_id("energy_consumer_phase", f"{load.name}:{index}")
        phase_element = writer._create_identified_object(
            root,
            "EnergyConsumerPhase",
            phase_id,
            f"{load.name}_phase_{index}",
        )
        writer._add_ref(phase_element, "EnergyConsumerPhase.EnergyConsumer", load_id)
        writer._add_literal(phase_element, "EnergyConsumerPhase.phase", writer._phase_text(phase))

    writer._create_terminal(root, load_id, bus_node_ids[bus.name], f"{load.name}:1")
