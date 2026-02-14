from uuid import uuid4
from enum import Enum

from infrasys import System, Component
from infrasys.quantities import Time

from gdm.quantities import (
    CapacitancePULength,
    ResistancePULength,
    ReactancePULength,
    Distance,
    Current,
)

from gdm.distribution.common import TimeCurrentCurve, ThermalLimitSet
from gdm.distribution.equipment import (
    MatrixImpedanceRecloserEquipment,
    MatrixImpedanceSwitchEquipment,
    MatrixImpedanceBranchEquipment,
    MatrixImpedanceFuseEquipment,
    ConcentricCableEquipment,
    GeometryBranchEquipment,
    BareConductorEquipment,
)
from gdm.distribution.components import (
    MatrixImpedanceSwitch,
    MatrixImpedanceBranch,
    MatrixImpedanceFuse,
    DistributionBus,
    GeometryBranch,
)
from gdm.distribution.enums import Phase

import opendssdirect as odd
from loguru import logger
import numpy as np

from ditto.readers.opendss.common import (
    get_equipment_from_catalog,
    query_model_data,
    PHASE_MAPPER,
    UNIT_MAPPER,
    get_unit_index,
    hash_model,
)


class MatrixBranchTypes(str, Enum):
    LINE_CODE = "LineCodes"
    LINE = "Lines"


def get_geometry_branch_equipments(
    system: System,
) -> tuple[list[GeometryBranchEquipment], dict[str, int]]:
    """Helper function that return a list of GeometryBranchEquipment objects

    Args:
        system (System): Instance of System

    Returns:
        list[GeometryBranchEquipment]: list of GeometryBranchEquipment objects
        dict[str, int]: mapping of line geometries names to GeometryBranchEquipment hash
    """

    logger.debug("parsing geometry branch equipment...")

    mapped_geometry = {}
    geometry_branch_equipment_catalog = {}
    flag = odd.LineGeometries.First()

    while flag > 0:
        geometry_name = odd.LineGeometries.Name().lower()
        x_coordinates = []
        y_coordinates = []
        units = UNIT_MAPPER[get_unit_index(odd.LineGeometries.Units()[0])]
        odd.Text.Command(f"? LineGeometry.{geometry_name}.wires")
        wires = odd.Text.Result().strip("[]").split(", ")
        model_name = odd.Element.Name().lower().split(".")[1]
        conductor_elements = []

        for i, wire in enumerate(wires):
            odd.Text.Command(f"LineGeometry.{geometry_name}.cond={i + 1}")
            odd.Text.Command(f"? LineGeometry.{geometry_name}.h")
            y_coordinates.append(float(odd.Text.Result()))
            odd.Text.Command(f"? LineGeometry.{geometry_name}.x")
            x_coordinates.append(float(odd.Text.Result()))

            equipments = list(
                system.get_components(BareConductorEquipment, filter_func=lambda x: x.name == wire)
            )
            if not equipments:
                equipments = list(
                    system.get_components(
                        ConcentricCableEquipment, filter_func=lambda x: x.name == wire
                    )
                )
            equipment = equipments[0]
            conductor_elements.append(equipment)

        geometry_branch_equipment = GeometryBranchEquipment.model_construct(
            name=model_name,
            conductors=conductor_elements,
            horizontal_positions=Distance(x_coordinates, units),
            vertical_positions=Distance(y_coordinates, units),
        )
        geometry_branch_equipment = get_equipment_from_catalog(
            geometry_branch_equipment, geometry_branch_equipment_catalog
        )
        mapped_geometry[geometry_name] = hash_model(geometry_branch_equipment)

        flag = odd.LineGeometries.Next()

    return geometry_branch_equipment_catalog, mapped_geometry


def _build_matrix_branch(
    model_type: str,
    matrix_branch_equipments_catalog: dict[int, Component],
    thermal_limit_catalog: dict[int, Component],
    model_class: (type[MatrixImpedanceSwitchEquipment] | type[MatrixImpedanceBranchEquipment]),
    fuse: dict,
    recloser: dict,
) -> MatrixImpedanceBranchEquipment:
    """Helper function to build a MatrixImpedanceBranchEquipment instance

    Args:
        model_type (str): OpenDSS model type e.g. LinesCode / Line
        matrix_branch_equipments_catalog (dict[int, Component]): mapping of model hash to MatrixImpedanceBranchEquipment instance
        thermal_limit_catalog (dict[int, Component]): mapping of model hash to ThermalLimitSet instance

    Returns:
        MatrixImpedanceBranchEquipment: instance of MatrixImpedanceBranchEquipment
    """

    model_name = odd.Element.Name().lower().split(".")[1]
    if model_type == MatrixBranchTypes.LINE_CODE.value:
        equipment_uuid = model_name
    else:
        equipment_uuid = str(uuid4())
    module: odd.LineCodes | odd.Lines = getattr(odd, model_type)

    num_phase = module.Phases()
    length_units = UNIT_MAPPER[get_unit_index(module.Units())]

    r_matrix = module.RMatrix() if model_type == MatrixBranchTypes.LINE.value else module.Rmatrix()
    x_matrix = module.XMatrix() if model_type == MatrixBranchTypes.LINE.value else module.Xmatrix()
    c_matrix = module.CMatrix() if model_type == MatrixBranchTypes.LINE.value else module.Cmatrix()
    amps = module.NormAmps() if module.NormAmps() else 0.001
    matrix_branch_dict = {
        "name": equipment_uuid,
        "r_matrix": ResistancePULength(
            np.reshape(np.array(r_matrix), (num_phase, num_phase)),
            f"ohm/{length_units}",
        ),
        "x_matrix": ReactancePULength(
            np.reshape(np.array(x_matrix), (num_phase, num_phase)),
            f"ohm/{length_units}",
        ),
        "c_matrix": CapacitancePULength(
            np.reshape(np.array(c_matrix), (num_phase, num_phase)),
            f"nanofarad/{length_units}",
        ),
        "ampacity": Current(amps, "ampere"),
    }
    if model_class == MatrixImpedanceSwitchEquipment:
        # TODO: implement switch controller logic here
        controller = _build_distribution_switch_controller()
        matrix_branch_dict["controller"] = controller
    elif model_class == MatrixImpedanceFuseEquipment:
        matrix_branch_dict.update(fuse)
    elif model_class == MatrixImpedanceRecloserEquipment:
        matrix_branch_dict.update(recloser)
    matrix_branch_equipment = model_class.model_construct(**matrix_branch_dict)
    matrix_branch_equipment = get_equipment_from_catalog(
        matrix_branch_equipment, matrix_branch_equipments_catalog, model_class.__name__
    )
    return matrix_branch_equipment


def _build_distribution_switch_controller():
    return None


def get_matrix_branch_equipments() -> (
    tuple[dict[int, MatrixImpedanceBranchEquipment], dict[int, ThermalLimitSet]]
):
    """Function to return list of all MatrixImpedanceBranchEquipment in Opendss model.

    Returns:
        dict[int, MatrixImpedanceBranchEquipment]: mapping of model hash to MatrixImpedanceBranchEquipment instance
        dict[int, ThermalLimitSet]: mapping of model hash to ThermalLimitSet instance
    """

    logger.debug("parsing matrix branch equipment...")
    reclosers = get_reclosers()
    fuses = get_fuses()
    matrix_branch_equipments_catalog = {
        MatrixImpedanceRecloserEquipment.__name__: {},
        MatrixImpedanceSwitchEquipment.__name__: {},
        MatrixImpedanceBranchEquipment.__name__: {},
        MatrixImpedanceFuseEquipment.__name__: {},
    }
    thermal_limit_catalog = {}
    odd_model_types = [v.value for v in MatrixBranchTypes]
    for odd_model_type in odd_model_types:
        module: odd.LineCodes | odd.Lines = getattr(odd, odd_model_type)
        flag = module.First()
        while flag > 0:
            if odd_model_type == MatrixBranchTypes.LINE.value and module.Geometry():
                pass
            else:
                fuse = {}
                recloser = {}
                if (
                    odd_model_type == MatrixBranchTypes.LINE.value
                    and odd.Lines.Name().lower() in fuses
                ):
                    fuse = fuses[odd.Lines.Name().lower()]
                    model_type = MatrixImpedanceFuseEquipment
                elif (
                    odd_model_type == MatrixBranchTypes.LINE.value
                    and odd.Lines.Name().lower() in reclosers
                ):
                    recloser = reclosers[odd.Lines.Name().lower()]
                    model_type = MatrixImpedanceRecloserEquipment
                elif odd_model_type == MatrixBranchTypes.LINE.value and odd.Lines.IsSwitch():
                    model_type = MatrixImpedanceSwitchEquipment
                else:
                    model_type = MatrixImpedanceBranchEquipment
                _build_matrix_branch(
                    odd_model_type,
                    matrix_branch_equipments_catalog,
                    thermal_limit_catalog,
                    model_type,
                    fuse,
                    recloser,
                )
            flag = module.Next()
    return matrix_branch_equipments_catalog, thermal_limit_catalog


def get_branches(
    system: System,
    mapping: dict[str, str],
    geometry_branch_equipment_catalog: dict,
    matrix_branch_equipments_catalog: dict,
    thermal_limit_catalog: dict,
) -> tuple[list[MatrixImpedanceBranch | GeometryBranch]]:
    """Method to build a model branches

    Args:
        system (System): Instance of System
        mapping (dict[str, int]): mapping of line geometries names to GeometryBranchEquipment hash
        geometry_branch_equipment_catalog (dict): mapping of model hash to GeometryBranchEquipment instance
        matrix_branch_equipments_catalog (dict): mapping of model hash to MatrixImpedanceBranchEquipment instance
        thermal_limit_catalog (dict): mapping of model hash to ThermalLimitSet instance

    Returns:
        tuple[list[MatrixImpedanceBranch | GeometryBranch]]: Returns a list of system branches
    """

    logger.debug("parsing branch components...")
    reclosers = get_reclosers()
    fuses = get_fuses()
    branches = []
    flag = odd.Lines.First()
    while flag > 0:
        logger.debug(f"building line {odd.CktElement.Name()}...")

        buses = odd.CktElement.BusNames()
        bus1, bus2 = buses[0].split(".")[0], buses[1].split(".")[0]
        num_phase = odd.CktElement.NumPhases()
        nodes = ["1", "2", "3"] if num_phase == 3 else buses[0].split(".")[1:]
        geometry = odd.Lines.Geometry().lower()
        if geometry:
            assert geometry in mapping
            geometry_hash = mapping[geometry]
            geometry_branch_equipment = geometry_branch_equipment_catalog[geometry_hash]

            n_conds = len(geometry_branch_equipment.conductors)
            for _ in range(n_conds - num_phase):
                nodes.append("4")

            if "4" in nodes:
                for bus in [bus1, bus2]:
                    bus_obj = system.get_component(DistributionBus, bus)
                    bus_obj.phases.append(Phase.N)

            geometry_branch = GeometryBranch.model_construct(
                name=odd.Lines.Name().lower(),
                equipment=geometry_branch_equipment,
                buses=[
                    system.get_component(DistributionBus, bus1),
                    system.get_component(DistributionBus, bus2),
                ],
                length=Distance(odd.Lines.Length(), UNIT_MAPPER[odd.Lines.Units()]),
                phases=[PHASE_MAPPER[node] for node in nodes],
            )
            branches.append(geometry_branch)
        else:
            fuse = {}
            recloser = {}
            if odd.Lines.Name().lower() in fuses:
                fuse = fuses[odd.Lines.Name().lower()]
                equipment_class = MatrixImpedanceFuseEquipment
                model_class = MatrixImpedanceFuse
            elif odd.Lines.Name().lower() in reclosers:
                recloser = reclosers[odd.Lines.Name().lower()]
                equipment_class = MatrixImpedanceFuseEquipment
                model_class = MatrixImpedanceFuse
            elif odd.Lines.IsSwitch():
                equipment_class = MatrixImpedanceSwitchEquipment
                model_class = MatrixImpedanceSwitch
            else:
                equipment_class = MatrixImpedanceBranchEquipment
                model_class = MatrixImpedanceBranch
            equipment = _build_matrix_branch(
                MatrixBranchTypes.LINE.value,
                matrix_branch_equipments_catalog,
                thermal_limit_catalog,
                equipment_class,
                fuse,
                recloser,
            )
            equipment = get_equipment_from_catalog(
                equipment, matrix_branch_equipments_catalog, equipment_class.__name__
            )
            model_dict = {
                "name": odd.Lines.Name().lower(),
                "buses": [
                    system.get_component(DistributionBus, bus1),
                    system.get_component(DistributionBus, bus2),
                ],
                "length": Distance(odd.Lines.Length(), UNIT_MAPPER[odd.Lines.Units()]),
                "phases": [PHASE_MAPPER[node] for node in nodes],
                "equipment": equipment,
            }
            if model_class in [MatrixImpedanceSwitch, MatrixImpedanceFuse]:
                model_dict["is_closed"] = [
                    not (odd.CktElement.IsOpen(1, node + 1) or odd.CktElement.IsOpen(2, node + 1))
                    for node in range(len(nodes))
                ]
            matrix_branch = model_class.model_construct(**model_dict)
            branches.append(matrix_branch)
        flag = odd.Lines.Next()

    return branches


def get_tcc_curves() -> dict[str, TimeCurrentCurve]:
    """method returns a dict of tcc curve names mapped to TimeCurrentCurve objects

    Returns:
        dict[str, TimeCurrentCurve]: mapped TimeCurrentCurve objects
    """
    curves = {}
    odd.Circuit.SetActiveClass("tcc_curve")
    flag = odd.ActiveClass.First()
    while flag:
        element_type, element_name = odd.Element.Name().split(".")
        c_array = query_model_data(element_type, element_name, "c_array", list)
        t_array = query_model_data(element_type, element_name, "t_array", list)
        curves[element_name] = TimeCurrentCurve(
            curve_x=Current(c_array, "ampere"),
            curve_y=Time(t_array, "second"),
        )
        flag = odd.ActiveClass.Next()
    return curves


def get_fuses() -> list[str]:
    """Returns a list of lines with fuses

    Returns:
        list[str]: List of lines with fuses
    """
    curves = get_tcc_curves()
    lines_with_fuses = {}
    flag = odd.Fuses.First()
    while flag:
        _, object_name = odd.Fuses.MonitoredObj().split(".")

        curve_name = odd.Fuses.TCCCurve()
        lines_with_fuses[object_name] = {
            "delay": Time(odd.Fuses.Delay(), "seconds"),
            "tcc_curve": curves[curve_name],
        }
        flag = odd.Fuses.Next()
    return lines_with_fuses


def get_reclosers():
    """Returns a list of lines with reclosers

    Returns:
        list[str]: List of lines with reclosers
    """
    lines_with_reclosers = {}
    flag = odd.Reclosers.First()
    while flag:
        _, object_name = odd.Reclosers.MonitoredObj().split(".")
        lines_with_reclosers[object_name] = None
        flag = odd.Reclosers.Next()
    return lines_with_reclosers
