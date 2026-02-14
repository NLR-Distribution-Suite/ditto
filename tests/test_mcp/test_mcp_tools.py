"""Tests for the DiTTo MCP server tools and resources."""

from pathlib import Path

import pytest

from ditto.mcp.server import (
    _SYNC_STATE,
    convert_model,
    export_gdm_json,
    get_component_detail,
    get_components,
    get_system_summary,
    list_loaded_systems,
    list_readers,
    list_writers,
    load_gdm_json,
    read_opendss_model,
    write_opendss,
)

# ---------------------------------------------------------------------------
# Paths to test data
# ---------------------------------------------------------------------------

_BASE = Path(__file__).parents[1]
_IEEE13_DSS = _BASE / "data" / "opendss_circuit_models" / "ieee13" / "Master.dss"
_CIM_XML = _BASE / "data" / "cim_iec_61968_13" / "IEEE13Nodeckt_CIM100x.XML"


# ---------------------------------------------------------------------------
# Discovery tools
# ---------------------------------------------------------------------------


def test_list_readers():
    readers = list_readers()
    assert isinstance(readers, list)
    assert "opendss" in readers
    assert "cim_iec_61968_13" in readers


def test_list_writers():
    writers = list_writers()
    assert isinstance(writers, list)
    assert "opendss" in writers


# ---------------------------------------------------------------------------
# OpenDSS reader
# ---------------------------------------------------------------------------


class TestOpenDSSModel:
    """Tests that load the IEEE 13-node OpenDSS model."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        """Load the model once and clean up after."""
        _SYNC_STATE.systems.clear()
        read_opendss_model(str(_IEEE13_DSS), name="ieee13")
        yield
        _SYNC_STATE.systems.clear()

    def test_read_opendss_model(self):
        assert "ieee13" in _SYNC_STATE.systems

    def test_list_loaded_systems(self):
        result = list_loaded_systems()
        assert "ieee13" in result

    def test_get_system_summary(self):
        summary = get_system_summary("ieee13")
        assert summary["name"] == "ieee13"
        assert isinstance(summary["component_types"], dict)
        assert summary["total_components"] > 0

    def test_get_components_buses(self):
        components = get_components("DistributionBus", name="ieee13")
        assert isinstance(components, list)
        assert len(components) > 0
        assert "name" in components[0]

    def test_get_components_limit(self):
        components = get_components("DistributionBus", name="ieee13", limit=2)
        assert len(components) <= 2

    def test_get_component_detail(self):
        buses = get_components("DistributionBus", name="ieee13", limit=1)
        assert len(buses) > 0
        bus_name = buses[0]["name"]
        detail = get_component_detail("DistributionBus", bus_name, name="ieee13")
        assert isinstance(detail, dict)
        assert "name" in detail

    def test_write_opendss(self, tmp_path):
        out = tmp_path / "opendss_out"
        result = write_opendss(name="ieee13", output_path=str(out))
        assert "written" in result.lower() or "OpenDSS" in result
        assert out.exists()

    def test_export_gdm_json(self, tmp_path):
        json_path = tmp_path / "model.json"
        result = export_gdm_json(name="ieee13", output_path=str(json_path))
        assert "exported" in result.lower() or "JSON" in result
        assert json_path.exists()

    def test_load_gdm_json_roundtrip(self, tmp_path):
        json_path = tmp_path / "model.json"
        export_gdm_json(name="ieee13", output_path=str(json_path))

        _SYNC_STATE.systems.pop("reloaded", None)
        result = load_gdm_json(str(json_path), name="reloaded")
        assert result["name"] == "reloaded"
        assert result["total_components"] > 0


# ---------------------------------------------------------------------------
# Conversion tool
# ---------------------------------------------------------------------------


class TestConvertModel:
    @pytest.fixture(autouse=True)
    def _setup(self):
        _SYNC_STATE.systems.clear()
        yield
        _SYNC_STATE.systems.clear()

    def test_convert_opendss_to_opendss(self, tmp_path):
        out = tmp_path / "converted"
        result = convert_model(
            reader_type="opendss",
            writer_type="opendss",
            input_path=str(_IEEE13_DSS),
            output_path=str(out),
        )
        assert "complete" in result.lower()
        assert out.exists()

    def test_convert_unknown_reader(self, tmp_path):
        result = convert_model(
            reader_type="nonexistent_format",
            writer_type="opendss",
            input_path="/tmp/fake",
            output_path=str(tmp_path),
        )
        assert "Unknown reader" in result

    def test_convert_unknown_writer(self, tmp_path):
        result = convert_model(
            reader_type="opendss",
            writer_type="nonexistent_format",
            input_path="/tmp/fake",
            output_path=str(tmp_path),
        )
        assert "Unknown writer" in result


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


def test_get_system_summary_not_loaded():
    _SYNC_STATE.systems.clear()
    with pytest.raises(KeyError, match="No system loaded"):
        get_system_summary("nosuchsystem")


def test_get_components_bad_type():
    _SYNC_STATE.systems.clear()
    read_opendss_model(str(_IEEE13_DSS), name="tmp")
    with pytest.raises(ValueError, match="Unknown component type"):
        get_components("NonExistentComponent", name="tmp")
    _SYNC_STATE.systems.clear()
