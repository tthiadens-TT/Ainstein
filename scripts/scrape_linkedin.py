#!/usr/bin/env python3
"""
scrape_linkedin.py — Haal LinkedIn posts op via Google Search + directe URL-fetch.

LinkedIn posts zijn publiek toegankelijk via directe URL (geen inlog nodig).
Google Search indexeert LinkedIn posts — wij halen de URL-lijst op via Google
en lezen dan elk post direct van LinkedIn (meta/OG-tags + page text via Playwright-achtige fetch).

Output:
  04_Marketing/_bronmateriaal/linkedin/jorgen/linkedin_jorgen_YYYY.md
  04_Marketing/_bronmateriaal/linkedin/minkowski/linkedin_minkowski_YYYY.md

Gebruik:
    python3 scripts/scrape_linkedin.py [--dry-run] [--max-posts N]

Vereiste env vars (via .env):
    GOOGLE_SERVICE_ACCOUNT_FILE of GOOGLE_SERVICE_ACCOUNT_JSON
    AINSTEIN_DRIVE_ROOT_ID
"""

import argparse
import logging
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(_REPO_ROOT / ".env")
except ImportError:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("scrape_linkedin")

from scrape_slack import _get_drive_service, _upload_markdown, _resolve_folder_chain

SHARED_DRIVE_ID = os.environ.get("AINSTEIN_DRIVE_ROOT_ID", "0AFvBEDYKrnHbUk9PVA")

# Subpaden ONDER de marketing-rolmap (prefix 04_). Rolmap wordt dynamisch
# opgelost via drive_structure, dus hernoemen breekt niets.
JORGEN_PATH    = ("_bronmateriaal", "linkedin", "jorgen")
MINKOWSKI_PATH = ("_bronmateriaal", "linkedin", "minkowski")

# Google Search queries for LinkedIn posts
QUERIES = {
    "jorgen": [
        'site:linkedin.com/posts/jorgenvandersloot',
        '"Jorgen van der Sloot" site:linkedin.com/posts',
    ],
    "minkowski": [
        'site:linkedin.com/posts/minkowski',
        'site:linkedin.com/company/minkowski',
    ],
}

# Bekende post-URLs als seed (gevonden via Google 2026-06-20).
# Worden altijd gefetcht ongeacht of Google search werkt.
# Bij nieuwe posts: voeg URL toe aan de juiste lijst.
KNOWN_URLS: dict[str, list[str]] = {
    "jorgen": [
        "https://www.linkedin.com/posts/jorgenvandersloot_were-living-through-one-of-the-most-radical-activity-7418984752931610625-bnyG",
        "https://www.linkedin.com/posts/jorgenvandersloot_learningorganization-change-leadershipdevelopment-activity-7365993920201146370-NxOs",
        "https://www.linkedin.com/posts/jorgenvandersloot_great-to-see-the-progress-lance-weiler-and-activity-7457027774755676160-afUi",
        "https://www.linkedin.com/posts/jorgenvandersloot_wat-me-elke-keer-weer-opvalt-hoe-snel-professionals-activity-7453327886830219265-llH2",
        "https://www.linkedin.com/posts/jorgenvandersloot_futuresready-activity-7463917890174402560-Yomk",
        "https://www.linkedin.com/posts/jorgenvandersloot_dutchdesignweek-scenarioplanning-engagement-activity-6980236271663124480-zMN3",
    ],
    "minkowski": [
        "https://www.linkedin.com/posts/minkowski_futuresready-personaldevelopment-leadership-activity-7376888196661403649-27jn",
        "https://www.linkedin.com/posts/minkowski_futuresready-leadingchange-leadership-activity-7346085334859870208-_p66",
        "https://www.linkedin.com/posts/minkowski_futuresthinking-peopledevelopment-drivechange-activity-7160575275049566208-G9Z5",
    ],
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "nl-NL,nl;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def _get(url: str, delay: float = 1.0) -> str:
    """Fetch URL en return als text. Respecteer robots via delay."""
    import ssl
    try:
        import certifi
        ctx = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        ctx = ssl.create_default_context()
    time.sleep(delay)
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=20, context=ctx) as r:
            return r.read().decode("utf-8", errors="replace")
    except Exception as e:
        log.warning("Fetch mislukt (%s): %s", url, e)
        return ""


# ---------------------------------------------------------------------------
# HTML helpers
# ---------------------------------------------------------------------------

class _MetaParser(HTMLParser):
    """Leest meta-tags uit HTML (og:description, og:title, article:published_time)."""
    def __init__(self):
        super().__init__()
        self.meta: dict[str, str] = {}
        self.title: str = ""
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        attrs_d = dict(attrs)
        if tag == "title":
            self._in_title = True
        if tag == "meta":
            name = attrs_d.get("property") or attrs_d.get("name") or ""
            content = attrs_d.get("content", "")
            if name and content:
                self.meta[name] = content

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data


def _parse_meta(html: str) -> dict:
    p = _MetaParser()
    p.feed(html[:50000])
    return {
        "og_title":       p.meta.get("og:title", p.title).strip(),
        "og_description": p.meta.get("og:description", "").strip(),
        "og_url":         p.meta.get("og:url", "").strip(),
        "published":      p.meta.get("article:published_time", "").strip(),
    }


# ---------------------------------------------------------------------------
# Google Search scraper (raw HTML parsing)
# ---------------------------------------------------------------------------

_LINKEDIN_POST_RE = re.compile(
    r'https?://(?:nl\.)?linkedin\.com/posts/([^"&\s<>]+)'
)
_LINKEDIN_COMPANY_POST_RE = re.compile(
    r'https?://(?:nl\.)?linkedin\.com/company/([^/]+)/posts[^"&\s<>]*'
)


def _google_search_urls(query: str, max_pages: int = 5) -> list[str]:
    """Zoek via Google en geef een deduplicated lijst van LinkedIn post-URLs."""
    found: set[str] = set()
    for page in range(max_pages):
        start = page * 10
        q = urllib.parse.quote_plus(query)
        url = f"https://www.google.com/search?q={q}&num=10&start={start}&hl=nl"
        html = _get(url, delay=2.0)
        if not html:
            break
        matches = _LINKEDIN_POST_RE.findall(html)
        new_urls = {f"https://www.linkedin.com/posts/{m}" for m in matches}
        if not new_urls - found:
            # Geen nieuwe resultaten → stop
            break
        found |= new_urls
        log.info("Google pagina %d: %d nieuwe URLs (totaal %d)", page + 1, len(new_urls - found | new_urls), len(found))
    return sorted(found)


# ---------------------------------------------------------------------------
# LinkedIn post fetcher
# ---------------------------------------------------------------------------

def _fetch_post(url: str) -> dict | None:
    """Haal één LinkedIn post op en geef een dict met title, body, date, url."""
    # Normaliseer naar non-locale URL
    url = url.replace("nl.linkedin.com", "www.linkedin.com")
    html = _get(url, delay=1.5)
    if not html or "authwall" in html[:2000].lower():
        log.warning("Post niet toegankelijk (authwall): %s", url)
        return None

    meta = _parse_meta(html)
    title = meta["og_title"].split(" | ")[0].strip()
    body  = meta["og_description"].strip()
    if not body and not title:
        log.warning("Geen content gevonden in meta: %s", url)
        return None

    # Probeer datum te destilleren uit URL of meta
    date_str = meta.get("published", "")
    date = None
    if date_str:
        try:
            date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except ValueError:
            pass

    return {
        "url":   url,
        "title": title,
        "body":  body,
        "date":  date,
    }


# ---------------------------------------------------------------------------
# Markdown formattering
# ---------------------------------------------------------------------------

def _post_to_md(post: dict) -> str:
    date_str = post["date"].strftime("%Y-%m-%d") if post["date"] else "datum onbekend"
    lines = [
        f"## {post['title'][:120]}",
        f"_Gepubliceerd: {date_str}_",
        f"_URL: {post['url']}_",
        "",
        post["body"],
        "",
        "---",
        "",
    ]
    return "\n".join(lines)


def _build_doc(origin: str, posts: list[dict], today: str) -> str:
    header = (
        f"# LinkedIn — {origin}\n"
        f"_{len(posts)} post(s) | Gegenereerd: {today}_\n\n"
        "---\n\n"
    )
    sorted_posts = sorted(posts, key=lambda p: p["date"] or datetime.min, reverse=True)
    return header + "\n".join(_post_to_md(p) for p in sorted_posts)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="LinkedIn posts → Drive markdown bakje")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-posts", type=int, default=100, help="Max posts per origin")
    parser.add_argument("--max-google-pages", type=int, default=8)
    parser.add_argument("--skip-google", action="store_true", default=True,
                        help="Sla Google Search over — gebruik alleen KNOWN_URLS (standaard aan; "
                             "gebruik --no-skip-google om Google-search ook te proberen)")
    parser.add_argument("--no-skip-google", dest="skip_google", action="store_false")
    args = parser.parse_args()

    log.info("=== LinkedIn scraper gestart ===")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Begin met bekende URLs als seed
    all_urls: dict[str, set[str]] = {
        origin: set(urls) for origin, urls in KNOWN_URLS.items()
    }
    for origin, urls in all_urls.items():
        log.info("Seed [%s]: %d bekende URLs", origin, len(urls))

    # Optioneel: Google Search (werkt alleen lokaal, niet op VM — Google blokkeert urllib)
    if not args.skip_google:
        for origin, queries in QUERIES.items():
            for q in queries:
                log.info("Google search [%s]: %s", origin, q)
                urls = _google_search_urls(q, max_pages=args.max_google_pages)
                new = set(urls) - all_urls[origin]
                all_urls[origin].update(urls)
                log.info("  → %d nieuwe URLs (totaal %d)", len(new), len(all_urls[origin]))
    else:
        log.info("Google Search overgeslagen (--skip-google). Voeg --no-skip-google toe om toch te zoeken.")

    # Normaliseer URLs (verwijder nl.linkedin.com → www.linkedin.com)
    for origin in list(all_urls.keys()):
        all_urls[origin] = {u.replace("nl.linkedin.com", "www.linkedin.com") for u in all_urls[origin]}

    # Splits: jorgenvandersloot-posts → jorgen, minkowski-posts → minkowski
    jorgen_urls  = {u for u in all_urls["jorgen"]    if "jorgenvandersloot" in u}
    mink_urls    = {u for u in all_urls["minkowski"] if "minkowski" in u.lower()}
    mink_extra   = {u for u in all_urls["jorgen"] if "minkowski" in u.lower() and "jorgenvandersloot" not in u}
    mink_urls   |= mink_extra

    log.info("Jorgen URLs: %d | Minkowski URLs: %d", len(jorgen_urls), len(mink_urls))

    # Limiteer
    jorgen_urls  = set(list(jorgen_urls)[:args.max_posts])
    mink_urls    = set(list(mink_urls)[:args.max_posts])

    results: dict[str, list[dict]] = {"jorgen": [], "minkowski": []}

    for url in jorgen_urls:
        post = _fetch_post(url)
        if post:
            results["jorgen"].append(post)
            log.info("[jorgen] ✓ %s", post["title"][:60])

    for url in mink_urls:
        post = _fetch_post(url)
        if post:
            results["minkowski"].append(post)
            log.info("[minkowski] ✓ %s", post["title"][:60])

    log.info("Resultaat: jorgen=%d posts, minkowski=%d posts",
             len(results["jorgen"]), len(results["minkowski"]))

    if args.dry_run:
        for origin, posts in results.items():
            print(f"\n{'='*60}\n{origin.upper()} ({len(posts)} posts)\n{'='*60}")
            doc = _build_doc(origin, posts, today)
            print(doc[:4000])
        return 0

    if not any(results.values()):
        log.error("Geen posts gevonden — afgebroken.")
        return 1

    service = _get_drive_service()

    for origin, posts in results.items():
        if not posts:
            log.warning("Geen posts voor %s — map wordt niet aangemaakt.", origin)
            continue
        import drive_structure as ds
        path = JORGEN_PATH if origin == "jorgen" else MINKOWSKI_PATH
        folder_id = ds.resolve_path(service, "marketing", path, create=True)
        doc = _build_doc(origin, posts, today)
        filename = f"linkedin_{origin}_{today}"
        link = _upload_markdown(service, filename, doc, folder_id)
        log.info("Geüpload: %s → %s", filename, link)

    log.info("=== LinkedIn scraper klaar ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
