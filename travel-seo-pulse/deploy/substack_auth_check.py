#!/usr/bin/env python3
"""Read-only check that the Substack cookie in /etc/travel-seo-pulse.env works.

Publishes NOTHING, creates NOTHING. Safe to run on a day when a draft
already exists. Use this instead of re-running the pipeline after a cookie
refresh: re-running main.py creates a second draft and can double-send.

Exit codes: 0 cookie works (can read posts), 1 auth failed, 2 config error.

Usage on the VPS (as root):
    set -a; . /etc/travel-seo-pulse.env; set +a
    /opt/travel-seo-pulse/.venv/bin/python /opt/travel-seo-pulse/travel-seo-pulse/deploy/substack_auth_check.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))


def main() -> int:
    try:
        from substack_publisher import _get_api
    except Exception as exc:  # pragma: no cover - import environment problems
        print(f"CONFIG ERROR: cannot import substack_publisher: {exc!r}")
        return 2
    try:
        api = _get_api()
    except ValueError as exc:
        print(f"CONFIG ERROR: {exc}")
        return 2
    try:
        posts = api.get_published_posts(offset=0, limit=3)
    except Exception as exc:
        print(f"AUTH FAILED: {exc!r}")
        print("Refresh SUBSTACK_COOKIE per deploy/README.md (copy the full cookie header).")
        return 1
    titles = []
    for p in posts if isinstance(posts, list) else []:
        if isinstance(p, dict):
            titles.append(p.get("title") or p.get("draft_title") or "?")
    print(f"OK: cookie authenticates. Latest published: {titles[:3]}")
    print("Note: this proves READ access. Publish+send is gated separately by")
    print("Substack; a fresh cookie (full header) is the known fix for that gate.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
