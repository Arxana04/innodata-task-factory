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
