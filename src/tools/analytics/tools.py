"""
Analytics tools — enrollment stats, completion rates, lesson performance.

Status: Placeholder. Implement and register when ready.
"""

import json


def register(mcp, get_client):
    """Mount analytics tools onto the MCP server."""

    @mcp.tool()
    def get_enrollment_stats(course_id: str) -> str:
        """Get enrollment count and completion rate for a course.

        Returns total enrolled, completed, in-progress, and completion
        percentage. Use a course_id from search_courses or get_course_catalog.
        """
        client = get_client()
        enrollments = client.list_enrollments(course_id)
        total = len(enrollments)
        completed = sum(1 for e in enrollments if e.get("completed_at"))
        in_progress = total - completed
        rate = round((completed / total) * 100, 1) if total > 0 else 0.0
        result = {
            "course_id": course_id,
            "total_enrolled": total,
            "completed": completed,
            "in_progress": in_progress,
            "completion_rate_pct": rate,
        }
        return json.dumps(result, indent=2)

    # Future tools:
    # - get_lesson_performance(course_id) — time-on-page, drop-off points
    # - get_assessment_results(course_id) — quiz pass/fail rates
    # - get_path_progress(path_id) — multi-course learning path completion
