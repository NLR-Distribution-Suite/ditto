from ditto.readers.synergi.synergi_mapper import SynergiMapper
from ditto.readers.synergi.equipment.capacitor_equipment import CapacitorEquipmentMapper
from gdm.distribution.components.distribution_bus import DistributionBus
from gdm.distribution.components.distribution_capacitor import DistributionCapacitor
from gdm.distribution.enums import Phase
from loguru import logger

class DistributionCapacitorMapper(SynergiMapper):
    def __init__(self, system):
        super().__init__(system)

    synergi_table = "InstCapacitors"
    synergi_database = "Model"

    def parse(self, row, unit_type, section_id_sections, from_node_sections, to_node_sections):
        name = self.map_name(row)
        bus = self.map_bus(row, section_id_sections)
        phases = self.map_phases(row)
        controllers = self.map_controllers(row)
        equipment = self.map_equipment(row)
        return DistributionCapacitor(name=name,
                                      bus=bus,
                                      phases=phases,
                                      controllers=controllers,
                                      equipment=equipment)

    def map_name(self, row):
        return str(row["UniqueDeviceId"])

    def map_phases(self, row):
        phase_info = row["ConnectedPhases"]
        phases = []
        for phase in phase_info:
            if phase == "A":
                phases.append(Phase.A)
            if phase == "B":
                phases.append(Phase.B)
            if phase == "C":
                phases.append(Phase.C)
        return phases

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


    def map_controllers(self, row):
        return []

    def map_equipment(self, row):
        mapper = CapacitorEquipmentMapper(self.system)
        equipment = mapper.parse(row)
        return equipment
