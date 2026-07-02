"""
Centrale, dynamische Drive-structuur-resolutie voor Ainstein.

WAAROM DIT BESTAAT
------------------
Op 30 juni 2026 zijn de top-level mappen in de Shared Drive hernoemd
(o.a. 06_Marketing -> 04_Marketing). Scripts met hardcoded mapnamen bleven
naar de oude namen zoeken en maakten die mappen opnieuw aan op rootniveau
("spookmappen"), waardoor verse scraperdata in een map belandde die Ainstein
niet leest. Dit module maakt dat structureel onmogelijk:

1. Top-level mappen worden herkend aan hun NUMMER-voorvoegsel (00_ t/m 05_),
   niet aan hun naam. Hernoemen ("04_Marketing" -> "04_GTM") breekt niets.
2. Een rol-map die niet gevonden wordt geeft een harde fout (fail loud).
   Er wordt NOOIT een top-level structuurmap aangemaakt door code.
3. Submappen mogen alleen worden aangemaakt ONDER een gevonden rol-map
   (en alleen als de aanroeper daar expliciet om vraagt).
4. Bij dubbele mappen met dezelfde naam (bv. twee "_kennis") wint
   deterministisch de OUDSTE (createdTime), met een waarschuwing in de log.

GEBRUIK
-------
    import drive_structure as ds
    folder_id = ds.resolve_path(service, "marketing", ("_bronmateriaal", "slack"), create=True)
    kennis_id = ds.resolve_path(service, "marketing", ("_kennis",))
    folder_id = ds.parse_location(service, "04_Marketing/_bronmateriaal/jamie/")

Omgevingsvariabele-override per rol (optioneel, voor uitzonderingen):
    AINSTEIN_FOLDER_MARKETING=<folder-id>

Read-only zelftest (veilig, alleen lezen):
    python3 drive_structure.py
"""

from __future__ import annotations

import logging
import os
import re

logger = logging.getLogger("drive_structure")

_DEFAULT_ROOT_ID = "0AFvBEDYKrnHbUk9PVA"  # Shared Drive "Minkowski AInstein"

# Rol -> nummer-voorvoegsel van de top-level map. Dit voorvoegsel is de
# huisconventie en het enige anker; de naam erachter mag vrij veranderen.
ROLE_PREFIXES: dict[str, str] = {
    "werkdocumenten": "00",
    "clients": "01",
    "frameworks": "02",
    "experts": "03",
    "marketing": "04",
    "knowledge_base": "05",
}

# Cache per proces: (root_id, cache_key) -> folder_id
_cache: dict[tuple[str, str], str] = {}


class DriveStructureError(RuntimeError):
    """Structuurmap niet gevonden of niet eenduidig oplosbaar. Fail loud."""


def _root_id(root_id: str | None) -> str:
    return root_id or os.environ.get("AINSTEIN_DRIVE_ROOT_ID", _DEFAULT_ROOT_ID)


def _list_child_folders(service, parent_id: str) -> list[dict]:
    """Alle submappen van parent_id, met createdTime (voor oudste-wint)."""
    items: list[dict] = []
    page_token = None
    while True:
        resp = service.files().list(
            q=(
                f"'{parent_id}' in parents "
                "and mimeType='application/vnd.google-apps.folder' "
                "and trashed=false"
            ),
            fields="nextPageToken, files(id, name, createdTime)",
            pageSize=100,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            pageToken=page_token,
        ).execute()
        items.extend(resp.get("files", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return items


def _pick_oldest(candidates: list[dict], label: str) -> dict:
    """Bij meerdere kandidaten: kies deterministisch de oudste + waarschuw.

    Puur (geen netwerk) zodat dit unit-testbaar is.
    """
    if len(candidates) == 1:
        return candidates[0]
    ordered = sorted(candidates, key=lambda f: f.get("createdTime", ""))
    logger.warning(
        "drive_structure: %d mappen matchen '%s' (%s) — oudste wint: %s (%s). "
        "Ruim de duplicaten op.",
        len(candidates), label,
        ", ".join(f"{f['name']}:{f['id']}" for f in ordered),
        ordered[0]["name"], ordered[0]["id"],
    )
    return ordered[0]


def match_role_folder(folders: list[dict], prefix: str) -> list[dict]:
    """Puur: filter mappen op nummer-voorvoegsel (bv. '04' matcht '04_Marketing',
    '04 GTM', '04-Marketing'). Unit-testbaar zonder netwerk."""
    pattern = re.compile(rf"^{re.escape(prefix)}[\s_\-]")
    return [f for f in folders if pattern.match(f.get("name", ""))]


def resolve_role(service, role: str, root_id: str | None = None) -> str:
    """Folder-ID van een top-level rol-map. Fail loud, maakt NOOIT aan."""
    role = role.lower()
    if role not in ROLE_PREFIXES:
        raise DriveStructureError(
            f"Onbekende rol '{role}'. Geldig: {sorted(ROLE_PREFIXES)}"
        )

    env_override = os.environ.get(f"AINSTEIN_FOLDER_{role.upper()}")
    if env_override:
        return env_override

    rid = _root_id(root_id)
    cache_key = (rid, f"role:{role}")
    if cache_key in _cache:
        return _cache[cache_key]

    prefix = ROLE_PREFIXES[role]
    matches = match_role_folder(_list_child_folders(service, rid), prefix)
    if not matches:
        raise DriveStructureError(
            f"Geen top-level map met voorvoegsel '{prefix}_' gevonden voor rol "
            f"'{role}' in Drive-root {rid}. NIET automatisch aangemaakt — check "
            "de Shared Drive-structuur (is de map hernoemd zonder nummer, of "
            "verwijderd?). Override mogelijk via env var "
            f"AINSTEIN_FOLDER_{role.upper()}=<folder-id>."
        )
    chosen = _pick_oldest(matches, f"rol {role} (prefix {prefix})")
    _cache[cache_key] = chosen["id"]
    return chosen["id"]


def resolve_path(
    service,
    role: str,
    subpath: tuple[str, ...] | list[str] = (),
    create: bool = False,
    root_id: str | None = None,
) -> str:
    """Folder-ID van rol-map + submappen-pad eronder.

    create=True maakt ontbrekende SUBmappen aan (nooit de rol-map zelf) —
    altijd onder de correct gevonden ouder, dus nooit een spookmap op root.
    """
    rid = _root_id(root_id)
    current = resolve_role(service, role, rid)

    for name in subpath:
        cache_key = (rid, f"sub:{current}/{name}")
        if cache_key in _cache:
            current = _cache[cache_key]
            continue
        children = _list_child_folders(service, current)
        matches = [f for f in children if f.get("name") == name]
        if matches:
            chosen = _pick_oldest(matches, f"submap '{name}'")
            _cache[cache_key] = chosen["id"]
            current = chosen["id"]
        elif create:
            meta = {
                "name": name,
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [current],
            }
            created = service.files().create(
                body=meta, fields="id", supportsAllDrives=True
            ).execute()
            logger.info("drive_structure: submap '%s' aangemaakt onder %s", name, current)
            _cache[cache_key] = created["id"]
            current = created["id"]
        else:
            raise DriveStructureError(
                f"Submap '{name}' niet gevonden onder {current} (rol {role}, "
                f"pad {'/'.join(subpath)}). Niet aangemaakt (create=False)."
            )
    return current


def split_location(location: str) -> tuple[str, tuple[str, ...]]:
    """Puur: splits een config-locatie ('04_Marketing/_bronmateriaal/slack/')
    in (rol, subpad). Het eerste segment wordt op nummer-voorvoegsel gematcht,
    dus de naam erachter mag afwijken van de werkelijkheid in Drive."""
    parts = [p for p in location.strip("/").split("/") if p]
    if not parts:
        raise DriveStructureError(f"Lege locatie: '{location}'")
    m = re.match(r"^(\d{2})[\s_\-]?", parts[0])
    if not m:
        raise DriveStructureError(
            f"Locatie '{location}' begint niet met een nummer-voorvoegsel "
            "(bv. '04_...'). Kan geen rol bepalen."
        )
    prefix = m.group(1)
    for role, p in ROLE_PREFIXES.items():
        if p == prefix:
            return role, tuple(parts[1:])
    raise DriveStructureError(
        f"Voorvoegsel '{prefix}' uit locatie '{location}' hoort bij geen enkele "
        f"bekende rol. Geldig: {ROLE_PREFIXES}"
    )


def parse_location(
    service, location: str, create: bool = False, root_id: str | None = None
) -> str:
    """Folder-ID van een config-locatie-string (zoals in scripts/bronnen.json)."""
    role, subpath = split_location(location)
    return resolve_path(service, role, subpath, create=create, root_id=root_id)


def clear_cache() -> None:
    """Cache legen (bv. na het aanmaken van mappen buiten dit module om)."""
    _cache.clear()


if __name__ == "__main__":
    # Read-only zelftest: resolve alle rollen + bekende subpaden. Geen writes.
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        from dotenv import load_dotenv
        load_dotenv(Path(__file__).resolve().parent / ".env")
    except Exception:
        pass
    from gdoc_tools import _get_service_account_creds
    from googleapiclient.discovery import build

    creds = _get_service_account_creds()
    if creds is None:
        sys.exit("Geen serviceaccount-credentials (GOOGLE_SERVICE_ACCOUNT_FILE/_JSON).")
    svc = build("drive", "v3", credentials=creds, cache_discovery=False)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    print("=== drive_structure zelftest (read-only) ===")
    for role in ROLE_PREFIXES:
        try:
            fid = resolve_role(svc, role)
            print(f"  rol {role:15s} -> {fid}")
        except DriveStructureError as e:
            print(f"  rol {role:15s} -> FOUT: {e}")
    for sub in [("marketing", ("_bronmateriaal",)), ("marketing", ("_kennis",)),
                ("marketing", ("_bronmateriaal", "slack"))]:
        try:
            fid = resolve_path(svc, sub[0], sub[1])
            print(f"  {sub[0]}/{'/'.join(sub[1]):30s} -> {fid}")
        except DriveStructureError as e:
            print(f"  {sub[0]}/{'/'.join(sub[1])} -> FOUT: {e}")
    print("=== klaar ===")
