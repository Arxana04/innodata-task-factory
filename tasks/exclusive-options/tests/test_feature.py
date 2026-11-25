import click
import pytest
from click.testing import CliRunner


def make_cli():
    @click.command(mutually_exclusive=[("json", "text"), ("brief", "wide")])
    @click.option("--json", is_flag=True, envvar="DEMO_JSON")
    @click.option("--text", is_flag=True, default=True)
    @click.option("-b", "--brief", is_flag=True)
    @click.option("--wide", is_flag=True)
    def cli(**kwargs):
        click.echo("called")

    return cli


def test_each_group_rejects_conflicts_before_command_callback():
    runner = CliRunner()
    cli = make_cli()
    for args in (["--json", "--text"], ["-b", "--wide"]):
        result = runner.invoke(cli, args)
        assert result.exit_code == 2, result.output
        assert all(flag in result.output for flag in args)
        assert "mutually exclusive" in result.output
        assert "called" not in result.output


def test_defaults_and_env_do_not_conflict_and_help_still_works():
    runner = CliRunner()
    cli = make_cli()
    result = runner.invoke(cli, ["--text", "-b"], env={"DEMO_JSON": "1"})
    assert result.exit_code == 0, result.output
    assert result.output.strip() == "called"
    help_result = runner.invoke(cli, ["--json", "--text", "--help"])
    assert help_result.exit_code == 0, help_result.output
    assert "Usage:" in help_result.output
    ctx = cli.make_context("cli", ["--json", "--text"], resilient_parsing=True)
    assert ctx.params["json"] and ctx.params["text"]


def test_invalid_declarations_fail_at_construction():
    for group in (("known",), ("known", "known"), ("known", "missing")):
        with pytest.raises(ValueError):
            click.Command(
                "demo", params=[click.Option(["--known"])],
                mutually_exclusive=[group],
            )
