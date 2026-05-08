#!/usr/bin/env python3
"""
PDF text extractor — fallback for when the Read tool cannot read PDFs.
Usage: python3 read_pdf.py <path_to_pdf> [--pages 1-5]
"""

import sys
import argparse
import pypdf


def read_pdf(path: str, pages: str = None) -> str:
    reader = pypdf.PdfReader(path)
    total = len(reader.pages)

    if pages:
        parts = pages.split("-")
        start = int(parts[0]) - 1
        end = int(parts[1]) if len(parts) > 1 else start + 1
    else:
        start, end = 0, total

    lines = [f"PDF: {path}", f"Totaal pagina's: {total}", ""]
    for i in range(start, min(end, total)):
        lines.append(f"--- PAGINA {i+1} ---")
        text = reader.pages[i].extract_text()
        lines.append(text if text else "(geen tekst extraheerbaar op deze pagina)")
        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Lees tekst uit een PDF via pypdf.")
    parser.add_argument("path", help="Pad naar het PDF-bestand")
    parser.add_argument("--pages", help="Pagina-bereik, bijv. 1-5", default=None)
    args = parser.parse_args()

    try:
        print(read_pdf(args.path, args.pages))
    except FileNotFoundError:
        print(f"FOUT: Bestand niet gevonden: {args.path}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"FOUT bij lezen PDF: {e}", file=sys.stderr)
        sys.exit(1)
