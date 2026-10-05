from gdm.distribution import DistributionSystem
from infrasys import Component


from ditto.writers.opendss.components.distribution_branch import DistributionBranchMapper
from ditto.enumerations import OpenDSSFileTypes
from ditto.opendss_metadata import OpenDSSSwitchProperties


class MatrixImpedanceSwitchMapper(DistributionBranchMapper):
    def __init__(self, model: Component, system: DistributionSystem):
        super().__init__(model, system)

    altdss_name = "Line_LineCode"
    altdss_composition_name = "Line"
    opendss_file = OpenDSSFileTypes.SWITCH_FILE.value

    def map_name(self):
        self.opendss_dict["Name"] = self.get_opendss_safe_name(self.model.name)

    def map_equipment(self):
        self.opendss_dict["LineCode"] = self.get_opendss_safe_name(self.model.equipment.name)

    def map_is_closed(self):
        # Require every phase to be enabled for the OpenDSS line to be enabled.
        self.opendss_dict["Switch"] = True

    def custom_dss_string(self):
        properties = self.system.get_supplemental_attributes_with_component(
            self.model, OpenDSSSwitchProperties
        )
        if not properties:
            return None

        source = properties[0]
        name = self.get_opendss_safe_name(self.model.name)
        bus1 = self._map_source_bus(source.bus1)
        bus2 = self._map_source_bus(source.bus2)
        phases = len(self.model.phases)
        return (
            f"new Line.{name} Switch=True Bus1={bus1} Bus2={bus2} "
            f"R1={source.r1} X1={source.x1} C1={source.c1} "
            f"R0={source.r0} X0={source.x0} C0={source.c0} "
            f"Length={source.length} Phases={phases} Enabled={self.model.in_service}\n"
        )

    def _map_source_bus(self, bus_entry: str) -> str:
        parts = bus_entry.split(".")
        base = self.get_opendss_safe_name(parts[0])
        return base + "".join(f".{token}" for token in parts[1:])

    def map_in_service(self):
        self.opendss_dict["Enabled"] = self.model.in_service
