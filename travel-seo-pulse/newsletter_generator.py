"""
Travel SEO Pulse — Newsletter Generator
Takes stories from feeds, sends them to Claude, gets back formatted newsletter.
"""

import anthropic
from config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL, TODAY, NEWSLETTER_SUBTITLE
from prompt_template import SYSTEM_PROMPT, SUMMARIZE_STORIES_PROMPT
from feed_puller import pull_feeds, stories_to_prompt_text
import logging

logger = logging.getLogger(__name__)


def generate_newsletter(stories_text: str) -> str:
    """Send stories to Claude and get back the formatted newsletter markdown."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    user_prompt = SUMMARIZE_STORIES_PROMPT.format(
        stories_text=stories_text,
        date=TODAY,
        subtitle=NEWSLETTER_SUBTITLE,
    )

    logger.info(f"Sending {len(stories_text)} chars to Claude ({ANTHROPIC_MODEL})...")

    message = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=8000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    newsletter_md = message.content[0].text
    logger.info(f"Generated newsletter: {len(newsletter_md)} chars")
    return newsletter_md


def run_generator() -> str:
    """Full pipeline: pull feeds → generate newsletter markdown."""
    # Pull feeds
    stories = pull_feeds()
    if not stories:
        logger.warning("No stories found. Skipping newsletter generation.")
        return ""

    # Format for prompt
    stories_text = stories_to_prompt_text(stories)
    logger.info(f"Formatted {len(stories)} stories into prompt ({len(stories_text)} chars)")

    # Generate via Claude
    newsletter_md = generate_newsletter(stories_text)

    return newsletter_md


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    newsletter = run_generator()
    if newsletter:
        # Save to file for review
        output_file = f"output/newsletter-{TODAY.replace(' ', '-').replace(',', '')}.md"
        import os
        os.makedirs("output", exist_ok=True)
        with open(output_file, "w") as f:
            f.write(newsletter)
        print(f"\nNewsletter saved to: {output_file}")
        print(f"\nPreview (first 500 chars):\n{newsletter[:500]}")
    else:
        print("No newsletter generated.")
