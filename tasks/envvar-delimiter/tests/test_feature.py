import click
import pytest
from click.testing import CliRunner


def test_literal_delimiter_keeps_spaces_and_empty_fields():
    @click.command()
    @click.option("--tag", multiple=True, envvar="TAGS", envvar_delimiter="::")
    def cli(tag):
        click.echo(repr(tag))

    result = CliRunner().invoke(cli, env={"TAGS": "red fox::::blue"})
    assert result.exit_code == 0, result.output
    assert result.output.strip() == "('red fox', '', 'blue')"


def test_auto_envvar_feeds_composite_parser_and_cli_still_wins():
    @click.command(context_settings={"auto_envvar_prefix": "DEMO"})
    @click.option("--pair", type=(str, int), envvar_delimiter="|")
    def cli(pair):
        click.echo(repr(pair))

    runner = CliRunner()
    env = {"DEMO_PAIR": "red fox|7"}
    result = runner.invoke(cli, env=env)
    assert result.exit_code == 0, result.output
    assert result.output.strip() == "('red fox', 7)"
    override = runner.invoke(cli, ["--pair", "blue", "3"], env=env)
    assert override.exit_code == 0, override.output
    assert override.output.strip() == "('blue', 3)"


def test_bad_delimiter_configurations_are_rejected():
    with pytest.raises(ValueError):
        click.Option(["--tag"], multiple=True, envvar_delimiter="")
    with pytest.raises(ValueError):
        click.Option(["--tag"], envvar_delimiter=",")
    with pytest.raises(ValueError):
        click.Option(["--tag"], is_flag=True, envvar_delimiter=",")
