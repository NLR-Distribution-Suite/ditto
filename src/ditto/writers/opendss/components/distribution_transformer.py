from gdm.distribution import DistributionSystem
from infrasys import Component


from ditto.writers.opendss.opendss_mapper import OpenDSSMapper
from ditto.enumerations import OpenDSSFileTypes


class DistributionTransformerMapper(OpenDSSMapper):
    def __init__(self, model: Component, system: DistributionSystem):
        super().__init__(model, system)

    altdss_name = "Transformer_XfmrCode"
    altdss_composition_name = "Transformer"
    opendss_file = OpenDSSFileTypes.TRANSFORMERS_FILE.value

    def map_in_service(self):
        self.opendss_dict["enabled"] = self.model.in_service

    def map_name(self):
        self.opendss_dict["Name"] = self.get_opendss_safe_name(self.model.name)

    def map_buses(self):
        buses = []
        phases = []
        buses_and_phases = []
        is_center_tapped = self.model.equipment.is_center_tapped
        if is_center_tapped:
            for i in range(len(self.model.buses)):
                bus = self.model.buses[i]
                buses.append(self.get_opendss_safe_name(bus.name))
            dss_phases = ""
            for phase in self.model.winding_phases[0]:
                dss_phases += self.phase_map[phase]
            phases.append(dss_phases)
            phases.append(".1.0")
            phases.append(".0.2")

        else:
            for bus in self.model.buses:
                buses.append(self.get_opendss_safe_name(bus.name))
            for winding_phases in self.model.winding_phases:
                dss_phases = ""
                for phase in winding_phases:
                    dss_phases += self.phase_map[phase]
                phases.append(dss_phases)

        for i in range(len(buses)):
            buses_and_phases.append(buses[i] + phases[i])
        self.opendss_dict["Bus"] = buses_and_phases

    def map_winding_phases(self):
        primary_winding = self.model.winding_phases[0]
        self.opendss_dict["Phases"] = len(primary_winding)

    def map_equipment(self):
        equipment = self.model.equipment
        self.opendss_dict["XfmrCode"] = self.get_opendss_safe_name(equipment.name)
