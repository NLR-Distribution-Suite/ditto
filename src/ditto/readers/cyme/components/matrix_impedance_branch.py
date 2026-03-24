
from gdm.quantities import Distance, Current, ResistancePULength, ReactancePULength, CapacitancePULength
from ditto.readers.cyme.cyme_mapper import CymeMapper
from gdm.distribution.equipment.matrix_impedance_branch_equipment import MatrixImpedanceBranchEquipment
from gdm.distribution.components.matrix_impedance_branch import MatrixImpedanceBranch
from gdm.distribution.components.distribution_bus import DistributionBus
from gdm.distribution.enums import Phase




class MatrixImpedanceBranchMapper(CymeMapper):
    def __init__(self, system):
        super().__init__(system)

    cyme_file = 'Network'
    cyme_section = ['UNDERGROUNDLINE SETTING', 'SECTION']

    def parse(self, row, used_sections, section_id_sections, cyme_section):
        name = self.map_name(row)
        if cyme_section == 'SECTION' and name in used_sections:
            return None
        buses = self.map_buses(row,section_id_sections)
        length = self.map_length(row, cyme_section)
        phases = self.map_phases(row, section_id_sections)
        equipment = self.map_equipment(row, phases, cyme_section)
        used_sections.add(name)
        try:
            return MatrixImpedanceBranch(name=name,
                                buses=buses,
                                length=length,
                                phases=phases,
                                equipment=equipment)
        except Exception as e:
            print(f"Error creating MatrixImpedanceBranch {name}: {e}")
            print(buses)
            return None

    def map_name(self, row):
        name = row['SectionID']
        return name
    def map_buses(self, row, section_id_sections):
        section_id = str(row['SectionID'])
        section = section_id_sections[section_id]
        from_bus_name = section['FromNodeID']
        to_bus_name = section['ToNodeID']
        
        from_bus = self.system.get_component(component_type=DistributionBus, name=from_bus_name)
        to_bus = self.system.get_component(component_type=DistributionBus, name=to_bus_name)
        return [from_bus, to_bus]

    def map_length(self, row, cyme_section):
        if cyme_section == 'UNDERGROUNDLINE SETTING':
            length = Distance(float(row['Length']),'foot').to('km')
        else:
             length = Distance(0.001,'kilometer')

        return length

    def map_phases(self, row, section_id_sections):
        section_id = str(row['SectionID'])
        section = section_id_sections[section_id]
        phase = section['Phase']
        phases = []
        if 'A' in phase:
            phases.append(Phase.A)
        if 'B' in phase:
            phases.append(Phase.B)
        if 'C' in phase:
            phases.append(Phase.C)
        return phases

    def map_equipment(self, row, phases, cyme_section):
        if cyme_section == 'UNDERGROUNDLINE SETTING':
            line_id = row['LineCableID']
            equipment_name = f"{line_id}_{len(phases)}"
            line = self.system.get_component(component_type=MatrixImpedanceBranchEquipment, name=equipment_name)
        elif cyme_section == 'SECTION':
            r = [
                [1e-6, 0.0, 0.0],
                [0.0, 1e-6, 0.0],
                [0.0, 0.0, 1e-6],
                ]
            r_matrix = ResistancePULength(
                [row[:len(phases)] for row in r[:len(phases)]],
                "ohm/mi",
            )
            x = [
                [1e-4, 0.0, 0.0],
                [0.0, 1e-4, 0.0],
                [0.0, 0.0, 1e-4],
                ]
            x_matrix = ReactancePULength(
                [row[:len(phases)] for row in x[:len(phases)]],
                "ohm/mi",
            )
            c = [
                [0.0, 0.0, 0.0],
                [0.0, 0.0, 0.0],
                [0.0, 0.0, 0.0],
                ]
            c_matrix = CapacitancePULength(
                [row[:len(phases)] for row in c[:len(phases)]],
                "nanofarad/mi",
            )
            ampacity = Current(600.0, "A")
            line = MatrixImpedanceBranchEquipment.model_construct(name=row['SectionID'],
                                                r_matrix=r_matrix,
                                                x_matrix=x_matrix,
                                                c_matrix=c_matrix,
                                                ampacity=ampacity
                                                )
        return line