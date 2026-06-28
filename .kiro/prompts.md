# Terra Backend — Kiro Prompts

A collection of ready-to-use prompts for common development tasks. Each uses one or more of the project's specs, hooks, skills, and steering documents.

---

## Testing prompts

### Run the full test suite and report

```
Run all tests using the run-tests skill. Report which tests pass and fail.
If any fail, explain the root cause and suggest the fix.
After tests pass, run with --coverage and tell me which files are below 80%
and what specific lines/branches are missing.
```

*Uses: skill/run-tests, steering/project.md*

---

### Run tests for a specific area

```
Run tests for the chatbot module only (tests/test_chatbot.py).
Show me the full output with --tb=long so I can see any assertion details.
If everything passes, also run tests/test_agents.py and report the combined result.
```

*Uses: skill/run-tests, steering/conventions.md*

---

### Fix a failing test

```
The test `test_memory_retrieved_on_next_call` in tests/test_chatbot.py is failing.
Read the test, read the ChatbotService implementation in src/terra/services/chatbot.py,
and read the DatabaseMemoryStore in src/terra/memory/db_store.py.
Identify why the test is failing and fix the issue in the source code (not the test).
Then run tests/test_chatbot.py to confirm it passes.
```

*Uses: skill/run-tests, steering/architecture.md, steering/conventions.md*

---

## End-to-end cycle prompts

### Run the full e2e smoke test

```
Implement and run an end-to-end test following the e2e-cycle spec in .kiro/specs/e2e-cycle.md.
Write the test in tests/test_e2e.py.
The test must cover all 5 phases: auth, chatbot (mocked LLM), documents, agents listing, and health checks.
After writing, run it with `uv run pytest tests/test_e2e.py -v` and confirm all phases pass.
```

*Uses: spec/e2e-cycle.md, skill/run-tests, steering/architecture.md*

---

### Verify the live deployed service

```
The Terra backend is deployed at ECS. Using the AWS CLI:
1. Check that the ECS service terra-backend-28b2 has rolloutState=COMPLETED and runningCount=1
2. Check that the ALB target group ecs-gateway-tg-0af4c47a0922ee36f shows at least one healthy target
3. Describe the running task and show me its last 20 log lines from CloudWatch
   (log group: /aws/ecs/default/terra-backend-28b2-3fc8)
4. Report the overall health: HEALTHY / DEGRADED / DOWN
```

*Uses: skill/deploy (for context), steering/project.md*

---

## Documentation prompts

### Improve the README

```
The current README.md is minimal — it covers quick start and a project structure tree
but is missing context about what Terra actually does, who it's for, and how the
agentic system works.

Rewrite README.md to include:
1. A 2-3 sentence "What is Terra?" intro (immigrants in Germany, Integreat KB, BA jobs)
2. The existing Quick Start section (keep as-is)
3. An "Architecture" section with a short description of the chatbot flow and agent system
   (derive this from .kiro/steering/architecture.md — don't copy it verbatim, summarise for a README audience)
4. An "API Reference" section listing all endpoints with their method, path, auth requirement, and one-line description
5. The existing Development section (lint, type-check, migrations)
6. A "Deployment" section explaining the Docker + ECS setup and the ECR push flow
7. The existing Tech Stack section

Keep it tight — a developer should be able to onboard from the README alone.
Do not add emojis. Do not change pyproject.toml or any source files.
```

*Uses: steering/project.md, steering/architecture.md, spec/run-tests.md*

---

### Document a specific module

```
Write a clear module-level docstring and inline comments for src/terra/orchestration/runner.py.
The audience is a new contributor who understands Python async but hasn't seen this codebase.
Focus on WHY, not WHAT — the code already explains what it does.
Specifically explain:
- Why the tool-call loop exists and when it terminates
- Why context is currently unused (ARG002 suppress) and what it's intended for
- What happens if max_iterations is reached without a clean stop
Follow the conventions in .kiro/steering/conventions.md (no over-commenting, one-line max per comment).
```

*Uses: steering/conventions.md, steering/architecture.md*

---

## Quality / linting prompts

### Full quality gate before a PR

```
Run the full quality gate before I open a PR:
1. lint-and-type --fix (auto-fix safe issues, report what changed)
2. run-tests --coverage (all must pass, coverage ≥ 80%)
3. If anything fails, fix it and re-run until clean
4. Summarise what was fixed and confirm the final status
```

*Uses: skill/lint-and-type, skill/run-tests, hook/pre-commit.md*

---

### Check for missing test coverage on a new file

```
I just added src/terra/tools/my_new_tool.py.
Check the new-tool-checklist hook (.kiro/hooks/new-tool-checklist.md) against it:
- Does it subclass Tool?
- Is definition implemented?
- Is execute async?
- Is it registered in setup.py?
- Are there tests in tests/test_tools.py covering it?
Report each item as ✓ or ✗ and tell me what to add for any gaps.
```

*Uses: hook/new-tool-checklist.md, spec/add-tool.md*

---

## Scaffolding prompts

### Add a new tool (guided)

```
I want to add a tool that translates text using the DeepL API.
Follow the spec in .kiro/specs/add-tool.md to:
1. Create src/terra/tools/translate.py with a TranslateTool class
2. Parameters: text (string, required), target_language (string, required, enum: ["de","en","fr","es"])
3. Mock the actual HTTP call for now — return ToolResult(success=True, data={"translated": "[mock] " + text})
4. Register it in setup.py
5. Write 3 tests in tests/test_tools.py: success case, unsupported language, empty text
6. Run the tests and confirm they pass
```

*Uses: spec/add-tool.md, hook/new-tool-checklist.md, skill/run-tests*

---

### Add a new agent (guided)

```
I want to add an agent that specialises in answering questions about German bureaucracy
using only the static knowledge base.
Follow .kiro/specs/add-agent.md to:
1. Create src/terra/agents/bureaucracy_agent.py
2. System prompt: focus the agent on step-by-step bureaucratic process explanations
3. Tools: search_static_kb, get_static_kb_item, list_static_kb_categories
4. Register in setup.py with name "bureaucracy" and a one-line description
5. Write a test in tests/test_agents_api.py that posts to /api/v1/agents/run with agent_name="bureaucracy"
   and verifies the response has success=true (mock the LLM)
6. Run tests and confirm pass
```

*Uses: spec/add-agent.md, skill/run-tests, steering/architecture.md*
