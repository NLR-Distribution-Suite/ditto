from ditto.writers.opendss.opendss_mapper import OpenDSSMapper
from ditto.enumerations import OpenDSSFileTypes


class ConcentricCableEquipmentMapper(OpenDSSMapper):
    def __init__(self, model):
        super().__init__(model)

    altdss_name = "CNData"
    altdss_composition_name = None
    opendss_file = OpenDSSFileTypes.CABLES_FILE.value

    def map_name(self):
        self.opendss_dict["Name"] = self.get_opendss_safe_name(self.model.name)

    def map_strand_diameter(self):
        self.opendss_dict["DiaStrand"] = self.model.strand_diameter.magnitude

    def map_conductor_diameter(self):
        self.opendss_dict["Radius"] = self.model.conductor_diameter.magnitude / 2
        rad_units = str(self.model.conductor_diameter.units)
        if rad_units not in self.length_units_map:
            raise ValueError(f"{rad_units} not mapped for OpenDSS")
        self.opendss_dict["RadUnits"] = self.length_units_map[rad_units]

    def map_cable_diameter(self):
        self.opendss_dict["DiaCable"] = self.model.cable_diameter.magnitude

    def map_insulation_thickness(self):
        self.opendss_dict["InsLayer"] = self.model.insulation_thickness.magnitude

    def map_insulation_diameter(self):
        self.opendss_dict["DiaIns"] = self.model.insulation_diameter.magnitude

    def map_ampacity(self):
        ampacity_amps = self.model.ampacity.to("ampere")
        self.opendss_dict["NormAmps"] = ampacity_amps.magnitude

    def map_conductor_gmr(self):
        gmr = self.model.conductor_gmr.magnitude
        self.opendss_dict["GMRAC"] = gmr
        gmr_units = str(self.model.conductor_gmr.units)
        if gmr_units not in self.length_units_map:
            raise ValueError(f"{gmr_units} not mapped for OpenDSS")
        self.opendss_dict["GMRUnits"] = self.length_units_map[gmr_units]

    def map_strand_gmr(self):
        self.opendss_dict["GMRStrand"] = self.model.strand_gmr.magnitude
    def map_phase_ac_resistance(self):
        resistance = self.model.phase_ac_resistance.to("ohms/km")
        self.opendss_dict["RAC"] = resistance.magnitude
        self.opendss_dict["RUnits"] = "km"

    def map_strand_ac_resistance(self):
        resistance = self.model.strand_ac_resistance.to("ohms/km")
        self.opendss_dict["RStrand"] = resistance.magnitude
        self.opendss_dict["RUnits"] = "km"

    def map_num_neutral_strands(self):
        self.opendss_dict["k"] = self.model.num_neutral_strands

    def map_rated_voltage(self):
        pass

    def map_insulation(self):
        pass

    def map_loading_limit(self):
        # Not mapped in OpenDSS
        pass
