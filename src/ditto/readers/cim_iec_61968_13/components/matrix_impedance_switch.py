from gdm.distribution.components import MatrixImpedanceSwitch, DistributionBus
from gdm.quantities import Distance
from gdm.distribution.equipment import (
    MatrixImpedanceSwitchEquipment,
    MatrixImpedanceBranchEquipment,
)

from ditto.readers.cim_iec_61968_13.cim_mapper import CimMapper


class MatrixImpedanceSwitchMapper(CimMapper):
    def __init__(self, system):
        super().__init__(system)

    def parse(self, row):
        switch_name = self.map_name(row)
        bus_2_name = self._required_field(row, "bus_2", f"MatrixImpedanceSwitch '{switch_name}'")
        self.bus_2 = self._required_component(
            DistributionBus,
            bus_2_name,
            f"MatrixImpedanceSwitch '{switch_name}'",
        )
        self.n_phases = len(self.bus_2.phases)

        return MatrixImpedanceSwitch(
            name=self.map_name(row),
            buses=self.map_buses(row),
            length=Distance(1, "m"),
            phases=self.map_phases(row),
            equipment=self.map_equipment(row),
            is_closed=self.map_is_closed(row),
        )

    def map_is_closed(self, row):
        state = True if row["is_open"] == "false" else False
        return [state] * max(1, len(self.bus_2.phases))

    def map_name(self, row):
        return self._required_field(row, "switch_name", "MatrixImpedanceSwitch")

    def map_buses(self, row):
        switch_name = self.map_name(row)
        bus_1_name = self._required_field(
            row,
            "bus_1",
            f"MatrixImpedanceSwitch '{switch_name}'",
        )
        bus_2_name = self._required_field(
            row,
            "bus_2",
            f"MatrixImpedanceSwitch '{switch_name}'",
        )
        bus_1 = self._required_component(
            DistributionBus,
            bus_1_name,
            f"MatrixImpedanceSwitch '{switch_name}'",
        )
        bus_2 = self._required_component(
            DistributionBus,
            bus_2_name,
            f"MatrixImpedanceSwitch '{switch_name}'",
        )
        return [bus_1, bus_2]

    def map_length(self, row):
        length = float(row["length"])
        return Distance(length, "m")

    def map_phases(self, row):
        return self.bus_2.phases

    def map_equipment(self, row):
        equipments: list[MatrixImpedanceBranchEquipment] = list(
            self.system.get_components(
                MatrixImpedanceBranchEquipment,
                filter_func=lambda x: len(x.r_matrix) == self.n_phases,
            )
        )
        if len(equipments):
            model_dict = equipments[0].model_dump(exclude={"uuid"})
            equipment = MatrixImpedanceSwitchEquipment(**model_dict)
            return equipment
        else:
            raise ValueError(
                "No MatrixImpedanceBranchEquipment found for switch "
                f"'{row['switch_name']}' with {self.n_phases} phases"
            )
