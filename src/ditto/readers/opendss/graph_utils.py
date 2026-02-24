from loguru import logger

from gdm.distribution import DistributionSystem
from gdm.distribution.enums import Phase
from gdm.distribution.components import (
    DistributionTransformer,
    DistributionBranchBase,
    DistributionCapacitor,
    DistributionSolar,
    DistributionLoad,
    DistributionBus,
)
from networkx import Graph, DiGraph

import networkx as nx

from ditto.readers.opendss.common import get_source_bus


def dfs_multidigraph(G: nx.MultiGraph, source: str) -> nx.MultiDiGraph:
    tree = nx.MultiDiGraph()
    for u, v, k in nx.edge_dfs(G, source=source):
        tree.add_edge(u, v, key=k, **G[u][v][k])
    return tree


def update_split_phase_nodes(graph: Graph, system: DistributionSystem) -> DistributionSystem:
    """Return the system with corrected split phase representation

    Args:
        graph (Graph):  Graph representation of the dirtribution model
        system (DistributionSystem): Instance of an gdm DistributionSystem

    Returns:
        DistributionSystem: Updated system with fixed split phase representation
    """

    source_buses = get_source_bus(system)
    if len(set(source_buses)) != 1:
        raise ValueError(
            f"Expected exactly one source bus, but found {len(set(source_buses))}: {set(source_buses)}"
        )
    tree = dfs_multidigraph(graph, source=source_buses[0])
    split_phase_transformers = _get_split_phase_transformers(system)
    for transformer in split_phase_transformers:
        _get_split_phase_sub_graph(transformer, tree, system)


def _get_split_phase_transformers(system: DistributionSystem) -> list[DistributionTransformer]:
    """returns a list of split phase transformers

    Args:
        system (DistributionSystem): Instance of an gdm DistributionSystem

    Returns:
        list[DistributionTransformer]: list of split phase transformers
    """

    split_phase_transformers = system.get_components(
        DistributionTransformer,
        filter_func=lambda x: x.equipment.is_center_tapped,
    )
    return list(split_phase_transformers)


def _get_split_phase_sub_graph(
    xfmr: DistributionTransformer, graph: DiGraph, system: DistributionSystem
) -> Graph:
    """returns the subgraph for a given distribution transformer

    Args:
        xfmr(DistributionTransformer): instance of DistributionTransformer
        graph (DiGraph): Graph representation of the dirtribution model
        system (DistributionSystem): Instance of an gdm DistributionSystem

    Returns:
        Graph: subgraph for a given distribution transformer
    """

    xfmr_buses = list(
        {(bus.name, bus.rated_voltage.to("kilovolt").magnitude) for bus in xfmr.buses}
    )
    hv_xfmr_bus = max(xfmr_buses, key=lambda x: x[1])[0]
    lv_xfmr_bus = min(xfmr_buses, key=lambda x: x[1])[0]
    logger.debug(f"Processing split-phase transformer: {xfmr.name}")
    xfmr_info = graph[hv_xfmr_bus][lv_xfmr_bus]

    for k in xfmr_info:
        if xfmr_info[k]["type"] != DistributionTransformer:
            raise TypeError(f"Unsupported model type {xfmr_info[k]['type']}")
        model_type = xfmr_info[k]["type"]
        xfmr_model = system.get_component(model_type, xfmr_info[k]["name"])

        filter_nodes = []
        for node, sucessors in nx.bfs_successors(graph, lv_xfmr_bus):
            filter_nodes.append(node)
            filter_nodes.extend(sucessors)

        descendants = set(filter_nodes)
        subgraph = graph.subgraph(descendants)
        _get_components_in_subgraph(hv_xfmr_bus, xfmr_model, subgraph, system)
        return


def _get_components_in_subgraph(
    hv_xfmr_bus: str,
    xfmr_model: DistributionTransformer,
    subgraph: Graph,
    system: DistributionSystem,
):
    """fixes the split phase representation for the system

    Args:
        hv_xfmr_bus (str): bus name for the distribution transformer (HV side)
        xfmr_model (DistributionTransformer): instance of DistributionTransformer
        subgraph (Graph): subgraph (downstream) of a split phase dirtribution transformer
        system (DistributionSystem): Instance of an gdm DistributionSystem

    """

    secondary_wdg_phases = xfmr_model.winding_phases[1:]
    xfmr_phases_filtered = []
    split_phases = [Phase.S1, Phase.S2]
    xfmr_phases_filtered = [
        phase for phase_lists in secondary_wdg_phases for phase in phase_lists if phase != Phase.N
    ]
    mapped_split_phases = {k: v for k, v in zip(xfmr_phases_filtered, split_phases)}
    _fix_bus_phases(hv_xfmr_bus, mapped_split_phases, subgraph, system)
    _fix_transformer_phases(mapped_split_phases, xfmr_model, secondary_wdg_phases)
    _fix_component_phases(mapped_split_phases, subgraph, system)


def _fix_bus_phases(
    hv_xfmr_bus: str, mapped_split_phases: dict, subgraph: Graph, system: DistributionSystem
):
    """method fixes phasing for distribution buses downstream of split phase transformers

    Args:
        hv_xfmr_bus (str): bus name for the distribution transformer (HV side)
        mapped_split_phases (dict):  mapping A,B,C phase to S1/S2 phase
        subgraph (Graph): subgraph (downstream) of a split phase dirtribution transformer
        system (DistributionSystem): Instance of an gdm DistributionSystem
    """
    for u in subgraph.nodes():
        if u != hv_xfmr_bus:
            bus = system.get_component(DistributionBus, u)
            bus.phases = _mapped_phases(mapped_split_phases, bus.phases)

    for _, _, data in subgraph.edges(data=True):
        model: DistributionBranchBase = system.get_component(data["type"], data["name"])
        if not issubclass(model.__class__, DistributionBranchBase):
            raise TypeError(f"Unsupported model type {model.__class__.__name__}")
        model.phases = _mapped_phases(mapped_split_phases, model.phases)


def _mapped_phases(mapped_split_phases, phases):
    return list(
        set(
            [
                mapped_split_phases[phase] if phase in mapped_split_phases else phase
                for phase in phases
            ]
        )
    )


def _fix_transformer_phases(
    mapped_split_phases: dict,
    xfmr_model: DistributionTransformer,
    secondary_wdg_phases: list[list[Phase]],
):
    """method fixes phasing for split phase transformers

    Args:
        mapped_split_phases (dict): mapping A,B,C phase to S1/S2 phase
        xfmr_model (DistributionTransformer): instance of DistributionTransformer
        secondary_wdg_phases (list[list[Phase]]): secondary phases for a distribution transformers
    """
    wdg_phases = [xfmr_model.winding_phases[0]]
    for phase_list in secondary_wdg_phases:
        new_phases = list(
            set(
                [
                    mapped_split_phases[phase] if phase in mapped_split_phases else phase
                    for phase in phase_list
                ]
            )
        )
        wdg_phases.append(new_phases)
    xfmr_model.winding_phases = wdg_phases


def _fix_component_phases(mapped_split_phases: dict, subgraph: Graph, system: DistributionSystem):
    """method fixes phasing for components downstream of split phase transformers

    Args:
        mapped_split_phases (dict): mapping A,B,C phase to S1/S2 phase
        subgraph (Graph): subgraph (downstream) of a split phase dirtribution transformer
        system (DistributionSystem): Instance of an gdm DistributionSystem
    """
    component_types = [DistributionLoad, DistributionCapacitor, DistributionSolar]
    for node in subgraph.nodes():
        for component_type in component_types:
            for component in system.get_bus_connected_components(node, component_type) or []:
                component.phases = [mapped_split_phases[phase] for phase in component.phases]
