"""
Curriculum planning tools — registered onto the shared MCP server.

Tools:
  - search_courses: fuzzy title match
  - get_course_content: scrape lesson content
  - get_course_catalog: full course listing (cached)
"""

import json
from core.client import SkillJarClient
from tools.curriculum.resolver import resolve_courses
from tools.curriculum.scraper import scrape_course


def _course_description_text(course: dict) -> str:
    parts = []
    if course.get("short_description"):
        parts.append(course["short_description"])
    if course.get("long_description_html"):
        parts.append(course["long_description_html"])
    if course.get("description"):
        parts.append(course["description"])
    return "\n\n".join(p for p in parts if p)


def register(mcp, get_client):
    """
    Mount curriculum tools onto an MCP server instance.

    Args:
        mcp: FastMCP server instance
        get_client: callable that returns a shared SkillJarClient
    """

    @mcp.tool()
    def search_courses(query: str, max_results: int = 5) -> str:
        """Search for SkillJar courses by title (fuzzy match).
        Returns matching course titles, IDs, and match scores."""
        client = get_client()
        matches = resolve_courses(query, client, max_results=max_results)
        results = [
            {"id": m["id"], "title": m["title"], "score": m["match_score"]}
            for m in matches
        ]
        return json.dumps(results, indent=2)

    @mcp.tool()
    def get_course_content(course_id: str) -> str:
        """Fetch and return the full scraped content for a course.

        Returns structured lesson data including: titles, heading outlines,
        code block counts, and plain text summaries for each lesson.
        Use a course_id from search_courses results.

        The host agent should use this content to reason about curriculum
        plans — refreshes, extensions, or new course proposals.
        """
        client = get_client()
        full_course = client.get_full_course_content(course_id)
        lessons = scrape_course(full_course)
        result = {
            "course_id": course_id,
            "course_title": full_course.get("title", ""),
            "course_description": _course_description_text(full_course),
            "lesson_count": len(lessons),
            "lessons": [
                {
                    "lesson_id": l.lesson_id,
                    "title": l.title,
                    "headings": l.headings,
                    "code_block_count": len(l.code_blocks),
                    "content_preview": l.plain_text[:3000],
                }
                for l in lessons
            ],
        }
        return json.dumps(result, indent=2)

    @mcp.tool()
    def get_course_catalog() -> str:
        """Return the full SkillJar course catalog (title and ID for every
        published course). Results are cached locally."""
        client = get_client()
        courses = client.list_courses()
        catalog = [
            {"id": c["id"], "title": c.get("title", "")}
            for c in courses
        ]
        return json.dumps(catalog, indent=2)
