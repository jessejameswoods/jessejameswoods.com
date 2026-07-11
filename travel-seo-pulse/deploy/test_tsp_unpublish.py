"""Tests for tsp_unpublish.py - written before the implementation (TDD).

Encodes the Phase 2 pre-mortem hardening:
- success = HTTP 200 AND parseable dict body (a 200 with garbage is a failure)
- NO retry on any failure (Apr 15 lesson: invisible success + retry = duplicates)
- verification follows redirects, appends a cache-buster, requires 404 on
  BOTH the substack.com URL and the www custom-domain URL
- on verification failure: ping healthchecks /fail exactly once, do not retry
"""
import pytest

from tsp_unpublish import (
    UnpublishError,
    unpublish_post,
    verify_gone,
    find_todays_post,
    run_unpublish,
)


class FakeResponse:
    def __init__(self, status_code=200, json_data=None, text=""):
        self.status_code = status_code
        self._json = json_data
        self.text = text or (str(json_data) if json_data is not None else "")

    def json(self):
        if self._json is None:
            raise ValueError("no json")
        return self._json


class FakeSession:
    """Records calls; returns queued responses."""

    def __init__(self, post_responses=None, get_responses=None):
        self.post_calls = []
        self.get_calls = []
        self._post_responses = list(post_responses or [])
        self._get_responses = list(get_responses or [])

    def post(self, url, **kwargs):
        self.post_calls.append((url, kwargs))
        return self._post_responses.pop(0)

    def get(self, url, **kwargs):
        self.get_calls.append((url, kwargs))
        if self._get_responses:
            return self._get_responses.pop(0)
        return FakeResponse(404)


API = "https://jessejameswoods.substack.com/api/v1"


# ---- unpublish_post ----

def test_unpublish_success_200_with_dict_body():
    s = FakeSession(post_responses=[FakeResponse(200, {"id": 123, "is_published": False})])
    body = unpublish_post(s, API, 123)
    assert body["id"] == 123
    assert s.post_calls[0][0] == f"{API}/posts/123/unpublish"
    assert s.post_calls[0][1].get("json") == {}


def test_unpublish_200_with_unparseable_body_is_failure():
    s = FakeSession(post_responses=[FakeResponse(200, None, text="<html>login</html>")])
    with pytest.raises(UnpublishError):
        unpublish_post(s, API, 123)


def test_unpublish_200_with_error_key_is_failure():
    s = FakeSession(post_responses=[FakeResponse(200, {"error": "nope"})])
    with pytest.raises(UnpublishError):
        unpublish_post(s, API, 123)


def test_unpublish_non_200_is_failure_and_never_retries():
    s = FakeSession(post_responses=[FakeResponse(401, {"error": "auth"})])
    with pytest.raises(UnpublishError):
        unpublish_post(s, API, 123)
    assert len(s.post_calls) == 1  # exactly one attempt, no retry


# ---- verify_gone ----

def test_verify_gone_passes_when_all_urls_404():
    s = FakeSession(get_responses=[FakeResponse(404), FakeResponse(404)])
    ok, details = verify_gone(s, ["https://a/p/x", "https://b/p/x"], cache_buster="cb123")
    assert ok is True
    # cache buster appended and redirects followed on every check
    for url, kwargs in s.get_calls:
        assert "cb123" in url
        assert kwargs.get("allow_redirects") is True


def test_verify_gone_fails_if_any_url_still_live():
    s = FakeSession(get_responses=[FakeResponse(404), FakeResponse(200)])
    ok, details = verify_gone(s, ["https://a/p/x", "https://b/p/x"], cache_buster="cb")
    assert ok is False
    assert "https://b/p/x" in details


def test_verify_gone_treats_non_404_non_200_as_failure():
    # a 403 or 500 is NOT proof the post is gone
    s = FakeSession(get_responses=[FakeResponse(500), FakeResponse(404)])
    ok, details = verify_gone(s, ["https://a/p/x", "https://b/p/x"], cache_buster="cb")
    assert ok is False


# ---- find_todays_post ----

POSTS = [
    {"id": 2, "slug": "brief-jul-13", "post_date": "2026-07-13T04:03:11.000Z", "title": "Travel Search Pulse Daily - July 13, 2026"},
    {"id": 1, "slug": "brief-jul-10", "post_date": "2026-07-10T04:02:00.000Z", "title": "Travel SEO Pulse - July 10, 2026"},
]


def test_find_todays_post_matches_date():
    post = find_todays_post(POSTS, today="2026-07-13")
    assert post["id"] == 2


def test_find_todays_post_none_when_absent():
    assert find_todays_post(POSTS, today="2026-07-14") is None


# ---- run_unpublish orchestration ----

def test_run_unpublish_happy_path_no_healthcheck_ping():
    pings = []
    s = FakeSession(
        post_responses=[FakeResponse(200, {"id": 5, "is_published": False})],
        get_responses=[FakeResponse(404), FakeResponse(404)],
    )
    code = run_unpublish(
        s, API, post_id=5, slug="x",
        ping_fail=lambda msg: pings.append(msg),
    )
    assert code == 0
    assert pings == []


def test_run_unpublish_verify_failure_pings_fail_once_and_no_retry():
    pings = []
    s = FakeSession(
        post_responses=[FakeResponse(200, {"id": 5, "is_published": False})],
        get_responses=[FakeResponse(200), FakeResponse(404)],
    )
    code = run_unpublish(
        s, API, post_id=5, slug="x",
        ping_fail=lambda msg: pings.append(msg),
    )
    assert code == 1
    assert len(pings) == 1
    assert len(s.post_calls) == 1  # the unpublish was NOT retried


def test_run_unpublish_api_failure_pings_fail_and_skips_verify():
    pings = []
    s = FakeSession(post_responses=[FakeResponse(401, {"error": "auth"})])
    code = run_unpublish(
        s, API, post_id=5, slug="x",
        ping_fail=lambda msg: pings.append(msg),
    )
    assert code == 1
    assert len(pings) == 1
    assert len(s.get_calls) == 0
