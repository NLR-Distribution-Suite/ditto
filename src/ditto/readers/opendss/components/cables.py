from gdm.quantities import (
    ResistancePULength,
    Distance,
    Current,
    Voltage,
)
from gdm.distribution.equipment import ConcentricCableEquipment
from pydantic import PositiveInt
import opendssdirect as odd
from loguru import logger

from ditto.readers.opendss.common import query_model_data, get_equipment_from_catalog


def get_cables_equipment() -> list[ConcentricCableEquipment]:
    """Method returns a list of ConcentricCableEquipment objects

    Returns:
        list[ConcentricCableEquipment]: list of ConcentricCableEquipment
    """

    logger.debug("parsing cable components...")
    concentric_cable_equipment_catalog = {}
    model_type = "CNData"
    cables = []
    odd.Circuit.SetActiveClass(model_type)
    flag = odd.ActiveClass.First()
    while flag > 0:
        model_name = odd.Element.Name().lower().split(".")[1]
        gmr_units = query_model_data(model_type, model_name, "gmrunits", str)
        radius_units = query_model_data(model_type, model_name, "radunits", str)
        length_units = query_model_data(model_type, model_name, "runits", str)

        gmr = query_model_data(model_type, model_name, "gmr", float)
        diam = query_model_data(model_type, model_name, "diam", float)
        gmr_strand = query_model_data(model_type, model_name, "gmr", float)
        diam_strand = query_model_data(model_type, model_name, "diam", float)

        cable = ConcentricCableEquipment.model_construct(
            strand_ac_resistance=ResistancePULength(
                query_model_data(model_type, model_name, "rstrand", float), f"ohms/{length_units}"
            ),
            dc_resistance=ResistancePULength(
                query_model_data(model_type, model_name, "rdc", float), f"ohms/{length_units}"
            ),
            phase_ac_resistance=ResistancePULength(
                query_model_data(model_type, model_name, "rac", float), f"ohms/{length_units}"
            ),
            strand_gmr=Distance(
                gmr_strand if gmr_strand else diam_strand * 0.7788, f"{radius_units}"
            ),
            strand_diameter=Distance(
                diam_strand if diam_strand else gmr_strand / 0.7788, f"{radius_units}"
            ),
            ampacity=Current(
                query_model_data(model_type, model_name, "normamps", float), "ampere"
            ),
            emergency_ampacity=Current(
                query_model_data(model_type, model_name, "emergamps", float), "ampere"
            ),
            insulation_thickness=Distance(
                query_model_data(model_type, model_name, "InsLayer", float), "ampere"
            ),
            cable_diameter=Distance(
                query_model_data(model_type, model_name, "DiaCable", float), "ampere"
            ),
            insulation_diameter=Distance(
                query_model_data(model_type, model_name, "diains", float), "ampere"
            ),
            num_neutral_strands=PositiveInt(
                query_model_data(model_type, model_name, "k", int), "ampere"
            ),
            conductor_diameter=Distance(diam if diam else gmr / 0.7788, f"{radius_units}"),
            conductor_gmr=Distance(gmr if gmr else diam * 0.7788, f"{gmr_units}"),
            rated_voltage=Voltage(12.47, "volts"),
            name=model_type,
        )

        cable = get_equipment_from_catalog(cable, concentric_cable_equipment_catalog)

        cables.append(cable)
        flag = odd.ActiveClass.Next()
    return cables
