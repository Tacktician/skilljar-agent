"""
SkillJar REST API client.

Shared across all tool groups. Handles authentication, pagination, and
caching. All domain-specific logic lives in the tool modules — this
client provides only generic CRUD against the SkillJar API.

Auth: HTTP Basic Auth — API key as username, empty password.
Docs: https://api.skilljar.com/docs/
"""

import os
from base64 import b64encode
from pathlib import Path
from typing import Optional

import httpx

from core.cache import FileCache


def _aggregate_lesson_content_items(items: list[dict]) -> str:
    """Join HTML from lesson content items in display order."""
    if not items:
        return ""
    sorted_items = sorted(items, key=lambda x: x.get("order", 0))
    parts = []
    for item in sorted_items:
        header = (item.get("header") or "").strip()
        chunk = (item.get("content_html") or "").strip()
        if header and chunk:
            parts.append(f"<h2>{header}</h2>\n{chunk}")
        elif header:
            parts.append(f"<h2>{header}</h2>")
        elif chunk:
            parts.append(chunk)
    return "\n\n".join(parts)


def _lesson_primary_html(lesson: dict) -> str:
    """Prefer API field names; fall back to legacy `body`."""
    parts = []
    for key in ("content_html", "body", "description_html"):
        v = (lesson.get(key) or "").strip()
        if v:
            parts.append(v)
    return "\n\n".join(parts)


def _normalize_lesson_type(lesson_type: str) -> str:
    u = lesson_type.strip().upper()
    allowed = ("ASSET", "HTML", "WEB_PACKAGE", "QUIZ", "VILT", "MODULAR", "SECTION")
    if u in allowed:
        return u
    if lesson_type.lower() == "html":
        return "HTML"
    return "HTML"


class SkillJarClient:
    """Authenticated wrapper around the SkillJar REST API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        domain: Optional[str] = None,
        cache: Optional[FileCache] = None,
    ):
        self.api_key = api_key or os.environ["SKILLJAR_API_KEY"]
        self.domain = domain or os.environ.get("SKILLJAR_DOMAIN", "api.skilljar.com")
        self.base_url = f"https://{self.domain}/v1"

        token = b64encode(f"{self.api_key}:".encode()).decode()
        self.headers = {
            "Authorization": f"Basic {token}",
            "Accept": "application/json",
        }

        self.cache = cache or FileCache()

    # ── HTTP helpers ─────────────────────────────────────────

    def get(self, path: str, params: dict = None) -> dict:
        """Authenticated GET request."""
        url = f"{self.base_url}{path}"
        resp = httpx.get(url, headers=self.headers, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def post(self, path: str, payload: dict = None) -> dict:
        """Authenticated POST request."""
        url = f"{self.base_url}{path}"
        resp = httpx.post(url, headers=self.headers, json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def put(self, path: str, payload: dict = None) -> dict:
        """Authenticated PUT request."""
        url = f"{self.base_url}{path}"
        resp = httpx.put(url, headers=self.headers, json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def delete(self, path: str) -> int:
        """Authenticated DELETE request. Returns status code."""
        url = f"{self.base_url}{path}"
        resp = httpx.delete(url, headers=self.headers, timeout=30)
        resp.raise_for_status()
        return resp.status_code

    def get_all_pages(self, path: str, params: dict = None) -> list:
        """Fetch all pages of a paginated endpoint."""
        params = params or {}
        results = []
        page = 1
        while True:
            params["page"] = page
            data = self.get(path, params)
            results.extend(data.get("results", []))
            if not data.get("next"):
                break
            page += 1
        return results

    # ── Cached catalog endpoints ─────────────────────────────

    def list_courses(self, bypass_cache: bool = False) -> list[dict]:
        """All published courses. Cached."""
        cache_key = "courses"
        if not bypass_cache:
            cached = self.cache.get(cache_key)
            if cached is not None:
                return cached
        results = self.get_all_pages("/courses")
        self.cache.set(cache_key, results)
        return results

    def list_paths(self, bypass_cache: bool = False) -> list[dict]:
        """All published learning paths. Cached."""
        cache_key = "paths"
        if not bypass_cache:
            cached = self.cache.get(cache_key)
            if cached is not None:
                return cached
        results = self.get_all_pages("/paths")
        self.cache.set(cache_key, results)
        return results

    # ── Course / Lesson reads ────────────────────────────────

    def get_course(self, course_id: str) -> dict:
        return self.get(f"/courses/{course_id}")

    def list_lessons(self, course_id: str) -> list[dict]:
        return self.get_all_pages("/lessons", params={"course_id": course_id})

    def get_lesson(self, course_id: str, lesson_id: str) -> dict:
        return self.get(f"/lessons/{lesson_id}", params={"course_id": course_id})

    def list_lesson_content_items(self, lesson_id: str) -> list[dict]:
        return self.get_all_pages(f"/lessons/{lesson_id}/content-items")

    def _next_lesson_order(self, course_id: str) -> int:
        lessons = self.list_lessons(course_id)
        if not lessons:
            return 0
        return max(l.get("order", 0) for l in lessons) + 1

    def _attach_scraping_html(self, lesson: dict) -> None:
        """Set `scraping_html` for curriculum scraping (HTML + modular blocks)."""
        base = _lesson_primary_html(lesson)
        ltype = (lesson.get("type") or "").upper()
        extra = ""
        if not base or ltype in ("MODULAR", "SECTION", "WEB_PACKAGE"):
            items = self.list_lesson_content_items(lesson["id"])
            extra = _aggregate_lesson_content_items(items).strip()
        if base and extra:
            lesson["scraping_html"] = f"{base}\n\n{extra}"
        elif extra:
            lesson["scraping_html"] = extra
        else:
            lesson["scraping_html"] = base

    def get_full_course_content(self, course_id: str) -> dict:
        """Course metadata + all lesson bodies in one call."""
        course = self.get_course(course_id)
        lessons_summary = self.list_lessons(course_id)
        lessons = []
        for row in lessons_summary:
            lesson = self.get_lesson(course_id, row["id"])
            self._attach_scraping_html(lesson)
            lessons.append(lesson)
        course["lessons"] = lessons
        return course

    # ── User / Enrollment reads (for future tools) ───────────

    def list_enrollments(self, course_id: str) -> list[dict]:
        return self.get_all_pages(f"/courses/{course_id}/enrollments")

    def get_user(self, user_id: str) -> dict:
        return self.get(f"/users/{user_id}")

    def search_users(self, email: str) -> list[dict]:
        return self.get_all_pages("/users", params={"email": email})

    # ── Course / Lesson writes ───────────────────────────────

    def create_course(self, title: str, description: str = "", **kwargs) -> dict:
        """Create a new course. Returns the created course object with ID."""
        short = description.strip() if description else ""
        if not short:
            short = " "
        payload = {
            "title": title,
            "short_description": short,
            "enforce_sequential_navigation": kwargs.pop(
                "enforce_sequential_navigation", False
            ),
            **kwargs,
        }
        result = self.post("/courses", payload)
        self.cache.clear()  # Invalidate course catalog cache
        return result

    def update_course(self, course_id: str, **fields) -> dict:
        """Update course metadata (title, short_description, etc.)."""
        fields = dict(fields)
        if "description" in fields and "short_description" not in fields:
            fields["short_description"] = fields.pop("description")
        result = self.put(f"/courses/{course_id}", fields)
        self.cache.clear()
        return result

    def create_lesson(
        self,
        course_id: str,
        title: str,
        body: str = "",
        lesson_type: str = "html",
        **kwargs,
    ) -> dict:
        """Create a new lesson in a course. `body` is mapped to `content_html`."""
        order = kwargs.pop("order", None)
        if order is None:
            order = self._next_lesson_order(course_id)
        payload = {
            "course_id": course_id,
            "title": title,
            "content_html": body,
            "type": _normalize_lesson_type(lesson_type),
            "order": order,
            **kwargs,
        }
        return self.post("/lessons", payload)

    def update_lesson(self, course_id: str, lesson_id: str, **fields) -> dict:
        """Update a lesson. Maps legacy `body` to `content_html`."""
        mapped = dict(fields)
        if "body" in mapped:
            if "content_html" not in mapped:
                mapped["content_html"] = mapped.pop("body")
            else:
                mapped.pop("body", None)
        mapped.pop("course_id", None)
        return self.put(f"/lessons/{lesson_id}", mapped)

    def reorder_lessons(self, course_id: str, lesson_ids: list[str]) -> dict:
        """Set lesson order for a course by providing ordered lesson IDs.

        Not present in the published OpenAPI bundle; uses the legacy path.
        """
        return self.put(f"/courses/{course_id}/lessons/order", {"lesson_ids": lesson_ids})

    # ── Cache management ─────────────────────────────────────

    def clear_cache(self):
        self.cache.clear()