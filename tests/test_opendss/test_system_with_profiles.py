from infrasys import NonSequentialTimeSeries
from gdm.distribution import DistributionSystem

from ditto.writers.opendss.write import Writer


def test_export_opends_model_with_profiles(
    distribution_system_with_single_timeseries: DistributionSystem, tmp_path
):
    writer = Writer(distribution_system_with_single_timeseries)

    assert tmp_path.exists(), f"Export path: {tmp_path}"
    writer.write(tmp_path, separate_substations=False, separate_feeders=False)
    assert (
        tmp_path / "LoadShape.dss"
    ).exists(), f"LoadShape.dss file not found in the export path: {tmp_path}"
    with open(tmp_path / "Master.dss", "r", encoding="utf-8") as file:
        content = file.read()
        assert "redirect LoadShape.dss" in content


def test_export_opends_model_with_discontineous_profiles(
    distribution_system_with_nonsequential_timeseries: DistributionSystem, tmp_path
):
    writer = Writer(distribution_system_with_nonsequential_timeseries)

    assert tmp_path.exists(), f"Export path: {tmp_path}"
    writer.write(
        tmp_path,
        separate_substations=False,
        separate_feeders=False,
        profile_type=NonSequentialTimeSeries,
    )
    assert (
        tmp_path / "LoadShape.dss"
    ).exists(), f"LoadShape.dss file not found in the export path: {tmp_path}"

    with open(tmp_path / "Master.dss", "r", encoding="utf-8") as file:
        content = file.read()
        assert "redirect LoadShape.dss" in content
