from gdm.distribution.equipment.distribution_transformer_equipment import (
    DistributionTransformerEquipment,
)
from gdm.distribution.common import SequencePair

from ditto.readers.cim_iec_61968_13.equipment.winding_equipment import WindingEquipmentMapper
from ditto.readers.cim_iec_61968_13.cim_mapper import CimMapper


class DistributionTransformerEquipmentMapper(CimMapper):
    def __init__(self, system):
        super().__init__(system)

    def parse(self, row):
        self.s = float(row["wdg_1_apparent_power"])
        self.v_h = float(row["wdg_1_rated_voltage"])
        self.v_l = float(row["wdg_2_rated_voltage"])
        self.r_h = float(row["wdg_1_per_resistance"])
        self.r_l = float(row["wdg_2_per_resistance"])

        self.per_r_1 = self.r_h / (self.v_h**2 / self.s) * 100
        self.per_r_2 = self.r_l / (self.v_l**2 / self.s) * 100

        return DistributionTransformerEquipment(
            name=self.map_name(row),
            pct_no_load_loss=self.map_pct_no_load_loss(row),
            pct_full_load_loss=self.map_pct_full_load_loss(row),
            windings=self.map_windings(row),
            coupling_sequences=self.map_coupling_sequences(row),
            winding_reactances=self.map_winding_reactances(row),
            is_center_tapped=self.map_is_center_tapped(row),
        )

    def map_name(self, row):
        return row["xfmr"] + "_equipment"

    def map_pct_no_load_loss(self, row):
        return 0

    def map_pct_full_load_loss(self, row):
        return self.per_r_1 + self.per_r_2

    def map_windings(self, row):
        mapper = WindingEquipmentMapper(self.system)
        wingings = mapper.parse(row)
        return wingings

    def map_coupling_sequences(self, row):
        return [SequencePair(1, 2)]

    def map_winding_reactances(self, row):
        if "x0" in row and "x1" in row:
            x0 = float(row["x0"])
            x1 = float(row["x1"])
            x_hl = 1 / 3 * (2 * x1 + x0)
            per_x = x_hl / (self.v_h**2 / self.s) * 100

            return [per_x]

        if "wdg_1_z_1_leakage" in row and "wdg_1_z_0_leakage" in row:
            z1 = row["wdg_1_z_1_leakage"]
            z0 = row["wdg_1_z_0_leakage"]
            if z1 is not None and z0 is not None:
                x_hl = (2 * float(z1) + float(z0)) / 3
                per_x = x_hl / (self.v_h**2 / self.s) * 100
                return [per_x]

        if "wdg_2_z_1_leakage" in row and "wdg_2_z_0_leakage" in row:
            z1 = row["wdg_2_z_1_leakage"]
            z0 = row["wdg_2_z_0_leakage"]
            if z1 is not None and z0 is not None:
                x_hl = (2 * float(z1) + float(z0)) / 3
                per_x = x_hl / (self.v_h**2 / self.s) * 100
                return [per_x]

        return [0.01]

    def map_is_center_tapped(self, row):
        return False
