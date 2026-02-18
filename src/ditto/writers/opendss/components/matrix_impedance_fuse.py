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
        self.opendss_dict["LineCode"] = self.model.equipment.name

    def map_is_closed(self):
        self.opendss_dict["Switch"] = True
        if not all(self.model.is_closed):
            self.opendss_dict["Enabled"] = False

    def map_in_service(self):
        if not self.model.in_service:
            self.opendss_dict["Enabled"] = False
