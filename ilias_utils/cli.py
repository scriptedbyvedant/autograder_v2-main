# ilias_utils/cli.py
import os
import json
import argparse
from .zip_parser import parse_ilias_zip, save_manifest, load_manifest, extract_student_files
from .manifest_adapter import build_items_from_ingest


def main():
    ap = argparse.ArgumentParser(description="ILIAS ZIP utilities (standalone; safe).")
    sub = ap.add_subparsers(dest="cmd", required=True)

    # parse → manifest.json
    p_parse = sub.add_parser("parse", help="Parse ILIAS ZIP and write a manifest JSON.")
    p_parse.add_argument("zip_path", help="Path to assignment-*.zip")
    p_parse.add_argument("--out", help="Output JSON path (default: <zip_basename>_manifest.json)")

    # extract → files into sandbox dir
    p_ext = sub.add_parser("extract", help="Extract submissions/* to a sandbox directory.")
    p_ext.add_argument("zip_path", help="Path to assignment-*.zip")
    p_ext.add_argument("--dest", required=True, help="Destination directory")
    p_ext.add_argument("--only-students", nargs="*", help='Raw folder names to include (exact match), e.g. "Doe John john@x.com 123456"')

    # items → map manifest + question spec → grading-ready items JSON
    p_items = sub.add_parser("items", help="Build grading items from an existing manifest and a question manifest.")
    p_items.add_argument("--manifest", required=True, help="Path to previously saved manifest JSON")
    p_items.add_argument("--questions", required=True, help="Path to assignment question manifest JSON")
    p_items.add_argument("--out", required=True, help="Where to write items JSON")

    args = ap.parse_args()

    if args.cmd == "parse":
        res = parse_ilias_zip(args.zip_path)
        out = args.out or os.path.splitext(args.zip_path)[0] + "_manifest.json"
        save_manifest(res, out)
        print(f"Manifest saved → {out}")
        print(f"Students parsed: {len(res.student_folders)}")
        if res.excel_path:
            print(f"Found Excel: {res.excel_path}")

    elif args.cmd == "extract":
        n = extract_student_files(args.zip_path, args.dest, args.only_students)
        print(f"Extracted {n} files to: {args.dest}")

    elif args.cmd == "items":
        ingest = load_manifest(args.manifest)
        with open(args.questions, "r", encoding="utf-8") as f:
            qman = json.load(f)
        items = build_items_from_ingest(ingest, qman)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        print(f"Wrote {len(items)} items → {args.out}")


if __name__ == "__main__":
    main()
