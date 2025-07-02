#!/usr/bin/env bash
set -euo pipefail

CHECK=""
if [[ "${1-}" == "--check" ]]; then
  CHECK="--check"
  shift || true
fi

isort ${CHECK} .
black ${CHECK} .
# Ensure flake8 reads configuration from pyproject.toml
flake8 --config pyproject.toml "$@"
