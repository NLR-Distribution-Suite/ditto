from ditto.readers.cyme.utils import read_cyme_data
from ditto.readers.cyme.cyme_mapper import CymeMapper
from ditto.readers.cyme.equipment.capacitor_equipment import CapacitorEquipmentMapper
from gdm.distribution.components.distribution_bus import DistributionBus
from gdm.distribution.components.distribution_capacitor import DistributionCapacitor
from gdm.distribution.enums import Phase
from loguru import logger

class DistributionCapacitorMapper(CymeMapper):
    def __init__(self, system):
        super().__init__(system)

    cyme_file = 'Network'
    cyme_section = 'SHUNT CAPACITOR SETTING'

    def parse(self, row, section_id_sections, equipment_data):
        name = self.map_name(row)
        bus = self.map_bus(row, section_id_sections)
        phases = self.map_phases(row, section_id_sections)
        controllers = self.map_controllers(row)
        equipment = self.map_equipment(row, equipment_data)
        in_service = self.map_in_service(row)
        return DistributionCapacitor.model_construct(name=name,
                                      bus=bus,
                                      phases=phases,
                                      controllers=controllers,
                                      equipment=equipment,
                                      in_service=in_service)

    def map_name(self, row):
        return row["DeviceNumber"]

    def map_phases(self, row, section_id_sections):
        phases = []
        section_id = row['SectionID']
        section = section_id_sections[section_id]
        section_phases = section['Phase']
        if 'FixedKVARA' in row and row["FixedKVARA"] or 'A' in section_phases:
            phases.append(Phase.A)
        if 'FixedKVARB' in row and row["FixedKVARB"] or 'B' in section_phases:
            phases.append(Phase.B)
        if 'FixedKVARC' in row and row["FixedKVARC"] or 'C' in section_phases:
            phases.append(Phase.C)
        if phases == []:
            raise ValueError(f"Could not determine phases for capacitor {row['DeviceNumber']} on section {section_id} with section phases {section_phases}")
        return phases

    def map_bus(self, row, section_id_sections):
        section_id = row["SectionID"]
        section = section_id_sections[section_id]
        from_bus_name = section["FromNodeID"]
        to_bus_name = section["ToNodeID"]
        to_bus = None
        from_bus = None
        try:
            from_bus = self.system.get_component(component_type=DistributionBus,name=from_bus_name)
        except Exception as e:    
            pass

        try:
            to_bus = self.system.get_component(component_type=DistributionBus,name=to_bus_name)
        except Exception as e:
            pass

        if from_bus is None:
            return to_bus
        if from_bus is None:
            logger.warning(f"Load {section_id} has no bus")
        return from_bus


    def map_controllers(self, row):
        return []

    def map_equipment(self, row, equipment_data):
        mapper = CapacitorEquipmentMapper(self.system)
        capacitor_id = row['ShuntCapacitorID']
        if capacitor_id not in equipment_data.index:
            capacitor_id = 'DEFAULT'
        equipment_row = equipment_data.loc[capacitor_id]
        if not equipment_row.empty:
            equipment = mapper.parse(equipment_row, connection=row['Connection'])
            return equipment
        return None
    
    def map_in_service(self, row):
        return True if int(row['ConnectionStatus']) == 0 else False
