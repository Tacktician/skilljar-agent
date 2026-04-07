"""Extract readable content from SkillJar lesson HTML bodies."""

import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from urllib.parse import urlparse


@dataclass
class LessonContent:
    lesson_id: str
    title: str
    headings: list[str] = field(default_factory=list)
    code_blocks: list[str] = field(default_factory=list)
    plain_text: str = ""

    def summary(self, max_chars: int = 2000) -> str:
        parts = [f"## {self.title}"]
        if self.headings:
            parts.append("Headings: " + " → ".join(self.headings))
        if self.code_blocks:
            parts.append(f"Code blocks: {len(self.code_blocks)}")
        parts.append(self.plain_text[:max_chars])
        return "\n".join(parts)


def _html_attr(attrs: list[tuple[str, str | None]], name: str) -> str:
    n = name.lower()
    for k, v in attrs:
        if k and k.lower() == n and v:
            return str(v).strip()
    return ""


def _host_from_src(src: str) -> str:
    if not src or not src.strip():
        return ""
    try:
        return (urlparse(src).netloc or "").lower()
    except ValueError:
        return ""


def _is_arcade_embed_src(src: str) -> bool:
    return "arcade.software" in _host_from_src(src)


def _embed_hint_from_src(src: str) -> str:
    if not src or not src.strip():
        return ""
    host = _host_from_src(src)
    if _is_arcade_embed_src(src):
        return f"Embedded Arcade: {src.strip()}"
    if host:
        return f"Embedded media ({host})"
    return ""


def _iframe_embed_hint(title: str, src: str) -> str:
    """Human-readable line for MCP previews (Arcade iframes get a distinct label + URL)."""
    title = (title or "").strip()
    src = (src or "").strip()
    if _is_arcade_embed_src(src):
        if title and src:
            return f"Embedded Arcade: {title} — {src}"
        if title:
            return f"Embedded Arcade: {title}"
        if src:
            return f"Embedded Arcade: {src}"
        return ""
    if title:
        return f"Embedded: {title}"
    return _embed_hint_from_src(src)


class _HTMLStripper(HTMLParser):
    """Pulls readable text + embed hints; ignores inline CSS/JS (new SkillJar lesson templates)."""

    # Skip only non-visible-to-scraper payloads. Do NOT skip <noscript>: SkillJar (and
    # many LMS templates) put real static lesson HTML there as a JS-disabled fallback;
    # skipping it would drop the entire body from content_preview.
    _SKIP_CONTAINER_TAGS = frozenset({"style", "script"})

    def __init__(self):
        super().__init__()
        # Text and embed hints in document order (multiple content-items / iframes stay interleaved).
        self._segments: list[str] = []
        self.headings = []
        self.code_blocks = []
        self._in_code = False
        self._in_heading = False
        self._current_buf = []
        self._skip_data_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in self._SKIP_CONTAINER_TAGS:
            self._skip_data_depth += 1
            return
        if self._skip_data_depth > 0:
            return
        if tag in ("code", "pre"):
            self._in_code = True
            self._current_buf = []
        elif tag in ("h1", "h2", "h3", "h4"):
            self._in_heading = True
            self._current_buf = []
        elif tag in ("iframe", "video", "embed", "object"):
            title = _html_attr(attrs, "title")
            src = _html_attr(attrs, "src")
            hint = _iframe_embed_hint(title, src)
            if hint:
                self._segments.append(hint)

    def handle_endtag(self, tag):
        if tag in self._SKIP_CONTAINER_TAGS:
            if self._skip_data_depth > 0:
                self._skip_data_depth -= 1
            return
        if self._skip_data_depth > 0:
            return
        if tag in ("code", "pre") and self._in_code:
            self._in_code = False
            self.code_blocks.append("".join(self._current_buf))
        elif tag in ("h1", "h2", "h3", "h4") and self._in_heading:
            self._in_heading = False
            self.headings.append("".join(self._current_buf).strip())

    def handle_data(self, data):
        if self._skip_data_depth > 0:
            return
        if self._in_code or self._in_heading:
            self._current_buf.append(data)
        self._segments.append(data)


def extract_lesson_content(lesson: dict) -> LessonContent:
    html = (
        lesson.get("scraping_html")
        or lesson.get("content_html")
        or lesson.get("body")
        or ""
    ) or ""
    stripper = _HTMLStripper()
    stripper.feed(html)
    plain = re.sub(r"\s+", " ", " ".join(stripper._segments)).strip()
    return LessonContent(
        lesson_id=lesson.get("id", ""),
        title=lesson.get("title", "Untitled"),
        headings=stripper.headings,
        code_blocks=stripper.code_blocks,
        plain_text=plain,
    )


def scrape_course(course_with_lessons: dict) -> list[LessonContent]:
    return [
        extract_lesson_content(lesson)
        for lesson in course_with_lessons.get("lessons", [])
    ]
