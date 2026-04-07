"""
Shared output models used across tool groups.

Domain-specific models (e.g. CurriculumPlan) live in their
respective tool modules. This file holds models that are
reused across multiple domains.
"""

from pydantic import BaseModel


class CourseInfo(BaseModel):
    """Lightweight course reference returned by search/catalog tools."""
    id: str
    title: str
    description: str = ""
    match_score: float | None = None


class UserInfo(BaseModel):
    """Basic user info for enrollment and classroom tools."""
    id: str
    email: str
    first_name: str = ""
    last_name: str = ""


class ToolResult(BaseModel):
    """Standard wrapper for tool responses that need status + data."""
    success: bool
    message: str
    data: dict | list | None = None
