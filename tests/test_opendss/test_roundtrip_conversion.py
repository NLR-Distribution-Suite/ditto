from pathlib import Path

import numpy as np
import pytest
import opendssdirect as odd

from ditto.writers.opendss.write import Writer
from ditto.readers.opendss.reader import Reader
from ditto.enumerations import OpenDSSFileTypes
from tests.helpers import get_metrics

test_folder = Path(__file__).parent.parent


TEST_MODELS = [
    test_folder
    / "data"
    / "opendss_circuit_models"
    / "ieee13"
    / OpenDSSFileTypes.MASTER_FILE.value,
    test_folder / "data" / "opendss_circuit_models" / "P4U" / OpenDSSFileTypes.MASTER_FILE.value,
]


@pytest.mark.parametrize("DSS_MODEL", TEST_MODELS)
def test_opendss_roundtrip_converion(DSS_MODEL, tmp_path):
    pre_converion_metrics = get_metrics(DSS_MODEL)
    reader = Reader(DSS_MODEL)
    writer = Writer(reader.get_system())

    assert tmp_path.exists(), f"Export path: {tmp_path}"
    writer.write(tmp_path, separate_substations=False, separate_feeders=False)
    dss_master_file = tmp_path / OpenDSSFileTypes.MASTER_FILE.value
    assert dss_master_file.exists()
    post_converion_metrics = get_metrics(dss_master_file)
    assert np.allclose(
        pre_converion_metrics, post_converion_metrics, rtol=0.01, atol=0.01
    ), f"Round trip coversion exceeds error tolerance, \npre: {pre_converion_metrics}, \npost: {post_converion_metrics}"


def _redirect_without_control_changes(master_file: Path) -> None:
    odd.Basic.ClearAll()
    odd.Text.Command(f'redirect "{master_file}"')
    odd.Solution.Solve()


def test_roundtrip_preserves_load_voltage_and_cvr_properties(tmp_path):
    """ZIP canonicalization must not discard source load operating limits."""

    source = test_folder / "data" / "opendss_circuit_models" / "ckt7" / "Master.dss"
    reader = Reader(source)
    Writer(reader.get_system()).write(tmp_path, separate_substations=False, separate_feeders=False)

    _redirect_without_control_changes(tmp_path / OpenDSSFileTypes.MASTER_FILE.value)
    odd.Loads.Name("1001577-d1")

    assert odd.Loads.Model() == 4
    assert odd.Loads.Vminpu() == pytest.approx(0.85)
    assert odd.Loads.Vmaxpu() == pytest.approx(1.05)
    assert odd.Loads.CVRwatts() == pytest.approx(0.8)
    assert odd.Loads.CVRvars() == pytest.approx(3.0)


def test_roundtrip_preserves_center_tapped_transformer_connections(tmp_path):
    """A center-tapped transformer must not be split as a generic two-phase unit."""

    source = test_folder / "data" / "opendss_circuit_models" / "SFO" / "Master.dss"
    reader = Reader(source)
    Writer(reader.get_system()).write(tmp_path, separate_substations=False, separate_feeders=False)

    _redirect_without_control_changes(tmp_path / OpenDSSFileTypes.MASTER_FILE.value)
    name = "tr(r:p10udt6041-p10udt6041lv)"
    odd.Transformers.Name(name)

    assert odd.Transformers.NumWindings() == 3
    assert odd.CktElement.NumPhases() == 1
    assert odd.CktElement.BusNames() == [
        "p10udt6041.1.3",
        "p10udt6041lv.1.0",
        "p10udt6041lv.0.2",
    ]

    odd.Transformers.Wdg(1)
    assert odd.Transformers.kV() == pytest.approx(12.47)
    odd.Transformers.Wdg(2)
    assert odd.Transformers.kV() == pytest.approx(0.12)
    odd.Transformers.Wdg(3)
    assert odd.Transformers.kV() == pytest.approx(0.12)


def test_roundtrip_preserves_transformer_magnetizing_current(tmp_path):
    """Transformer %imag must survive the GDM equipment conversion."""

    source = test_folder / "data" / "opendss_circuit_models" / "ckt7" / "Master.dss"
    reader = Reader(source)
    Writer(reader.get_system()).write(tmp_path, separate_substations=False, separate_feeders=False)

    _redirect_without_control_changes(tmp_path / OpenDSSFileTypes.MASTER_FILE.value)
    odd.Text.Command("? Transformer.1001577_xfmr_abc.%imag")

    assert float(odd.Text.Result()) == pytest.approx(1.0)
