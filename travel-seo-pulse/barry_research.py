"""
Barry Schwartz Daily Recap — Source Citation Extractor v2
Fetches 20 recaps and tallies which sources appear in each category section.

Structure discovered: Under "Other Great Search Stories:" the content is:
  CategoryName\n\n\tTitle, SourceName\n\tTitle, SourceName\n\n\nNextCategory
"""
import urllib.request
import re
import ssl
import json
from collections import defaultdict

ctx = ssl.create_default_context()

RECAP_URLS = [
    ("2026-03-27", "https://www.seroundtable.com/recap-03-27-2026-41122.html"),
    ("2026-03-26", "https://www.seroundtable.com/recap-03-26-2026-41116.html"),
    ("2026-03-25", "https://www.seroundtable.com/recap-03-25-2026-41111.html"),
    ("2026-03-24", "https://www.seroundtable.com/recap-03-24-2026-41104.html"),
    ("2026-03-23", "https://www.seroundtable.com/recap-03-23-2026-41098.html"),
    ("2026-03-19", "https://www.seroundtable.com/recap-03-19-2026-41081.html"),
    ("2026-03-10", "https://www.seroundtable.com/recap-03-10-2026-41054.html"),
    ("2026-03-09", "https://www.seroundtable.com/recap-03-09-2026-41047.html"),
    ("2026-03-05", "https://www.seroundtable.com/recap-03-05-2026-41037.html"),
    ("2026-03-04", "https://www.seroundtable.com/recap-03-04-2026-41023.html"),
    ("2026-03-03", "https://www.seroundtable.com/recap-03-03-2026-41020.html"),
    ("2026-03-02", "https://www.seroundtable.com/recap-03-02-2026-41013.html"),
    ("2026-02-24", "https://www.seroundtable.com/recap-02-24-2026-40981.html"),
    ("2026-02-23", "https://www.seroundtable.com/recap-02-23-2026-40977.html"),
    ("2026-02-20", "https://www.seroundtable.com/recap-02-20-2026-40967.html"),
    ("2026-02-19", "https://www.seroundtable.com/recap-02-19-2026-40959.html"),
    ("2026-02-09", "https://www.seroundtable.com/recap-02-09-2026-40898.html"),
    ("2026-02-02", "https://www.seroundtable.com/recap-02-02-2026-40859.html"),
    ("2026-01-27", "https://www.seroundtable.com/recap-01-27-2026-40826.html"),
    ("2026-01-22", "https://www.seroundtable.com/recap-01-22-2026-40802.html"),
]


def fetch_page(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    })
    with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
        return resp.read().decode("utf-8", errors="replace")


def extract_json_ld_text(html):
    """
    Barry's recap content is cleanly available in the JSON-LD articleBody.
    This gives us clean text without HTML parsing issues.
    """
    match = re.search(r'"articleBody"\s*:\s*"(.*?)"(?=\s*,\s*"author")', html, re.DOTALL)
    if match:
        text = match.group(1)
        # Unescape JSON string
        text = text.replace('\\r\\n', '\n').replace('\\n', '\n').replace('\\t', '\t')
        text = text.replace('\\/', '/').replace('\\"', '"')
        text = text.replace('&mdash;', '—').replace('&amp;', '&')
        return text
    return None


def parse_categories_from_text(text):
    """
    Parse the 'Other Great Search Stories:' section from the articleBody text.
    
    Format:
    Other Great Search Stories:
    CategoryName
    
    \tTitle, SourceName
    \tTitle, SourceName
    
    
    NextCategory
    """
    results = {}
    
    # Find "Other Great Search Stories:" section
    marker = "Other Great Search Stories:"
    idx = text.find(marker)
    if idx < 0:
        return results
    
    section_text = text[idx + len(marker):]
    
    # Cut off at "Feedback:" or "Have feedback"
    for end_marker in ["Feedback:", "Have feedback"]:
        end_idx = section_text.find(end_marker)
        if end_idx >= 0:
            section_text = section_text[:end_idx]
    
    # Split into lines
    lines = section_text.split('\n')
    
    current_category = None
    
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        
        # A category header is a non-tab line that doesn't contain a comma
        # (story entries are tab-indented and have "Title, Source" format)
        if not line.startswith('\t') and not line.startswith('  ') and ',' not in stripped:
            # This looks like a category header
            current_category = stripped
            if current_category not in results:
                results[current_category] = []
        elif current_category and (',' in stripped):
            # This is a story entry: "Title, Source Name"
            # The source is after the LAST comma
            parts = stripped.rsplit(',', 1)
            if len(parts) == 2:
                source = parts[1].strip()
                if source:
                    results[current_category].append(source)
    
    return results


def also_parse_sel_stories(text):
    """
    Also extract Search Engine Land stories section — Barry lists these separately.
    They appear under "Search Engine Land Stories:" header.
    """
    results = {}
    marker = "Search Engine Land Stories:"
    idx = text.find(marker)
    if idx < 0:
        return results
    
    end_marker = "Other Great Search Stories:"
    end_idx = text.find(end_marker, idx)
    if end_idx < 0:
        end_idx = len(text)
    
    section = text[idx + len(marker):end_idx]
    lines = section.strip().split('\n')
    count = 0
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith('#'):
            count += 1
    
    if count > 0:
        results["Search Engine Land (dedicated section)"] = count
    
    return results


def normalize_section(name):
    name_lower = name.lower().strip()
    if name_lower in ("seo",):
        return "SEO"
    elif "ai" in name_lower and "llm" in name_lower:
        return "AI & LLMs"
    elif name_lower == "ai":
        return "AI & LLMs"
    elif "ads" in name_lower or "ppc" in name_lower:
        return "Google Ads / PPC"
    elif "local" in name_lower or "maps" in name_lower:
        return "Local & Maps"
    elif "social" in name_lower:
        return "Social"
    elif "industry" in name_lower or "business" in name_lower:
        return "Industry & Business"
    elif "link" in name_lower or "content" in name_lower:
        return "Links & Content Marketing"
    elif "feature" in name_lower:
        return "Search Features"
    elif "other" in name_lower:
        return "Other Search"
    else:
        return name


def main():
    seo_sources = defaultdict(int)
    ai_sources = defaultdict(int)
    all_sections_seen = defaultdict(int)
    all_source_tallies = defaultdict(lambda: defaultdict(int))  # section -> source -> count
    per_recap = {}
    sel_story_counts = []
    
    success = 0
    fail = 0
    
    for date, url in RECAP_URLS:
        print(f"Fetching {date}... ", end="", flush=True)
        try:
            html = fetch_page(url)
            text = extract_json_ld_text(html)
            
            if not text:
                print(f"NO JSON-LD articleBody found")
                fail += 1
                continue
            
            categories = parse_categories_from_text(text)
            sel_data = also_parse_sel_stories(text)
            
            if not categories:
                print(f"NO CATEGORIES PARSED from articleBody (text length: {len(text)})")
                # Debug: print first 500 chars
                print(f"  First 300 chars: {text[:300]}")
                fail += 1
                continue
            
            recap_data = {}
            for cat_name, sources in categories.items():
                normalized = normalize_section(cat_name)
                all_sections_seen[normalized] += 1
                recap_data[normalized] = sources
                
                for s in sources:
                    all_source_tallies[normalized][s] += 1
                
                if normalized == "SEO":
                    for s in sources:
                        seo_sources[s] += 1
                elif normalized == "AI & LLMs":
                    for s in sources:
                        ai_sources[s] += 1
            
            if sel_data:
                count = list(sel_data.values())[0]
                sel_story_counts.append(count)
            
            per_recap[date] = recap_data
            cat_summary = {k: len(v) for k, v in recap_data.items()}
            print(f"OK — {cat_summary}")
            success += 1
            
        except Exception as e:
            print(f"ERROR: {e}")
            fail += 1
    
    print(f"\n{'='*70}")
    print(f"RESULTS: {success} fetched, {fail} failed out of {len(RECAP_URLS)}")
    
    print(f"\nSections seen across all recaps:")
    for section, count in sorted(all_sections_seen.items(), key=lambda x: -x[1]):
        print(f"  {section}: appears in {count}/{success} recaps")
    
    if sel_story_counts:
        print(f"\nSearch Engine Land dedicated section: avg {sum(sel_story_counts)/len(sel_story_counts):.1f} stories/recap")
    
    print(f"\n{'='*70}")
    print(f"SEO SECTION — Source frequency (across {all_sections_seen.get('SEO', 0)} recaps):")
    print(f"{'='*70}")
    for source, count in sorted(seo_sources.items(), key=lambda x: -x[1]):
        print(f"  {count:3d}x  {source}")
    
    print(f"\n{'='*70}")
    print(f"AI & LLMs SECTION — Source frequency (across {all_sections_seen.get('AI & LLMs', 0)} recaps):")
    print(f"{'='*70}")
    for source, count in sorted(ai_sources.items(), key=lambda x: -x[1]):
        print(f"  {count:3d}x  {source}")
    
    # Also print all other sections
    for section in sorted(all_source_tallies.keys()):
        if section not in ("SEO", "AI & LLMs"):
            print(f"\n{'='*70}")
            print(f"{section} — Source frequency:")
            print(f"{'='*70}")
            for source, count in sorted(all_source_tallies[section].items(), key=lambda x: -x[1])[:15]:
                print(f"  {count:3d}x  {source}")
    
    # Save to JSON
    output = {
        "meta": {
            "total_recaps": len(RECAP_URLS),
            "successful": success,
            "failed": fail,
        },
        "seo_sources": dict(sorted(seo_sources.items(), key=lambda x: -x[1])),
        "ai_sources": dict(sorted(ai_sources.items(), key=lambda x: -x[1])),
        "sections_seen": dict(all_sections_seen),
        "all_section_tallies": {k: dict(sorted(v.items(), key=lambda x: -x[1])) for k, v in all_source_tallies.items()},
        "per_recap": per_recap,
    }
    outpath = "/Users/jessejameswoods/Projects/jessejameswoods.com/travel-seo-pulse/barry_research_results.json"
    with open(outpath, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nRaw data saved to {outpath}")


if __name__ == "__main__":
    main()
