from rdflib import Graph, Literal, Namespace, RDF, URIRef

from ditto.readers.cim_iec_61968_13.queries import (
    query_batteries,
    query_capacitors,
    query_distribution_buses,
    query_distribution_regulators,
    query_line_codes,
    query_line_segments,
    query_load_break_switches,
    query_loads,
    query_power_transformers,
    query_regulator_controllers,
    query_source,
    query_transformer_windings,
)


_CIM = Namespace("http://iec.ch/TC57/CIM100#")


def _empty_cim_graph() -> Graph:
    graph = Graph()
    graph.bind("cim", _CIM)
    graph.bind("rdf", RDF)
    return graph


def test_query_contracts_empty_graph_schema():
    graph = _empty_cim_graph()

    expectations = [
        (
            query_distribution_buses,
            ["x", "y", "rated_voltage", "bus"],
        ),
        (
            query_line_segments,
            [
                "line",
                "voltage",
                "length",
                "phase_count",
                "line_code",
                "bus_1",
                "phases_1",
                "bus_2",
                "phases_2",
            ],
        ),
        (
            query_line_codes,
            ["line_code", "phase_count", "r", "x", "b", "ampacity_normal", "ampacity_emergency"],
        ),
        (
            query_load_break_switches,
            [
                "switch_name",
                "capacity",
                "ratedCurrent",
                "normally_open",
                "is_open",
                "voltage",
                "bus_1",
                "bus_2",
            ],
        ),
        (
            query_power_transformers,
            [
                "xfmr",
                "apparent_power",
                "rated_voltage",
                "vector_group",
                "per_resistance",
                "conn",
                "angle",
                "winding",
                "bus",
                "xfmr_end",
            ],
        ),
        (
            query_distribution_regulators,
            [
                "xfmr",
                "apparent_power",
                "rated_voltage",
                "per_resistance",
                "conn",
                "angle",
                "winding",
                "bus",
                "xfmr_end",
                "phase",
                "max_tap",
                "min_tap",
                "neutral_tap",
                "normal_tap",
                "dv",
                "current_tap",
                "z_1_leakage",
                "z_0_leakage",
                "z_1_loadloss",
                "z_0_loadloss",
            ],
        ),
        (
            query_transformer_windings,
            ["winding", "r1", "x1", "r0", "x0", "xfmr_end_1", "xfmr_end_2"],
        ),
        (
            query_capacitors,
            [
                "capacitor",
                "rated_voltage",
                "conn",
                "bus",
                "b1",
                "g1",
                "b0",
                "g0",
                "phase",
                "steps",
            ],
        ),
        (
            query_source,
            ["source", "rated_voltage", "src_voltage", "src_angle", "r1", "x1", "r0", "x0", "bus"],
        ),
        (
            query_loads,
            [
                "load",
                "active power",
                "reactive power",
                "rated_voltage",
                "grounded",
                "phase",
                "conn",
                "bus",
                "z_p",
                "i_p",
                "p_p",
                "z_q",
                "i_q",
                "p_q",
                "p_exp",
                "q_exp",
            ],
        ),
        (
            query_batteries,
            [
                "battery",
                "rated_energy",
                "stored_energy",
                "max_p",
                "p",
                "q",
                "rated_s",
                "rated_voltage",
                "phase",
                "bus",
            ],
        ),
        (
            query_regulator_controllers,
            [
                "regulator",
                "neutral_voltage",
                "initial_delay",
                "subsequent_delay",
                "ltc_flag",
                "enabled",
                "pt_ratio",
                "ct_ratio",
                "ct_rating",
                "mode",
                "bus",
                "phase",
                "target",
                "deadband",
                "ldc",
                "line_drop_r",
                "line_drop_x",
                "reversible",
                "max_voltage",
                "min_voltage",
            ],
        ),
    ]

    for query_func, expected_columns in expectations:
        dataframe = query_func(graph)
        assert dataframe.empty
        assert list(dataframe.columns) == expected_columns


def test_query_batteries_minimal_graph_normalizes_and_orders_phases():
    graph = _empty_cim_graph()

    unit = URIRef("urn:test:battery-unit:1")
    pec = URIRef("urn:test:pec:1")
    base_voltage = URIRef("urn:test:base-voltage:1")
    terminal = URIRef("urn:test:terminal:1")
    node = URIRef("urn:test:node:1")
    phase_c = URIRef("urn:test:pec-phase:c")
    phase_a = URIRef("urn:test:pec-phase:a")

    graph.add((unit, RDF.type, _CIM.BatteryUnit))
    graph.add((unit, _CIM["IdentifiedObject.name"], Literal("battery_1")))
    graph.add((unit, _CIM["BatteryUnit.ratedE"], Literal(120.0)))
    graph.add((unit, _CIM["BatteryUnit.storedE"], Literal(80.0)))

    graph.add((pec, RDF.type, _CIM.PowerElectronicsConnection))
    graph.add((pec, _CIM["PowerElectronicsConnection.PowerElectronicsUnit"], unit))
    graph.add((pec, _CIM["PowerElectronicsConnection.maxP"], Literal(30.0)))
    graph.add((pec, _CIM["PowerElectronicsConnection.p"], Literal(5.0)))
    graph.add((pec, _CIM["PowerElectronicsConnection.q"], Literal(1.5)))
    graph.add((pec, _CIM["PowerElectronicsConnection.ratedS"], Literal(35.0)))
    graph.add((pec, _CIM["ConductingEquipment.BaseVoltage"], base_voltage))

    graph.add((base_voltage, _CIM["BaseVoltage.nominalVoltage"], Literal(12470.0)))

    graph.add((terminal, RDF.type, _CIM.Terminal))
    graph.add((terminal, _CIM["Terminal.ConductingEquipment"], pec))
    graph.add((terminal, _CIM["Terminal.ConnectivityNode"], node))
    graph.add((node, _CIM["IdentifiedObject.name"], Literal("bus_1")))

    graph.add((phase_c, RDF.type, _CIM.PowerElectronicsConnectionPhase))
    graph.add((phase_c, _CIM["PowerElectronicsConnectionPhase.PowerElectronicsConnection"], pec))
    graph.add((phase_c, _CIM["PowerElectronicsConnectionPhase.phase"], _CIM["SinglePhaseKind.C"]))

    graph.add((phase_a, RDF.type, _CIM.PowerElectronicsConnectionPhase))
    graph.add((phase_a, _CIM["PowerElectronicsConnectionPhase.PowerElectronicsConnection"], pec))
    graph.add((phase_a, _CIM["PowerElectronicsConnectionPhase.phase"], _CIM["SinglePhaseKind.A"]))

    dataframe = query_batteries(graph)

    assert len(dataframe) == 1
    assert dataframe["battery"].iloc[0] == "battery_1"
    assert dataframe["bus"].iloc[0] == "bus_1"
    assert dataframe["phase"].iloc[0] == "A,C"


def test_query_line_segments_single_terminal_line_returns_empty_schema():
    graph = _empty_cim_graph()

    line = URIRef("urn:test:line:1")
    line_phase = URIRef("urn:test:line-phase:1")
    terminal = URIRef("urn:test:terminal:1")
    node = URIRef("urn:test:node:1")
    base_voltage = URIRef("urn:test:base-voltage:1")
    impedance = URIRef("urn:test:per-length-impedance:1")

    graph.add((line, RDF.type, _CIM.ACLineSegment))
    graph.add((line, _CIM["IdentifiedObject.name"], Literal("line_1")))
    graph.add((line, _CIM["Conductor.length"], Literal(100.0)))
    graph.add((line, _CIM["ConductingEquipment.BaseVoltage"], base_voltage))
    graph.add((base_voltage, _CIM["BaseVoltage.nominalVoltage"], Literal(12470.0)))

    graph.add((line_phase, _CIM["ACLineSegmentPhase.ACLineSegment"], line))
    graph.add((line_phase, _CIM["ACLineSegmentPhase.phase"], _CIM["SinglePhaseKind.A"]))

    graph.add((line, _CIM["ACLineSegment.PerLengthImpedance"], impedance))
    graph.add((impedance, _CIM["PerLengthPhaseImpedance.conductorCount"], Literal(1)))
    graph.add((impedance, _CIM["IdentifiedObject.name"], Literal("code_1")))

    graph.add((terminal, RDF.type, _CIM.Terminal))
    graph.add((terminal, _CIM["Terminal.ConductingEquipment"], line))
    graph.add((terminal, _CIM["Terminal.ConnectivityNode"], node))
    graph.add((node, _CIM["IdentifiedObject.name"], Literal("bus_1")))

    dataframe = query_line_segments(graph)

    assert dataframe.empty
    assert list(dataframe.columns) == [
        "line",
        "voltage",
        "length",
        "phase_count",
        "line_code",
        "bus_1",
        "phases_1",
        "bus_2",
        "phases_2",
    ]
