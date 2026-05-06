import numpy as np
from gdm.distribution.equipment.matrix_impedance_branch_equipment import MatrixImpedanceBranchEquipment
from gdm.distribution.enums import LineType
from gdm.quantities import ResistancePULength, ReactancePULength, CapacitancePULength
from gdm.distribution.equipment.bare_conductor_equipment import BareConductorEquipment
from infrasys.quantities import Current
from ditto.readers.synergi.synergi_mapper import SynergiMapper
from ditto.readers.synergi.utils import sanitize_name, safe_float
from ditto.readers.synergi.length_units import length_units


class MatrixImpedanceBranchEquipmentMapper(SynergiMapper):

    synergi_table = "DevConductors"
    synergi_database = "Equipment"

    def parse(self, row, unit_type, section_id_sections, from_node_sections, to_node_sections):
        conductor_name = str(row["ConductorName"]).strip()
        per_lul_unit = length_units[unit_type]["PerLUL"]
        lul_unit = length_units[unit_type]["LUL"]

        r1 = safe_float(row.get("PosSequenceResistance_PerLUL"), 0.5) or 0.5
        x1 = safe_float(row.get("PosSequenceReactance_PerLUL"), 0.5) or 0.5
        r0_raw = safe_float(row.get("ZeroSequenceResistance_PerLUL"))
        x0_raw = safe_float(row.get("ZeroSequenceReactance_PerLUL"))
        r0 = r0_raw if r0_raw else r1 * 2
        x0 = x0_raw if x0_raw else x1 * 3
        c1_raw = safe_float(row.get("PosSequenceAdmittance_PerLUL"), 10.0)
        c1 = c1_raw if c1_raw > 0 else 6.21

        # Convert to ohm/km and nF/km for matrix storage
        r1_km = ResistancePULength(r1, per_lul_unit).to("ohm/km").magnitude
        x1_km = ResistancePULength(x1, per_lul_unit).to("ohm/km").magnitude
        r0_km = ResistancePULength(r0, per_lul_unit).to("ohm/km").magnitude
        x0_km = ResistancePULength(x0, per_lul_unit).to("ohm/km").magnitude
        c1_km = CapacitancePULength(c1, f"nF/{lul_unit}").to("nF/km").magnitude

        # Sequence-to-phase transformation
        r_self = (2 * r1_km + r0_km) / 3
        x_self = (2 * x1_km + x0_km) / 3
        r_mut = (r0_km - r1_km) / 3
        x_mut = (x0_km - x1_km) / 3

        ampacity = safe_float(row.get("ContinuousCurrentRating"), 400.0) or 400.0

        # Determine construction by checking whether the conductor is bare (OH) or cable (UG)
        try:
            self.system.get_component(BareConductorEquipment, conductor_name)
            construction = LineType.OVERHEAD
        except Exception:
            construction = LineType.UNDERGROUND

        equipment_list = []
        for n_cond in (1, 2, 3):
            r_matrix = np.full((n_cond, n_cond), r_mut)
            np.fill_diagonal(r_matrix, r_self)
            x_matrix = np.full((n_cond, n_cond), x_mut)
            np.fill_diagonal(x_matrix, x_self)
            c_matrix = np.eye(n_cond) * c1_km

            equipment_list.append(MatrixImpedanceBranchEquipment(
                name=sanitize_name(f"{conductor_name}_{n_cond}ph"),
                construction=construction,
                r_matrix=ResistancePULength(r_matrix, "ohm/km"),
                x_matrix=ReactancePULength(x_matrix, "ohm/km"),
                c_matrix=CapacitancePULength(c_matrix, "nF/km"),
                ampacity=Current(ampacity, "ampere"),
            ))

        return equipment_list
