"""Tests for build_brief_site.py v2 - written before the implementation (TDD).

v2 spec (Jesse, 2026-07-11), on top of v1 requirements:
1. Retroactive rebrand of archived pages: title/H1 -> "Travel Search Pulse
   Daily - [Month D, YYYY]" (plain hyphen), substack.com links -> www
   custom domain, KAYAK bio clause dropped from footer. Body content
   untouched.
2. Shared chrome on every page: masthead wordmark -> www, "Daily" identity,
   nav Essays/About/Archive. Injected once, idempotent.
3. Index cards: date + lead story headline as title, next story headlines
   as excerpt, parsed from the files. Newest first.
4. Exact intro copy with "Travel Search Pulse" linked; bare domain never
   named in prose elsewhere.
Constraints: noindex meta still injected, robots.txt still allows crawl,
no em/en dashes in any template-authored copy (parsed content passes
through verbatim).
"""
import re
from pathlib import Path

import pytest

from build_brief_site import (
    discover_briefs,
    date_label,
    inject_noindex,
    inject_chrome,
    transform_brief,
    extract_story_headlines,
    render_index,
    ROBOTS_TXT,
    INTRO_HTML,
    CHROME_HTML,
    CHROME_CSS,
    build_site,
)

# Realistic mini-brief modeled on the live template (em-dash title, TL;DR
# with anchor-wrapped bold, story sections with bold external links,
# KAYAK footer). One story headline deliberately contains an em dash to
# prove content passes through verbatim.
SAMPLE_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Travel SEO Pulse — July 10, 2026</title>
<style>body{font-family:'Inter'}</style>
</head>
<body>
<div class="container">
<h1>Travel SEO Pulse — July 10, 2026</h1>
<p><em>The daily briefing for people who care about search in travel.</em></p>
<p><strong>By Jesse James Woods</strong></p>
<hr>
<h2 id="the-briefing-tldr"><div id="§the-briefing-tldr"></div>The Briefing TL;DR</h2>
<ul>
<li>✈️ <a href="#§travel-industry"><strong>AI is breaking the travel funnel</strong></a> — summary. <em>From a Travel SEO POV: something.</em></li>
</ul>
<hr>
<h2 id="travel-industry"><div id="§travel-industry"></div>✈️ Travel Industry</h2>
<ul>
<li><strong><a href="https://example.com/story1">Lead Story Headline — With An Em Dash</a></strong> — <em>PhocusWire</em> · summary.</li>
</ul>
<ul>
<li><strong><a href="https://example.com/story2">Second Story Headline</a></strong> — <em>Skift</em> · summary.</li>
</ul>
<h2 id="seo-search"><div id="§seo-and-search"></div>🔍 SEO &amp; Search</h2>
<ul>
<li><strong><a href="https://example.com/story3">Third Story Headline</a></strong> — <em>Ahrefs</em> · summary.</li>
</ul>
<ul>
<li><strong><a href="https://example.com/story4">Fourth Story Headline</a></strong> — <em>SER</em> · summary.</li>
</ul>
<ul>
<li><strong><a href="https://example.com/story5">Fifth Story Headline</a></strong> — <em>Blog</em> · summary.</li>
</ul>
<hr>
<p><em>Travel SEO Pulse by Jesse James Woods, VP of SEO &amp; Localization at KAYAK. <a href="https://jessejameswoods.substack.com">Subscribe</a> · <a href="https://jessejameswoods.com">Website</a> · <a href="https://linkedin.com/in/jessejameswoods">LinkedIn</a></em></p>
</div>
</body>
</html>"""

INTRO_TEXT = (
    "The automated radar behind Travel Search Pulse: assembled every "
    "weekday morning by an AI pipeline that Jesse James Woods built and "
    "configured, from his curated source list."
)


def sample_for(date_iso):
    return SAMPLE_HTML.replace("July 10, 2026", date_iso)


@pytest.fixture
def output_dir(tmp_path):
    d = tmp_path / "output"
    d.mkdir()
    for date in ("2026-04-14", "2026-07-10", "2026-05-01"):
        (d / f"newsletter-{date}.html").write_text(SAMPLE_HTML, encoding="utf-8")
    (d / "preview.html").write_text(SAMPLE_HTML, encoding="utf-8")
    (d / "newsletter-2026-07-10.md").write_text("# md file", encoding="utf-8")
    (d / "newsletter-garbage.html").write_text("<html></html>", encoding="utf-8")
    return d


# ---- v1 behaviors that must not regress ----

def test_discover_finds_only_valid_briefs_newest_first(output_dir):
    briefs = discover_briefs(output_dir)
    assert [b.name for b in briefs] == [
        "newsletter-2026-07-10.html",
        "newsletter-2026-05-01.html",
        "newsletter-2026-04-14.html",
    ]


def test_date_label():
    assert date_label("newsletter-2026-07-10.html") == "July 10, 2026"
    assert date_label("newsletter-2026-04-01.html") == "April 1, 2026"


def test_inject_noindex_idempotent():
    once = inject_noindex(SAMPLE_HTML)
    assert once.count('<meta name="robots" content="noindex">') == 1
    assert inject_noindex(once).count('<meta name="robots" content="noindex">') == 1


def test_robots_txt_allows_crawling():
    assert "User-agent: *" in ROBOTS_TXT
    assert re.search(r"^Disallow:", ROBOTS_TXT, re.MULTILINE) is None
    assert "Allow: /" in ROBOTS_TXT


# ---- part 1: retroactive rebrand ----

def test_transform_rebrands_title_and_h1_plain_hyphen():
    out = transform_brief(SAMPLE_HTML, "July 10, 2026")
    assert "<title>Travel Search Pulse Daily - July 10, 2026</title>" in out
    assert "<h1>Travel Search Pulse Daily - July 10, 2026</h1>" in out
    assert "Travel SEO Pulse —" not in out


def test_transform_rewrites_substack_links_to_www():
    out = transform_brief(SAMPLE_HTML, "July 10, 2026")
    assert "jessejameswoods.substack.com" not in out
    assert '<a href="https://www.travelsearchpulse.com">Subscribe</a>' in out


def test_transform_drops_kayak_bio_from_footer():
    out = transform_brief(SAMPLE_HTML, "July 10, 2026")
    assert "KAYAK" not in out.split("<hr>")[-1]  # footer region
    assert "VP of SEO" not in out
    assert "Travel Search Pulse Daily by Jesse James Woods." in out


def test_transform_handles_already_rebranded_footer():
    pre = SAMPLE_HTML.replace(
        "Travel SEO Pulse by Jesse James Woods",
        "Travel Search Pulse Daily by Jesse James Woods",
    )
    out = transform_brief(pre, "July 10, 2026")
    assert "VP of SEO" not in out
    assert "Travel Search Pulse Daily by Jesse James Woods." in out


def test_transform_leaves_body_content_verbatim():
    out = transform_brief(SAMPLE_HTML, "July 10, 2026")
    # story headline with em dash untouched
    assert "Lead Story Headline — With An Em Dash" in out
    # POV phrasing untouched ("Travel SEO POV" is not the brand phrase)
    assert "From a Travel SEO POV: something." in out
    # story URLs untouched
    assert 'href="https://example.com/story1"' in out


def test_transform_adds_noindex_and_chrome():
    out = transform_brief(SAMPLE_HTML, "July 10, 2026")
    assert '<meta name="robots" content="noindex">' in out
    assert out.count("tsp-masthead") >= 1
    assert "tsp-chrome" in out


# ---- part 2: shared chrome ----

def test_chrome_mirrors_main_site_masthead():
    # real logo icon + wordmark linking home
    assert '<img src="/tsp-icon.png"' in CHROME_HTML
    assert ">Travel Search Pulse<" in CHROME_HTML
    assert 'href="https://www.travelsearchpulse.com"' in CHROME_HTML
    # same five tabs as the Substack site, same order, Daily active -> "/"
    tabs = re.findall(r'<a[^>]*class="[^"]*tsp-tab[^"]*"[^>]*>([^<]+)</a>', CHROME_HTML)
    assert tabs == ["Home", "Notes", "Daily", "Archive", "About"]
    assert '<a class="tsp-tab tsp-tab-active" href="/">Daily</a>' in CHROME_HTML
    assert 'href="https://www.travelsearchpulse.com/notes"' in CHROME_HTML
    assert 'href="https://www.travelsearchpulse.com/archive"' in CHROME_HTML
    assert 'href="https://www.travelsearchpulse.com/about"' in CHROME_HTML


def test_inject_chrome_is_idempotent():
    once = inject_chrome(SAMPLE_HTML)
    twice = inject_chrome(once)
    assert twice.count('class="tsp-masthead-inner"') == 1


def test_template_copy_has_no_em_or_en_dashes():
    for blob in (CHROME_HTML, CHROME_CSS, INTRO_HTML, ROBOTS_TXT):
        assert "—" not in blob and "–" not in blob


# ---- part 3: index cards ----

def test_extract_story_headlines_external_links_only_limit_4():
    heads = extract_story_headlines(SAMPLE_HTML)
    assert heads == [
        "Lead Story Headline — With An Em Dash",
        "Second Story Headline",
        "Third Story Headline",
        "Fourth Story Headline",
    ]
    # TL;DR anchor-wrapped bold must NOT be picked up
    assert "AI is breaking the travel funnel" not in heads


def test_extract_story_headlines_empty_on_malformed():
    assert extract_story_headlines("<html><body>nothing</body></html>") == []


def test_render_index_card_title_is_brand_plus_date(output_dir):
    briefs = discover_briefs(output_dir)
    html = render_index(briefs)
    assert 'href="newsletter-2026-07-10.html"' in html
    assert ('<span class="tsp-card-title">Travel Search Pulse Daily - '
            "July 10, 2026</span>") in html
    # top story headlines land in the excerpt instead
    assert "Lead Story Headline — With An Em Dash" in html
    assert "Fourth Story Headline" in html
    assert "Fifth Story Headline" not in html               # beyond top 4
    # newest first
    assert html.index("newsletter-2026-07-10.html") < html.index(
        "newsletter-2026-04-14.html"
    )


def test_render_index_falls_back_gracefully_without_headlines(tmp_path):
    d = tmp_path / "o"
    d.mkdir()
    (d / "newsletter-2026-06-01.html").write_text(
        "<html><head><title>x</title></head><body>no stories</body></html>",
        encoding="utf-8",
    )
    html = render_index(discover_briefs(d))
    assert 'href="newsletter-2026-06-01.html"' in html
    assert "Travel Search Pulse Daily - June 1, 2026" in html


# ---- part 4: intro copy ----

def test_index_intro_exact_copy_with_brand_link(output_dir):
    html = render_index(discover_briefs(output_dir))
    text = re.sub(r"<[^>]+>", "", html)
    assert INTRO_TEXT in " ".join(text.split())
    assert ('<a href="https://www.travelsearchpulse.com">Travel Search Pulse</a>'
            in html)


def test_index_never_names_bare_domain_in_prose(output_dir):
    html = render_index(discover_briefs(output_dir))
    text = re.sub(r"<[^>]+>", " ", html)  # strip tags, keep text nodes
    assert "travelsearchpulse.com" not in text


def test_index_has_chrome_and_noindex(output_dir):
    html = render_index(discover_briefs(output_dir))
    assert html.count('class="tsp-masthead-inner"') == 1
    assert '<meta name="robots" content="noindex">' in html


# ---- end to end ----

def test_build_site_end_to_end(output_dir, tmp_path):
    webroot = tmp_path / "webroot"
    count = build_site(output_dir, webroot)
    assert count == 3
    copied = (webroot / "newsletter-2026-07-10.html").read_text(encoding="utf-8")
    assert "<title>Travel Search Pulse Daily - July 10, 2026</title>" in copied
    assert "jessejameswoods.substack.com" not in copied
    assert "KAYAK" not in copied
    assert copied.count('class="tsp-masthead-inner"') == 1
    assert '<meta name="robots" content="noindex">' in copied
    # source untouched
    src = (output_dir / "newsletter-2026-07-10.html").read_text(encoding="utf-8")
    assert "Travel SEO Pulse —" in src and "KAYAK" in src
    assert (webroot / "robots.txt").read_text(encoding="utf-8") == ROBOTS_TXT


def test_build_site_rerun_is_idempotent(output_dir, tmp_path):
    webroot = tmp_path / "webroot"
    build_site(output_dir, webroot)
    build_site(output_dir, webroot)
    copied = (webroot / "newsletter-2026-07-10.html").read_text(encoding="utf-8")
    assert copied.count('class="tsp-masthead-inner"') == 1
    assert copied.count('<meta name="robots" content="noindex">') == 1


# ---- byline author link + schema ----

def test_transform_links_byline_to_author_page():
    out = transform_brief(SAMPLE_HTML, "July 10, 2026")
    assert ('By <a href="https://www.travelsearchpulse.com/about">'
            "Jesse James Woods</a>") in out


def test_transform_injects_author_schema_once():
    out = transform_brief(SAMPLE_HTML, "July 10, 2026")
    assert out.count('application/ld+json') == 1
    assert '"@type": "Person"' in out
    assert '"name": "Jesse James Woods"' in out
    assert '"url": "https://www.travelsearchpulse.com/about"' in out
    assert '"datePublished": "2026-07-10"' in out
    # idempotent
    again = transform_brief(out, "July 10, 2026")
    assert again.count('application/ld+json') == 1


def test_build_site_copies_icon_when_present(output_dir, tmp_path, monkeypatch):
    import build_brief_site as b
    icon_src = tmp_path / "icon.png"
    icon_src.write_bytes(b"\x89PNG-fake")
    monkeypatch.setattr(b, "ICON_SOURCE", str(icon_src))
    webroot = tmp_path / "webroot"
    b.build_site(output_dir, webroot)
    assert (webroot / "tsp-icon.png").read_bytes() == b"\x89PNG-fake"


def test_build_site_survives_missing_icon(output_dir, tmp_path, monkeypatch):
    import build_brief_site as b
    monkeypatch.setattr(b, "ICON_SOURCE", str(tmp_path / "nope.png"))
    webroot = tmp_path / "webroot"
    assert b.build_site(output_dir, webroot) == 3


# ---- hero image (Jesse, Jul 13: recurring brand hero on every post, Indig precedent) ----

def test_transform_injects_hero_after_byline():
    out = transform_brief(SAMPLE_HTML, "July 10, 2026")
    assert '<img src="/daily-brief-hero.jpg"' in out
    assert 'class="tsp-hero"' in out
    assert 'alt="Travel Search Pulse Daily"' in out
    # placed after the byline, before the TL;DR content
    assert out.index("By ") < out.index("tsp-hero") < out.index("The Briefing TL;DR")


def test_transform_hero_is_idempotent():
    once = transform_brief(SAMPLE_HTML, "July 10, 2026")
    twice = inject_chrome(once)  # re-running injectors must not duplicate
    from build_brief_site import inject_hero
    assert inject_hero(once).count('class="tsp-hero"') == 1


def test_build_site_copies_hero_when_present(output_dir, tmp_path, monkeypatch):
    import build_brief_site as b
    hero_src = tmp_path / "hero.jpg"
    hero_src.write_bytes(b"\xff\xd8fakejpg")
    monkeypatch.setattr(b, "HERO_SOURCE", str(hero_src))
    webroot = tmp_path / "webroot"
    b.build_site(output_dir, webroot)
    assert (webroot / "daily-brief-hero.jpg").read_bytes() == b"\xff\xd8fakejpg"


def test_build_site_survives_missing_hero(output_dir, tmp_path, monkeypatch):
    import build_brief_site as b
    monkeypatch.setattr(b, "HERO_SOURCE", str(tmp_path / "nope.jpg"))
    assert b.build_site(output_dir, tmp_path / "webroot") == 3
