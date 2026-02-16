from gdm.distribution import DistributionSystem
from infrasys import Component


from ditto.writers.opendss.opendss_mapper import OpenDSSMapper
from ditto.enumerations import OpenDSSFileTypes


class SequenceImpedanceBranchEquipmentMapper(OpenDSSMapper):
    def __init__(self, model: Component, system: DistributionSystem):
        super().__init__(model, system)

    altdss_name = "LineCode_Z0Z1C0C1"
    altdss_composition_name = "LineCode"
    opendss_file = OpenDSSFileTypes.LINECODES_FILE.value

    def map_name(self):
        self.opendss_dict["Name"] = self.get_opendss_safe_name(self.model.name)

    def map_common(self):
        self.opendss_dict["Units"] = "km"

    # TODO: Do we need to add NPhases? This might be very important for secondary lines.

    def map_pos_seq_resistance(self):
        pos_seq_resistance_ohms = self.model.pos_seq_resistance.to("ohm/km")
        self.opendss_dict["R1"] = pos_seq_resistance_ohms.magnitude

    def map_zero_seq_resistance(self):
        zero_seq_resistance_ohms = self.model.zero_seq_resistance.to("ohm/km")
        self.opendss_dict["R0"] = zero_seq_resistance_ohms.magnitude

    def map_pos_seq_reactance(self):
        pos_seq_reactance_ohms = self.model.pos_seq_reactance.to("ohm/km")
        self.opendss_dict["X1"] = pos_seq_reactance_ohms.magnitude

    def map_zero_seq_reactance(self):
        zero_seq_reactance_ohms = self.model.zero_seq_reactance.to("ohm/km")
        self.opendss_dict["X0"] = zero_seq_reactance_ohms.magnitude

    def map_pos_seq_capacitance(self):
        pos_seq_capacitance_nf = self.model.pos_seq_capacitance.to("nanofarad/km")
        self.opendss_dict["C1"] = pos_seq_capacitance_nf.magnitude

    def map_zero_seq_capacitance(self):
        zero_seq_capacitance_nf = self.model.zero_seq_capacitance.to("nanofarad/km")
        self.opendss_dict["C0"] = zero_seq_capacitance_nf.magnitude

    def map_ampacity(self):
        ampacity_amps = self.model.ampacity.to("ampere")
        self.opendss_dict["NormAmps"] = ampacity_amps.magnitude
