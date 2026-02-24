from abc import ABC
from typing import Any

from gdm.distribution import DistributionSystem


class CimMapper(ABC):
    def __init__(self, system: DistributionSystem):
        self.system = system

    def _required_component(self, component_type: type, name: str, context: str):
        try:
            component = self.system.get_component(component_type=component_type, name=name)
        except Exception as error:
            raise LookupError(
                f"Failed to resolve {component_type.__name__} '{name}' while mapping {context}"
            ) from error

        if component is None:
            raise LookupError(
                f"Missing {component_type.__name__} '{name}' while mapping {context}"
            )

        return component

    def _required_field(self, row: Any, field_name: str, context: str):
        if field_name not in row:
            raise ValueError(f"Missing required field '{field_name}' while mapping {context}")
        value = row[field_name]
        if value is None:
            raise ValueError(f"Null required field '{field_name}' while mapping {context}")
        return value
