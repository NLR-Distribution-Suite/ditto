from gdm.distribution.controllers.distribution_capacitor_controller import (
    VoltageCapacitorController,
)
from gdm.distribution import DistributionSystem

from ditto.writers.opendss.opendss_mapper import OpenDSSMapper
from ditto.enumerations import OpenDSSFileTypes


class VoltageCapacitorControllerMapper(OpenDSSMapper):
    altdss_name = "CapControl"
    altdss_composition_name = None
    opendss_file = OpenDSSFileTypes.CAPACITOR_CONTROLLERS_FILE.value

    def __init__(
        self,
        model: VoltageCapacitorController,
        capacitor_name: str,
        system: DistributionSystem,
    ):
        super().__init__(model, system)
        self.model: VoltageCapacitorController = model
        self.capacitor_name = capacitor_name

    def map_name(self):
        self.opendss_dict["Name"] = self.model.name
        self.opendss_dict["Element"] = f"Capacitor.{self.capacitor_name}"
        self.opendss_dict["Terminal"] = 1
        self.opendss_dict["Capacitor"] = self.capacitor_name
        self.opendss_dict["Type"] = "Voltage"

    def map_on_voltage(self):
        self.opendss_dict["OnSetting"] = self.model.on_voltage.to("volts").magnitude

    def map_off_voltage(self):
        self.opendss_dict["OffSetting"] = self.model.off_voltage.to("volts").magnitude

    def map_pt_ratio(self):
        self.opendss_dict["PTRatio"] = self.model.pt_ratio

    def map_delay_on(self):
        if self.model.delay_on is not None:
            self.opendss_dict["Delay"] = self.model.delay_on.to("s").magnitude

    def map_delay_off(self):
        if self.model.delay_off is not None:
            self.opendss_dict["DelayOff"] = self.model.delay_off.to("s").magnitude

    def map_dead_time(self):
        if self.model.dead_time is not None:
            self.opendss_dict["DeadTime"] = self.model.dead_time.to("s").magnitude
