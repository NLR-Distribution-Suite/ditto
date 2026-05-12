from abc import ABC

from ditto.readers.cyme.constants import ModelUnitSystem


class CymeMapper(ABC):
    def __init__(self, system, units=ModelUnitSystem):
        self.system = system
        self.units = units
