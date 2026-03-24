from gdm.distribution.components import DistributionBus
from gdm.distribution.common import VoltageLimitSet
from gdm.distribution.enums import VoltageTypes
from gdm.quantities import Voltage
from infrasys.location import Location
import opendssdirect as odd
from loguru import logger

from ditto.readers.opendss.common import PHASE_MAPPER, get_equipment_from_catalog


def get_buses(crs: str = None) -> list[DistributionBus]:
    """Function to return list of all buses in Opendss model

    Args:
        crs (str, optional): Coordinate reference system name. Defaults to None.

    Returns:
        list[DistributionBus]: list of DistributionBus objects
    """

    logger.debug("parsing bus components...")
    voltage_limit_set_catalog = {}
    location_catalog = {}
    buses = []

    for bus in odd.Circuit.AllBusNames():
        odd.Circuit.SetActiveBus(bus)
        rated_voltage = odd.Bus.kVBase()

        loc = Location(x=odd.Bus.X(), y=odd.Bus.Y(), crs=crs)
        loc = get_equipment_from_catalog(loc, location_catalog)

        voltage_lower_bound = VoltageLimitSet(
            limit_type="min",
            value=Voltage(rated_voltage * 0.95, "kilovolt"),
        )
        voltage_lower_bound = get_equipment_from_catalog(
            voltage_lower_bound, voltage_limit_set_catalog
        )
        voltage_upper_bound = VoltageLimitSet(
            limit_type="max",
            value=Voltage(rated_voltage * 1.05, "kilovolt"),
        )
        voltage_upper_bound = get_equipment_from_catalog(
            voltage_upper_bound, voltage_limit_set_catalog
        )

        limitsets = [voltage_lower_bound, voltage_upper_bound]
        buses.append(
            DistributionBus.model_construct(
                voltage_type=VoltageTypes.LINE_TO_GROUND.value,
                name=bus,
                rated_voltage=Voltage(rated_voltage, "kilovolt"),
                phases=[PHASE_MAPPER[str(node)] for node in odd.Bus.Nodes()],
                coordinate=loc,
                voltagelimits=limitsets,
            )
        )
    return buses
