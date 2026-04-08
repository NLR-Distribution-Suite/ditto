from ditto.readers.synergi.synergi_mapper import SynergiMapper
from gdm.distribution.equipment.distribution_transformer_equipment import WindingEquipment
from gdm.distribution.enums import VoltageTypes, ConnectionType
from gdm.quantities import Voltage

class WindingEquipmentMapper(SynergiMapper):
    def __init__(self, system):
        super().__init__(system)

    synergi_table = "DevTransformers"
    synergi_database = "Equipment"

    def parse(self, row, winding_number):
        name = self.map_name(row, winding_number)
        resistance = self.map_resistance(row, winding_number)
        is_grounded = self.map_is_grounded(row, winding_number)
        rated_voltage = self.map_nominal_voltage(row, winding_number)
        voltage_type = self.map_voltage_type(row)
        rated_power = self.map_rated_power(row)
        num_phases = self.num_phases(row)
        connection_type = self.connection_type(row, winding_number)
        tap_positions = self.map_tap_positions(row)
        total_taps = self.map_total_taps(row)
        min_tap_pu = self.map_min_tap_pu(row)
        max_tap_pu = self.map_max_tap_pu(row)

        return WindingEquipment(name=name,
                                resistance=resistance,
                                is_grounded=is_grounded,
                                rated_voltage=rated_voltage,
                                voltage_type=voltage_type,
                                rated_power=rated_power,
                                num_phases=num_phases,
                                connection_type=connection_type,
                                tap_positions=tap_positions,
                                total_taps=total_taps,
                                min_tap_pu=min_tap_pu,
                                max_tap_pu=max_tap_pu)

    def map_name(self, row, winding_number):
        return row["TransformerName"] + "_Winding_" + str(winding_number)

    def map_resistance(self, row, winding_number):
        percent_resistance = row["PercentResistance"]
        return percent_resistance


    def map_is_grounded(self, row, winding_number):
        if winding_number == 1:
            connection = row["HighVoltageConnectionCode"]
        else:
            connection = row["LowVoltageConnectionCode"]

        if "G" in connection:    
            return True
        return False

    def map_nominal_voltage(self, row, winding_number):
        if winding_number == 1:
            return Voltage(row["HighSideRatedKv"], "kilovolt")
        else:
            return Voltage(row["LowSideRatedKv"], "kilovolt")

    def map_voltage_type(self, row):
        return VoltageTypes.LINE_TO_LINE

    def map_rated_power(self, row):
        return row["TransformerRatedKva"]

    def num_phases(self, row):
        if row["IsThreePhaseUnit"] == 1:
            return 3
        return 1

    def connection_type(self, row, winding_number):
        if winding_number == 1:
            connection = row["HighVoltageConnectionCode"]
        else:
            connection = row["LowVoltageConnectionCode"]
        
        if "D" in connection:
            return ConnectionType.DELTA
        if "Y" in connection:
            return ConnectionType.STAR

    #TODO: Check if this is correct
    def map_tap_positions(self, row):
        if row["IsThreePhaseUnit"] == 1:
            return [1, 1, 1]
        return [1]

    def map_total_taps(self, row):
        return row["NumberOfTaps"]

    def map_min_tap_pu(self, row):
        return 1-float(row["RaiseAndLowerMaxPercentage"])/100

    def map_max_tap_pu(self, row):
        return 1+float(row["RaiseAndLowerMaxPercentage"])/100
