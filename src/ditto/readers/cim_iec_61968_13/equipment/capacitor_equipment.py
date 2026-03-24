from gdm.quantities import ReactivePower, Resistance, Reactance
from gdm.distribution.equipment.phase_capacitor_equipment import PhaseCapacitorEquipment
from gdm.distribution.equipment.capacitor_equipment import CapacitorEquipment
from gdm.distribution.enums import ConnectionType, VoltageTypes
from gdm.quantities import Voltage

from ditto.readers.cim_iec_61968_13.cim_mapper import CimMapper


class CapacitorEquipmentMapper(CimMapper):
    def __init__(self, system):
        super().__init__(system)

    def parse(self, row):
        phases = row["phase"]
        if phases is None:
            self.phases = ["A", "B", "C"]
        else:
            self.phases = phases.split(",")

        return CapacitorEquipment(
            name=self.map_name(row),
            phase_capacitors=self.map_phase_capacitors(row),
            connection_type=self.map_connection_type(row),
            rated_voltage=self.map_rated_voltage(row),
            voltage_type=self.map_voltage_type(),
        )

    def map_name(self, row):
        return row["capacitor"] + "_equipment"

    def map_voltage_type(self):
        n_phases = len(self.phases)
        return VoltageTypes.LINE_TO_LINE if n_phases == 3 else VoltageTypes.LINE_TO_LINE

    def map_rated_voltage(self, row):
        return Voltage(float(row["rated_voltage"]), "volt")

    def map_phase_capacitors(self, row):
        phase_loads = []
        n_phases = len(self.phases)
        voltage = (
            float(row["rated_voltage"]) if n_phases == 3 else float(row["rated_voltage"]) / 1.732
        )
        b1 = float(row["b1"])
        var = voltage**2 * b1
        var_per_phase = var / n_phases
        for phase in self.phases:
            if b1 > 0:
                mapper = PhaseCapacitorEquipmentMapper(self.system)
                phase_load = mapper.parse(row, var_per_phase, phase)
                phase_loads.append(phase_load)
        return phase_loads

    def map_connection_type(self, row):
        return ConnectionType.DELTA if row["conn"] == "D" else ConnectionType.STAR


class PhaseCapacitorEquipmentMapper(CimMapper):
    def __init__(self, system):
        super().__init__(system)

    def parse(self, row, var_per_phase, phase):
        return PhaseCapacitorEquipment(
            name=self.map_name(row, phase),
            resistance=self.map_resistance(),
            reactance=self.map_reactance(),
            rated_reactive_power=self.map_rated_reactive_power(var_per_phase),
            num_banks_on=self.map_num_banks_on(row),
            num_banks=self.map_num_banks(row),
        )

    def map_name(self, row, phase):
        return row["capacitor"] + "_phase_capacitor_equipment_" + phase

    # Resistance and Reactance not included for capacitors
    def map_resistance(self):
        return Resistance(0, "ohm")

    # Resistance and Reactance not included for capacitors
    def map_reactance(self):
        return Reactance(0, "ohm")

    # TODO: This doesn't make sense. We should have fixed and switched values
    def map_rated_reactive_power(self, var_per_phase):
        return ReactivePower(var_per_phase, "var")

    # TODO: This doesn't make sense. This should indicate if the bank is switched
    def map_num_banks_on(self, row):
        return row["steps"]

    # TODO: This doesn't make sense. This should indicate how many banks are switched
    def map_num_banks(self, row):
        return row["steps"]
