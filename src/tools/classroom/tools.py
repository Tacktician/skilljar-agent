"""
Classroom tools — ILT support, sandbox access, password resets.

Status: Placeholder. Implement and register when ready.

NOTE: These tools perform WRITE and potentially SENSITIVE operations
(password resets, sandbox provisioning). Tool descriptions must clearly
flag this so the host agent confirms with the instructor before executing.

Intended users: ILT facilitators running live workshops in SkillJar.
"""

import json


def register(mcp, get_client):
    """Mount classroom support tools onto the MCP server."""

    @mcp.tool()
    def check_user_access(email: str, course_id: str) -> str:
        """Check whether a user has access to a specific course.
        Useful when a learner reports they can't get into their course.

        Returns enrollment status, completion state, and last activity.
        """
        client = get_client()
        users = client.search_users(email)
        if not users:
            return json.dumps({
                "found": False,
                "email": email,
                "suggestion": "User not found. They may need to create a SkillJar account first.",
            })

        user = users[0]
        enrollments = client.list_enrollments(course_id)
        user_enrollment = next(
            (e for e in enrollments if e.get("user_id") == user["id"]),
            None,
        )

        if not user_enrollment:
            return json.dumps({
                "found": True,
                "enrolled": False,
                "user_id": user["id"],
                "email": email,
                "suggestion": "User exists but is not enrolled in this course. Enroll them using the enrollment tools.",
            })

        return json.dumps({
            "found": True,
            "enrolled": True,
            "user_id": user["id"],
            "email": email,
            "status": "completed" if user_enrollment.get("completed_at") else "in_progress",
            "started_at": user_enrollment.get("created_at", ""),
            "completed_at": user_enrollment.get("completed_at", ""),
        }, indent=2)

    # Future tools:
    # - reset_user_password(email) — ⚠️ WRITE. Trigger SkillJar password reset email
    # - provision_sandbox(user_id, sandbox_type) — ⚠️ WRITE. Spin up lab environment
    # - get_live_session_roster(course_id, session_date) — attendance for ILT session
    # - bulk_check_access(emails[], course_id) — batch version of check_user_access
