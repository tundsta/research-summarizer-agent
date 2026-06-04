"""Level 3 LLM-as-judge evals for the research summarizer agent.

These tests replay recorded Tavily search results by default, then make real
Anthropic calls for both the agent and the judge. Run them explicitly with:

    pytest tests/test_level3.py

To intentionally refresh the recorded search fixtures from live Tavily, run:

    LIVE_LEVEL3_SEARCH=1 pytest tests/test_level3.py

The file skips unless ANTHROPIC_API_KEY is available. Live search refresh also
requires TAVILY_API_KEY.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
from pathlib import Path
from typing import Any

import anthropic
import pytest
from dotenv import load_dotenv

from agent import SearchResult, StubSearchTool, SummaryResult, summarize
from agent.tools import TavilySearchTool


load_dotenv()

REPO_ROOT = Path(__file__).resolve().parent.parent
TRACE_DIR = REPO_ROOT / ".pytest_cache" / "level3"
FIXTURE_PATH = REPO_ROOT / "tests" / "fixtures" / "level3_search_results.json"
LIVE_SEARCH_ENV = "LIVE_LEVEL3_SEARCH"

AGENT_MODEL = "claude-haiku-4-5-20251001"
JUDGE_MODEL = "claude-sonnet-4-6"
TEST_TEMPERATURE = 0

TOPICS = [
    "the discovery of penicillin",
    "photosynthesis",
    "urban heat islands",
]

JUDGE_TOOL_NAME = "return_level3_verdict"
JUDGE_DIMENSIONS = [
    "factual_grounding",
    "citation_support",
    "synopsis_quality",
    "findings_quality",
]


def _uses_live_search() -> bool:
    return os.environ.get(LIVE_SEARCH_ENV) == "1"


pytestmark = pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY")
    or (_uses_live_search() and not os.environ.get("TAVILY_API_KEY")),
    reason=(
        "Level 3 tests require ANTHROPIC_API_KEY; "
        f"{LIVE_SEARCH_ENV}=1 also requires TAVILY_API_KEY"
    ),
)


@pytest.fixture(autouse=True)
def constrained_level3_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin model settings so judge failures are semantic, not model drift."""
    monkeypatch.setenv("SUMMARIZER_MODEL", AGENT_MODEL)
    monkeypatch.setenv("SUMMARIZER_TEMPERATURE", str(TEST_TEMPERATURE))


@pytest.mark.parametrize("topic", TOPICS)
def test_summary_passes_llm_judge(topic: str) -> None:
    search_results = _search_results_for(topic)
    assert search_results, f"No recorded search results found for {topic!r}"

    # Re-inject the exact recorded or refreshed search results so the judge can
    # inspect the same evidence the agent saw. This mirrors evals/judge_eval.py
    # while keeping the test replayable by default.
    try:
        agent_result = summarize(topic, search_tool=StubSearchTool(search_results))
    except Exception as exc:
        trace_path = _write_trace(
            topic=topic,
            search_results=search_results,
            agent_result=None,
            judge_prompt=None,
            judge_verdict=None,
            objective_errors=[],
            agent_error=exc,
        )
        raise AssertionError(f"Agent failed before judging; trace: {trace_path}") from exc

    objective_errors = _objective_contract_errors(agent_result, search_results)
    if objective_errors:
        trace_path = _write_trace(
            topic=topic,
            search_results=search_results,
            agent_result=agent_result,
            judge_prompt=None,
            judge_verdict=None,
            objective_errors=objective_errors,
        )
        pytest.fail(
            "Level 3 objective checks failed before judging:\n"
            + "\n".join(f"- {error}" for error in objective_errors)
            + f"\nTrace: {trace_path}"
        )

    judge_prompt = _build_judge_prompt(topic, search_results, agent_result)
    judge_verdict = _judge_summary(judge_prompt)
    trace_path = _write_trace(
        topic=topic,
        search_results=search_results,
        agent_result=agent_result,
        judge_prompt=judge_prompt,
        judge_verdict=judge_verdict,
        objective_errors=[],
    )

    failing_dimensions = _failing_dimensions(judge_verdict)
    assert not failing_dimensions, (
        "Level 3 judge failed semantic dimensions:\n"
        + "\n".join(f"- {failure}" for failure in failing_dimensions)
        + f"\nTrace: {trace_path}"
    )


def _search_results_for(topic: str) -> list[SearchResult]:
    if _uses_live_search():
        search_results = TavilySearchTool().search(topic, max_results=5)
        _refresh_search_fixture(topic, search_results)
        return search_results

    if not FIXTURE_PATH.exists():
        pytest.fail(
            f"Level 3 search fixture is missing: {FIXTURE_PATH}. "
            f"Run {LIVE_SEARCH_ENV}=1 pytest tests/test_level3.py to create it."
        )

    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    raw_results = fixture.get("topics", {}).get(topic)
    if raw_results is None:
        pytest.fail(
            f"Level 3 search fixture has no results for {topic!r}. "
            f"Run {LIVE_SEARCH_ENV}=1 pytest tests/test_level3.py to refresh it."
        )
    return [SearchResult.model_validate(result) for result in raw_results]


def _refresh_search_fixture(topic: str, search_results: list[SearchResult]) -> None:
    if FIXTURE_PATH.exists():
        fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    else:
        fixture = {
            "description": (
                "Recorded Tavily search results for deterministic Level 3 replay "
                f"tests. Refresh intentionally with {LIVE_SEARCH_ENV}=1 pytest "
                "tests/test_level3.py."
            ),
            "topics": {},
        }

    topics = fixture.setdefault("topics", {})
    topics[topic] = [result.model_dump() for result in search_results]
    ordered_topics = {name: topics[name] for name in TOPICS if name in topics}
    ordered_topics.update(
        {name: topics[name] for name in sorted(topics) if name not in ordered_topics}
    )
    fixture["topics"] = ordered_topics
    fixture["refreshed_at"] = dt.datetime.now(dt.timezone.utc).isoformat()

    FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE_PATH.write_text(json.dumps(fixture, indent=2) + "\n", encoding="utf-8")


def _objective_contract_errors(
    result: SummaryResult,
    search_results: list[SearchResult],
) -> list[str]:
    errors: list[str] = []
    if not isinstance(result, SummaryResult):
        return [f"result is {type(result).__name__}, not SummaryResult"]

    allowed_urls = {search_result.url for search_result in search_results}
    citation_urls = [citation.url for citation in result.citations]

    if not result.synopsis.strip():
        errors.append("synopsis is empty")
    if not (2 <= len(result.key_findings) <= 5):
        errors.append(f"expected 2-5 key findings, got {len(result.key_findings)}")
    if any(not finding.strip() for finding in result.key_findings):
        errors.append("one or more key findings are empty")
    if len(result.citations) < len(result.key_findings):
        errors.append(
            f"expected at least one citation per finding, got "
            f"{len(result.citations)} citations for {len(result.key_findings)} findings"
        )
    if not citation_urls:
        errors.append("citations are empty")
    unexpected_urls = sorted(set(citation_urls) - allowed_urls)
    if unexpected_urls:
        errors.append(f"citations include URLs not returned by Tavily: {unexpected_urls}")
    if any(not citation.title.strip() for citation in result.citations):
        errors.append("one or more citation titles are empty")
    if any(not citation.snippet.strip() for citation in result.citations):
        errors.append("one or more citation snippets are empty")

    return errors


def _build_judge_prompt(
    topic: str,
    search_results: list[SearchResult],
    agent_result: SummaryResult,
) -> str:
    search_payload = [result.model_dump() for result in search_results]
    agent_payload = agent_result.model_dump()
    return f"""Grade this research summarizer output.

Topic:
{topic}

Search results provided to the agent:
{json.dumps(search_payload, indent=2)}

Agent output:
{json.dumps(agent_payload, indent=2)}

Use only the search results above as evidence. Be strict but fair: do not
penalize the agent for omitting details that are not required by the task, but
mark unsupported claims, hallucinated facts, weak citation support, opinions, or
recommendations as failures. If the provided evidence is insufficient to decide
a dimension, return "unknown" for that dimension rather than guessing.

Grade these dimensions independently:
- factual_grounding: every factual claim in the synopsis and key findings is
  supported by or consistent with any of the search-result snippets; there are
  no contradictions or fabricated facts. Treat facts from general knowledge as
  unsupported unless they appear in the provided snippets. Do not fail this
  dimension because the claim is supported by a different search result than a
  listed citation; source-to-output support is checked separately.
- citation_support: treat the citations as a flat bibliography, not as a
  positional mapping to key findings. Do not assume citation 1 supports finding
  1, citation 2 supports finding 2, etc. Pass this dimension when each key
  finding's material claims are supported by one or more citation objects
  anywhere in the citations list. URL membership is already checked by code, so
  focus on whether the listed citation snippets collectively support the key
  findings. Fail if a finding is supported only by an uncited search result, or
  if a finding combines multiple material claims and the citation list does not
  support all of them.
- synopsis_quality: the synopsis is 2-4 sentences, on-topic, high-level,
  neutral, clear, and free of opinions or recommendations. Do not fail this
  dimension solely for unsupported facts; report those under factual_grounding.
- findings_quality: the key findings are 2-5 distinct, substantive,
  non-duplicative, and clearly written. Do not fail this dimension solely for
  unsupported facts; report those under factual_grounding or citation_support.
  Do fail this dimension for confusing, garbled, or misleading wording.

Return the verdict by calling the {JUDGE_TOOL_NAME} tool."""


def _judge_summary(judge_prompt: str) -> dict[str, Any]:
    client = anthropic.Anthropic()
    response = client.messages.create(
        model=JUDGE_MODEL,
        max_tokens=1024,
        temperature=TEST_TEMPERATURE,
        system=(
            "You are an evaluation judge for a research summarizer. Return only "
            "the requested tool call. Each dimension must be pass, fail, or "
            "unknown with a concise critique."
        ),
        tools=[
            {
                "name": JUDGE_TOOL_NAME,
                "description": "Return Level 3 pass/fail/unknown judge verdicts.",
                "input_schema": _judge_tool_schema(),
            }
        ],
        tool_choice={"type": "tool", "name": JUDGE_TOOL_NAME},
        messages=[{"role": "user", "content": judge_prompt}],
    )

    for block in response.content:
        if getattr(block, "type", None) == "tool_use" and block.name == JUDGE_TOOL_NAME:
            return dict(block.input)
    raise RuntimeError(f"Judge response did not include a {JUDGE_TOOL_NAME} tool_use block")


def _judge_tool_schema() -> dict[str, Any]:
    dimension_schema = {
        "type": "object",
        "properties": {
            "verdict": {"type": "string", "enum": ["pass", "fail", "unknown"]},
            "critique": {"type": "string"},
        },
        "required": ["verdict", "critique"],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {
            "factual_grounding": dimension_schema,
            "citation_support": dimension_schema,
            "synopsis_quality": dimension_schema,
            "findings_quality": dimension_schema,
            "overall_comments": {"type": "string"},
        },
        "required": [*JUDGE_DIMENSIONS, "overall_comments"],
        "additionalProperties": False,
    }


def _failing_dimensions(judge_verdict: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    for dimension in JUDGE_DIMENSIONS:
        result = judge_verdict.get(dimension, {})
        verdict = result.get("verdict", "missing")
        critique = result.get("critique", "")
        if verdict != "pass":
            failures.append(f"{dimension}: {verdict} — {critique}")
    return failures


def _write_trace(
    *,
    topic: str,
    search_results: list[SearchResult],
    agent_result: SummaryResult | None,
    judge_prompt: str | None,
    judge_verdict: dict[str, Any] | None,
    objective_errors: list[str],
    agent_error: Exception | None = None,
) -> Path:
    TRACE_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    slug = re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-")
    trace_path = TRACE_DIR / f"{timestamp}-{slug}.json"
    trace = {
        "topic": topic,
        "agent_model": AGENT_MODEL,
        "judge_model": JUDGE_MODEL,
        "temperature": TEST_TEMPERATURE,
        "search_results": [result.model_dump() for result in search_results],
        "agent_result": agent_result.model_dump() if agent_result is not None else None,
        "agent_error": (
            {"type": type(agent_error).__name__, "message": str(agent_error)}
            if agent_error is not None
            else None
        ),
        "objective_errors": objective_errors,
        "judge_prompt": judge_prompt,
        "judge_verdict": judge_verdict,
        "run_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    trace_path.write_text(json.dumps(trace, indent=2) + "\n", encoding="utf-8")
    return trace_path
