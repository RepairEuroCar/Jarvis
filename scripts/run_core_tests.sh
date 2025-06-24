#!/usr/bin/env bash
set -euo pipefail

python scripts/generate_core_tests.py
coverage run -m pytest "$@"
