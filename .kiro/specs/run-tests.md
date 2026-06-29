# Spec: Run Tests

## Goal

Run the full test suite and report results. Used to verify correctness after any code change.

## Steps

1. Ensure the virtual environment is active: `source .venv/bin/activate` (or prefix commands with `uv run`)
2. Run `uv run pytest -v --tb=short` from the project root
3. If any tests fail, read the error output and identify the root cause
4. Run `uv run pytest --cov --cov-report=term-missing` to check coverage
5. Coverage must be ≥ 80% (enforced by `pyproject.toml → [tool.coverage.report] fail_under = 80`)

## Pass criteria

- All tests pass (exit code 0)
- Coverage ≥ 80%

## Common failure modes

| Symptom | Likely cause |
|---------|-------------|
| `ImportError` on test start | Missing dependency — run `uv sync --all-extras` |
| `fixture 'db' not found` | conftest.py not on path — run from project root |
| `RuntimeError: no running event loop` | Test not using `asyncio_mode = "auto"` — check `pyproject.toml` |
| LLM call goes to real API | Missing `@patch` on `LLMService.completion` |

## Notes

- Tests use in-memory SQLite — no `terra.db` file is touched
- LLM is always mocked — no API key needed for tests
- `tests/fixtures/static_kb_sample.json` is the sample KB used in static KB tests
