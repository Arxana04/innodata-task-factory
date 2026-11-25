import click
import pytest
from click.testing import CliRunner


def test_multiple_pairs_are_converted_in_order():
    @click.command()
    @click.option("--item", type=click.KeyValue(), multiple=True)
    def cli(item):
        click.echo(repr(item))

    runner = CliRunner()
    result = runner.invoke(cli, ["--item", "name=red=fox", "--item", "tag="])
    assert result.exit_code == 0, result.output
    assert result.output.strip() == "(('name', 'red=fox'), ('tag', ''))"
    assert "KEY=VALUE" in runner.invoke(cli, ["--help"]).output


def test_accepts_preconverted_pairs_and_keeps_whitespace():
    value_type = click.KeyValue()
    assert value_type.convert(("name", "red fox"), None, None) == ("name", "red fox")
    assert value_type.convert("name= red fox ", None, None) == ("name", " red fox ")


def test_bad_pairs_use_click_parameter_errors():
    value_type = click.KeyValue()
    for value in ("no-separator", " =value", "=value", ("", "value"), ("x", 3), 1):
        with pytest.raises(click.BadParameter, match="KEY=VALUE"):
            value_type.convert(value, None, None)
