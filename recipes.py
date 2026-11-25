"""Click feature recipes and their independent acceptance cases."""

from __future__ import annotations

import ast
from dataclasses import dataclass


@dataclass(frozen=True)
class Edit:
    path: str
    before: str
    after: str
    owner: str | None = None

    def apply(self, source: str) -> str:
        lines = source.splitlines(keepends=True)
        start, end = 0, len(lines)
        if self.owner:
            matches = [
                node for node in ast.parse(source).body
                if isinstance(node, ast.ClassDef) and node.name == self.owner
            ]
            if len(matches) != 1:
                raise ValueError(f"Expected one class {self.owner} in {self.path}.")
            start, end = matches[0].lineno - 1, matches[0].end_lineno
        section = "".join(lines[start:end])
        if section.count(self.before) != 1:
            detail = self.before.lstrip().splitlines()[0]
            raise ValueError(f"Cannot find a unique anchor in {self.path}: {detail}")
        return "".join(lines[:start]) + section.replace(self.before, self.after, 1) + "".join(lines[end:])


@dataclass(frozen=True)
class Recipe:
    id: str
    instruction: str
    edits: tuple[Edit, ...]
    tests: str
    regressions: tuple[str, ...]


TYPES = "src/click/types.py"
CORE = "src/click/core.py"
EXPORTS = "src/click/__init__.py"

DATE_BOUNDS = Recipe(
    id="datetime-bounds",
    instruction="""
    # Inclusive bounds for Click DateTime

    Extend the existing public `click.DateTime(formats=None)` type with optional
    keyword-only `min_value` and `max_value` datetime bounds. Existing formats
    remain supported. Either bound may be omitted, and both endpoints are
    inclusive. A value may be a parsed CLI string or a datetime supplied as a
    default or via the parameter type directly. Apply the same bounds to both.

    Raise `ValueError` at construction if the bounds are reversed or use
    incompatible timezone awareness. Use Click's normal invalid-parameter error
    for out-of-range values and for values whose timezone awareness prevents
    comparison to a bound. Include the applicable bound or timezone mismatch
    in the message. Dates without bounds and invalid-format errors should behave
    as before.
    """,
    edits=(
        Edit(TYPES, "    def __init__(self, formats: cabc.Sequence[str] | None = None):\n", """    def __init__(
        self,
        formats: cabc.Sequence[str] | None = None,
        *,
        min_value: datetime | None = None,
        max_value: datetime | None = None,
    ) -> None:
        if min_value is not None and max_value is not None:
            try:
                backwards = min_value > max_value
            except TypeError as error:
                raise ValueError("DateTime bounds must agree on timezone awareness.") from error
            if backwards:
                raise ValueError("DateTime minimum cannot exceed its maximum.")
        self.min_value = min_value
        self.max_value = max_value
""", "DateTime"),
        Edit(TYPES, "        if isinstance(value, datetime):\n            return value\n", """        if isinstance(value, datetime):
            return self._check_bounds(value, param, ctx)
""", "DateTime"),
        Edit(TYPES, "                return converted\n", "                return self._check_bounds(converted, param, ctx)\n", "DateTime"),
        Edit(TYPES, "    def __repr__(self) -> str:\n", """    def _check_bounds(
        self, value: datetime, param: Parameter | None, ctx: Context | None
    ) -> datetime:
        try:
            too_early = self.min_value is not None and value < self.min_value
            too_late = self.max_value is not None and value > self.max_value
        except TypeError:
            self.fail(_("Value and bound must agree on timezone awareness."), param, ctx)
        if too_early:
            self.fail(_("Value must be on or after {bound}.").format(bound=self.min_value), param, ctx)
        if too_late:
            self.fail(_("Value must be on or before {bound}.").format(bound=self.max_value), param, ctx)
        return value

    def __repr__(self) -> str:
""", "DateTime"),
    ),
    tests="""
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
    """,
    regressions=("tests/test_basic.py", "tests/test_types/test_IntRange.py"),
)

ENVVAR_DELIMITER = Recipe(
    id="envvar-delimiter",
    instruction="""
    # Configurable delimiter for multi-value option environment variables

    Add an optional keyword `envvar_delimiter` to `click.Option` and expose it
    through `@click.option`. For an option that accepts multiple values, split
    a raw environment-variable value on that literal delimiter. Keep the
    whitespace and empty fields that ordinary Python string splitting keeps.
    Support both repeated options and options with a fixed tuple arity, including
    automatic environment-variable names. Let existing typing and grouping run
    after splitting. CLI arguments retain their existing parsing and priority.

    Omitting the delimiter preserves the current type-specific splitting. Raise
    `ValueError` for an empty delimiter or for use on a scalar or flag option.
    """,
    edits=(
        Edit(CORE, "        **attrs: t.Any,\n", "        envvar_delimiter: str | None = None,\n        **attrs: t.Any,\n", "Option"),
        Edit(CORE, "        self._validate(prompt, deprecated)\n", """        self._validate(prompt, deprecated)
        if envvar_delimiter is not None:
            if not envvar_delimiter:
                raise ValueError("envvar_delimiter must not be empty.")
            if self.is_flag or self.count or (not self.multiple and self.nargs == 1):
                raise ValueError("envvar_delimiter requires a multi-value option.")
        self.envvar_delimiter = envvar_delimiter
""", "Option"),
        Edit(CORE, "            multi_rv = self.type.split_envvar_value(rv)\n", """            if self.envvar_delimiter is None:
                multi_rv = self.type.split_envvar_value(rv)
            else:
                multi_rv = rv.split(self.envvar_delimiter)
""", "Option"),
    ),
    tests="""
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
    """,
    regressions=(
        "tests/test_options.py::test_multiple_envvar",
        "tests/test_options.py::test_envvar_container_type",
        "tests/test_options.py::test_empty_envvar",
    ),
)

HELP_SECTIONS = Recipe(
    id="option-help-sections",
    instruction="""
    # Named help sections for Click options

    Add an optional keyword `help_group` to `click.Option` and expose it
    through `@click.option`. A non-empty label puts a visible option under
    that heading in command help. Options without a label, including
    `--help`, remain in the normal Options section. Render the default
    section first and custom groups in first-appearance order. Keep the normal
    option order within each group and omit empty sections and hidden options.
    Positional arguments, including documented arguments, retain their
    existing help output. The change only affects help rendering.
    """,
    edits=(
        Edit(CORE, "        **attrs: t.Any,\n", "        help_group: str | None = None,\n        **attrs: t.Any,\n", "Option"),
        Edit(CORE, "        self.hidden = hidden\n", "        self.hidden = hidden\n        self.help_group = help_group or None\n", "Option"),
        Edit(CORE, """        opts = []
        for param in self.get_params(ctx):
            rv = param.get_help_record(ctx)
            if rv is not None and not isinstance(param, Argument):
                opts.append(rv)

        if opts:
            with formatter.section(_("Options")):
                formatter.write_dl(opts)
""", """        default_heading = _("Options")
        groups: dict[str, list[tuple[str, str]]] = {default_heading: []}
        for param in self.get_params(ctx):
            record = param.get_help_record(ctx)
            if record is None or isinstance(param, Argument):
                continue
            heading = param.help_group if isinstance(param, Option) else None
            groups.setdefault(heading or default_heading, []).append(record)

        for heading, records in groups.items():
            if records:
                with formatter.section(heading):
                    formatter.write_dl(records)
""", "Command"),
    ),
    tests="""
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
        sections = result.output.split("Options:\\n", 1)[1]
        default, custom = sections.split("Network:\\n", 1)
        network, output = custom.split("Output:\\n", 1)
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
    """,
    regressions=(
        "tests/test_formatting.py::test_wrapping_long_options_strings",
        "tests/test_arguments.py::test_argument_help",
        "tests/test_arguments.py::test_argument_help_options_only_no_arguments_section",
    ),
)

KEY_VALUE = Recipe(
    id="key-value-type",
    instruction="""
    # A reusable Click type for KEY=VALUE options

    Add `click.KeyValue()` as a public parameter type. Convert a string of the
    form `KEY=VALUE` to a two-string tuple by splitting at the first equals
    sign. Preserve additional equals signs, whitespace in accepted strings,
    and empty values. Reject a missing separator and empty or whitespace-only
    keys with a normal Click invalid-parameter error.

    Accept an already converted pair of strings, such as a default supplied
    by the developer, under the same key rules. Reject other invalid values
    with a normal parameter error. Using the type with multiple=True should
    produce a tuple of key-value pairs in the original order. Show KEY=VALUE
    as the metavar in help.
    """,
    edits=(
        Edit(TYPES, "class DateTimeInfoDict(ParamTypeInfoDict):\n", '''class KeyValue(ParamType[tuple[str, str]]):
    """Convert a KEY=VALUE parameter to a pair of strings."""

    name = "key=value"

    def get_metavar(self, param: Parameter, ctx: Context) -> str:
        return "KEY=VALUE"

    def convert(
        self, value: t.Any, param: Parameter | None, ctx: Context | None
    ) -> tuple[str, str]:
        if isinstance(value, str):
            key, separator, item = value.partition("=")
            if separator and key.strip():
                return key, item
        elif (
            isinstance(value, tuple)
            and len(value) == 2
            and all(isinstance(part, str) for part in value)
            and value[0].strip()
        ):
            return value

        self.fail(_("Expected KEY=VALUE with a non-empty key."), param, ctx)


class DateTimeInfoDict(ParamTypeInfoDict):
'''),
        Edit(EXPORTS, "from .types import IntRange as IntRange\n", "from .types import IntRange as IntRange\nfrom .types import KeyValue as KeyValue\n"),
    ),
    tests="""
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
    """,
    regressions=(
        "tests/test_options.py::test_nargs_tup_composite_mult",
        "tests/test_types/test_ParamType.py",
        "tests/test_types/test_convert_type.py",
    ),
)

EXCLUSIVE_OPTIONS = Recipe(
    id="exclusive-options",
    instruction="""
    # Mutually exclusive command options

    Add an optional keyword `mutually_exclusive` to `click.Command`, exposed
    through `@click.command`. It accepts an iterable of option-name groups,
    where each group has at least two distinct normalized names from that
    command's declared options. A command may declare more than one group.
    Raise `ValueError` for an undersized group, a duplicate member, or a
    name that does not identify a declared option.

    When the user explicitly supplies more than one option from a group on
    the command line, report a Click usage error naming their flags before
    the command callback is invoked. Defaults and environment values do
    not count as explicit. Preserve normal help behavior and skip conflict
    checks during resilient parsing, such as shell completion.
    """,
    edits=(
        Edit(CORE, "        deprecated: bool | str = False,\n", """        deprecated: bool | str = False,
        *,
        mutually_exclusive: cabc.Iterable[cabc.Iterable[str]] = (),
""", "Command"),
        Edit(CORE, "        self.params = params or []\n", """        self.params = params or []
        options = {param.name: param for param in self.params if isinstance(param, Option)}
        self._exclusive_options: list[tuple[Option, ...]] = []
        for group in mutually_exclusive:
            names = tuple(group)
            if len(names) < 2 or len(set(names)) != len(names):
                raise ValueError("An exclusive group needs at least two distinct option names.")
            if any(name not in options for name in names):
                raise ValueError("Exclusive groups must name declared options.")
            self._exclusive_options.append(tuple(options[name] for name in names))
""", "Command"),
        Edit(
            CORE,
            "            _, args = param.handle_parse_result(ctx, opts, args)\n",
            "            _value, args = param.handle_parse_result(ctx, opts, args)\n",
            "Command",
        ),
        Edit(CORE, "        ctx.args = args\n", """        if not ctx.resilient_parsing:
            for group in self._exclusive_options:
                flags = [
                    option.opts[0] for option in group
                    if option.name is not None
                    and ctx.get_parameter_source(option.name) is ParameterSource.COMMANDLINE
                ]
                if len(flags) > 1:
                    message = _("Options {flags} are mutually exclusive.")
                    ctx.fail(message.format(flags=", ".join(flags)))

        ctx.args = args
""", "Command"),
    ),
    tests="""
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
    """,
    regressions=(
        "tests/test_options.py::test_invalid_option",
        "tests/test_commands.py::test_help_param_priority",
        "tests/test_commands.py::test_command_parse_args_collects_option_prefixes",
    ),
)

RECIPES = {
    recipe.id: recipe
    for recipe in (DATE_BOUNDS, ENVVAR_DELIMITER, HELP_SECTIONS, KEY_VALUE, EXCLUSIVE_OPTIONS)
}
