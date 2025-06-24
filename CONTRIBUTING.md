# Contributing to Jarvis

Thank you for your interest in contributing!

## Running tests

Pull requests trigger the CI workflow which automatically generates tests for any new core functions using `scripts/generate_core_tests.py` and then runs the full test suite. You can replicate this locally by executing:

```bash
./scripts/run_core_tests.sh
```

This script regenerates tests under `tests/generated/` and executes `pytest` with coverage.
