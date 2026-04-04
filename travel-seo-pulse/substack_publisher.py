"""
Travel SEO Pulse — Substack Publisher
Uses python-substack to create a draft, then publish + send email.
"""

import logging
import re
from config import SUBSTACK_COOKIE, SUBSTACK_PUBLICATION, SUBSTACK_USER_ID, SEND_EMAIL, AUDIENCE

logger = logging.getLogger(__name__)


def _prepare_markdown_for_substack(markdown_content: str) -> str:
    """
    Clean up newsletter markdown for Substack publishing.

    - Strips the duplicate title/subtitle/byline block (Substack renders its own)
    - Adds blank lines between story entries for visual breathing room
    """
    lines = markdown_content.split('\n')

    # Strip everything before the first "## " section header or "---" after the byline
    # The pattern is: # Title, *subtitle*, **By Jesse James Woods**, ---, content...
    # We want to skip the title block and start from "## The Briefing TL;DR"
    start_idx = 0
    for i, line in enumerate(lines):
        if line.startswith('## '):
            start_idx = i
            break

    cleaned = '\n'.join(lines[start_idx:])

    # Strip the footer (duplicate of what Substack shows)
    cleaned = re.sub(
        r'\n\*Travel SEO Pulse by Jesse James Woods.*$',
        '',
        cleaned,
        flags=re.DOTALL
    )

    return cleaned.strip()


def _get_api():
    """Initialize the Substack API with cookie auth."""
    from substack import Api

    api = Api(
        publication_url=f"https://{SUBSTACK_PUBLICATION}.substack.com",
        cookies_string=f"substack.sid={SUBSTACK_COOKIE}",
    )
    return api


def _markdown_to_draft_body(title: str, subtitle: str, markdown_content: str) -> dict:
    """Build the draft body payload from markdown content."""
    # Convert markdown to a simple paragraph-based body for Substack's API
    # Substack expects a specific JSON body format for drafts
    return {
        "draft_title": title,
        "draft_subtitle": subtitle,
        "draft_body": _prepare_markdown_for_substack(markdown_content),
        "draft_bylines": [{"id": int(SUBSTACK_USER_ID), "is_guest": False}],
        "type": "newsletter",
        "audience": AUDIENCE,
    }


def publish_to_substack(title: str, subtitle: str, markdown_content: str, draft_only: bool = False) -> dict:
    """
    Create a Substack post from markdown and publish it.

    Args:
        draft_only: If True, create draft but don't publish or send email.

    Returns dict with post info (id, url, etc.) or error details.
    """
    try:
        from substack import Api
    except ImportError:
        logger.error(
            "python-substack not installed. Run: pip install python-substack"
        )
        return {"error": "python-substack not installed"}

    if not SUBSTACK_COOKIE:
        logger.error("SUBSTACK_COOKIE not set. Cannot publish.")
        return {"error": "SUBSTACK_COOKIE not set"}

    try:
        api = _get_api()

        # Create draft body
        body = _markdown_to_draft_body(title, subtitle, markdown_content)

        # Create draft
        logger.info("Creating Substack draft...")
        draft_response = api.post_draft(body)
        draft_id = draft_response.get("id")
        logger.info(f"Draft created: ID {draft_id}")

        if draft_only or not SEND_EMAIL:
            logger.info("Stopping at draft (draft_only or SEND_EMAIL=False).")
            return {"status": "draft", "draft_id": draft_id, "response": draft_response}

        # Prepublish (required step)
        logger.info("Prepublishing draft...")
        api.prepublish_draft(draft_id)

        # Publish + send email
        logger.info(f"Publishing + sending email (audience: {AUDIENCE})...")
        publish_response = api.publish_draft(
            draft_id,
            send=True,
            share_automatically=False,
        )

        post_url = publish_response.get("canonical_url", "")
        logger.info(f"Published! URL: {post_url}")

        return {
            "status": "published",
            "draft_id": draft_id,
            "url": post_url,
            "response": publish_response,
        }

    except Exception as e:
        logger.error(f"Substack publish error: {e}")
        return {"error": str(e)}


def publish_draft_only(title: str, subtitle: str, markdown_content: str) -> dict:
    """Create a draft without publishing — useful for review."""
    return publish_to_substack(title, subtitle, markdown_content, draft_only=True)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    print("Substack publisher module loaded.")
    print(f"Publication: {SUBSTACK_PUBLICATION}")
    print(f"Cookie set: {'Yes' if SUBSTACK_COOKIE else 'No'}")
    print(f"User ID: {SUBSTACK_USER_ID}")
    print(f"Send email: {SEND_EMAIL}")
