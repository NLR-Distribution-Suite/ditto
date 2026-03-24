from gdm.distribution.controllers import RegulatorController
from gdm.distribution.components import DistributionBus
from gdm.quantities import Voltage
from infrasys.quantities import Time

from ditto.readers.cim_iec_61968_13.cim_mapper import CimMapper
from ditto.readers.cim_iec_61968_13.common import phase_mapper


class RegulatorControllerMapper(CimMapper):
    def __init__(self, system):
        super().__init__(system)

    def parse(self, row):
        return RegulatorController(
            name=self.map_name(row),
            delay=self.map_delay(row),
            v_setpoint=self.map_vsetpoint(row),
            min_v_limit=self.min_v_limit(row),
            max_v_limit=self.max_v_limit(row),
            pt_ratio=self.map_pt_ratio(row),
            use_ldc=self.map_use_ldc(row),
            is_reversible=self.map_is_reversible(row),
            ldc_R=self.map_ldc_R(row),
            ldc_X=self.map_ldc_X(row),
            ct_primary=self.map_ct_primary(row),
            max_step=self.map_max_step(row),
            bandwidth=self.map_bandwidth(row),
            controlled_bus=self.map_controlled_bus(row),
            controlled_phase=self.map_controlled_phase(row),
        )

    def map_name(self, row):
        return row["regulator"]

    def map_use_ldc(self, row):
        return row["ldc"]

    def map_is_reversible(self, row):
        return row["reversible"]

    def map_controlled_bus(self, row):
        bus_name = row["bus"]
        return self.system.get_component(component_type=DistributionBus, name=bus_name)

    def map_controlled_phase(self, row):
        return phase_mapper[row["phase"]]

    def map_delay(self, row):
        return Time(float(row["initial_delay"]), "second")

    def map_vsetpoint(self, row):
        return Voltage(float(row["target"]), "volt")

    def min_v_limit(self, row):
        return Voltage(float(row["min_voltage"]), "volt")

    def max_v_limit(self, row):
        return Voltage(float(row["max_voltage"]), "volt")

    def map_pt_ratio(self, row):
        return float(row["pt_ratio"])

    def map_ldc_R(self, row):
        return float(row["line_drop_r"])

    def map_ldc_X(self, row):
        return float(row["line_drop_x"])

    def map_ct_primary(self, row):
        return float(row["ct_rating"])

    def map_max_step(self, row):
        return 5

    def map_bandwidth(self, row):
        return Voltage(float(row["deadband"]), "volt")
