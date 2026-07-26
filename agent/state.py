"""Shared state/types for the LangGraph pipeline."""

from __future__ import annotations

from typing import Any, Optional, TypedDict

from pydantic import BaseModel, Field


class GraphState(TypedDict, total=False):
    # Input
    country_code: Optional[str]
    depot_id: Optional[str]

    # Set by the retriever node
    retrieved: dict[str, Any]

    # Set by the analyst node
    analysis: str

    # Set by the briefing node (final output)
    briefing: "Briefing"


class Briefing(BaseModel):
    """Structured SITREP output - the only agent output shown to the user."""

    situation: str = Field(description="What the retrieved data shows, factually.")
    assessment: str = Field(
        description=(
            "What it means: cross-system correlations, risk implications, "
            "explicitly caveated by known model/data limitations."
        )
    )
    recommendation: str = Field(
        description="A concrete, plain-English next action given the situation and assessment."
    )
    sources: list[str] = Field(
        default_factory=list,
        description="Which tables/files the briefing draws on, for traceability.",
    )
    no_data_warning: Optional[str] = Field(
        default=None,
        description=(
            "Set if the country_code/depot_id had no data in one or more "
            "sources, so the caller knows the briefing is partial."
        ),
    )
