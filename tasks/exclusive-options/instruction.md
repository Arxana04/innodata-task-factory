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
