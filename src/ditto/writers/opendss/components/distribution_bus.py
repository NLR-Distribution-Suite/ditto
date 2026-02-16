from ditto.writers.opendss.opendss_mapper import OpenDSSMapper
from ditto.enumerations import OpenDSSFileTypes

from gdm.distribution import DistributionSystem
from infrasys import Component


class DistributionBusMapper(OpenDSSMapper):
    def __init__(self, model: Component, system: DistributionSystem):
        super().__init__(model, system)

    altdss_name = "Bus"
    altdss_composition_name = None
    opendss_file = OpenDSSFileTypes.COORDINATE_FILE.value

    def map_name(self):
        self.opendss_dict["Name"] = self.get_opendss_safe_name(self.model.name)

    def map_coordinate(self):
        if hasattr(self.model.coordinate, "x"):
            self.opendss_dict["X"] = self.model.coordinate.y
        if hasattr(self.model.coordinate, "y"):
            self.opendss_dict["Y"] = self.model.coordinate.x

    def map_rated_voltage(self):
        kv_rated_voltage = self.model.rated_voltage.to("kV")
        if self.model.voltage_type == "line-to-ground":
            self.opendss_dict["kVLN"] = kv_rated_voltage.magnitude
        elif self.model.voltage_type == "line-to-line":
            self.opendss_dict["kVLL"] = kv_rated_voltage.magnitude

    def map_phases(self):
        # Not mapped for OpenDSS buses in BusCoords.dss files
        return

    def map_voltagelimits(self):
        # Not mapped for OpenDSS buses in BusCoords.dss files
        return

    def map_voltage_type(self):
        # Handled in map_rated_voltage
        return

    def map_in_service(self):
        return
