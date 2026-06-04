---
title: Stabilizing Level 3 LLM-as-Judge Tests
date: 2026-06-02
category: test-failures
module: research-summarizer-agent
problem_type: test_failure
component: testing_framework
symptoms:
  - "Level 3 LLM-as-judge pytest runs were nondeterministic because they depended on live Tavily search results."
  - "The judge rubric produced an over-strict citation failure by treating flat bibliography citations as positional per-finding citations."
  - "The agent failed Level 3 factual grounding by adding names or dates not explicitly present in search snippets."
  - "The agent sometimes returned invalid structured output, such as key_findings as a string instead of a list."
root_cause: test_isolation
resolution_type: test_fix
severity: medium
related_components:
  - assistant
  - documentation
  - tooling
tags:
  - level3-evals
  - llm-as-judge
  - tavily-fixtures
  - replay-tests
  - citation-rubric
  - strict-tool-use
  - prompt-grounding
---

# Stabilizing Level 3 LLM-as-Judge Tests

## Problem

Level 3 tests for the research summarizer mixed live Tavily search variability, agent behavior, and LLM judge interpretation in one pytest run. The evals surfaced real quality issues, but live search and an initially over-strict citation rubric made failures harder to classify and reproduce.

## Symptoms

- `pytest tests/test_level3.py -v` produced different failure modes across runs.
- The penicillin topic failed because the agent added unsupported facts such as unstated date ranges or names absent from snippets.
- Photosynthesis runs sometimes failed objective checks because the agent returned fewer citations than key findings.
- Urban heat island runs exposed a judge rubric bug: the judge assumed citation order mapped to finding order even though the schema has a flat `citations` list.
- One run failed before judging because `key_findings` came back as a string instead of a list.

## What Didn't Work

- **Pure live Tavily Level 3 runs**: live search was realistic, but it made failures hard to reproduce. A failure could come from changed search snippets, model variation, or judge strictness rather than the code under test.
- **Positional citation judging**: treating `citation[0]` as support for `key_findings[0]` was too strict because `SummaryResult` has a flat bibliography, not per-finding citation references.
- **Weakening factual grounding**: some failures were genuine hallucination/grounding problems. For example, historically true facts were still invalid when they did not appear in the provided snippets.
- **Prompt-only schema reliability**: forced tool use alone did not prevent malformed tool input, such as `key_findings` being returned as a string.

## Solution

### Replay Tavily fixtures by default

Record representative Tavily results in `tests/fixtures/level3_search_results.json` and replay them during normal Level 3 pytest runs. Keep live search behind an explicit refresh flag:

```python
FIXTURE_PATH = REPO_ROOT / "tests" / "fixtures" / "level3_search_results.json"
LIVE_SEARCH_ENV = "LIVE_LEVEL3_SEARCH"


def _uses_live_search() -> bool:
    return os.environ.get(LIVE_SEARCH_ENV) == "1"


def _search_results_for(topic: str) -> list[SearchResult]:
    if _uses_live_search():
        search_results = TavilySearchTool().search(topic, max_results=5)
        _refresh_search_fixture(topic, search_results)
        return search_results

    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    raw_results = fixture.get("topics", {}).get(topic)
    return [SearchResult.model_validate(result) for result in raw_results]
```

Normal replay mode:

```bash
pytest tests/test_level3.py
```

Intentional live refresh mode:

```bash
LIVE_LEVEL3_SEARCH=1 pytest tests/test_level3.py
```

### Keep objective checks in code

Use deterministic Python assertions for schema and provenance constraints before spending judge tokens:

```python
if len(result.citations) < len(result.key_findings):
    errors.append(
        f"expected at least one citation per finding, got "
        f"{len(result.citations)} citations for {len(result.key_findings)} findings"
    )

unexpected_urls = sorted(set(citation_urls) - allowed_urls)
if unexpected_urls:
    errors.append(f"citations include URLs not returned by Tavily: {unexpected_urls}")
```

### Match the judge rubric to the schema

The judge rubric now treats citations as a flat bibliography:

```text
citation_support: treat the citations as a flat bibliography, not as a
positional mapping to key findings. Do not assume citation 1 supports finding
1, citation 2 supports finding 2, etc. Pass this dimension when each key
finding's material claims are supported by one or more citation objects
anywhere in the citations list.
```

### Harden grounding in the prompt and spec

The prompt and `requirements/Research_Summarizer_Agent_Spec.md` now both require snippet-only grounding:

```python
SYSTEM_PROMPT = """You are a research assistant. Your job is to summarize information about a topic
based only on the web search results provided to you.

You must:
- Use only facts that are explicitly present in the search result snippets
- Return at least as many citations as key findings, and ensure the citations
  collectively support all material claims in the key findings

You must not:
- Invent facts not present in the search result snippets
- Add names, dates, institutions, mechanisms, impacts, or other details unless
  they appear in the search result snippets
- Infer unstated dates or date ranges from general knowledge or relative clues
"""
```

### Use strict Anthropic tool input

Forced tool use ensures the model calls the tool; strict tool use improves schema conformance for the tool input:

```python
tools=[
    {
        "name": _TOOL_NAME,
        "description": (
            "Return the structured research summary with key_findings "
            "as a JSON array of strings and citations as a JSON array "
            "of source objects."
        ),
        "input_schema": summary_result_tool_schema(),
        "strict": True,
    }
]
```

### Forbid extra Pydantic fields

`extra="forbid"` makes the emitted JSON schema include `additionalProperties: false`, which strict tool use expects for nested object schemas:

```python
from pydantic import BaseModel, ConfigDict


class Citation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    url: str
    snippet: str


class SummaryResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    topic: str
    synopsis: str
    key_findings: list[str]
    citations: list[Citation]
```

## Why This Works

Replay-first Level 3 evals separate the moving parts:

- Tavily variability is controlled by fixtures.
- The agent and judge still use real Anthropic calls.
- Objective invariants fail quickly and deterministically.
- The LLM judge focuses on semantic quality and grounding.
- Live search remains available as an explicit fixture-refresh workflow.

The agent hardening addresses the real failures discovered by Level 3:

- Snippet-only prompt language prevents unsupported names and date ranges.
- Citation instructions align output expectations with the Level 2/3 contract.
- Strict tool use plus `additionalProperties: false` improves schema reliability.

## Prevention

- Prefer replayed retrieval fixtures for Level 3 tests of search/RAG-style agents; use live retrieval only for intentional refresh runs.
- Keep objective invariants in code and reserve LLM judges for semantic claims, tone, reasoning quality, and hallucination detection.
- Calibrate judge rubrics against the actual schema. If citations are flat, do not judge them as positional.
- Treat historically true but unprovided facts as hallucinations when the contract is grounded summarization.
- When using Anthropic native tool use for structured output, use detailed tool descriptions and `strict: True` when schema conformance matters.
- Keep spec and prompt text synchronized when prompt semantics are contractual.

## Related Issues

- `requirements/Testing-Pyramid.md` — defines Level 3 LLM-as-judge evals and transaction replay.
- `requirements/Research_Summarizer_Agent_Spec.md` — defines grounded citation semantics and the structured output contract.
- `evals/judge_eval.py` — existing live LLM-as-judge demo that inspired the pytest driver.
- `tests/test_level3.py` — replay-based Level 3 pytest driver.
- `tests/fixtures/level3_search_results.json` — recorded Tavily search fixtures.
- `solution/tests/test_level3.py` and `solution/Level3-Claude-Conversation.md` — likely refresh candidates now that the Level 3 approach has changed.
