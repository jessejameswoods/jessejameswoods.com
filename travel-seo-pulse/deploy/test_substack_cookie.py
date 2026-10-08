"""Tests for Substack cookie handling in substack_publisher.py (TDD).

Why: on 2026-10-08 Substack refused the publish+send call with
"For your security, please sign out and sign back in" on a 177-day-old
session, while reads and draft creation still worked. The documented
refresh (README) copies the FULL cookie header from DevTools, but the
code only ever sent `substack.sid=<value>`. The env must accept either
form so a refresh that follows the README cannot produce a broken
`substack.sid=substack.sid=...` string.
"""
from substack_publisher import _cookies_string


def test_bare_sid_value_is_wrapped():
    assert _cookies_string("s%3Aabc.def") == "substack.sid=s%3Aabc.def"


def test_full_cookie_header_is_passed_through_untouched():
    full = "substack.sid=s%3Aabc.def; substack.lli=1759900000; ab_experiment_sampled=false"
    assert _cookies_string(full) == full


def test_single_named_sid_cookie_is_passed_through():
    assert _cookies_string("substack.sid=s%3Aabc.def") == "substack.sid=s%3Aabc.def"


def test_surrounding_whitespace_and_quotes_are_stripped():
    assert _cookies_string('  "substack.sid=s%3Aabc; x=1"  ') == "substack.sid=s%3Aabc; x=1"
    assert _cookies_string(" s%3Aabc ") == "substack.sid=s%3Aabc"


def test_empty_value_raises_a_clear_error():
    import pytest
    with pytest.raises(ValueError, match="SUBSTACK_COOKIE"):
        _cookies_string("")
