
from gdm.quantities import Current, Distance, ResistancePULength, Distance, Voltage
from ditto.readers.cyme.cyme_mapper import CymeMapper
from gdm.distribution.equipment.matrix_impedance_branch_equipment import MatrixImpedanceBranchEquipment
from gdm.distribution.enums import Phase
import numpy as np

class MatrixImpedanceBranchEquipmentMapper(CymeMapper):
    def __init__(self, system):
        super().__init__(system)

    cyme_file = 'Equipment'
    cyme_section = 'CABLE'
    
    def _sequence_impedance_to_phase_impedance_matrix(self, r1, r0, phases=3):
        """
        Return the phase resistance matrix given
        positive-sequence r1 and zero-sequence r0.
        Assumes r2 = r1 (typical for transposed lines/cables).
        """
        if phases == 3:
            r_s = (r0 + 2*r1) / 3.0  # self term
            r_m = (r0 - r1) / 3.0    # mutual term
            R = np.array([[r_s, r_m, r_m],
                        [r_m, r_s, r_m],
                        [r_m, r_m, r_s]], dtype=float)
        elif phases == 2:
            r_s = (r0 + 2*r1) / 3.0  # self term
            r_m = (r0 - r1) / 3.0    # mutual term
            R = np.array([[r_s, r_m],
                        [r_m, r_s]], dtype=float)
        elif phases == 1:
            r_s = (r0 + 2*r1) / 3.0  # self term
            R = np.array([[r_s]], dtype=float)
        return R

    def parse(self, row, phases):
        num_phases = len(phases)
        name = self.map_name(row, num_phases)
        r_matrix = self.map_r_matrix(row, num_phases)
        x_matrix = self.map_x_matrix(row, num_phases)
        c_matrix = self.map_c_matrix(row, num_phases)
        ampacity = self.map_ampacity(row)
        try:
            return MatrixImpedanceBranchEquipment(name=name,
                                        r_matrix=r_matrix,
                                        x_matrix=x_matrix,
                                        c_matrix=c_matrix,
                                        ampacity=ampacity)
        except Exception as e:
            print(f"Error creating MatrixImpedanceBranchEquipment {name}: {e}")
            return None

    def map_name(self, row, phases):
        name = f"{row['ID']}_{phases}"
        return name
    
    def map_r_matrix(self, row, phases):
        r1 = float(row['R1'])
        r0 = float(row['R0'])
        matrix = self._sequence_impedance_to_phase_impedance_matrix(r1, r0, phases)
        matrix = ResistancePULength(np.array(matrix), "ohm/mile")
        return matrix

    def map_x_matrix(self, row, phases):
        x1 = float(row['X1'])
        x0 = float(row['X0'])
        matrix = self._sequence_impedance_to_phase_impedance_matrix(x1, x0, phases)
        matrix =  ResistancePULength(np.array(matrix), "ohm/mile")
        return matrix

    def map_c_matrix(self, row, phases):
        b1 = float(row['B1'])
        b0 = float(row['B0'])
        susceptance_matrix = self._sequence_impedance_to_phase_impedance_matrix(b1, b0, phases)
        # Convert susceptance to capacitance: C = B / (2 * pi * f)
        frequency = 60  # Hz
        capacitance_matrix = susceptance_matrix / (2 * np.pi * frequency)
        capacitance_matrix =  ResistancePULength(np.array(capacitance_matrix), "farad/mile")
        return capacitance_matrix

    def map_ampacity(self, row):
        ampacity = float(row['Amps'])
        return ampacity