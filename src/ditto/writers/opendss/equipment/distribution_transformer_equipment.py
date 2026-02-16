from gdm.distribution import DistributionSystem
from infrasys import Component


from ditto.writers.opendss.opendss_mapper import OpenDSSMapper
from ditto.enumerations import OpenDSSFileTypes


class DistributionTransformerEquipmentMapper(OpenDSSMapper):
    def __init__(self, model: Component, system: DistributionSystem):
        super().__init__(model, system)

    altdss_name = "XfmrCode_X12X13X23"
    altdss_composition_name = "XfmrCode"
    opendss_file = OpenDSSFileTypes.TRANSFORMERS_FILE.value

    def map_name(self):
        self.opendss_dict["Name"] = self.get_opendss_safe_name(self.model.name)

    def map_pct_no_load_loss(self):
        self.opendss_dict["pctNoLoadLoss"] = self.model.pct_no_load_loss

    def map_pct_full_load_loss(self):
        self.opendss_dict["pctLoadLoss"] = self.model.pct_full_load_loss

    def map_windings(self):
        kvs = []
        pctRs = []
        kVAs = []
        conns = []
        taps = []
        min_tap = []
        max_tap = []
        num_taps = []
        # TODO: Add TapWindingEquipment
        for i in range(len(self.model.windings)):
            winding = self.model.windings[i]
            tap_pu = winding.tap_positions
            taps.append(tap_pu[0])
            min_tap.append(winding.min_tap_pu)
            max_tap.append(winding.max_tap_pu)
            num_taps.append(winding.total_taps)

            num_phases = winding.num_phases
            # rated_voltage
            nom_voltage = winding.rated_voltage.to("kV").magnitude
            voltage_type = winding.voltage_type
            connection_type = winding.connection_type
            nom_voltage = nom_voltage if voltage_type == "line-to-ground" else nom_voltage / 1.732
            kvs.append(
                nom_voltage
                if num_phases == 1 and connection_type != "DELTA"
                else nom_voltage * 1.732
            )
            # resistance
            pctRs.append(winding.resistance)
            # rated_power
            kVAs.append(winding.rated_power.to("kva").magnitude)
            # connection_type
            conns.append(self.connection_map[connection_type])
            # TODO: num_phases and is_grounded aren't included
            if self.model.is_center_tapped and i == len(self.model.windings):
                kvs.append(nom_voltage)
                pctRs.append(winding.resistance)
                kVAs.append(winding.rated_power.to("kVa").magnitude)
                conns.append(self.connection_map[winding.connection_type])
        self.opendss_dict["kV"] = kvs
        self.opendss_dict["pctR"] = pctRs
        self.opendss_dict["kVA"] = kVAs
        self.opendss_dict["Conn"] = conns
        for x, x_value in zip(["X12", "X23", "X13"], self.model.winding_reactances):
            self.opendss_dict[x] = x_value
        self.opendss_dict["Phases"] = num_phases
        self.opendss_dict["Tap"] = taps
        self.opendss_dict["Tap"] = taps
        self.opendss_dict["MinTap"] = min_tap
        self.opendss_dict["MaxTap"] = max_tap
        self.opendss_dict["NumTaps"] = num_taps
        pass

    def map_coupling_sequences(self):
        # Used to know the reactance couplings
        pass

    def map_winding_reactances(self):
        for i in range(len(self.model.coupling_sequences)):
            coupling_sequence = self.model.coupling_sequences[i]
            reactance = self.model.winding_reactances[i]
            first = coupling_sequence[0] + 1
            second = coupling_sequence[1] + 1
            reactance_name = "X" + str(first) + str(second)
            self.opendss_dict[reactance_name] = reactance

    def map_is_center_tapped(self):
        pass  # Used on buses

    def map_mounting(self):
        pass
