"""Tests for cross-day story dedup in feed_puller.py (TDD).

Incident 2026-07-14: 5 cross-day duplicate stories since April, all with
DIFFERENT URLs (publishers re-post under new URLs with fresh pubDates).
Fix: the archive markdown on disk is the memory - filter candidates that
match a recent brief by URL or by normalized-title containment.
"""
from datetime import datetime, timezone

from feed_puller import (
    normalize_title,
    load_seen_stories,
    is_already_covered,
    MIN_TITLE_MATCH_LEN,
)

MD = """# Travel Search Pulse Daily - July 13, 2026
## Travel Industry
- **[AI is confidently wrong about your hotel, and the guest arrives believing it](https://www.hospitalitynet.org/opinion/4133441/ai-is-confidently-wrong)** — *Hospitality Net* · summary.
- **[Hopper Settles With the FTC Over Practices Expedia Called Out in 2023](https://skift.com/2026/07/10/hopper-settles)** — *Skift* · summary.
- **[Short](https://example.com/short)** — too short to title-match.
"""


def test_normalize_title():
    assert normalize_title("AI Is Confidently Wrong, About Your Hotel!") == \
        "ai is confidently wrong about your hotel"


def make_output(tmp_path, name="newsletter-2026-07-13.md", text=MD):
    d = tmp_path / "output"
    d.mkdir(exist_ok=True)
    (d / name).write_text(text, encoding="utf-8")
    return d


def test_load_seen_stories_parses_archive_markdown(tmp_path):
    d = make_output(tmp_path)
    now = datetime(2026, 7, 14, tzinfo=timezone.utc)
    urls, titles = load_seen_stories(str(d), days=14, now=now)
    assert "https://www.hospitalitynet.org/opinion/4133441/ai-is-confidently-wrong" in urls
    assert "ai is confidently wrong about your hotel and the guest arrives believing it" in titles
    # short titles never enter the title set (length guard)
    assert "short" not in titles
    # but their URLs still count
    assert "https://example.com/short" in urls


def test_load_seen_stories_respects_day_window(tmp_path):
    d = make_output(tmp_path, name="newsletter-2026-06-01.md")
    now = datetime(2026, 7, 14, tzinfo=timezone.utc)
    urls, titles = load_seen_stories(str(d), days=14, now=now)
    assert urls == set() and titles == set()


def test_load_seen_stories_survives_missing_dir(tmp_path):
    urls, titles = load_seen_stories(str(tmp_path / "nope"), days=14)
    assert urls == set() and titles == set()


def test_same_url_is_covered():
    assert is_already_covered(
        "Whatever Title", "https://a.com/x",
        {"https://a.com/x"}, set())


# ---- the five REAL duplicate pairs from the live archive ----

REAL_PAIRS = [
    # (title already covered,                                        new candidate title)
    ("AI is confidently wrong about your hotel, and the guest arrives believing it",
     "AI Is Confidently Wrong About Your Hotel and the Guest Arrives Believing It: The Org Chart Is a Revenue Problem"),
    ("Shorter, Focused Content Wins In ChatGPT",
     "Shorter Focused Content Wins in ChatGPT"),
    ("Google Search Now Powered By Gemini 3.5 Flash",
     "Google Search now powered by Gemini 3.5 Flash"),
    ("Why Proprietary Data Is Your Most Defensible AI Citation Asset",
     "Why proprietary data is your most defensible AI citation asset"),
    ("Why Most Original Data Never Gets Cited",
     "Why most original data never gets cited"),
]


def test_all_five_real_incident_pairs_are_caught():
    for seen_title, new_title in REAL_PAIRS:
        seen_titles = set()
        nt = normalize_title(seen_title)
        assert len(nt) >= MIN_TITLE_MATCH_LEN, seen_title
        seen_titles.add(nt)
        assert is_already_covered(new_title, "https://different.url/each-time",
                                  set(), seen_titles), new_title


def test_unrelated_story_passes():
    seen = {normalize_title(
        "AI is confidently wrong about your hotel, and the guest arrives believing it")}
    assert not is_already_covered(
        "Google Updates Its Crawler Documentation for Travel Sites",
        "https://new.url/y", set(), seen)


def test_short_titles_never_title_match():
    # generic short titles must not false-positive via containment
    seen = {normalize_title("Google Search Now Powered By Gemini 3.5 Flash")}
    assert not is_already_covered("Google Search", "https://u/1", set(), seen)
