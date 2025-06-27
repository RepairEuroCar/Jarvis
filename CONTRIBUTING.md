# Contributing to Jarvis

Thank you for your interest in contributing!

## Running tests

Pull requests trigger the CI workflow which automatically generates tests for any new core functions using `scripts/generate_core_tests.py` and then runs the full test suite. You can replicate this locally by executing:

```bash
./scripts/run_core_tests.sh
```

This script regenerates tests under `tests/generated/` and executes `pytest` with coverage.

Pull requests must maintain at least **80%** test coverage. The CI workflow uploads coverage
results and posts a comment on the pull request showing the total coverage and how far it is
from this threshold. If coverage drops below 80%, the workflow will fail.
