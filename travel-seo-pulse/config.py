"""
Travel SEO Pulse — Configuration
"""

import os
from datetime import datetime
from pathlib import Path

# ── Load .env file if present ──────────────────────────────────
_env_file = Path(__file__).parent / ".env"
if _env_file.exists():
    for line in _env_file.read_text().strip().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, val = line.split("=", 1)
            os.environ.setdefault(key.strip(), val.strip())

# ── Anthropic API ──────────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = "claude-sonnet-4-20250514"

# ── Substack ───────────────────────────────────────────────────
# To get your cookie:
#   1. Log in to substack.com in Chrome
#   2. Open DevTools → Application → Cookies → substack.com
#   3. Copy the value of "substack.sid"
SUBSTACK_COOKIE = os.environ.get("SUBSTACK_COOKIE", "")
SUBSTACK_PUBLICATION = "jessejameswoods"  # your subdomain
SUBSTACK_USER_ID = os.environ.get("SUBSTACK_USER_ID", "")

# ── RSS Sources ────────────────────────────────────────────────
# Category → list of (name, feed_url)
RSS_SOURCES = {
    "travel_industry": [
        ("PhocusWire", "https://news.google.com/rss/search?q=site:phocuswire.com&hl=en-US&gl=US&ceid=US:en"),
        ("Skift", "https://skift.com/feed/"),
        ("Tnooz/WebInTravel", "https://www.webintravel.com/feed/"),
        ("Hospitality Net", "https://www.hospitalitynet.org/rss/news.xml"),
        # Travel Weekly removed — 403 for weeks, dead feed
    ],
    "seo_search": [
        ("Search Engine Land", "https://searchengineland.com/feed"),
        ("Search Engine Roundtable", "https://www.seroundtable.com/index.xml"),
        ("Ahrefs", "https://ahrefs.com/blog/feed/"),
        ("Moz", "https://moz.com/blog/feed"),
        ("Search Engine Journal", "https://www.searchenginejournal.com/feed/"),
        ("Growth Memo", "https://www.growth-memo.com/feed"),
        ("iPullRank", "https://ipullrank.com/feed"),
        ("DEJAN", "https://dejanmarketing.com/feed/"),
        ("SparkToro", "https://sparktoro.com/blog/feed/"),
        ("Semrush", "https://www.semrush.com/blog/feed/"),
    ],
    "ai_tech": [
        ("Google Blog", "https://blog.google/rss/"),
        ("TechCrunch AI", "https://techcrunch.com/category/artificial-intelligence/feed/"),
        ("The Verge - AI", "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml"),
        ("Anthropic Blog", "https://news.google.com/rss/search?q=site:anthropic.com&hl=en-US&gl=US&ceid=US:en"),
        ("OpenAI Blog", "https://openai.com/blog/rss.xml"),
        ("Ars Technica - AI", "https://feeds.arstechnica.com/arstechnica/technology-lab"),
    ],
}

# ── Source Authority Weights ──────────────────────────────────
# Based on 18-sample analysis of Barry Schwartz's daily SERoundtable
# recaps + Jesse's editorial judgment. Scale: 1 (nice-to-have) → 5 (must-include).
# Sources not listed default to weight 2.
SOURCE_WEIGHTS = {
    # Travel Industry — Jesse's ranking
    "PhocusWire": 5,
    "Skift": 5,
    "Tnooz/WebInTravel": 2,
    "Hospitality Net": 2,
    # SEO & Search — Barry-validated frequency + Jesse's picks
    "Search Engine Land": 5,       # Dedicated section in every Barry recap (~10 stories/day)
    "Search Engine Roundtable": 5,  # Barry's own site — the pulse of search
    "Ahrefs": 5,                    # 9 citations across 18 Barry recaps
    "Moz": 4,                       # 4 citations + Whiteboard Friday staple
    "Search Engine Journal": 4,     # Solid general SEO coverage
    "Growth Memo": 4,               # Jesse's pick — high-signal newsletter
    "iPullRank": 4,                 # Jesse's pick — practitioner-level content
    "DEJAN": 4,                     # Jesse's pick — 3 citations in Barry's AI section too
    "SparkToro": 4,                 # Jesse's pick — audience research authority
    "Semrush": 3,                   # 2 Barry citations, good data-driven posts
    # AI & LLMs — Barry-validated
    "Google Blog": 5,               # 9 citations in Barry's AI section — top source
    "TechCrunch AI": 4,             # 3 citations
    "The Verge - AI": 3,            # 2 citations
    "Anthropic Blog": 4,            # 3 citations — major AI lab
    "OpenAI Blog": 3,               # 2 citations — major AI lab
    "Ars Technica - AI": 2,         # 0 citations in Barry's AI section
}

# ── Newsletter Settings ────────────────────────────────────────
MAX_STORIES_PER_CATEGORY = {
    "travel_industry": 15,
    "seo_search": 25,
    "ai_tech": 10,
}
MAX_STORIES_PER_SOURCE = 4  # Force source diversity — no single publisher floods the pool
# Lookback: 26 hours on weekdays, 74 hours on Monday (covers Fri→Mon)
_weekday = datetime.now().weekday()
HOURS_LOOKBACK = 74 if _weekday == 0 else 26  # Monday=0
TODAY = datetime.now().strftime("%B %d, %Y")
NEWSLETTER_TITLE = f"Travel SEO Pulse — {TODAY}"
NEWSLETTER_SUBTITLE = "The daily briefing for people who care about search in travel."

# ── Email Settings ─────────────────────────────────────────────
SEND_EMAIL = True  # set to False to create draft only
AUDIENCE = "everyone"  # "everyone", "only_paid", "only_free"
