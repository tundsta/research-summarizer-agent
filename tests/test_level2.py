"""Level 2 constrained model tests for the research summarizer agent.

These tests make real Anthropic calls, so run them intentionally with:

    pytest tests/test_level2.py

Search results are controlled fixtures. That keeps this tier focused on prompt
behavior, structured tool output, and citation provenance rather than Tavily
network variability.
"""

from __future__ import annotations

import os

import pytest
from dotenv import load_dotenv

from agent import SearchResult, StubSearchTool, SummaryResult, summarize


load_dotenv()

# Level 2 tests should be stable enough to automate: use an exact model pin so
# behavior does not silently change, and temperature 0 to minimize randomness.
TEST_MODEL = "claude-haiku-4-5-20251001"
TEST_TEMPERATURE = 0

pytestmark = pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="Level 2 tests require ANTHROPIC_API_KEY for real Anthropic calls",
)


@pytest.fixture(autouse=True)
def constrained_model_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SUMMARIZER_MODEL", TEST_MODEL)
    monkeypatch.setenv("SUMMARIZER_TEMPERATURE", str(TEST_TEMPERATURE))


def test_photosynthesis_summary_meets_level2_contract() -> None:
    search_results = [
        SearchResult(
            title="Photosynthesis | Definition, Formula, Process",
            url="https://www.britannica.com/science/photosynthesis",
            snippet=(
                "Photosynthesis is the process by which green plants and certain "
                "organisms transform light energy into chemical energy."
            ),
        ),
        SearchResult(
            title="Intro to photosynthesis",
            url="https://www.khanacademy.org/science/biology/photosynthesis-in-plants/introduction-to-stages-of-photosynthesis/a/intro-to-photosynthesis",
            snippet=(
                "During photosynthesis, plants use light energy to convert carbon "
                "dioxide and water into sugars and oxygen."
            ),
        ),
        SearchResult(
            title="Photosynthesis",
            url="https://education.nationalgeographic.org/resource/photosynthesis/",
            snippet=(
                "Chlorophyll in plant cells absorbs sunlight and helps power the "
                "reactions that make glucose."
            ),
        ),
    ]

    result = summarize(
        "photosynthesis",
        search_tool=StubSearchTool(search_results),
    )

    assert_level2_summary_contract(result, "photosynthesis", search_results)

    combined_text = " ".join([result.synopsis, *result.key_findings]).lower()
    assert "light" in combined_text
    assert any(term in combined_text for term in ["sugar", "glucose"])
    assert any(term in combined_text for term in ["carbon dioxide", "co2"])


def test_urban_heat_island_summary_cites_only_provided_urls() -> None:
    search_results = [
        SearchResult(
            title="Heat Island Effect",
            url="https://www.epa.gov/heatislands",
            snippet=(
                "Heat islands are urbanized areas that experience higher temperatures "
                "than nearby outlying areas. Buildings, roads, and other infrastructure "
                "absorb and re-emit the sun's heat."
            ),
        ),
        SearchResult(
            title="Urban Heat Islands",
            url="https://climatekids.nasa.gov/heat-islands/",
            snippet=(
                "Urban areas can be hotter than nearby rural areas because surfaces "
                "such as pavement and rooftops absorb more heat and there are fewer trees."
            ),
        ),
        SearchResult(
            title="Reduce Urban Heat Island Effects",
            url="https://www.energy.gov/eere/buildings/articles/reduce-urban-heat-island-effects-cool-roofs",
            snippet=(
                "Cool roofs and reflective surfaces can reduce heat absorption and help "
                "lower building cooling demand in cities."
            ),
        ),
    ]

    result = summarize(
        "urban heat islands",
        search_tool=StubSearchTool(search_results),
    )

    assert_level2_summary_contract(result, "urban heat islands", search_results)


def assert_level2_summary_contract(
    result: SummaryResult,
    topic: str,
    search_results: list[SearchResult],
) -> None:
    allowed_urls = {search_result.url for search_result in search_results}
    citation_urls = {citation.url for citation in result.citations}

    assert isinstance(result, SummaryResult)
    assert result.topic.strip().lower() == topic.lower()
    assert result.synopsis.strip()
    assert 2 <= len(result.key_findings) <= 5
    assert all(finding.strip() for finding in result.key_findings)
    assert len(result.citations) >= len(result.key_findings)
    assert citation_urls
    assert citation_urls <= allowed_urls
    assert all(citation.title.strip() for citation in result.citations)
    assert all(citation.snippet.strip() for citation in result.citations)
