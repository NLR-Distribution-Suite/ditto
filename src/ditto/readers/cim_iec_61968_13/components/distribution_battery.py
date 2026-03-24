from gdm.distribution.components import DistributionBattery, DistributionBus
from gdm.quantities import ActivePower, ReactivePower

from ditto.readers.cim_iec_61968_13.equipment.battery_equipment import (
    BatteryEquipmentMapper,
    InverterEquipmentMapper,
)
from ditto.readers.cim_iec_61968_13.cim_mapper import CimMapper
from ditto.readers.cim_iec_61968_13.common import phase_mapper


class DistributionBatteryMapper(CimMapper):
    def __init__(self, system):
        super().__init__(system)

    def parse(self, row):
        return DistributionBattery(
            name=self.map_name(row),
            bus=self.map_bus(row),
            phases=self.map_phases(row),
            active_power=self.map_active_power(row),
            reactive_power=self.map_reactive_power(row),
            controller=None,
            inverter=self.map_inverter(row),
            equipment=self.map_equipment(row),
        )

    def map_name(self, row):
        return self._required_field(row, "battery", "DistributionBattery")

    def map_bus(self, row):
        battery_name = self.map_name(row)
        bus_name = self._required_field(row, "bus", f"DistributionBattery '{battery_name}'")
        return self._required_component(
            DistributionBus,
            bus_name,
            f"DistributionBattery '{battery_name}'",
        )

    def map_phases(self, row):
        phases = row["phase"]
        if phases is None:
            phases = ["A", "B", "C"]
        else:
            phases = phases.split(",")
        return [phase_mapper[phase] for phase in phases if phase in phase_mapper]

    def map_active_power(self, row):
        return ActivePower(float(row["p"]), "watt")

    def map_reactive_power(self, row):
        return ReactivePower(float(row["q"]), "var")

    def map_equipment(self, row):
        return BatteryEquipmentMapper(self.system).parse(row)

    def map_inverter(self, row):
        return InverterEquipmentMapper(self.system).parse(row)
