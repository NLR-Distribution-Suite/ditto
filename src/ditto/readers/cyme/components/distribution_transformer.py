from loguru import logger
from ditto.readers.cyme.cyme_mapper import CymeMapper
from ditto.readers.cyme.equipment.distribution_transformer_equipment import (
    DistributionTransformerEquipmentMapper,
)
from ditto.readers.cyme.equipment.distribution_transformer_three_winding_equipment import (
    DistributionTransformerThreeWindingEquipmentMapper,
)
from gdm.distribution.components.distribution_bus import DistributionBus
from gdm.distribution.components.distribution_transformer import DistributionTransformer
from gdm.distribution.enums import Phase


class DistributionTransformerMapper(CymeMapper):
    def __init__(self, system):
        super().__init__(system)

    cyme_file = "Network"
    cyme_section = "TRANSFORMER SETTING"

    def parse(self, row, used_sections, section_id_sections, equipment_data):
        section_id = str(row["SectionID"])
        section = section_id_sections[section_id]
        phase = section["Phase"]

        equipment_row = equipment_data.get(row["EqID"], None)
        name = self.map_name(row)
        buses = self.map_buses(row, section_id_sections)
        winding_phases = self.map_winding_phases(row, section_id_sections, equipment_row, phase)
        equipment = self.map_equipment(row, equipment_row, phase)
        try:
            used_sections.add(name)
            return DistributionTransformer.model_construct(
                name=name, buses=buses, winding_phases=winding_phases, equipment=equipment
            )
        except Exception as e:
            logger.warning(f"Failed to create DistributionTransformer {name}: {e}")
            return None

    def map_name(self, row):
        name = row["SectionID"]
        return name

    def map_buses(self, row, section_id_sections):
        section_id = str(row["SectionID"])
        section = section_id_sections[section_id]
        from_bus_name = section["FromNodeID"]
        to_bus_name = section["ToNodeID"]

        from_bus = self.system.get_component(component_type=DistributionBus, name=from_bus_name)
        to_bus = self.system.get_component(component_type=DistributionBus, name=to_bus_name)
        return [from_bus, to_bus]

    def map_winding_phases(self, row, section_id_sections, equipment_row, phase):
        section_id = str(row["SectionID"])
        section = section_id_sections[section_id]

        if equipment_row is None:
            print(
                f"Equipment row not found for transformer {row['EqID']}. Assuming 2 windings. {section}"
            )
            equipment_row = {"Type": "2"}
        windings_list = []
        # TODO Center tapped/Split phase not supported
        # This will assign it properly but handling of buses needs to be developed
        # if equipment_row['Type'] == "4":
        #    num_windings = 3
        # else:
        #    num_windings = 2
        num_windings = 2
        for i in range(num_windings):
            winding_phases = []
            if "A" in phase:
                winding_phases.append(Phase.A)
            if "B" in phase:
                winding_phases.append(Phase.B)
            if "C" in phase:
                winding_phases.append(Phase.C)
            windings_list.append(winding_phases)
        return windings_list

    def map_equipment(self, row, equipment_row, phase):
        mapper = DistributionTransformerEquipmentMapper(self.system)
        if equipment_row is not None:
            equipment = mapper.parse(equipment_row, row, phase)
            if equipment is not None:
                return equipment
        return None


class DistributionTransformerByPhaseMapper(CymeMapper):
    def __init__(self, system):
        super().__init__(system)

    cyme_file = "Network"
    cyme_section = "TRANSFORMER BYPHASE SETTING"

    def parse(self, row, used_sections, section_id_sections, equipment_data):
        additional_transformers = []

        for phase in ["1", "2", "3"]:
            if (
                row["PhaseTransformerID" + phase] is None
                or row["PhaseTransformerID" + phase] == ""
            ):
                continue
            equipment_row = equipment_data.get(row["PhaseTransformerID" + phase], None)

            name = self.map_name(row, phase)
            equipment = self.map_equipment(row, phase, equipment_row)
            buses = self.map_buses(row, section_id_sections, equipment.is_center_tapped)
            winding_phases = self.map_winding_phases(row, phase, equipment_row)

            try:
                used_sections.add(row["SectionID"])
                additional_transformers.append(
                    DistributionTransformer.model_construct(
                        name=name, buses=buses, winding_phases=winding_phases, equipment=equipment
                    )
                )
            except Exception as e:
                logger.warning(
                    f"Failed to add additional transformer {name} for phase {phase} on {row['SectionID']}: {e}"
                )
                continue
        return additional_transformers

    def map_name(self, row, phase):
        name = row["SectionID"] + f"_{phase}"
        return name

    def map_buses(self, row, section_id_sections, is_center_tapped=False):
        section_id = str(row["SectionID"])
        section = section_id_sections[section_id]
        from_bus_name = section["FromNodeID"]
        to_bus_name = section["ToNodeID"]

        from_bus = self.system.get_component(component_type=DistributionBus, name=from_bus_name)
        to_bus = self.system.get_component(component_type=DistributionBus, name=to_bus_name)
        if is_center_tapped:
            return [from_bus, to_bus, to_bus]
        return [from_bus, to_bus]

    def map_winding_phases(self, row, phase, equipment_row):
        if equipment_row is None:
            print(
                f"Equipment row not found for transformer {row['PhaseTransformerID' + phase]}. Assuming 2 windings."
            )
            equipment_row = {"Type": 2}
        windings_list = []

        # TODO Center tapped/Split phase not supported
        # This will assign it properly but handling of buses needs to be developed
        # num_windings = 3
        # if equipment_row['Type'] == "4":
        #    num_windings = 3
        # else:
        #    num_windings = 2
        num_windings = 2
        for i in range(num_windings):
            winding_phases = []
            if "1" == phase:
                winding_phases.append(Phase.A)
            if "2" == phase:
                winding_phases.append(Phase.B)
            if "3" == phase:
                winding_phases.append(Phase.C)
            windings_list.append(winding_phases)
        assert len(windings_list) == num_windings
        return windings_list

    def map_equipment(self, row, phase, equipment_row):
        mapper = DistributionTransformerEquipmentMapper(self.system)
        if equipment_row is not None:
            equipment = mapper.parse(equipment_row, row, phase)
            if equipment is not None:
                return equipment
        return None


class DistributionTransformerThreeWindingMapper(CymeMapper):
    def __init__(self, system):
        super().__init__(system)

    cyme_file = "Network"
    cyme_section = "THREE WINDING TRANSFORMER SETTING"

    def parse(self, row, used_sections, section_id_sections, equipment_data):
        equipment_row = equipment_data.get(row["EqID"], None)
        name = self.map_name(row)
        buses = self.map_buses(row, section_id_sections)
        winding_phases = self.map_winding_phases(row, section_id_sections)
        equipment = self.map_equipment(row, equipment_row)
        try:
            used_sections.add(name)
            return DistributionTransformer.model_construct(
                name=name, buses=buses, winding_phases=winding_phases, equipment=equipment
            )
        except Exception as e:
            logger.warning(f"Failed to create DistributionTransformer {name}: {e}")
            return None

    def map_name(self, row):
        name = row["SectionID"]
        return name

    def map_buses(self, row, section_id_sections):
        section_id = str(row["SectionID"])
        section = section_id_sections[section_id]
        from_bus_name = section["FromNodeID"]
        to_bus_name = section["ToNodeID"]
        tertiary_bus = row["TertiaryNodeID"]

        from_bus = self.system.get_component(component_type=DistributionBus, name=from_bus_name)
        to_bus = self.system.get_component(component_type=DistributionBus, name=to_bus_name)

        tertiary_bus = self.system.get_component(component_type=DistributionBus, name=tertiary_bus)
        if tertiary_bus.phases == []:
            tertiary_bus.phases = to_bus.phases

        return [from_bus, to_bus, tertiary_bus]

    def map_winding_phases(self, row, section_id_sections):
        section_id = str(row["SectionID"])
        section = section_id_sections[section_id]
        phase = section["Phase"]
        windings_list = []

        num_windings = 3
        for i in range(num_windings):
            winding_phases = []
            if "A" in phase:
                winding_phases.append(Phase.A)
            if "B" in phase:
                winding_phases.append(Phase.B)
            if "C" in phase:
                winding_phases.append(Phase.C)
            windings_list.append(winding_phases)
        return windings_list

    def map_equipment(self, row, equipment_row):
        mapper = DistributionTransformerThreeWindingEquipmentMapper(self.system)
        if equipment_row is not None:
            equipment = mapper.parse(equipment_row, row)
            if equipment is not None:
                return equipment
        return None
