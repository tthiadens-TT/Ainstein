import os
import re
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent

# Cache of (abs_path_str, mtime_ns) -> parsed text. Keeps one agent turn from
# re-parsing the same PDFs/DOCX repeatedly across search + read_file calls.
_READ_CACHE: dict[tuple[str, int], str] = {}
_READ_CACHE_MAX = 256

# Source layer = Google Drive (multi-user, single source of truth).
# Override AINSTEIN_SOURCE_ROOT to point elsewhere (e.g. another machine,
# a CI mount, or a future Drive-API-backed path) without touching code.
_DEFAULT_SOURCE_ROOT = (
    "/Users/thomasthiadens/Library/CloudStorage/"
    "GoogleDrive-tthiadens@gmail.com/.shortcut-targets-by-id/"
    "1ziMd8Zmhgpqq_iHyoz3-59_KwL7kbm7e/Minkowski    Thomas /AInstein"
)
SOURCE_ROOT = Path(os.environ.get("AINSTEIN_SOURCE_ROOT", _DEFAULT_SOURCE_ROOT))

_FOLDER_NAMES = [
    "01_Proposals",
    "02_Tools",
    "03_Pricing",
    "04_Experts",
    "05_Venues",
    "06_Marketing",
    "07_Feedback",
]

SOURCE_FOLDERS = {name: SOURCE_ROOT / name for name in _FOLDER_NAMES}

TEXT_EXTENSIONS = {".txt", ".md", ".pdf", ".docx", ".doc", ".rtf", ".csv", ".json", ".xlsx", ".xlsm", ".pptx", ".gdoc", ".gsheet", ".gslides", ".eml"}


def _log_source_health() -> None:
    """Log per-folder file counts at import time so a broken SOURCE_ROOT or
    missing folder is visible in the bot logs instead of silently degrading
    output quality."""
    root_ok = SOURCE_ROOT.exists()
    print(
        f"[tools] source health — SOURCE_ROOT exists: {root_ok} ({SOURCE_ROOT})",
        file=sys.stderr, flush=True,
    )
    for name, path in SOURCE_FOLDERS.items():
        try:
            n = sum(1 for p in path.rglob("*") if p.is_file() and not p.name.startswith("."))
        except OSError:
            n = 0
        warn = "  ⚠ THIN" if n <= 1 else ""
        print(f"[tools]   {name}: ({n} files){warn}", file=sys.stderr, flush=True)


_log_source_health()


# ---- OCR fallback (scanned PDFs → Claude vision) ----

OCR_MODEL = "claude-haiku-4-5-20251001"
OCR_MAX_PAGES = 20  # cap to keep cost predictable
OCR_RENDER_DPI = 200


def _ocr_pdf_via_vision(path: Path) -> str:
    """Render PDF pages to PNG and OCR them via Claude vision. Returns
    extracted text, or empty string on failure. Triggered only when pypdf
    found no embedded text."""
    import base64
    try:
        import fitz  # PyMuPDF
        import anthropic
    except ImportError as e:
        print(f"[tools] OCR unavailable: {e}", file=sys.stderr, flush=True)
        return ""

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("[tools] OCR skipped: ANTHROPIC_API_KEY not set", file=sys.stderr, flush=True)
        return ""

    try:
        doc = fitz.open(str(path))
    except Exception as e:
        print(f"[tools] OCR could not open PDF {path.name}: {e}", file=sys.stderr, flush=True)
        return ""

    n_pages = min(len(doc), OCR_MAX_PAGES)
    if len(doc) > OCR_MAX_PAGES:
        print(
            f"[tools] OCR capped at {OCR_MAX_PAGES} of {len(doc)} pages for {path.name}",
            file=sys.stderr, flush=True,
        )

    client = anthropic.Anthropic(api_key=api_key)
    parts = []
    for i in range(n_pages):
        try:
            page = doc.load_page(i)
            pix = page.get_pixmap(dpi=OCR_RENDER_DPI)
            png_b64 = base64.standard_b64encode(pix.tobytes("png")).decode()
        except Exception as e:
            print(f"[tools] OCR render failed page {i+1}: {e}", file=sys.stderr, flush=True)
            continue

        try:
            resp = client.messages.create(
                model=OCR_MODEL,
                max_tokens=2048,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": png_b64}},
                        {"type": "text", "text": (
                            "Extract all text from this page verbatim. Preserve structure "
                            "(headings, lists, tables) using plain markdown. Output only the "
                            "extracted text — no commentary. If the page is blank or has no "
                            "text, output exactly: [blank page]"
                        )},
                    ],
                }],
            )
            text = "\n".join(b.text for b in resp.content if b.type == "text").strip()
        except Exception as e:
            print(f"[tools] OCR API failed page {i+1}: {e}", file=sys.stderr, flush=True)
            continue

        if text and text != "[blank page]":
            parts.append(f"## Page {i+1} (OCR)\n{text}")

    doc.close()
    return "\n\n".join(parts)


# ---- Google Docs resolver (.gdoc stubs → live content) ----

GDOC_TOKEN_PATH = Path.home() / ".minkowski_gdrive_token.json"
GDOC_CREDS_PATH = Path.home() / ".minkowski_gdrive_credentials.json"
_GDOC_SERVICE = None


def _get_gdoc_service():
    """Build (and cache) a Google Drive API client. Returns None if
    credentials are not configured — callers must handle that gracefully."""
    global _GDOC_SERVICE
    if _GDOC_SERVICE is not None:
        return _GDOC_SERVICE
    if not GDOC_TOKEN_PATH.exists():
        return None
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        creds = Credentials.from_authorized_user_file(
            str(GDOC_TOKEN_PATH),
            scopes=["https://www.googleapis.com/auth/drive.readonly"],
        )
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            GDOC_TOKEN_PATH.write_text(creds.to_json())
        _GDOC_SERVICE = build("drive", "v3", credentials=creds, cache_discovery=False)
        return _GDOC_SERVICE
    except Exception as e:
        print(f"[tools] gdoc service init failed: {e}", file=sys.stderr, flush=True)
        return None


def _read_gdoc(path: Path) -> str:
    """Read a .gdoc / .gsheet stub by exporting the live document via the
    Drive API. Returns clear marker text if credentials missing or fetch
    fails — never raises into the caller."""
    import json as _json
    try:
        meta = _json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        return f"[Could not parse .gdoc stub: {e}]"
    doc_id = meta.get("doc_id")
    if not doc_id:
        return "[.gdoc stub has no doc_id]"

    service = _get_gdoc_service()
    if service is None:
        return (
            f"[.gdoc unresolved — Google Drive credentials not configured. "
            f"doc_id={doc_id}. Run setup_gdrive_auth.py to enable.]"
        )

    suffix = path.suffix.lower()
    mime = {
        ".gdoc":   "text/markdown",
        ".gsheet": "text/csv",
        ".gslides":"text/plain",
    }.get(suffix, "text/plain")

    try:
        data = service.files().export(fileId=doc_id, mimeType=mime).execute()
        if isinstance(data, bytes):
            data = data.decode("utf-8", errors="replace")
        return data or "[Google Doc returned empty content]"
    except Exception as e:
        return f"[.gdoc fetch failed for {path.name}: {e}]"


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
        if path.suffix.lower() in {".gdoc", ".gsheet", ".gslides"}:
            return _read_gdoc(path)
        if path.suffix.lower() == ".eml":
            from email import policy
            from email.parser import BytesParser
            with open(path, "rb") as fh:
                msg = BytesParser(policy=policy.default).parse(fh)
            headers = []
            for h in ("From", "To", "Cc", "Date", "Subject"):
                v = msg.get(h)
                if v:
                    headers.append(f"{h}: {v}")
            body_part = msg.get_body(preferencelist=("plain", "html"))
            body = ""
            if body_part is not None:
                body = body_part.get_content() or ""
                if body_part.get_content_type() == "text/html":
                    import re as _re
                    body = _re.sub(r"<[^>]+>", "", body)
                    body = _re.sub(r"\n{3,}", "\n\n", body).strip()
            attachments = [
                p.get_filename() for p in msg.iter_attachments() if p.get_filename()
            ]
            parts = ["\n".join(headers), "", body.strip()]
            if attachments:
                parts.append("")
                parts.append("Attachments: " + ", ".join(attachments))
            return "\n".join(parts).strip()
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
            if parts:
                return "\n\n".join(parts)
            # No embedded text — try OCR via Claude vision
            ocr = _ocr_pdf_via_vision(path)
            if ocr:
                return ocr
            return "[PDF has no extractable text — may be scanned images, OCR also returned nothing]"
        if path.suffix.lower() == ".pptx":
            from pptx import Presentation
            prs = Presentation(str(path))
            parts = []
            for i, slide in enumerate(prs.slides, start=1):
                slide_lines = [f"## Slide {i}"]
                for shape in slide.shapes:
                    if shape.has_text_frame:
                        for para in shape.text_frame.paragraphs:
                            text = "".join(run.text for run in para.runs).strip()
                            if text:
                                slide_lines.append(text)
                    if shape.has_table:
                        for row in shape.table.rows:
                            row_text = " | ".join(c.text.strip() for c in row.cells if c.text.strip())
                            if row_text:
                                slide_lines.append(row_text)
                if slide.has_notes_slide:
                    notes = slide.notes_slide.notes_text_frame.text.strip()
                    if notes:
                        slide_lines.append(f"[Notes] {notes}")
                if len(slide_lines) > 1:
                    parts.append("\n".join(slide_lines))
            return "\n\n".join(parts) if parts else "[PPTX has no extractable text]"
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
    Accepts absolute paths or paths relative to SOURCE_ROOT (or BASE_DIR for repo files).
    """
    target = Path(path)

    if not target.is_absolute():
        candidate = SOURCE_ROOT / path.lstrip("/")
        if candidate.exists():
            target = candidate
        else:
            candidate = BASE_DIR / path.lstrip("/")
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


def record_correction(
    bot_excerpt: str,
    user_correction: str,
    feedback_type: str,
    category: str,
    skill: str | None = None,
    thread_id: str | None = None,
) -> dict:
    """Log an inline mid-conversation correction to 07_Feedback/gaps.md.

    Use when the user explicitly corrects something Ainstein just said
    ("nee, dat klopt niet", "je vergeet X"). The agent must propose a
    type+category and confirm with the user BEFORE calling this tool.

    feedback_type: "technical" | "qualitative"
    category:      one of the fixed sub-labels (see 07_Feedback/README.md)
    """
    # Imported lazily to avoid a circular import at module load (feedback.py
    # imports SOURCE_ROOT from this module).
    from feedback import capture_feedback

    capture_feedback(
        thread_id=thread_id or "inline",
        user_id="inline",
        user_name=None,
        skill=skill,
        bot_excerpt=bot_excerpt,
        user_comment=user_correction,
        feedback_type=feedback_type,
        category=category,
        source="inline",
    )
    return {
        "status": "logged",
        "type": feedback_type,
        "category": category,
        "skill": skill,
        "note": "Saved to 07_Feedback/gaps.md. Will surface in future answers + /feedback-review.",
    }


def web_search(query: str, max_results: int = 5) -> dict:
    """
    Search the web using DuckDuckGo. Use for live company research,
    market context, competitive landscape, and recent news.
    """
    try:
        from ddgs import DDGS
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
        "name": "record_correction",
        "description": (
            "Log an inline mid-conversation correction to 07_Feedback/gaps.md. "
            "Call this ONLY after the user has confirmed the proposed type+category. "
            "Use when the user explicitly says you got something wrong "
            "('nee dat klopt niet', 'je vergeet X', 'dit moet anders'). "
            "Always classify and confirm BEFORE calling — never log without explicit user OK."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "bot_excerpt": {
                    "type": "string",
                    "description": "The part of your previous answer that was wrong or weak (max ~500 chars).",
                },
                "user_correction": {
                    "type": "string",
                    "description": "What the user said is wrong / what should be different.",
                },
                "feedback_type": {
                    "type": "string",
                    "enum": ["technical", "qualitative"],
                    "description": (
                        "technical = bot misunderstood, hallucinated, picked wrong source, tool error. "
                        "qualitative = answer was technically correct but commercially or qualitatively weak."
                    ),
                },
                "category": {
                    "type": "string",
                    "enum": [
                        # technical
                        "hallucinatie", "context-misverstand", "onleesbaar-bestand",
                        "tool-fout", "verkeerde-bron-gekozen",
                        # qualitative
                        "commercieel-zwak", "tone-of-voice", "missende-inhoud",
                        "verkeerde-logica", "niet-Minkowski", "te-generiek",
                    ],
                    "description": "Sub-label confirmed with the user.",
                },
                "skill": {
                    "type": "string",
                    "description": "Skill name if known (e.g. 'analyse_opportunity'). Optional.",
                },
                "thread_id": {
                    "type": "string",
                    "description": "Thread or conversation id if available. Optional.",
                },
            },
            "required": ["bot_excerpt", "user_correction", "feedback_type", "category"],
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
    elif tool_name == "record_correction":
        result = record_correction(
            bot_excerpt=tool_input["bot_excerpt"],
            user_correction=tool_input["user_correction"],
            feedback_type=tool_input["feedback_type"],
            category=tool_input["category"],
            skill=tool_input.get("skill"),
            thread_id=tool_input.get("thread_id"),
        )
    elif tool_name == "web_search":
        result = web_search(
            tool_input["query"],
            tool_input.get("max_results", 5),
        )
    else:
        result = {"error": f"Unknown tool: {tool_name}"}

    return json.dumps(result, ensure_ascii=False, indent=2)
