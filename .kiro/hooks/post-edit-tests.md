# Hook: Post-Edit Test Runner

## Trigger

After editing any file under `src/terra/` or `tests/`.

## Actions

1. Identify which module was changed (e.g. `src/terra/services/chatbot.py`)
2. Run the corresponding test file(s) first for fast feedback:
   - `src/terra/services/chatbot.py` → `tests/test_chatbot.py`
   - `src/terra/tools/*.py` → `tests/test_tools.py`
   - `src/terra/agents/*.py` → `tests/test_agents.py` + `tests/test_agents_api.py`
   - `src/terra/api/v1/endpoints/auth.py` → `tests/test_auth.py`
   - `src/terra/api/v1/endpoints/documents.py` → `tests/test_documents.py`
   - `src/terra/llm/` → `tests/test_llm.py`
3. If those pass, run the full suite: `uv run pytest -q`

## On failure

Show the failure immediately. Don't continue to the full suite if the targeted tests fail.

## Notes

This is an advisory hook — it surfaces test failures during development before a commit is made.
