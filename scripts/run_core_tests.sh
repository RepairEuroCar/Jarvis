#!/usr/bin/env bash
set -euo pipefail

PYTHONPATH="${PYTHONPATH:-.:}" python scripts/generate_core_tests.py
coverage run -m pytest "$@"
coverage xml -o coverage.xml
coverage report --fail-under=80
