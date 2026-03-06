from gdm.distribution.components import DistributionBus, DistributionVoltageSource

from ditto.readers.cim_iec_61968_13.equipment.voltage_source_equipment import (
    VoltageSourceEquipmentMapper,
)
from ditto.readers.cim_iec_61968_13.cim_mapper import CimMapper
from ditto.readers.cim_iec_61968_13.common import phase_mapper


class DistributionVoltageSourceMapper(CimMapper):
    def __init__(self, system):
        super().__init__(system)

    def parse(self, row):
        return DistributionVoltageSource(
            name=self.map_name(row),
            bus=self.map_bus(row),
            phases=self.map_phases(),
            equipment=self.map_equipment(row),
        )

    def map_name(self, row):
        return self._required_field(row, "source", "DistributionVoltageSource")

    def map_bus(self, row):
        bus_name = self._required_field(
            row,
            "bus",
            f"DistributionVoltageSource '{self.map_name(row)}'",
        )
        return self._required_component(
            DistributionBus,
            bus_name,
            f"DistributionVoltageSource '{self.map_name(row)}'",
        )

    def map_phases(self):
        return [phase_mapper[phase] for phase in ["A", "B", "C"]]

    def map_equipment(self, row):
        mapper = VoltageSourceEquipmentMapper(self.system)
        equipment = mapper.parse(row)
        return equipment
