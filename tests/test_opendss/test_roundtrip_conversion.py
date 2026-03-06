from pathlib import Path

import numpy as np
import pytest

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
    ), "Round trip coversion exceeds error tolerance"
