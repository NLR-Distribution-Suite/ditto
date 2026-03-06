from gdm.distribution.components import DistributionLoad, DistributionBus

from ditto.readers.cim_iec_61968_13.equipment.load_equipment import LoadEquipmentMapper
from ditto.readers.cim_iec_61968_13.cim_mapper import CimMapper
from ditto.readers.cim_iec_61968_13.common import phase_mapper


class DistributionLoadMapper(CimMapper):
    def __init__(self, system):
        super().__init__(system)

    def parse(self, row):
        return DistributionLoad(
            name=self.map_name(row),
            bus=self.map_bus(row),
            phases=self.map_phases(row),
            equipment=self.map_equipment(row),
        )

    def map_name(self, row):
        return self._required_field(row, "load", "DistributionLoad")

    def map_bus(self, row):
        bus_name = self._required_field(row, "bus", f"DistributionLoad '{self.map_name(row)}'")
        return self._required_component(
            DistributionBus,
            bus_name,
            f"DistributionLoad '{self.map_name(row)}'",
        )

    def map_phases(self, row):
        bus_name = self._required_field(row, "bus", f"DistributionLoad '{self.map_name(row)}'")
        bus = self._required_component(
            DistributionBus,
            bus_name,
            f"DistributionLoad '{self.map_name(row)}'",
        )
        phases = row["phase"]

        if phases is None:
            phases = ["A", "B", "C"]
        else:
            phases = phases.split(",")
        phases = [phase_mapper[phase] for phase in phases]

        if row["grounded"] == "false" and len(phases) == 1:
            diff = list(set(bus.phases).difference(phases))
            if diff:
                phases.append(sorted(diff)[0].value)
        return phases

    def map_equipment(self, row):
        mapper = LoadEquipmentMapper(self.system)
        equipment = mapper.parse(row)
        return equipment
