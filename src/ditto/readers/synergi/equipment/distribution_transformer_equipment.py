from ditto.readers.synergi.synergi_mapper import SynergiMapper
from ditto.readers.synergi.equipment.winding_equipment import WindingEquipmentMapper
from gdm.distribution.equipment.distribution_transformer_equipment import DistributionTransformerEquipment

from gdm.distribution.enums import Phase, ConnectionType
from gdm.distribution.common import SequencePair



class DistributionTransformerEquipmentMapper(SynergiMapper):
    def __init__(self, system):
        super().__init__(system)

    synergi_table = "DevTransformers"
    synergi_database = "Equipment"

    def parse(self, row, unit_type, section_id_sections, from_node_sections, to_node_sections):
        name = self.map_name(row)
        pct_no_load_loss = self.map_pct_no_load_loss(row)
        pct_full_load_loss = self.map_pct_full_load_loss(row)
        windings = self.map_windings(row)
        coupling_sequences = self.map_coupling_sequences(row)
        winding_reactances = self.map_winding_reactances(row)
        is_center_tapped = self.map_is_center_tapped(row)
        return DistributionTransformerEquipment(name=name,
                                                pct_no_load_loss=pct_no_load_loss,
                                                pct_full_load_loss=pct_full_load_loss,
                                                windings=windings,
                                                coupling_sequences=coupling_sequences,
                                                winding_reactances=winding_reactances,
                                                is_center_tapped=is_center_tapped)

    def map_name(self, row):
        return row["TransformerName"]

    def map_pct_no_load_loss(self, row):
        return row["NoLoadLosses"]

    def map_pct_full_load_loss(self, row):
        return 0

    def map_windings(self, row):
        winding1 = WindingEquipmentMapper(self.system).parse(row, 1)
        winding2 = WindingEquipmentMapper(self.system).parse(row, 2)
        return [winding1, winding2]

    def map_coupling_sequences(self, row):
        return [SequencePair(1, 2)]

    def map_winding_reactances(self, row):
        percent_impedance = row["PercentImpedance"]
        percent_resistance = row["PercentResistance"]
        x_pu = ((percent_impedance/100)**2 - (percent_resistance/100)**2)**0.5
        return [x_pu]

    def map_is_center_tapped(self, row):
        if row["HasCtrTap"] == 1:
            return True
        return False

