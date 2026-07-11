#!/usr/bin/env python3
"""Build the static brief archive site for brief.travelsearchpulse.com.

Copies newsletter-YYYY-MM-DD.html artifacts from the pipeline output
directory into a webroot, injecting <meta name="robots" content="noindex">
into each copy, and generates index.html + robots.txt.

Idempotent: safe to run any number of times. Stdlib only (Python 3.12).

Usage:
    build_brief_site.py [SOURCE_DIR] [WEBROOT]

Defaults:
    SOURCE_DIR = /opt/travel-seo-pulse/travel-seo-pulse/output
    WEBROOT    = /var/www/brief
"""
import re
import sys
from datetime import date
from pathlib import Path

DEFAULT_SOURCE = "/opt/travel-seo-pulse/travel-seo-pulse/output"
DEFAULT_WEBROOT = "/var/www/brief"

BRIEF_RE = re.compile(r"^newsletter-(\d{4})-(\d{2})-(\d{2})\.html$")
NOINDEX_META = '<meta name="robots" content="noindex">'

# robots.txt must ALLOW crawling. A Disallow would stop Google from ever
# seeing the X-Robots-Tag noindex header, defeating the mechanism entirely.
ROBOTS_TXT = "User-agent: *\nAllow: /\n"

PLACEHOLDER = (
    "Travel Search Pulse Daily is an automated radar: assembled every weekday "
    "morning by an AI pipeline that Jesse James Woods built and configured, "
    "from his curated source list. Essays and analysis live at travelsearchpulse.com."
)

INDEX_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="robots" content="noindex">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Travel Search Pulse Daily - Brief Archive</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Inter',sans-serif;background:#FAF7F2;color:#1a1a1a;line-height:1.7;font-size:16px}}
.container{{max-width:680px;margin:0 auto;padding:2rem 1.5rem}}
h1{{font-family:'DM Serif Display',serif;font-size:2.2rem;margin-bottom:.5rem}}
.header{{text-align:center;padding:2rem 0;border-bottom:2px solid #C2532E;margin-bottom:2rem}}
.header p{{color:#6B6560;font-size:.95rem;margin-top:1rem;text-align:left}}
ul{{list-style:none}}
li{{margin-bottom:.75rem;padding-bottom:.75rem;border-bottom:1px solid #E8E3DD}}
a{{color:#C2532E;text-decoration:none;font-weight:500}}
a:hover{{opacity:.8}}
.footer{{text-align:center;padding:2rem 0;margin-top:2rem;border-top:2px solid #C2532E;color:#6B6560;font-size:.9rem}}
.footer a{{color:#C2532E}}
</style>
</head>
<body>
<div class="container">
<div class="header">
<h1>Travel Search Pulse Daily</h1>
<p>{placeholder}</p>
</div>
<ul>
{entries}
</ul>
<div class="footer">
<p><a href="https://travelsearchpulse.com">travelsearchpulse.com</a></p>
</div>
</div>
</body>
</html>
"""


def discover_briefs(source_dir):
    """Return brief HTML files matching newsletter-YYYY-MM-DD.html,
    newest first. Ignores everything else (preview.html, .md, logs,
    malformed names)."""
    source_dir = Path(source_dir)
    briefs = [p for p in source_dir.iterdir() if BRIEF_RE.match(p.name)]
    return sorted(briefs, key=lambda p: p.name, reverse=True)


def date_label(filename):
    """Human date label from a brief filename: 'July 10, 2026'.
    No em or en dashes anywhere in generated text (Jesse's writing rule)."""
    m = BRIEF_RE.match(Path(filename).name)
    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    dt = date(y, mo, d)
    return f"{dt.strftime('%B')} {dt.day}, {dt.year}"


def inject_noindex(html):
    """Insert the noindex meta right after <meta charset...>. Idempotent."""
    if NOINDEX_META in html:
        return html
    charset = re.search(r"<meta charset[^>]*>", html)
    if charset:
        i = charset.end()
        return html[:i] + "\n" + NOINDEX_META + html[i:]
    # Fallback: right after <head>
    return html.replace("<head>", "<head>\n" + NOINDEX_META, 1)


def render_index(briefs):
    """Reverse-chronological index page. Briefs are already newest-first."""
    entries = "\n".join(
        f'<li><a href="{p.name}">{date_label(p.name)}</a></li>' for p in briefs
    )
    return INDEX_TEMPLATE.format(placeholder=PLACEHOLDER, entries=entries)


def build_site(source_dir, webroot):
    """Copy briefs (with noindex meta), write index.html and robots.txt.
    Returns the number of briefs published."""
    source_dir, webroot = Path(source_dir), Path(webroot)
    webroot.mkdir(parents=True, exist_ok=True)

    briefs = discover_briefs(source_dir)
    for src in briefs:
        html = inject_noindex(src.read_text(encoding="utf-8"))
        dest = webroot / src.name
        if not dest.exists() or dest.read_text(encoding="utf-8") != html:
            dest.write_text(html, encoding="utf-8")

    (webroot / "index.html").write_text(render_index(briefs), encoding="utf-8")
    (webroot / "robots.txt").write_text(ROBOTS_TXT, encoding="utf-8")
    return len(briefs)


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SOURCE
    dst = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_WEBROOT
    n = build_site(src, dst)
    print(f"brief site built: {n} briefs -> {dst}")
