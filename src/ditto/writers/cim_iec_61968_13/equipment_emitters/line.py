from __future__ import annotations

import math
import xml.etree.ElementTree as ET


def emit_line_code_equipment(
    writer, root: ET.Element, branch_equipment, emitted_ids: set[str]
) -> str:
    line_code_id = writer._deterministic_id("per_length_impedance", branch_equipment.name)
    if line_code_id in emitted_ids:
        return line_code_id

    emitted_ids.add(line_code_id)
    line_code = writer._create_identified_object(
        root,
        "PerLengthPhaseImpedance",
        line_code_id,
        branch_equipment.name,
    )

    r_matrix = branch_equipment.r_matrix.magnitude
    x_matrix = branch_equipment.x_matrix.magnitude
    c_matrix = branch_equipment.c_matrix.magnitude
    conductor_count = int(r_matrix.shape[0])
    writer._add_literal(line_code, "PerLengthPhaseImpedance.conductorCount", conductor_count)

    for row in range(conductor_count):
        for col in range(row + 1):
            phase_data_id = writer._deterministic_id(
                "phase_impedance_data",
                f"{branch_equipment.name}:{row + 1}:{col + 1}",
            )
            phase_data = writer._create_identified_object(
                root,
                "PhaseImpedanceData",
                phase_data_id,
                f"{branch_equipment.name}_{row + 1}_{col + 1}",
            )
            writer._add_ref(phase_data, "PhaseImpedanceData.PhaseImpedance", line_code_id)
            writer._add_literal(phase_data, "PhaseImpedanceData.r", float(r_matrix[row, col]))
            writer._add_literal(phase_data, "PhaseImpedanceData.x", float(x_matrix[row, col]))
            susceptance = float(c_matrix[row, col]) * 2 * math.pi * 60
            writer._add_literal(phase_data, "PhaseImpedanceData.b", susceptance)
            writer._add_literal(phase_data, "PhaseImpedanceData.row", row + 1)
            writer._add_literal(phase_data, "PhaseImpedanceData.column", col + 1)

    return line_code_id


def emit_line_segment(
    writer,
    root: ET.Element,
    branch,
    bus_node_ids: dict[str, str],
    bus_location_ids: dict[str, str],
    base_voltage_cache: dict[str, str],
    emitted_line_code_ids: set[str],
) -> None:
    if not getattr(branch, "buses", None) or len(branch.buses) < 2:
        return
    if not getattr(branch, "equipment", None):
        return

    line_id = writer._deterministic_id("line_segment", branch.name)
    line = writer._create_identified_object(root, "ACLineSegment", line_id, branch.name)

    nominal_voltage = writer._bus_nominal_voltage(branch.buses[0])
    base_voltage_id = writer._create_base_voltage(root, nominal_voltage, base_voltage_cache)
    writer._add_ref(line, "ConductingEquipment.BaseVoltage", base_voltage_id)
    writer._add_ref(line, "PowerSystemResource.Location", bus_location_ids[branch.buses[0].name])
    writer._add_literal(line, "Conductor.length", writer._quantity(branch.length, "meter"))

    line_code_id = emit_line_code_equipment(writer, root, branch.equipment, emitted_line_code_ids)
    writer._add_ref(line, "ACLineSegment.PerLengthImpedance", line_code_id)

    for index, phase in enumerate(getattr(branch, "phases", []), start=1):
        phase_id = writer._deterministic_id("line_segment_phase", f"{branch.name}:{index}")
        line_phase = writer._create_identified_object(
            root,
            "ACLineSegmentPhase",
            phase_id,
            f"{branch.name}_phase_{index}",
        )
        writer._add_ref(line_phase, "ACLineSegmentPhase.ACLineSegment", line_id)
        writer._add_literal(line_phase, "ACLineSegmentPhase.phase", writer._phase_text(phase))

    ampacity = writer._quantity(getattr(branch.equipment, "ampacity", 0.0), "ampere")
    writer._create_terminal(
        root,
        line_id,
        bus_node_ids[branch.buses[0].name],
        f"{branch.name}:1",
        with_limits=True,
        ampacity=ampacity,
    )
    writer._create_terminal(
        root,
        line_id,
        bus_node_ids[branch.buses[1].name],
        f"{branch.name}:2",
        with_limits=True,
        ampacity=ampacity,
    )
