from gdm.distribution import DistributionSystem
from ditto.readers.reader import AbstractReader
from ditto.readers.synergi.utils import read_synergi_data, download_mdbtools, build_node_feeder_map
import ditto.readers.synergi as synergi_mapper
from loguru import logger

class Reader(AbstractReader):

    # Order matters — feeders/substations first, equipment before components that reference them
    component_types = [
            "DistributionFeeder",
            "DistributionSubstation",
            "DistributionBus",
            "DistributionCapacitor",
            "DistributionLoad",
            "ConductorEquipment",
            "GeometryBranchEquipment",
            "MatrixImpedanceBranchEquipment",
            "DistributionTransformerEquipment",
            "DistributionTransformer",
            "Switch",
            "Breaker",
            "Fuse",
            "Recloser",
            "LineSection",
    ]

    def __init__(self, model_file, equipment_file):
        download_mdbtools()
        self.system = DistributionSystem(auto_add_composed_components=True)
        self.read(model_file, equipment_file)

    def read(self, model_file, equipment_file):

        # Read the measurement unit
        unit_type = read_synergi_data(model_file, "SAI_Control").iloc[0]["LengthUnits"]

        # Build section lookup dicts and geometry conductor map
        section_id_sections = {}
        from_node_sections = {}
        to_node_sections = {}
        geometry_conductors = {}
        section_data = read_synergi_data(model_file, "InstSection")
        for idx, row in section_data.iterrows():
            section_id = row["SectionId"]
            section_id_sections[section_id] = row

            from_node = row["FromNodeId"]
            to_node = row["ToNodeId"]
            if from_node not in from_node_sections:
                from_node_sections[from_node] = []
            from_node_sections[from_node].append(row)
            if to_node not in to_node_sections:
                to_node_sections[to_node] = []
            to_node_sections[to_node].append(row)

            geometry = row["ConfigurationId"]
            phases = row["SectionPhases"].replace(' ', "")
            conductor_names = []
            for phase in phases:
                conductor = row["NeutralConductorId"] if phase == "N" else row["PhaseConductorId"]
                conductor_names.append(conductor)
            if geometry not in geometry_conductors:
                geometry_conductors[geometry] = set()
            geometry_conductors[geometry].add(tuple(conductor_names))

        # Collect section IDs that have devices so LineSectionMapper can skip them
        devices_on_section = set()
        for device_table in ["InstSwitches", "InstBreakers", "InstFuses", "InstReclosers", "InstDTrans"]:
            try:
                dev_data = read_synergi_data(model_file, device_table)
                for _, drow in dev_data.iterrows():
                    sid = str(drow.get("SectionId", "")).strip()
                    if sid:
                        devices_on_section.add(sid)
            except Exception:
                pass

        # Build node→feeder lookup for voltage and context (used by DistributionBusMapper)
        feeder_data = read_synergi_data(model_file, "InstFeeders")
        node_feeder_map = build_node_feeder_map(feeder_data, section_data)

        for component_type in self.component_types:
            mapper_name = component_type + "Mapper"
            if not hasattr(synergi_mapper, mapper_name):
                logger.warning(f"Mapper for {mapper_name} not found. Skipping")
                continue
            mapper = getattr(synergi_mapper, mapper_name)(self.system, node_feeder_map=node_feeder_map)
            table_name = mapper.synergi_table
            database = mapper.synergi_database

            if database == "Model":
                table_data = read_synergi_data(model_file, table_name)
            elif database == "Equipment":
                table_data = read_synergi_data(equipment_file, table_name)
            else:
                raise ValueError("Invalid database type")

            # DistributionSubstation needs all rows at once to group by SubstationId
            if component_type == "DistributionSubstation":
                components = mapper.parse_all(table_data, unit_type, section_id_sections, from_node_sections, to_node_sections)
                self.system.add_components(*components)
                continue

            components = []
            for idx, row in table_data.iterrows():
                try:
                    if component_type == "GeometryBranchEquipment":
                        result = mapper.parse(row, unit_type, section_id_sections, from_node_sections, to_node_sections, geometry_conductors)
                    elif component_type == "LineSection":
                        result = mapper.parse(row, unit_type, section_id_sections, from_node_sections, to_node_sections, devices_on_section)
                    else:
                        result = mapper.parse(row, unit_type, section_id_sections, from_node_sections, to_node_sections)

                    if result is None:
                        continue
                    if isinstance(result, list):
                        components.extend(result)
                    else:
                        components.append(result)
                except Exception as e:
                    logger.warning(f"Failed to parse {component_type} row {idx}: {e}")
            self.system.add_components(*components)

    def get_system(self) -> DistributionSystem:
        return self.system
