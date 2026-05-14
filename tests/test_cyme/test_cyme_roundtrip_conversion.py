from pathlib import Path

import numpy as np
import pandas as pd

from ditto.enumerations import OpenDSSFileTypes
from ditto.readers.cyme.reader import Reader as CymeReader
from ditto.writers.opendss.write import Writer
from tests.helpers import get_metrics_reduced


test_folder = Path(__file__).parent.parent


def test_cyme_to_opendss_ieee13(tmp_path):
    """Convert CYME ieee_123_node to OpenDSS in .dump/converted and compare metrics."""
    cyme_folder = test_folder / "data" / "cyme_models" / "13_node"
    reference_dss = test_folder / "data" / "opendss_circuit_models" / "ieee13" / "Master.dss"

    # Save conversion artifacts in repository .dump/converted as requested.
    dump_path = tmp_path / "converted"
    dump_path.mkdir(parents=True, exist_ok=True)

    reference_metrics = get_metrics_reduced(reference_dss)

    cyme_reader = CymeReader(
        cyme_folder / "Network.txt",
        cyme_folder / "Equipment.txt",
        cyme_folder / "Load.txt",
    )
    writer = Writer(cyme_reader.get_system())
    writer.write(dump_path, separate_substations=False, separate_feeders=False)

    converted_dss = dump_path / OpenDSSFileTypes.MASTER_FILE.value
    assert converted_dss.exists(), f"Converted DSS master file not found at {converted_dss}"

    converted_metrics = get_metrics_reduced(converted_dss)

    comparison = pd.DataFrame(
        [
            reference_metrics,
            converted_metrics,
            np.subtract(reference_metrics, converted_metrics) / reference_metrics * 100,
        ],
        index=["Original", "Converted", "Difference (%)"],
        columns=[
            "Min Voltage (pu)",
            "Max Voltage (pu)",
            "Avg Voltage (pu)",
            "Feeder Head P (kW)",
            "Feeder Head Q (kvar)",
        ],
    )

    assert np.allclose(
        reference_metrics, converted_metrics, rtol=0.01, atol=0.01
    ), f"CYME-to-OpenDSS conversion metrics differ from reference.\n{comparison.T}"

    cyme_reader.get_system().kron_reduce()


def test_cyme_to_opendss_ieee123(tmp_path):
    """Convert CYME ieee_123_node to OpenDSS in .dump/converted and compare metrics."""
    cyme_folder = test_folder / "data" / "cyme_models" / "ieee_123_node"
    reference_dss = (
        test_folder / "data" / "opendss_circuit_models" / "123Bus" / "IEEE123Master.dss"
    )

    # Save conversion artifacts in repository .dump/converted as requested.
    dump_path = Path(__file__).resolve().parents[2] / ".dump" / "converted"
    dump_path.mkdir(parents=True, exist_ok=True)

    reference_metrics = get_metrics_reduced(reference_dss)

    cyme_reader = CymeReader(
        cyme_folder / "Network.txt",
        cyme_folder / "Equipment.txt",
        cyme_folder / "Load.txt",
    )
    writer = Writer(cyme_reader.get_system())
    writer.write(dump_path, separate_substations=False, separate_feeders=False)

    converted_dss = dump_path / OpenDSSFileTypes.MASTER_FILE.value
    assert converted_dss.exists(), f"Converted DSS master file not found at {converted_dss}"

    converted_metrics = get_metrics_reduced(converted_dss)

    comparison = pd.DataFrame(
        [
            reference_metrics,
            converted_metrics,
            np.subtract(reference_metrics, converted_metrics) / reference_metrics * 100,
        ],
        index=["Original", "Converted", "Difference (%)"],
        columns=[
            "Min Voltage (pu)",
            "Max Voltage (pu)",
            "Avg Voltage (pu)",
            "Feeder Head P (kW)",
            "Feeder Head Q (kvar)",
        ],
    )

    assert np.allclose(
        reference_metrics, converted_metrics, rtol=0.01, atol=0.01
    ), f"CYME-to-OpenDSS conversion metrics differ from reference.\n{comparison.T}"

    cyme_reader.get_system().kron_reduce()
