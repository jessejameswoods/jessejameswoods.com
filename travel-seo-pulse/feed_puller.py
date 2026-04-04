"""
Travel SEO Pulse — RSS Feed Puller
Pulls stories from all configured RSS sources within the lookback window.
"""

import feedparser
import urllib.request
import ssl
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from config import RSS_SOURCES, HOURS_LOOKBACK, MAX_STORIES_PER_CATEGORY, MAX_STORIES_PER_SOURCE, SOURCE_WEIGHTS
import logging
import re
from urllib.parse import urlparse

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


DEFAULT_WEIGHT = 2


@dataclass
class Story:
    title: str
    url: str
    source: str
    category: str
    published: datetime
    summary: str = ""
    weight: int = DEFAULT_WEIGHT

    def to_text(self) -> str:
        """Format for passing to the AI prompt."""
        parts = [
            f"TITLE: {self.title}",
            f"URL: {self.url}",
            f"SOURCE: {self.source}",
            f"CATEGORY: {self.category}",
            f"AUTHORITY: {self.weight}/5",
            f"PUBLISHED: {self.published.strftime('%Y-%m-%d %H:%M')}",
        ]
        if self.summary:
            parts.append(f"SUMMARY: {self.summary}")
        return "\n".join(parts)


def parse_pub_date(entry) -> datetime:
    """Extract published date from a feed entry, with fallback."""
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
    if hasattr(entry, "updated_parsed") and entry.updated_parsed:
        return datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
    # Fallback: assume it's recent
    return datetime.now(timezone.utc)


def clean_summary(entry) -> str:
    """Extract a clean text summary from the entry."""
    summary = ""
    if hasattr(entry, "summary"):
        summary = entry.summary
    elif hasattr(entry, "description"):
        summary = entry.description

    # Strip HTML tags
    summary = re.sub(r"<[^>]+>", "", summary)
    summary = re.sub(r"\s+", " ", summary).strip()

    # Truncate to ~300 chars
    if len(summary) > 300:
        summary = summary[:297] + "..."

    return summary


def resolve_google_news_url(google_url: str) -> str:
    """
    Resolve a Google News RSS redirect URL to the actual article URL.
    Google News encodes the real URL in a protobuf blob — uses googlenewsdecoder to crack it.
    """
    if "news.google.com" not in google_url:
        return google_url

    try:
        from googlenewsdecoder import gnewsdecoder
        result = gnewsdecoder(google_url)
        if result.get("status") and result.get("decoded_url"):
            return result["decoded_url"]
    except Exception as e:
        logger.warning(f"  Could not decode Google News URL: {e}")

    return google_url


def fetch_feed_lenient(feed_url: str):
    """
    Try feedparser first. If the feed has XML errors, fetch raw content,
    sanitize it, and re-parse. Handles malformed feeds like PhocusWire/SERoundtable.
    """
    feed = feedparser.parse(feed_url)
    if not feed.bozo or feed.entries:
        return feed

    # Feed is malformed — try fetching raw and sanitizing
    try:
        ctx = ssl.create_default_context()
        req = urllib.request.Request(feed_url, headers={"User-Agent": "TravelSEOPulse/1.0"})
        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
            raw = resp.read().decode("utf-8", errors="replace")

        # Strip common XML-breaking characters
        raw = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", raw)
        # Fix unescaped ampersands (common in RSS)
        raw = re.sub(r"&(?!amp;|lt;|gt;|quot;|apos;|#)", "&amp;", raw)

        feed = feedparser.parse(raw)
        if feed.entries:
            return feed
    except Exception as e:
        logger.warning(f"  Lenient fetch also failed: {e}")

    return feed


def pull_feeds() -> list[Story]:
    """Pull all RSS feeds and return stories within the lookback window."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=HOURS_LOOKBACK)
    all_stories = []

    for category, sources in RSS_SOURCES.items():
        category_stories = []
        max_stories = MAX_STORIES_PER_CATEGORY.get(category, 15)

        for source_name, feed_url in sources:
            try:
                logger.info(f"Pulling {source_name}: {feed_url}")
                feed = fetch_feed_lenient(feed_url)

                if not feed.entries:
                    logger.warning(f"  No entries for {source_name} (bozo: {feed.bozo})")
                    continue

                count = 0
                for entry in feed.entries:
                    if count >= MAX_STORIES_PER_SOURCE:
                        break

                    pub_date = parse_pub_date(entry)
                    if pub_date < cutoff:
                        continue

                    title = entry.get("title", "").strip()
                    url = entry.get("link", "").strip()

                    # Google News RSS: strip " - Source" suffix from titles
                    if "news.google.com" in feed_url and " - " in title:
                        title = title.rsplit(" - ", 1)[0].strip()

                    # Google News RSS: resolve redirect URLs to real article URLs
                    if "news.google.com" in url:
                        resolved = resolve_google_news_url(url)
                        if resolved != url:
                            logger.info(f"    Resolved: {resolved}")
                        url = resolved

                    story = Story(
                        title=title,
                        url=url,
                        source=source_name,
                        category=category,
                        published=pub_date,
                        summary=clean_summary(entry),
                        weight=SOURCE_WEIGHTS.get(source_name, DEFAULT_WEIGHT),
                    )

                    if story.title and story.url:
                        category_stories.append(story)
                        count += 1

                logger.info(f"  Found {count} recent stories from {source_name} (cap: {MAX_STORIES_PER_SOURCE})")

            except Exception as e:
                logger.error(f"  Error pulling {source_name}: {e}")

        # Sort by authority weight (high first), then recency within same weight
        category_stories.sort(key=lambda s: (s.weight, s.published), reverse=True)
        all_stories.extend(category_stories[:max_stories])

    logger.info(f"Total stories pulled: {len(all_stories)}")
    return all_stories


def stories_to_prompt_text(stories: list[Story]) -> str:
    """Format all stories into a single text block for the AI prompt."""
    blocks = []
    for i, story in enumerate(stories, 1):
        blocks.append(f"--- Story {i} ---")
        blocks.append(story.to_text())
        blocks.append("")
    return "\n".join(blocks)


if __name__ == "__main__":
    stories = pull_feeds()
    print(f"\nPulled {len(stories)} stories:\n")
    for s in stories[:5]:
        print(f"  [{s.category}] {s.source}: {s.title}")
    if len(stories) > 5:
        print(f"  ... and {len(stories) - 5} more")
