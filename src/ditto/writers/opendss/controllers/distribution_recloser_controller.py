from gdm.distribution.controllers.distribution_recloser_controller import (
    DistributionRecloserController,
)
from gdm.distribution import DistributionSystem

from ditto.writers.opendss.opendss_mapper import OpenDSSMapper
from ditto.enumerations import OpenDSSFileTypes


class DistributionRecloserControllerMapper(OpenDSSMapper):
    """Maps a DistributionRecloserController to an OpenDSS Recloser object.

    The Recloser element in OpenDSS is a protection device that monitors a
    Line element and can open/close it based on TCC curves.
    """

    altdss_name = "Recloser"
    altdss_composition_name = None
    opendss_file = OpenDSSFileTypes.RECLOSER_CONTROLLERS_FILE.value

    def __init__(
        self,
        model: DistributionRecloserController,
        component_name: str,
        system: DistributionSystem,
    ):
        super().__init__(model, system)
        self.model: DistributionRecloserController = model
        self.component_name = component_name

    def map_name(self):
        self.opendss_dict["Name"] = self.model.name
        # The recloser monitors the Line element it is associated with
        self.opendss_dict["MonitoredObj"] = f"Line.{self.component_name}"
        self.opendss_dict["MonitoredTerm"] = 1

    def map_delay(self):
        self.opendss_dict["Delay"] = self.model.delay.to("second").magnitude

    def map_ground_delayed(self):
        self.opendss_dict["GroundDelayed"] = self.model.ground_delayed.name

    def map_ground_fast(self):
        self.opendss_dict["GroundFast"] = self.model.ground_fast.name

    def map_phase_delayed(self):
        self.opendss_dict["PhaseDelayed"] = self.model.phase_delayed.name

    def map_phase_fast(self):
        self.opendss_dict["PhaseFast"] = self.model.phase_fast.name

    def map_num_fast_ops(self):
        self.opendss_dict["NumFast"] = self.model.num_fast_ops

    def map_num_shots(self):
        self.opendss_dict["Shots"] = self.model.num_shots

    def map_reclose_intervals(self):
        intervals = self.model.reclose_intervals.to("second").magnitude
        # Convert to list if numpy array
        if hasattr(intervals, "tolist"):
            intervals = intervals.tolist()
        else:
            intervals = list(intervals)
        self.opendss_dict["RecloseIntervals"] = intervals

    def map_reset_time(self):
        self.opendss_dict["Reset"] = self.model.reset_time.to("second").magnitude

    def map_equipment(self):
        # RecloserControllerEquipment has no OpenDSS-mapped fields
        pass
