from ditto.readers.opendss.reader import Reader

from pydantic import ValidationError
from opendssdirect import dss

import pytest


def test_model(tmp_path):
    save_dir = tmp_path / "test_circuit"
    dss.run_command("clear")
    dss.run_command(
        "new Circuit.test bus1=bus_1.1 BasekV=7.2 pu=1.03 Angle=0.0 Phases=1 Z1=[1e-05, 1e-05] Z0=[1e-05, 1e-05]"
    )
    dss.run_command("new line.line_1  bus1=bus_1.1 bus2=bus_2.2 phases=1")
    dss.run_command("new line.line_2  bus1=bus_1.1 bus2=bus_2.2 phases=1 length=-10")
    dss.run_command("solve")
    dss.run_command(f"save circuit dir={save_dir}")
    with pytest.raises(ValidationError):
        reader = Reader(str(save_dir / "Master.dss"))
        reader.get_system()
