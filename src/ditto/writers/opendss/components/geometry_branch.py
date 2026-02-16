from gdm.distribution import DistributionSystem
from infrasys import Component


from ditto.writers.opendss.components.distribution_branch import DistributionBranchMapper
from ditto.enumerations import OpenDSSFileTypes


class GeometryBranchMapper(DistributionBranchMapper):
    def __init__(self, model: Component, system: DistributionSystem):
        super().__init__(model, system)

    altdss_name = "Line_LineGeometry"
    altdss_composition_name = "Line"
    opendss_file = OpenDSSFileTypes.LINES_FILE.value

    def map_equipment(self):
        self.opendss_dict["Geometry"] = self.get_opendss_safe_name(self.model.equipment.name)

    def map_in_service(self):
        self.opendss_dict["enabled"] = self.model.in_service
