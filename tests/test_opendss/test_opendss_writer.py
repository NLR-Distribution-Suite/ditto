"""Module for testing writers."""

from pathlib import Path

from gdm.distribution import DistributionSystem
from gdm.distribution.components import (
    DistributionVoltageSource,
    DistributionTransformer,
    SequenceImpedanceBranch,
    DistributionCapacitor,
    MatrixImpedanceBranch,
    DistributionLoad,
    DistributionBus,
    GeometryBranch,
)
import pytest

from ditto.writers.opendss.write import Writer

MODULES = [
    DistributionVoltageSource,
    DistributionTransformer,
    SequenceImpedanceBranch,
    DistributionCapacitor,
    MatrixImpedanceBranch,
    # DistributionSystem,
    DistributionLoad,
    DistributionBus,
    GeometryBranch,
]


@pytest.mark.parametrize("component", MODULES)
def test_component(component, tmp_path):
    system = DistributionSystem(
        name=f"test {component.__name__}", auto_add_composed_components=True
    )
    system.add_component(component.example())
    writer = Writer(system)
    writer.write(output_path=tmp_path, separate_substations=False, separate_feeders=False)

    # Verify at least one .dss file was written with content
    dss_files = list(Path(tmp_path).rglob("*.dss"))
    assert len(dss_files) > 0, f"No .dss files produced for {component.__name__}"
    for dss_file in dss_files:
        assert dss_file.stat().st_size > 0, f"Empty .dss file: {dss_file.name}"


def test_all_types(tmp_path):
    system = DistributionSystem(name="test full system", auto_add_composed_components=True)
    for component in MODULES:
        system.add_component(component.example())
    writer = Writer(system)
    writer.write(output_path=tmp_path, separate_substations=True, separate_feeders=True)

    # Verify output files were produced
    dss_files = list(Path(tmp_path).rglob("*.dss"))
    assert len(dss_files) > 0, "No .dss files produced for full system write"
