from gdm.distribution.equipment import BatteryEquipment, InverterEquipment
from gdm.distribution.enums import VoltageTypes
from gdm.quantities import ActivePower, ApparentPower, EnergyDC, Voltage

from ditto.readers.cim_iec_61968_13.cim_mapper import CimMapper


class BatteryEquipmentMapper(CimMapper):
    def __init__(self, system):
        super().__init__(system)

    def parse(self, row):
        return BatteryEquipment(
            name=self.map_name(row),
            rated_energy=self.map_rated_energy(row),
            rated_power=self.map_rated_power(row),
            charging_efficiency=1.0,
            discharging_efficiency=1.0,
            idling_efficiency=1.0,
            rated_voltage=self.map_rated_voltage(row),
            voltage_type=VoltageTypes.LINE_TO_LINE,
        )

    def map_name(self, row):
        return row["battery"] + "_equipment"

    def map_rated_energy(self, row):
        return EnergyDC(float(row["rated_energy"]), "watthour")

    def map_rated_power(self, row):
        return ActivePower(float(row["max_p"]), "watt")

    def map_rated_voltage(self, row):
        return Voltage(float(row["rated_voltage"]), "volt")


class InverterEquipmentMapper(CimMapper):
    def __init__(self, system):
        super().__init__(system)

    def parse(self, row):
        return InverterEquipment(
            name=self.map_name(row),
            rated_apparent_power=self.map_rated_apparent_power(row),
            rise_limit=None,
            fall_limit=None,
            cutout_percent=0.0,
            cutin_percent=0.0,
            dc_to_ac_efficiency=1.0,
            eff_curve=None,
        )

    def map_name(self, row):
        return row["battery"] + "_inverter"

    def map_rated_apparent_power(self, row):
        rated_s = row["rated_s"]
        if rated_s is None:
            rated_s = row["max_p"]
        return ApparentPower(float(rated_s), "VA")
