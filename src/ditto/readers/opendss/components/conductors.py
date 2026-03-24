from gdm.quantities import Current, Distance, ResistancePULength
from gdm.distribution.equipment import BareConductorEquipment
import opendssdirect as odd
from loguru import logger

from ditto.readers.opendss.common import query_model_data, get_equipment_from_catalog


def get_conductors_equipment() -> list[BareConductorEquipment]:
    """Method returns a list of BareConductorEquipment objects

    Returns:
        list[BareConductorEquipment]: list of BareConductorEquipment
    """

    logger.debug("parsing conductor components...")
    bare_conductor_equipment_catalog = {}
    model_type = "WireData"
    conductors = []
    odd.Circuit.SetActiveClass(model_type)
    flag = odd.ActiveClass.First()
    while flag > 0:
        model_name = odd.Element.Name().lower().split(".")[1]
        gmr_units = query_model_data(model_type, model_name, "gmrunits", str)
        radius_units = query_model_data(model_type, model_name, "radunits", str)
        length_units = query_model_data(model_type, model_name, "runits", str)
        gmr = query_model_data(model_type, model_name, "gmr", float)
        diam = query_model_data(model_type, model_name, "diam", float)
        conductor = BareConductorEquipment.model_construct(
            emergency_ampacity=Current(
                query_model_data(model_type, model_name, "emergamps", float), "ampere"
            ),
            conductor_diameter=Distance(diam if diam else gmr / 0.7788, f"{radius_units}"),
            conductor_gmr=Distance(gmr if gmr else diam * 0.7788, f"{gmr_units}"),
            ac_resistance=ResistancePULength(
                query_model_data(model_type, model_name, "rac", float), f"ohms/{length_units}"
            ),
            dc_resistance=ResistancePULength(
                query_model_data(model_type, model_name, "rdc", float), f"ohms/{length_units}"
            ),
            ampacity=Current(
                query_model_data(model_type, model_name, "normamps", float), "ampere"
            ),
            name=model_name,
        )

        conductor = get_equipment_from_catalog(conductor, bare_conductor_equipment_catalog)
        conductors.append(conductor)
        flag = odd.ActiveClass.Next()
    return conductors
