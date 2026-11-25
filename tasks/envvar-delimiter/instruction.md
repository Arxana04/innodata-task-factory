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
