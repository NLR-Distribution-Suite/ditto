from ditto.readers.cyme.cyme_mapper import CymeMapper
from gdm.quantities import Distance, Current, ResistancePULength, ReactancePULength, CapacitancePULength
from gdm.distribution.equipment.matrix_impedance_switch_equipment import MatrixImpedanceSwitchEquipment
from gdm.distribution.enums import LineType

class MatrixImpedanceSwitchEquipmentMapper(CymeMapper):
    def __init__(self, system):
        super().__init__(system)

    cyme_file = 'Equipment'
    cyme_section = 'SWITCH'

    def parse(self, row, phases):
        name = self.map_name(row, phases)
        r_matrix = self.map_r_matrix(phases)
        x_matrix = self.map_x_matrix(phases)
        c_matrix = self.map_c_matrix(phases)
        ampacity = self.map_ampacity(row)

        return MatrixImpedanceSwitchEquipment(
            name=name,
            construction=LineType.OVERHEAD,
            r_matrix=r_matrix,
            x_matrix=x_matrix,
            c_matrix=c_matrix,
            ampacity=ampacity
        )

    def map_name(self, row, phases):
        return f"{row['ID']}_{len(phases)}"

    def map_r_matrix(self, phases):
        default_matrix = [
            [1e-6, 0.0, 0.0],
            [0.0, 1e-6, 0.0],
            [0.0, 0.0, 1e-6],
        ]
        matrix = [row[:len(phases)] for row in default_matrix[:len(phases)]]
        return ResistancePULength(
            matrix,
            "ohm/mi",
        )

    def map_x_matrix(self, phases):
        default_matrix = [
                    [1e-4, 0.0, 0.0],
                    [0.0, 1e-4, 0.0],
                    [0.0, 0.0, 1e-4],
                ]
        matrix = [row[:len(phases)] for row in default_matrix[:len(phases)]]
        return ReactancePULength(
                matrix,
                "ohm/mi",
            )

    def map_c_matrix(self, phases):
        default_matrix = [
                    [0.0, 0.0, 0.0],
                    [0.0, 0.0, 0.0],
                    [0.0, 0.0, 0.0],
                ]
        matrix = [row[:len(phases)] for row in default_matrix[:len(phases)]]

        return CapacitancePULength(
                matrix,
                "nanofarad/mi",
            )

    def map_ampacity(self, row):
        return Current(float(row['Amps']), "ampere")
    

