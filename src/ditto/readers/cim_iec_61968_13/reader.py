from pathlib import Path

from gdm.distribution.equipment import MatrixImpedanceBranchEquipment
from gdm.distribution.controllers import RegulatorController
from gdm.distribution import DistributionSystem
from gdm.distribution.components import (
    DistributionComponentBase,
    DistributionBattery,
    DistributionVoltageSource,
    DistributionTransformer,
    MatrixImpedanceBranch,
    DistributionCapacitor,
    DistributionRegulator,
    MatrixImpedanceSwitch,
    DistributionLoad,
    DistributionBus,
)
from loguru import logger
from rdflib import Graph
import pandas as pd


from ditto.readers.cim_iec_61968_13.queries import (
    query_distribution_regulators,
    query_regulator_controllers,
    query_transformer_windings,
    query_load_break_switches,
    query_power_transformers,
    query_distribution_buses,
    query_line_segments,
    query_line_codes,
    query_capacitors,
    query_batteries,
    query_source,
    query_loads,
)
import ditto.readers.cim_iec_61968_13 as cim_mapper
from ditto.readers.reader import AbstractReader


class Reader(AbstractReader):
    # NOTE:  Do not change sequnce of the component types below.
    component_types: list[type[DistributionComponentBase]] = [
        DistributionBus,
        DistributionLoad,
        DistributionBattery,
        DistributionCapacitor,
        DistributionVoltageSource,
        RegulatorController,
        MatrixImpedanceBranchEquipment,
        MatrixImpedanceBranch,
        DistributionTransformer,
        DistributionRegulator,
        MatrixImpedanceSwitch,
    ]

    def __init__(self, cim_file: str | Path):
        cim_file = Path(cim_file)
        if not cim_file.exists():
            raise FileNotFoundError(f"{cim_file} does not exist")
        self.system = DistributionSystem(auto_add_composed_components=True)
        self.graph = Graph()
        self.graph.parse(cim_file, format="xml")

    def read(self):
        datasets: dict[DistributionComponentBase, pd.DataFrame] = {}
        logger.debug("Querying for distribution buses...")
        datasets[DistributionBus] = query_distribution_buses(self.graph)

        logger.debug("Querying for AC line segments...")
        datasets[MatrixImpedanceBranch] = query_line_segments(self.graph)

        logger.debug("Querying for line codes...")
        datasets[MatrixImpedanceBranchEquipment] = query_line_codes(self.graph)

        logger.debug("Querying for loads...")
        datasets[DistributionLoad] = query_loads(self.graph)

        logger.debug("Querying for capacitors...")
        datasets[DistributionCapacitor] = query_capacitors(self.graph)

        logger.debug("Querying for batteries...")
        datasets[DistributionBattery] = query_batteries(self.graph)

        logger.debug("Querying for transformers...")
        xfmr_data = query_power_transformers(self.graph)
        logger.debug("Querying for transformer windings...")
        winding_data = query_transformer_windings(self.graph)
        datasets[DistributionTransformer] = self._build_xfmr_dataset(xfmr_data, winding_data)

        logger.debug("Querying for regulators...")
        regulator_data = query_distribution_regulators(self.graph)
        datasets[DistributionRegulator] = self._build_xfmr_dataset(regulator_data)

        logger.debug("Querying for sources...")
        datasets[DistributionVoltageSource] = query_source(self.graph)

        logger.debug("Querying for regulator controllers...")
        datasets[RegulatorController] = query_regulator_controllers(self.graph)

        logger.debug("Querying for load break switches...")
        datasets[MatrixImpedanceSwitch] = query_load_break_switches(self.graph)

        datasets[DistributionBus] = self._set_bus_phases(datasets)

        query_summary = {
            component_type.__name__: int(len(dataframe))
            for component_type, dataframe in datasets.items()
        }
        logger.info(f"CIM query row counts: {query_summary}")

        parse_summary: dict[str, dict[str, int]] = {}

        for component_type in self.component_types:
            mapper_name = component_type.__name__ + "Mapper"
            components = []
            row_count = 0
            if component_type in datasets:
                try:
                    mapper = getattr(cim_mapper, mapper_name)(self.system)
                    logger.debug(f"Buliding components for {component_type.__name__}")
                except AttributeError as _:
                    logger.warning(f"Mapper for {mapper_name} not found. Skipping")
                    parse_summary[component_type.__name__] = {
                        "rows": int(len(datasets[component_type])),
                        "parsed": 0,
                    }
                    continue
                if datasets[component_type].empty:
                    logger.warning(
                        f"Dataframe for {component_type.__name__} is empty. Check query."
                    )
                for row_index, row in datasets[component_type].iterrows():
                    row_count += 1
                    try:
                        model_entry = mapper.parse(row)
                    except Exception as error:
                        component_name = row.get("name") if hasattr(row, "get") else None
                        if component_name is None and hasattr(row, "get"):
                            component_name = (
                                row.get("xfmr") or row.get("line") or row.get("switch_name")
                            )
                        raise ValueError(
                            f"Failed parsing {component_type.__name__} row {row_index}"
                            + (f" (name={component_name})" if component_name is not None else "")
                        ) from error
                    components.append(model_entry)
            else:
                logger.warning(f"Dataframe for {component_type.__name__} not found. Skipping")
            self.system.add_components(*components)
            parse_summary[component_type.__name__] = {
                "rows": row_count,
                "parsed": int(len(components)),
            }

        logger.info(f"CIM parse summary: {parse_summary}")
        logger.info("System summary: ", self.system.info())

    def _select_transformer_winding_rows(
        self, xfmr_df: pd.DataFrame, windings: list
    ) -> tuple[list[str], list[pd.Series]]:
        selected_buses: list[str] = []
        winding_rows: list[pd.Series] = []

        for winding in windings:
            winding_rows_df = xfmr_df[xfmr_df["winding"] == winding]
            if winding_rows_df.empty:
                continue

            bus_candidates = winding_rows_df["bus"].drop_duplicates().to_list()
            selected_bus = next(
                (candidate for candidate in bus_candidates if candidate not in selected_buses),
                bus_candidates[0],
            )
            selected_buses.append(selected_bus)

            selected_row = winding_rows_df[winding_rows_df["bus"] == selected_bus]
            winding_rows.append(selected_row.iloc[0])

        return selected_buses, winding_rows

    def _build_winding_series(self, winding_rows: list[pd.Series], windings: list) -> pd.Series:
        winding_df = pd.DataFrame(winding_rows).drop(columns=["winding", "bus"], errors="ignore")

        winding_series = []
        for winding, (_, winding_data) in zip(windings, winding_df.iterrows()):
            winding_data.index = [
                f"wdg_{winding}_" + column_name for column_name in winding_data.index
            ]
            winding_series.append(winding_data)

        return pd.concat(winding_series)

    def _attach_winding_coupling_data(self, wdgs: pd.Series, winding_df: pd.DataFrame) -> None:
        for _, wdg_coupling_data in winding_df.iterrows():
            xfmr_ends = {wdg_coupling_data["xfmr_end_1"], wdg_coupling_data["xfmr_end_2"]}
            if not xfmr_ends.intersection(wdgs.to_list()):
                continue

            wdgs["r0"] = wdg_coupling_data["r0"]
            wdgs["r1"] = wdg_coupling_data["r1"]
            wdgs["x0"] = wdg_coupling_data["x0"]
            wdgs["x1"] = wdg_coupling_data["x1"]
            wdgs["winding"] = wdg_coupling_data["winding"]

    def _build_xfmr_dataset(
        self, xfmr_data: pd.DataFrame, winding_df: pd.DataFrame = pd.DataFrame()
    ) -> pd.DataFrame:
        if xfmr_data.empty or "xfmr" not in xfmr_data.columns:
            return pd.DataFrame()

        xfms = []
        for xfmr in xfmr_data["xfmr"].unique():
            xfmr_df = xfmr_data[xfmr_data["xfmr"] == xfmr].copy()
            xfmr_df.drop(columns=["xfmr"], inplace=True, errors="ignore")
            windings = xfmr_df["winding"].drop_duplicates().to_list()
            selected_buses, winding_rows = self._select_transformer_winding_rows(xfmr_df, windings)

            if not winding_rows:
                continue

            wdgs = self._build_winding_series(winding_rows, windings)
            if selected_buses:
                wdgs["bus_1"] = selected_buses[0]
                wdgs["bus_2"] = selected_buses[1] if len(selected_buses) > 1 else selected_buses[0]
            wdgs["xfmr"] = xfmr
            self._attach_winding_coupling_data(wdgs, winding_df)
            xfms.append(wdgs)

        return pd.DataFrame(xfms)

    def _set_bus_phases(
        self, df_dict: dict[DistributionComponentBase, pd.DataFrame]
    ) -> pd.DataFrame:
        all_phases = []
        bus_df = df_dict[DistributionBus].copy()
        phase_columns = ["phase", "phases_1", "phases_2"]
        bus_columns = ["bus", "bus_1", "bus_2"]

        bus_phases_lookup: dict[str, list[str]] = {}
        for df_type, df in df_dict.items():
            if df_type == DistributionBus or not isinstance(df, pd.DataFrame) or df.empty:
                continue

            available_bus_columns = [column for column in bus_columns if column in df.columns]
            available_phase_columns = [column for column in phase_columns if column in df.columns]
            if not available_bus_columns or not available_phase_columns:
                continue

            for bus_column in available_bus_columns:
                for phase_column in available_phase_columns:
                    subset = df[[bus_column, phase_column]].dropna(subset=[bus_column])
                    for bus_name, phase_value in subset.itertuples(index=False):
                        phase_text = "" if phase_value is None else str(phase_value)
                        cleaned = phase_text.replace(",", "").replace("N", "")
                        phase_list = [phase for phase in cleaned if len(phase) == 1]
                        if not phase_list:
                            continue
                        bus_phases_lookup.setdefault(str(bus_name), []).extend(phase_list)

        for _, bus_data in bus_df.iterrows():
            bus_name = bus_data["bus"]
            phases = sorted(set(bus_phases_lookup.get(bus_name, [])))
            phases = sorted(phases)
            if not phases:
                phases = ["A", "B", "C"]
            all_phases.append(",".join(phases))

        bus_df["phase"] = all_phases
        return bus_df

    def get_system(self) -> DistributionSystem:
        return self.system
