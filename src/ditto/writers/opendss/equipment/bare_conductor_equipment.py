from gdm.distribution import DistributionSystem
from infrasys import Component

from ditto.writers.opendss.opendss_mapper import OpenDSSMapper
from ditto.enumerations import OpenDSSFileTypes


class BareConductorEquipmentMapper(OpenDSSMapper):
    def __init__(self, model: Component, system: DistributionSystem):
        super().__init__(model, system)

    altdss_name = "WireData"
    altdss_composition_name = None
    opendss_file = OpenDSSFileTypes.WIRES_FILE.value

    def map_name(self):
        self.opendss_dict["Name"] = self.get_opendss_safe_name(self.model.name)

    def map_conductor_diameter(self):
        self.opendss_dict["Radius"] = self.model.conductor_diameter.magnitude / 2
        rad_units = str(self.model.conductor_diameter.units)
        if rad_units not in self.length_units_map:
            raise ValueError(f"{rad_units} not mapped for OpenDSS")
        self.opendss_dict["RadUnits"] = self.length_units_map[rad_units]

    def map_conductor_gmr(self):
        self.opendss_dict["GMRAC"] = self.model.conductor_gmr.magnitude
        gmr_units = str(self.model.conductor_gmr.units)
        if gmr_units not in self.length_units_map:
            raise ValueError(f"{gmr_units} not mapped for OpenDSS")
        self.opendss_dict["GMRUnits"] = self.length_units_map[gmr_units]

    def map_ac_resistance(self):
        resistance = self.model.ac_resistance.to("ohms/km")
        self.opendss_dict["RAC"] = resistance.magnitude
        self.opendss_dict["RUnits"] = "km"

    def map_dc_resistance(self):
        resistance = self.model.dc_resistance.to("ohms/km")
        self.opendss_dict["RDC"] = resistance.magnitude
        self.opendss_dict["RUnits"] = "km"

    def map_ampacity(self):
        ampacity_amps = self.model.ampacity.to("ampere")
        self.opendss_dict["NormAmps"] = ampacity_amps.magnitude

    def map_emergency_ampacity(self):
        ampacity_amps = self.model.ampacity.to("ampere")
        self.opendss_dict["EmergAmps"] = ampacity_amps.magnitude
