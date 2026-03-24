import pandas as pd
from gdm.distribution.components.distribution_feeder import DistributionFeeder
from gdm.distribution.components.distribution_substation import DistributionSubstation
from gdm.distribution.distribution_system import DistributionSystem
from gdm.distribution.components.distribution_bus import DistributionBus
from infrasys.exceptions import ISAlreadyAttached

from functools import partial


def read_cyme_data(
    cyme_file,
    cyme_section,
    index_col=None,
    node_feeder_map=None,
    node_substation_map=None,
    parse_feeders=False,
    parse_substation=False,
):
    all_data = []
    headers = None
    with open(cyme_file) as f:
        reading = False
        feeder_id = None
        feeder_object_map = {}
        substation_id = None
        substation_object_map = {}

        for line in f:
            if line.startswith(f"[{cyme_section}]"):
                reading = True
                continue
            if not reading:
                continue
            if line.strip() == "":
                break

            if line.startswith(f"FORMAT_{cyme_section.replace(' ','')}"):
                headers = line.split("=")[1].strip().split(",")
                continue
            elif (
                line.startswith("FORMAT")
                or line.startswith("FEEDER")
                or line.startswith("SUBSTATION")
            ):
                feeder_id, substation_id = _parse_context_line(
                    line, parse_feeders, parse_substation
                )
                continue
            else:
                try:
                    line = line.strip()
                    line_data = line.split(",")
                    if cyme_section == "SECTION":
                        _track_section_nodes(
                            line_data,
                            feeder_id,
                            substation_id,
                            parse_feeders,
                            parse_substation,
                            node_feeder_map,
                            feeder_object_map,
                            node_substation_map,
                            substation_object_map,
                        )
                    all_data.append(line_data)
                except Exception as e:
                    raise Exception(f"Failed to parse line: {line}. Error: {e}")

    data = pd.DataFrame(all_data, columns=headers)
    if index_col is not None:
        data.set_index(index_col, inplace=True, drop=False)
    return data


def _parse_context_line(line, parse_feeders, parse_substation):
    """Extract feeder_id / substation_id from FEEDER= or SUBSTATION= lines."""
    feeder_id = None
    substation_id = None
    if parse_substation and line.startswith("SUBSTATION"):
        substation_id = line.split(",")[0].split("=")[1].strip()
    if parse_feeders and line.startswith("FEEDER"):
        feeder_id = line.split(",")[0].split("=")[1].strip()
    return feeder_id, substation_id


def _track_section_nodes(
    line_data,
    feeder_id,
    substation_id,
    parse_feeders,
    parse_substation,
    node_feeder_map,
    feeder_object_map,
    node_substation_map,
    substation_object_map,
):
    """Map SECTION nodes to their feeder/substation objects."""
    node1 = line_data[1].strip()
    node2 = line_data[3].strip()
    if parse_feeders and (feeder_id is not None):
        feeder = feeder_object_map.get(feeder_id, DistributionFeeder(name=feeder_id))
        node_feeder_map[node1] = feeder
        node_feeder_map[node2] = feeder
        feeder_object_map[feeder_id] = feeder
    if parse_substation and (substation_id is not None):
        substation = substation_object_map.get(
            substation_id,
            DistributionSubstation(name=substation_id, feeders=[]),
        )
        node_substation_map[node1] = substation
        node_substation_map[node2] = substation
        substation_object_map[substation_id] = substation


def network_truncation(system, substation_names=None, feeder_names=None):
    trunc_dist_sys = DistributionSystem(auto_add_composed_components=True)

    bus_set = _collect_connected_buses(
        system, substation_names=substation_names, feeder_names=feeder_names
    )

    print(f"Truncating to {len(bus_set)} buses")
    types = list(system.get_component_types())
    for component_type in types:
        components = list(system.get_components(component_type))
        length = len(components)
        print(f"Truncating components of type {component_type.__name__}, total: {length}")
        for i, comp in enumerate(components):
            print(f"Truncating component {i+1} of {length}", end="\r", flush=True)
            if hasattr(comp, "bus"):
                if comp.bus.name in bus_set:
                    _safe_add_component(trunc_dist_sys, comp)
            elif hasattr(comp, "buses"):
                for bus in comp.buses:
                    if bus.name in bus_set:
                        _safe_add_component(trunc_dist_sys, comp)
                        break
            else:
                break

    return trunc_dist_sys


def _collect_connected_buses(system, substation_names=None, feeder_names=None):
    buses = list(
        system.get_components(
            DistributionBus,
            filter_func=partial(filter_substation, substation_names=substation_names),
        )
    )
    buses.extend(
        list(
            system.get_components(
                DistributionBus, filter_func=partial(filter_feeder, feeder_names=feeder_names)
            )
        )
    )
    bus_set = set(bus.name for bus in buses)

    return bus_set


def _safe_add_component(trunc_dist_sys, comp):
    try:
        trunc_dist_sys.add_component(comp)
    except ISAlreadyAttached:
        pass


def filter_feeder(object, feeder_names=None):
    if not hasattr(object.feeder, "name"):
        return False
    if object.feeder.name in feeder_names:
        return True
    return False


def filter_substation(object, substation_names=None):
    if not hasattr(object.substation, "name"):
        return False
    if object.substation.name in substation_names:
        return True
    return False
