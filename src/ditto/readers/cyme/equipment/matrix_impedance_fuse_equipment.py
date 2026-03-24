from ditto.readers.cyme.cyme_mapper import CymeMapper
from gdm.quantities import Distance, Current, ResistancePULength, ReactancePULength, CapacitancePULength
from gdm.distribution.equipment.matrix_impedance_fuse_equipment import MatrixImpedanceFuseEquipment
from gdm.distribution.common.curve import TimeCurrentCurve
from infrasys.quantities import Time
from gdm.distribution.enums import LineType


class MatrixImpedanceFuseEquipmentMapper(CymeMapper):
    def __init__(self, system):
        super().__init__(system)

    cyme_file = 'Equipment'
    cyme_section = 'FUSE'

    def parse(self, row, phases):
        name = self.map_name(row, phases)
        delay = self.map_delay(row)
        tcc_curve = self.map_tcc_curve(row)
        r_matrix = self.map_r_matrix(phases)
        x_matrix = self.map_x_matrix(phases)
        c_matrix = self.map_c_matrix(phases)
        ampacity = self.map_ampacity(row)

        return MatrixImpedanceFuseEquipment(
            name=name,
            delay=delay,
            tcc_curve=tcc_curve,
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
    
    def map_delay(self, row):
        return Time(0, "minutes")
    
    def map_tcc_curve(self, row):
        return TimeCurrentCurve.example()

