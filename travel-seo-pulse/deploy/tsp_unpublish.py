#!/usr/bin/env python3
"""Travel Search Pulse Daily - Substack unpublish CLI.

Unpublishes a published Substack post (reverts to draft) via the private
API endpoint POST {api}/posts/{id}/unpublish (precedent:
JPres-Projects/Substack-API, Sep 2025), then verifies the public URL is
gone on BOTH the substack.com URL and the www custom-domain URL.

Hardening rules (do not weaken):
- Success requires HTTP 200 AND a parseable JSON dict without an "error"
  key. A 200 with a garbage body is a FAILURE.
- NEVER retry a failed unpublish. Invisible-success-plus-retry caused the
  Apr 15 2026 duplicate-post incident. One attempt, then alarm.
- Verification follows redirects, appends a cache-buster, and requires a
  final 404 on every URL. Anything other than 404 (including 500/403) is
  a failure: only a 404 proves the post is gone.
- On any failure: ping healthchecks /fail exactly once and exit 1.

Usage (on the VPS, as the pulse user, env sourced from
/etc/travel-seo-pulse.env):

    tsp_unpublish.py list                 # read-only: published posts
    tsp_unpublish.py verify <slug>        # read-only: check URLs 404
    tsp_unpublish.py unpublish <post_id> <slug>
    tsp_unpublish.py unpublish-today      # find today's post and unpublish

Exit codes: 0 = success, 1 = failure (alarm pinged), 2 = usage/not-found.
"""
import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta

PUBLICATION = "jessejameswoods"
API_BASE = f"https://{PUBLICATION}.substack.com/api/v1"
PUBLIC_URL_TEMPLATES = (
    "https://jessejameswoods.substack.com/p/{slug}",
    "https://www.travelsearchpulse.com/p/{slug}",
)
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


class UnpublishError(Exception):
    pass


# ---------- core, dependency-injected (tested) ----------

def unpublish_post(session, api_base, post_id):
    """One attempt, no retry. 200 + sane JSON dict = success."""
    resp = session.post(f"{api_base}/posts/{post_id}/unpublish", json={})
    if resp.status_code != 200:
        raise UnpublishError(
            f"unpublish returned HTTP {resp.status_code}: {resp.text[:200]}"
        )
    try:
        body = resp.json()
    except ValueError:
        raise UnpublishError(
            f"unpublish returned 200 but body is not JSON: {resp.text[:200]}"
        )
    if not isinstance(body, dict) or body.get("error"):
        raise UnpublishError(f"unpublish returned 200 but body looks wrong: {body}")
    return body


def verify_gone(session, urls, cache_buster):
    """Every URL must return a final 404 (redirects followed, cache busted)."""
    failures = []
    for url in urls:
        sep = "&" if "?" in url else "?"
        resp = session.get(
            f"{url}{sep}cb={cache_buster}",
            allow_redirects=True,
            timeout=30,
        )
        if resp.status_code != 404:
            failures.append(f"{url} -> HTTP {resp.status_code} (expected 404)")
    if failures:
        return False, "; ".join(failures)
    return True, f"all {len(urls)} URLs return 404"


def find_todays_post(posts, today):
    """today: 'YYYY-MM-DD' string. Matches on post_date prefix."""
    for post in posts:
        if str(post.get("post_date", "")).startswith(today):
            return post
    return None


def run_unpublish(session, api_base, post_id, slug, ping_fail, log=print):
    """Orchestrate: unpublish -> verify -> alarm on failure. No retries."""
    try:
        body = unpublish_post(session, api_base, post_id)
        log(f"unpublish OK for post {post_id}: is_published="
            f"{body.get('is_published', '?')}")
    except UnpublishError as e:
        msg = f"UNPUBLISH FAILED post {post_id}: {e}. NOT retrying."
        log(msg)
        ping_fail(msg)
        return 1

    urls = [t.format(slug=slug) for t in PUBLIC_URL_TEMPLATES]
    ok, details = verify_gone(session, urls, cache_buster=str(int(time.time())))
    if not ok:
        msg = (f"UNPUBLISH VERIFICATION FAILED post {post_id}: {details}. "
               f"Post may still be live. NOT retrying.")
        log(msg)
        ping_fail(msg)
        return 1

    log(f"verification OK: {details}")
    return 0


# ---------- wiring (thin, not unit-tested) ----------

def _make_session():
    """Reuse python-substack's authenticated session and resolved
    publication URL. With the custom domain attached, the library resolves
    to https://www.travelsearchpulse.com/api/v1 (proxied by Substack); a
    hand-rolled session against the .substack.com subdomain gets 403.
    Returns (session, api_base)."""
    from substack import Api

    cookie = os.environ.get("SUBSTACK_COOKIE")
    if not cookie:
        print("SUBSTACK_COOKIE not set", file=sys.stderr)
        sys.exit(2)
    api = Api(
        publication_url=f"https://{PUBLICATION}.substack.com",
        cookies_string=f"substack.sid={cookie}",
    )
    return api._session, api.publication_url


def _ping_fail(msg):
    import requests

    hc = os.environ.get("HEALTHCHECK_URL")
    if not hc:
        print("HEALTHCHECK_URL not set; cannot alarm", file=sys.stderr)
        return
    try:
        requests.post(f"{hc.rstrip('/')}/fail", data=msg.encode(), timeout=10)
    except Exception as e:  # alarm failure must not mask the original error
        print(f"healthcheck fail-ping errored: {e}", file=sys.stderr)


def _get_published(session, api_base):
    resp = session.get(
        f"{api_base}/post_management/published",
        params={"offset": 0, "limit": 25,
                "order_by": "post_date", "order_direction": "desc"},
        timeout=30,
    )
    if resp.status_code != 200:
        print(f"list failed: HTTP {resp.status_code}: {resp.text[:200]}",
              file=sys.stderr)
        sys.exit(2)
    data = resp.json()
    return data.get("posts", data if isinstance(data, list) else [])


def _berlin_today():
    return (datetime.now(timezone.utc) + timedelta(hours=2)).strftime("%Y-%m-%d")


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    cmd = argv[1]
    session, api_base = _make_session()

    if cmd == "list":
        for p in _get_published(session, api_base):
            print(json.dumps({k: p.get(k) for k in
                              ("id", "slug", "title", "post_date", "email_sent_at")}))
        return 0

    if cmd == "verify":
        if len(argv) != 3:
            print("usage: tsp_unpublish.py verify <slug>")
            return 2
        urls = [t.format(slug=argv[2]) for t in PUBLIC_URL_TEMPLATES]
        ok, details = verify_gone(session, urls, cache_buster=str(int(time.time())))
        print(("GONE: " if ok else "STILL LIVE: ") + details)
        return 0 if ok else 1

    if cmd == "unpublish":
        if len(argv) != 4:
            print("usage: tsp_unpublish.py unpublish <post_id> <slug>")
            return 2
        return run_unpublish(session, api_base, int(argv[2]), argv[3], _ping_fail)

    if cmd == "unpublish-today":
        posts = _get_published(session, api_base)
        post = find_todays_post(posts, _berlin_today())
        if post is None:
            print(f"no published post found for {_berlin_today()}")
            return 2
        print(f"today's post: id={post['id']} slug={post['slug']} "
              f"title={post.get('title')!r} post_date={post.get('post_date')}")
        return run_unpublish(session, api_base, post["id"], post["slug"], _ping_fail)

    print(f"unknown command: {cmd}")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
