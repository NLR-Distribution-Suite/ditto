from pathlib import Path

import numpy as np

from ditto.readers.cim_iec_61968_13.reader import Reader
from ditto.writers.opendss.write import Writer
from tests.helpers import get_metrics


def test_cim_to_opendss_roundtrip(ieee13_node_xml_file, tmp_path):
    ieee13_node_dss_file = (
        Path(__file__).parent.parent / "data" / "opendss_circuit_models" / "ieee13" / "Master.dss"
    )
    pre_converion_metrics = get_metrics(ieee13_node_dss_file)
    cim_reader = Reader(ieee13_node_xml_file)
    cim_reader.read()
    system = cim_reader.get_system()
    writer = Writer(system)
    writer.write(output_path=tmp_path, separate_substations=False, separate_feeders=False)
    post_converion_metrics = get_metrics(tmp_path / "Master.dss")
    assert np.allclose(
        pre_converion_metrics, post_converion_metrics, rtol=0.01, atol=0.01
    ), "Round trip coversion exceeds error tolerance"
