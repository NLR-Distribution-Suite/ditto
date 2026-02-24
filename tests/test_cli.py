from typer.testing import CliRunner

from ditto import cli


def test_list_readers():
    runner = CliRunner()
    result = runner.invoke(cli.app, ["list-readers"])
    assert result.exit_code == 0
    output = result.stdout.strip().splitlines()
    # repo provides these readers
    assert "opendss" in output
    assert "cim_iec_61968_13" in output


def test_list_writers():
    runner = CliRunner()
    result = runner.invoke(cli.app, ["list-writers"])
    assert result.exit_code == 0
    output = result.stdout
    assert "opendss" in output
    assert "cim_iec_61968_13" in output


def test_convert_missing_args():
    runner = CliRunner()
    # calling convert without required options should fail
    result = runner.invoke(cli.app, ["convert"])
    assert result.exit_code != 0
