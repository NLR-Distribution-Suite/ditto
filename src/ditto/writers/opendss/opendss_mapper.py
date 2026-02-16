from abc import ABC, abstractmethod

from gdm.distribution import DistributionSystem
from infrasys import Component


# TODO: Define a BaseMapper class one level up from this?
class OpenDSSMapper(ABC):
    phase_map = {"A": ".1", "B": ".2", "C": ".3", "N": ".0", "S1": ".1", "S2": ".2"}
    length_units_map = {
        "meter": "m",
        "mile": "mi",
        "feet": "ft",
        "foot": "ft",
        "kilometer": "km",
        "inch": "in",
        "centimeter": "cm",
        "millimeter": "mm",
    }
    connection_map = {"STAR": "wye", "DELTA": "delta", "OPEN_DELTA": "delta", "OPEN_STAR": "wye"}

    def __init__(self, model: Component, system: DistributionSystem):
        self.model = model
        self.system = system
        self.opendss_dict = {}
        self.substation = ""
        self.feeder = ""

        @property
        @abstractmethod
        def opendss_file():
            """Return the OpenDSS file."""
            pass

        @property
        @abstractmethod
        def altdss_name():
            """Return the name of the AltDSS class which defines the object."""
            pass

        @property
        @abstractmethod
        def altdss_composition_name():
            """Return the name of the AltDSS class which constructs the object through composition"""
            pass

    def map_common(self):
        return

    def map_uuid(self):
        return

    def map_system_uuid(self):
        return

    def map_substation(self):
        if hasattr(self.model, "substation") and self.model.substation is not None:
            self.substation = self.model.substation.name

    def map_feeder(self):
        if hasattr(self.model, "feeder") and self.model.feeder is not None:
            self.feeder = self.model.feeder.name

    def populate_opendss_dictionary(self):
        # Should not be populating an existing dictionary. Assert error if not empty
        assert len(self.opendss_dict) == 0
        self.map_common()
        for field in type(self.model).model_fields:
            mapping_function = getattr(self, "map_" + field)
            mapping_function()

    def get_profile_name(self, component):
        profiles = self.system.list_time_series(component)
        profile_data = []
        for profile in profiles:
            profile_data.append(
                {
                    "profile": profile,
                    "metadata": self.system.list_time_series_metadata(component, profile.name),
                }
            )
        if profile_data:
            metadata = profile_data[0]["metadata"]
            if metadata[0] and "profile_name" in metadata[0].features:
                profile_name = metadata[0].features["profile_name"]
            else:
                profile_name = str(self.model.uuid)

            return profile_name
