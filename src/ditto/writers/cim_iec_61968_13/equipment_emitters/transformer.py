from __future__ import annotations

import xml.etree.ElementTree as ET


def emit_transformer_mesh_impedance(
    writer,
    root: ET.Element,
    xfmr_name: str,
    end_1_id: str,
    end_2_id: str,
    winding_1,
    winding_reactances: list,
) -> None:
    mesh_id = writer._deterministic_id("transformer_mesh_impedance", xfmr_name)
    mesh = writer._create_identified_object(
        root,
        "TransformerMeshImpedance",
        mesh_id,
        f"{xfmr_name}_mesh",
    )
    per_x = winding_reactances[0] if winding_reactances else 1.0
    x1 = writer._winding_reactance_ohm(winding_1, per_x)
    x0 = x1
    r1 = writer._winding_resistance_ohm(winding_1)
    r0 = r1
    writer._add_literal(mesh, "TransformerMeshImpedance.r", r1)
    writer._add_literal(mesh, "TransformerMeshImpedance.x", x1)
    writer._add_literal(mesh, "TransformerMeshImpedance.r0", r0)
    writer._add_literal(mesh, "TransformerMeshImpedance.x0", x0)
    writer._add_ref(mesh, "TransformerMeshImpedance.FromTransformerEnd", end_1_id)
    writer._add_ref(mesh, "TransformerMeshImpedance.ToTransformerEnd", end_2_id)


def emit_power_transformer(
    writer,
    root: ET.Element,
    xfmr_name: str,
    buses: list,
    winding_phases: list,
    equipment,
    bus_node_ids: dict[str, str],
    bus_location_ids: dict[str, str],
    base_voltage_cache: dict[str, str],
) -> tuple[str, list[str], list[str], list[str]]:
    power_id = writer._deterministic_id("power_transformer", xfmr_name)
    power = writer._create_identified_object(root, "PowerTransformer", power_id, xfmr_name)

    if buses:
        writer._add_ref(power, "PowerSystemResource.Location", bus_location_ids[buses[0].name])
        nominal_voltage = writer._bus_nominal_voltage(buses[0])
        base_voltage_id = writer._create_base_voltage(root, nominal_voltage, base_voltage_cache)
        writer._add_ref(power, "ConductingEquipment.BaseVoltage", base_voltage_id)

    windings = list(getattr(equipment, "windings", []))
    if len(windings) < 2:
        return power_id, [], [], []

    vector_group = "".join(writer._connection_kind(winding) for winding in windings[:2])
    writer._add_literal(power, "PowerTransformer.vectorGroup", vector_group)

    end_ids: list[str] = []
    tank_end_ids: list[str] = []
    terminal_ids: list[str] = []

    for index, (winding, bus) in enumerate(zip(windings[:2], buses[:2]), start=1):
        end_id = writer._deterministic_id("power_transformer_end", f"{xfmr_name}:{index}")
        end_ids.append(end_id)
        end = writer._create_identified_object(
            root,
            "PowerTransformerEnd",
            end_id,
            f"{xfmr_name}_end_{index}",
        )
        writer._add_ref(end, "PowerTransformerEnd.PowerTransformer", power_id)
        writer._add_literal(
            end,
            "PowerTransformerEnd.ratedS",
            writer._quantity(getattr(winding, "rated_power", 0.0), "VA"),
        )
        writer._add_literal(
            end, "PowerTransformerEnd.ratedU", writer._line_to_line_winding_voltage(winding)
        )
        writer._add_literal(end, "PowerTransformerEnd.r", writer._winding_resistance_ohm(winding))
        writer._add_literal(
            end, "PowerTransformerEnd.connectionKind", writer._connection_kind(winding)
        )
        writer._add_literal(end, "PowerTransformerEnd.phaseAngleClock", index - 1)
        writer._add_literal(end, "TransformerEnd.endNumber", index)

        terminal_id = writer._create_terminal(
            root,
            power_id,
            bus_node_ids[bus.name],
            f"{xfmr_name}:terminal:{index}",
        )
        terminal_ids.append(terminal_id)
        writer._add_ref(end, "TransformerEnd.Terminal", terminal_id)
        winding_base_voltage_id = writer._create_base_voltage(
            root,
            writer._line_to_line_winding_voltage(winding),
            base_voltage_cache,
        )
        writer._add_ref(end, "TransformerEnd.BaseVoltage", winding_base_voltage_id)

        tank_end_id = writer._deterministic_id("transformer_tank_end", f"{xfmr_name}:{index}")
        tank_end_ids.append(tank_end_id)

    emit_transformer_mesh_impedance(
        writer,
        root,
        xfmr_name,
        end_ids[0],
        end_ids[1],
        windings[0],
        getattr(equipment, "winding_reactances", []),
    )
    return power_id, end_ids, tank_end_ids, terminal_ids


def emit_distribution_transformer(
    writer,
    root: ET.Element,
    transformer,
    bus_node_ids: dict[str, str],
    bus_location_ids: dict[str, str],
    base_voltage_cache: dict[str, str],
) -> None:
    if len(getattr(transformer, "buses", [])) < 2:
        return
    emit_power_transformer(
        writer,
        root,
        transformer.name,
        transformer.buses,
        getattr(transformer, "winding_phases", []),
        transformer.equipment,
        bus_node_ids,
        bus_location_ids,
        base_voltage_cache,
    )


def emit_regulator(
    writer,
    root: ET.Element,
    regulator,
    bus_node_ids: dict[str, str],
    bus_location_ids: dict[str, str],
    base_voltage_cache: dict[str, str],
) -> None:
    buses = list(getattr(regulator, "buses", []))
    if len(buses) < 2:
        return

    equipment = regulator.equipment
    power_id, _, tank_end_ids, power_terminal_ids = emit_power_transformer(
        writer,
        root,
        f"{regulator.name}_power",
        buses,
        getattr(regulator, "winding_phases", []),
        equipment,
        bus_node_ids,
        bus_location_ids,
        base_voltage_cache,
    )

    tank_info_id = writer._deterministic_id("transformer_tank_info", regulator.name)
    writer._create_identified_object(
        root,
        "TransformerTankInfo",
        tank_info_id,
        f"{regulator.name}_tank_info",
    )

    tank_id = writer._deterministic_id("transformer_tank", regulator.name)
    tank = writer._create_identified_object(root, "TransformerTank", tank_id, regulator.name)
    writer._add_ref(tank, "TransformerTank.TransformerTankInfo", tank_info_id)
    writer._add_ref(tank, "TransformerTank.PowerTransformer", power_id)
    writer._add_ref(tank, "PowerSystemResource.Location", bus_location_ids[buses[0].name])

    windings = list(getattr(equipment, "windings", []))
    for index, winding in enumerate(windings[:2], start=1):
        end_info_id = writer._deterministic_id("transformer_end_info", f"{regulator.name}:{index}")
        end_info = writer._create_identified_object(
            root,
            "TransformerEndInfo",
            end_info_id,
            f"{regulator.name}_end_{index}",
        )
        writer._add_ref(end_info, "TransformerEndInfo.TransformerTankInfo", tank_info_id)
        writer._add_literal(
            end_info,
            "TransformerEndInfo.ratedS",
            writer._quantity(getattr(winding, "rated_power", 0.0), "VA"),
        )
        writer._add_literal(
            end_info, "TransformerEndInfo.ratedU", writer._line_to_line_winding_voltage(winding)
        )
        writer._add_literal(
            end_info, "TransformerEndInfo.r", writer._winding_resistance_ohm(winding)
        )
        writer._add_literal(
            end_info, "TransformerEndInfo.connectionKind", writer._connection_kind(winding)
        )
        writer._add_literal(end_info, "TransformerEndInfo.phaseAngleClock", index - 1)
        writer._add_literal(end_info, "TransformerEndInfo.endNumber", index)

        tank_end = writer._create_identified_object(
            root,
            "TransformerTankEnd",
            tank_end_ids[index - 1],
            f"{regulator.name}_tank_end_{index}",
        )
        writer._add_ref(tank_end, "TransformerTankEnd.TransformerTank", tank_id)
        phases = getattr(regulator, "winding_phases", [])
        phase_text = (
            writer._winding_phases_text(phases[index - 1]) if len(phases) >= index else "ABC"
        )
        writer._add_literal(tank_end, "TransformerTankEnd.orderedPhases", phase_text)

    controllers = list(getattr(regulator, "controllers", []))
    controller = controllers[0] if controllers else None
    if controller is None:
        return

    tap_changer_id = writer._deterministic_id("ratio_tap_changer", regulator.name)
    tap_changer = writer._create_identified_object(
        root,
        "RatioTapChanger",
        tap_changer_id,
        regulator.name,
    )
    writer._add_ref(tap_changer, "RatioTapChanger.TransformerEnd", tank_end_ids[0])

    primary_winding = windings[0] if windings else None
    (
        dv_percent,
        high_step,
        low_step,
        neutral_step,
        normal_step,
        current_step,
    ) = writer._tap_step_values(primary_winding)

    writer._add_literal(tap_changer, "TapChanger.highStep", high_step)
    writer._add_literal(tap_changer, "TapChanger.lowStep", low_step)
    writer._add_literal(tap_changer, "TapChanger.neutralStep", neutral_step)
    writer._add_literal(tap_changer, "TapChanger.normalStep", normal_step)
    writer._add_literal(tap_changer, "RatioTapChanger.stepVoltageIncrement", dv_percent)
    writer._add_literal(tap_changer, "TapChanger.step", current_step)
    writer._add_literal(
        tap_changer, "TapChanger.neutralU", writer._quantity(controller.v_setpoint, "volt")
    )
    writer._add_literal(
        tap_changer, "TapChanger.initialDelay", writer._quantity(controller.delay, "second")
    )
    writer._add_literal(
        tap_changer, "TapChanger.subsequentDelay", writer._quantity(controller.delay, "second")
    )
    writer._add_literal(tap_changer, "TapChanger.ltcFlag", "true")
    writer._add_literal(tap_changer, "TapChanger.controlEnabled", "true")
    writer._add_literal(
        tap_changer, "TapChanger.ptRatio", float(getattr(controller, "pt_ratio", 1.0))
    )
    writer._add_literal(tap_changer, "TapChanger.ctRatio", 1.0)
    writer._add_literal(
        tap_changer, "TapChanger.ctRating", writer._quantity(controller.ct_primary, "ampere")
    )

    control_id = writer._deterministic_id("tap_changer_control", regulator.name)
    control = writer._create_identified_object(
        root,
        "TapChangerControl",
        control_id,
        f"{regulator.name}_control",
    )
    writer._add_ref(tap_changer, "TapChanger.TapChangerControl", control_id)

    writer._add_literal(control, "RegulatingControl.mode", "voltage")
    writer._add_ref(control, "RegulatingControl.Terminal", power_terminal_ids[0])
    writer._add_ref(control, "PowerSystemResource.Location", bus_location_ids[buses[0].name])
    writer._add_literal(
        control,
        "RegulatingControl.monitoredPhase",
        writer._phase_text(controller.controlled_phase),
    )
    writer._add_literal(
        control, "RegulatingControl.targetValue", writer._quantity(controller.v_setpoint, "volt")
    )
    writer._add_literal(
        control, "RegulatingControl.targetDeadband", writer._quantity(controller.bandwidth, "volt")
    )
    writer._add_literal(
        control,
        "TapChangerControl.lineDropCompensation",
        str(getattr(controller, "use_ldc", False)).lower(),
    )
    writer._add_literal(
        control, "TapChangerControl.lineDropR", writer._quantity(controller.ldc_R, "volt")
    )
    writer._add_literal(
        control, "TapChangerControl.lineDropX", writer._quantity(controller.ldc_X, "volt")
    )
    writer._add_literal(
        control,
        "TapChangerControl.reversible",
        str(getattr(controller, "is_reversible", False)).lower(),
    )
    writer._add_literal(
        control,
        "TapChangerControl.maxLimitVoltage",
        writer._quantity(controller.max_v_limit, "volt"),
    )
    writer._add_literal(
        control,
        "TapChangerControl.minLimitVoltage",
        writer._quantity(controller.min_v_limit, "volt"),
    )

    short_test_id = writer._deterministic_id("short_circuit_test", regulator.name)
    short_test = writer._create_identified_object(
        root,
        "ShortCircuitTest",
        short_test_id,
        f"{regulator.name}_short_test",
    )
    x_test = (
        writer._winding_reactance_ohm(primary_winding, equipment.winding_reactances[0])
        if getattr(equipment, "winding_reactances", []) and primary_winding
        else 0.0
    )
    r_test = writer._winding_resistance_ohm(primary_winding) if primary_winding else 0.0
    writer._add_ref(
        short_test,
        "ShortCircuitTest.EnergisedEnd",
        writer._deterministic_id("transformer_end_info", f"{regulator.name}:1"),
    )
    writer._add_literal(short_test, "ShortCircuitTest.leakageImpedance", x_test)
    writer._add_literal(short_test, "ShortCircuitTest.leakageImpedanceZero", x_test)
    writer._add_literal(short_test, "ShortCircuitTest.loss", r_test)
    writer._add_literal(short_test, "ShortCircuitTest.lossZero", r_test)
