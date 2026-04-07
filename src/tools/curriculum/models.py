"""Output models for curriculum planning."""

from pydantic import BaseModel


class LearningObjective(BaseModel):
    description: str
    bloom_level: str  # Remember, Understand, Apply, Analyze, Evaluate, Create


class LessonOutline(BaseModel):
    title: str
    objective: str
    key_topics: list[str]
    estimated_minutes: int
    content_type: str  # conceptual, hands-on, assessment, recap


class ResearchTodo(BaseModel):
    topic: str
    reason: str
    priority: str  # high, medium, low


class CurriculumPlan(BaseModel):
    plan_type: str  # refresh, extend, new_course
    course_title: str
    summary: str
    target_audience: str
    prerequisites: list[str]
    learning_objectives: list[LearningObjective]
    lesson_outlines: list[LessonOutline]
    research_todos: list[ResearchTodo]
    notes: str = ""
