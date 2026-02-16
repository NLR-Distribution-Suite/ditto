from gdm.distribution.controllers import RegulatorController
from gdm.distribution import DistributionSystem

from ditto.writers.opendss.opendss_mapper import OpenDSSMapper
from ditto.enumerations import OpenDSSFileTypes


class RegulatorControllerMapper(OpenDSSMapper):
    altdss_name = "RegControl"
    # altdss_composition_name = "RegControl"
    altdss_composition_name = None
    opendss_file = OpenDSSFileTypes.REGULATOR_CONTROLLERS_FILE.value

    def __init__(self, model: RegulatorController, xfmr_name: str, system: DistributionSystem):
        super().__init__(model, system)
        self.model: RegulatorController = model
        self.xfmr_name = xfmr_name

    def map_name(self):
        self.opendss_dict["Name"] = self.get_opendss_safe_name(self.model.name)
        self.opendss_dict["Transformer"] = self.get_opendss_safe_name(self.xfmr_name)

    def map_delay(self):
        self.opendss_dict["TapDelay"] = self.model.delay.to("s").magnitude

    def map_v_setpoint(self):
        self.opendss_dict["VReg"] = self.model.v_setpoint.to("volts").magnitude

    def map_min_v_limit(self):
        self.model.min_v_limit.to("volts").magnitude

    def map_max_v_limit(self):
        self.model.max_v_limit.to("volts").magnitude

    def map_pt_ratio(self):
        self.opendss_dict["PTRatio"] = self.model.pt_ratio

    def map_use_ldc(self):
        ...

    def map_is_reversible(self):
        self.opendss_dict["Reversible"] = self.model.is_reversible

    def map_ldc_R(self):
        self.opendss_dict["R"] = self.model.ldc_R.to("volts").magnitude

    def map_ldc_X(self):
        self.opendss_dict["X"] = self.model.ldc_X.to("volts").magnitude

    def map_ct_primary(self):
        self.opendss_dict["CTPrim"] = self.model.ct_primary.to("ampere").magnitude

    def map_max_step(self):
        self.opendss_dict["MaxTapChange"] = self.model.max_step

    def map_bandwidth(self):
        self.opendss_dict["Band"] = self.model.bandwidth.to("volts").magnitude

    def map_controlled_bus(self):
        self.opendss_dict[
            "Bus"
        ] = f"{self.get_opendss_safe_name(self.model.controlled_bus.name)}{self.phase_map[self.model.controlled_phase]}"

    def map_controlled_phase(self):
        ...
