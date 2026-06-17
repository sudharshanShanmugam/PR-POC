"""
Shared Pydantic models for the G4 AI Impact Agent.
"""

from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel


class ChangedFile(BaseModel):
    filename: str
    status: Literal["added", "modified", "removed", "renamed"]
    additions: int = 0
    deletions: int = 0
    patch: Optional[str] = None


class PRDetails(BaseModel):
    number: int
    title: str
    author: str
    base_branch: str
    head_branch: str
    repo: str
    owner: str
    body: Optional[str] = None


class ImpactReport(BaseModel):
    pr_number: int
    repo: str
    affected_components: list[str]
    potentially_impacted_components: list[str] = []
    change_type: str
    risk: Literal["Low", "Medium", "High"]
    confidence: int = 0
    risk_reasons: list[str] = []
    testing_scope: list[str] = []
    summary: str
    changed_files: list[str]
    retrieved_context: list[str] = []
