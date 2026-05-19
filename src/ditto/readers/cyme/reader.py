from gdm.distribution.distribution_system import DistributionSystem
from ditto.readers.reader import AbstractReader
from ditto.readers.cyme.utils import read_cyme_data, network_truncation
import ditto.readers.cyme as cyme_mapper
from loguru import logger
from pydantic import ValidationError
from rich.console import Console
from infrasys import Component
from rich.table import Table
from collections import defaultdict, deque

from gdm.distribution.components.distribution_bus import DistributionBus
from gdm.distribution.components import DistributionVoltageSource
from gdm.distribution.components.distribution_transformer import DistributionTransformer
from gdm.distribution.enums import ConnectionType, VoltageTypes
from gdm.quantities import Voltage
from ditto.constants import LL_LN_CONVERSION_FACTOR
from ditto.readers.cyme.constants import ModelUnitSystem


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
        "DistributionRegulator",
        "DistributionTransformerByPhase",
        "DistributionTransformer",
        "DistributionTransformerThreeWinding",
        "MatrixImpedanceBranch",  # This must be last as it includes a catch-all for unrecognized branches
    ]

    def __init__(
        self,
        network_file,
        equipment_file,
        load_file,
        load_model_id=None,
        substation_names=None,
        feeder_names=None,
        raise_on_validation_error=False,
    ):
        self.validation_errors = []
        self.raise_on_validation_error = raise_on_validation_error
        self.system = DistributionSystem(auto_add_composed_components=True)
        self.read(
            network_file,
            equipment_file,
            load_file,
            load_model_id,
            substation_names=substation_names,
            feeder_names=feeder_names,
        )

    def _get_unit_system(self, network_file):
        # Default to SI if unit system not specified in file
        with open(network_file, "r") as f:
            for line in f:
                if f"[{ModelUnitSystem.SI.value}]" in line:
                    return ModelUnitSystem.SI
        return ModelUnitSystem.IMPERIAL

    def _build_section_maps(self, network_file):
        node_feeder_map = {}
        node_substation_map = {}
        section_data = read_cyme_data(
            network_file,
            "SECTION",
            node_feeder_map=node_feeder_map,
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
        return (
            section_id_sections,
            from_node_sections,
            to_node_sections,
            node_feeder_map,
            node_substation_map,
        )

    def _get_mapper(self, component_type, unit_system):
        mapper_name = component_type + "Mapper"
        if not hasattr(cyme_mapper, mapper_name):
            logger.warning(f"Mapper {mapper_name} not found. Skipping.")
            return None, mapper_name
        mapper = getattr(cyme_mapper, mapper_name)(self.system, units=unit_system)
        return mapper, mapper_name

    def _get_mapper_sections(self, mapper):
        all_cyme_sections = mapper.cyme_section
        if isinstance(all_cyme_sections, str):
            all_cyme_sections = [all_cyme_sections]
        return all_cyme_sections

    def _build_argument_handler(
        self,
        section_id_sections,
        from_node_sections,
        to_node_sections,
        node_feeder_map,
        node_substation_map,
        used_sections,
        load_file,
        load_record,
        equipment_file,
        cyme_section,
    ):
        return {
            "DistributionCapacitorMapper": lambda: [section_id_sections],
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
            "GeometryBranchMapper": lambda: [used_sections, section_id_sections, cyme_section],
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
                read_cyme_data(equipment_file, "TRANSFORMER", index_col="ID").to_dict("index"),
            ],
            "DistributionTransformerByPhaseMapper": lambda: [
                used_sections,
                section_id_sections,
                read_cyme_data(equipment_file, "TRANSFORMER", index_col="ID").to_dict("index"),
            ],
            "DistributionRegulatorMapper": lambda: [
                used_sections,
                section_id_sections,
                read_cyme_data(equipment_file, "REGULATOR", index_col="ID").to_dict("index"),
            ],
            "MatrixImpedanceBranchEquipmentMapper": lambda: [],
            "MatrixImpedanceBranchMapper": lambda: [
                used_sections,
                section_id_sections,
                cyme_section,
            ],
        }

    def _flatten_components(self, components):
        filtered = [c for c in components if c is not None]
        return [item for c in filtered for item in (c if isinstance(c, list) else [c])]

    def _add_components_if_missing(self, components):
        for comp in components:
            if not self.system.has_component(comp):
                self.system.add_component(comp)

    def _parse_components_for_mapper(self, mapper, data, args):
        def parse_row(row):
            return mapper.parse(row, *args)

        return self._flatten_components(data.apply(parse_row, axis=1))

    def _parse_phase_components(self, mapper, data):
        phases = []
        all_components = []
        for phase in ["A", "B", "C"]:
            phases.append(phase)
            all_components.extend(self._parse_components_for_mapper(mapper, data, [phases]))
        return all_components

    def _post_process_network(self, substation_names, feeder_names):
        self.serialize_parallel_branches()

        self.assign_bus_voltages()

        if substation_names is not None or feeder_names is not None:
            self.system = network_truncation(
                self.system, substation_names=substation_names, feeder_names=feeder_names
            )
            print("Finished truncation")

        for component_type in self.system.get_component_types():
            components = self.system.get_components(component_type)
            for c in components:
                if not self.system.has_component(c):
                    self.system.add_component(c)

    def read(
        self,
        network_file,
        equipment_file,
        load_file,
        load_model_id=None,
        substation_names=None,
        feeder_names=None,
    ):
        phase_elements = {
            "MatrixImpedanceBranchEquipmentMapper",
            "MatrixImpedanceRecloserEquipmentMapper",
            "MatrixImpedanceSwitchEquipmentMapper",
            "MatrixImpedanceFuseEquipmentMapper",
        }

        load_record = {}
        used_sections = set()

        (
            section_id_sections,
            from_node_sections,
            to_node_sections,
            node_feeder_map,
            node_substation_map,
        ) = self._build_section_maps(network_file)

        unit_system = self._get_unit_system(network_file)

        for component_type in self.component_types:
            logger.info(f"Parsing Type: {component_type}")
            mapper, mapper_name = self._get_mapper(component_type, unit_system)
            if mapper is None:
                continue

            cyme_file = mapper.cyme_file
            all_cyme_sections = self._get_mapper_sections(mapper)

            for cyme_section in all_cyme_sections:
                data = self._prepare_data(
                    cyme_file, cyme_section, load_model_id, network_file, equipment_file, load_file
                )

                argument_handler = self._build_argument_handler(
                    section_id_sections,
                    from_node_sections,
                    to_node_sections,
                    node_feeder_map,
                    node_substation_map,
                    used_sections,
                    load_file,
                    load_record,
                    equipment_file,
                    cyme_section,
                )
                args = argument_handler.get(mapper_name, lambda: [])()
                if mapper_name in phase_elements:
                    components = self._parse_phase_components(mapper, data)
                else:
                    components = self._parse_components_for_mapper(mapper, data, args)
                self._add_components_if_missing(components)

        self._post_process_network(substation_names, feeder_names)

        self._validate_model()

    def _add_components(self, components: list[Component]):
        """Internal method to add components to the system."""

        if components:
            for component in components:
                try:
                    component.__class__.model_validate(component.model_dump())
                except ValidationError as e:
                    for error in e.errors():
                        err_info = [
                            component.name,
                            component.__class__.__name__,
                            error["loc"][0] if error["loc"] else "On model validation",
                            error["type"],
                            error["msg"],
                        ]

                        self.validation_errors.append(err_info)

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
            if self.raise_on_validation_error:
                raise Exception(
                    "Validations errors occurred when running the script. See the table above"
                )
            logger.warning(
                f"Validation warnings detected in CYME reader: {len(self.validation_errors)} issue(s). "
                "Continuing because raise_on_validation_error=False."
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
        """
        Assign bus voltages by traversing the system from voltage sources outward using BFS.
        Voltage is assigned based on the voltage source and transformer ratings.
        """

        observed_buses = set()
        observed_components = set()

        bus_obj_map = self._create_bus_obj_map()

        bus_queue = self._start_queue_w_voltage_sources()

        while bus_queue:
            current_bus_name = bus_queue.popleft()
            current_voltage, current_voltage_type = self._get_current_bus_voltage(current_bus_name)
            observed_buses.add(current_bus_name)
            conn_objs = bus_obj_map[current_bus_name]
            for obj in conn_objs:
                if self._component_already_observed(obj, observed_components):
                    continue
                self._propagate_component_voltage(
                    obj,
                    current_bus_name,
                    current_voltage,
                    current_voltage_type,
                    observed_buses,
                    bus_queue,
                )

    def _get_current_bus_voltage(self, bus_name):
        current_bus = self.system.get_component(DistributionBus, name=bus_name)
        return current_bus.rated_voltage, current_bus.voltage_type

    def _component_already_observed(self, obj, observed_components):
        component_key = (obj.__class__.__name__, obj.name)
        if component_key in observed_components:
            return True
        observed_components.add(component_key)
        return False

    def _transformer_winding_voltage(self, winding):
        voltage = winding.rated_voltage
        voltage_type = winding.voltage_type
        if (
            winding.connection_type == ConnectionType.STAR
            and winding.num_phases > 1
            and voltage_type == VoltageTypes.LINE_TO_LINE
        ):
            voltage = Voltage(
                voltage.to("kilovolt").magnitude / LL_LN_CONVERSION_FACTOR,
                "kilovolt",
            )
            voltage_type = VoltageTypes.LINE_TO_GROUND
        return voltage, voltage_type

    def _assign_transformer_bus_voltage(self, obj, bus_index, bus, current_voltage):
        for winding_index, winding in enumerate(obj.equipment.windings):
            voltage, voltage_type = self._transformer_winding_voltage(winding)
            if winding_index == bus_index and voltage != current_voltage:
                bus.voltage_type = voltage_type
                bus.rated_voltage = voltage
                logger.info(
                    f"Assigned voltage {voltage} and type {voltage_type} to bus {bus.name} based on transformer {obj.name} winding {winding_index}"
                )
                return

    def _propagate_component_voltage(
        self,
        obj,
        current_bus_name,
        current_voltage,
        current_voltage_type,
        observed_buses,
        bus_queue,
    ):
        is_transformer = obj.__class__.__name__ == "DistributionTransformer"
        for bus_index, bus in enumerate(obj.buses):
            if bus.name == current_bus_name:
                continue
            if is_transformer:
                self._assign_transformer_bus_voltage(obj, bus_index, bus, current_voltage)
            else:
                bus.rated_voltage = current_voltage
                bus.voltage_type = current_voltage_type

            if bus.name not in observed_buses:
                bus_queue.append(bus.name)

    def _start_queue_w_voltage_sources(self):
        bus_queue = deque()

        voltage_sources = list(self.system.get_components(DistributionVoltageSource))

        for vsource in voltage_sources:
            # Source equipment stores per-phase voltage as L-N.
            # Bus rated_voltage is propagated in L-N form and converted in writers when needed.
            vsource.bus.rated_voltage = vsource.equipment.sources[0].voltage
            vsource.bus.voltage_type = VoltageTypes.LINE_TO_GROUND
            bus_queue.append(vsource.bus.name)

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

    def serialize_parallel_branches(self):
        """
        Detect parallel branches and serialize them by inserting new buses and copying components as needed.
        All non-transformer parallel branches are chained in series. Only transformers may remain in parallel.
        After serialization, validates that no non-transformer parallel edges remain and that parallel
        transformers do not overlap on phases.
        """

        parallel_components = self._get_parallel_components()

        for i, comps in enumerate(parallel_components):
            transformers, non_transformers = self._sort_parallel_components(comps)
            if transformers:
                self._serialize_parallel_with_transformers(i, transformers, non_transformers)
            else:
                self._serialize_parallel_without_transformers(i, non_transformers)

    def _clone_with_new_name(self, obj, new_name):
        values = {}
        for field in type(obj).model_fields:
            cur_val = getattr(obj, field)
            if field == "name":
                val = new_name
            elif field in ("uuid",):
                continue
            else:
                val = cur_val
            values[field] = val
        return type(obj).model_construct(**values)

    def _create_parallel_bus(self, base_bus, index, edge_index):
        new_bus = self._clone_with_new_name(base_bus, f"{base_bus.name}_{index}_{edge_index}")
        self.system.add_component(new_bus)
        return new_bus

    def _serialize_parallel_with_transformers(self, edge_index, transformers, non_transformers):
        xfmr_primary_base = transformers[0].buses[0]
        xfmr_primary = self._clone_with_new_name(
            xfmr_primary_base, f"{xfmr_primary_base.name}_primary"
        )
        self.system.add_component(xfmr_primary)
        xfmr_secondary = transformers[0].buses[1]

        for j, comp in enumerate(non_transformers):
            if j == 0:
                if len(non_transformers) > 1:
                    new_bus = self._create_parallel_bus(
                        non_transformers[j + 1].buses[1], j, edge_index
                    )
                    comp.buses[0] = new_bus
                comp.buses[1] = xfmr_primary
            elif j < len(non_transformers) - 1:
                comp.buses[1] = non_transformers[j - 1].buses[0]
                new_bus = self._create_parallel_bus(
                    non_transformers[j + 1].buses[1], j, edge_index
                )
                comp.buses[0] = new_bus
            else:
                comp.buses[1] = non_transformers[j - 1].buses[0]

        for comp in transformers:
            comp.buses[0] = xfmr_primary
            comp.buses[1] = xfmr_secondary

    def _serialize_parallel_without_transformers(self, edge_index, non_transformers):
        for j, comp in enumerate(non_transformers[:-1]):
            new_bus = self._create_parallel_bus(comp.buses[1], j, edge_index)
            comp.buses[1] = new_bus
            non_transformers[j + 1].buses[0] = new_bus

    def _get_parallel_edges(self):
        G = self.system.get_undirected_graph()
        edges = defaultdict(list)
        for u, v, key in G.edges(keys=True):
            edge_pair = tuple(sorted((u, v)))
            edges[edge_pair].append(key)
        return G, {edge: keys for edge, keys in edges.items() if len(keys) > 1}

    def _get_parallel_components(self) -> list[list[Component]]:
        G, parallel_edges = self._get_parallel_edges()

        parallel_edges = {
            edge: keys
            for edge, keys in parallel_edges.items()
            if not all(
                G.get_edge_data(edge[0], edge[1], key)["type"] == DistributionTransformer
                for key in keys
            )
        }

        parallel_components = list()
        for edge in parallel_edges:
            comps = list()
            for key in parallel_edges[edge]:
                edge_data = G.get_edge_data(edge[0], edge[1], parallel_edges[edge][key])
                comps.append(self.system.get_component(edge_data["type"], edge_data["name"]))
            parallel_components.append(comps)

        return parallel_components

    def _sort_parallel_components(
        self, comps: list[Component]
    ) -> tuple[list[DistributionTransformer], list[Component]]:
        name_counts = defaultdict(int)
        for comp in comps:
            name_counts[comp.name] += 1

        seen_names = defaultdict(int)
        renamed_components = []
        for comp in comps:
            if name_counts[comp.name] > 1:
                new_name = f"{comp.name}_{seen_names[comp.name]}"
                # Use model_construct to avoid validation before assign_bus_voltages()
                # At this point buses have placeholder voltages, so pydantic validation would fail
                values = {}
                for field in type(comp).model_fields:
                    cur_val = getattr(comp, field)
                    if field == "name":
                        val = new_name
                    elif field in ("uuid",):
                        continue
                    else:
                        val = cur_val
                    values[field] = val
                new_comp = type(comp).model_construct(**values)
                self.system.add_component(new_comp)
                self.system.remove_component(comp)
                renamed_components.append(new_comp)
                seen_names[comp.name] += 1
            else:
                renamed_components.append(comp)

        transformers = [c for c in renamed_components if isinstance(c, DistributionTransformer)]
        non_transformers = [
            c for c in renamed_components if not isinstance(c, DistributionTransformer)
        ]

        return transformers, non_transformers
