"""
Travel SEO Pulse — HTML Preview Generator
Converts newsletter markdown to styled HTML preview.
"""

import re

HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Inter',sans-serif;background:#FAF7F2;color:#1a1a1a;line-height:1.7;font-size:16px}}
.container{{max-width:680px;margin:0 auto;padding:2rem 1.5rem}}
h1{{font-family:'DM Serif Display',serif;font-size:2.2rem;margin-bottom:.25rem;color:#1a1a1a}}
h2{{font-family:'DM Serif Display',serif;font-size:1.5rem;color:#2C1810;margin:2rem 0 1rem;padding-bottom:.5rem;border-bottom:2px solid #E8E3DD}}
h3{{font-size:1.1rem;margin:1.5rem 0 .5rem}}
p{{margin-bottom:1rem;color:#1a1a1a}}
em{{color:#6B6560}}
a{{color:#C2532E;text-decoration:none}}
a:hover{{opacity:.8}}
strong a{{color:#C2532E;text-decoration:underline;text-decoration-color:#E8E3DD;text-underline-offset:2px}}
strong a:hover{{opacity:.8}}
ul{{padding-left:1.2rem;margin-bottom:1rem;list-style:disc}}
ul li{{margin-bottom:.75rem;padding-left:.25rem}}
ul li strong a{{color:#C2532E;text-decoration:underline;text-decoration-color:#E8E3DD;text-underline-offset:2px}}
.byline{{font-weight:600;color:#1a1a1a;margin-bottom:1rem}}
.pov{{font-style:italic}}
hr{{border:none;border-top:1px solid #E8E3DD;margin:1.5rem 0}}
.header{{text-align:center;padding:2rem 0;border-bottom:2px solid #C2532E;margin-bottom:2rem}}
.header p{{color:#6B6560;font-size:.95rem}}
.footer{{text-align:center;padding:2rem 0;margin-top:2rem;border-top:2px solid #C2532E;color:#6B6560;font-size:.9rem}}
.footer a{{color:#C2532E}}
</style>
</head>
<body>
<div class="container">
{content}
</div>
</body>
</html>"""


def slugify(text: str) -> str:
    """Convert header text to a URL-friendly slug for anchor links."""
    # Remove emojis and special characters
    slug = re.sub(r'[^\w\s-]', '', text)
    slug = slug.strip().lower()
    slug = re.sub(r'[\s]+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    return slug


def md_to_html(markdown_text: str) -> str:
    """Simple markdown to HTML conversion for newsletter preview."""
    html = markdown_text

    # Headers — h2 gets id attributes for anchor links
    html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)

    def h2_with_id(match):
        title = match.group(1)
        slug = slugify(title)
        # Generate Substack §-prefixed slug: Substack converts & to "and"
        substack_title = title.replace('&', 'and')
        substack_slug = '§' + slugify(substack_title)
        return f'<h2 id="{slug}"><div id="{substack_slug}"></div>{title}</h2>'

    html = re.sub(r'^## (.+)$', h2_with_id, html, flags=re.MULTILINE)
    html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)

    # Horizontal rules
    html = re.sub(r'^---+$', r'<hr>', html, flags=re.MULTILINE)

    # Bold + link combo: **[text](url)**
    html = re.sub(r'\*\*\[([^\]]+)\]\(([^)]+)\)\*\*', r'<strong><a href="\2">\1</a></strong>', html)

    # Bold
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)

    # Italic
    html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)

    # Links
    html = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', html)

    # Normalize POV capitalization and ensure consistent italic styling
    # Full italic block: <em>From a travel SEO pov: ...text...</em> → keep as <em> with proper caps
    def _pov_em_replace(m):
        rest = m.group(1)
        return f'<em>From a Travel SEO POV: {rest}</em>'

    html = re.sub(
        r'<em>From a [Tt]ravel SEO [Pp][Oo][Vv]:?\s*(.*?)</em>',
        _pov_em_replace,
        html
    )
    # No anchor fixups needed — prompt now generates correct Substack §-prefix slugs

    # Paragraphs — wrap non-tag lines, handle lists
    lines = html.split('\n')
    result = []
    in_ul = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if in_ul:
                result.append('</ul>')
                in_ul = False
            result.append('')
        elif re.match(r'^- ', stripped):
            # Unordered list item (dash bullet)
            if not in_ul:
                result.append('<ul>')
                in_ul = True
            item_text = re.sub(r'^- ', '', stripped)
            result.append(f'<li>{item_text}</li>')
        elif re.match(r'^\d+\.\s', stripped):
            # Numbered list item (fallback)
            if not in_ul:
                result.append('<ul>')
                in_ul = True
            item_text = re.sub(r'^\d+\.\s', '', stripped)
            result.append(f'<li>{item_text}</li>')
        elif stripped.startswith(('<h', '<hr', '<strong>', '<div', '<ul', '<li', '<ol')):
            if in_ul:
                result.append('</ul>')
                in_ul = False
            result.append(stripped)
        else:
            if in_ul:
                result.append('</ul>')
                in_ul = False
            result.append(f'<p>{stripped}</p>')
    if in_ul:
        result.append('</ul>')
    html = '\n'.join(result)

    # Merge split POV in TL;DR: <em>From a Travel SEO POV: </em> rest → <em>From a Travel SEO POV: rest</em>
    html = re.sub(
        r'<em>(From a Travel SEO POV:\s*)</em>\s*(.+?)(?=</li>|</p>)',
        r'<em>\1\2</em>',
        html
    )

    # Clean up empty <p></p>
    html = re.sub(r'<p>\s*</p>', '', html)

    return html


def generate_preview_html(newsletter_md: str, title: str = "Travel SEO Pulse") -> str:
    """Convert newsletter markdown to styled HTML."""
    content_html = md_to_html(newsletter_md)
    return HTML_TEMPLATE.format(title=title, content=content_html)
