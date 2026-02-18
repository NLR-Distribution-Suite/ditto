from enum import Enum


class OpenDSSFileTypes(str, Enum):
    MASTER_FILE = "Master.dss"
    COORDINATE_FILE = "BusCoords.dss"
    LOADSHAPE_FILE = "LoadShape.dss"
    WIRES_FILE = "WireData.dss"
    LINE_GEOMETRIES_FILE = "LineGeometry.dss"
    LINECODES_FILE = "LineCodes.dss"
    SWITCH_CODES_FILE = "SwitchCodes.dss"
    FUSE_CODES_FILE = "FuseCodes.dss"
    TRANSFORMERS_FILE = "Transformers.dss"
    CAPACITORS_FILE = "Capacitors.dss"
    LINES_FILE = "Lines.dss"
    LOADS_FILE = "Loads.dss"
    SOLAR_FILE = "Solar.dss"
    SWITCH_FILE = "Switches.dss"
    FUSE_FILE = "Fuses.dss"
    RECLOSER_CODES_FILE = "RecloserCodes.dss"
    RECLOSER_FILE = "Reclosers.dss"
    RECLOSER_CONTROLLERS_FILE = "RecloserControllers.dss"
    TCC_CURVES_FILE = "TCC_Curves.dss"
    REGULATOR_CONTROLLERS_FILE = "RegControllers.dss"
