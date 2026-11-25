# Named help sections for Click options

Add an optional keyword `help_group` to `click.Option` and expose it
through `@click.option`. A non-empty label puts a visible option under
that heading in command help. Options without a label, including
`--help`, remain in the normal Options section. Render the default
section first and custom groups in first-appearance order. Keep the normal
option order within each group and omit empty sections and hidden options.
Positional arguments, including documented arguments, retain their
existing help output. The change only affects help rendering.
