import os
import re
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent

# Cache of (abs_path_str, mtime_ns) -> parsed text. Keeps one agent turn from
# re-parsing the same PDFs/DOCX repeatedly across search + read_file calls.
_READ_CACHE: dict[tuple[str, int], str] = {}
_READ_CACHE_MAX = 256

GDRIVE_DIR = Path(
    "/Users/thomasthiadens/Library/CloudStorage/"
    "GoogleDrive-tthiadens@gmail.com/.shortcut-targets-by-id/"
    "1ziMd8Zmhgpqq_iHyoz3-59_KwL7kbm7e/Thomas /AInstein"
)

_FOLDER_NAMES = [
    "01_Proposals",
    "02_Tools",
    "03_Pricing",
    "04_Experts",
    "05_Venues",
    "06_Marketing",
    "07_Feedback",
]


def _resolve_folder(name: str) -> Path:
    """Return Google Drive path if it exists and has content, else local path."""
    gdrive = GDRIVE_DIR / name
    local = BASE_DIR / name
    if gdrive.exists() and any(gdrive.iterdir()):
        return gdrive
    return local


SOURCE_FOLDERS = {name: _resolve_folder(name) for name in _FOLDER_NAMES}

TEXT_EXTENSIONS = {".txt", ".md", ".pdf", ".docx", ".doc", ".rtf", ".csv", ".json", ".xlsx", ".xlsm"}


def _read_text(path: Path) -> str:
    """Read a file as plain text, best-effort. Cached by (abspath, mtime)."""
    try:
        st = path.stat()
        cache_key = (str(path.resolve()), st.st_mtime_ns)
    except OSError:
        cache_key = None

    if cache_key is not None:
        cached = _READ_CACHE.get(cache_key)
        if cached is not None:
            return cached

    result = _read_text_uncached(path)

    if cache_key is not None:
        if len(_READ_CACHE) >= _READ_CACHE_MAX:
            # Simple FIFO eviction — drop the oldest key
            _READ_CACHE.pop(next(iter(_READ_CACHE)))
        _READ_CACHE[cache_key] = result
    return result


def _read_text_uncached(path: Path) -> str:
    """Actual parser implementation, separated so the cache wraps it cleanly."""
    try:
        if path.suffix.lower() in {".docx", ".doc"}:
            from docx import Document
            doc = Document(str(path))
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            for table in doc.tables:
                for row in table.rows:
                    row_text = " | ".join(c.text.strip() for c in row.cells if c.text.strip())
                    if row_text:
                        paragraphs.append(row_text)
            return "\n".join(paragraphs)
        if path.suffix.lower() == ".pdf":
            try:
                from pypdf import PdfReader
            except ImportError:
                from PyPDF2 import PdfReader  # fallback
            reader = PdfReader(str(path))
            parts = []
            for i, page in enumerate(reader.pages, start=1):
                try:
                    text = page.extract_text() or ""
                except Exception:
                    text = ""
                text = text.strip()
                if text:
                    parts.append(f"## Page {i}\n{text}")
            return "\n\n".join(parts) if parts else "[PDF has no extractable text — may be scanned images]"
        if path.suffix.lower() in {".xlsx", ".xlsm"}:
            import openpyxl
            wb = openpyxl.load_workbook(str(path), data_only=True)
            parts = []
            for sheet in wb.worksheets:
                parts.append(f"## Sheet: {sheet.title}")
                for row in sheet.iter_rows(values_only=True):
                    cells = [str(c) if c is not None else "" for c in row]
                    if any(c.strip() for c in cells):
                        parts.append(" | ".join(cells))
            return "\n".join(parts)
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return f"[Could not read file: {e}]"


def list_folder(folder: str | None = None) -> dict:
    """
    List files in one or all source folders.
    Returns a dict mapping folder names to lists of relative file paths.
    """
    if folder:
        folder = folder.strip().lstrip("/")
        # Accept short names like "04_Experts" or just "Experts"
        matched = None
        for key in SOURCE_FOLDERS:
            if folder.lower() in key.lower() or key.lower() in folder.lower():
                matched = key
                break
        if not matched:
            return {"error": f"Folder '{folder}' not found. Available: {list(SOURCE_FOLDERS.keys())}"}
        folders_to_scan = {matched: SOURCE_FOLDERS[matched]}
    else:
        folders_to_scan = SOURCE_FOLDERS

    result = {}
    for name, path in folders_to_scan.items():
        if not path.exists():
            result[name] = []
            continue
        files = []
        for f in sorted(path.rglob("*")):
            if f.is_file() and not f.name.startswith("."):
                files.append(str(f))  # use absolute path so read_file can locate it
        result[name] = files

    return result


def read_file(path: str) -> dict:
    """
    Read a file from the Minkowski source structure.
    Accepts absolute paths or paths relative to BASE_DIR or GDRIVE_DIR.
    """
    target = Path(path)

    # Absolute path that exists — use directly
    if not target.is_absolute():
        # Try relative to BASE_DIR first, then GDRIVE_DIR
        candidate = BASE_DIR / path.lstrip("/")
        if candidate.exists():
            target = candidate
        else:
            candidate = GDRIVE_DIR / path.lstrip("/")
            if candidate.exists():
                target = candidate

    if not target.exists():
        # Last resort: search by filename across all source folders
        name = target.name
        for folder_path in SOURCE_FOLDERS.values():
            matches = list(folder_path.rglob(name))
            if matches:
                target = matches[0]
                break
        else:
            return {"error": f"File not found: {path}"}

    if not target.is_file():
        return {"error": f"Path is not a file: {path}"}

    content = _read_text(target)
    return {
        "path": str(target),
        "size_chars": len(content),
        "content": content,
    }


def search_files(query: str, folders: list[str] | None = None) -> dict:
    """
    Search for files whose name or content contains the query terms.
    Returns matches ranked by relevance (number of term hits).

    Args:
        query: Search string. Space-separated terms are all searched.
        folders: Optional list of folder names to restrict search to.
                 Accepts short names like ["Proposals", "Experts"].
    """
    terms = [t.strip().lower() for t in query.split() if t.strip()]
    if not terms:
        return {"error": "Empty search query"}

    if folders:
        scan = {}
        for f in folders:
            for key, path in SOURCE_FOLDERS.items():
                if f.lower() in key.lower() or key.lower() in f.lower():
                    scan[key] = path
                    break
    else:
        scan = SOURCE_FOLDERS

    results = []
    for folder_name, folder_path in scan.items():
        if not folder_path.exists():
            continue
        for file_path in sorted(folder_path.rglob("*")):
            if not file_path.is_file() or file_path.name.startswith("."):
                continue
            if file_path.suffix.lower() not in TEXT_EXTENSIONS:
                continue

            name_lower = file_path.name.lower()
            content = _read_text(file_path)
            content_lower = content.lower()

            name_hits = sum(t in name_lower for t in terms)
            content_hits = sum(content_lower.count(t) for t in terms)
            total_score = name_hits * 10 + content_hits

            if total_score == 0:
                continue

            # Extract relevant snippets (up to 3)
            snippets = []
            for term in terms:
                for match in re.finditer(re.escape(term), content_lower):
                    start = max(0, match.start() - 100)
                    end = min(len(content), match.end() + 100)
                    snippet = content[start:end].replace("\n", " ").strip()
                    snippets.append(f"…{snippet}…")
                    if len(snippets) >= 3:
                        break
                if len(snippets) >= 3:
                    break

            results.append({
                "path": str(file_path),
                "folder": folder_name,
                "score": total_score,
                "name_matches": name_hits,
                "content_matches": content_hits,
                "snippets": snippets[:3],
            })

    results.sort(key=lambda r: r["score"], reverse=True)

    return {
        "query": query,
        "total_matches": len(results),
        "results": results[:20],  # cap at 20
    }


def web_search(query: str, max_results: int = 5) -> dict:
    """
    Search the web using DuckDuckGo. Use for live company research,
    market context, competitive landscape, and recent news.
    """
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        return {
            "query": query,
            "results": [
                {"title": r.get("title"), "url": r.get("href"), "snippet": r.get("body")}
                for r in results
            ],
        }
    except Exception as e:
        # Loud log so the agent loop operator sees this, not just a 119-char payload
        print(f"[tools] web_search FAILED: {type(e).__name__}: {e}", file=sys.stderr, flush=True)
        return {"error": f"Web search failed: {e}", "results": []}


# Tool schemas for the Anthropic API

TOOL_SCHEMAS = [
    {
        "name": "list_folder",
        "description": (
            "List files in one or all Minkowski source folders. "
            "Use this to understand what material is available before searching or reading. "
            "Folders: 01_Proposals, 02_Tools, 03_Pricing, 04_Experts, 05_Venues, 06_Marketing."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "folder": {
                    "type": "string",
                    "description": (
                        "Optional. Name of a specific folder to list, e.g. '04_Experts' or 'Proposals'. "
                        "Omit to list all folders."
                    ),
                }
            },
            "required": [],
        },
    },
    {
        "name": "read_file",
        "description": (
            "Read the full content of a file from the Minkowski source structure. "
            "Use after search_files or list_folder to retrieve actual content."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path to the file, e.g. '04_Experts/jane_doe.md'.",
                }
            },
            "required": ["path"],
        },
    },
    {
        "name": "search_files",
        "description": (
            "Search for files across the Minkowski source folders by keyword. "
            "Searches both filenames and file content. Returns ranked results with snippets. "
            "Always use this before generating any proposal, analysis, or expert match — "
            "never skip retrieval."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search terms, e.g. 'leadership futures banking sector'.",
                },
                "folders": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Optional. Restrict search to specific folders, "
                        "e.g. ['01_Proposals', '04_Experts']. Omit to search all."
                    ),
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "web_search",
        "description": (
            "Search the web for live information. "
            "Use this for every opportunity analysis to research: "
            "(1) the client company — recent news, strategy, leadership, challenges; "
            "(2) competitive landscape — who else competes with Minkowski for this type of work; "
            "(3) relevant market trends in the client's sector. "
            "Always run at least 2–3 web searches per opportunity analysis."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query, e.g. 'ING Bank leadership strategy 2025' or 'futures thinking leadership consultancy Netherlands competitors'.",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Number of results to return. Default 5.",
                },
            },
            "required": ["query"],
        },
    },
]


def dispatch(tool_name: str, tool_input: dict) -> str:
    """Dispatch a tool call and return result as string."""
    import json

    if tool_name == "list_folder":
        result = list_folder(tool_input.get("folder"))
    elif tool_name == "read_file":
        result = read_file(tool_input["path"])
    elif tool_name == "search_files":
        result = search_files(
            tool_input["query"],
            tool_input.get("folders"),
        )
    elif tool_name == "web_search":
        result = web_search(
            tool_input["query"],
            tool_input.get("max_results", 5),
        )
    else:
        result = {"error": f"Unknown tool: {tool_name}"}

    return json.dumps(result, ensure_ascii=False, indent=2)
