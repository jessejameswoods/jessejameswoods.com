#!/usr/bin/env python3
"""
Travel SEO Pulse — Main Runner
Full pipeline: pull feeds → generate newsletter → publish to Substack.

Usage:
  python main.py                # Full run: generate + publish + send email
  python main.py --draft        # Generate + create Substack draft (no send)
  python main.py --preview      # Generate + save to file only (no Substack)
  python main.py --dry-run      # Pull feeds only, show what would be included
"""

import argparse
import logging
import os
import sys
from datetime import datetime

from config import NEWSLETTER_TITLE, NEWSLETTER_SUBTITLE, ANTHROPIC_API_KEY, SUBSTACK_COOKIE
from feed_puller import pull_feeds, stories_to_prompt_text
from newsletter_generator import generate_newsletter
from html_preview import generate_preview_html
from substack_publisher import publish_to_substack, publish_draft_only

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("travel_seo_pulse.log"),
    ],
)
logger = logging.getLogger(__name__)


def check_config(mode: str) -> bool:
    """Verify required config is set for the given mode."""
    if mode in ("full", "draft"):
        if not ANTHROPIC_API_KEY:
            logger.error("ANTHROPIC_API_KEY not set. Export it: export ANTHROPIC_API_KEY='sk-...'")
            return False
        if not SUBSTACK_COOKIE:
            logger.error("SUBSTACK_COOKIE not set. Export it: export SUBSTACK_COOKIE='...'")
            return False
    elif mode == "preview":
        if not ANTHROPIC_API_KEY:
            logger.error("ANTHROPIC_API_KEY not set.")
            return False
    return True


def main():
    parser = argparse.ArgumentParser(description="Travel SEO Pulse Newsletter Generator")
    parser.add_argument("--draft", action="store_true", help="Create Substack draft only, don't send email")
    parser.add_argument("--preview", action="store_true", help="Generate and save to file only")
    parser.add_argument("--dry-run", action="store_true", help="Pull feeds only, show what would be included")
    args = parser.parse_args()

    # Determine mode
    if args.dry_run:
        mode = "dry-run"
    elif args.preview:
        mode = "preview"
    elif args.draft:
        mode = "draft"
    else:
        mode = "full"

    logger.info(f"=== Travel SEO Pulse — {mode.upper()} mode ===")
    logger.info(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    # Config check
    if not check_config(mode):
        sys.exit(1)

    # ── Step 1: Pull feeds ──
    logger.info("Step 1: Pulling RSS feeds...")
    stories = pull_feeds()

    if not stories:
        logger.error(
            "No stories found in any feed. This is a failure, not a no-op - "
            "feeds are likely blocked (bot detection, 403s) or recency window is wrong. "
            "Exiting non-zero so the runtime alerts instead of silently claiming success."
        )
        sys.exit(1)

    logger.info(f"Pulled {len(stories)} stories across {len(set(s.category for s in stories))} categories")

    # Category breakdown
    for cat in sorted(set(s.category for s in stories)):
        cat_count = len([s for s in stories if s.category == cat])
        logger.info(f"  {cat}: {cat_count} stories")

    if mode == "dry-run":
        print(f"\n{'='*60}")
        print(f"DRY RUN — {len(stories)} stories would be included:")
        print(f"{'='*60}\n")
        for s in stories:
            print(f"  [{s.category}] {s.source}: {s.title}")
            print(f"    {s.url}")
            print()
        return

    # ── Step 2: Generate newsletter ──
    logger.info("Step 2: Generating newsletter via Claude...")
    stories_text = stories_to_prompt_text(stories)
    newsletter_md = generate_newsletter(stories_text)

    if not newsletter_md:
        logger.error("Newsletter generation returned empty. Aborting.")
        sys.exit(1)

    # Save to file regardless of mode
    os.makedirs("output", exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    output_file = f"output/newsletter-{date_str}.md"
    with open(output_file, "w") as f:
        f.write(newsletter_md)
    logger.info(f"Newsletter saved to: {output_file}")

    # Generate HTML preview
    html_file = f"output/newsletter-{date_str}.html"
    preview_html = generate_preview_html(newsletter_md, NEWSLETTER_TITLE)
    with open(html_file, "w") as f:
        f.write(preview_html)
    # Also save as preview.html for easy opening
    with open("output/preview.html", "w") as f:
        f.write(preview_html)
    logger.info(f"HTML preview saved to: {html_file}")

    if mode == "preview":
        print(f"\n{'='*60}")
        print(f"PREVIEW — Newsletter saved to {output_file}")
        print(f"{'='*60}\n")
        print(newsletter_md[:1000])
        if len(newsletter_md) > 1000:
            print(f"\n... ({len(newsletter_md)} total chars)")
        return

    # ── Step 3: Publish to Substack ──
    if mode == "draft":
        logger.info("Step 3: Creating Substack draft...")
        result = publish_draft_only(NEWSLETTER_TITLE, NEWSLETTER_SUBTITLE, newsletter_md)
    else:
        logger.info("Step 3: Publishing to Substack + sending email...")
        result = publish_to_substack(NEWSLETTER_TITLE, NEWSLETTER_SUBTITLE, newsletter_md)

    if "error" in result:
        logger.error(f"Publish failed: {result['error']}")
        logger.info(f"Newsletter is still saved at: {output_file}")
        sys.exit(1)

    logger.info(f"Result: {result}")

    if result.get("url"):
        print(f"\n{'='*60}")
        print(f"PUBLISHED: {result['url']}")
        print(f"{'='*60}\n")
    else:
        print(f"\nDraft created: ID {result.get('draft_id')}")

    logger.info("=== Travel SEO Pulse — Complete ===")


if __name__ == "__main__":
    main()
