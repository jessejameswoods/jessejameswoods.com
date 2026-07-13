#!/usr/bin/env python3
"""One-off probe: does POST {api}/drafts/{id}/unpublish exist?
(The /posts/{id}/unpublish variant returned 404 on 2026-07-13.)
Single attempt, no retry. Prints status + body head."""
import os

from substack import Api

POST_ID = 206790434

api = Api(
    publication_url="https://jessejameswoods.substack.com",
    cookies_string=f"substack.sid={os.environ['SUBSTACK_COOKIE']}",
)
url = f"{api.publication_url}/drafts/{POST_ID}/unpublish"
print("probing:", url)
resp = api._session.post(url, json={})
print("status:", resp.status_code)
print("body:", resp.text[:400])
