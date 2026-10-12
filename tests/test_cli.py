from importlib.metadata import version

from typer.testing import CliRunner

from dailyainotes.cli import app


def test_version_prints_the_installed_version() -> None:
    result = CliRunner().invoke(app, ["version"])

    assert result.exit_code == 0
    assert result.output.strip() == version("dailyainotes")
