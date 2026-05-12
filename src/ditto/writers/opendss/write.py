from collections import defaultdict
from copy import deepcopy
from io import TextIOWrapper
from pathlib import Path
import re
from typing import Any

from infrasys import NonSequentialTimeSeries, SingleTimeSeries
from altdss_schema import altdss_models
from gdm.distribution.components import (
    DistributionVoltageSource,
    DistributionComponentBase,
    DistributionTransformer,
    DistributionBranchBase,
    MatrixImpedanceSwitch,
    DistributionBus,
)
from gdm.distribution.equipment import (
    ConcentricCableEquipment,
    BareConductorEquipment,
)
from loguru import logger

from ditto.writers.abstract_writer import AbstractWriter
from ditto.enumerations import OpenDSSFileTypes
import ditto.writers.opendss as opendss_mapper
from ditto.constants import LL_LN_CONVERSION_FACTOR
from ditto.writers.opendss.opendss_mapper import OpenDSSMapper


class Writer(AbstractWriter):
    @staticmethod
    def _normalize_dss_string(dss_string: str) -> str:
        """Normalize enum-style unit tokens emitted by altdss_schema.

        OpenDSS expects plain unit strings (for example, ``m``), but some
        schema objects currently emit enum-qualified values (for example,
        ``LengthUnit.m``). Strip the enum prefix in the final DSS text.
        """

        return re.sub(r"\bLengthUnit\.([A-Za-z_][A-Za-z0-9_]*)\b", r"\1", dss_string)

    def _get_dss_string(self, model_map: Any) -> str:
        # Example model_map is instance of DistributionBusMapper
        altdss_class = getattr(altdss_models, model_map.altdss_name)
        # Example altdss_class is Bus
        altdss_object = altdss_class.model_validate(model_map.opendss_dict)
        if model_map.altdss_composition_name is not None:
            altdss_composition_class = getattr(altdss_models, model_map.altdss_composition_name)

            altdss_composition_object = altdss_composition_class(altdss_object)
            dss_string = altdss_composition_object.dumps_dss()
        else:
            dss_string = altdss_object.dumps_dss()
        return self._normalize_dss_string(dss_string)

    def _clone_mapper_like(self, model_map: Any, opendss_dict: dict[str, Any]) -> Any:
        clone = type("MapperClone", (), {})()
        clone.altdss_name = model_map.altdss_name
        clone.altdss_composition_name = model_map.altdss_composition_name
        clone.opendss_file = model_map.opendss_file
        clone.substation = getattr(model_map, "substation", "")
        clone.feeder = getattr(model_map, "feeder", "")
        clone.opendss_dict = opendss_dict
        return clone

    def _get_bus_phase_tokens(self, bus_entry: str) -> list[str]:
        parts = bus_entry.split(".")
        if len(parts) <= 1:
            return []
        return [token for token in parts[1:] if token]

    def _bus_for_single_phase(self, bus_entry: str, phase_token: str) -> str:
        parts = bus_entry.split(".")
        if len(parts) <= 1:
            return f"{bus_entry}.{phase_token}"

        base = parts[0]
        existing_tokens = [token for token in parts[1:] if token]
        grounded = [token for token in existing_tokens if token == "0"]
        phase_and_ground = [phase_token, *grounded]
        return base + "".join(f".{token}" for token in phase_and_ground)

    def _expand_two_phase_transformer_outputs(
        self, model: Any, model_map: Any, equipment_map: Any | None
    ) -> tuple[list[Any], list[Any], dict[str, str]]:
        if model_map.altdss_composition_name != "Transformer":
            return [model_map], [equipment_map] if equipment_map is not None else [], {}

        phases = model_map.opendss_dict.get("Phases")
        buses = model_map.opendss_dict.get("Bus", [])
        if phases != 2 or not buses:
            return [model_map], [equipment_map] if equipment_map is not None else [], {}

        phase_tokens = self._get_bus_phase_tokens(buses[0])
        phase_tokens = [token for token in phase_tokens if token != "0"]
        if len(phase_tokens) != 2:
            return [model_map], [equipment_map] if equipment_map is not None else [], {}

        original_name = model_map.opendss_dict.get("Name", "Transformer")
        original_xfmr_code = model_map.opendss_dict.get("XfmrCode")

        expanded_model_maps = []
        expanded_equipment_maps = []
        phase_to_transformer_name = {}

        for phase_token in phase_tokens:
            model_dict = deepcopy(model_map.opendss_dict)
            model_dict["Name"] = f"{original_name}_{phase_token}"
            model_dict["Phases"] = 1
            model_dict["Bus"] = [
                self._bus_for_single_phase(bus_entry, phase_token) for bus_entry in buses
            ]
            if original_xfmr_code:
                model_dict["XfmrCode"] = f"{original_xfmr_code}_{phase_token}"
            phase_to_transformer_name[phase_token] = model_dict["Name"]
            expanded_model_maps.append(self._clone_mapper_like(model_map, model_dict))

            if equipment_map is not None:
                equipment_dict = deepcopy(equipment_map.opendss_dict)
                equipment_name = equipment_dict.get("Name", original_xfmr_code)
                if equipment_name:
                    equipment_dict["Name"] = f"{equipment_name}_{phase_token}"
                equipment_dict["Phases"] = 1
                # Two-phase OpenDSS entries are split to single-phase. Convert
                # non-delta winding kVs from LL to LN to keep voltage semantics.
                if "kV" in equipment_dict and "Conn" in equipment_dict:
                    converted_kvs = []
                    for kv, conn in zip(equipment_dict["kV"], equipment_dict["Conn"]):
                        if str(conn).lower() == "delta":
                            converted_kvs.append(kv)
                        else:
                            converted_kvs.append(kv / LL_LN_CONVERSION_FACTOR)
                    equipment_dict["kV"] = converted_kvs
                expanded_equipment_maps.append(
                    self._clone_mapper_like(equipment_map, equipment_dict)
                )

        return expanded_model_maps, expanded_equipment_maps, phase_to_transformer_name

    def prepare_folder(self, output_path):
        directory = Path(output_path)
        files_to_remove = directory.rglob("*.dss")
        for dss_file in files_to_remove:
            logger.debug(f"Deleting existing file {dss_file}")
            dss_file.unlink()

    def _get_voltage_bases(self) -> list[float]:
        voltage_bases = []
        buses: list[DistributionBus] = list(self.system.get_components(DistributionBus))
        for bus in buses:
            voltage_bases.append(
                bus.rated_voltage.to("kilovolt").magnitude
                if bus.voltage_type == "line-to-line"
                else bus.rated_voltage.to("kilovolt").magnitude * LL_LN_CONVERSION_FACTOR
            )
        return list(set(voltage_bases))

    def write(  # noqa
        self,
        output_path: Path = Path("./"),
        separate_substations: bool = True,
        separate_feeders: bool = True,
        profile_type: type[NonSequentialTimeSeries | SingleTimeSeries] = SingleTimeSeries,
    ):
        self.profile_type = profile_type
        base_redirect = set()
        feeders_redirect = defaultdict(set)
        substations_redirect = defaultdict(set)

        self.prepare_folder(output_path)
        component_types = self.system.get_component_types()

        seen_equipment = set()
        seen_controller = set()
        seen_profile = set()

        output_folder = output_path
        output_redirect = Path("")
        self._write_profiles(output_path, seen_profile, output_redirect, base_redirect)
        for component_type in component_types:
            # Example component_type is DistributionBus
            components = self.system.get_components(component_type)

            mapper_name = component_type.__name__ + "Mapper"
            # Example mapper_name is string DistributionBusMapper
            if not hasattr(opendss_mapper, mapper_name):
                logger.warning(f"Mapper {mapper_name} not found. Skipping")
                continue

            logger.debug(f"Mapping components in {mapper_name}...")
            mapper = getattr(opendss_mapper, mapper_name)

            # Example mapper is class DistributionBusMapper
            for model in components:
                # Example model is instance of DistributionBus
                if not isinstance(model, DistributionComponentBase) and not (
                    isinstance(model, BareConductorEquipment)
                    or isinstance(model, ConcentricCableEquipment)
                ):
                    continue

                model_map = mapper(model, self.system)
                model_map.populate_opendss_dictionary()

                # Skip components with empty mappings (e.g., unused intermediate buses)
                if not model_map.opendss_dict:
                    continue

                equipment_map = None
                controller_outputs = []

                if hasattr(model, "equipment"):
                    equipment_mapper_name = model.equipment.__class__.__name__ + "Mapper"
                    if not hasattr(opendss_mapper, equipment_mapper_name):
                        logger.warning(
                            f"Equipment Mapper {equipment_mapper_name} not found. Skipping"
                        )
                    else:
                        equipment_mapper = getattr(opendss_mapper, equipment_mapper_name)
                        equipment_map = equipment_mapper(model.equipment, self.system)
                        equipment_map.populate_opendss_dictionary()

                (
                    model_maps_to_write,
                    equipment_maps_to_write,
                    phase_to_transformer_name,
                ) = self._expand_two_phase_transformer_outputs(model, model_map, equipment_map)

                if hasattr(model, "controllers"):
                    for controller in model.controllers:
                        controller_mapper_name = controller.__class__.__name__ + "Mapper"
                        if not hasattr(opendss_mapper, controller_mapper_name):
                            logger.warning(
                                f"Controller Mapper {controller_mapper_name} not found. Skipping"
                            )
                        else:
                            controller_mapper = getattr(opendss_mapper, controller_mapper_name)
                            controller_xfmr_name = model.name
                            if phase_to_transformer_name:
                                controlled_phase = getattr(
                                    controller.controlled_phase,
                                    "value",
                                    str(controller.controlled_phase),
                                )
                                controller_phase = OpenDSSMapper.phase_map.get(
                                    controlled_phase, ""
                                ).lstrip(".")
                                if controller_phase in phase_to_transformer_name:
                                    controller_xfmr_name = phase_to_transformer_name[
                                        controller_phase
                                    ]
                                else:
                                    controller_xfmr_name = next(
                                        iter(phase_to_transformer_name.values())
                                    )

                            controller_map = controller_mapper(
                                controller, controller_xfmr_name, self.system
                            )
                            controller_map.populate_opendss_dictionary()
                            controller_dss_string = self._get_dss_string(controller_map)
                            controller_outputs.append((controller_map, controller_dss_string))

                output_folder = output_path
                output_folder, output_redirect = self._build_directory_structure(
                    separate_substations,
                    separate_feeders,
                    output_path,
                    model_map,
                    output_redirect,
                    output_folder,
                )

                for equipment_map_to_write in equipment_maps_to_write:
                    equipment_dss_string = self._get_dss_string(equipment_map_to_write)
                    feeder_substation_equipment = (
                        model_map.substation + model_map.feeder + equipment_dss_string
                    )
                    if feeder_substation_equipment not in seen_equipment:
                        seen_equipment.add(feeder_substation_equipment)
                        with open(
                            output_folder / equipment_map_to_write.opendss_file,
                            "a",
                            encoding="utf-8",
                        ) as fp:
                            fp.write(equipment_dss_string)

                for controller_map, controller_dss_string in controller_outputs:
                    feeder_substation_controller = (
                        model_map.substation + model_map.feeder + controller_dss_string
                    )
                    if feeder_substation_controller not in seen_controller:
                        seen_controller.add(feeder_substation_controller)
                        with open(
                            output_folder / controller_map.opendss_file, "a", encoding="utf-8"
                        ) as fp:
                            fp.write(controller_dss_string)

                for model_map_to_write in model_maps_to_write:
                    dss_string = self._get_dss_string(model_map_to_write)
                    if dss_string.startswith("new Vsource"):
                        dss_string = dss_string.replace("new Vsource", "Clear\n\nNew Circuit")

                    # TODO: Check that there aren't multiple voltage sources for the same master file
                    with open(
                        output_folder / model_map_to_write.opendss_file, "a", encoding="utf-8"
                    ) as fp:
                        fp.write(dss_string)

                if (
                    model_map.opendss_file == OpenDSSFileTypes.MASTER_FILE.value
                    or model_map.opendss_file == OpenDSSFileTypes.COORDINATE_FILE.value
                ):
                    continue

                if separate_substations and separate_feeders:
                    substations_redirect[model_map.substation].add(
                        Path(model_map.feeder) / model_map.opendss_file
                    )
                    for equipment_map_to_write in equipment_maps_to_write:
                        substations_redirect[model_map.substation].add(
                            Path(model_map.feeder) / equipment_map_to_write.opendss_file
                        )
                    for controller_map, _ in controller_outputs:
                        substations_redirect[model_map.substation].add(
                            Path(model_map.feeder) / controller_map.opendss_file
                        )

                elif separate_substations:
                    substations_redirect[model_map.substation].add(Path(model_map.opendss_file))
                    for equipment_map_to_write in equipment_maps_to_write:
                        substations_redirect[model_map.substation].add(
                            Path(equipment_map_to_write.opendss_file)
                        )
                    for controller_map, _ in controller_outputs:
                        substations_redirect[model_map.substation].add(
                            Path(controller_map.opendss_file)
                        )

                if separate_feeders:
                    combined_feeder_sub = Path(model_map.substation) / Path(model_map.feeder)
                    if combined_feeder_sub not in feeders_redirect:
                        feeders_redirect[combined_feeder_sub] = set()
                    feeders_redirect[combined_feeder_sub].add(Path(model_map.opendss_file))
                    for equipment_map_to_write in equipment_maps_to_write:
                        feeders_redirect[combined_feeder_sub].add(
                            Path(equipment_map_to_write.opendss_file)
                        )
                    for controller_map, _ in controller_outputs:
                        feeders_redirect[combined_feeder_sub].add(
                            Path(controller_map.opendss_file)
                        )

                base_redirect.add(output_redirect / model_map.opendss_file)
                for equipment_map_to_write in equipment_maps_to_write:
                    base_redirect.add(output_redirect / equipment_map_to_write.opendss_file)
                for controller_map, _ in controller_outputs:
                    base_redirect.add(output_redirect / controller_map.opendss_file)

        self._write_base_master(base_redirect, output_folder)
        self._write_substation_master(substations_redirect)
        self._write_feeder_master(feeders_redirect)

    def _write_profiles(
        self, output_folder, seen_profile: set, output_redirect, base_redirect
    ) -> dict[str, dict[str, list[str]]]:
        all_profiles = []
        profile_type = None
        for component in self.system.iter_all_components():
            profiles = self.system.list_time_series(component, time_series_type=self.profile_type)
            profile_data = []
            for profile in profiles:
                if profile_type is None:
                    profile_type = profile.__class__

                if not issubclass(profile.__class__, profile_type):
                    msg = (
                        f"Profile {profile} is not of type {profile_type}. OpenDSS conversion "
                        + "requires all profiles to be of the same type. Please check your data model."
                    )
                    raise ValueError(msg)

                profile_data.append(
                    {
                        "profile": profile,
                        "metadata": self.system.list_time_series_metadata(component, profile.name),
                    }
                )
            if profile_data:
                profile_map = opendss_mapper.ProfileMapper(component, profile_data, self.system)
                profile_map.populate_opendss_dictionary()
                model_text = self._get_dss_string(profile_map)
                all_profiles.append(model_text)
                profile_id = profile_map.substation + profile_map.feeder + model_text
                if profile_id not in seen_profile:
                    seen_profile.add(profile_id)
                    with open(
                        output_folder / profile_map.opendss_file, "a", encoding="utf-8"
                    ) as fp:
                        fp.write(model_text)

                if profile_map is not None:
                    base_redirect.add(output_redirect / profile_map.opendss_file)

        return all_profiles

    def _build_directory_structure(
        self,
        separate_substations,
        separate_feeders,
        output_path,
        model_map,
        output_redirect,
        output_folder,
    ):
        if separate_substations:
            output_folder = Path(output_path, model_map.substation)
            output_redirect = Path(model_map.substation)
            output_folder.mkdir(exist_ok=True)
        else:
            output_folder.mkdir(exist_ok=True)

        if separate_feeders:
            output_folder /= model_map.feeder
            output_redirect /= model_map.feeder
            output_folder.mkdir(exist_ok=True)

        return output_folder, output_redirect

    def _write_switch_status(self, file_handler: TextIOWrapper):
        switches: list[MatrixImpedanceSwitch] = list(
            self.system.get_components(MatrixImpedanceSwitch)
        )
        for switch in switches:
            if not switch.is_closed[0]:
                file_handler.write(f"open line.{switch.name}\n")

    def _write_base_master(self, base_redirect, output_folder):
        # Only use Masters that have a voltage source, and hence already written.
        sources = list(self.system.get_components(DistributionVoltageSource))
        has_source = True if sources else False

        if has_source:
            bus = self.system.get_source_bus()
            equipment = self.system.get_bus_connected_components(bus.name, DistributionTransformer)
            if equipment:
                equipment_type = "Transformer"
                equipment_name = equipment[0].name
            else:
                equipment = self.system.get_bus_connected_components(
                    bus.name, DistributionBranchBase
                )
                if equipment:
                    equipment_type = "Line"
                    equipment_name = equipment[0].name
                else:
                    equipment_type = None
                    equipment_name = None

        file_order = [file_type.value for file_type in OpenDSSFileTypes]
        master_file = output_folder / OpenDSSFileTypes.MASTER_FILE.value
        if master_file.is_file():
            master_file = output_folder / OpenDSSFileTypes.MASTER_FILE.value
            with open(master_file, "a") as base_master:
                # TODO: provide ordering so LineCodes before Lines
                for file in file_order:
                    for dss_file in base_redirect:
                        if dss_file.name == file:
                            if (master_file.parent / dss_file).exists():
                                base_master.write("redirect " + str(dss_file))
                                base_master.write("\n")
                                break
                self._write_switch_status(base_master)
                if has_source and equipment_type:
                    base_master.write(
                        f"New EnergyMeter.SourceMeter element={equipment_type}.{equipment_name}\n"
                    )
                base_master.write(f"Set Voltagebases={self._get_voltage_bases()}\n")
                base_master.write("calcv\n")
                base_master.write("Solve\n")
                base_master.write(f"redirect {OpenDSSFileTypes.COORDINATE_FILE.value}\n")

        # base_master.write(f"BusCoords {filename}\n")

    def _write_substation_master(self, substations_redirect):
        for substation in substations_redirect:
            if (Path(substation) / OpenDSSFileTypes.MASTER_FILE.value).is_file():
                with open(
                    Path(substation) / OpenDSSFileTypes.MASTER_FILE.value, "a"
                ) as substation_master:
                    # TODO: provide ordering so LineCodes before Lines
                    for dss_file in substations_redirect[substation]:
                        if (Path(substation).parent / dss_file).exists():
                            substation_master.write("redirect " + str(dss_file))
                            substation_master.write("\n")

    def _write_feeder_master(self, feeders_redirect):
        for feeder in feeders_redirect:
            if (Path(feeder) / OpenDSSFileTypes.MASTER_FILE.value).is_file():
                with open(Path(feeder) / OpenDSSFileTypes.MASTER_FILE.value, "a") as feeder_master:
                    # TODO: provide ordering so LineCodes before Lines
                    for dss_file in feeders_redirect[feeder]:
                        if (Path(feeder).parent / dss_file).exists():
                            feeder_master.write("redirect " + str(dss_file))
                            feeder_master.write("\n")
