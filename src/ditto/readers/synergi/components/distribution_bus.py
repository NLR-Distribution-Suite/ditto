from infrasys.location import Location
from gdm.distribution.components.distribution_bus import DistributionBus
from gdm.distribution.enums import VoltageTypes, Phase
from gdm.quantities import Voltage
from ditto.readers.synergi.synergi_mapper import SynergiMapper

class DistributionBusMapper(SynergiMapper):
    def __init__(self, system):

        super().__init__(system)

    synergi_table = "Node"
    synergi_database = "Model"

    def parse(self, row, unit_type, section_id_sections, from_node_sections, to_node_sections):
        name = self.map_name(row)
        coordinate = self.map_coordinate(row)
        rated_voltage = self.map_nominal_voltage(row)
        phases = self.map_phases(row, from_node_sections, to_node_sections)
        voltage_limits = self.map_voltagelimits(row)
        voltage_type = self.map_voltage_type(row)
        return DistributionBus(name=name,
                               coordinate=coordinate,
                               rated_voltage=rated_voltage,
                               phases=phases,
                               voltagelimits=voltage_limits,
                               voltage_type=voltage_type)

    def map_name(self, row):
        name = row["NodeId"]
        return name

    def map_coordinate(self, row):
        X, Y = row["X"], row["Y"]
        #crs = SAI_Control.ProjectionWKT
        crs = None
        location = Location(x = X, y = Y, crs = crs)
        return location

    # Nominal voltage is only defined by transformers
    def map_nominal_voltage(self, row):
        return Voltage(12.47, "kilovolts")

    def map_phases(self, row, from_node_sections, to_node_sections):
        node_id = row["NodeId"]
        section = None
        all_phases = set()
        if node_id in from_node_sections: 
            for section in from_node_sections[node_id]:
                phases = section["SectionPhases"].replace(" ","")
                for phase in phases:
                    all_phases.add(phase)
        if node_id in to_node_sections:    
            for section in to_node_sections[node_id]:
                phases = section["SectionPhases"].replace(" ","")
                for phase in phases:
                    all_phases.add(phase)

        all_phases = sorted(list(all_phases))
        phases = []
        if "A" in all_phases:
            phases.append(Phase.A)
        if "B" in all_phases:
            phases.append(Phase.B)
        if "C" in all_phases:
            phases.append(Phase.C)
        if "N" in all_phases:
            phases.append(Phase.N)
            
        return phases

    def map_voltagelimits(self, row):
        return []

    def map_voltage_type(self, row):
        return VoltageTypes.LINE_TO_LINE.value

