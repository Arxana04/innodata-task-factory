# Local validation evidence

These checks used Python 3.12.16 and pytest 9.0.2 on macOS. Each check used
a fresh Click checkout at the pinned commit. Docker and Harbor execution
are pending.

| Task | Run | Feature tests passed | Regression tests passed | Reward | Test time |
| --- | --- | --- | --- | --- | --- |
| `datetime-bounds` | `nop` | 0/3 | 123 | 0.0 | 0.18 s |
| `datetime-bounds` | `oracle` | 3/3 | 123 | 1.0 | 0.15 s |
| `envvar-delimiter` | `nop` | 0/3 | 4 | 0.0 | 0.21 s |
| `envvar-delimiter` | `oracle` | 3/3 | 4 | 1.0 | 0.13 s |
| `exclusive-options` | `nop` | 0/3 | 3 | 0.0 | 0.17 s |
| `exclusive-options` | `oracle` | 3/3 | 3 | 1.0 | 0.17 s |
| `key-value-type` | `nop` | 0/3 | 33 | 0.0 | 0.17 s |
| `key-value-type` | `oracle` | 3/3 | 33 | 1.0 | 0.15 s |
| `option-help-sections` | `nop` | 0/2 | 3 | 0.0 | 0.14 s |
| `option-help-sections` | `oracle` | 2/2 | 3 | 1.0 | 0.08 s |

The default upstream pytest suite also passed independently on all five
reference-patched checkouts. Each run reported 2,433 passes, 25 skips,
one expected failure, and 31,000 tests deselected by Click's default configuration.

During development, the first exclusive-options oracle run scored 0.67.
The command parser had shadowed the translation function. The recipe was
corrected, the packages were regenerated, and all ten checks above were rerun.

The date-bounds verifier also caught a deliberate change from `<` to `<=`
in the minimum check. Two of three feature tests failed while all
123 regression tests passed. The resulting reward was 0.33.

Regeneration produced identical task contents on a second run.
To reproduce the raw logs, run `factory.py check-local` as shown in the
[project README](../README.md).
