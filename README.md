# Innodata Coding Task Factory

Generate five independent Harbor coding tasks from a clean checkout of [Click 8.5.1](https://github.com/pallets/click/commit/cf19179e8e2fd54c601378cec9e0d21bb12b6fb1). Each task includes a feature brief, a Dockerfile, a reference patch, and a verifier with feature and regression tests.

## Generate the tasks

From this directory, use Python 3.12 and Git. The generator itself uses the Python standard library.

```sh
git clone --branch 8.5.1 https://github.com/pallets/click.git ../click-8.5.1
python3.12 factory.py generate --repo ../click-8.5.1 --out regenerated
```

The default commit is `cf19179e8e2fd54c601378cec9e0d21bb12b6fb1`. Use `--task datetime-bounds` to generate just one package. Choose a new output directory for each run. Inspect the included samples under [tasks](tasks/).

| Task | Behavior |
| --- | --- |
| `datetime-bounds` | Validate parsed and preconverted datetimes against inclusive bounds. |
| `envvar-delimiter` | Parse multi-value environment variables with an option-specific separator. |
| `option-help-sections` | Render labeled groups of visible options in command help. |
| `key-value-type` | Parse the first equals sign in a CLI assignment and return a pair of strings. |
| `exclusive-options` | Reject incompatible options explicitly supplied to the same command. |

## Check without Docker

Install the starter's locked test dependencies in a local virtual environment. Run these commands in the factory directory.

```sh
uv sync --project ../click-8.5.1 --python 3.12 --frozen --no-default-groups --group tests
python3.12 factory.py check-local \
  --repo ../click-8.5.1 \
  --tasks regenerated \
  --python ../click-8.5.1/.venv/bin/python \
  --logs local-evidence
```

The command creates a fresh checkout for every run. It calls the packaged verifier on the baseline, then calls the packaged solution and verifier in a second checkout. Save the output directory for its per-task logs and summary. The local checks execute the verifier and reference patches without Docker. They cover the test logic and scoring before the container rehearsal.

## Check in Harbor

Start Docker and install Harbor `0.25.0` in a Python 3.12 environment. Docker needs network access during image build to fetch Click and the pinned PyPI dependencies. The task runtime and tests use local files.

```sh
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install 'harbor==0.25.0'

harbor run -p regenerated/datetime-bounds -a nop -k 1 -o harbor-evidence/nop --no-delete -y
harbor run -p regenerated/datetime-bounds -a oracle -k 1 -o harbor-evidence/oracle --no-delete -y
```

Repeat for all five paths. On the clean baseline, every feature test should fail and the selected regression tests should pass, giving `0.0`. With the reference patch, all checks should pass, giving `1.0`. Check the logs to distinguish a valid baseline score from regression breakage. A missing reward indicates a verifier or environment error.

The [local evidence](evidence/) comes from the packaged verifier on macOS. The Docker and Harbor matrix is the remaining teammate handoff before submission. [Participant guide](https://docs.google.com/document/d/1dk_C057AJFQsL5UzmNZ1YoQB7AWSml7go0NUrX-UrCM/edit) · [Harbor 0.25.0](https://pypi.org/project/harbor/0.25.0/)

## How the factory works

1. Confirm that the supplied checkout is clean and matches the requested commit. Read the required source and dependency lock directly from that Git commit.
2. Apply each recipe as scoped edits to the source in memory. Reject missing or ambiguous anchors, compile the resulting Python source, and use Git to check that the diff applies to the clean clone.
3. Build each standalone instruction, Docker environment, patch, and verifier. Derive the feature-test selectors from the generated test functions. Publish the output directory after all requested packages are complete.
4. Score regressions and features separately. A regression failure scores `0.0`. When regressions pass, reward equals the share of passing feature tests. Tool and collection errors produce no reward.

The current prototype uses five curated recipes in `recipes.py`. These cover distinct Click behaviors and produce repeatable outputs for the verified commit. Extending the set means defining another feature recipe with its behavior, source edits, and acceptance checks. The pipeline uses no model API or credentials. It reuses Click's native pytest suite and Harbor's task layout.

## Demo outline

1. Show that the starter checkout is clean and pinned.
2. Run the generator into a fresh directory and show the five package names.
3. Open the date-bounds instruction and the two test manifests.
4. Show the actual Harbor baseline and oracle results and the test outcomes behind the rewards.

## License

The factory is licensed under the [3-Clause BSD License](LICENSE). The reference
patches include context from Click, whose original license and copyright notice
are in [the Click license file](licenses/Click-BSD-3-Clause.txt).
