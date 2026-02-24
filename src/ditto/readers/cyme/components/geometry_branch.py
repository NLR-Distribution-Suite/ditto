from gdm.quantities import Distance
from ditto.readers.cyme.cyme_mapper import CymeMapper
from ditto.readers.cyme.equipment.geometry_branch_equipment import GeometryBranchEquipment
from gdm.distribution.components.geometry_branch import GeometryBranch
from gdm.distribution.components.distribution_bus import DistributionBus
from gdm.distribution.enums import Phase


class GeometryBranchMapper(CymeMapper):
    def __init__(self, system):
        super().__init__(system)

    cyme_file = "Network"
    cyme_section = ["OVERHEADLINE SETTING", "OVERHEAD BYPHASE SETTING"]

    def parse(self, row, used_sections, section_id_sections, cyme_section):
        name = self.map_name(row)
        buses = self.map_buses(row, section_id_sections)
        length = self.map_length(row)
        equipment = self.map_equipment(row, cyme_section)
        phases = self.map_phases(row, section_id_sections, equipment, buses)

        used_sections.add(name)
        return GeometryBranch.model_construct(
            name=name, buses=buses, length=length, phases=phases, equipment=equipment
        )

    def map_name(self, row):
        name = row["SectionID"]
        return name

    def map_buses(self, row, section_id_sections):
        section_id = str(row["SectionID"])
        section = section_id_sections[section_id]
        from_bus_name = section["FromNodeID"]
        to_bus_name = section["ToNodeID"]

        from_bus = self.system.get_component(component_type=DistributionBus, name=from_bus_name)
        to_bus = self.system.get_component(component_type=DistributionBus, name=to_bus_name)
        return [from_bus, to_bus]

    def map_length(self, row):
        length = Distance(float(row["Length"]), "foot").to("km")
        if length <= 0:
            length = Distance(0.001, "km")
        return length

    def map_phases(self, row, section_id_sections, equipment, buses):
        section_id = str(row["SectionID"])
        section = section_id_sections[section_id]
        phase = section["Phase"]
        phases = []
        if "A" in phase:
            phases.append(Phase.A)
        if "B" in phase:
            phases.append(Phase.B)
        if "C" in phase:
            phases.append(Phase.C)

        if len(phases) == len(equipment.conductors):
            return phases
        elif len(phase) == len(equipment.conductors) - 1:
            phases.append(Phase.N)
            for bus in buses:
                if bus.phases is not None and Phase.N not in bus.phases:
                    bus.phases.append(Phase.N)
            return phases
        else:
            return phases

    def map_equipment(self, row, cyme_section):
        line_id = (
            row["LineCableID"] if cyme_section == "OVERHEADLINE SETTING" else row["DeviceNumber"]
        )

        line = self.system.get_component(component_type=GeometryBranchEquipment, name=line_id)
        return line
