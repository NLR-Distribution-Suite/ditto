from gdm.distribution.components import MatrixImpedanceBranch, DistributionBus
from gdm.distribution.equipment import MatrixImpedanceBranchEquipment
from gdm.quantities import Distance

from ditto.readers.cim_iec_61968_13.cim_mapper import CimMapper
from ditto.readers.cim_iec_61968_13.common import phase_mapper


class MatrixImpedanceBranchMapper(CimMapper):
    def __init__(self, system):
        super().__init__(system)

    def parse(self, row):
        return MatrixImpedanceBranch(
            name=self.map_name(row),
            buses=self.map_buses(row),
            length=self.map_length(row),
            phases=self.map_phases(row),
            equipment=self.map_equipment(row),
        )

    def map_name(self, row):
        return self._required_field(row, "line", "MatrixImpedanceBranch")

    def map_buses(self, row):
        line_name = self.map_name(row)
        bus_1_name = self._required_field(row, "bus_1", f"MatrixImpedanceBranch '{line_name}'")
        bus_2_name = self._required_field(row, "bus_2", f"MatrixImpedanceBranch '{line_name}'")
        bus_1 = self._required_component(
            DistributionBus,
            bus_1_name,
            f"MatrixImpedanceBranch '{line_name}'",
        )
        bus_2 = self._required_component(
            DistributionBus,
            bus_2_name,
            f"MatrixImpedanceBranch '{line_name}'",
        )
        return [bus_1, bus_2]

    def map_length(self, row):
        length = float(row["length"])
        return Distance(length, "m")

    def map_phases(self, row):
        phases = row["phases_1"].split(",")
        return [phase_mapper[phase] for phase in phases]

    def map_equipment(self, row):
        line_name = self.map_name(row)
        line_code = self._required_field(
            row,
            "line_code",
            f"MatrixImpedanceBranch '{line_name}'",
        )
        return self._required_component(
            MatrixImpedanceBranchEquipment,
            line_code,
            f"MatrixImpedanceBranch '{line_name}'",
        )
