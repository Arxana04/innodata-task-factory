from datetime import datetime, timezone

import click
import pytest
from click.testing import CliRunner


def test_bounds_are_inclusive_for_cli_strings():
    @click.command()
    @click.option("--day", type=click.DateTime(
        min_value=datetime(2030, 1, 2), max_value=datetime(2030, 1, 4)
    ))
    def cli(day):
        click.echo(day.date().isoformat())

    runner = CliRunner()
    for day in ("2030-01-02", "2030-01-03", "2030-01-04"):
        result = runner.invoke(cli, ["--day", day])
        assert result.exit_code == 0, result.output
        assert result.output.strip() == day


def test_single_bound_applies_to_converted_datetimes():
    lower = click.DateTime(min_value=datetime(2030, 1, 2))
    upper = click.DateTime(max_value=datetime(2030, 1, 4))
    with pytest.raises(click.BadParameter, match="2030-01-02"):
        lower.convert(datetime(2030, 1, 1), None, None)
    with pytest.raises(click.BadParameter, match="2030-01-04"):
        upper.convert("2030-01-05", None, None)


def test_invalid_bounds_and_timezone_mismatch_are_clear():
    with pytest.raises(ValueError):
        click.DateTime(min_value=datetime(2030, 1, 4), max_value=datetime(2030, 1, 2))
    aware = datetime(2030, 1, 2, tzinfo=timezone.utc)
    with pytest.raises(ValueError):
        click.DateTime(min_value=aware, max_value=datetime(2030, 1, 4))
    bounded = click.DateTime(min_value=aware)
    with pytest.raises(click.BadParameter, match="timezone"):
        bounded.convert("2030-01-03", None, None)
    assert bounded.convert(aware, None, None) == aware
