import glob
import os

from infrasys import NonSequentialTimeSeries
from gdm.distribution import DistributionSystem
from loguru import logger

from ditto.writers.opendss.write import Writer


def test_export_opends_model_with_profiles(
    distribution_system_with_single_timeseries: DistributionSystem, tmp_path
):
    fixed_tmp_path = tmp_path
    distribution_system_with_single_timeseries.info()
    writer = Writer(distribution_system_with_single_timeseries)
    csv_files = glob.glob(os.path.join(fixed_tmp_path, "*.dss"))
    for file in csv_files:
        os.remove(file)
        logger.debug(f"Deleted: {file}")

    assert fixed_tmp_path.exists(), f"Export path: {fixed_tmp_path}"
    writer.write(fixed_tmp_path, separate_substations=False, separate_feeders=False)
    assert (
        fixed_tmp_path / "LoadShape.dss"
    ).exists(), f"LoadShape.dss file not found in the export path: {fixed_tmp_path}"
    with open(fixed_tmp_path / "Master.dss", "r", encoding="utf-8") as file:
        content = file.read()
        assert "redirect LoadShape.dss" in content


def test_export_opends_model_with_discontineous_profiles(
    distribution_system_with_nonsequential_timeseries: DistributionSystem, tmp_path
):
    fixed_tmp_path = tmp_path

    writer = Writer(distribution_system_with_nonsequential_timeseries)
    csv_files = glob.glob(os.path.join(fixed_tmp_path, "*.dss"))
    for file in csv_files:
        os.remove(file)
        logger.debug(f"Deleted: {file}")

    assert fixed_tmp_path.exists(), f"Export path: {fixed_tmp_path}"
    writer.write(
        fixed_tmp_path,
        separate_substations=False,
        separate_feeders=False,
        profile_type=NonSequentialTimeSeries,
    )
    assert (
        fixed_tmp_path / "LoadShape.dss"
    ).exists(), f"LoadShape.dss file not found in the export path: {fixed_tmp_path}"

    with open(fixed_tmp_path / "Master.dss", "r", encoding="utf-8") as file:
        content = file.read()
        assert "redirect LoadShape.dss" in content
