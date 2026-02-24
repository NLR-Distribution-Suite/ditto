from gdm.distribution.components import DistributionBus, DistributionTransformer
from gdm.distribution.enums import Phase

from ditto.readers.cim_iec_61968_13.equipment.distribution_transformer_equipment import (
    DistributionTransformerEquipmentMapper,
)
from ditto.readers.cim_iec_61968_13.cim_mapper import CimMapper


class DistributionTransformerMapper(CimMapper):
    def __init__(self, system):
        super().__init__(system)

    def parse(self, row):
        return DistributionTransformer(
            name=self.map_name(row),
            buses=self.map_bus(row),
            equipment=self.map_equipment(row),
            winding_phases=self.map_winding_phases(row),
        )

    def map_name(self, row):
        return self._required_field(row, "xfmr", "DistributionTransformer")

    def _infer_winding_phases(self, row, winding_index: int):
        phase_key = f"wdg_{winding_index}_phase"
        if phase_key in row and row[phase_key] is not None:
            phase_text = str(row[phase_key]).replace("N", "")
            return [Phase[phase] for phase in phase_text if phase in {"A", "B", "C"}]

        bus_name = row.get(f"bus_{winding_index}") if hasattr(row, "get") else None
        if bus_name is None:
            return [Phase.A, Phase.B, Phase.C]

        try:
            bus = self.system.get_component(DistributionBus, bus_name)
        except Exception:
            bus = None
        if bus is None:
            return [Phase.A, Phase.B, Phase.C]

        bus_voltage = bus.rated_voltage.to("volt").magnitude
        winding_voltage = float(row.get(f"wdg_{winding_index}_rated_voltage", 0.0))
        if bus_voltage <= 0.0 or winding_voltage <= 0.0:
            return [Phase.A, Phase.B, Phase.C]

        ratio = winding_voltage / bus_voltage
        if 1.45 <= ratio <= 2.05:
            return [Phase.A, Phase.B, Phase.C]
        return [Phase.A]

    def map_winding_phases(self, row):
        return [self._infer_winding_phases(row, 1), self._infer_winding_phases(row, 2)]

    def map_bus(self, row):
        transformer_name = self.map_name(row)
        bus_1_name = self._required_field(
            row,
            "bus_1",
            f"DistributionTransformer '{transformer_name}'",
        )
        bus_2_name = self._required_field(
            row,
            "bus_2",
            f"DistributionTransformer '{transformer_name}'",
        )
        bus_1 = self._required_component(
            DistributionBus,
            bus_1_name,
            f"DistributionTransformer '{transformer_name}'",
        )
        bus_2 = self._required_component(
            DistributionBus,
            bus_2_name,
            f"DistributionTransformer '{transformer_name}'",
        )
        return [bus_1, bus_2]

    def map_equipment(self, row):
        xfmr_equip_mapper = DistributionTransformerEquipmentMapper(self.system)
        xfmr_equip = xfmr_equip_mapper.parse(row)
        return xfmr_equip
