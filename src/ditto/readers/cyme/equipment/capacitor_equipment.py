from ditto.readers.cyme.cyme_mapper import CymeMapper
from gdm.quantities import ReactivePower, Resistance, Reactance
from gdm.distribution.equipment.phase_capacitor_equipment import PhaseCapacitorEquipment
from gdm.distribution.equipment.capacitor_equipment import CapacitorEquipment
from gdm.distribution.enums import VoltageTypes, ConnectionType
from gdm.quantities import Voltage

class CapacitorEquipmentMapper(CymeMapper):
    def __init__(self, system):
        super().__init__(system)

    cyme_file = 'Equipment'
    cyme_section = 'SHUNT CAPACITOR'

    def parse(self, row, connection):
        name = self.map_name(row)
        rated_voltage = self.map_rated_voltage(row)
        phase_capacitors = self.map_phase_capacitors(row)
        voltage_type = self.map_voltage_type(connection)
        return CapacitorEquipment(name=name,
                                  phase_capacitors=phase_capacitors,
                                  rated_voltage=rated_voltage,
                                  voltage_type=voltage_type)

    def map_name(self, row):
        return row["ID"]
    
    def map_rated_voltage(self, row):
        return Voltage(float(row["KV"]), "kilovolt")

    def map_phase_capacitors(self, row):
        phase_capacitors = []
        number_of_phases = 3 if int(row["Type"]) > 1 else 1
        
        for phase in range(1, number_of_phases + 1):
            mapper = PhaseCapacitorEquipmentMapper(self.system, num_banks_on=number_of_phases)
            phase_capacitor = mapper.parse(row, phase)
            phase_capacitors.append(phase_capacitor)
        return phase_capacitors
    
    def map_voltage_type(self, connection):
        if connection in ("Y", "YNG"):
            return VoltageTypes.LINE_TO_GROUND
        return VoltageTypes.LINE_TO_LINE


class PhaseCapacitorEquipmentMapper(CymeMapper):
    def __init__(self, system, num_banks_on):
        super().__init__(system)
        self.num_banks_on = num_banks_on

    cyme_file = 'Equipment'
    cyme_section = 'SHUNT CAPACITOR'

    def parse(self, row, phase):
        name = self.map_name(row, phase)
        rated_reactive_power = self.map_rated_reactive_power(row)
        return PhaseCapacitorEquipment(name = name,
                                       rated_reactive_power=rated_reactive_power,
                                       num_banks_on=self.num_banks_on)

    def map_name(self, row, phase):
        if phase == 1:
            return row["ID"] + "_A"
        if phase == 2:
            return row["ID"] + "_B"
        if phase == 3:
            return row["ID"] + "_C"


    def map_rated_reactive_power(self, row):
        return ReactivePower(float(row["KVAR"]),'kilovar')
