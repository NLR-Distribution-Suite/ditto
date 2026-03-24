from gdm.distribution.enums import Phase

from ditto.writers.opendss.opendss_mapper import OpenDSSMapper
from ditto.enumerations import OpenDSSFileTypes

from gdm.distribution import DistributionSystem
from infrasys import Component


class DistributionBranchMapper(OpenDSSMapper):
    def __init__(self, model: Component, system: DistributionSystem):
        super().__init__(model, system)

    altdss_name = "Line_Common"
    altdss_composition_name = "Line"
    opendss_file = OpenDSSFileTypes.LINES_FILE.value

    def map_name(self):
        self.opendss_dict["Name"] = self.get_opendss_safe_name(self.model.name)

    def map_buses(self):
        self.opendss_dict["Bus1"] = self.get_opendss_safe_name(self.model.buses[0].name)
        self.opendss_dict["Bus2"] = self.get_opendss_safe_name(self.model.buses[1].name)
        for phase in self.model.phases:
            if phase != Phase.N:
                self.opendss_dict["Bus1"] += self.phase_map[phase]
                self.opendss_dict["Bus2"] += self.phase_map[phase]

    def map_length(self):
        self.opendss_dict["Length"] = self.model.length.magnitude
        model_unit = str(self.model.length.units)
        if model_unit not in self.length_units_map:
            raise ValueError(f"{model_unit} not mapped for OpenDSS")
        self.opendss_dict["Units"] = self.length_units_map[model_unit]

    def map_phases(self):
        # Redundant information - included in buses
        # TODO: remove from GDM?

        live_phases = [phase for phase in self.model.phases if phase != Phase.N]
        self.opendss_dict["Phases"] = len(live_phases)
        pass
