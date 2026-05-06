import math
from infrasys.location import Location
from gdm.distribution.components.distribution_bus import DistributionBus
from gdm.distribution.components.distribution_feeder import DistributionFeeder
from gdm.distribution.components.distribution_substation import DistributionSubstation
from gdm.distribution.enums import VoltageTypes, Phase
from gdm.quantities import Voltage
from ditto.readers.synergi.synergi_mapper import SynergiMapper
from ditto.readers.synergi.utils import parse_phases, sort_phases, sanitize_name


class DistributionBusMapper(SynergiMapper):

    synergi_table = "Node"
    synergi_database = "Model"

    def parse(self, row, unit_type, section_id_sections, from_node_sections, to_node_sections):
        node_id = str(row["NodeId"]).strip()
        feeder_info = self.node_feeder_map.get(node_id, {})

        feeder = None
        substation = None
        if feeder_info:
            try:
                feeder = self.system.get_component(DistributionFeeder, name=sanitize_name(feeder_info["feeder_id"]))
            except Exception:
                pass
            try:
                substation = self.system.get_component(DistributionSubstation, name=sanitize_name(feeder_info["sub_id"]))
            except Exception:
                pass

        return DistributionBus(
            name=sanitize_name(node_id),
            coordinate=self.map_coordinate(row),
            rated_voltage=self.map_nominal_voltage(feeder_info),
            phases=self.map_phases(node_id, from_node_sections, to_node_sections),
            voltagelimits=[],
            voltage_type=VoltageTypes.LINE_TO_GROUND,
            substation=substation,
            feeder=feeder,
        )

    def map_coordinate(self, row):
        return Location(x=row["X"], y=row["Y"])

    def map_nominal_voltage(self, feeder_info: dict) -> Voltage:
        nominal_kvll = feeder_info.get("nominal_kvll", 12.47) or 12.47
        return Voltage(nominal_kvll / math.sqrt(3), "kilovolt")

    def map_phases(self, node_id, from_node_sections, to_node_sections):
        all_phases: set[Phase] = set()
        for section in from_node_sections.get(node_id, []):
            all_phases.update(parse_phases(section["SectionPhases"]))
        for section in to_node_sections.get(node_id, []):
            all_phases.update(parse_phases(section["SectionPhases"]))
        return sort_phases(all_phases)

