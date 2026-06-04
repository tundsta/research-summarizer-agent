"""Data models for the Research Summarizer Agent.

The spec leaves the model library choice open; this build uses Pydantic v2 so
that ``model_json_schema()`` can produce the tool schema for Anthropic's
structured-output endpoint without manual JSON wrestling.

No field validators or constraints are declared here. All bounds (synopsis
sentence count, findings count, citation URL provenance) are enforced by the
prompt only, per the spec.
"""

from __future__ import annotations

from typing import Any

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


def summary_result_tool_schema() -> dict[str, Any]:
    """Return the JSON schema for SummaryResult shaped for Anthropic tool use.

    Anthropic's tool-use endpoint accepts a JSON Schema with ``$defs``, which is
    what Pydantic v2 emits for nested models. The models forbid extra keys so the
    emitted schema includes ``additionalProperties: false`` for strict tool use.
    """
    return SummaryResult.model_json_schema()
