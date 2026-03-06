from pathlib import Path
from defusedxml import ElementTree as ET

import pytest
from gdm.distribution.components import DistributionBattery, DistributionBus
from gdm.distribution.equipment import BatteryEquipment, InverterEquipment
from gdm.distribution.enums import Phase, VoltageTypes
from gdm.quantities import ActivePower, ApparentPower, EnergyDC, ReactivePower, Voltage

from ditto.readers.opendss.reader import Reader
from ditto.writers.cim_iec_61968_13.write import Writer


_BASE = Path(__file__).parents[1]
_IEEE13_DSS = _BASE / "data" / "opendss_circuit_models" / "ieee13" / "Master.dss"
_P4U_DT0_DSS = (
    _BASE
    / "data"
    / "opendss_circuit_models"
    / "P4U"
    / "p4uhs0_4"
    / "p4uhs0_4--p4udt0"
    / "Master.dss"
)


def test_cim_writer_single_mode(tmp_path):
    system = Reader(_IEEE13_DSS).get_system()
    writer = Writer(system)

    writer.write(output_path=tmp_path, output_mode="single")

    output_file = tmp_path / "model.xml"
    assert output_file.exists()

    tree = ET.parse(output_file)
    root = tree.getroot()
    assert root.tag.endswith("RDF")


def test_cim_writer_package_mode(tmp_path):
    system = Reader(_IEEE13_DSS).get_system()
    writer = Writer(system)

    writer.write(output_path=tmp_path, output_mode="package")

    manifest_file = tmp_path / "manifest.xml"
    assert manifest_file.exists()

    manifest_tree = ET.parse(manifest_file)
    manifest_root = manifest_tree.getroot()
    assert manifest_root.tag == "PackageManifest"

    package_files = list(tmp_path.rglob("*.xml"))
    assert len(package_files) > 1

    package_names = [path.name for path in package_files]
    assert any("distribution_bus" in name for name in package_names)
    assert any("distribution_load" in name for name in package_names)
    assert any("matrix_impedance_branch" in name for name in package_names)


def test_cim_writer_invalid_mode(tmp_path):
    system = Reader(_IEEE13_DSS).get_system()
    writer = Writer(system)

    with pytest.raises(ValueError, match="output_mode"):
        writer.write(output_path=tmp_path, output_mode="invalid")


def test_cim_writer_serializes_solar_and_fuse_components(tmp_path):
    system = Reader(_P4U_DT0_DSS).get_system()
    writer = Writer(system)

    writer.write(output_path=tmp_path, output_mode="single")
    output_file = tmp_path / "model.xml"
    assert output_file.exists()

    tree = ET.parse(output_file)
    root = tree.getroot()
    ns = {"cim": "http://iec.ch/TC57/CIM100#"}

    assert len(root.findall("cim:PhotoVoltaicUnit", ns)) >= 1
    assert len(root.findall("cim:PowerElectronicsConnection", ns)) >= 1
    assert len(root.findall("cim:Fuse", ns)) >= 1

    writer.write(output_path=tmp_path / "package", output_mode="package")
    package_names = [path.name for path in (tmp_path / "package").rglob("*.xml")]
    assert any("distribution_solar" in name for name in package_names)
    assert any("matrix_impedance_fuse" in name for name in package_names)


def test_cim_writer_serializes_battery_components(tmp_path):
    system = Reader(_IEEE13_DSS).get_system()
    bus = next(iter(system.get_components(DistributionBus)))

    battery = DistributionBattery.model_construct(
        name="test_battery",
        bus=bus,
        phases=[Phase.A, Phase.B, Phase.C],
        active_power=ActivePower(25.0, "kilowatt"),
        reactive_power=ReactivePower(5.0, "kilovar"),
        controller=None,
        inverter=InverterEquipment.model_construct(
            name="test_battery_inverter",
            rated_apparent_power=ApparentPower(30.0, "kilova"),
            rise_limit=None,
            fall_limit=None,
            cutout_percent=0.1,
            cutin_percent=0.1,
            dc_to_ac_efficiency=0.96,
            eff_curve=None,
        ),
        equipment=BatteryEquipment.model_construct(
            name="test_battery_equipment",
            rated_energy=EnergyDC(100.0, "kilowatthour"),
            rated_power=ActivePower(25.0, "kilowatt"),
            charging_efficiency=0.95,
            discharging_efficiency=0.95,
            idling_efficiency=0.99,
            rated_voltage=Voltage(12.47, "kilovolt"),
            voltage_type=VoltageTypes.LINE_TO_LINE,
        ),
    )
    system.add_components(battery)

    writer = Writer(system)
    writer.write(output_path=tmp_path, output_mode="single")

    output_file = tmp_path / "model.xml"
    assert output_file.exists()
    tree = ET.parse(output_file)
    root = tree.getroot()
    ns = {"cim": "http://iec.ch/TC57/CIM100#"}

    assert len(root.findall("cim:BatteryUnit", ns)) >= 1
    assert len(root.findall("cim:PowerElectronicsConnection", ns)) >= 1

    writer.write(output_path=tmp_path / "package", output_mode="package")
    package_names = [path.name for path in (tmp_path / "package").rglob("*.xml")]
    assert any("distribution_battery" in name for name in package_names)
