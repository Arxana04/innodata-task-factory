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
