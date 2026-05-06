from abc import ABC, abstractproperty

class SynergiMapper(ABC):

    def __init__(self, system, node_feeder_map=None):
        self.system = system
        self.node_feeder_map = node_feeder_map or {}

