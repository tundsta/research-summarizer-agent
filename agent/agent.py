"""Orchestration logic for the Research Summarizer Agent.

The pipeline is intentionally short — five steps, simple enough to diagram
on a single slide. Anything more complex has drifted outside the workshop's
scope.
"""

from __future__ import annotations

import os

import anthropic
from dotenv import load_dotenv

from agent.models import SummaryResult, summary_result_tool_schema
from agent.prompts import SYSTEM_PROMPT, build_user_message
from agent.tools import (
    NoResultsError,
    SearchTool,
    StubSearchTool,
    TavilySearchTool,
)


load_dotenv()

_DEFAULT_MODEL = "claude-haiku-4-5-20251001"
_TOOL_NAME = "return_summary"
_MAX_TOKENS = 1024


def summarize(topic: str, search_tool: SearchTool | None = None) -> SummaryResult:
    """Summarize ``topic`` using web search and an LLM.

    Raises:
        ValueError: ``topic`` is empty or whitespace-only.
        NoResultsError: the search tool returned an empty list.
        SearchToolError: the search tool failed.
        anthropic.APIError: the Anthropic API returned an error.
    """
    topic = topic.strip()
    if not topic:
        raise ValueError("topic must be non-empty")

    if search_tool is None:
        search_tool = _default_search_tool()

    results = search_tool.search(topic, max_results=5)
    if not results:
        raise NoResultsError("no search results found")

    user_message = build_user_message(topic, results)

    model = os.environ.get("SUMMARIZER_MODEL", _DEFAULT_MODEL)
    temperature = float(os.environ.get("SUMMARIZER_TEMPERATURE", "1.0"))

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=model,
        max_tokens=_MAX_TOKENS,
        temperature=temperature,
        system=SYSTEM_PROMPT,
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
        ],
        tool_choice={"type": "tool", "name": _TOOL_NAME},
        messages=[{"role": "user", "content": user_message}],
    )

    for block in response.content:
        if getattr(block, "type", None) == "tool_use" and block.name == _TOOL_NAME:
            return SummaryResult.model_validate(block.input)
    raise RuntimeError(
        f"Anthropic response did not include a {_TOOL_NAME} tool_use block"
    )


def _default_search_tool() -> SearchTool:
    if os.environ.get("TAVILY_API_KEY"):
        return TavilySearchTool()
    return StubSearchTool(results=[])
