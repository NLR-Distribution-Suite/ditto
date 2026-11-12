from gdm.quantities import (
    ResistancePULength,
    Distance,
    Current,
    Voltage,
)
from gdm.distribution.equipment import ConcentricCableEquipment
import opendssdirect as odd
from loguru import logger

from ditto.readers.opendss.common import query_model_data


def get_cables_equipment() -> list[ConcentricCableEquipment]:
    """Method returns a list of ConcentricCableEquipment objects

    Returns:
        list[ConcentricCableEquipment]: list of ConcentricCableEquipment
    """

    logger.debug("parsing cable components...")
    model_type = "CNData"
    cables = []
    odd.Circuit.SetActiveClass(model_type)
    flag = odd.ActiveClass.First()
    while flag > 0:
        model_name = odd.Element.Name().lower().split(".")[1]
        gmr_units = query_model_data(model_type, model_name, "gmrunits", str)
        radius_units = query_model_data(model_type, model_name, "radunits", str)
        length_units = query_model_data(model_type, model_name, "runits", str)

        gmr = query_model_data(model_type, model_name, "gmrac", float)
        diam = query_model_data(model_type, model_name, "diam", float)
        gmr_strand = query_model_data(model_type, model_name, "gmrstrand", float)
        diam_strand = query_model_data(model_type, model_name, "diastrand", float)

        if not gmr and not diam:
            raise ValueError(f"CNData {model_name!r} has neither conductor GMR nor diameter")
        if not gmr_strand and not diam_strand:
            raise ValueError(f"CNData {model_name!r} has neither strand GMR nor diameter")
        if not diam:
            diam = 2 * Distance(gmr, gmr_units).to(radius_units).magnitude / 0.7788
        if not gmr:
            gmr = Distance(diam / 2, radius_units).to(gmr_units).magnitude * 0.7788
        if not diam_strand:
            diam_strand = 2 * Distance(gmr_strand, gmr_units).to(radius_units).magnitude / 0.7788
        if not gmr_strand:
            gmr_strand = Distance(diam_strand / 2, radius_units).to(gmr_units).magnitude * 0.7788

        cable = ConcentricCableEquipment.model_construct(
            strand_ac_resistance=ResistancePULength(
                query_model_data(model_type, model_name, "rstrand", float), f"ohms/{length_units}"
            ),
            phase_ac_resistance=ResistancePULength(
                query_model_data(model_type, model_name, "rac", float), f"ohms/{length_units}"
            ),
            strand_gmr=Distance(gmr_strand, gmr_units),
            strand_diameter=Distance(diam_strand, radius_units),
            ampacity=Current(
                query_model_data(model_type, model_name, "normamps", float), "ampere"
            ),
            insulation_thickness=Distance(
                query_model_data(model_type, model_name, "InsLayer", float), radius_units
            ),
            cable_diameter=Distance(
                query_model_data(model_type, model_name, "DiaCable", float), radius_units
            ),
            insulation_diameter=Distance(
                query_model_data(model_type, model_name, "diains", float), radius_units
            ),
            num_neutral_strands=query_model_data(model_type, model_name, "k", int),
            conductor_diameter=Distance(diam, radius_units),
            conductor_gmr=Distance(gmr, gmr_units),
            rated_voltage=Voltage(12.47, "volts"),
            name=model_name,
        )

        cables.append(cable)
        flag = odd.ActiveClass.Next()
    return cables
