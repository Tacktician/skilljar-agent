"""Extract readable content from SkillJar lesson HTML bodies."""

import re
from dataclasses import dataclass, field
from html.parser import HTMLParser


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


class _HTMLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text_parts = []
        self.headings = []
        self.code_blocks = []
        self._in_code = False
        self._in_heading = False
        self._current_buf = []

    def handle_starttag(self, tag, attrs):
        if tag in ("code", "pre"):
            self._in_code = True
            self._current_buf = []
        elif tag in ("h1", "h2", "h3", "h4"):
            self._in_heading = True
            self._current_buf = []

    def handle_endtag(self, tag):
        if tag in ("code", "pre") and self._in_code:
            self._in_code = False
            self.code_blocks.append("".join(self._current_buf))
        elif tag in ("h1", "h2", "h3", "h4") and self._in_heading:
            self._in_heading = False
            self.headings.append("".join(self._current_buf).strip())

    def handle_data(self, data):
        if self._in_code or self._in_heading:
            self._current_buf.append(data)
        self.text_parts.append(data)


def extract_lesson_content(lesson: dict) -> LessonContent:
    html = lesson.get("body", "") or ""
    stripper = _HTMLStripper()
    stripper.feed(html)
    plain = re.sub(r"\s+", " ", " ".join(stripper.text_parts)).strip()
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
