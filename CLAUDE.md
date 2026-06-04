# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose and constraints

This is a **workshop teaching vehicle** for the AI Agent Testing Pyramid, not a production system. Every design decision is calibrated for ten-minute comprehension. The full source under `agent/` is intentionally under ~250 lines combined.

When making changes, preserve simplicity over robustness. Do not introduce abstractions, retry logic, caching, or extra layers (e.g. `instructor`) — the spec deliberately keeps Anthropic native `tool_use` as the only structured-output path.

Authoritative design docs:
- `requirements/Research_Summarizer_Agent_Spec.md` — field semantics and design rationale
- `requirements/Testing-Pyramid.md` — the testing model the workshop teaches
- `plans/ImplementationPlan.md` — the build plan that produced the current code

## Common commands

```bash
# Setup
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then add ANTHROPIC_API_KEY and TAVILY_API_KEY
python verify_setup.py # exits 0 when env is fully wired

# Run the agent
python -m agent "photosynthesis"            # plain-text
python -m agent --json "quantum computing"  # JSON SummaryResult

# Tests
pytest tests/test_level1.py     # fast, no API calls (mocked search tool)
pytest tests/test_level2.py     # real Anthropic + Tavily; auto-skips if keys missing
pytest tests/test_level1.py::test_name -v   # single test

# Eval (LLM-as-judge, calls real API)
python evals/judge_eval.py      # writes trace to sample_outputs/judge_eval_run.json

# Sample-output URL liveness check
python scripts/check_sample_urls.py
```

`conftest.py` at the repo root puts the project root on `sys.path` so `from agent import ...` works without a `pyproject.toml`.

## Architecture

The agent is stateless and runs a fixed five-step pipeline (`agent/agent.py::summarize`):

1. Validate the topic string (raise `ValueError` if empty).
2. Call the injected `SearchTool.search()` (Tavily by default; `StubSearchTool` in tests).
3. Format a user message via `agent/prompts.py::build_user_message`.
4. Call `claude-haiku-4-5-20251001` with `tool_choice` forcing the `return_summary` tool, whose `input_schema` is `SummaryResult.model_json_schema()`.
5. Parse the `tool_use` block back into a `SummaryResult` via `model_validate`.

Key seams and conventions:

- **`SearchTool` is a `Protocol`** (`agent/tools.py`). It is the only mock boundary for Level 1 tests — *do not* patch internals of `summarize()`. Inject a `StubSearchTool` instead. The agent (not the tool) is responsible for raising `NoResultsError` when the tool returns `[]`; this separation is what gives Level 1 tests a clean seam.
- **No Pydantic validators on `SummaryResult` / `Citation`.** Per spec, all bounds (synopsis sentence count, findings count, citation provenance) are enforced by the prompt only. Don't add field constraints.
- **Pinned model name** (`claude-haiku-4-5-20251001`), never an alias. Pin date is in `README.md`; refresh per the playbook there if stale.
- **Eval judge** uses `claude-sonnet-4-6` (not the agent's model) to grade four pass/fail dimensions.
- **Tavily timeout** is 10s, set in `TavilySearchTool._TIMEOUT_SECONDS`.
- **Env overrides**: `SUMMARIZER_MODEL` and `SUMMARIZER_TEMPERATURE` are read at call time. `TAVILY_API_KEY` absence falls back to `StubSearchTool(results=[])`, which makes every call raise `NoResultsError`.

## Workshop-specific layout

- `tests/test_level1.py` and `tests/test_level2.py` are **commented stubs** for attendees to fill in. Reference solutions live in `solution/tests/` and should not be edited as part of "fixing the tests" — they are the answer key.
- `solution/DEFECTS.md` is the instructor's defects writeup.
- `sample_outputs/*.json` are hand-curated `SummaryResult` examples with stable URLs (Wikipedia, NIH, quantum.gov). Verify liveness with `scripts/check_sample_urls.py` before each session.
- `exercises/`, `notes/`, `instructions/` hold workshop material. `plans/` and `requirements/` hold design docs.
- `docs/solutions/` holds documented solutions to past problems and durable workflow/testing learnings, organized by category with YAML frontmatter (`module`, `tags`, `problem_type`). Relevant when implementing or debugging in documented areas.
