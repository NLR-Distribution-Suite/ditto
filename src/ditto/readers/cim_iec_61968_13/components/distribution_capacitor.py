from gdm.distribution.components import DistributionBus, DistributionCapacitor

from ditto.readers.cim_iec_61968_13.equipment.capacitor_equipment import CapacitorEquipmentMapper
from ditto.readers.cim_iec_61968_13.cim_mapper import CimMapper
from ditto.readers.cim_iec_61968_13.common import phase_mapper


class DistributionCapacitorMapper(CimMapper):
    def __init__(self, system):
        super().__init__(system)

    def parse(self, row):
        return DistributionCapacitor(
            name=self.map_name(row),
            bus=self.map_bus(row),
            phases=self.map_phases(row),
            controllers=self.map_controllers(row),
            equipment=self.map_equipment(row),
        )

    def map_name(self, row):
        return self._required_field(row, "capacitor", "DistributionCapacitor")

    def map_bus(self, row):
        bus_name = self._required_field(
            row,
            "bus",
            f"DistributionCapacitor '{self.map_name(row)}'",
        )
        return self._required_component(
            DistributionBus,
            bus_name,
            f"DistributionCapacitor '{self.map_name(row)}'",
        )

    def map_phases(self, row):
        phases = row["phase"]
        if phases is None:
            phases = ["A", "B", "C"]
        else:
            phases = phases.split(",")
        return [phase_mapper[phase] for phase in phases]

    def map_controllers(self, row):
        return []

    def map_equipment(self, row):
        mapper = CapacitorEquipmentMapper(self.system)
        equipment = mapper.parse(row)
        return equipment
