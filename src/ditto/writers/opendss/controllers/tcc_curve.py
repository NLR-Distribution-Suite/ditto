"""Writer for TCC_Curve objects used by recloser controllers."""

from gdm.distribution.common.curve import TimeCurrentCurve
from gdm.distribution import DistributionSystem

from ditto.writers.opendss.opendss_mapper import OpenDSSMapper
from ditto.enumerations import OpenDSSFileTypes


class TimeCurrentCurveMapper(OpenDSSMapper):
    """Maps a GDM TimeCurrentCurve to an OpenDSS TCC_Curve object."""

    altdss_name = "TCC_Curve"
    altdss_composition_name = None
    opendss_file = OpenDSSFileTypes.TCC_CURVES_FILE.value

    def __init__(self, model: TimeCurrentCurve, system: DistributionSystem):
        super().__init__(model, system)
        self.model: TimeCurrentCurve = model

    def map_name(self):
        self.opendss_dict["Name"] = self.model.name

    def map_curve_x(self):
        # curve_x is Current (amperes) -> maps to C_Array in OpenDSS TCC_Curve
        c_vals = self.model.curve_x.to("ampere").magnitude
        if hasattr(c_vals, "tolist"):
            c_vals = c_vals.tolist()
        else:
            c_vals = list(c_vals)
        self.opendss_dict["C_Array"] = c_vals

    def map_curve_y(self):
        # curve_y is Time (seconds) -> maps to T_Array in OpenDSS TCC_Curve
        t_vals = self.model.curve_y.to("second").magnitude
        if hasattr(t_vals, "tolist"):
            t_vals = t_vals.tolist()
        else:
            t_vals = list(t_vals)
        self.opendss_dict["T_Array"] = t_vals
