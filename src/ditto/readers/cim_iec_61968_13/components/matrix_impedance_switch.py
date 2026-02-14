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
        self.bus_2 = self.system.get_component(DistributionBus, row["bus_2"])
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
        return [state] * 3

    def map_name(self, row):
        return row["switch_name"]

    def map_buses(self, row):
        bus_1_name = row["bus_1"]
        bus_1 = self.system.get_component(DistributionBus, bus_1_name)
        bus_2_name = row["bus_2"]
        bus_2 = self.system.get_component(DistributionBus, bus_2_name)
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
            raise Exception(
                "No Matrix Impedance Branch Equipment found with {} phases".format(self.n_phases)
            )
