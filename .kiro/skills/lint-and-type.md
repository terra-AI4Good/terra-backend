# Skill: lint-and-type

Run ruff lint, ruff format check, and mypy type checking.

## Usage

```
lint-and-type
lint-and-type --fix
lint-and-type --types-only
```

## Behavior

**`lint-and-type`** (no args)
```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src/
```

**`lint-and-type --fix`**
```bash
uv run ruff check --fix .
uv run ruff format .
uv run mypy src/
```
Auto-fixes safe lint issues and formats code. Reports what was changed.

**`lint-and-type --types-only`**
```bash
uv run mypy src/
```

## Output format

For each tool, report pass/fail and the first 5 issues if any. End with:
```
Ruff lint: PASS (or N issues)
Ruff format: PASS (or N files need formatting)
mypy: PASS (or N errors)
```
