from gdm.distribution.components.base.distribution_component_base import DistributionComponentBase
from gdm.distribution.equipment.geometry_branch_equipment import GeometryBranchEquipment
from gdm.distribution.equipment.bare_conductor_equipment import BareConductorEquipment
from gdm.distribution.equipment.concentric_cable_equipment import ConcentricCableEquipment
from gdm.distribution import DistributionSystem
from gdm.quantities import Distance
from ditto.readers.reader import AbstractReader
from ditto.readers.synergi.utils import read_synergi_data, download_mdbtools
import ditto.readers.synergi as synergi_mapper
from loguru import logger

class Reader(AbstractReader):

    # Order matters here
    component_types = [
            "DistributionBus",
            "DistributionCapacitor",
            "DistributionLoad",
#            "DistributionTransformerEquipment",
#            "DistributionTransformer",
            "ConductorEquipment",
            "GeometryBranchEquipment",
            "GeometryBranch",
    ]

    def __init__(self, model_file, equipment_file):
        download_mdbtools()
        self.system = DistributionSystem(auto_add_composed_components=True)
        self.read(model_file, equipment_file)

    def create_geometry_defaults(self, model_file):

        # TODO: Add delta-configured lines as well
        all_conductors = set()
        section_data = read_synergi_data(model_file,"InstSection")
        for idx, row in section_data.iterrows():
            conductor_n = row["NeutralConductorId"]
            conductor = row["PhaseConductorId"]
            all_conductors.add((conductor,conductor_n))
        default_geometries = []
        for conductor,conductor_n in all_conductors:
            wire = None
            cable = None
            wire_n = None
            cable_n = None
            try:
                wire = self.system.get_component(component_type=BareConductorEquipment,name=conductor)
            except:
                pass
            try:
                wire_n = self.system.get_component(component_type=BareConductorEquipment,name=conductor_n)
            except:
                pass
            try:
                cable = self.system.get_component(component_type=ConcentricCableEquipment,name=conductor)
            except:
                pass
            try:
                cable_n = self.system.get_component(component_type=ConcentricCableEquipment,name=conductor_n)
            except:
                pass
            if wire is not None and wire_n is not None:
                conductors = [wire, wire, wire, wire_n]
                conductor_names = [wire.name, wire.name, wire.name, wire_n.name]
                default_geometries.append(GeometryBranchEquipment(
                        name="Default_OH_3PH_"+"_".join(conductor_names),
                        conductors = conductors,
                        horizontal_positions = Distance([0,0.5,1.0, 1.5],"m"),
                        vertical_positions = Distance([6,6,6,6],"m")))

                conductors = [wire, wire, wire]
                conductor_names = [wire.name, wire.name, wire.name]
                default_geometries.append(GeometryBranchEquipment(
                        name="Default_OH_3PH_Delta_"+"_".join(conductor_names),
                        conductors = conductors,
                        horizontal_positions = Distance([0,0.5,1.0],"m"),
                        vertical_positions = Distance([6,6,6],"m")))

                conductors = [wire, wire, wire_n]
                conductor_names = [wire.name, wire.name, wire_n.name]
                default_geometries.append(GeometryBranchEquipment(
                        name="Default_OH_2PH_"+"_".join(conductor_names),
                        conductors = conductors,
                        horizontal_positions = Distance([0,0.5,1.0],"m"),
                        vertical_positions = Distance([6,6,6],"m")))

                conductors = [wire, wire]
                conductor_names = [wire.name, wire.name]
                default_geometries.append(GeometryBranchEquipment(
                        name="Default_OH_2PH_Delta_"+"_".join(conductor_names),
                        conductors = conductors,
                        horizontal_positions = Distance([0,0.5],"m"),
                        vertical_positions = Distance([6,6],"m")))
 
                conductors = [wire, wire_n]
                conductor_names = [wire.name, wire_n.name]
                default_geometries.append(GeometryBranchEquipment(
                        name="Default_OH_1PH_"+ "_".join(conductor_names),
                        conductors = conductors,
                        horizontal_positions = Distance([0,0.5],"m"),
                        vertical_positions = Distance([6,6],"m")))

                conductors = [wire]
                conductor_names = [wire.name]
                default_geometries.append(GeometryBranchEquipment(
                        name="Default_OH_1PH_Delta_"+ "_".join(conductor_names),
                        conductors = conductors,
                        horizontal_positions = Distance([0],"m"),
                        vertical_positions = Distance([6],"m"))) 
            if cable is not None and cable_n is not None:    
                conductors = [cable, cable, cable, cable_n]
                conductor_names = [cable.name, cable.name, cable.name, cable_n.name]
                default_geometries.append(GeometryBranchEquipment(
                        name="Default_UG_3PH_"+"_".join(conductor_names),
                        conductors = conductors,
                        horizontal_positions = Distance([0,0.5,1.0, 1.5],"m"),
                        vertical_positions = Distance([-1,-1,-1,-1],"m")))

                conductors = [cable, cable, cable]
                conductor_names = [cable.name, cable.name, cable.name]
                default_geometries.append(GeometryBranchEquipment(
                        name="Default_UG_3PH_Delta_"+"_".join(conductor_names),
                        conductors = conductors,
                        horizontal_positions = Distance([0,0.5,1.0],"m"),
                        vertical_positions = Distance([-1,-1,-1],"m")))

                conductors = [cable, cable, cable_n]
                conductor_names = [cable.name, cable.name, cable_n.name]
                default_geometries.append(GeometryBranchEquipment(
                        name="Default_UG_2PH_"+"_".join(conductor_names),
                        conductors = conductors,
                        horizontal_positions = Distance([0,0.5,1.0],"m"),
                        vertical_positions = Distance([-1,-1,-1],"m")))

                conductors = [cable, cable]
                conductor_names = [cable.name, cable.name]
                default_geometries.append(GeometryBranchEquipment(
                        name="Default_UG_2PH_Delta_"+"_".join(conductor_names),
                        conductors = conductors,
                        horizontal_positions = Distance([0,0.5],"m"),
                        vertical_positions = Distance([-1,-1],"m")))

                conductors = [cable, cable_n]
                conductor_names = [cable.name, cable_n.name]
                default_geometries.append(GeometryBranchEquipment(
                        name="Default_UG_1PH_"+ "_".join(conductor_names),
                        conductors = conductors,
                        horizontal_positions = Distance([0,0.5],"m"),
                        vertical_positions = Distance([-1,-1],"m")))

                conductors = [cable]
                conductor_names = [cable.name]
                default_geometries.append(GeometryBranchEquipment(
                        name="Default_UG_1PH_Delta_"+ "_".join(conductor_names),
                        conductors = conductors,
                        horizontal_positions = Distance([0],"m"),
                        vertical_positions = Distance([-1],"m")))


        self.system.add_components(*default_geometries)

    def read(self, model_file, equipment_file):

        # Read the measurement unit
        unit_type = read_synergi_data(model_file,"SAI_Control").iloc[0]["LengthUnits"]

        # Section data read separately as it links to other tables
        section_id_sections = {}
        from_node_sections = {}
        to_node_sections = {}
        geometry_conductors = {}
        section_data = read_synergi_data(model_file,"InstSection")
        for idx, row in section_data.iterrows():
            section_id = row["SectionId"]
            section_id_sections[section_id] = row

            from_node = row["FromNodeId"]
            to_node = row["ToNodeId"]
            if not from_node in from_node_sections:
                from_node_sections[from_node] = []
            from_node_sections[from_node].append(row)    
            if not to_node in to_node_sections:
                to_node_sections[to_node] = []
            to_node_sections[to_node].append(row)    

            geometry = row["ConfigurationId"]
            phases = row["SectionPhases"].replace(' ',"")
            conductor_names = []
            for phase in phases:
                conductor = None
                if phase == "N":
                    conductor = row["NeutralConductorId"]
                else:    
                    # Sample model has missing conductors for PhaseConductor2Id, PhaseConductor3Id
                    # Use PhaseConductorId for all non-neutral conductors
                    conductor = row["PhaseConductorId"]
                conductor_names.append(conductor)    
            if geometry not in geometry_conductors:
                geometry_conductors[geometry] = set()
            geometry_conductors[geometry].add(tuple(conductor_names))    



        # TODO: Base this off of the components in the init file
        for component_type in self.component_types:
            if component_type == "GeometryBranchEquipment":
                self.create_geometry_defaults(model_file)

            mapper_name = component_type+ "Mapper"
            if not hasattr(synergi_mapper, mapper_name):
                logger.warning(f"Mapper for {mapper_name} not found. Skipping")
                continue
            mapper = getattr(synergi_mapper, mapper_name)(self.system)
            table_name = mapper.synergi_table
            database = mapper.synergi_database

            table_data = None
            if database == "Model":
                table_data = read_synergi_data(model_file,table_name)
            elif database == "Equipment":
                table_data = read_synergi_data(equipment_file,table_name)
            else:
                raise ValueError("Invalid database type")

            components = []
            for idx,row in table_data.iterrows():
                mapper_name = component_type+ "Mapper"
                if component_type == "GeometryBranchEquipment":
                    try:
                        model_entries = mapper.parse(row, unit_type, section_id_sections, from_node_sections, to_node_sections, geometry_conductors)
                        for model_entry in model_entries:
                            components.append(model_entry)
                    except Exception as e:
                        logger.warning(f"Failed to parse GeometryBranchEquipment row {idx}: {e}")
                else:
                    try:
                        model_entry = mapper.parse(row, unit_type, section_id_sections, from_node_sections, to_node_sections)
                        if model_entry is not None:
                            components.append(model_entry)
                    except Exception as e:
                        logger.warning(f"Failed to parse {component_type} row {idx}: {e}")
            self.system.add_components(*components)

    def get_system(self) -> DistributionSystem:
        return self.system  
