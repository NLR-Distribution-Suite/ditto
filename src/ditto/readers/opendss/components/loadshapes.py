from datetime import datetime, timedelta
from enum import Enum
from gdm.distribution.components import (
    DistributionVoltageSource,
    DistributionSolar,
    DistributionLoad,
)
from infrasys.normalization import NormalizationMax, NormalizationByValue
from gdm.quantities import ActivePower, ReactivePower, Irradiance
from infrasys.time_series_models import SingleTimeSeries
from infrasys.base_quantity import BaseQuantity
from pydantic import BaseModel, ConfigDict
import opendssdirect as odd
from loguru import logger


class ObjectsWithProfile(Enum):
    """GDM models that support profiles in OpenDSS"""

    LOAD = DistributionLoad
    PV_SYSTEM = DistributionSolar
    SOURCE = DistributionVoltageSource


class ProfileBases(str, Enum):
    """Profile base (used for normalization of profiles)"""

    P_BASE = "PBase"
    Q_BASE = "QBase"


class ProfileTypes(str, Enum):
    """Profile multiplier (used for scaling profiles)"""

    P_MULT = "PMult"
    Q_MULT = "QMult"


class ProfileMap(BaseModel):
    """Profile mapping"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    quantity: type[BaseQuantity] | None
    units: str | None
    profile_type: ProfileTypes
    variable: str


profile_type_to_base_type_map = {
    ProfileTypes.P_MULT: ProfileBases.P_BASE,
    ProfileTypes.Q_MULT: ProfileBases.Q_BASE,
}

model_type_to_profile_type_map = {
    ObjectsWithProfile.LOAD: [
        ProfileMap(
            profile_type=ProfileTypes.P_MULT,
            quantity=ActivePower,
            units="kilowatt",
            variable="active_power",
        ),
        ProfileMap(
            profile_type=ProfileTypes.Q_MULT,
            quantity=ReactivePower,
            units="kilovar",
            variable="reactive_power",
        ),
    ],
    ObjectsWithProfile.PV_SYSTEM: [
        ProfileMap(
            profile_type=ProfileTypes.P_MULT,
            quantity=Irradiance,
            units="kilowatt/meter**2",
            variable="irradiance",
        ),
    ],
    ObjectsWithProfile.SOURCE: [
        ProfileMap(
            profile_type=ProfileTypes.P_MULT, quantity=None, units=None, variable="pu_voltage"
        ),
    ],
}


def build_profiles(
    profile_names: list[str], component_type: ObjectsWithProfile, profile_catalog: dict[str,]
) -> dict[str, dict[str, SingleTimeSeries]]:
    """Function to return dictionary of SingleTimeSeries objects representing load shapes in the Opendss model.

    Args:
        profile_names (list[str]): list of profile names
        component_type (ObjectsWithProfile): type of component
        profile_catalog (dict[str,]): dictionary name mapping to  SingleTimeSeries objects in the
                                      following convention:
                                      dict[profile_name, dict[profile_type, SingleTimeSeries]]

    Returns:
        dict[str, dict[str, SingleTimeSeries]]: updated profile catalog is returned
    """

    logger.debug("parsing timeseries components...")
    for profile_name in profile_names:
        if profile_name and profile_name not in profile_catalog:
            profiles = {}
            odd.LoadShape.Name(profile_name)
            for profile in model_type_to_profile_type_map[component_type]:
                profile_type = profile.profile_type
                profile_base = profile_type_to_base_type_map[profile_type]
                profile_func = getattr(odd.LoadShape, profile_type.value)
                base_func = getattr(odd.LoadShape, profile_base.value)
                data = profile_func()
                if len(data) > 1:
                    if profile.quantity:
                        data = profile.quantity(data, profile.units)
                    length = odd.LoadShape.Npts()
                    initial_time = datetime(year=2020, month=1, day=1)
                    resolution = odd.LoadShape.SInterval()
                    time_array = [
                        initial_time + timedelta(seconds=i * resolution) for i in range(length)
                    ]
                    variable_name = profile.variable

                    if odd.LoadShape.Normalize() and base_func():
                        normalization = NormalizationByValue(value=base_func())
                    elif odd.LoadShape.Normalize() and not base_func():
                        normalization = NormalizationMax()
                    else:
                        normalization = None

                    ts = SingleTimeSeries.from_time_array(
                        data, variable_name, time_array, normalization=normalization
                    )
                    profiles[profile_type.value] = {
                        "data": ts,
                        "use_actual": odd.LoadShape.UseActual(),
                    }
            profile_catalog[profile_name] = profiles

    return profile_catalog
