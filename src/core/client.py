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
        return self.get_all_pages(f"/courses/{course_id}/lessons")

    def get_lesson(self, course_id: str, lesson_id: str) -> dict:
        return self.get(f"/courses/{course_id}/lessons/{lesson_id}")

    def get_full_course_content(self, course_id: str) -> dict:
        """Course metadata + all lesson bodies in one call."""
        course = self.get_course(course_id)
        lessons_summary = self.list_lessons(course_id)
        course["lessons"] = [
            self.get_lesson(course_id, l["id"]) for l in lessons_summary
        ]
        return course

    # ── User / Enrollment reads (for future tools) ───────────

    def list_enrollments(self, course_id: str) -> list[dict]:
        return self.get_all_pages(f"/courses/{course_id}/enrollments")

    def get_user(self, user_id: str) -> dict:
        return self.get(f"/users/{user_id}")

    def search_users(self, email: str) -> list[dict]:
        return self.get_all_pages("/users", params={"email": email})

    # ── Cache management ─────────────────────────────────────

    def clear_cache(self):
        self.cache.clear()
