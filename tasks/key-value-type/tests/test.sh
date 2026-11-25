#!/bin/sh
set -eu
tests_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec python "$tests_dir/verify.py" --repo /app --logs /logs/verifier
