from abc import ABC
from gdm.distribution.components.distribution_feeder import DistributionFeeder
from gdm.distribution.components.distribution_substation import DistributionSubstation
from ditto.readers.synergi.utils import sanitize_name


class SynergiMapper(ABC):

    def __init__(self, system, node_feeder_map=None):
        self.system = system
        self.node_feeder_map = node_feeder_map or {}

    def _lookup_feeder_substation(self, node_id: str):
        feeder = None
        substation = None
        feeder_info = self.node_feeder_map.get(node_id, {})
        if feeder_info:
            try:
                feeder = self.system.get_component(DistributionFeeder, sanitize_name(feeder_info["feeder_id"]))
            except Exception:
                pass
            try:
                substation = self.system.get_component(DistributionSubstation, sanitize_name(feeder_info["sub_id"]))
            except Exception:
                pass
        return feeder, substation

