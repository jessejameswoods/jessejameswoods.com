#!/usr/bin/env python3
"""Read-only diagnostic: how does python-substack resolve the publication,
and does post_management/published work through its session?"""
import json
import os

from substack import Api

api = Api(
    publication_url="https://jessejameswoods.substack.com",
    cookies_string=f"substack.sid={os.environ['SUBSTACK_COOKIE']}",
)
print("publication_url:", api.publication_url)

try:
    posts = api.get_published_posts(limit=5)
    if isinstance(posts, dict):
        posts = posts.get("posts", posts)
    print("get_published_posts OK, count:", len(posts))
    for p in posts[:5]:
        print(json.dumps({k: p.get(k) for k in
                          ("id", "slug", "title", "post_date", "email_sent_at")}))
except Exception as e:
    print("get_published_posts FAILED:", repr(e)[:300])

# Also probe the raw endpoint through the library session for comparison
r = api._session.get(
    f"{api.publication_url}/post_management/published",
    params={"offset": 0, "limit": 3, "order_by": "post_date",
            "order_direction": "desc"},
)
print("raw via library session:", r.status_code, r.text[:120])
