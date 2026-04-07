"""Fuzzy-match natural language queries against SkillJar course titles."""

from difflib import SequenceMatcher
from core.client import SkillJarClient


def resolve_courses(
    query: str,
    client: SkillJarClient,
    threshold: float = 0.4,
    max_results: int = 5,
) -> list[dict]:
    """
    Given a free-text query, return the best-matching courses
    sorted by relevance. Each result includes a `match_score` field.
    """
    courses = client.list_courses()
    query_lower = query.lower()

    scored = []
    for course in courses:
        title = course.get("title", "")
        ratio = SequenceMatcher(None, query_lower, title.lower()).ratio()
        substring_bonus = 0.2 if query_lower in title.lower() else 0.0
        score = min(ratio + substring_bonus, 1.0)
        if score >= threshold:
            scored.append({**course, "match_score": round(score, 3)})

    scored.sort(key=lambda c: c["match_score"], reverse=True)
    return scored[:max_results]
