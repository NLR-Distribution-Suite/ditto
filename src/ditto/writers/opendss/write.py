from collections import defaultdict
from io import TextIOWrapper
from pathlib import Path
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


class Writer(AbstractWriter):
    files = []

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
        return dss_string

    def prepare_folder(self, output_path):
        directory = Path(output_path)
        files_to_remove = directory.rglob("*.dss")
        for dss_file in files_to_remove:
            logger.debug(f"Deleting existing file {dss_file}")
            # dss_file.unlink() #TODO: deletion causing tets to fail @tarek

    def _get_voltage_bases(self) -> list[float]:
        voltage_bases = []
        buses: list[DistributionBus] = list(self.system.get_components(DistributionBus))
        for bus in buses:
            voltage_bases.append(
                bus.rated_voltage.to("kilovolt").magnitude
                if bus.voltage_type == "line-to-line"
                else bus.rated_voltage.to("kilovolt").magnitude * 1.732
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

        output_redirect = Path("")
        profiles = self._write_profiles(output_path, seen_profile, output_redirect, base_redirect)
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

                dss_string = self._get_dss_string(model_map)
                if dss_string.startswith("new Vsource"):
                    dss_string = dss_string.replace("new Vsource", "Clear\n\nNew Circuit")
                equipment_dss_string = None
                equipment_map: list[Path] = None
                controller_dss_string = None
                controller_map: list[Path] = None

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
                        equipment_dss_string = self._get_dss_string(equipment_map)

                if hasattr(model, "controllers"):
                    for controller in model.controllers:
                        controller_mapper_name = controller.__class__.__name__ + "Mapper"
                        if not hasattr(opendss_mapper, controller_mapper_name):
                            logger.warning(
                                f"Equipment Mapper {controller_mapper_name} not found. Skipping"
                            )
                        else:
                            controller_mapper = getattr(opendss_mapper, controller_mapper_name)
                            controller_map = controller_mapper(controller, model.name, self.system)
                            controller_map.populate_opendss_dictionary()
                            controller_dss_string = self._get_dss_string(controller_map)

                output_folder = output_path
                self._build_directory_structure(
                    separate_substations,
                    separate_feeders,
                    output_path,
                    model_map,
                    output_redirect,
                    output_folder,
                )

                if equipment_dss_string is not None:
                    feeder_substation_equipment = (
                        model_map.substation + model_map.feeder + equipment_dss_string
                    )
                    if feeder_substation_equipment not in seen_equipment:
                        seen_equipment.add(feeder_substation_equipment)
                        with open(
                            output_folder / equipment_map.opendss_file, "a", encoding="utf-8"
                        ) as fp:
                            fp.write(equipment_dss_string)

                if controller_dss_string is not None:
                    feeder_substation_controller = (
                        model_map.substation + model_map.feeder + controller_dss_string
                    )
                    if feeder_substation_controller not in seen_controller:
                        seen_controller.add(feeder_substation_controller)
                        with open(
                            output_folder / controller_map.opendss_file, "a", encoding="utf-8"
                        ) as fp:
                            fp.write(controller_dss_string)

                # TODO: Check that there aren't multiple voltage sources for the same master file
                with open(output_folder / model_map.opendss_file, "a", encoding="utf-8") as fp:
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
                    if equipment_map is not None:
                        substations_redirect[model_map.substation].add(
                            Path(model_map.feeder) / equipment_map.opendss_file
                        )

                elif separate_substations:
                    substations_redirect[model_map.substation].add(Path(model_map.opendss_file))
                    if equipment_map is not None:
                        substations_redirect[model_map.substation].add(
                            Path(equipment_map.opendss_file)
                        )
                        if profiles:
                            substations_redirect

                if separate_feeders:
                    combined_feeder_sub = Path(model_map.substation) / Path(model_map.feeder)
                    if combined_feeder_sub not in feeders_redirect:
                        feeders_redirect[combined_feeder_sub] = set()
                    feeders_redirect[combined_feeder_sub].add(Path(model_map.opendss_file))
                    if equipment_map is not None:
                        feeders_redirect[combined_feeder_sub].add(Path(equipment_map.opendss_file))

                base_redirect.add(output_redirect / model_map.opendss_file)
                if equipment_map is not None:
                    base_redirect.add(output_redirect / equipment_map.opendss_file)
                if controller_map is not None:
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
