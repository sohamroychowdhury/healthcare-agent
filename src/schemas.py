"""Structured data the agent passes around.

Using Pydantic gives us free validation and clean parsing of the LLM's
JSON output at every step of the ReAct loop.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Action(str, Enum):
    SEARCH = "search_medical_database"
    FINAL_ANSWER = "final_answer"


class AgentStep(BaseModel):
    """One decision from the LLM: think, then either search or answer."""

    thought: str = Field(..., description="Reasoning about what to do next.")
    action: Action
    action_input: Optional[str] = Field(
        None, description="Search query when action is search_medical_database."
    )
    answer: Optional[str] = Field(
        None, description="Final response when action is final_answer."
    )
    sources: List[str] = Field(
        default_factory=list, description="Source URLs backing the answer."
    )


class SearchResult(BaseModel):
    title: str
    snippet: str
    url: str


class AgentResult(BaseModel):
    """What the agent returns to the caller / UI after a full run."""

    query: str
    answer: str
    sources: List[str] = Field(default_factory=list)
    steps_taken: int = 0
    used_fallback: bool = False
    trace: List[Dict[str, Any]] = Field(default_factory=list)
