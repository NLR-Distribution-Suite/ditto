from gdm.distribution import DistributionSystem
from infrasys import Component


from ditto.writers.opendss.equipment.matrix_impedance_branch_equipment import (
    MatrixImpedanceBranchEquipmentMapper,
)
from ditto.enumerations import OpenDSSFileTypes


class MatrixImpedanceFuseEquipmentMapper(MatrixImpedanceBranchEquipmentMapper):
    def __init__(self, model: Component, system: DistributionSystem):
        super().__init__(model, system)

    altdss_name = "LineCode_ZMatrixCMatrix"
    altdss_composition_name = "LineCode"
    opendss_file = OpenDSSFileTypes.FUSE_CODES_FILE.value

    def map_name(self):
        self.opendss_dict["Name"] = self.get_opendss_safe_name(self.model.name)

    def map_controller(self):
        # Not mapped in OpenDSS
        pass

    def map_delay(self):
        # Not mapped in OpenDSS
        pass

    def map_tcc_curve(self):
        # Not mapped in OpenDSS
        pass
