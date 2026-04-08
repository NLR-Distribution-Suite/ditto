import re

from ditto.readers.synergi.synergi_mapper import SynergiMapper
from gdm.distribution.equipment.concentric_cable_equipment import ConcentricCableEquipment
from gdm.distribution.equipment.bare_conductor_equipment import BareConductorEquipment
from gdm.quantities import Current, Distance, ResistancePULength, Voltage
from ditto.readers.synergi.length_units import length_units

class ConductorEquipmentMapper(SynergiMapper):
    def __init__(self, system):
        super().__init__(system)

    synergi_table = "DevConductors"
    synergi_database = "Equipment"
    MAGIC_NUMBER_1 = 2
    MAGIC_NUMBER_2 = 0.2

    def parse(self, row, unit_type, section_id_sections, from_node_sections, to_node_sections):
        name = self.map_name(row)
        strand_diameter = self.map_strand_diameter(row, unit_type)
        conductor_diameter = self.map_conductor_diameter(row, unit_type)
        cable_diameter = self.map_cable_diameter(row, unit_type)
        insulation_thickness = self.map_insulation_thickness(row, unit_type)
        insulation_diameter = self.map_insulation_diameter(row, unit_type)
        ampacity = self.map_ampacity(row)
        emergency_ampacity = self.map_emergency_ampacity(row)
        conductor_gmr = self.map_conductor_gmr(row, unit_type)
        strand_gmr = self.map_strand_gmr(row, unit_type)
        phase_ac_resistance = self.map_phase_ac_resistance(row, unit_type)
        strand_ac_resistance = self.map_strand_ac_resistance(row, unit_type)
        num_neutral_strands = self.map_num_neutral_strands(row)
        rated_voltage = self.map_rated_voltage(row)

        if insulation_thickness.magnitude <= 0:
            return BareConductorEquipment(name=name,
                                          conductor_diameter=conductor_diameter,
                                          conductor_gmr=conductor_gmr,
                                          ampacity=ampacity,
                                          emergency_ampacity=emergency_ampacity,
                                          ac_resistance=phase_ac_resistance,
                                          dc_resistance=phase_ac_resistance)
        elif rated_voltage is not None:
            return ConcentricCableEquipment(name=name,
                                            strand_diameter=strand_diameter,
                                            conductor_diameter=conductor_diameter,
                                            cable_diameter=cable_diameter,
                                            insulation_thickness=insulation_thickness,
                                            insulation_diameter=insulation_diameter,
                                            ampacity=ampacity,
                                            conductor_gmr=conductor_gmr,
                                            strand_gmr=strand_gmr,
                                            phase_ac_resistance=phase_ac_resistance,
                                            strand_ac_resistance=strand_ac_resistance,
                                            num_neutral_strands=num_neutral_strands,
                                            rated_voltage=rated_voltage)
        else:
            return None


    def map_name(self, row):
        return row["ConductorName"]

    def map_strand_diameter(self, row, unit_type):
        value = row["CableConNeutStrandDiameter_SUL"] * self.MAGIC_NUMBER_2
        unit = length_units[unit_type]["SUL"]
        return Distance(value, unit).to("mm")

    def map_conductor_diameter(self, row, unit_type):
        # TODO: Zero diameter indicates missing data; should be resolved with correct source values
        value = row["CableDiamConductor_SUL"] or row["Diameter_SUL"] or 0.001
        unit = length_units[unit_type]["SUL"]
        return Distance(value, unit).to("mm")

    def map_cable_diameter(self, row, unit_type):
        value = row["CableDiamOutside_SUL"] * self.MAGIC_NUMBER_1
        unit = length_units[unit_type]["SUL"]
        return Distance(value, unit).to("mm")

    def map_insulation_thickness(self, row, unit_type):
        outside = row["CableDiamOutside_SUL"]
        inside = row["CableDiamOverInsul_SUL"]
        thickness = (outside - inside)/2
        unit = length_units[unit_type]["SUL"]
        return Distance(thickness, unit).to("mm")

    def map_insulation_diameter(self, row, unit_type):
        value = row["CableDiamOverInsul_SUL"] * self.MAGIC_NUMBER_1
        unit = length_units[unit_type]["SUL"]
        return Distance(value, unit).to("mm")

    def map_ampacity(self, row):
        # TODO: Zero ampacity likely indicates missing data; should be resolved with correct source values
        value = row["ContinuousCurrentRating"] or 600
        return Current(value, "ampere")
    
    def map_emergency_ampacity(self, row):
        # TODO: Zero emergency ampacity indicates missing data; should be resolved with correct source values
        value = row["InterruptCurrentRating"] or 600
        return Current(value, "ampere")

    def map_conductor_gmr(self, row, unit_type):
        value = row["CableGMR_MUL"]
        if not value:
            # Estimate GMR from conductor diameter: GMR ≈ 0.7788 * radius
            diameter = row["CableDiamConductor_SUL"] or row["Diameter_SUL"]
            sul_unit = length_units[unit_type]["SUL"]
            # TODO: Zero diameter/GMR indicates missing data; should be resolved with correct source values
            return Distance(max(diameter / 2 * 0.7788, 0.001), sul_unit).to("mm")
        unit = length_units[unit_type]["MUL"]
        return Distance(value, unit).to("mm")

    def map_strand_gmr(self, row, unit_type):
        value = row["CableConNeutStrandDiameter_SUL"]
        value = value / 2 * 0.7788  # OpenDSS estimate is 0.7788 * radius
        # TODO: Zero strand GMR indicates missing data; should be resolved with correct source values
        value = max(value, 0.001)
        unit = length_units[unit_type]["SUL"]
        return Distance(value, unit).to("mm")

    def map_phase_ac_resistance(self, row, unit_type):
        # TODO: Zero resistance indicates missing data; should be resolved with correct source values
        value = row["CableResistance_PerLUL"] or row["PosSequenceResistance_PerLUL"] or 0.001
        unit = length_units[unit_type]["PerLUL"]
        return ResistancePULength(value, unit).to("ohm/km")

    def map_strand_ac_resistance(self, row, unit_type):
        # TODO: Zero strand resistance indicates missing data; should be resolved with correct source values
        value = row["CableConNeutResistance_PerLUL"] or 0.001
        unit = length_units[unit_type]["PerLUL"]
        return ResistancePULength(value, unit).to("ohm/km")

    #Need a field for number of phase strands too...
    def map_num_neutral_strands(self, row):
        value = row["CableConNeutStrandCount"]
        return value

    def map_rated_voltage(self, row):
        match = re.search(r"(\d+(?:\.\d+)?)\s*kV", row["ConductorName"], re.IGNORECASE)
        if match:
            return Voltage(float(match.group(1)), "kilovolt")
        return None

    def map_loading_limit(self, row):
        return None


