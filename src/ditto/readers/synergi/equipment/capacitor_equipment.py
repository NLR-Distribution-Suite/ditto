from ditto.readers.synergi.synergi_mapper import SynergiMapper
from gdm.quantities import ReactivePower, Resistance, Reactance
from gdm.distribution.equipment.phase_capacitor_equipment import PhaseCapacitorEquipment
from gdm.distribution.equipment.capacitor_equipment import CapacitorEquipment
from gdm.distribution.enums import ConnectionType, VoltageTypes
from gdm.quantities import Voltage

class CapacitorEquipmentMapper(SynergiMapper):
    def __init__(self, system):
        super().__init__(system)

    synergi_table = "InstCapacitors"
    synergi_database = "Model"

    def parse(self, row):
        name = self.map_name(row)
        phase_capacitors = self.map_phase_capacitors(row)
        connection_type = self.map_connection_type(row)
        rated_voltage = self.map_rated_voltage(row)
        voltage_type = self.map_voltage_type(row)
        return CapacitorEquipment(name=name,
                                  phase_capacitors=phase_capacitors,
                                  connection_type=connection_type,
                                  rated_voltage=rated_voltage,
                                  voltage_type=voltage_type)


    def map_name(self, row):
        return str(row["UniqueDeviceId"])

    def map_rated_voltage(self, row):
        return Voltage(float(row["RatedKv"]), "kilovolt")

    def map_voltage_type(self, row):
        return VoltageTypes.LINE_TO_LINE

    def map_phase_capacitors(self, row):
        phase_capacitors = []
        for phase in range(1, 4):
            mapper = PhaseCapacitorEquipmentMapper(self.system)
            phase_capacitor = mapper.parse(row, phase)
            phase_capacitors.append(phase_capacitor)
        return phase_capacitors


    def map_connection_type(self, row):
        value = row["ConnectionType"]
        if value == "YG":
            return ConnectionType.STAR.value
        if value == "D":
            return ConnectionType.DELTA.value


class PhaseCapacitorEquipmentMapper(SynergiMapper):
    def __init__(self, system):
        super().__init__(system)

    synergi_table = "InstCapacitors"
    synergi_database = "Model"

    def parse(self, row, phase):
        name = self.map_name(row, phase)
        resistance = self.map_resistance(row, phase)
        reactance = self.map_reactance(row, phase)
        rated_capacity = self.map_rated_capacity(row, phase)
        num_banks_on = self.map_num_banks_on(row, phase)
        num_banks = self.map_num_banks(row, phase)
        return PhaseCapacitorEquipment(name = name,
                                       resistance=resistance,
                                       reactance=reactance,
                                       rated_reactive_power=rated_capacity,
                                       num_banks_on=num_banks_on,
                                       num_banks=num_banks)

    def map_name(self, row, phase):
        if phase == 1:
            return str(row["UniqueDeviceId"]) + "_A"
        if phase == 2:
            return str(row["UniqueDeviceId"]) + "_B"
        if phase == 3:
            return str(row["UniqueDeviceId"]) + "_C"

    # Resistance and Reactance not included for capacitors
    def map_resistance(self, row, phase):
        return Resistance(0,'ohm')

    # Resistance and Reactance not included for capacitors
    def map_reactance(self, row, phase):
        return Reactance(0,'ohm')

    # TODO: This doesn't make sense. We should have fixed and switched values
    def map_rated_capacity(self, row, phase):
        total_capacity = 0
        fixed_key = f"FixedKvarPhase{phase}"
        if row[fixed_key] > 0:
            total_capacity += row[fixed_key]
        activated_key = f"Module{phase}Activated"    
        if row[activated_key] == 1:
            switched_key = f"Module{phase}KvarPerPhase"
            total_capacity += row[switched_key]
        return ReactivePower(total_capacity,'kilovar')

    # TODO: This doesn't make sense. This should indicate if the bank is switched
    def map_num_banks_on(self, row, phase):
        num_banks_on = 0
        activated_key = f"Module{phase}Activated"
        if row[activated_key] == 1:
            num_banks_on += 1
        return num_banks_on

    #TODO: This doesn't make sense. This should indicate how many banks are switched
    def map_num_banks(self, row, phase):
        num_banks = 1
        return num_banks


