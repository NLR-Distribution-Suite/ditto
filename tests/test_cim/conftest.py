from pathlib import Path

import pytest


@pytest.fixture
def ieee13_node_xml_file():
    return Path(__file__).parent.parent / "data" / "cim_iec_61968_13" / "IEEE13Nodeckt_CIM100x.XML"
