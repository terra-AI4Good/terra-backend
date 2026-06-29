# Skill: run-tests

Run the test suite with optional coverage reporting.

## Usage

```
run-tests
run-tests --coverage
run-tests --file test_chatbot
run-tests --failed-only
```

## Behavior

**`run-tests`** (no args)
```bash
uv run pytest -v --tb=short
```

**`run-tests --coverage`**
```bash
uv run pytest --cov --cov-report=term-missing
```
Then report: total coverage %, which files are below 80%, which lines are missing.

**`run-tests --file <name>`**
```bash
uv run pytest tests/test_<name>.py -v --tb=long
```

**`run-tests --failed-only`**
```bash
uv run pytest --lf -v
```
Re-runs only tests that failed in the last run.

## Output format

Always end with a summary:
```
Tests: X passed, Y failed, Z skipped
Coverage: N% (threshold: 80%)
Status: PASS / FAIL
```

If any tests fail, list them by name and give the most likely fix for each.
