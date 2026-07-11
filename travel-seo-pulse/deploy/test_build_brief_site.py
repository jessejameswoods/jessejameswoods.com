"""Tests for build_brief_site.py - written before the implementation (TDD).

Encodes the BUILD-BRIEF requirements:
- discover newsletter-YYYY-MM-DD.html files only (skip preview.html, .md, malformed)
- reverse-chronological ordering
- date label extraction with filename fallback
- <meta name="robots" content="noindex"> injection, idempotent
- index page: exact placeholder copy, all entries, noindex meta, no em/en dashes
- robots.txt: allows crawling, no Disallow
"""
import re
from pathlib import Path

import pytest

from build_brief_site import (
    discover_briefs,
    date_label,
    inject_noindex,
    render_index,
    ROBOTS_TXT,
    build_site,
)

SAMPLE_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Travel SEO Pulse — July 10, 2026</title>
</head>
<body><h1>Travel SEO Pulse — July 10, 2026</h1></body>
</html>"""

PLACEHOLDER = (
    "Travel Search Pulse Daily is an automated radar: assembled every weekday "
    "morning by an AI pipeline that Jesse James Woods built and configured, "
    "from his curated source list. Essays and analysis live at travelsearchpulse.com."
)


@pytest.fixture
def output_dir(tmp_path):
    d = tmp_path / "output"
    d.mkdir()
    for date in ("2026-04-14", "2026-07-10", "2026-05-01"):
        (d / f"newsletter-{date}.html").write_text(
            SAMPLE_HTML.replace("July 10, 2026", date), encoding="utf-8"
        )
    # Files that must be ignored
    (d / "preview.html").write_text(SAMPLE_HTML, encoding="utf-8")
    (d / "newsletter-2026-07-10.md").write_text("# md file", encoding="utf-8")
    (d / "newsletter-garbage.html").write_text("<html></html>", encoding="utf-8")
    (d / "travel_seo_pulse.log").write_text("log", encoding="utf-8")
    return d


def test_discover_finds_only_valid_briefs(output_dir):
    briefs = discover_briefs(output_dir)
    names = [b.name for b in briefs]
    assert len(briefs) == 3
    assert "preview.html" not in names
    assert "newsletter-garbage.html" not in names
    assert "newsletter-2026-07-10.md" not in names


def test_discover_reverse_chronological(output_dir):
    briefs = discover_briefs(output_dir)
    assert [b.name for b in briefs] == [
        "newsletter-2026-07-10.html",
        "newsletter-2026-05-01.html",
        "newsletter-2026-04-14.html",
    ]


def test_date_label_formats_from_filename():
    assert date_label("newsletter-2026-07-10.html") == "July 10, 2026"
    assert date_label("newsletter-2026-04-01.html") == "April 1, 2026"


def test_inject_noindex_adds_meta_after_charset():
    out = inject_noindex(SAMPLE_HTML)
    assert '<meta name="robots" content="noindex">' in out
    # placed inside <head>
    assert out.index('<meta name="robots"') < out.index("</head>")


def test_inject_noindex_is_idempotent():
    once = inject_noindex(SAMPLE_HTML)
    twice = inject_noindex(once)
    assert twice.count('<meta name="robots" content="noindex">') == 1


def test_render_index_contains_exact_placeholder_and_entries(output_dir):
    briefs = discover_briefs(output_dir)
    html = render_index(briefs)
    assert PLACEHOLDER in html
    assert '<meta name="robots" content="noindex">' in html
    assert 'href="newsletter-2026-07-10.html"' in html
    assert "July 10, 2026" in html
    # reverse-chronological: newest link appears before oldest
    assert html.index("newsletter-2026-07-10.html") < html.index(
        "newsletter-2026-04-14.html"
    )


def test_render_index_has_no_em_or_en_dashes(output_dir):
    html = render_index(discover_briefs(output_dir))
    assert "—" not in html
    assert "–" not in html


def test_robots_txt_allows_crawling():
    assert "User-agent: *" in ROBOTS_TXT
    assert re.search(r"^Disallow:\s*/\s*$", ROBOTS_TXT, re.MULTILINE) is None
    assert "Allow: /" in ROBOTS_TXT


def test_build_site_end_to_end(output_dir, tmp_path):
    webroot = tmp_path / "webroot"
    count = build_site(output_dir, webroot)
    assert count == 3
    assert (webroot / "index.html").exists()
    assert (webroot / "robots.txt").exists()
    copied = webroot / "newsletter-2026-07-10.html"
    assert copied.exists()
    assert '<meta name="robots" content="noindex">' in copied.read_text(
        encoding="utf-8"
    )
    # original untouched
    src = output_dir / "newsletter-2026-07-10.html"
    assert '<meta name="robots"' not in src.read_text(encoding="utf-8")


def test_build_site_rerun_is_idempotent(output_dir, tmp_path):
    webroot = tmp_path / "webroot"
    build_site(output_dir, webroot)
    count = build_site(output_dir, webroot)
    assert count == 3
    copied = (webroot / "newsletter-2026-07-10.html").read_text(encoding="utf-8")
    assert copied.count('<meta name="robots" content="noindex">') == 1
