#!/usr/bin/env python3
"""
CLI wrapper: read comments from a Google Doc.

Usage:
    python3 read_gdoc_comments.py <document_id>
    python3 read_gdoc_comments.py <document_id> --include-resolved

Requires ~/.minkowski_gdrive_token.json (run setup_gdrive_auth.py first).
"""

import argparse
import sys
from dotenv import load_dotenv
import os
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"), override=True)

from tools import read_doc_comments


def main():
    parser = argparse.ArgumentParser(description="Lees comments uit een Google Doc.")
    parser.add_argument("doc_id", help="Google Doc ID (uit de URL)")
    parser.add_argument("--include-resolved", action="store_true",
                        help="Toon ook opgeloste comments")
    args = parser.parse_args()

    result = read_doc_comments(args.doc_id, include_resolved=args.include_resolved)

    if "error" in result:
        print(f"FOUT: {result['error']}")
        sys.exit(1)

    comments = result["comments"]
    if not comments:
        print("Geen openstaande comments gevonden.")
        return

    print(f"\n{'='*60}")
    print(f"TOTAAL: {len(comments)} comment(s) — doc_id: {args.doc_id}")
    print(f"{'='*60}\n")

    for i, c in enumerate(comments, 1):
        resolved = "✅ Opgelost" if c["resolved"] else "🔴 Open"
        print(f"--- Comment {i} ---")
        print(f"Auteur:  {c['author']}")
        print(f"Datum:   {c['date']}")
        print(f"Status:  {resolved}")
        if c["quoted_text"]:
            q = c["quoted_text"]
            print(f"Over:    \"{q[:120]}{'...' if len(q) > 120 else ''}\"")
        print(f"Tekst:   {c['content']}")
        if c["replies"]:
            print(f"Replies ({len(c['replies'])}):")
            for r in c["replies"]:
                if r["action"] == "resolve":
                    print(f"  → {r['author']} heeft dit opgelost")
                elif r["content"]:
                    print(f"  → {r['author']}: {r['content']}")
        print()


if __name__ == "__main__":
    main()
