from gdm.distribution import DistributionSystem
from infrasys import Component


from ditto.writers.opendss.components.distribution_branch import DistributionBranchMapper
from ditto.enumerations import OpenDSSFileTypes


class MatrixImpedanceFuseMapper(DistributionBranchMapper):
    def __init__(self, model: Component, system: DistributionSystem):
        super().__init__(model, system)

    altdss_name = "Line_LineCode"
    altdss_composition_name = "Line"
    opendss_file = OpenDSSFileTypes.FUSE_FILE.value

    def map_equipment(self):
        self.opendss_dict["LineCode"] = self.get_opendss_safe_name(self.model.equipment.name)

    def map_is_closed(self):
        # Require every phase to be enabled for the OpenDSS line to be enabled.
        self.opendss_dict["Switch"] = "true"

    def map_in_service(self):
        self.opendss_dict["enabled"] = self.model.in_service
