from ditto.readers.cyme.constants import DEFAULT_BRANCH_AMPACITY, DEFAULT_BRANCH_RESISTANCE
from loguru import logger
from gdm.quantities import Current, Distance, ResistancePULength
from ditto.readers.cyme.cyme_mapper import CymeMapper
from gdm.distribution.equipment.geometry_branch_equipment import GeometryBranchEquipment
from gdm.distribution.equipment.bare_conductor_equipment import BareConductorEquipment


class GeometryBranchEquipmentMapper(CymeMapper):
    def __init__(self, system):
        super().__init__(system)

    cyme_file = "Equipment"
    cyme_section = "LINE"

    def parse(self, row, spacing_ids):
        name = self.map_name(row)
        conductors = self.map_conductors(row, spacing_ids)
        horizontal_positions = self.map_horizontal_positions(row, spacing_ids)
        vertical_positions = self.map_vertical_positions(row, spacing_ids)

        return GeometryBranchEquipment.model_construct(
            name=name,
            conductors=conductors,
            horizontal_positions=horizontal_positions,
            vertical_positions=vertical_positions,
        )

    def map_name(self, row):
        name = row["ID"]
        return name

    def map_vertical_positions(self, row, spacing_ids):
        spacing_id = row["SpacingID"]
        spacing = spacing_ids.loc[spacing_id]

        if not spacing.empty:
            vertical_positions = []
            cond1_y = spacing["PosOfCond1_Y"]
            cond2_y = spacing["PosOfCond2_Y"]
            cond3_y = spacing["PosOfCond3_Y"]
            neutral_y = spacing["PosOfNeutralCond_Y"]
            if cond1_y != "":
                y1 = float(cond1_y)
                vertical_positions.append(y1)
            if cond2_y != "":
                y2 = float(cond2_y)
                vertical_positions.append(y2)
            if cond3_y != "":
                y3 = float(cond3_y)
                vertical_positions.append(y3)
            if neutral_y != "":
                y_n = float(neutral_y)
                vertical_positions.append(y_n)
            return Distance(vertical_positions, "feet").to("m")
        return None

    def map_horizontal_positions(self, row, spacing_ids):
        spacing_id = row["SpacingID"]
        spacing = spacing_ids.loc[spacing_id]
        if not spacing.empty:
            horizontal_positions = []
            cond1_x = spacing["PosOfCond1_X"]
            cond2_x = spacing["PosOfCond2_X"]
            cond3_x = spacing["PosOfCond3_X"]
            neutral_x = spacing["PosOfNeutralCond_X"]
            if cond1_x != "":
                x1 = float(cond1_x)
                horizontal_positions.append(x1)
            if cond2_x != "":
                x2 = float(cond2_x)
                horizontal_positions.append(x2)
            if cond3_x != "":
                x3 = float(cond3_x)
                horizontal_positions.append(x3)
            if neutral_x != "":
                x_n = float(neutral_x)
                horizontal_positions.append(x_n)
            return Distance(horizontal_positions, "feet").to("m")
        return None

    def map_conductors(self, row, spacing_ids):
        phase_conductor_name = row["PhaseCondID"]
        neutral_conductor_name = row["NeutralCondID"]
        try:
            phase_conductor = self.system.get_component(
                component_type=BareConductorEquipment, name=phase_conductor_name
            )
        except Exception as e:
            logger.warning(
                f"Phase conductor {phase_conductor_name} not found in system. Using default conductor. Error: {e}"
            )
            phase_conductor = self.system.get_component(
                component_type=BareConductorEquipment, name="Default"
            )
        try:
            neutral_conductor = self.system.get_component(
                component_type=BareConductorEquipment, name=neutral_conductor_name
            )
        except Exception as e:
            logger.warning(
                f"Neutral conductor {neutral_conductor_name} not found in system. Using default conductor. Error: {e}"
            )
            neutral_conductor = self.system.get_component(
                component_type=BareConductorEquipment, name="Default"
            )

        spacing_id = row["SpacingID"]
        spacing = spacing_ids.loc[spacing_id]
        if not spacing.empty:
            conductors = []
            cond1 = spacing["PosOfCond1_X"]
            cond2 = spacing["PosOfCond2_X"]
            cond3 = spacing["PosOfCond3_X"]
            neutral = spacing["PosOfNeutralCond_X"]
            if cond1 != "":
                conductors.append(phase_conductor)
            if cond2 != "":
                conductors.append(phase_conductor)
            if cond3 != "":
                conductors.append(phase_conductor)
            if neutral != "":
                conductors.append(neutral_conductor)
            return conductors
        return None


class BareConductorEquipmentMapper(CymeMapper):
    def __init__(self, system):
        super().__init__(system)

    cyme_file = "Equipment"
    cyme_section = "CONDUCTOR"

    def parse(self, row):
        name = self.map_name(row)
        conductor_diameter = self.map_conductor_diameter(row)
        conductor_gmr = self.map_conductor_gmr(row)
        ampacity = self.map_ampacity(row)
        emergency_ampacity = self.map_emergency_ampacity(row)
        ac_resistance = self.map_ac_resistance(row)
        dc_resistance = self.map_dc_resistance(row)
        return BareConductorEquipment.model_construct(
            name=name,
            conductor_diameter=conductor_diameter,
            conductor_gmr=conductor_gmr,
            ampacity=ampacity,
            emergency_ampacity=emergency_ampacity,
            ac_resistance=ac_resistance,
            dc_resistance=dc_resistance,
        )

    def map_name(self, row):
        name = row["ID"]
        return name

    def map_conductor_diameter(self, row):
        conductor_diameter = float(row["Diameter"])
        return Distance(conductor_diameter, "inch").to("mm")

    def map_conductor_gmr(self, row):
        conductor_gmr = Distance(float(row["GMR"]), "inch").to("mm")
        return conductor_gmr

    def map_ampacity(self, row):
        ampacity = Current(float(row["Amps"]), "amp")
        if ampacity == 0.0:
            ampacity = DEFAULT_BRANCH_AMPACITY
        return ampacity

    def map_emergency_ampacity(self, row):
        emergency_ampacity = Current(float(row["Amps_4"]), "amp")
        if emergency_ampacity == 0.0:
            emergency_ampacity = DEFAULT_BRANCH_AMPACITY
        return emergency_ampacity

    def map_ac_resistance(self, row):
        ac_resistance = ResistancePULength(float(row["R25"]), "ohm/mile").to("ohm/km")
        if ac_resistance == 0.0:
            ac_resistance = DEFAULT_BRANCH_RESISTANCE
        return ac_resistance

    def map_dc_resistance(self, row):
        dc_resistance = ResistancePULength(float(row["R25"]), "ohm/mile").to("ohm/km")
        if dc_resistance == 0.0:
            dc_resistance = DEFAULT_BRANCH_RESISTANCE
        return dc_resistance


class GeometryBranchByPhaseEquipmentMapper(CymeMapper):
    def __init__(self, system):
        super().__init__(system)

    cyme_file = "Network"
    cyme_section = "OVERHEAD BYPHASE SETTING"

    def parse(self, row, spacing_ids):
        name = self.map_name(row)
        conductors = self.map_conductors(row, spacing_ids)
        horizontal_positions = self.map_horizontal_positions(row, spacing_ids)
        vertical_positions = self.map_vertical_positions(row, spacing_ids)

        return GeometryBranchEquipment.model_construct(
            name=name,
            conductors=conductors,
            horizontal_positions=horizontal_positions,
            vertical_positions=vertical_positions,
        )

    def map_name(self, row):
        name = row["DeviceNumber"]
        return name

    def map_vertical_positions(self, row, spacing_ids):
        phase_A_conductor_name = row["CondID_A"]
        phase_B_conductor_name = row["CondID_B"]
        phase_C_conductor_name = row["CondID_C"]
        if "CondID_N1" in row:
            neutral_conductor_name = row["CondID_N1"]
        else:
            neutral_conductor_name = row["CondID_N"]
        spacing_id = row["SpacingID"]
        spacing = spacing_ids.loc[spacing_id]

        if not spacing.empty:
            vertical_positions = []
            cond1_y = spacing["PosOfCond1_Y"]
            cond2_y = spacing["PosOfCond2_Y"]
            cond3_y = spacing["PosOfCond3_Y"]
            neutral_y = spacing["PosOfNeutralCond_Y"]
            if cond1_y != "" and phase_A_conductor_name != "NONE":
                y1 = float(cond1_y)
                vertical_positions.append(y1)
            if cond2_y != "" and phase_B_conductor_name != "NONE":
                y2 = float(cond2_y)
                vertical_positions.append(y2)
            if cond3_y != "" and phase_C_conductor_name != "NONE":
                y3 = float(cond3_y)
                vertical_positions.append(y3)
            if neutral_y != "" and neutral_conductor_name != "NONE":
                y_n = float(neutral_y)
                vertical_positions.append(y_n)
            return Distance(vertical_positions, "feet").to("m")
        return None

    def map_horizontal_positions(self, row, spacing_ids):
        phase_A_conductor_name = row["CondID_A"]
        phase_B_conductor_name = row["CondID_B"]
        phase_C_conductor_name = row["CondID_C"]
        if "CondID_N1" in row:
            neutral_conductor_name = row["CondID_N1"]
        else:
            neutral_conductor_name = row["CondID_N"]
        spacing_id = row["SpacingID"]
        spacing = spacing_ids.loc[spacing_id]
        if not spacing.empty:
            horizontal_positions = []
            cond1_x = spacing["PosOfCond1_X"]
            cond2_x = spacing["PosOfCond2_X"]
            cond3_x = spacing["PosOfCond3_X"]
            neutral_x = spacing["PosOfNeutralCond_X"]
            if cond1_x != "" and phase_A_conductor_name != "NONE":
                x1 = float(cond1_x)
                horizontal_positions.append(x1)
            if cond2_x != "" and phase_B_conductor_name != "NONE":
                x2 = float(cond2_x)
                horizontal_positions.append(x2)
            if cond3_x != "" and phase_C_conductor_name != "NONE":
                x3 = float(cond3_x)
                horizontal_positions.append(x3)
            if neutral_x != "" and neutral_conductor_name != "NONE":
                x_n = float(neutral_x)
                horizontal_positions.append(x_n)
            return Distance(horizontal_positions, "feet").to("m")
        return None

    def map_conductors(self, row, spacing_ids):
        phase_A_conductor_name = row["CondID_A"]
        phase_B_conductor_name = row["CondID_B"]
        phase_C_conductor_name = row["CondID_C"]
        neutral_conductor_name = row["CondID_N1"] if "CondID_N1" in row else row["CondID_N"]

        phase_A_conductor = None
        phase_B_conductor = None
        phase_C_conductor = None
        neutral_conductor = None

        if phase_A_conductor_name != "NONE":
            phase_A_conductor = self.system.get_component(
                component_type=BareConductorEquipment, name=phase_A_conductor_name
            )
        if phase_B_conductor_name != "NONE":
            phase_B_conductor = self.system.get_component(
                component_type=BareConductorEquipment, name=phase_B_conductor_name
            )
        if phase_C_conductor_name != "NONE":
            phase_C_conductor = self.system.get_component(
                component_type=BareConductorEquipment, name=phase_C_conductor_name
            )
        if neutral_conductor_name != "NONE":
            neutral_conductor = self.system.get_component(
                component_type=BareConductorEquipment, name=neutral_conductor_name
            )

        spacing_id = row["SpacingID"]
        # Spacing is used to see how many conductors there are
        spacing = spacing_ids.loc[spacing_id]
        if not spacing.empty:
            conductors = []
            cond1 = spacing["PosOfCond1_X"]
            cond2 = spacing["PosOfCond2_X"]
            cond3 = spacing["PosOfCond3_X"]
            neutral = spacing["PosOfNeutralCond_X"]
            if cond1 != "" and phase_A_conductor is not None:
                conductors.append(phase_A_conductor)
            if cond2 != "" and phase_B_conductor is not None:
                conductors.append(phase_B_conductor)
            if cond3 != "" and phase_C_conductor is not None:
                conductors.append(phase_C_conductor)
            if neutral != "" and neutral_conductor is not None:
                conductors.append(neutral_conductor)

            return conductors
        return None
