"""Tests for lesson scraping_html merge (content-items + top-level HTML)."""

import os

import pytest

from core.client import (
    SkillJarClient,
    _aggregate_lesson_content_items,
    _extra_redundant_with_base,
)


@pytest.fixture
def api_key(monkeypatch):
    monkeypatch.setenv("SKILLJAR_API_KEY", "test-key-for-unit-tests")
    yield
    monkeypatch.delenv("SKILLJAR_API_KEY", raising=False)


def test_aggregate_quiz_placeholder_includes_header_and_id():
    html = _aggregate_lesson_content_items(
        [
            {
                "order": 0,
                "type": "QUIZ",
                "header": "Knowledge check",
                "content_quiz_id": "quiz_abc",
                "content_html": "",
            }
        ]
    )
    assert "Knowledge check" in html
    assert "quiz_abc" in html


def test_aggregate_asset_placeholder_includes_header_and_id():
    html = _aggregate_lesson_content_items(
        [
            {
                "order": 0,
                "type": "ASSET",
                "header": "Handout",
                "content_asset_id": "asset_xyz",
                "content_html": "",
            }
        ]
    )
    assert "Handout" in html
    assert "asset_xyz" in html


def test_extra_redundant_when_identical_normalized():
    body = "<p>Same text content</p>"
    assert _extra_redundant_with_base(body, body) is True


def test_extra_not_redundant_when_items_add_new_text():
    base = "<div class='shell'></div>"
    extra = "<p>Only in content-items</p>"
    assert _extra_redundant_with_base(base, extra) is False


def test_attach_scraping_html_merges_html_lesson_shell_with_content_items(api_key):
    client = SkillJarClient()
    items = [
        {
            "order": 0,
            "type": "HTML",
            "content_html": "<p>Real learner copy from items</p>",
            "header": "",
        }
    ]
    client.list_lesson_content_items = lambda _lid: items  # type: ignore[method-assign]

    lesson = {
        "id": "lesson1",
        "type": "HTML",
        "content_html": "<div class='shell'></div>",
    }
    client._attach_scraping_html(lesson)

    assert "Real learner copy from items" in lesson["scraping_html"]
    assert "shell" in lesson["scraping_html"]


def test_attach_scraping_html_dedupes_when_extra_already_in_base(api_key):
    client = SkillJarClient()
    same = "<p>Unique paragraph for dedup test</p>"
    client.list_lesson_content_items = lambda _lid: [  # type: ignore[method-assign]
        {"order": 0, "type": "HTML", "content_html": same, "header": ""}
    ]
    lesson = {"id": "l2", "type": "HTML", "content_html": same}
    client._attach_scraping_html(lesson)

    assert lesson["scraping_html"] == same
