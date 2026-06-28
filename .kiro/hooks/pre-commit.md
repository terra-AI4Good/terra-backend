# Hook: Pre-Commit Quality Gate

## Trigger

Before any commit to this repository.

## Actions

Run these checks in order. Stop on first failure and explain what broke.

```bash
# 1. Lint
uv run ruff check .

# 2. Format check (don't auto-fix — flag it)
uv run ruff format --check .

# 3. Type check
uv run mypy src/

# 4. Tests (fast — no coverage report needed for pre-commit)
uv run pytest -x -q
```

## On failure

- Lint errors: show the specific rule and line. Don't auto-fix unless asked.
- Format errors: run `uv run ruff format .` and stage the changes, then re-run.
- Type errors: explain the type mismatch and suggest the fix.
- Test failures: show the failing test name and traceback, suggest the root cause.

## Skip conditions

If the only changed files are in `.kiro/`, `docs/`, `README.md`, or `*.md` — skip the type check and tests (lint still runs).
