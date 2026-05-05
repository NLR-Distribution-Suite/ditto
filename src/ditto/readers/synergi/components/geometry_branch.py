from ditto.readers.synergi.synergi_mapper import SynergiMapper
from ditto.readers.synergi.utils import parse_phases, phases_without_neutral
from gdm.distribution.components.geometry_branch import GeometryBranch
from gdm.distribution.equipment.geometry_branch_equipment import GeometryBranchEquipment
from gdm.distribution.components.distribution_bus import DistributionBus
from gdm.distribution.equipment.bare_conductor_equipment import BareConductorEquipment
from gdm.distribution.equipment.concentric_cable_equipment import ConcentricCableEquipment
from gdm.distribution.enums import Phase
from gdm.quantities import Distance
from loguru import logger
from ditto.readers.synergi.length_units import length_units

class GeometryBranchMapper(SynergiMapper):
    def __init__(self, system):
        super().__init__(system)

    synergi_table = "InstSection"
    synergi_database = "Model"

    def parse(self, row, unit_type, section_id_sections, from_node_sections, to_node_sections):
        name = self.map_name(row)
        buses = self.map_buses(row, section_id_sections)
        length = self.map_length(row, unit_type)
        phases = self.map_phases(row)   
        equipment = self.map_equipment(row)
        try: 
            return GeometryBranch(name=name,
                                       buses=buses,
                                       length=length,
                                       phases=phases,
                                       equipment=equipment)
        except Exception as e:
            logger.warning(f"Failed to parse geometry branch: {e}")

    def map_name(self, row):
        return row["SectionId"]

    def map_buses(self, row, section_id_sections):
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
            logger.warning(f"Line {section_id} has no from bus")
        if from_bus is None:
            logger.warning(f"Line {section_id} has no to bus")
        return [from_bus,to_bus]

    def map_length(self, row, unit_type):
        unit = length_units[unit_type]["MUL"]
        length = row["SectionLength_MUL"]
        return Distance(length, unit).to("m")

    def map_phases(self, row):
        return parse_phases(row["SectionPhases"])
 

    def map_equipment(self, row):
        input_geometry = row["ConfigurationId"]
        phases = row["SectionPhases"].replace(" ","")
        num_phases = len(phases.replace("N",""))
        delta = False
        if len(phases) == len(phases.replace("N","")):
            delta = True

        conductors = []
        for phase in phases:
            conductor = None
            if phase == "N":
                conductor = row["NeutralConductorId"]
            else:    
                # Sample model has missing conductors for PhaseConductor2Id, PhaseConductor3Id
                # Use PhaseConductorId for all non-neutral conductors
                #conductor = row[f"PhaseConductor{phase_count}Id"]
                conductor = row["PhaseConductorId"]
            conductors.append(conductor)    

        try:
            self.system.get_component(BareConductorEquipment, conductors[0])
            is_OH = True
        except:
            is_OH = False

        default_three_phase_OH_geometry = "Default_OH_3PH_" + "_".join(conductors)
        default_two_phase_OH_geometry = "Default_OH_2PH_" + "_".join(conductors)
        default_single_phase_OH_geometry = "Default_OH_1PH_" + "_".join(conductors)
        default_three_phase_UG_geometry = "Default_UG_3PH_" + "_".join(conductors)
        default_two_phase_UG_geometry = "Default_UG_2PH_" + "_".join(conductors)
        default_single_phase_UG_geometry = "Default_UG_1PH_" + "_".join(conductors)

        default_three_phase_OH_delta_geometry = "Default_OH_3PH_Delta_" + "_".join(conductors)
        default_two_phase_OH_delta_geometry = "Default_OH_2PH_Delta_" + "_".join(conductors)
        default_single_phase_OH_delta_geometry = "Default_OH_1PH_Delta_" + "_".join(conductors)
        default_three_phase_UG_delta_geometry = "Default_UG_3PH_Delta_" + "_".join(conductors)
        default_two_phase_UG_delta_geometry = "Default_UG_2PH_Delta_" + "_".join(conductors)
        default_single_phase_UG_delta_geometry = "Default_UG_1PH_Delta_" + "_".join(conductors)
        found_geometry = False
        geometry = None

        if input_geometry != "Unknown":
            name = input_geometry+"_"+"_".join(conductors) 
            try:
                geometry = self.system.get_component(component_type=GeometryBranchEquipment,name=name)
                if len(geometry.horizontal_positions) != len(phases):
                    logger.warning(f"Geometry of section {row['SectionId']} {input_geometry} does not have the correct number of horizontal positions. Using default geometry")
                    found_geometry = False
                else:
                    found_geometry = True
            except Exception as e:
                found_geometry = False

        

        if not found_geometry: 
            logger.warning(f"Geometry of section {row['SectionId']} {input_geometry} not found. Using default geometry")
            if num_phases == 3:
                if is_OH:
                    if delta:
                        geometry = self.system.get_component(component_type=GeometryBranchEquipment,name=default_three_phase_OH_delta_geometry)
                    else:
                        geometry = self.system.get_component(component_type=GeometryBranchEquipment,name=default_three_phase_OH_geometry)
                else:
                    if delta:
                        geometry = self.system.get_component(component_type=GeometryBranchEquipment,name=default_three_phase_UG_delta_geometry)
                    else:    
                        geometry = self.system.get_component(component_type=GeometryBranchEquipment,name=default_three_phase_UG_geometry)
            elif num_phases == 2:
                if is_OH:
                    if delta:
                        geometry = self.system.get_component(component_type=GeometryBranchEquipment,name=default_two_phase_OH_delta_geometry)
                    else:    
                        geometry = self.system.get_component(component_type=GeometryBranchEquipment,name=default_two_phase_OH_geometry)
                else:
                    if delta:
                        geometry = self.system.get_component(component_type=GeometryBranchEquipment,name=default_two_phase_UG_delta_geometry)
                    else:
                        geometry = self.system.get_component(component_type=GeometryBranchEquipment,name=default_two_phase_UG_geometry)

            else:
                if is_OH:
                    if delta:
                        geometry = self.system.get_component(component_type=GeometryBranchEquipment,name=default_single_phase_OH_delta_geometry)
                    else:    
                        geometry = self.system.get_component(component_type=GeometryBranchEquipment,name=default_single_phase_OH_geometry)
                else:
                    if delta:
                        geometry = self.system.get_component(component_type=GeometryBranchEquipment,name=default_single_phase_UG_delta_geometry)
                    else:
                        geometry = self.system.get_component(component_type=GeometryBranchEquipment,name=default_single_phase_UG_geometry)

        return geometry

    def map_conductors(self, row):
        conductors = []
        phases = row["SectionPhases"].replace(" ","")
        # TODO: Currently including neutral conductors even if cables. Need to check this.
        for phase in phases:
            conductor = None
            if phase == "N":
                conductor = row["NeutralConductorId"]
            else:    
                # Sample model has missing conductors for PhaseConductor2Id, PhaseConductor3Id
                # Use PhaseConductorId for all non-neutral conductors
                #conductor = row[f"PhaseConductor{phase_count}Id"]
                conductor = row["PhaseConductorId"]
            if conductor != "Unknown":
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




