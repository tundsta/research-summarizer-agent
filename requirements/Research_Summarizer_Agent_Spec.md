# Research Summarizer Agent: Technical Specification

**Version:** 1.0 (draft for build team)
**Status:** For review
**Purpose:** Workshop vehicle for the AI Agent Testing Pyramid hands-on session

---

## Overview

***The Research Summarizer Agent is an intentionally simple, single-purpose agent designed to serve as a teaching vehicle -- not a production system.*** Its complexity is calibrated so workshop attendees can understand its full behavior in under ten minutes, leaving the remaining time for writing tests. Every design decision below should be evaluated against that constraint.

The agent accepts a topic string, invokes a web search tool, and returns a structured summary containing a synopsis, key findings, and cited sources. Each invocation is stateless -- there is no conversation history, session state, or memory between calls.

This agent will be used in a workshop to illustrate different forms of testing decoumented in file `requirements/Testing-Pyramid.md`.

Workshop attendees will be creating tests using Claude Code without the experimental agent teams feature.

---

## Repository Layout

```
research-summarizer/
├── agent/
│   ├── __init__.py
│   ├── __main__.py       # `python -m agent` entry point (delegates to cli.main)
│   ├── agent.py          # orchestration logic and main entry point
│   ├── cli.py            # thin CLI wrapper around summarize()
│   ├── tools.py          # search tool interface and implementations
│   ├── models.py         # SummaryResult and supporting types
│   └── prompts.py        # system prompt and prompt construction
├── tests/
│   ├── __init__.py
│   ├── test_level1.py    # starter file with stubs (attendees fill in)
│   └── test_level2.py    # starter file with stubs (attendees fill in)
├── evals/
│   └── judge_eval.py     # pre-built LLM-as-judge demo (workshop Segment 5)
├── exercises/
│   └── level1_prompts.md # suggested Claude Code prompts for workshop Segment 3
├── sample_outputs/       # pre-generated SummaryResult examples
├── solution/             # complete automated test suite (published answers)
├── verify_setup.py       # pre-workshop environment self-check
├── .env.example          # environment variable template
├── requirements.txt
└── README.md
```

---

## Public Interface

***The agent exposes a single public function.*** All other symbols in the `agent` package are considered internal implementation details and may change without notice.

```python
from agent import summarize

result: SummaryResult = summarize(topic: str) -> SummaryResult
```

### Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `topic` | `str` | Yes | The subject to research. Must be non-empty after stripping whitespace. |

### Return Value

Returns a `SummaryResult` instance. See the Data Model section for the full schema.

### Exceptions

| Exception | Raised When |
|---|---|
| `ValueError` | `topic` is empty or whitespace-only |
| `SearchToolError` | The search tool returns an error or times out |
| `NoResultsError` | The search tool returns zero results for the given topic |
| `anthropic.APIError` | The Anthropic API returns an error (propagated as-is) |

***All exceptions are raised immediately with no retry logic.*** This is an intentional simplification for the workshop. Error handling complexity is a distraction from the testing concepts being taught.

---

## Data Model

***The build team should choose between a Pydantic model and a plain dataclass based on their preference.*** Both are acceptable. The fields and their semantics are specified here and must be honored regardless of implementation choice.

### SummaryResult

```python
# Pydantic implementation (recommended -- enables automatic validation)
from pydantic import BaseModel, Field

class Citation(BaseModel):
    title: str                  # page or article title from search result
    url: str                    # source URL
    snippet: str                # brief excerpt supporting its use

class SummaryResult(BaseModel):
    topic: str                  # echoed from input
    synopsis: str               # 2-4 sentence overview of the topic
    key_findings: list[str]     # 2-5 distinct findings, each 1-2 sentences
    citations: list[Citation]   # one citation per key finding, minimum

# Plain dataclass alternative (simpler, no validation)
from dataclasses import dataclass

@dataclass
class Citation:
    title: str
    url: str
    snippet: str

@dataclass
class SummaryResult:
    topic: str
    synopsis: str
    key_findings: list[str]
    citations: list[Citation]
```

### Field Constraints

| Field | Constraint | Rationale |
|---|---|---|
| `synopsis` | 2-4 sentences | Enforced via prompt instruction; not validated in code |
| `key_findings` | 2-5 items | Enforced via prompt instruction; not validated in code |
| `citations` | Length >= length of `key_findings` | Enforced via prompt instruction; not validated in code |
| `citations[].url` | Must be a URL present in search tool output | Prevents hallucinated citations |

***Citation URLs must be traceable to actual search tool output.*** This constraint is what makes citation integrity testable at Level 2 and is the primary semantic regression risk the LLM-as-judge eval covers at Level 3.

---

## Search Tool Interface

***The search tool is the sole external dependency and the primary mock boundary for Level 1 tests.*** Its interface must be clean and injectable so tests can substitute a controlled implementation without patching internals.

### Interface Definition

```python
from typing import Protocol

class SearchResult:
    title: str
    url: str
    snippet: str

class SearchTool(Protocol):
    def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        """
        Search for web results matching query.

        Raises SearchToolError on API failure or timeout.
        Returns an empty list if no results are found (does NOT raise).
        """
        ...
```

***The tool returns an empty list for zero results rather than raising.*** The agent is responsible for detecting this condition and raising `NoResultsError`. This separation is intentional -- it gives Level 1 tests a clear seam to test agent-side zero-result handling independently of the tool.

### Implementations

The build team must provide two implementations of the `SearchTool` protocol:

**TavilySearchTool** (real implementation)

- Uses the [Tavily Search API](https://tavily.com)
- Requires `TAVILY_API_KEY` environment variable
- Should be the default when the environment variable is present
- Timeout: 10 seconds

**StubSearchTool** (fallback implementation)

- Accepts a pre-configured list of `SearchResult` objects at construction time
- Returns the pre-configured list regardless of query
- Used by Level 1 tests and as a fallback when `TAVILY_API_KEY` is absent
- Must be importable from `agent.tools`

```python
# StubSearchTool construction pattern for tests
from agent.tools import StubSearchTool, SearchResult

stub = StubSearchTool(results=[
    SearchResult(
        title="Example Result",
        url="https://example.com/article",
        snippet="Relevant excerpt from the article."
    )
])
```

### Tool Selection Logic

```
if TAVILY_API_KEY is set in environment:
    use TavilySearchTool
else:
    use StubSearchTool with an empty result list
    (agent will raise NoResultsError on invocation)
```

***The tool selection must be overridable via dependency injection.*** The `summarize()` function must accept an optional `search_tool` parameter so tests can inject a stub without monkeypatching.

```python
def summarize(topic: str, search_tool: SearchTool | None = None) -> SummaryResult:
    ...
```

---

## Orchestration Logic

***The orchestration sequence must be simple enough to diagram on a single slide.*** If it becomes more complex than the steps below, it has drifted outside the workshop's scope.

### Sequence

```
1. Validate input
   - Strip whitespace from topic
   - Raise ValueError if empty

2. Execute search
   - Call search_tool.search(topic, max_results=5)
   - Raise NoResultsError if result list is empty

3. Build prompt
   - Construct user message containing topic and formatted search results
   - See Prompts section for format requirements

4. Call LLM
   - Model: claude-haiku-4-5-20251001 (pinned)
   - temperature: configurable, default 1.0
   - max_tokens: 1024
   - Request structured output matching SummaryResult schema
   - Use Anthropic native strict tool use when available to enforce schema types

5. Parse and return
   - Parse LLM response into SummaryResult
   - Propagate anthropic.APIError on failure
```

### Pinned Model

The agent must use `claude-haiku-4-5-20251001` and must not fall back to an alias such as `claude-haiku-latest`. Model pinning is a teaching point in the workshop -- aliased model names can silently change behavior between the time the workshop is built and the day it runs.

---

## Prompts

### System Prompt

```
You are a research assistant. Your job is to summarize information about a topic
based only on the web search results provided to you.

You must:
- Write a synopsis of 2-4 sentences covering the topic at a high level
- Identify 2-5 distinct key findings supported by the search results
- Use only facts that are explicitly present in the search result snippets
- Cite at least one source per key finding using only URLs present in the
  provided search results
- Return at least as many citations as key findings, and ensure the citations
  collectively support all material claims in the key findings

You must not:
- Invent facts not present in the search result snippets
- Add names, dates, institutions, mechanisms, impacts, or other details unless
  they appear in the search result snippets
- Infer unstated dates or date ranges from general knowledge or relative clues
- Cite URLs that were not provided to you
- Express opinions or recommendations
```

### User Message Format

```
Topic: {topic}

Search Results:
{for each result}
[{index}] {title}
URL: {url}
{snippet}

{end for}

Return a structured summary following the required schema.
```

---

## Configuration

All configuration must be via environment variables. No configuration files.

| Variable | Required | Default | Description |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | -- | Anthropic API key |
| `TAVILY_API_KEY` | No | -- | Tavily Search API key; if absent, StubSearchTool is used |
| `SUMMARIZER_MODEL` | No | `claude-haiku-4-5-20251001` | Override the model (for instructor use only) |
| `SUMMARIZER_TEMPERATURE` | No | `1.0` | Override temperature (set to `0` for Level 2 tests) |

---

## Command-Line Interface

***A thin CLI wrapper around `summarize()` is provided so workshop attendees can run the agent without writing Python.*** The CLI must add no new behavior — only argument parsing, output formatting, and exception-to-exit-code mapping.

### Invocation

```bash
python -m agent <topic>            # plain-text output
python -m agent --json <topic>     # SummaryResult as indented JSON
python -m agent --help             # usage
```

The implementation lives in `agent/cli.py` with `agent/__main__.py` as the package entry point. No `console_scripts` entry point or separate install step is required.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `topic` | positional, `str` | Yes | The subject to research. Must be non-empty after stripping whitespace. |
| `--json` | flag | No | Emit `SummaryResult.model_dump_json(indent=2)` to stdout instead of plain text. |

No flags for model, temperature, or API keys. Configuration remains entirely environment-variable-driven per the *Configuration* section.

### Output

- **stdout:** the `SummaryResult` only — plain-text by default, JSON when `--json` is passed. Nothing else is written to stdout.
- **stderr:** error messages on a single line in the form `error: <ExceptionClass>: <message>`. Used for any of the four exceptions `summarize()` documents.

### Exit Codes

| Code | Meaning |
|---|---|
| 0 | Success — a `SummaryResult` was printed to stdout |
| 1 | Any of the four documented exceptions was raised (`ValueError`, `NoResultsError`, `SearchToolError`, `anthropic.APIError`) |
| 2 | argparse usage error (missing `topic`, unknown flag, etc.) |

***The CLI catches only the four exceptions `summarize()` documents.*** Any other exception propagates as a Python traceback. Catching `Exception` would hide bugs from workshop attendees.

---

## Test Starter Files

***The starter files are as important as the agent itself.*** They determine the workshop attendee experience. Each starter file must compile and run cleanly out of the box, with stubs that fail meaningfully rather than erroring on import.

### tests/test_level1.py (required stubs)

The file must include working boilerplate for:

- Importing `summarize` and `StubSearchTool`
- A `stub_results` fixture returning two pre-built `SearchResult` objects
- A stub test asserting that `summarize("", ...)` raises `ValueError` (this one should pass -- it shows attendees what a passing test looks like before they write their own)
- Commented stubs for: zero results raises `NoResultsError`, tool failure raises `SearchToolError`, result fields map correctly to `SummaryResult`

### tests/test_level2.py (required stubs)

The file must include working boilerplate for:

- Model and temperature constants at the top of the file (`TEST_MODEL`, `TEST_TEMPERATURE = 0`)
- A module-level skip guard: `pytest.importorskip` or a skip marker that skips the entire file if `ANTHROPIC_API_KEY` is not set
- A stub test for topic "photosynthesis" asserting `len(result.key_findings) >= 2` and `len(result.citations) >= 1`
- A comment explaining why the model is pinned and temperature is set to zero

---

## Intentional Weaknesses

***The agent must be seeded with at least one latent defect that Level 1 or Level 2 tests will surface.*** Nothing teaches testing like a test that catches something real. The build team should implement exactly one of the following and document which one was chosen in a `solution/DEFECTS.md` file that ships with the workshop materials alongside the completed tests.

| Option | Description | Caught at Level |
|---|---|---|
| A | Agent does not raise `NoResultsError` when search returns empty list -- returns an empty `SummaryResult` instead | Level 1 |
| B | Citation URLs are not validated against search tool output -- the prompt does not constrain the model to use only provided URLs | Level 2 |
| C | `key_findings` list is not bounded -- the prompt omits the 2-5 item constraint, so the model sometimes returns one finding for simple topics | Level 2 |

**Recommendation:** Option A. It produces a deterministic, fast-failing Level 1 test that is satisfying to write and easy to explain to an audience.

---

## verify_setup.py Requirements

The self-check script must validate the following and print a clear pass/fail for each:

1. Python version >= 3.11
2. All packages in `requirements.txt` are importable
3. `ANTHROPIC_API_KEY` is set and non-empty
4. A minimal Anthropic API call succeeds (single-token completion)
5. `TAVILY_API_KEY` presence (warn if absent, do not fail -- stub fallback is acceptable)

The script must exit with code 0 on full pass and code 1 on any failure.

---

## Out of Scope

The following are explicitly out of scope and must not be implemented:

- Multi-turn conversation or session state
- Result caching or deduplication
- Rate limiting or backoff retry logic
- Streaming responses
- Any UI or CLI beyond `verify_setup.py` and the workshop CLI specified in the *Command-Line Interface* section
- Logging frameworks (print statements are acceptable for the workshop)
- Authentication beyond API keys in environment variables


