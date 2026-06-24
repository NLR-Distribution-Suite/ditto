from gdm.quantities import ResistancePULength
from ditto.readers.cyme.cyme_mapper import CymeMapper
from gdm.distribution.equipment.matrix_impedance_branch_equipment import (
    MatrixImpedanceBranchEquipment,
)
import numpy as np
from ditto.readers.cyme.constants import ModelUnitSystem


class MatrixImpedanceBranchEquipmentMapper(CymeMapper):
    def __init__(self, system, units=ModelUnitSystem):
        super().__init__(system, units=units)

    cyme_file = "Equipment"
    cyme_section = ["CABLE", "LINE UNBALANCED"]

    def _sequence_impedance_to_phase_impedance_matrix(self, r1, r0, phases=3):
        """
        Return the phase resistance matrix given
        positive-sequence r1 and zero-sequence r0.
        Assumes r2 = r1 (typical for transposed lines/cables).
        """
        if phases == 3:
            r_s = (r0 + 2 * r1) / 3.0  # self term
            r_m = (r0 - r1) / 3.0  # mutual term
            R = np.array([[r_s, r_m, r_m], [r_m, r_s, r_m], [r_m, r_m, r_s]], dtype=float)
        elif phases == 2:
            r_s = (r0 + 2 * r1) / 3.0  # self term
            r_m = (r0 - r1) / 3.0  # mutual term
            R = np.array([[r_s, r_m], [r_m, r_s]], dtype=float)
        elif phases == 1:
            r_s = (r0 + 2 * r1) / 3.0  # self term
            R = np.array([[r_s]], dtype=float)
        return R

    def _get_reduction_mask(self, matrix):
        non_zero_rows = ~np.all(matrix == 0, axis=1)
        non_zero_cols = ~np.all(matrix == 0, axis=0)
        return non_zero_rows | non_zero_cols

    def _reduce(self, matrix, mask):
        return matrix[np.ix_(mask, mask)]

    def parse(self, row, phases):
        num_phases = len(phases)
        name = self.map_name(row, num_phases)
        r_matrix = self.map_r_matrix(row, num_phases)
        x_matrix = self.map_x_matrix(row, num_phases)
        c_matrix = self.map_c_matrix(row, num_phases)
        ampacity = self.map_ampacity(row)
        mask = self._get_reduction_mask(r_matrix) | self._get_reduction_mask(x_matrix)
        try:
            model = MatrixImpedanceBranchEquipment(
                name=name,
                r_matrix=self._reduce(r_matrix, mask),
                x_matrix=self._reduce(x_matrix, mask),
                c_matrix=self._reduce(c_matrix, mask),
                ampacity=ampacity,
            )
            return model
        except Exception as e:
            print(f"Error creating MatrixImpedanceBranchEquipment {name}: {e}")
            return None

    def map_name(self, row, phases):
        name = f"{row['ID']}_{phases}"
        return name

    def _build_phase_matrix(self, row, self_tag: str, mutual_tag: str):
        n = 3
        matrix = np.zeros((n, n), dtype=float)
        imp_map = {0: "a", 1: "b", 2: "c"}
        for i in range(n):
            matrix[i, i] = float(row.get(f"{self_tag}{imp_map[i]}", 0.0))  # self impedance
            for j in range(n):
                if i != j:
                    tag = f"{mutual_tag}{imp_map[i].upper()}{imp_map[j].upper()}"
                    if tag in row:
                        matrix[i, j] = float(row.get(tag, 0.0))  # mutual impedance
                        matrix[j, i] = matrix[i, j]  # ensure symmetry
        return matrix

    def map_r_matrix(self, row, phases):
        if "R1" in row:
            r1 = float(row["R1"])
            r0 = float(row["R0"])
            matrix = self._sequence_impedance_to_phase_impedance_matrix(r1, r0, phases)
        elif "Ra" in row:
            matrix = self._build_phase_matrix(row, "R", "MutualResistance")
        else:
            raise ValueError(
                f"Neither sequence nor phase resistance values found for equipment {row['ID']}"
            )

        if self.units == ModelUnitSystem.SI:
            matrix = ResistancePULength(np.array(matrix), "ohm/km")
        else:
            matrix = ResistancePULength(np.array(matrix), "ohm/mile")
        return matrix

    def map_x_matrix(self, row, phases):
        if "X1" in row:
            x1 = float(row["X1"])
            x0 = float(row["X0"])
            matrix = self._sequence_impedance_to_phase_impedance_matrix(x1, x0, phases)
        elif "Xa" in row:
            matrix = self._build_phase_matrix(row, "X", "MutualReactance")
        else:
            raise ValueError(
                f"Neither sequence nor phase reactance values found for equipment {row['ID']}"
            )
        if self.units == ModelUnitSystem.SI:
            matrix = ResistancePULength(np.array(matrix), "ohm/km")
        else:
            matrix = ResistancePULength(np.array(matrix), "ohm/mile")
        return matrix

    def map_c_matrix(self, row, phases):
        if "B1" in row:
            b1 = float(row["B1"])
            b0 = float(row["B0"])
            susceptance_matrix = self._sequence_impedance_to_phase_impedance_matrix(b1, b0, phases)
        elif "Ba" in row:
            susceptance_matrix = self._build_phase_matrix(row, "B", "MutualShuntSusceptance")
        else:
            raise ValueError(
                f"Neither sequence nor phase susceptance values found for equipment {row['ID']}"
            )
        # Convert susceptance to capacitance: C = B / (2 * pi * f)
        frequency = 60  # Hz
        capacitance_matrix = susceptance_matrix / (2 * np.pi * frequency)
        if self.units == ModelUnitSystem.SI:
            capacitance_matrix = ResistancePULength(np.array(capacitance_matrix), "microfarad/km")
        else:
            capacitance_matrix = ResistancePULength(
                np.array(capacitance_matrix), "microfarad/mile"
            )
        return capacitance_matrix

    def map_ampacity(self, row):
        if "Amps" in row:
            ampacity = float(row["Amps"])
        elif "AmpsA" in row:
            ampacity = (
                sum(
                    [
                        float(row["AmpsA"]),
                        float(row["AmpsB"]),
                        float(row["AmpsC"]),
                    ]
                )
                / 3
            )
        else:
            raise ValueError(f"Ampacity value not found for equipment {row['ID']}")
        return ampacity
