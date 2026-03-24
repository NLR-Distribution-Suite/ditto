from gdm.distribution.components import DistributionBus
from gdm.distribution.common import VoltageLimitSet
from gdm.quantities import Voltage
from infrasys.location import Location
from gdm.distribution.enums import (
    VoltageTypes,
    LimitType,
)

from ditto.readers.cim_iec_61968_13.cim_mapper import CimMapper
from ditto.readers.cim_iec_61968_13.common import phase_mapper


class DistributionBusMapper(CimMapper):
    def __init__(self, system):
        super().__init__(system)

    def parse(self, row):
        phases = row["phase"].split(",")
        self.n_phase = len(phases)
        return DistributionBus(
            name=self.map_name(row),
            coordinate=self.map_coordinate(row),
            rated_voltage=self.map_rated_voltage(row),
            phases=self.map_phases(row),
            voltagelimits=self.map_voltagelimits(row),
            voltage_type=self.map_voltage_type(row),
        )

    def map_name(self, row):
        return row["bus"]

    def map_coordinate(self, row):
        X, Y = row["x"], row["y"]
        crs = None
        location = Location(x=X, y=Y, crs=crs)
        return location

    # Nominal voltage is only defined by transformers
    def map_rated_voltage(self, row):
        return Voltage(float(row["rated_voltage"]) / 1.732, "volt")

    def map_phases(self, row):
        phases = row["phase"].split(",")
        all_phases = [phase_mapper[phase] for phase in phases]
        return all_phases

    def map_voltagelimits(self, row):
        return [
            VoltageLimitSet(
                limit_type=LimitType.MIN,
                value=Voltage(float(row["rated_voltage"]) * 0.95, "volt"),
            ),
            VoltageLimitSet(
                limit_type=LimitType.MAX,
                value=Voltage(float(row["rated_voltage"]) * 1.05, "volt"),
            ),
        ]

    def map_voltage_type(self, row):
        return VoltageTypes.LINE_TO_GROUND.value
