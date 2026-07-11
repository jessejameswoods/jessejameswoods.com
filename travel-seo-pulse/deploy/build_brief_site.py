#!/usr/bin/env python3
"""Build the static brief archive site for brief.travelsearchpulse.com (v3).

Reads newsletter-YYYY-MM-DD.html artifacts from the pipeline output
directory and publishes them to a webroot with, per copy:
- retroactive rebrand: title/H1 -> "Travel Search Pulse Daily - Month D,
  YYYY" (plain hyphen), substack.com links -> www.travelsearchpulse.com,
  KAYAK bio clause dropped from the footer. Body content never rewritten.
- byline linked to the author page (www/about) + NewsArticle JSON-LD
  with Person author schema.
- shared site chrome mirroring the main Substack site: real pulse icon,
  bold sans wordmark, tabs Home / Notes / Daily / Archive / About with
  Daily active on this site.
- noindex meta injected (belt-and-braces next to the Caddy header).

Also generates index.html (cards titled "Travel Search Pulse Daily -
[date]" with top story headlines as excerpt, newest first), robots.txt
(ALLOW crawling - a Disallow would hide the noindex from Google), and
copies the site icon into the webroot.

Source files are never modified. Idempotent. Stdlib only (Python 3.12).

Usage: build_brief_site.py [SOURCE_DIR] [WEBROOT]
"""
import re
import shutil
import sys
from datetime import date, datetime
from pathlib import Path

DEFAULT_SOURCE = "/opt/travel-seo-pulse/travel-seo-pulse/output"
DEFAULT_WEBROOT = "/var/www/brief"
ICON_SOURCE = "/usr/local/share/travel-search-pulse/tsp-icon.png"

BRAND = "Travel Search Pulse Daily"
WWW = "https://www.travelsearchpulse.com"
AUTHOR_URL = f"{WWW}/about"

BRIEF_RE = re.compile(r"^newsletter-(\d{4})-(\d{2})-(\d{2})\.html$")
NOINDEX_META = '<meta name="robots" content="noindex">'

ROBOTS_TXT = "User-agent: *\nAllow: /\n"

# Exact copy per spec. "Travel Search Pulse" is the only place the site
# is named in prose; the bare domain is never written out as text.
INTRO_HTML = (
    '<p class="tsp-intro">The automated radar behind '
    f'<a href="{WWW}">Travel Search Pulse</a>: assembled every weekday '
    "morning by an AI pipeline that Jesse James Woods built and "
    "configured, from his curated source list.</p>"
)

# Masthead mirrors the main Substack site: pulse icon + dark bold sans
# wordmark, centered, with the same five tabs in the same order.
CHROME_CSS = """<link rel="icon" href="/tsp-icon.png">
<style>/* tsp-chrome */
.tsp-masthead{background:#FAF7F2;border-bottom:1px solid #E8E3DD}
.tsp-masthead-inner{max-width:680px;margin:0 auto;padding:1rem 1.5rem 0}
.tsp-brand{display:flex;align-items:center;justify-content:center;gap:.55rem;text-decoration:none}
.tsp-icon{width:28px;height:28px;border-radius:6px;display:block}
.tsp-wordmark{font-family:'Inter',sans-serif;font-size:1.2rem;font-weight:700;color:#1a1a1a}
.tsp-tabs{display:flex;justify-content:center;gap:1.5rem;margin-top:.7rem;flex-wrap:wrap}
.tsp-tab{font-family:'Inter',sans-serif;font-size:.92rem;font-weight:500;color:#6B6560;text-decoration:none;padding:.35rem 0 .55rem;border-bottom:2px solid transparent}
.tsp-tab:hover{color:#1a1a1a}
.tsp-tab-active{color:#1a1a1a;font-weight:600;border-bottom:2px solid #1a1a1a}
</style>"""

CHROME_HTML = """<header class="tsp-masthead"><div class="tsp-masthead-inner">
<a class="tsp-brand" href="https://www.travelsearchpulse.com"><img src="/tsp-icon.png" alt="Travel Search Pulse" class="tsp-icon"><span class="tsp-wordmark">Travel Search Pulse</span></a>
<nav class="tsp-tabs"><a class="tsp-tab" href="https://www.travelsearchpulse.com">Home</a><a class="tsp-tab" href="https://www.travelsearchpulse.com/notes">Notes</a><a class="tsp-tab tsp-tab-active" href="/">Daily</a><a class="tsp-tab" href="https://www.travelsearchpulse.com/archive">Archive</a><a class="tsp-tab" href="https://www.travelsearchpulse.com/about">About</a></nav>
</div></header>"""

SCHEMA_TEMPLATE = """<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "NewsArticle",
  "headline": "__HEADLINE__",
  "datePublished": "__DATE__",
  "author": {
    "@type": "Person",
    "name": "Jesse James Woods",
    "url": "https://www.travelsearchpulse.com/about",
    "sameAs": [
      "https://jessejameswoods.com",
      "https://linkedin.com/in/jessejameswoods"
    ]
  },
  "publisher": {
    "@type": "Organization",
    "name": "Travel Search Pulse",
    "url": "https://www.travelsearchpulse.com"
  }
}
</script>"""

INDEX_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="robots" content="noindex">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Travel Search Pulse Daily - Brief Archive</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Inter',sans-serif;background:#FAF7F2;color:#1a1a1a;line-height:1.7;font-size:16px}
.container{max-width:680px;margin:0 auto;padding:2rem 1.5rem}
h1{font-family:'DM Serif Display',serif;font-size:2rem;margin-bottom:.75rem}
.tsp-intro{color:#6B6560;font-size:.95rem;margin-bottom:2rem;padding-bottom:1.5rem;border-bottom:1px solid #E8E3DD}
.tsp-intro a{color:#C2532E;text-decoration:none}
.tsp-intro a:hover{opacity:.8}
ul.tsp-cards{list-style:none}
.tsp-card{margin-bottom:1.1rem;padding-bottom:1.1rem;border-bottom:1px solid #E8E3DD}
.tsp-card-link{text-decoration:none;display:block}
.tsp-card-title{display:block;font-family:'DM Serif Display',serif;font-size:1.15rem;line-height:1.4;color:#1a1a1a}
.tsp-card-link:hover .tsp-card-title{color:#C2532E}
.tsp-card-excerpt{display:block;font-size:.88rem;color:#6B6560;margin-top:.25rem}
</style>
__CHROME_CSS__
</head>
<body>
__CHROME_HTML__
<div class="container">
<h1>The Daily Brief</h1>
__INTRO__
<ul class="tsp-cards">
__ENTRIES__
</ul>
</div>
</body>
</html>
"""


def discover_briefs(source_dir):
    """Brief files matching newsletter-YYYY-MM-DD.html, newest first."""
    source_dir = Path(source_dir)
    briefs = [p for p in source_dir.iterdir() if BRIEF_RE.match(p.name)]
    return sorted(briefs, key=lambda p: p.name, reverse=True)


def date_label(filename):
    """'July 10, 2026' from a brief filename. Plain text, no dashes."""
    m = BRIEF_RE.match(Path(filename).name)
    dt = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return f"{dt.strftime('%B')} {dt.day}, {dt.year}"


def _label_to_iso(label):
    return datetime.strptime(label, "%B %d, %Y").strftime("%Y-%m-%d")


def inject_noindex(html):
    """Insert the noindex meta after <meta charset...>. Idempotent."""
    if NOINDEX_META in html:
        return html
    charset = re.search(r"<meta charset[^>]*>", html)
    if charset:
        i = charset.end()
        return html[:i] + "\n" + NOINDEX_META + html[i:]
    return html.replace("<head>", "<head>\n" + NOINDEX_META, 1)


def inject_chrome(html):
    """Masthead + its CSS on any page. Idempotent (marker: tsp-masthead)."""
    if "tsp-masthead" in html:
        return html
    html = html.replace("</head>", CHROME_CSS + "\n</head>", 1)
    body = re.search(r"<body[^>]*>", html)
    if body:
        i = body.end()
        html = html[:i] + "\n" + CHROME_HTML + html[i:]
    return html


def inject_author_schema(html, headline, iso_date):
    """NewsArticle JSON-LD with Person author. Idempotent."""
    if "application/ld+json" in html:
        return html
    block = (SCHEMA_TEMPLATE
             .replace("__HEADLINE__", headline)
             .replace("__DATE__", iso_date))
    return html.replace("</head>", block + "\n</head>", 1)


def transform_brief(html, label):
    """Rebrand branding surfaces of an archived brief, link the byline,
    add author schema and chrome. Body content is left verbatim."""
    canonical = f"{BRAND} - {label}"
    html = re.sub(r"<title>[^<]*</title>", f"<title>{canonical}</title>",
                  html, count=1)
    html = re.sub(r"<h1>[^<]*</h1>", f"<h1>{canonical}</h1>", html, count=1)

    # Substack publication links move to the custom domain
    html = html.replace("https://jessejameswoods.substack.com", WWW)
    html = html.replace("jessejameswoods.substack.com",
                        "www.travelsearchpulse.com")

    # Footer bio: drop the role clause entirely (approved option)
    html = re.sub(
        r"Travel (?:SEO Pulse|Search Pulse Daily) by Jesse James Woods, "
        r"VP of SEO (?:&amp;|&) Localization at KAYAK\.",
        f"{BRAND} by Jesse James Woods.",
        html,
    )

    # Any remaining exact brand-phrase mentions (does not touch
    # "Travel SEO POV" or other body prose)
    html = html.replace("Travel SEO Pulse", BRAND)

    # Byline links to the author page (idempotent: pattern gone after)
    html = html.replace(
        "<strong>By Jesse James Woods</strong>",
        f'<strong>By <a href="{AUTHOR_URL}">Jesse James Woods</a></strong>',
        1,
    )

    html = inject_author_schema(html, canonical, _label_to_iso(label))
    html = inject_noindex(html)
    html = inject_chrome(html)
    return html


STORY_RE = re.compile(
    r'<strong><a href="https?://[^"]*"[^>]*>(.*?)</a></strong>', re.DOTALL
)


def extract_story_headlines(html, limit=4):
    """Story headlines = bold external links (<strong><a href="http...">).
    TL;DR bullets are anchor-wrapped the other way around and are skipped
    by construction. Returns up to `limit` headlines, document order."""
    heads = []
    for m in STORY_RE.finditer(html):
        text = re.sub(r"<[^>]+>", "", m.group(1)).strip()
        if text:
            heads.append(text)
        if len(heads) >= limit:
            break
    return heads


def render_card(brief_path):
    """Card title is literally the brand + date; the day's top story
    headlines form the excerpt."""
    label = date_label(brief_path.name)
    try:
        heads = extract_story_headlines(
            brief_path.read_text(encoding="utf-8"))
    except OSError:
        heads = []
    excerpt = " · ".join(heads)
    excerpt_html = (
        f'\n<span class="tsp-card-excerpt">{excerpt}</span>' if excerpt else ""
    )
    return (
        f'<li class="tsp-card"><a class="tsp-card-link" href="{brief_path.name}">'
        f'<span class="tsp-card-title">{BRAND} - {label}</span>'
        f"{excerpt_html}</a></li>"
    )


def render_index(briefs):
    """Content-card index, newest first (briefs arrive newest-first)."""
    entries = "\n".join(render_card(p) for p in briefs)
    return (
        INDEX_TEMPLATE
        .replace("__CHROME_CSS__", CHROME_CSS)
        .replace("__CHROME_HTML__", CHROME_HTML)
        .replace("__INTRO__", INTRO_HTML)
        .replace("__ENTRIES__", entries)
    )


def build_site(source_dir, webroot):
    """Transform + publish briefs, write index.html, robots.txt, icon."""
    source_dir, webroot = Path(source_dir), Path(webroot)
    webroot.mkdir(parents=True, exist_ok=True)

    briefs = discover_briefs(source_dir)
    for src in briefs:
        html = transform_brief(src.read_text(encoding="utf-8"),
                               date_label(src.name))
        dest = webroot / src.name
        if not dest.exists() or dest.read_text(encoding="utf-8") != html:
            dest.write_text(html, encoding="utf-8")

    (webroot / "index.html").write_text(render_index(briefs), encoding="utf-8")
    (webroot / "robots.txt").write_text(ROBOTS_TXT, encoding="utf-8")

    icon = Path(ICON_SOURCE)
    if icon.is_file():
        shutil.copyfile(icon, webroot / "tsp-icon.png")
    return len(briefs)


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SOURCE
    dst = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_WEBROOT
    n = build_site(src, dst)
    print(f"brief site built: {n} briefs -> {dst}")
