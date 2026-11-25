#!/bin/sh
set -eu
solution_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
git -C "${1:-/app}" apply "$solution_dir/reference.patch"
