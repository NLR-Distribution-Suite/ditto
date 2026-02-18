from gdm.distribution import DistributionSystem
from infrasys import Component


from ditto.writers.opendss.components.distribution_branch import DistributionBranchMapper
from ditto.enumerations import OpenDSSFileTypes


class MatrixImpedanceRecloserMapper(DistributionBranchMapper):
    def __init__(self, model: Component, system: DistributionSystem):
        super().__init__(model, system)

    altdss_name = "Line_LineCode"
    altdss_composition_name = "Line"
    opendss_file = OpenDSSFileTypes.RECLOSER_FILE.value

    def map_equipment(self):
        self.opendss_dict["LineCode"] = self.model.equipment.name

    def map_is_closed(self):
        # Model the recloser as a switchable line element
        self.opendss_dict["Switch"] = "true"

    def map_controller(self):
        # Controller is handled separately via write.py's controller loop
        pass

    def map_in_service(self):
        self.opendss_dict["enabled"] = self.model.in_service
