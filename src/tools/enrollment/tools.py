"""
Enrollment tools — enroll/unenroll users, batch operations.

Status: Placeholder. Implement and register when ready.

NOTE: These tools perform WRITE operations. The MCP tool descriptions
should make this clear so the host agent can confirm with the user
before executing.
"""

import json


def register(mcp, get_client):
    """Mount enrollment tools onto the MCP server."""

    @mcp.tool()
    def lookup_user(email: str) -> str:
        """Look up a SkillJar user by email address.
        Returns user ID, name, and email if found."""
        client = get_client()
        users = client.search_users(email)
        if not users:
            return json.dumps({"found": False, "email": email})
        user = users[0]
        return json.dumps({
            "found": True,
            "id": user["id"],
            "email": user.get("email", ""),
            "first_name": user.get("first_name", ""),
            "last_name": user.get("last_name", ""),
        }, indent=2)

    @mcp.tool()
    def enroll_user(course_id: str, user_id: str) -> str:
        """Enroll a user in a course by course ID and user ID.

        ⚠️ This is a WRITE operation. Confirm with the user before executing.
        Use lookup_user to find the user_id first.
        """
        client = get_client()
        try:
            result = client.post(
                f"/courses/{course_id}/enrollments",
                payload={"user_id": user_id},
            )
            return json.dumps({"success": True, "enrollment": result}, indent=2)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    # Future tools:
    # - unenroll_user(course_id, user_id)
    # - batch_enroll(course_id, emails[])
    # - transfer_enrollment(from_course, to_course, user_id)
