from gdm.distribution.equipment import MatrixImpedanceBranchEquipment
from gdm.quantities import (
    CapacitancePULength,
    ResistancePULength,
    Current,
)
import numpy as np

from ditto.readers.cim_iec_61968_13.cim_mapper import CimMapper


class MatrixImpedanceBranchEquipmentMapper(CimMapper):
    def __init__(self, system):
        super().__init__(system)

    def parse(self, row):
        return MatrixImpedanceBranchEquipment(
            name=self.map_name(row),
            r_matrix=self.map_r_matrix(row),
            x_matrix=self.map_x_matrix(row),
            c_matrix=self.map_c_matrix(row),
            ampacity=self.map_ampacity(row),
        )

    def _array_to_matrix(self, array, n):
        array = [float(x) for x in array]
        matrix = np.zeros((n, n), dtype=float)
        index = 0
        for i in range(n):
            for j in range(i + 1):
                matrix[i, j] = array[index]
                matrix[j, i] = array[index]
                index += 1
        return matrix

    def map_name(self, row):
        return row["line_code"]

    def map_r_matrix(self, row):
        r = row["r"]
        r_matrix = self._array_to_matrix(r, int(row["phase_count"]))
        return ResistancePULength(r_matrix, "ohm/m")

    def map_x_matrix(self, row):
        x = row["x"]
        x_matrix = self._array_to_matrix(x, int(row["phase_count"]))
        return ResistancePULength(x_matrix, "ohm/m")

    def map_c_matrix(self, row):
        b = row["b"]
        b_matrix = self._array_to_matrix(b, int(row["phase_count"]))
        c_matrix = b_matrix / (2 * np.pi * 60)
        return CapacitancePULength(c_matrix, "F/m")

    def map_ampacity(self, row):
        return Current(row["ampacity_normal"], "ampere")
