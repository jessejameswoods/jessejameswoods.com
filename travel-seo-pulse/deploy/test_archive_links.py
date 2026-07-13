"""Tests for the archive-link injection in substack_publisher.py (TDD).

Why: the Substack web post 404s ~30 min after send (publish-then-
unpublish design), so every emailed link needs an in-body path to the
permanent archive copy at brief.travelsearchpulse.com.
"""
from substack_publisher import (
    _add_archive_links,
    _archive_url_for_today,
    _prepare_markdown_for_substack,
)

RAW = """# Travel Search Pulse Daily - July 14, 2026
*subtitle*
**By Jesse James Woods**

---

## The Briefing TL;DR

- bullet one

---

*Travel Search Pulse Daily by Jesse James Woods, VP of SEO & Localization at KAYAK. [Subscribe](https://jessejameswoods.substack.com)*"""

URL = "https://brief.travelsearchpulse.com/newsletter-2026-07-14.html"


def test_hero_image_is_first_line_then_browser_link():
    out = _add_archive_links("body text", URL)
    lines = out.splitlines()
    assert lines[0] == ("![Travel Search Pulse Daily]"
                        "(https://brief.travelsearchpulse.com/daily-brief-hero.jpg)")
    assert lines[2] == f"*[Read this brief in your browser]({URL})*"


def test_bottom_block_has_archive_and_index_links():
    out = _add_archive_links("body text", URL)
    tail = out.splitlines()[-1]
    assert f"[Read this brief in your browser]({URL})" in tail
    assert "[Full archive](https://brief.travelsearchpulse.com/)" in tail


def test_body_preserved_between_links():
    out = _add_archive_links("line a\n\nline b", URL)
    assert "line a\n\nline b" in out


def test_no_em_or_en_dashes_in_injected_copy():
    out = _add_archive_links("", URL)
    assert "—" not in out and "–" not in out


def test_composes_with_strip_function():
    # strip first (removes title block + old footer), then inject
    stripped = _prepare_markdown_for_substack(RAW)
    assert "KAYAK" not in stripped  # old footer gone
    out = _add_archive_links(stripped, URL)
    assert out.splitlines()[0].startswith("![Travel Search Pulse Daily]")
    assert "## The Briefing TL;DR" in out
    assert "KAYAK" not in out


def test_archive_url_for_today_shape():
    url = _archive_url_for_today()
    import re
    assert re.fullmatch(
        r"https://brief\.travelsearchpulse\.com/newsletter-\d{4}-\d{2}-\d{2}\.html",
        url,
    )
