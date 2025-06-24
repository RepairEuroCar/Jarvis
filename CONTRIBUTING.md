# Contributing to Jarvis

Thank you for your interest in improving Jarvis! Before submitting a pull request please ensure that the test suite passes.

The project includes an automatic workflow that generates core tests and runs `pytest` on every pull request. You can reproduce the same behavior locally by running:

```bash
./scripts/run_core_tests.sh
```

This script executes `scripts/generate_core_tests.py` and then runs the test suite. Any generated tests will be included in your commit, so remember to add them before pushing.
