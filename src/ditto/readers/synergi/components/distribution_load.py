from ditto.readers.synergi.synergi_mapper import SynergiMapper
from ditto.readers.synergi.equipment.load_equipment import LoadEquipmentMapper
from gdm.distribution.components.distribution_bus import DistributionBus
from gdm.distribution.components.distribution_load import DistributionLoad
from gdm.distribution.enums import Phase
from loguru import logger

class DistributionLoadMapper(SynergiMapper):
    def __init__(self, system):
        super().__init__(system)

    synergi_table = "Loads"    
    synergi_database = "Model"


    def parse(self, row, unit_type, section_id_sections, from_node_sections, to_node_sections):
        name = self.map_name(row)
        bus = self.map_bus(row, section_id_sections)
        phases = self.map_phases(row)
        equipment = self.map_equipment(row)
        if len(phases) == 0:
            logger.warning(f"Load {name} has no kW values. Skipping...")
            return None
        return DistributionLoad(name=name,
                                bus=bus,
                                phases=phases,
                                equipment=equipment)
        

    def map_name(self, row):
        return row["SectionId"]

    def map_bus(self, row, section_id_sections):
        section_id = row["SectionId"]
        section = section_id_sections[section_id]
        from_bus_name = section["FromNodeId"]
        to_bus_name = section["ToNodeId"]
        to_bus = None
        from_bus = None
        try:
            from_bus = self.system.get_component(component_type=DistributionBus,name=from_bus_name)
        except Exception as e:    
            pass

        try:
            to_bus = self.system.get_component(component_type=DistributionBus,name=to_bus_name)
        except:
            pass

        if from_bus is None:
            return to_bus
        if from_bus is None:
            logger.warning(f"Load {section_id} has no bus")
        return from_bus

    def map_phases(self, row):
        nonzero_phases = []
        for phase in range(1,4):
            kw_column = f"Phase{phase}Kw"
            if row[kw_column] > 0:
                nonzero_phases.append(phase)
        phases = []
        for phase in nonzero_phases:
            if phase == 1:
                phases.append(Phase.A)
            if phase == 2:
                phases.append(Phase.B)
            if phase == 3:
                phases.append(Phase.C)
        return phases

    def map_equipment(self, row):
        mapper = LoadEquipmentMapper(self.system)
        equipment = mapper.parse(row)
        return equipment

