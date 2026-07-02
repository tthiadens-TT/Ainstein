#!/usr/bin/env python3
"""
scrape_substack.py — Haal Substack-artikelen op via RSS en sla op als Markdown-bakjes in Drive.

Aslander IA-principe: plain text (.md) per jaar, directe URL-fetch voor volledige inhoud.
Output: substack_futuresready_YYYY.md in 04_Marketing/_bronmateriaal/substack/

Gebruik:
    python3 scripts/scrape_substack.py [--url URL] [--dry-run]

Standaard: futuresready.substack.com, alle beschikbare artikelen.

Vereiste env vars (via .env):
    GOOGLE_SERVICE_ACCOUNT_FILE of GOOGLE_SERVICE_ACCOUNT_JSON
    AINSTEIN_DRIVE_ROOT_ID   — Shared Drive ID (default: Minkowski AInstein)
"""

import argparse
import io
import logging
import os
import re
import sys
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
log = logging.getLogger("scrape_substack")

# Hergebruik Drive-helpers uit scrape_slack.py
from scrape_slack import _get_drive_service, _get_or_create_folder, _upload_markdown, _resolve_folder_chain

SHARED_DRIVE_ID = os.environ.get("AINSTEIN_DRIVE_ROOT_ID", "0AFvBEDYKrnHbUk9PVA")
DEFAULT_FEED_URL = "https://futuresready.substack.com/feed"

SUBSTACK_PATH = ("_bronmateriaal", "substack")  # onder marketing-rolmap (drive_structure)


# ---------------------------------------------------------------------------
# HTML → plain text
# ---------------------------------------------------------------------------

class _TextExtractor(HTMLParser):
    """Strip HTML tags en converteer naar leesbare plain text."""

    _BLOCK = {"p", "div", "br", "h1", "h2", "h3", "h4", "li", "blockquote", "hr", "tr"}

    def __init__(self):
        super().__init__()
        self._parts: list[str] = []
        self._skip = 0  # nesting level van te skippen tags

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in ("script", "style", "figure", "figcaption"):
            self._skip += 1
        elif tag in self._BLOCK:
            self._parts.append("\n")

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in ("script", "style", "figure", "figcaption"):
            self._skip = max(0, self._skip - 1)

    def handle_data(self, data):
        if self._skip == 0:
            self._parts.append(data)

    def get_text(self) -> str:
        raw = "".join(self._parts)
        # Comprimeer witruimte maar bewaar alinea-scheidingen
        lines = [line.strip() for line in raw.splitlines()]
        result = "\n".join(lines)
        result = re.sub(r"\n{3,}", "\n\n", result)
        return result.strip()


def _html_to_text(html: str) -> str:
    extractor = _TextExtractor()
    extractor.feed(html)
    return extractor.get_text()


# ---------------------------------------------------------------------------
# RSS parsing
# ---------------------------------------------------------------------------

_NS = {
    "content": "http://purl.org/rss/1.0/modules/content/",
    "dc":      "http://purl.org/dc/elements/1.1/",
    "atom":    "http://www.w3.org/2005/Atom",
}


def _fetch_feed(url: str) -> bytes:
    import ssl
    try:
        import certifi
        ctx = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers={"User-Agent": "Ainstein/1.0 (+https://ainstein.duckdns.org)"})
    with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
        return resp.read()


def _parse_date(date_str: str) -> datetime | None:
    """Parse RSS pubDate (RFC 2822) naar datetime."""
    if not date_str:
        return None
    # Probeer de meest voorkomende RFC-2822 formaten
    for fmt in (
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%d %b %Y %H:%M:%S %z",
    ):
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    log.warning("Kon datum niet parsen: %s", date_str)
    return None


def _parse_rss(data: bytes) -> list[dict]:
    """Geef lijst van artikel-dicts terug (title, url, date, content)."""
    root = ET.fromstring(data)
    channel = root.find("channel")
    if channel is None:
        log.error("Geen <channel> gevonden in RSS feed")
        return []

    articles = []
    for item in channel.findall("item"):
        title = (item.findtext("title") or "").strip()
        url   = (item.findtext("link") or "").strip()
        date_str = item.findtext("pubDate") or ""
        pub_date = _parse_date(date_str)

        # Volledige inhoud (content:encoded) heeft de voorkeur boven description
        content_html = (
            item.findtext("content:encoded", namespaces=_NS)
            or item.findtext("description")
            or ""
        )
        content_text = _html_to_text(content_html)

        if not title and not url:
            continue

        articles.append({
            "title":   title,
            "url":     url,
            "date":    pub_date,
            "content": content_text,
        })

    log.info("%d artikelen gevonden in RSS feed", len(articles))
    return articles


# ---------------------------------------------------------------------------
# Markdown formattering
# ---------------------------------------------------------------------------

def _article_to_md(article: dict) -> str:
    date_str = article["date"].strftime("%Y-%m-%d") if article["date"] else "datum onbekend"
    lines = [
        f"## {article['title']}",
        f"_Gepubliceerd: {date_str}_",
        f"_URL: {article['url']}_",
        "",
        article["content"],
        "",
        "---",
        "",
    ]
    return "\n".join(lines)


def _group_by_year(articles: list[dict]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for a in articles:
        year = a["date"].strftime("%Y") if a["date"] else "onbekend"
        groups[year].append(a)
    return dict(groups)


def _build_year_doc(year: str, articles: list[dict], feed_url: str) -> str:
    header = (
        f"# Substack — {feed_url}\n"
        f"_Jaar: {year} | {len(articles)} artikel(en) | "
        f"Gegenereerd: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}_\n\n"
        "---\n\n"
    )
    return header + "\n".join(_article_to_md(a) for a in sorted(articles, key=lambda x: x["date"] or datetime.min))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Substack RSS → Drive markdown bakje")
    parser.add_argument("--url", default=DEFAULT_FEED_URL, help="RSS feed URL")
    parser.add_argument("--dry-run", action="store_true", help="Niet schrijven — print naar stdout")
    args = parser.parse_args()

    log.info("=== Substack scraper gestart ===")
    log.info("Feed: %s", args.url)

    # RSS ophalen + parsen
    try:
        data = _fetch_feed(args.url)
    except Exception as e:
        log.error("Kon RSS feed niet ophalen: %s", e)
        return 1

    articles = _parse_rss(data)
    if not articles:
        log.warning("Geen artikelen gevonden — afgebroken.")
        return 1

    groups = _group_by_year(articles)
    log.info("Jaren: %s", sorted(groups.keys()))

    if args.dry_run:
        for year, arts in sorted(groups.items()):
            doc = _build_year_doc(year, arts, args.url)
            print(f"\n{'='*60}\nJAAR {year} ({len(arts)} artikelen)\n{'='*60}")
            print(doc[:3000], "...[ingekort voor dry-run]" if len(doc) > 3000 else "")
        return 0

    # Drive upload
    service = _get_drive_service()
    import drive_structure as ds
    folder_id = ds.resolve_path(service, "marketing", SUBSTACK_PATH, create=True)
    log.info("Doelmap: marketing/%s (%s)", "/".join(SUBSTACK_PATH), folder_id)

    uploaded = 0
    for year, arts in sorted(groups.items()):
        doc = _build_year_doc(year, arts, args.url)
        filename = f"substack_futuresready_{year}"
        link = _upload_markdown(service, filename, doc, folder_id)
        log.info("Geüpload: %s.md → %s", filename, link)
        uploaded += 1

    log.info("=== Klaar: %d bestand(en) geüpload ===", uploaded)
    return 0


if __name__ == "__main__":
    sys.exit(main())
