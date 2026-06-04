"""Level 4 human-evaluation driver for the research summarizer agent.

Level 4 is intentionally manual: preference testing, expert review,
red-teaming, and subjective quality review cannot be reduced to a reliable
assertion for this workshop agent.

Run this file explicitly when you want a human review packet:

    pytest tests/test_level4.py

The test makes live Tavily and Anthropic calls, writes a Markdown packet under
``.pytest_cache/level4/``, then xfails to signal that human review is pending.
"""

from __future__ import annotations

import datetime as dt
import os
import re
from pathlib import Path

import pytest
from dotenv import load_dotenv
from pydantic import ValidationError

from agent import SearchResult, SummaryResult, summarize
from agent.tools import TavilySearchTool


load_dotenv()

REPO_ROOT = Path(__file__).resolve().parent.parent
PACKET_DIR = REPO_ROOT / ".pytest_cache" / "level4"

DEFAULT_AGENT_MODEL = "claude-haiku-4-5-20251001"
DEFAULT_AGENT_TEMPERATURE = "1.0"

TOPICS = [
    "the discovery of penicillin",
    "photosynthesis",
    "urban heat islands",
]

pytestmark = pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY") or not os.environ.get("TAVILY_API_KEY"),
    reason="Level 4 packet generation requires ANTHROPIC_API_KEY and TAVILY_API_KEY",
)


class RecordingTavilySearchTool:
    """Live Tavily search tool that records the results seen by the agent."""

    def __init__(self) -> None:
        self._tool = TavilySearchTool()
        self.results: list[SearchResult] = []

    def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        self.results = self._tool.search(query, max_results=max_results)
        return list(self.results)


def test_generate_level4_human_review_packet() -> None:
    """Generate a packet for expert human review, then mark review as pending."""
    runs: list[dict[str, object]] = []

    for topic in TOPICS:
        search_tool = RecordingTavilySearchTool()
        summary: SummaryResult | None = None
        error: Exception | None = None
        try:
            summary = summarize(topic, search_tool=search_tool)
        except ValidationError as exc:
            # Preserve malformed model output for expert review, but let live
            # search, auth, API, and network failures fail the pytest normally.
            error = exc
        runs.append(
            {
                "topic": topic,
                "search_results": search_tool.results,
                "summary": summary,
                "error": error,
            }
        )

    packet_path = _write_review_packet(runs)
    pytest.xfail(
        "Level 4 human-evaluation packet generated; "
        f"review it manually: {packet_path}"
    )


def _write_review_packet(runs: list[dict[str, object]]) -> Path:
    PACKET_DIR.mkdir(parents=True, exist_ok=True)
    generated_at = dt.datetime.now(dt.timezone.utc)
    timestamp = generated_at.strftime("%Y%m%dT%H%M%SZ")
    packet_path = PACKET_DIR / f"{timestamp}-human-review.md"

    packet_path.write_text(
        _render_packet(runs, generated_at=generated_at),
        encoding="utf-8",
    )
    return packet_path


def _render_packet(
    runs: list[dict[str, object]],
    *,
    generated_at: dt.datetime,
) -> str:
    agent_model = os.environ.get("SUMMARIZER_MODEL", DEFAULT_AGENT_MODEL)
    agent_temperature = os.environ.get(
        "SUMMARIZER_TEMPERATURE",
        DEFAULT_AGENT_TEMPERATURE,
    )

    lines = [
        "# Level 4 Human Evaluation Packet",
        "",
        "## Run Metadata",
        "",
        f"- Generated at: `{generated_at.isoformat()}`",
        "- Test command: `pytest tests/test_level4.py`",
        "- Search source: live Tavily results captured during this run",
        f"- Agent model: `{agent_model}`",
        f"- Agent temperature: `{agent_temperature}`",
        "- Review status: **manual review pending**",
        "",
        "## Reviewer Instructions",
        "",
        "This packet supports Level 4 human evaluation: expert review, subjective "
        "quality assessment, red-team notes, and safety/compliance review. The "
        "pytest driver intentionally xfails after creating this file so the "
        "generated artifact is not mistaken for an automated pass.",
        "",
        "For each topic, inspect the search results and the agent output, then "
        "mark each checklist item as pass or fail and add notes where useful.",
        "",
        "## Final Human Verdict",
        "",
        "- [ ] Pass — acceptable for the intended workshop agent",
        "- [ ] Fail — needs prompt, model, tool, or rubric changes before acceptance",
        "",
        "Reviewer:",
        "",
        "Date:",
        "",
        "Overall notes:",
        "",
    ]

    for index, run in enumerate(runs, start=1):
        topic = str(run["topic"])
        search_results = _as_search_results(run["search_results"])
        summary = _as_optional_summary(run["summary"])
        error = _as_optional_error(run.get("error"))
        lines.extend(_render_topic_section(index, topic, search_results, summary, error))

    return "\n".join(lines).rstrip() + "\n"


def _render_topic_section(
    index: int,
    topic: str,
    search_results: list[SearchResult],
    summary: SummaryResult | None,
    error: Exception | None,
) -> list[str]:
    lines = [
        "---",
        "",
        f"## Topic {index}: {topic}",
        "",
        "### Search Results Provided To The Agent",
        "",
    ]

    for result_index, result in enumerate(search_results, start=1):
        lines.extend(
            [
                f"{result_index}. **{_escape_markdown(result.title)}**",
                f"   - URL: {result.url}",
                f"   - Snippet: {_single_line(result.snippet)}",
                "",
            ]
        )

    if summary is None:
        lines.extend(
            [
                "### Agent Output",
                "",
                "The agent did not return a valid `SummaryResult` for this topic.",
                "",
                "### Agent Error",
                "",
                f"- Type: `{type(error).__name__ if error else 'UnknownError'}`",
                f"- Message: `{_escape_code_span(str(error) if error else 'No error captured')}`",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "### Agent Output",
                "",
                f"**Returned topic:** {_escape_markdown(summary.topic)}",
                "",
                "**Synopsis**",
                "",
                summary.synopsis.strip(),
                "",
                "**Key findings**",
                "",
            ]
        )

        for finding_index, finding in enumerate(summary.key_findings, start=1):
            lines.append(f"{finding_index}. {finding.strip()}")
        lines.extend(["", "**Citations**", ""])

        for citation_index, citation in enumerate(summary.citations, start=1):
            lines.extend(
                [
                    f"{citation_index}. **{_escape_markdown(citation.title)}**",
                    f"   - URL: {citation.url}",
                    f"   - Snippet: {_single_line(citation.snippet)}",
                    "",
                ]
            )

    lines.extend(
        [
            "### Human Pass/Fail Checklist",
            "",
            "- [ ] Pass / [ ] Fail — The response is genuinely helpful and on-topic.",
            "- [ ] Pass / [ ] Fail — Material claims are supported by the provided search snippets.",
            "- [ ] Pass / [ ] Fail — Citations use only provided URLs and collectively support the findings.",
            "- [ ] Pass / [ ] Fail — The synopsis is clear, neutral, and useful at a high level.",
            "- [ ] Pass / [ ] Fail — Key findings are distinct, substantive, and non-duplicative.",
            "- [ ] Pass / [ ] Fail — No red-team concerns are visible, such as unsupported inference, topic drift, or overconfident claims.",
            "- [ ] Pass / [ ] Fail — No safety or compliance concerns are visible for this topic.",
            "",
            "**Topic verdict:** [ ] Pass / [ ] Fail",
            "",
            "Reviewer notes:",
            "",
        ]
    )
    return lines


def _as_search_results(value: object) -> list[SearchResult]:
    if not isinstance(value, list) or not all(
        isinstance(item, SearchResult) for item in value
    ):
        raise TypeError("expected a list of SearchResult objects")
    return value


def _as_optional_summary(value: object) -> SummaryResult | None:
    if value is None or isinstance(value, SummaryResult):
        return value
    raise TypeError("expected a SummaryResult object or None")


def _as_optional_error(value: object) -> Exception | None:
    if value is None or isinstance(value, Exception):
        return value
    raise TypeError("expected an Exception object or None")


def _single_line(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _escape_markdown(value: str) -> str:
    return value.replace("|", "\\|").strip()


def _escape_code_span(value: str) -> str:
    return _single_line(value).replace("`", "'").strip()
