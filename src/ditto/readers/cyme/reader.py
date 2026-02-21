from gdm.quantities import Distance, Current, ResistancePULength
from gdm.distribution.equipment.bare_conductor_equipment import BareConductorEquipment
from gdm.distribution.distribution_system import DistributionSystem
from ditto.readers.reader import AbstractReader
from ditto.readers.cyme.utils import read_cyme_data, network_truncation
import ditto.readers.cyme as cyme_mapper
from loguru import logger
from pydantic import ValidationError
from rich.console import Console
from infrasys import Component
from rich.table import Table
from collections import defaultdict


from gdm.distribution.components.distribution_bus import DistributionBus
from gdm.distribution.components import DistributionVoltageSource


class Reader(AbstractReader):
    # Order of components is important
    component_types = [
        "DistributionBus",  # First as other components connect to buses
        "DistributionVoltageSource",
        "MatrixImpedanceRecloserEquipment",
        "MatrixImpedanceRecloser",
        "MatrixImpedanceSwitchEquipment",
        "MatrixImpedanceSwitch",
        "MatrixImpedanceFuseEquipment",
        "MatrixImpedanceFuse",
        "DistributionCapacitor",
        "DistributionLoad",
        "BareConductorEquipment",
        "MatrixImpedanceBranchEquipment",
        "GeometryBranchEquipment",
        "GeometryBranchByPhaseEquipment",
        "GeometryBranch",
        "GeometryBranchByPhase",
        "DistributionTransformerByPhase",
        "DistributionTransformer",
        "DistributionTransformerThreeWinding",
        "MatrixImpedanceBranch",  # This must be last as it includes a catch-all for unrecognized branches
    ]

    validation_errors = []

    def __init__(
        self,
        network_file,
        equipment_file,
        load_file,
        load_model_id=None,
        substation_names=None,
        feeder_names=None,
    ):
        self.system = DistributionSystem(auto_add_composed_components=True)
        self.read(
            network_file,
            equipment_file,
            load_file,
            load_model_id,
            substation_names=substation_names,
            feeder_names=feeder_names,
        )

    def read(
        self,
        network_file,
        equipment_file,
        load_file,
        load_model_id=None,
        substation_names=None,
        feeder_names=None,
    ):
        # Section data read separately as it links to other tables
        section_id_sections = {}
        from_node_sections = {}
        to_node_sections = {}
        phase_elements = set(
            [
                "MatrixImpedanceBranchEquipmentMapper",
                "MatrixImpedanceRecloserEquipmentMapper",
                "MatrixImpedanceSwitchEquipmentMapper",
                "MatrixImpedanceFuseEquipmentMapper",
            ]
        )
        default_conductor = BareConductorEquipment(
            name="Default",
            conductor_diameter=Distance(0.368000, "inch").to("mm"),
            conductor_gmr=Distance(0.133200, "inch").to("mm"),
            ampacity=Current(600.0, "amp"),
            emergency_ampacity=Current(600.0, "amp"),
            ac_resistance=ResistancePULength(0.555000, "ohm/mile").to("ohm/km"),
            dc_resistance=ResistancePULength(0.555000, "ohm/mile").to("ohm/km"),
        )
        self.system.add_component(default_conductor)

        node_feeder_map = {}
        node_substation_map = {}
        network_voltage_map = {}
        load_record = {}
        used_sections = set()

        section_data = read_cyme_data(
            network_file,
            "SECTION",
            node_feeder_map=node_feeder_map,
            network_voltage_map=network_voltage_map,
            node_substation_map=node_substation_map,
            parse_feeders=True,
            parse_substation=True,
        )

        section_id_sections = section_data.set_index("SectionID").to_dict(orient="index")
        from_node_sections = (
            section_data.groupby("FromNodeID")
            .apply(lambda df: df.to_dict(orient="records"))
            .to_dict()
        )
        to_node_sections = (
            section_data.groupby("ToNodeID")
            .apply(lambda df: df.to_dict(orient="records"))
            .to_dict()
        )

        for component_type in self.component_types:
            logger.info(f"Parsing Type: {component_type}")
            mapper_name = component_type + "Mapper"
            if not hasattr(cyme_mapper, mapper_name):
                logger.warning(f"Mapper {mapper_name} not found. Skipping.")
                continue

            mapper = getattr(cyme_mapper, mapper_name)(self.system)

            cyme_file = mapper.cyme_file
            cyme_section = mapper.cyme_section
            all_cyme_sections = mapper.cyme_section
            if isinstance(all_cyme_sections, str):
                all_cyme_sections = [all_cyme_sections]

            for cyme_section in all_cyme_sections:
                data = self._prepare_data(
                    cyme_file, cyme_section, load_model_id, network_file, equipment_file, load_file
                )

                argument_handler = {
                    "DistributionCapacitorMapper": lambda: [
                        section_id_sections,
                        read_cyme_data(equipment_file, "SHUNT CAPACITOR", index_col="ID"),
                    ],
                    "DistributionBusMapper": lambda: [
                        from_node_sections,
                        to_node_sections,
                        node_feeder_map,
                        node_substation_map,
                    ],
                    "DistributionVoltageSourceMapper": lambda: [],
                    "DistributionLoadMapper": lambda: [
                        section_id_sections,
                        read_cyme_data(load_file, "LOADS", index_col="DeviceNumber"),
                        load_record,
                    ],
                    "GeometryBranchMapper": lambda: [used_sections, section_id_sections],
                    "GeometryBranchByPhaseMapper": lambda: [used_sections, section_id_sections],
                    "BareConductorEquipmentMapper": lambda: [],
                    "GeometryBranchEquipmentMapper": lambda: [
                        read_cyme_data(equipment_file, "SPACING TABLE FOR LINE", index_col="ID")
                    ],
                    "MatrixImpedanceSwitchEquipmentMapper": lambda: [],
                    "MatrixImpedanceSwitchMapper": lambda: [used_sections, section_id_sections],
                    "MatrixImpedanceFuseEquipmentMapper": lambda: [],
                    "MatrixImpedanceFuseMapper": lambda: [used_sections, section_id_sections],
                    "MatrixImpedanceRecloserEquipmentMapper": lambda: [],
                    "MatrixImpedanceRecloserMapper": lambda: [used_sections, section_id_sections],
                    "GeometryBranchByPhaseEquipmentMapper": lambda: [
                        read_cyme_data(equipment_file, "SPACING TABLE FOR LINE", index_col="ID")
                    ],
                    "DistributionTransformerThreeWindingMapper": lambda: [
                        used_sections,
                        section_id_sections,
                        read_cyme_data(
                            equipment_file, "THREE WINDING TRANSFORMER", index_col="ID"
                        ).to_dict("index"),
                    ],
                    "DistributionTransformerMapper": lambda: [
                        used_sections,
                        section_id_sections,
                        read_cyme_data(equipment_file, "TRANSFORMER", index_col="ID").to_dict(
                            "index"
                        ),
                    ],
                    "DistributionTransformerByPhaseMapper": lambda: [
                        used_sections,
                        section_id_sections,
                        read_cyme_data(equipment_file, "TRANSFORMER", index_col="ID").to_dict(
                            "index"
                        ),
                    ],
                    "MatrixImpedanceBranchEquipmentMapper": lambda: [],
                    "MatrixImpedanceBranchMapper": lambda: [
                        used_sections,
                        section_id_sections,
                        cyme_section,
                    ],
                }

                args = argument_handler.get(mapper_name, lambda: [])()

                def parse_row(row):
                    model_entry = mapper.parse(row, *args)
                    return model_entry

                if mapper_name in phase_elements:
                    phases = []
                    for phase in ["A", "B", "C"]:
                        phases.append(phase)
                        args = [phases]
                        components = data.apply(parse_row, axis=1)
                        components = [c for c in components if c is not None]
                        components = [
                            item
                            for c in components
                            for item in (c if isinstance(c, list) else [c])
                        ]
                        self.system.add_components(*components)
                else:
                    components = data.apply(parse_row, axis=1)
                    components = [c for c in components if c is not None]
                    components = [
                        item for c in components for item in (c if isinstance(c, list) else [c])
                    ]
                    self.system.add_components(*components)

        self.assign_bus_voltages()

        if substation_names is not None or feeder_names is not None:
            self.system = network_truncation(
                self.system, substation_names=substation_names, feeder_names=feeder_names
            )
            print("Finished truncation")

        for component_type in self.system.get_component_types():
            components = self.system.get_components(component_type)
            self._add_components(components)

        self._validate_model()

    def _add_components(self, components: list[Component]):
        """Internal method to add components to the system."""

        if components:
            for component in components:
                try:
                    component.__class__.model_validate(component.model_dump())
                except ValidationError as e:
                    for error in e.errors():
                        self.validation_errors.append(
                            [
                                component.name,
                                component.__class__.__name__,
                                error["loc"][0] if error["loc"] else "On model validation",
                                error["type"],
                                error["msg"],
                            ]
                        )

    def _validate_model(self):
        if self.validation_errors:
            error_table = Table(title="Validation warning summary")
            error_table.add_column("Model", justify="right", style="cyan", no_wrap=True)
            error_table.add_column("Type", style="green")
            error_table.add_column("Field", justify="right", style="bright_magenta")
            error_table.add_column("Error", style="bright_red")
            error_table.add_column("Message", justify="right", style="turquoise2")

            for row in self.validation_errors:
                print(row)
                error_table.add_row(*row)

            console = Console()
            console.print(error_table)
            raise Exception(
                "Validations errors occured when running the script. See the table above"
            )

    def _prepare_data(
        self, cyme_file, cyme_section, load_model_id, network_file, equipment_file, load_file
    ):
        if cyme_file == "Network":
            data = read_cyme_data(network_file, cyme_section)
        elif cyme_file == "Equipment":
            data = read_cyme_data(equipment_file, cyme_section)
        elif cyme_file == "Load":
            data = read_cyme_data(load_file, cyme_section)
            if load_model_id is not None:
                data = data[data["LoadModelID"] == load_model_id]
                logger.info(f"Filtered Load data by LoadModelID: {load_model_id}")
            else:
                if len(data["LoadModelID"].unique()) > 1:
                    raise ValueError(
                        f"Multiple LoadModelIDs found in load data: {data['LoadModelID'].unique()}. Please specify load_model_id"
                    )
        else:
            raise ValueError(f"Unknown CYME file {cyme_file}")

        return data

    def get_system(self) -> DistributionSystem:
        return self.system

    def assign_bus_voltages(self):
        observed_buses = set()
        observed_components = set()

        bus_obj_map = self._create_bus_obj_map()

        bus_queue = self._start_queue_w_voltage_sources()

        while bus_queue:
            current_bus_name = bus_queue.pop()

            current_bus = self.system.get_component(DistributionBus, name=current_bus_name)
            current_voltage = current_bus.rated_voltage
            current_voltage_type = current_bus.voltage_type
            observed_buses.add(current_bus.name)

            conn_objs = bus_obj_map[current_bus.name]
            for obj in conn_objs:
                if obj.name in observed_components:
                    continue
                observed_components.add(obj.name)
                component_type = obj.__class__.__name__

                for j, bus in enumerate(obj.buses):
                    if bus.name == current_bus.name:
                        continue

                    if component_type == "DistributionTransformer":
                        for i, winding in enumerate(obj.equipment.windings):
                            voltage = winding.rated_voltage
                            voltage_type = winding.voltage_type

                            if i == j and voltage != current_voltage:
                                bus.voltage_type = voltage_type
                                bus.rated_voltage = voltage

                    else:
                        bus.rated_voltage = current_voltage
                        bus.voltage_type = current_voltage_type

                    if bus.name not in observed_buses:
                        bus_queue.add(bus.name)

    def _start_queue_w_voltage_sources(self):
        bus_queue = set()

        voltage_sources = list(self.system.get_components(DistributionVoltageSource))

        for vsource in voltage_sources:
            vsource.bus.rated_voltage = (
                vsource.equipment.sources[0].voltage * 1.732
                if len(vsource.phases) > 1
                else vsource.equipment[0].voltage
            )
            bus_queue.add(vsource.bus.name)

        return bus_queue

    def _create_bus_obj_map(self):
        bus_obj_map = defaultdict(list)
        for component_type in self.system.get_component_types():
            component_list = list(self.system.get_components(component_type))
            for comp in component_list:
                if hasattr(comp, "buses"):
                    for bus in comp.buses:
                        bus_obj_map[bus.name].append(comp)

        return bus_obj_map
