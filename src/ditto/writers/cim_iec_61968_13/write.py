from __future__ import annotations

import re
from uuid import NAMESPACE_URL, uuid5
from collections import defaultdict
from pathlib import Path
import xml.etree.ElementTree as ET

from ditto.writers.abstract_writer import AbstractWriter
from ditto.writers.cim_iec_61968_13.equipment_emitters.source import emit_energy_source
from ditto.writers.cim_iec_61968_13.equipment_emitters.load import emit_energy_consumer
from ditto.writers.cim_iec_61968_13.equipment_emitters.line import emit_line_segment
from ditto.writers.cim_iec_61968_13.equipment_emitters.capacitor import emit_capacitor
from ditto.writers.cim_iec_61968_13.equipment_emitters.switch import emit_switch
from ditto.writers.cim_iec_61968_13.equipment_emitters.solar import emit_solar
from ditto.writers.cim_iec_61968_13.equipment_emitters.fuse import emit_fuse
from ditto.writers.cim_iec_61968_13.equipment_emitters.battery import emit_battery
from ditto.writers.cim_iec_61968_13.equipment_emitters.transformer import (
    emit_distribution_transformer,
    emit_regulator,
)


RDF_NS = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
CIM_NS = "http://iec.ch/TC57/CIM100#"

ET.register_namespace("rdf", RDF_NS)
ET.register_namespace("cim", CIM_NS)


class Writer(AbstractWriter):
    _SUPPORTED_COMPONENT_TYPES = {
        "DistributionBus",
        "DistributionVoltageSource",
        "DistributionLoad",
        "MatrixImpedanceBranch",
        "DistributionTransformer",
        "DistributionRegulator",
        "DistributionCapacitor",
        "MatrixImpedanceSwitch",
        "DistributionSolar",
        "DistributionBattery",
        "MatrixImpedanceFuse",
    }

    def _rdf(self, suffix: str) -> str:
        return f"{{{RDF_NS}}}{suffix}"

    def _cim(self, suffix: str) -> str:
        return f"{{{CIM_NS}}}{suffix}"

    def _deterministic_id(self, kind: str, name: str) -> str:
        return str(uuid5(NAMESPACE_URL, f"ditto-cim:{kind}:{name}"))

    def _safe_text(self, value) -> str:
        if value is None:
            return ""
        if hasattr(value, "value"):
            return str(value.value)
        return str(value)

    def _add_literal(self, element: ET.Element, prop: str, value) -> None:
        child = ET.SubElement(element, self._cim(prop))
        child.text = self._safe_text(value)

    def _add_ref(self, element: ET.Element, prop: str, ref_id: str) -> None:
        ET.SubElement(
            element,
            self._cim(prop),
            attrib={self._rdf("resource"): f"#{ref_id}"},
        )

    def _build_root(self) -> ET.Element:
        return ET.Element(self._rdf("RDF"))

    def _create_identified_object(self, root: ET.Element, class_name: str, obj_id: str, name: str):
        element = ET.SubElement(
            root, self._cim(class_name), attrib={self._rdf("about"): f"#{obj_id}"}
        )
        self._add_literal(element, "IdentifiedObject.name", name)
        self._add_literal(element, "IdentifiedObject.mRID", obj_id)
        return element

    def _quantity(self, value, unit: str | None = None) -> float:
        if value is None:
            return 0.0
        if hasattr(value, "to") and unit is not None:
            return float(value.to(unit).magnitude)
        if hasattr(value, "magnitude"):
            return float(value.magnitude)
        return float(value)

    def _bus_nominal_voltage(self, bus) -> float:
        return self._quantity(bus.rated_voltage, "volt") * 1.732

    def _phase_text(self, phase) -> str:
        text = self._safe_text(phase)
        return text.replace("Phase.", "")

    def _connection_kind(self, winding) -> str:
        connection = self._safe_text(getattr(winding, "connection_type", "STAR"))
        return "D" if "DELTA" in connection else "Y"

    def _line_to_line_winding_voltage(self, winding) -> float:
        phase_voltage = self._quantity(getattr(winding, "rated_voltage", 0.0), "volt")
        num_phases = int(getattr(winding, "num_phases", 1) or 1)
        return phase_voltage * 1.732 if num_phases > 1 else phase_voltage

    def _winding_resistance_ohm(self, winding) -> float:
        rated_power = self._quantity(getattr(winding, "rated_power", 0.0), "VA")
        rated_voltage = self._line_to_line_winding_voltage(winding)
        if rated_power <= 0.0:
            return 0.0
        return (
            float(getattr(winding, "resistance", 0.0)) / 100.0 * (rated_voltage**2 / rated_power)
        )

    def _winding_reactance_ohm(self, winding, per_x: float | None) -> float:
        rated_power = self._quantity(getattr(winding, "rated_power", 0.0), "VA")
        rated_voltage = self._line_to_line_winding_voltage(winding)
        if rated_power <= 0.0 or per_x is None:
            return 0.0
        return float(per_x) / 100.0 * (rated_voltage**2 / rated_power)

    def _winding_phases_text(self, winding_phases: list) -> str:
        return "".join(self._phase_text(phase) for phase in winding_phases)

    def _tap_step_values(self, winding) -> tuple[float, int, int, int, int, int]:
        total_taps = int(getattr(winding, "total_taps", 32) or 32)
        max_tap_pu = float(getattr(winding, "max_tap_pu", 1.1) or 1.1)
        min_tap_pu = float(getattr(winding, "min_tap_pu", 0.9) or 0.9)
        tap_position = float(getattr(winding, "tap_positions", [1.0])[0] or 1.0)

        dv_pu = (max_tap_pu - min_tap_pu) / total_taps if total_taps > 0 else 0.00625
        if dv_pu <= 0:
            dv_pu = 0.00625
        dv_percent = dv_pu * 100.0

        high_step = int(round((max_tap_pu - 1.0) / dv_pu))
        low_step = int(round((min_tap_pu - 1.0) / dv_pu))
        normal_step = int(round((tap_position - 1.0) / dv_pu))
        neutral_step = 0
        current_step = normal_step
        return dv_percent, high_step, low_step, neutral_step, normal_step, current_step

    def _camel_to_snake(self, name: str) -> str:
        return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()

    def _component_type_key(self, component) -> str | None:
        component_type = component.__class__.__name__
        if component_type in self._SUPPORTED_COMPONENT_TYPES:
            return component_type
        return None

    def _combine_with_required_buses(self, components: list, buses: list) -> list:
        bus_names = {bus.name for bus in buses}
        merged = []
        seen = set()

        for bus in buses:
            key = (bus.__class__.__name__, bus.name)
            seen.add(key)
            merged.append(bus)

        for component in components:
            key = (component.__class__.__name__, getattr(component, "name", str(id(component))))
            if key in seen:
                continue
            seen.add(key)

            if component.__class__.__name__ == "DistributionBus":
                merged.append(component)
                continue

            if hasattr(component, "bus") and getattr(component, "bus", None) is not None:
                if component.bus.name in bus_names:
                    merged.append(component)
                continue

            if hasattr(component, "buses") and getattr(component, "buses", None):
                buses_list = [bus.name for bus in component.buses]
                if all(name in bus_names for name in buses_list):
                    merged.append(component)
                continue

            merged.append(component)

        return merged

    def _create_base_voltage(
        self, root: ET.Element, nominal_voltage: float, cache: dict[str, str]
    ) -> str:
        key = f"{nominal_voltage:.6f}"
        if key in cache:
            return cache[key]

        base_voltage_id = self._deterministic_id("base_voltage", key)
        base_voltage = self._create_identified_object(
            root,
            "BaseVoltage",
            base_voltage_id,
            f"BaseVoltage_{int(round(nominal_voltage))}",
        )
        self._add_literal(base_voltage, "BaseVoltage.nominalVoltage", nominal_voltage)
        cache[key] = base_voltage_id
        return base_voltage_id

    def _create_bus_objects(
        self,
        root: ET.Element,
        buses: list,
        bus_node_ids: dict[str, str],
        bus_location_ids: dict[str, str],
    ) -> None:
        for bus in buses:
            bus_name = bus.name
            node_id = self._deterministic_id("connectivity_node", bus_name)
            bus_node_ids[bus_name] = node_id
            self._create_identified_object(root, "ConnectivityNode", node_id, bus_name)

            location_id = self._deterministic_id("location", bus_name)
            bus_location_ids[bus_name] = location_id
            location = self._create_identified_object(
                root, "Location", location_id, f"Location_{bus_name}"
            )

            position_id = self._deterministic_id("position_point", bus_name)
            position = self._create_identified_object(
                root,
                "PositionPoint",
                position_id,
                f"Position_{bus_name}",
            )
            coordinate = getattr(bus, "coordinate", None)
            x = getattr(coordinate, "x", 0.0)
            y = getattr(coordinate, "y", 0.0)
            self._add_literal(position, "PositionPoint.xPosition", x)
            self._add_literal(position, "PositionPoint.yPosition", y)
            self._add_ref(position, "PositionPoint.Location", location_id)
            self._add_literal(location, "IdentifiedObject.mRID", location_id)

    def _create_terminal(
        self,
        root: ET.Element,
        equipment_id: str,
        node_id: str,
        suffix: str,
        with_limits: bool = False,
        ampacity: float = 0.0,
    ) -> str:
        terminal_id = self._deterministic_id("terminal", f"{equipment_id}:{suffix}")
        terminal = self._create_identified_object(
            root, "Terminal", terminal_id, f"Terminal_{suffix}"
        )
        self._add_ref(terminal, "Terminal.ConductingEquipment", equipment_id)
        self._add_ref(terminal, "Terminal.ConnectivityNode", node_id)

        if with_limits:
            limit_set_id = self._deterministic_id("operational_limit_set", terminal_id)
            limit_set = self._create_identified_object(
                root,
                "OperationalLimitSet",
                limit_set_id,
                f"LimitSet_{suffix}",
            )
            self._add_ref(limit_set, "OperationalLimitSet.Terminal", terminal_id)
            self._add_ref(terminal, "ACDCTerminal.OperationalLimitSet", limit_set_id)

            normal_limit_id = self._deterministic_id("current_limit", f"{terminal_id}:normal")
            normal_limit = self._create_identified_object(
                root,
                "CurrentLimit",
                normal_limit_id,
                f"CurrentLimitNormal_{suffix}",
            )
            self._add_ref(normal_limit, "OperationalLimit.OperationalLimitSet", limit_set_id)
            self._add_literal(normal_limit, "CurrentLimit.value", max(ampacity, 0.0))

            emergency_limit_id = self._deterministic_id(
                "current_limit", f"{terminal_id}:emergency"
            )
            emergency_limit = self._create_identified_object(
                root,
                "CurrentLimit",
                emergency_limit_id,
                f"CurrentLimitEmergency_{suffix}",
            )
            self._add_ref(emergency_limit, "OperationalLimit.OperationalLimitSet", limit_set_id)
            self._add_literal(emergency_limit, "CurrentLimit.value", max(ampacity * 1.2, ampacity))

        return terminal_id

    @staticmethod
    def _safe_group_name(value: str) -> str:
        cleaned = "".join(char if char.isalnum() or char in "-_" else "_" for char in value)
        return cleaned.strip("_") or "unknown"

    def _get_component_group(self, component) -> tuple[str, str]:
        substation_name = "default_substation"
        feeder_name = "default_feeder"

        substation = getattr(component, "substation", None)
        feeder = getattr(component, "feeder", None)

        if substation is not None:
            substation_name = getattr(substation, "name", str(substation))
        if feeder is not None:
            feeder_name = getattr(feeder, "name", str(feeder))

        return self._safe_group_name(substation_name), self._safe_group_name(feeder_name)

    @staticmethod
    def _write_xml(root: ET.Element, output_file: Path) -> None:
        tree = ET.ElementTree(root)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        tree.write(output_file, encoding="utf-8", xml_declaration=True)

    def _populate_core_graph(self, root: ET.Element, components: list) -> None:
        buses = [
            component
            for component in components
            if component.__class__.__name__ == "DistributionBus"
        ]
        sources = [
            component
            for component in components
            if component.__class__.__name__ == "DistributionVoltageSource"
        ]
        loads = [
            component
            for component in components
            if component.__class__.__name__ == "DistributionLoad"
        ]
        branches = [
            component
            for component in components
            if component.__class__.__name__ == "MatrixImpedanceBranch"
        ]
        transformers = [
            component
            for component in components
            if component.__class__.__name__ == "DistributionTransformer"
        ]
        regulators = [
            component
            for component in components
            if component.__class__.__name__ == "DistributionRegulator"
        ]
        capacitors = [
            component
            for component in components
            if component.__class__.__name__ == "DistributionCapacitor"
        ]
        switches = [
            component
            for component in components
            if component.__class__.__name__ == "MatrixImpedanceSwitch"
        ]
        solars = [
            component
            for component in components
            if component.__class__.__name__ == "DistributionSolar"
        ]
        batteries = [
            component
            for component in components
            if component.__class__.__name__ == "DistributionBattery"
        ]
        fuses = [
            component
            for component in components
            if component.__class__.__name__ == "MatrixImpedanceFuse"
        ]

        bus_node_ids: dict[str, str] = {}
        bus_location_ids: dict[str, str] = {}
        base_voltage_cache: dict[str, str] = {}
        emitted_line_code_ids: set[str] = set()

        self._create_bus_objects(root, buses, bus_node_ids, bus_location_ids)

        for source in sources:
            if source.bus.name in bus_node_ids:
                emit_energy_source(
                    self, root, source, bus_node_ids, bus_location_ids, base_voltage_cache
                )

        for load in loads:
            if load.bus.name in bus_node_ids:
                emit_energy_consumer(
                    self, root, load, bus_node_ids, bus_location_ids, base_voltage_cache
                )

        for branch in branches:
            if branch.buses[0].name in bus_node_ids and branch.buses[1].name in bus_node_ids:
                emit_line_segment(
                    self,
                    root,
                    branch,
                    bus_node_ids,
                    bus_location_ids,
                    base_voltage_cache,
                    emitted_line_code_ids,
                )

        for transformer in transformers:
            if (
                len(transformer.buses) >= 2
                and transformer.buses[0].name in bus_node_ids
                and transformer.buses[1].name in bus_node_ids
            ):
                emit_distribution_transformer(
                    self,
                    root,
                    transformer,
                    bus_node_ids,
                    bus_location_ids,
                    base_voltage_cache,
                )

        for regulator in regulators:
            if (
                len(regulator.buses) >= 2
                and regulator.buses[0].name in bus_node_ids
                and regulator.buses[1].name in bus_node_ids
            ):
                emit_regulator(
                    self, root, regulator, bus_node_ids, bus_location_ids, base_voltage_cache
                )

        for capacitor in capacitors:
            emit_capacitor(
                self, root, capacitor, bus_node_ids, bus_location_ids, base_voltage_cache
            )

        for switch in switches:
            emit_switch(self, root, switch, bus_node_ids, bus_location_ids, base_voltage_cache)

        for solar in solars:
            emit_solar(self, root, solar, bus_node_ids, bus_location_ids, base_voltage_cache)

        for battery in batteries:
            emit_battery(self, root, battery, bus_node_ids, bus_location_ids, base_voltage_cache)

        for fuse in fuses:
            emit_fuse(self, root, fuse, bus_node_ids, bus_location_ids, base_voltage_cache)

    def write(
        self,
        output_path: Path = Path("./"),
        output_mode: str = "single",
        separate_substations: bool = True,
        separate_feeders: bool = True,
        separate_equipment_types: bool = True,
    ) -> None:
        output_path = Path(output_path)
        output_path.mkdir(parents=True, exist_ok=True)

        component_types = sorted(
            self.system.get_component_types(), key=lambda component: component.__name__
        )

        if output_mode == "single":
            root = self._build_root()
            components = []
            for component_type in component_types:
                components.extend(self.system.get_components(component_type))

            self._populate_core_graph(root, components)

            self._write_xml(root, output_path / "model.xml")
            return

        if output_mode != "package":
            raise ValueError("output_mode must be either 'single' or 'package'")

        groups: dict[tuple[str, str], list] = defaultdict(list)
        for component_type in component_types:
            for component in self.system.get_components(component_type):
                substation_name, feeder_name = self._get_component_group(component)
                group_key = (
                    substation_name if separate_substations else "all_substations",
                    feeder_name if separate_feeders else "all_feeders",
                )
                groups[group_key].append(component)

        manifest = ET.Element(
            "PackageManifest",
            attrib={
                "xmlns:cim": "http://iec.ch/TC57/CIM100#",
            },
        )
        for (substation_name, feeder_name), components in groups.items():
            folder = output_path / substation_name / feeder_name

            if not separate_equipment_types:
                file_name = f"{substation_name}__{feeder_name}.xml"
                root = self._build_root()
                self._populate_core_graph(root, components)
                self._write_xml(root, folder / file_name)
                ET.SubElement(
                    manifest,
                    "cim:File",
                    attrib={
                        "substation": substation_name,
                        "feeder": feeder_name,
                        "type": "all",
                        "path": str(Path(substation_name) / feeder_name / file_name),
                    },
                )
                continue

            buses = [
                component
                for component in components
                if component.__class__.__name__ == "DistributionBus"
            ]
            component_buckets: dict[str, list] = defaultdict(list)
            for component in components:
                component_key = self._component_type_key(component)
                if component_key is None:
                    continue
                component_buckets[component_key].append(component)

            for component_key, bucket_components in component_buckets.items():
                file_components = self._combine_with_required_buses(bucket_components, buses)
                file_suffix = self._camel_to_snake(component_key)
                file_name = f"{substation_name}__{feeder_name}__{file_suffix}.xml"
                root = self._build_root()
                self._populate_core_graph(root, file_components)
                self._write_xml(root, folder / file_name)

                ET.SubElement(
                    manifest,
                    "cim:File",
                    attrib={
                        "substation": substation_name,
                        "feeder": feeder_name,
                        "type": component_key,
                        "path": str(Path(substation_name) / feeder_name / file_name),
                    },
                )

        self._write_xml(manifest, output_path / "manifest.xml")
