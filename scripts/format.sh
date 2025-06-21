#!/usr/bin/env bash
set -euo pipefail

CHECK=""
if [[ "${1-}" == "--check" ]]; then
  CHECK="--check"
  shift || true
fi

isort ${CHECK} .
black ${CHECK} .
flake8 "$@"
