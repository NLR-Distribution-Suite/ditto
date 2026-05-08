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

    def _bus_is_used(self) -> bool:
        """Check if this bus is referenced by any component in the system.

        A bus is considered 'unused' (and should be skipped) only if:
        - It's an orphaned intermediate bus created during parallel serialization
        - These typically have names like "67_1_3" created from multi-phase bus splits
        - AND it's not referenced by any actual component

        A bus is 'used' if:
        - It's referenced by any non-DistributionBus component
        - OR it has a simple name (no intermediate split pattern)
        """
        bus_name = self.model.name

        # Check if this bus is referenced by other components
        for component_type in self.system.get_component_types():
            # Skip DistributionBus components in the check to avoid circular references
            if component_type.__name__ == "DistributionBus":
                continue

            for component in self.system.get_components(component_type):
                if hasattr(component, "buses"):
                    for bus in component.buses:
                        if bus.name == bus_name:
                            return True
                elif hasattr(component, "bus") and component.bus is not None:
                    if component.bus.name == bus_name:
                        return True

        # If not referenced by components, check if it looks like an intermediate split bus
        # Intermediate buses from parallel serialization have patterns like "67_1_3" or "XYZ_0_2"
        # Real buses typically don't have this pattern
        # If it doesn't match the orphan pattern, consider it used
        parts = bus_name.split("_")
        # If bus has 2+ underscores and middle parts are single digits, it's likely intermediate
        if len(parts) >= 3 and all(p.isdigit() and len(p) == 1 for p in parts[1:-1]):
            # This looks like an intermediate bus (e.g., "67_1_3") - mark as unused
            return False

        # Otherwise consider it used (e.g., standalone buses or normal named buses)
        return True

    def populate_opendss_dictionary(self):
        """Skip writing coordinates for unused intermediate buses created during serialization."""
        if not self._bus_is_used():
            # Return empty dict so this bus doesn't get written to BusCoords.dss
            return
        super().populate_opendss_dictionary()

    def map_name(self):
        self.opendss_dict["Name"] = self.get_opendss_safe_name(self.model.name)

    def map_coordinate(self):
        if hasattr(self.model.coordinate, "x"):
            self.opendss_dict["X"] = self.model.coordinate.x
        if hasattr(self.model.coordinate, "y"):
            self.opendss_dict["Y"] = self.model.coordinate.y

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
