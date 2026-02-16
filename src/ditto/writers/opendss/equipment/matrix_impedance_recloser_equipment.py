from gdm.distribution import DistributionSystem
from infrasys import Component


from ditto.writers.opendss.equipment.matrix_impedance_branch_equipment import (
    MatrixImpedanceBranchEquipmentMapper,
)
from ditto.enumerations import OpenDSSFileTypes


class MatrixImpedanceRecloserEquipmentMapper(MatrixImpedanceBranchEquipmentMapper):
    def __init__(self, model: Component, system: DistributionSystem):
        super().__init__(model, system)

    altdss_name = "LineCode_ZMatrixCMatrix"
    altdss_composition_name = "LineCode"
    opendss_file = OpenDSSFileTypes.SWITCH_CODES_FILE.value

    def map_controller(self):
        # Not mapped in OpenDSS
        pass
