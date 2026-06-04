"""Level 1 deterministic tests for the research summarizer agent.

These tests stub every external service boundary so they can run quickly with:

    pytest tests/test_level1.py
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import anthropic
import pytest

from agent import (
    NoResultsError,
    SearchResult,
    SearchToolError,
    StubSearchTool,
    SummaryResult,
    summarize,
)


@pytest.fixture
def stub_results() -> list[SearchResult]:
    return [
        SearchResult(
            title="Photosynthesis overview",
            url="https://example.com/photosynthesis-overview",
            snippet="Photosynthesis converts light energy into chemical energy in plants.",
        ),
        SearchResult(
            title="Chlorophyll basics",
            url="https://example.com/chlorophyll-basics",
            snippet="Chlorophyll absorbs light that powers photosynthesis.",
        ),
    ]


@pytest.fixture
def summary_payload() -> dict[str, Any]:
    return {
        "topic": "photosynthesis",
        "synopsis": "Photosynthesis is the process plants use to turn light into stored chemical energy. It supports plant growth and many food webs.",
        "key_findings": [
            "Plants use chlorophyll to absorb light for photosynthesis.",
            "Photosynthesis produces energy-rich sugars that support plant growth.",
        ],
        "citations": [
            {
                "title": "Photosynthesis overview",
                "url": "https://example.com/photosynthesis-overview",
                "snippet": "Photosynthesis converts light energy into chemical energy in plants.",
            },
            {
                "title": "Chlorophyll basics",
                "url": "https://example.com/chlorophyll-basics",
                "snippet": "Chlorophyll absorbs light that powers photosynthesis.",
            },
        ],
    }


def install_fake_anthropic(
    monkeypatch: pytest.MonkeyPatch,
    payload: dict[str, Any],
) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []

    class FakeMessages:
        def create(self, **kwargs: Any) -> SimpleNamespace:
            calls.append(kwargs)
            return SimpleNamespace(
                content=[
                    SimpleNamespace(
                        type="tool_use",
                        name="return_summary",
                        input=payload,
                    )
                ]
            )

    class FakeAnthropic:
        def __init__(self) -> None:
            self.messages = FakeMessages()

    monkeypatch.setattr(anthropic, "Anthropic", FakeAnthropic)
    return calls


def test_empty_topic_raises_value_error(monkeypatch: pytest.MonkeyPatch) -> None:
    class ExplodingAnthropic:
        def __init__(self) -> None:
            raise AssertionError("LLM should not be called for an empty topic")

    class ExplodingSearchTool:
        def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
            raise AssertionError("search should not be called for an empty topic")

    monkeypatch.setattr(anthropic, "Anthropic", ExplodingAnthropic)

    with pytest.raises(ValueError, match="topic must be non-empty"):
        summarize("   ", search_tool=ExplodingSearchTool())


def test_search_receives_stripped_topic_and_max_results(
    monkeypatch: pytest.MonkeyPatch,
    stub_results: list[SearchResult],
    summary_payload: dict[str, Any],
) -> None:
    install_fake_anthropic(monkeypatch, summary_payload)
    calls: list[tuple[str, int]] = []

    class RecordingSearchTool:
        def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
            calls.append((query, max_results))
            return stub_results

    summarize("  photosynthesis  ", search_tool=RecordingSearchTool())

    assert calls == [("photosynthesis", 5)]


def test_empty_search_results_raise_no_results_error(
    monkeypatch: pytest.MonkeyPatch,
    summary_payload: dict[str, Any],
) -> None:
    anthropic_calls = install_fake_anthropic(monkeypatch, summary_payload)

    with pytest.raises(NoResultsError):
        summarize("photosynthesis", search_tool=StubSearchTool(results=[]))

    assert anthropic_calls == []


def test_search_tool_error_propagates_without_calling_llm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class ExplodingAnthropic:
        def __init__(self) -> None:
            raise AssertionError("LLM should not be called when search fails")

    class FailingSearchTool:
        def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
            raise SearchToolError("search timed out")

    monkeypatch.setattr(anthropic, "Anthropic", ExplodingAnthropic)

    with pytest.raises(SearchToolError, match="search timed out"):
        summarize("photosynthesis", search_tool=FailingSearchTool())


def test_happy_path_returns_summary_and_sends_structured_llm_request(
    monkeypatch: pytest.MonkeyPatch,
    stub_results: list[SearchResult],
    summary_payload: dict[str, Any],
) -> None:
    monkeypatch.delenv("SUMMARIZER_MODEL", raising=False)
    monkeypatch.delenv("SUMMARIZER_TEMPERATURE", raising=False)
    anthropic_calls = install_fake_anthropic(monkeypatch, summary_payload)

    result = summarize("photosynthesis", search_tool=StubSearchTool(stub_results))

    assert isinstance(result, SummaryResult)
    assert result.topic == "photosynthesis"
    assert result.key_findings == summary_payload["key_findings"]
    assert [citation.url for citation in result.citations] == [
        "https://example.com/photosynthesis-overview",
        "https://example.com/chlorophyll-basics",
    ]

    assert len(anthropic_calls) == 1
    request = anthropic_calls[0]
    assert request["model"] == "claude-haiku-4-5-20251001"
    assert request["temperature"] == 1.0
    assert request["max_tokens"] == 1024
    assert request["tool_choice"] == {"type": "tool", "name": "return_summary"}
    assert request["tools"][0]["name"] == "return_summary"

    user_message = request["messages"][0]["content"]
    assert "Topic: photosynthesis" in user_message
    assert "[1] Photosynthesis overview" in user_message
    assert "URL: https://example.com/photosynthesis-overview" in user_message
    assert "[2] Chlorophyll basics" in user_message
    assert "URL: https://example.com/chlorophyll-basics" in user_message
