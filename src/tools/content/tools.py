"""
Content management tools — create and update courses and lessons.

Status: Implemented (core CRUD). Extend as needed.

NOTE: ALL tools in this group perform WRITE operations against SkillJar.
Tool descriptions flag this so the host agent confirms with the user
before executing any mutations.
"""

import json
from pathlib import Path


def register(mcp, get_client):
    """Mount content management tools onto the MCP server."""

    @mcp.tool()
    def create_course(
        title: str,
        description: str = "",
        long_description_html: str = "",
        enforce_sequential_navigation: bool = False,
    ) -> str:
        """Create a new course in SkillJar.

        ⚠️ WRITE operation. Confirm with the user before executing.

        Args:
            title: Course title (e.g. "Introduction to API Mocking")
            description: Short description / summary (maps to API `short_description`)
            long_description_html: Optional full course description as HTML (`long_description_html`)
            enforce_sequential_navigation: When True, learners must complete lessons in order

        Returns the new course ID and metadata.
        """
        client = get_client()
        extra = {}
        if (long_description_html or "").strip():
            extra["long_description_html"] = long_description_html.strip()
        try:
            course = client.create_course(
                title=title,
                description=description,
                enforce_sequential_navigation=enforce_sequential_navigation,
                **extra,
            )
            return json.dumps({
                "success": True,
                "course_id": course["id"],
                "title": course.get("title", ""),
                "message": f"Course '{title}' created successfully.",
            }, indent=2)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    @mcp.tool()
    def update_course(
        course_id: str,
        title: str = "",
        description: str = "",
        long_description_html: str = "",
        enforce_sequential_navigation: bool | None = None,
    ) -> str:
        """Update an existing course's metadata in SkillJar.

        ⚠️ WRITE operation. Confirm with the user before executing.

        Args:
            course_id: The course to update
            title: New title (only sent if non-empty)
            description: New short description (only sent if non-empty; maps to `short_description`)
            long_description_html: New long description HTML (only sent if non-empty)
            enforce_sequential_navigation: Set sequential navigation on or off; omit by leaving default unset

        Provide at least one updatable field besides course_id. Empty strings are ignored (field left unchanged).
        """
        client = get_client()
        fields: dict = {}
        if (title or "").strip():
            fields["title"] = title.strip()
        if (description or "").strip():
            fields["description"] = description.strip()
        if (long_description_html or "").strip():
            fields["long_description_html"] = long_description_html.strip()
        if enforce_sequential_navigation is not None:
            fields["enforce_sequential_navigation"] = enforce_sequential_navigation
        if not fields:
            return json.dumps({
                "success": False,
                "error": "Nothing to update. Provide at least one of: title, description, long_description_html, or enforce_sequential_navigation.",
            })
        try:
            course = client.update_course(course_id, **fields)
            return json.dumps({
                "success": True,
                "course_id": course_id,
                "title": course.get("title", ""),
                "updated_fields": list(fields.keys()),
                "message": f"Course {course_id} updated.",
            }, indent=2)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    @mcp.tool()
    def create_lesson_from_html(
        course_id: str,
        title: str,
        html_content: str,
    ) -> str:
        """Create a new lesson in an existing course using HTML content.

        ⚠️ WRITE operation. Confirm with the user before executing.

        Args:
            course_id: The target course ID (from search_courses or get_course_catalog)
            title: Lesson title
            html_content: The full HTML body for the lesson

        The HTML is inserted as-is into the SkillJar lesson body.
        """
        client = get_client()
        try:
            lesson = client.create_lesson(
                course_id=course_id,
                title=title,
                body=html_content,
            )
            return json.dumps({
                "success": True,
                "course_id": course_id,
                "lesson_id": lesson["id"],
                "title": lesson.get("title", ""),
                "message": f"Lesson '{title}' created in course {course_id}.",
            }, indent=2)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    @mcp.tool()
    def create_lesson_from_file(
        course_id: str,
        title: str,
        file_path: str,
    ) -> str:
        """Create a new lesson from a local HTML file.

        ⚠️ WRITE operation. Confirm with the user before executing.

        Args:
            course_id: The target course ID
            title: Lesson title
            file_path: Absolute or relative path to an .html file on disk

        Reads the file contents and uploads as the lesson body.
        """
        client = get_client()
        path = Path(file_path).expanduser()
        if not path.exists():
            return json.dumps({"success": False, "error": f"File not found: {path}"})
        if not path.suffix.lower() in (".html", ".htm"):
            return json.dumps({"success": False, "error": f"Expected .html file, got: {path.suffix}"})

        html_content = path.read_text(encoding="utf-8")
        try:
            lesson = client.create_lesson(
                course_id=course_id,
                title=title,
                body=html_content,
            )
            return json.dumps({
                "success": True,
                "course_id": course_id,
                "lesson_id": lesson["id"],
                "title": lesson.get("title", ""),
                "file": str(path),
                "message": f"Lesson '{title}' created from {path.name}.",
            }, indent=2)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    @mcp.tool()
    def batch_create_lessons(
        course_id: str,
        lessons_json: str,
    ) -> str:
        """Create multiple lessons in a course from a JSON spec.

        ⚠️ WRITE operation. Confirm with the user before executing.

        Args:
            course_id: The target course ID
            lessons_json: JSON array of lesson objects, each with:
                - "title" (required): lesson title
                - "file_path" (optional): path to .html file
                - "html_content" (optional): inline HTML string
                Each lesson must have either file_path or html_content.

        Lessons are created in the order provided.

        Example lessons_json:
        [
            {"title": "Lesson 1: Intro", "file_path": "./lessons/01-intro.html"},
            {"title": "Lesson 2: Setup", "file_path": "./lessons/02-setup.html"},
            {"title": "Lesson 3: Summary", "html_content": "<h1>Summary</h1><p>Review.</p>"}
        ]
        """
        client = get_client()
        try:
            lessons = json.loads(lessons_json)
        except json.JSONDecodeError as e:
            return json.dumps({"success": False, "error": f"Invalid JSON: {e}"})

        results = []
        for i, spec in enumerate(lessons):
            title = spec.get("title", f"Lesson {i + 1}")
            html = ""

            if "file_path" in spec:
                path = Path(spec["file_path"]).expanduser()
                if not path.exists():
                    results.append({"title": title, "success": False, "error": f"File not found: {path}"})
                    continue
                html = path.read_text(encoding="utf-8")
            elif "html_content" in spec:
                html = spec["html_content"]
            else:
                results.append({"title": title, "success": False, "error": "Must provide file_path or html_content"})
                continue

            try:
                lesson = client.create_lesson(course_id=course_id, title=title, body=html)
                results.append({
                    "title": title,
                    "success": True,
                    "lesson_id": lesson["id"],
                })
            except Exception as e:
                results.append({"title": title, "success": False, "error": str(e)})

        succeeded = sum(1 for r in results if r["success"])
        return json.dumps({
            "course_id": course_id,
            "total": len(results),
            "succeeded": succeeded,
            "failed": len(results) - succeeded,
            "results": results,
        }, indent=2)

    @mcp.tool()
    def update_lesson_content(
        course_id: str,
        lesson_id: str,
        html_content: str = "",
        file_path: str = "",
        title: str = "",
    ) -> str:
        """Update an existing lesson's content and/or title.

        ⚠️ WRITE operation. Confirm with the user before executing.

        Args:
            course_id: The course containing the lesson
            lesson_id: The lesson to update (from get_course_content results)
            html_content: New HTML body (optional, provide this OR file_path)
            file_path: Path to .html file with new content (optional)
            title: New title (optional, only updates if provided)

        Provide either html_content or file_path for the body. If both
        are empty, only the title is updated.
        """
        client = get_client()
        fields = {}

        if title:
            fields["title"] = title

        if file_path:
            path = Path(file_path).expanduser()
            if not path.exists():
                return json.dumps({"success": False, "error": f"File not found: {path}"})
            fields["content_html"] = path.read_text(encoding="utf-8")
        elif html_content:
            fields["content_html"] = html_content

        if not fields:
            return json.dumps({"success": False, "error": "Nothing to update. Provide title, html_content, or file_path."})

        try:
            result = client.update_lesson(course_id, lesson_id, **fields)
            return json.dumps({
                "success": True,
                "course_id": course_id,
                "lesson_id": lesson_id,
                "updated_fields": list(fields.keys()),
                "message": f"Lesson {lesson_id} updated.",
            }, indent=2)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    # Future tools:
    # - delete_lesson(course_id, lesson_id) — ⚠️ DESTRUCTIVE
    # - reorder_lessons(course_id, lesson_ids[]) — set lesson sequence
    # - duplicate_course(course_id, new_title) — clone a course
    # - publish_course(course_id) / unpublish_course(course_id)