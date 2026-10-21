from gdm.distribution import DistributionSystem
from infrasys import Component


from ditto.writers.opendss.components.distribution_branch import DistributionBranchMapper
from ditto.enumerations import OpenDSSFileTypes


class MatrixImpedanceSwitchMapper(DistributionBranchMapper):
    def __init__(self, model: Component, system: DistributionSystem):
        super().__init__(model, system)

    altdss_name = "Line_LineCode"
    altdss_composition_name = "Line"
    opendss_file = OpenDSSFileTypes.SWITCH_FILE.value

    def map_name(self):
        self.opendss_dict["Name"] = self.get_opendss_safe_name(self.model.name)

    def map_equipment(self):
        self.opendss_dict["LineCode"] = self.get_opendss_safe_name(self.model.equipment.name)

    def map_buses(self):
        super().map_buses()
        conductor_phases = getattr(self.model, "conductor_phases", None)
        if conductor_phases is not None:
            for index, bus in enumerate(self.model.buses, start=1):
                self.opendss_dict[f"Bus{index}"] = self.get_opendss_safe_name(bus.name) + "".join(
                    self.phase_map[phase] for phase in conductor_phases
                )

    def map_phases(self):
        self.opendss_dict["Phases"] = self.model.num_conductors

    def map_conductor_phases(self):
        pass

    def map_is_closed(self):
        self.opendss_dict["Switch"] = True

    def map_in_service(self):
        self.opendss_dict["Enabled"] = self.model.in_service
