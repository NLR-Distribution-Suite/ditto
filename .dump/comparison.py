from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import opendssdirect as dss


@dataclass
class Record:
    name: str
    category: str
    key: str
    buses: list[str]
    phases: int | None = None
    kv: float | None = None
    kw: float | None = None
    kvar: float | None = None
    kva: float | None = None
    conn: str | None = None
    length_km: float | None = None
    losses_kw: float | None = None
    losses_kvar: float | None = None
    loading_pct: float | None = None
    voltage_drop_pu: float | None = None
    extra: dict[str, Any] | None = None


def parse_args() -> argparse.Namespace:
    dump_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(
        description="Compare OpenDSS models in .dump/original and .dump/converted"
    )
    parser.add_argument(
        "--original",
        type=Path,
        default=dump_dir / "original",
        help="Directory containing the reference OpenDSS model",
    )
    parser.add_argument(
        "--converted",
        type=Path,
        default=dump_dir / "converted",
        help="Directory containing the converted OpenDSS model",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=dump_dir / "comparison_report.json",
        help="Path to write the JSON report",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=20,
        help="Number of largest mismatches to print per category",
    )
    return parser.parse_args()


def find_master_file(folder: Path) -> Path:
    if folder.is_file():
        return folder

    preferred = [folder / "Master.dss", folder / "master.dss"]
    preferred.extend(folder.glob("*Master*.dss"))
    preferred.extend(folder.glob("*master*.dss"))

    for path in preferred:
        if path.exists():
            return path

    raise FileNotFoundError(f"Could not find a master DSS file in {folder}")


def redirect_and_solve(master_path: Path) -> None:
    dss.Text.Command("clear")
    dss.Text.Command(f'redirect "{master_path}"')
    dss.Text.Command("Batchedit regcontrol..* enabled=false")
    dss.Text.Command("Batchedit Transformer..* taps=[1, 1]")
    dss.Text.Command(f'redirect "{master_path}"')
    dss.Solution.SolveNoControl()


def safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def base_bus(bus_name: str) -> str:
    return bus_name.split(".")[0].lower()


def bus_nodes(bus_name: str) -> tuple[str, ...]:
    parts = bus_name.split(".")
    if len(parts) == 1:
        return tuple()
    return tuple(sorted(parts[1:]))


def normalized_edge_key(category: str, buses: list[str], phases: int | None) -> str:
    normalized = []
    for bus in buses[:2]:
        normalized.append((base_bus(bus), bus_nodes(bus)))
    normalized.sort()
    return json.dumps([category, phases, normalized])


def normalized_terminal_key(category: str, bus: str, phases: int | None, conn: str | None) -> str:
    return json.dumps([category, base_bus(bus), bus_nodes(bus), phases, conn])


def active_bus_stats(bus_name: str) -> dict[str, Any]:
    dss.Circuit.SetActiveBus(base_bus(bus_name))
    values = dss.Bus.puVmagAngle()[::2]
    if not values:
        return {"min_pu": None, "max_pu": None, "avg_pu": None}
    return {
        "min_pu": min(values),
        "max_pu": max(values),
        "avg_pu": sum(values) / len(values),
    }


def voltage_drop_between_buses(buses: list[str]) -> float | None:
    if len(buses) < 2:
        return None
    stats_1 = active_bus_stats(buses[0])
    stats_2 = active_bus_stats(buses[1])
    if stats_1["avg_pu"] is None or stats_2["avg_pu"] is None:
        return None
    return abs(stats_1["avg_pu"] - stats_2["avg_pu"])


def max_current_from_element() -> float | None:
    current_data = dss.CktElement.CurrentsMagAng()[::2]
    return max(current_data) if current_data else None


def loading_pct_from_element() -> float | None:
    max_current = max_current_from_element()
    normal_amps = safe_float(dss.CktElement.NormalAmps())
    if max_current is None or not normal_amps:
        return None
    return max_current / normal_amps * 100


def element_losses() -> tuple[float | None, float | None]:
    losses = dss.CktElement.Losses()
    if not losses:
        return None, None
    return losses[0] / 1000.0, losses[1] / 1000.0


def first_terminal_power() -> tuple[float | None, float | None]:
    powers = dss.CktElement.Powers()
    if not powers:
        return None, None
    terminal_count = len(dss.CktElement.BusNames())
    if terminal_count == 0:
        return None, None
    values_per_terminal = len(powers) // terminal_count
    first_terminal = powers[:values_per_terminal]
    kw = sum(first_terminal[0::2])
    kvar = sum(first_terminal[1::2])
    return kw, kvar


def collect_buses() -> dict[str, dict[str, Any]]:
    results: dict[str, dict[str, Any]] = {}
    for name in dss.Circuit.AllBusNames():
        dss.Circuit.SetActiveBus(name)
        pu_values = dss.Bus.puVmagAngle()[::2]
        results[name.lower()] = {
            "name": name,
            "kv_base": safe_float(dss.Bus.kVBase()),
            "nodes": dss.Bus.Nodes(),
            "min_pu": min(pu_values) if pu_values else None,
            "max_pu": max(pu_values) if pu_values else None,
            "avg_pu": (sum(pu_values) / len(pu_values)) if pu_values else None,
        }
    return results


def collect_lines() -> list[Record]:
    records: list[Record] = []
    for name in dss.Lines.AllNames():
        dss.Lines.Name(name)
        dss.Circuit.SetActiveElement(f"Line.{name}")
        buses = dss.CktElement.BusNames()
        losses_kw, losses_kvar = element_losses()
        is_switch = bool(getattr(dss.Lines, "IsSwitch", lambda: False)())
        category = "switch" if is_switch else "line"
        records.append(
            Record(
                name=name,
                category=category,
                key=normalized_edge_key(category, buses, dss.CktElement.NumPhases()),
                buses=buses,
                phases=dss.CktElement.NumPhases(),
                length_km=safe_float(dss.Lines.Length()),
                losses_kw=losses_kw,
                losses_kvar=losses_kvar,
                loading_pct=loading_pct_from_element(),
                voltage_drop_pu=voltage_drop_between_buses(buses),
                extra={
                    "bus1": dss.Lines.Bus1(),
                    "bus2": dss.Lines.Bus2(),
                    "units": dss.Lines.Units(),
                    "is_switch": is_switch,
                },
            )
        )
    return records


def collect_transformers() -> list[Record]:
    records: list[Record] = []
    for name in dss.Transformers.AllNames():
        dss.Transformers.Name(name)
        dss.Circuit.SetActiveElement(f"Transformer.{name}")
        buses = dss.CktElement.BusNames()
        losses_kw, losses_kvar = element_losses()
        records.append(
            Record(
                name=name,
                category="transformer",
                key=normalized_edge_key("transformer", buses, dss.CktElement.NumPhases()),
                buses=buses,
                phases=dss.CktElement.NumPhases(),
                kv=safe_float(dss.Transformers.kV()),
                kva=safe_float(dss.Transformers.kVA()),
                losses_kw=losses_kw,
                losses_kvar=losses_kvar,
                loading_pct=loading_pct_from_element(),
                voltage_drop_pu=voltage_drop_between_buses(buses),
                extra={
                    "num_windings": dss.Transformers.NumWindings(),
                },
            )
        )
    return records


def collect_loads() -> list[Record]:
    records: list[Record] = []
    for name in dss.Loads.AllNames():
        dss.Loads.Name(name)
        dss.Circuit.SetActiveElement(f"Load.{name}")
        buses = dss.CktElement.BusNames()
        solved_kw, solved_kvar = first_terminal_power()
        conn = "delta" if dss.Loads.IsDelta() else "wye"
        records.append(
            Record(
                name=name,
                category="load",
                key=normalized_terminal_key("load", buses[0], dss.CktElement.NumPhases(), conn),
                buses=buses,
                phases=dss.CktElement.NumPhases(),
                kv=safe_float(dss.Loads.kV()),
                kw=safe_float(dss.Loads.kW()),
                kvar=safe_float(dss.Loads.kvar()),
                conn=conn,
                loading_pct=None,
                voltage_drop_pu=None,
                extra={
                    "model": dss.Loads.Model(),
                    "solved_kw": solved_kw,
                    "solved_kvar": solved_kvar,
                },
            )
        )
    return records


def collect_capacitors() -> list[Record]:
    records: list[Record] = []
    for name in dss.Capacitors.AllNames():
        dss.Capacitors.Name(name)
        dss.Circuit.SetActiveElement(f"Capacitor.{name}")
        buses = dss.CktElement.BusNames()
        solved_kw, solved_kvar = first_terminal_power()
        records.append(
            Record(
                name=name,
                category="capacitor",
                key=normalized_terminal_key(
                    "capacitor", buses[0], dss.CktElement.NumPhases(), None
                ),
                buses=buses,
                phases=dss.CktElement.NumPhases(),
                kv=safe_float(dss.Capacitors.kV()),
                kvar=safe_float(dss.Capacitors.kvar()),
                extra={
                    "available_steps": dss.Capacitors.AvailableSteps(),
                    "solved_kw": solved_kw,
                    "solved_kvar": solved_kvar,
                },
            )
        )
    return records


def collect_summary(master_path: Path) -> dict[str, Any]:
    redirect_and_solve(master_path)
    voltages = dss.Circuit.AllBusMagPu()
    losses = dss.Circuit.Losses()
    total_power = dss.Circuit.TotalPower()
    return {
        "master_path": str(master_path),
        "converged": dss.Solution.Converged(),
        "num_buses": dss.Circuit.NumBuses(),
        "num_nodes": dss.Circuit.NumNodes(),
        "num_ckt_elements": dss.Circuit.NumCktElements(),
        "total_power_kw": total_power[0],
        "total_power_kvar": total_power[1],
        "losses_kw": losses[0] / 1000.0,
        "losses_kvar": losses[1] / 1000.0,
        "min_voltage_pu": min(voltages),
        "max_voltage_pu": max(voltages),
        "avg_voltage_pu": sum(voltages) / len(voltages),
        "buses": collect_buses(),
        "lines": [asdict(item) for item in collect_lines()],
        "transformers": [asdict(item) for item in collect_transformers()],
        "loads": [asdict(item) for item in collect_loads()],
        "capacitors": [asdict(item) for item in collect_capacitors()],
    }


def compare_scalar(expected: float | None, actual: float | None) -> dict[str, Any]:
    if expected is None and actual is None:
        return {"expected": None, "actual": None, "delta": None, "pct_delta": None}
    if expected is None or actual is None:
        return {"expected": expected, "actual": actual, "delta": None, "pct_delta": None}
    delta = actual - expected
    pct_delta = None if expected == 0 else (delta / expected * 100.0)
    return {
        "expected": expected,
        "actual": actual,
        "delta": delta,
        "pct_delta": pct_delta,
    }


def index_records(records: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[record["key"]].append(record)
    return grouped


def compare_record_groups(
    category: str,
    original: list[dict[str, Any]],
    converted: list[dict[str, Any]],
    metric_fields: list[str],
) -> dict[str, Any]:
    original_index = index_records(original)
    converted_index = index_records(converted)
    all_keys = sorted(set(original_index) | set(converted_index))

    matched = []
    unmatched = []
    group_mismatches = []

    for key in all_keys:
        original_group = original_index.get(key, [])
        converted_group = converted_index.get(key, [])
        if len(original_group) == 1 and len(converted_group) == 1:
            original_record = original_group[0]
            converted_record = converted_group[0]
            metrics = {
                field: compare_scalar(original_record.get(field), converted_record.get(field))
                for field in metric_fields
            }
            largest_abs_delta = max(
                (
                    abs(details["delta"])
                    for details in metrics.values()
                    if details["delta"] is not None
                ),
                default=0.0,
            )
            matched.append(
                {
                    "key": key,
                    "original_name": original_record["name"],
                    "converted_name": converted_record["name"],
                    "buses": original_record.get("buses") or converted_record.get("buses"),
                    "metrics": metrics,
                    "largest_abs_delta": largest_abs_delta,
                }
            )
        elif not original_group or not converted_group:
            unmatched.append(
                {
                    "key": key,
                    "original": [item["name"] for item in original_group],
                    "converted": [item["name"] for item in converted_group],
                }
            )
        else:
            group_mismatches.append(
                {
                    "key": key,
                    "original": [item["name"] for item in original_group],
                    "converted": [item["name"] for item in converted_group],
                }
            )

    matched.sort(key=lambda item: item["largest_abs_delta"], reverse=True)
    return {
        "category": category,
        "original_count": len(original),
        "converted_count": len(converted),
        "matched_count": len(matched),
        "unmatched_count": len(unmatched),
        "group_mismatch_count": len(group_mismatches),
        "matched": matched,
        "unmatched": unmatched,
        "group_mismatches": group_mismatches,
    }


def compare_buses(original: dict[str, Any], converted: dict[str, Any]) -> dict[str, Any]:
    original_buses = original["buses"]
    converted_buses = converted["buses"]
    all_bus_names = sorted(set(original_buses) | set(converted_buses))
    matched = []
    unmatched = []
    for name in all_bus_names:
        orig = original_buses.get(name)
        conv = converted_buses.get(name)
        if orig and conv:
            matched.append(
                {
                    "bus": name,
                    "min_pu": compare_scalar(orig["min_pu"], conv["min_pu"]),
                    "max_pu": compare_scalar(orig["max_pu"], conv["max_pu"]),
                    "avg_pu": compare_scalar(orig["avg_pu"], conv["avg_pu"]),
                    "kv_base": compare_scalar(orig["kv_base"], conv["kv_base"]),
                }
            )
        else:
            unmatched.append(
                {
                    "bus": name,
                    "original": bool(orig),
                    "converted": bool(conv),
                }
            )
    matched.sort(
        key=lambda item: abs(item["avg_pu"]["delta"])
        if item["avg_pu"]["delta"] is not None
        else 0.0,
        reverse=True,
    )
    return {
        "original_count": len(original_buses),
        "converted_count": len(converted_buses),
        "matched_count": len(matched),
        "unmatched_count": len(unmatched),
        "matched": matched,
        "unmatched": unmatched,
    }


def build_report(
    original_summary: dict[str, Any], converted_summary: dict[str, Any]
) -> dict[str, Any]:
    return {
        "circuit": {
            "total_power_kw": compare_scalar(
                original_summary["total_power_kw"], converted_summary["total_power_kw"]
            ),
            "total_power_kvar": compare_scalar(
                original_summary["total_power_kvar"], converted_summary["total_power_kvar"]
            ),
            "losses_kw": compare_scalar(
                original_summary["losses_kw"], converted_summary["losses_kw"]
            ),
            "losses_kvar": compare_scalar(
                original_summary["losses_kvar"], converted_summary["losses_kvar"]
            ),
            "min_voltage_pu": compare_scalar(
                original_summary["min_voltage_pu"], converted_summary["min_voltage_pu"]
            ),
            "max_voltage_pu": compare_scalar(
                original_summary["max_voltage_pu"], converted_summary["max_voltage_pu"]
            ),
            "avg_voltage_pu": compare_scalar(
                original_summary["avg_voltage_pu"], converted_summary["avg_voltage_pu"]
            ),
            "num_buses": compare_scalar(
                original_summary["num_buses"], converted_summary["num_buses"]
            ),
            "num_ckt_elements": compare_scalar(
                original_summary["num_ckt_elements"], converted_summary["num_ckt_elements"]
            ),
        },
        "buses": compare_buses(original_summary, converted_summary),
        "lines": compare_record_groups(
            "lines",
            [item for item in original_summary["lines"] if item["category"] == "line"],
            [item for item in converted_summary["lines"] if item["category"] == "line"],
            ["length_km", "losses_kw", "losses_kvar", "loading_pct", "voltage_drop_pu"],
        ),
        "switches": compare_record_groups(
            "switches",
            [item for item in original_summary["lines"] if item["category"] == "switch"],
            [item for item in converted_summary["lines"] if item["category"] == "switch"],
            ["losses_kw", "losses_kvar", "loading_pct", "voltage_drop_pu"],
        ),
        "transformers": compare_record_groups(
            "transformers",
            original_summary["transformers"],
            converted_summary["transformers"],
            ["kv", "kva", "losses_kw", "losses_kvar", "loading_pct", "voltage_drop_pu"],
        ),
        "loads": compare_record_groups(
            "loads",
            original_summary["loads"],
            converted_summary["loads"],
            ["kv", "kw", "kvar"],
        ),
        "capacitors": compare_record_groups(
            "capacitors",
            original_summary["capacitors"],
            converted_summary["capacitors"],
            ["kv", "kvar"],
        ),
    }


def print_metric(label: str, metric: dict[str, Any]) -> None:
    expected = metric["expected"]
    actual = metric["actual"]
    delta = metric["delta"]
    pct = metric["pct_delta"]
    if delta is None:
        print(f"  {label:<18} expected={expected} actual={actual}")
        return
    pct_str = "n/a" if pct is None else f"{pct:+.2f}%"
    print(
        f"  {label:<18} expected={expected:.6f} actual={actual:.6f} "
        f"delta={delta:+.6f} pct={pct_str}"
    )


def print_top_matches(category_report: dict[str, Any], top_n: int) -> None:
    print(
        f"{category_report['category'].title()}: "
        f"original={category_report['original_count']} converted={category_report['converted_count']} "
        f"matched={category_report['matched_count']} unmatched={category_report['unmatched_count']} "
        f"group_mismatches={category_report['group_mismatch_count']}"
    )
    for item in category_report["matched"][:top_n]:
        print(
            f"  {item['original_name']} -> {item['converted_name']} buses={item['buses']} "
            f"largest_abs_delta={item['largest_abs_delta']:.6f}"
        )
        for metric_name, details in item["metrics"].items():
            print_metric(metric_name, details)
    if category_report["unmatched"]:
        print("  Unmatched keys:")
        for item in category_report["unmatched"][:top_n]:
            print(
                f"    key={item['key']} original={item['original']} converted={item['converted']}"
            )
    if category_report["group_mismatches"]:
        print("  Group mismatches:")
        for item in category_report["group_mismatches"][:top_n]:
            print(
                f"    key={item['key']} original={item['original']} converted={item['converted']}"
            )


def main() -> None:
    args = parse_args()
    original_master = find_master_file(args.original)
    converted_master = find_master_file(args.converted)

    original_summary = collect_summary(original_master)
    converted_summary = collect_summary(converted_master)
    report = {
        "original": {
            key: value
            for key, value in original_summary.items()
            if key not in {"buses", "lines", "transformers", "loads", "capacitors"}
        },
        "converted": {
            key: value
            for key, value in converted_summary.items()
            if key not in {"buses", "lines", "transformers", "loads", "capacitors"}
        },
        "comparison": build_report(original_summary, converted_summary),
    }

    args.report.write_text(json.dumps(report, indent=2))

    print("Circuit summary")
    for metric_name, metric in report["comparison"]["circuit"].items():
        print_metric(metric_name, metric)

    bus_report = report["comparison"]["buses"]
    print(
        f"\nBuses: original={bus_report['original_count']} converted={bus_report['converted_count']} "
        f"matched={bus_report['matched_count']} unmatched={bus_report['unmatched_count']}"
    )
    for item in bus_report["matched"][: args.top]:
        print(f"  bus={item['bus']}")
        print_metric("min_pu", item["min_pu"])
        print_metric("max_pu", item["max_pu"])
        print_metric("avg_pu", item["avg_pu"])

    for category in ["lines", "switches", "transformers", "loads", "capacitors"]:
        print()
        print_top_matches(report["comparison"][category], args.top)

    print(f"\nWrote JSON report to {args.report}")


if __name__ == "__main__":
    main()
