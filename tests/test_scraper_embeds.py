"""Scraper extracts preview text from iframe / embed markup."""

from tools.curriculum.scraper import extract_lesson_content

ARCADE_IFRAME_HTML = """<!--ARCADE EMBED START-->
<div style="position: relative; padding-bottom: calc(56.25% + 41px); height: 0; width: 100%;"><iframe style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; color-scheme: light;" title="Writing baseline test coverage" src="https://demo.arcade.software/JBIhekHLSK0PpV3eXBhY?embed&amp;embed_mobile=tab&amp;embed_desktop=inline&amp;show_copy_link=true" frameborder="0" allowfullscreen="" loading="lazy"></iframe></div>
<!--ARCADE EMBED END-->"""


def test_iframe_title_becomes_plain_text_preview():
    lesson = {
        "id": "2k0izo8k4xnyg",
        "title": "Writing baseline test coverage",
        "scraping_html": ARCADE_IFRAME_HTML,
    }
    lc = extract_lesson_content(lesson)
    assert "Writing baseline test coverage" in lc.plain_text
    assert lc.plain_text.startswith("Embedded Arcade:")
    assert "demo.arcade.software" in lc.plain_text
    assert "JBIhekHLSK0PpV3eXBhY" in lc.plain_text


def test_iframe_without_title_uses_arcade_url():
    html = '<iframe src="https://demo.arcade.software/foo?embed"></iframe>'
    lc = extract_lesson_content({"id": "x", "title": "t", "scraping_html": html})
    assert lc.plain_text.startswith("Embedded Arcade:")
    assert "demo.arcade.software/foo" in lc.plain_text


def test_non_arcade_iframe_keeps_generic_embed_label():
    html = '<iframe title="Lesson video" src="https://www.youtube.com/embed/abc"></iframe>'
    lc = extract_lesson_content({"id": "x", "title": "t", "scraping_html": html})
    assert lc.plain_text == "Embedded: Lesson video"


def test_noscript_fallback_body_is_not_stripped():
    """Real copy often lives in <noscript> in authored HTML; it must appear in previews."""
    html = (
        "<script>console.log(1);</script>"
        "<noscript><p>Static fallback paragraph for scrapers.</p></noscript>"
    )
    lc = extract_lesson_content({"id": "x", "title": "t", "scraping_html": html})
    assert "Static fallback paragraph" in lc.plain_text
    assert "console.log" not in lc.plain_text


def test_skips_style_and_script_bodies_like_new_course_templates():
    """Bundled lesson CSS/JS should not flood plain_text; body + iframes still appear."""
    html = (
        "<div><style>*, *::before { box-sizing: border-box; margin: 999px; }</style></div>"
        '<p class="lesson-body">Visible lesson paragraph.</p>'
        '<iframe title="Walkthrough" src="https://demo.arcade.software/abc?embed"></iframe>'
        "<script>var items = document.querySelectorAll('.acc-item');</script>"
        "<p>After script.</p>"
    )
    lc = extract_lesson_content({"id": "x", "title": "t", "scraping_html": html})
    t = lc.plain_text
    assert "box-sizing" not in t and "querySelectorAll" not in t
    assert "Visible lesson paragraph" in t
    assert "After script" in t
    assert "Embedded Arcade: Walkthrough" in t
    assert "demo.arcade.software/abc" in t
    i_vis = t.find("Visible")
    i_arc = t.find("Embedded Arcade")
    i_after = t.find("After script")
    assert i_vis < i_arc < i_after


def test_multiple_arcade_iframes_interleaved_with_text_in_document_order():
    """Simulates merged HTML from several content-items: prose, embed, prose, embed."""
    html = (
        "<p>Introduction copy.</p>"
        '<iframe title="First walkthrough" src="https://demo.arcade.software/aaa"></iframe>'
        "<p>Middle section.</p>"
        '<iframe title="Second walkthrough" src="https://demo.arcade.software/bbb"></iframe>'
        "<p>Closing copy.</p>"
    )
    lc = extract_lesson_content({"id": "x", "title": "t", "scraping_html": html})
    t = lc.plain_text
    i_intro = t.find("Introduction")
    i_first = t.find("Embedded Arcade: First walkthrough")
    i_mid = t.find("Middle")
    i_second = t.find("Embedded Arcade: Second walkthrough")
    i_close = t.find("Closing")
    assert i_intro < i_first < i_mid < i_second < i_close
    assert "demo.arcade.software/aaa" in t and "demo.arcade.software/bbb" in t
