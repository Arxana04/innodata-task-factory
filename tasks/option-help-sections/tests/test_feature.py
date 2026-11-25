import click
from click.testing import CliRunner


def test_default_and_custom_sections_keep_option_order():
    @click.command()
    @click.option("--host", help_group="Network")
    @click.option("--format", help_group="Output")
    @click.option("--port", help_group="Network")
    @click.option("--verbose", is_flag=True)
    def cli(**kwargs):
        pass

    result = CliRunner().invoke(cli, ["--help"])
    assert result.exit_code == 0, result.output
    sections = result.output.split("Options:\n", 1)[1]
    default, custom = sections.split("Network:\n", 1)
    network, output = custom.split("Output:\n", 1)
    assert "--verbose" in default and "--help" in default
    assert network.index("--host") < network.index("--port")
    assert "--format" in output and "--format" not in network


def test_hidden_and_positional_parameters_are_not_moved_to_groups():
    @click.command(add_help_option=False)
    @click.argument("path", help="A local file.")
    @click.option("--secret-label", hidden=True, help_group="Hidden group")
    @click.option("--theme", help_group="Appearance")
    def cli(**kwargs):
        pass

    help_text = cli.get_help(click.Context(cli))
    assert "Positional arguments:" in help_text and "A local file." in help_text
    assert "Appearance:" in help_text and "--theme" in help_text
    assert "Options:" not in help_text
    assert "Hidden group" not in help_text and "--secret-label" not in help_text
