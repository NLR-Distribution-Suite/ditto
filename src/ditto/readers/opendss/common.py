from enum import IntEnum
from typing import Any
import ast

from gdm.distribution.components import DistributionVoltageSource
from gdm.distribution.enums import Phase
from infrasys import Component, System
import opendssdirect as odd


PHASE_MAPPER = {
    "0": Phase.N,
    "1": Phase.A,
    "2": Phase.B,
    "3": Phase.C,
    "4": Phase.N,
}

UNIT_MAPPER = {0: "m", 1: "mi", 2: "kft", 3: "km", 4: "m", 5: "ft", 6: "in", 7: "cm"}


def get_unit_index(units_value) -> int:
    """Extract an int from an opendssdirect Units() return value.

    Older versions of opendssdirect (>=0.7) return a plain int while
    newer versions return an IntEnum with a `.value` attribute.
    """
    return units_value.value if hasattr(units_value, "value") else int(units_value)


class LoadTypes(IntEnum):
    """Load types represented in Ditto"""

    CONST_POWER = 1
    CONST_IMPEDANCE = 2
    CONST_P__QUARDRATIC_Q = 3
    LINEAR_P__QUARDRATIC_Q = 4
    CONST_CURRENT = 5
    ZIP = 8


def hash_model(model: Component, key_names: list[str] = ["name", "uuid"]) -> int:
    """Return hash of the passed model

    Args:
        model (Component): Instance of a derived infrasys Component model
        key_names (list[str], optional): List of keys to be removed from the model. Defaults to ["name", "uuid"].

    Returns:
        int: model hash
    """
    model_dict = (
        model.model_dump()
    )  # TODO: exclude={"name"} seems not to work  well with list of objects
    cleaned_model = remove_keys_from_dict(model_dict, key_names)
    return hash(str(cleaned_model))


def remove_keys_from_dict(model_dict: dict, key_names: list[str] = ["name", "uuid"]) -> dict:
    """Method recursively removes keys from the model

    Args:
        model_dict (dict): model in dict representation
        key_names (list[str]): keys to remove from the model

    Returns:
        dict: reduced model dictionary
    """
    for key_name in key_names:
        if key_name in model_dict:
            model_dict.pop(key_name)
        for k, v in model_dict.items():
            if isinstance(v, dict):
                model_dict[k] = remove_keys_from_dict(v)
            elif isinstance(v, list):
                values = []
                for value in v:
                    if isinstance(value, dict):
                        value = remove_keys_from_dict(value)
                    values.append(value)
                    model_dict[k] = values
    return model_dict


def get_equipment_from_catalog(
    model: Component, catalog: dict[int, Component], sub_catalog: str | None = None
) -> Component | None:
    """If the equipment already exixts in th system the equipment instance is returned else None is returned

    Args:
        model (Component): Instance of GDM equipment
        catalog (dict[int, Component]): mapping model hash to model
        sub_catalog (str | None, optional): sub catalog in a catalog. Defaults to None.

    Returns:
        Component | None:  Instance of GDM equipment
    """

    model_hash = hash_model(model)
    if sub_catalog is None:
        if model_hash in catalog:
            return catalog[model_hash]
        else:
            catalog[model_hash] = model
            return model
    else:
        assert sub_catalog in catalog and isinstance(catalog[sub_catalog], dict)
        if model_hash in catalog[sub_catalog]:
            return catalog[sub_catalog][model_hash]
        else:
            catalog[sub_catalog][model_hash] = model
            return model


def query_model_data(model_type: str, model_name: str, property: str, dtype: type) -> Any:
    """query OpenDSS model property

    Args:
        model_type (str): OpenDSS model type
        model_name (str): OpenDSS model name
        property (str): OpenDSS model property
        dtype (type): data type e.g. str, float

    Returns:
        Any: OpenDSS model property value
    """
    command = f"? {model_type}.{model_name}.{property}"
    odd.Text.Command(command)
    result = odd.Text.Result()
    if result == "Property Unknown":
        return None
    if dtype is list:
        result = result.replace("[ ", "[").replace(" ", ",")
        return ast.literal_eval(result)
    else:
        return dtype(result)


def get_source_bus(system: System) -> str:
    """Returns the name of the source bus

    Args:
        system (System): Instance of an Infrasys System
    """

    voltage_sources = system.get_components(DistributionVoltageSource)
    buses = [v_source.bus.name for v_source in voltage_sources]
    return buses
