#!/usr/bin/env python3
"""
scrape_website.py — Haal publieke webpagina's op (minkowski.org + futuresready.com)
en sla ze op als plain-text Markdown-bakjes in Drive.

Anders dan LinkedIn/Medium zijn deze sites volledig publiek en zonder authenticatie
op te halen — geen browser-sessie nodig. Volledig automatiseerbaar (ook op de VM).

Bronnen worden dynamisch uit de WordPress-sitemap gelezen, zodat nieuwe artikelen
automatisch meekomen zonder code-aanpassing (schaalbaar, geen onderhoud).

Output (per job één bestand):
  06_Marketing/_bronmateriaal/website/minkowski/minkowski_org_artikelen.md
  06_Marketing/_bronmateriaal/website/team/minkowski_org_team.md
  06_Marketing/_bronmateriaal/website/futuresready/futuresready_7practices.md

Gebruik:
    python3 scripts/scrape_website.py [--dry-run] [--only minkowski|team|futuresready]

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
import urllib.request
import xml.etree.ElementTree as ET
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
log = logging.getLogger("scrape_website")

from scrape_slack import _get_drive_service, _upload_markdown, _resolve_folder_chain

SHARED_DRIVE_ID = os.environ.get("AINSTEIN_DRIVE_ROOT_ID", "0AFvBEDYKrnHbUk9PVA")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,nl;q=0.8",
}

# Markers waarna de eigenlijke artikelinhoud overgaat in gerelateerde posts / footer.
_FOOTER_MARKERS = (
    "Subscribe to our",
    "Radar for the Futures",
    "You can find\nus here",
    "You can find us here",
    "Weesperstraat 107",
)


def _ssl_ctx():
    import ssl
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def _get(url: str, delay: float = 1.0) -> str:
    time.sleep(delay)
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=25, context=_ssl_ctx()) as r:
            return r.read().decode("utf-8", errors="replace")
    except Exception as e:
        log.warning("Fetch mislukt (%s): %s", url, e)
        return ""


# ---------------------------------------------------------------------------
# HTML → schone tekst
# ---------------------------------------------------------------------------

class _Extractor(HTMLParser):
    _BLOCK = {"p", "div", "br", "h1", "h2", "h3", "h4", "li", "blockquote", "hr", "tr", "section"}
    _SKIP  = {"script", "style", "nav", "header", "footer", "aside", "form", "noscript", "svg", "button"}

    def __init__(self):
        super().__init__()
        self._parts: list[str] = []
        self._skip = 0
        self._title = ""
        self._in_title = False
        self.meta: dict[str, str] = {}

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        d = dict(attrs)
        if tag == "title":
            self._in_title = True
        if tag == "meta":
            n = d.get("property") or d.get("name") or ""
            if n and d.get("content"):
                self.meta[n] = d["content"]
        if tag in self._SKIP:
            self._skip += 1
        elif tag in self._BLOCK:
            self._parts.append("\n")

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag == "title":
            self._in_title = False
        if tag in self._SKIP:
            self._skip = max(0, self._skip - 1)

    def handle_data(self, data):
        if self._in_title:
            self._title += data
        if self._skip == 0:
            self._parts.append(data)

    def text(self) -> str:
        raw = "".join(self._parts)
        lines = [l.strip() for l in raw.splitlines()]
        out = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
        return out


def _clean_article(html: str) -> dict:
    e = _Extractor()
    e.feed(html)
    text = e.text()

    # Strip leading boilerplate
    text = re.sub(r"^.*?Skip to content\s*", "", text, flags=re.DOTALL).strip()

    # Knip footer / gerelateerde posts weg
    cut = len(text)
    for marker in _FOOTER_MARKERS:
        idx = text.find(marker)
        if idx != -1:
            cut = min(cut, idx)
    text = text[:cut].strip()

    # Verwijder een rij losse "Read more" links aan het eind (gerelateerde posts)
    text = re.sub(r"(\n?Read more\n?)+\s*$", "", text).strip()

    title = e.meta.get("og:title", e._title)
    title = re.split(r"\s+[-–]\s+", title)[0]            # strip " - Minkowski.org" / " – Futures Ready"
    title = title.replace("Toggle Menu", "").strip()
    return {
        "title":     title,
        "published": e.meta.get("article:published_time", "").strip(),
        "text":      text,
    }


# ---------------------------------------------------------------------------
# Sitemap
# ---------------------------------------------------------------------------

def _sitemap_urls(sitemap_url: str) -> list[str]:
    raw = _get(sitemap_url, delay=0.5)
    if not raw:
        return []
    try:
        root = ET.fromstring(raw.encode("utf-8"))
    except ET.ParseError as e:
        log.error("Sitemap parse-fout (%s): %s", sitemap_url, e)
        return []
    # Verwijder namespaces voor eenvoudig zoeken
    urls = [el.text.strip() for el in root.iter() if el.tag.endswith("loc") and el.text]
    # WordPress zet per afbeelding een bijlage-pagina in de sitemap — filter die weg
    urls = [
        u for u in urls
        if "/wp-content/" not in u
        and not re.search(r"\.(png|jpe?g|gif|webp|pdf|svg|mp4|mp3)$", u, re.I)
    ]
    return urls


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------

_SKIP_SLUGS = {"dit-is-een-review"}  # testpagina


def _minkowski_article_urls() -> list[str]:
    """Blogartikelen van minkowski.org — exclusief team-profielen en testpagina's."""
    urls = _sitemap_urls("https://minkowski.org/post-sitemap.xml")
    return [
        u for u in urls
        if "/meet-the-team-" not in u
        and u.rstrip("/").rsplit("/", 1)[-1] not in _SKIP_SLUGS
    ]


def _minkowski_team_urls() -> list[str]:
    """Team- en expertprofielen (voor match_experts)."""
    posts = [u for u in _sitemap_urls("https://minkowski.org/post-sitemap.xml") if "/meet-the-team-" in u]
    experts = _sitemap_urls("https://minkowski.org/expert-sitemap.xml")
    return sorted(set(posts + experts))


FUTURESREADY_URLS = [
    "https://futuresready.com/en/7-practices/",
    "https://futuresready.com/en/futures-ready/",
    "https://futuresready.com/en/change/",
    "https://futuresready.com/en/design/",
    "https://futuresready.com/en/strategy/",
    "https://futuresready.com/en/culture/",
    "https://futuresready.com/en/impact/",
    "https://futuresready.com/en/learning/",
    "https://futuresready.com/en/systems/",
    "https://futuresready.com/en/futures-academy/",
]

# Elk job: (key, beschrijving, url-provider, drive-subpad, bestandsnaam)
JOBS = {
    "minkowski": (
        "minkowski.org — artikelen",
        _minkowski_article_urls,
        ("06_Marketing", "_bronmateriaal", "website", "minkowski"),
        "minkowski_org_artikelen",
    ),
    "team": (
        "minkowski.org — team & experts",
        _minkowski_team_urls,
        ("06_Marketing", "_bronmateriaal", "website", "team"),
        "minkowski_org_team",
    ),
    "futuresready": (
        "futuresready.com — 7 practices",
        lambda: list(FUTURESREADY_URLS),
        ("06_Marketing", "_bronmateriaal", "website", "futuresready"),
        "futuresready_7practices",
    ),
}


def _build_doc(beschrijving: str, articles: list[dict], today: str) -> str:
    header = (
        f"# Website — {beschrijving}\n"
        f"_{len(articles)} pagina('s) | publiek opgehaald | Oorsprong: minkowski | "
        f"Gegenereerd: {today}_\n\n"
        "---\n\n"
    )
    parts = []
    for a in articles:
        date = a["published"][:10] if a["published"] else "datum onbekend"
        parts.append(
            f"## {a['title']}\n"
            f"_Gepubliceerd: {date}_\n"
            f"_URL: {a['url']}_\n\n"
            f"{a['text']}\n\n"
            "---\n"
        )
    return header + "\n".join(parts)


def _run_job(key: str, dry_run: bool, service) -> None:
    beschrijving, url_provider, drive_path, filename = JOBS[key]
    log.info("=== Job: %s ===", beschrijving)
    urls = url_provider()
    log.info("%d URL(s) te verwerken", len(urls))

    articles = []
    for i, url in enumerate(urls, 1):
        html = _get(url, delay=1.0)
        if not html:
            continue
        art = _clean_article(html)
        art["url"] = url
        if len(art["text"]) < 100:
            log.warning("  [%d/%d] te weinig tekst, overslaan: %s", i, len(urls), url)
            continue
        if len(art["text"]) > 40000 or not art["title"]:
            # Geen enkel echt artikel is zo lang — vrijwel zeker een bijlage/archiefpagina
            log.warning("  [%d/%d] junk (len=%d, titel=%r), overslaan: %s",
                        i, len(urls), len(art["text"]), art["title"][:30], url)
            continue
        articles.append(art)
        log.info("  [%d/%d] ✓ %s (%d chars)", i, len(urls), art["title"][:55], len(art["text"]))

    if not articles:
        log.warning("Geen artikelen voor job %s — overgeslagen.", key)
        return

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    doc = _build_doc(beschrijving, articles, today)
    log.info("Document: %d artikelen, %d chars totaal", len(articles), len(doc))

    if dry_run:
        print(f"\n{'='*60}\n{beschrijving} ({len(articles)} artikelen, {len(doc)} chars)\n{'='*60}")
        print(doc[:3000], "\n...[ingekort voor dry-run]")
        return

    folder_id = _resolve_folder_chain(service, SHARED_DRIVE_ID, *drive_path)
    # Ruim oude versie op
    existing = service.files().list(
        q=f"'{folder_id}' in parents and trashed=false",
        fields="files(id,name)", supportsAllDrives=True, includeItemsFromAllDrives=True,
        corpora="drive", driveId=SHARED_DRIVE_ID,
    ).execute().get("files", [])
    for f in existing:
        if f["name"].startswith(filename):
            service.files().update(fileId=f["id"], body={"trashed": True}, supportsAllDrives=True).execute()
            log.info("Oud bestand naar prullenbak: %s", f["name"])

    link = _upload_markdown(service, filename, doc, folder_id)
    log.info("Geüpload: %s.md → %s", filename, link)


def main() -> int:
    parser = argparse.ArgumentParser(description="Publieke website → Drive markdown bakje")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--only", choices=list(JOBS.keys()), help="Slechts één job draaien")
    args = parser.parse_args()

    log.info("=== Website scraper gestart ===")
    keys = [args.only] if args.only else list(JOBS.keys())

    service = None if args.dry_run else _get_drive_service()
    for key in keys:
        _run_job(key, args.dry_run, service)

    log.info("=== Website scraper klaar ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
