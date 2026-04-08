from ditto.readers.synergi.synergi_mapper import SynergiMapper
from gdm.distribution.equipment.distribution_transformer_equipment import DistributionTransformerEquipment
from gdm.distribution.components.distribution_transformer import DistributionTransformer
from gdm.distribution.components.distribution_bus import DistributionBus

from gdm.distribution.enums import Phase, ConnectionType
from loguru import logger

class DistributionTransformerMapper(SynergiMapper):
    def __init__(self, system):
        super().__init__(system)
    
    synergi_table = "InstDTrans"
    synergi_database = "Model"

    def parse(self, row, unit_type, section_id_sections, from_node_sections, to_node_sections):
        name = self.map_name(row)
        buses = self.map_bus(row, section_id_sections)
        winding_phases = self.map_winding_phases(row)
        equipment = self.map_equipment(row)

        # Set the voltages for the buses
        voltage_1 = round(equipment.windings[0].rated_voltage,5)
        voltage_2 = round(equipment.windings[1].rated_voltage,5)

        buses[0].rated_voltage = voltage_1
        buses[1].rated_voltage = voltage_2

        return DistributionTransformer(name=name,
                                       buses=buses,
                                       winding_phases=winding_phases,
                                       equipment=equipment)

    def map_name(self, row):
        return row["DTranId"]    

    def map_winding_phases(self,row):
        input_phases = row["ConnPhases"].replace(" ","")
        winding_phases = []
        # Assume 2 windings
        for i in range(1,3):
            phases = []
            if 'A' in input_phases:
                phases.append(Phase.A)
            if 'B' in input_phases:  
                phases.append(Phase.B)
            if 'C' in input_phases:
                phases.append(Phase.C)
            winding_phases.append(phases)    
        return winding_phases

    def map_bus(self, row, section_id_sections):
        section_id = str(row["SectionId"])
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
            logger.warning(f"Transformer {section_id} has no from bus")
        if from_bus is None:
            logger.warning(f"Transformer {section_id} has no to bus")
        return [from_bus,to_bus]

    def map_equipment(self, row):
        equipment_name = row["TransformerType"]
        try:
            equipment = self.system.get_component(component_type=DistributionTransformerEquipment, name=equipment_name)
        except Exception as e:
            logger.warning(f"Equipment {equipment_name} not found. Skipping")
            return None
        return equipment
