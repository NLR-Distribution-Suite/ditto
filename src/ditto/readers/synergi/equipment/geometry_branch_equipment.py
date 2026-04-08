from ditto.readers.synergi.synergi_mapper import SynergiMapper
from gdm.distribution.equipment.geometry_branch_equipment import GeometryBranchEquipment
from gdm.distribution.equipment.bare_conductor_equipment import BareConductorEquipment
from gdm.distribution.equipment.concentric_cable_equipment import ConcentricCableEquipment
from gdm.quantities import Distance
from ditto.readers.synergi.length_units import length_units
from loguru import logger

class GeometryBranchEquipmentMapper(SynergiMapper):
    def __init__(self, system):
        super().__init__(system)

    synergi_table = "DevConfig"
    synergi_database = "Equipment"

    def parse(self, row, unit_type, section_id_sections, from_node_sections, to_node_sections, geometry_conductors):
        name = self.map_name(row)
        horizontal_positions = self.map_horizontal_positions(row, unit_type)
        vertical_positions = self.map_vertical_positions(row, unit_type)
        all_geometries = []
        # Ignore geometries which are not used
        if name in geometry_conductors:
            for conductor_list in geometry_conductors[name]:
                num_conductors = len(conductor_list)
                name_with_conductors = name+"_"+"_".join(conductor_list)
                conductors = self.map_conductors(conductor_list)
                geometry = GeometryBranchEquipment(name=name_with_conductors,
                                conductors = conductors,        
                                horizontal_positions=horizontal_positions[0:num_conductors],
                                vertical_positions=vertical_positions[0:num_conductors])
                all_geometries.append(geometry)
        return all_geometries    

    def map_name(self, row):    
        return row["ConfigName"]

    def map_conductors(self, conducor_list):
        conductors = []
        for conductor in conducor_list:
            bare_equipment = None
            concentric_equipment = None
            try:
                bare_equipment = self.system.get_component(component_type=BareConductorEquipment,name=conductor)
            except Exception as e:
                pass
            try:
                concentric_equipment = self.system.get_component(component_type=ConcentricCableEquipment,name=conductor)
            except Exception as e:
                pass
            if bare_equipment is not None:
                conductors.append(bare_equipment)
            elif concentric_equipment is not None:    
                conductors.append(concentric_equipment)
            else:
                logger.warning(f"Conductor {conductor} not found. Skipping")

        return conductors


    def map_horizontal_positions(self, row, unit_type):
        unit = length_units[unit_type]["MUL"]
        x1 = row["Position1_X_MUL"]
        x2 = row["Position2_X_MUL"]
        x3 = row["Position3_X_MUL"]
        xn = row["Neutral_X_MUL"]
        return Distance([x1, x2, x3, xn], unit).to("m")

    def map_vertical_positions(self, row, unit_type):
        unit = length_units[unit_type]["MUL"]
        y1 = row["Position1_Y_MUL"]
        y2 = row["Position2_Y_MUL"]
        y3 = row["Position3_Y_MUL"]
        yn = row["Neutral_Y_MUL"]
        return Distance([y1, y2, y3, yn], unit).to("m")
