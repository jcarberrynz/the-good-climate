#!/usr/bin/env python3
"""
Fetches recent "good news" stories about the environment, emissions
reduction, sustainability, climate tech, the energy transition, and
Aotearoa New Zealand, and writes them to data/stories.json for the
static site to display, along with a photo scraped from each linked
article where one is available.

Uses Google News RSS search (no API key required). Runs on a schedule
via .github/workflows/update-news.yml (every 3 days), and can also be
run locally: `python3 scripts/fetch_news.py`
"""

import json
import re
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from html import unescape

# Search topics, each biased toward positive framing via included keywords.
# Google News RSS: https://news.google.com/rss/search?q=<query>
QUERIES = [
    {
        "category": "Emissions Reduction",
        "q": '(emissions OR "carbon emissions") (reduction OR falls OR drops OR cuts OR record low) '
             '(climate OR carbon) -war -died -death',
    },
    {
        "category": "Energy Transition",
        "q": '(solar OR wind OR "renewable energy" OR "clean energy" OR battery storage) '
             '(record OR milestone OR breakthrough OR surge OR expansion OR growth) -war -died -death',
    },
    {
        "category": "Sustainability",
        "q": '(sustainability OR recycling OR "circular economy" OR conservation) '
             '(breakthrough OR success OR progress OR milestone OR initiative) -war -died -death',
    },
    {
        "category": "Environment",
        "q": '(reforestation OR biodiversity OR wildlife OR ocean OR coral reef OR rewilding) '
             '(recovery OR restored OR protected OR rebound OR success) -war -died -death',
    },
    {
        "category": "Climate Tech",
        "q": '("climate tech" OR "carbon capture" OR "clean tech" OR "green hydrogen" OR "battery breakthrough") '
             '(breakthrough OR launches OR unveils OR milestone OR funding OR pilot) -war -died -death',
    },
    {
        "category": "New Zealand",
        "q": '("New Zealand" OR Aotearoa OR NZ) (climate OR conservation OR renewable OR predator-free OR native bush OR wildlife) '
             '(success OR recovery OR milestone OR restored OR progress OR record) -war -died -death',
    },
]

# Words that suggest a story is NOT "good news" even if it matched the query.
NEGATIVE_SIGNAL_WORDS = [
    "disaster", "collapse", "crisis", "extinct", "dying", "dead", "death",
    "war", "killed", "layoffs", "bankrupt", "shutdown", "scandal", "lawsuit",
    "denounce", "protest", "fails", "failure", "worst", "record heat",
    "wildfire kills", "flood kills", "hurricane", "drought crisis",
]

MAX_PER_CATEGORY = 4
TARGET_TOTAL_MIN = 10
TARGET_TOTAL_MAX = 20
TARGET_DEFAULT = 15  # aim for roughly this many stories when enough are available
STORIES_PATH = "data/stories.json"

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; GoodEnvNewsBot/1.0)"}

# Regexes for pulling a preview image out of an article page's <head>.
OG_IMAGE_RE = re.compile(
    r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', re.IGNORECASE
)
TWITTER_IMAGE_RE = re.compile(
    r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']', re.IGNORECASE
)


def fetch_article_image(link: str):
    """Best-effort scrape of the og:image (or twitter:image) from an article
    page. Returns None on any failure — a missing photo just falls back to
    the site's category-themed placeholder tile, so failures here are fine."""
    try:
        req = urllib.request.Request(link, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=8) as resp:
            # Only read the first chunk; the <head> with og:image is near the top.
            html = resp.read(200_000).decode("utf-8", errors="ignore")
        match = OG_IMAGE_RE.search(html) or TWITTER_IMAGE_RE.search(html)
        if match:
            return unescape(match.group(1).strip())
    except Exception:
        pass
    return None


def fetch_rss(query: str) -> bytes:
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode(
        {"q": query, "hl": "en-US", "gl": "US", "ceid": "US:en"}
    )
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read()


def clean_html(raw: str) -> str:
    text = re.sub(r"<[^>]+>", " ", raw or "")
    text = unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def looks_negative(title: str, summary: str) -> bool:
    combined = f"{title} {summary}".lower()
    return any(word in combined for word in NEGATIVE_SIGNAL_WORDS)


def parse_items(xml_bytes: bytes, category: str):
    root = ET.fromstring(xml_bytes)
    items = []
    for item in root.findall(".//item"):
        title = clean_html(item.findtext("title", ""))
        link = item.findtext("link", "").strip()
        pub_date_raw = item.findtext("pubDate", "")
        summary = clean_html(item.findtext("description", ""))
        source_el = item.find("source")
        source = source_el.text.strip() if source_el is not None and source_el.text else "Unknown source"

        if not title or not link:
            continue
        if looks_negative(title, summary):
            continue

        try:
            pub_dt = datetime.strptime(pub_date_raw, "%a, %d %b %Y %H:%M:%S %Z")
            pub_dt = pub_dt.replace(tzinfo=timezone.utc)
        except ValueError:
            pub_dt = datetime.now(timezone.utc)

        items.append(
            {
                "title": title,
                "link": link,
                "source": source,
                "category": category,
                "published": pub_dt.isoformat(),
                "image": None,  # filled in later via fetch_article_image()
            }
        )
        if len(items) >= MAX_PER_CATEGORY:
            break
    return items


def dedupe(stories):
    seen_titles = set()
    result = []
    for s in stories:
        key = re.sub(r"[^a-z0-9]+", "", s["title"].lower())[:60]
        if key in seen_titles:
            continue
        seen_titles.add(key)
        result.append(s)
    return result


def main():
    all_stories = []
    for q in QUERIES:
        try:
            xml_bytes = fetch_rss(q["q"])
            items = parse_items(xml_bytes, q["category"])
            all_stories.extend(items)
        except Exception as exc:  # keep going even if one query fails
            print(f"Warning: failed to fetch '{q['category']}': {exc}")

    all_stories = dedupe(all_stories)
    all_stories.sort(key=lambda s: s["published"], reverse=True)

    # Keep the story count around the target (aim for TARGET_DEFAULT, never
    # outside the TARGET_TOTAL_MIN-TARGET_TOTAL_MAX range).
    cap = min(TARGET_TOTAL_MAX, max(TARGET_TOTAL_MIN, TARGET_DEFAULT))
    stories = all_stories[:cap]
    if len(stories) < TARGET_TOTAL_MIN:
        print(f"Warning: only found {len(stories)} stories (target {TARGET_TOTAL_MIN}-{TARGET_TOTAL_MAX})")

    if not stories:
        print("No stories fetched this run (all sources unavailable). "
              "Leaving the existing data/stories.json untouched.")
        return

    # Best-effort: scrape a photo from each linked article. Any failures
    # just leave "image": None, which the site renders as a themed tile.
    for story in stories:
        story["image"] = fetch_article_image(story["link"])

    output = {
        "updated": datetime.now(timezone.utc).isoformat(),
        "count": len(stories),
        "stories": stories,
    }

    with open(STORIES_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Wrote {len(stories)} stories to {STORIES_PATH}")


if __name__ == "__main__":
    main()
