#!/usr/bin/env python3
"""
CLI:             cli.py
Family:          EBook
Module Purpose:  Command-line interface for the lib_bejson_ebook publication and multi-page portal engine.
Architecture:    BEJSON 104 Ecosystem Component enforcing Multi-Page Web Architecture & Subpage Routing Invariants.
Version:         1.0.0
Release_Version: 300
Date:            2026-11-11
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Format_Creator:  Elton Boehnen
RELATIONAL_ID:   480a0006-e000-11ef-9000-000000000006
License:         PolyForm-Noncommercial-1.0.0
"""

import argparse
import logging
from pathlib import Path
import sys

try:
    from .lib_bejson_EBook_orchestrator import orchestrate_ebook_compilation
except ImportError:
    from lib_bejson_EBook_orchestrator import orchestrate_ebook_compilation

DIVIDER_49: str = "=" * 49
SUBDIVIDER_49: str = "-" * 49


def main() -> int:
    parser = argparse.ArgumentParser(
        description="lib_bejson_ebook: Multi-Page E-Book & Documentation Portal Builder (No html3)."
    )
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="Input Markdown file or directory containing .md documents",
    )
    parser.add_argument(
        "--output", "-o",
        required=True,
        help="Destination directory for e-book portal (e.g. out/ebook/)",
    )
    parser.add_argument(
        "--taxonomy", "-t",
        default="transcripts",
        help="Taxonomy folder name (default: transcripts)",
    )
    parser.add_argument(
        "--title",
        default="Audio & Video Transcripts E-Book",
        help="Title for the Master E-Book Portal",
    )
    parser.add_argument(
        "--theme",
        choices=["dark", "light"],
        default="dark",
        help="Default color theme (dark/light)",
    )

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

    in_path = Path(args.input).resolve()
    if not in_path.exists():
        sys.stderr.write(f"Error: Input path not found: {in_path}\n")
        return 1

    md_files = []
    if in_path.is_file():
        md_files = [in_path]
    elif in_path.is_dir():
        md_files = sorted(in_path.glob("**/*.md"))

    if not md_files:
        sys.stderr.write(f"Error: No Markdown files found in {in_path}\n")
        return 1

    out_dir = Path(args.output).resolve()
    res = orchestrate_ebook_compilation(
        markdown_files=md_files,
        ebook_root_dir=out_dir,
        taxonomy=args.taxonomy,
        portal_title=args.title,
        theme=args.theme,
    )

    print(DIVIDER_49)
    print("lib_bejson_ebook Compilation Complete")
    print(SUBDIVIDER_49)
    print(f"E-Book Root:  {res['ebook_root']}")
    print(f"Master Hub:   {res['master_hub']}")
    print(f"Total Pages:  {res['total_records']}")
    print(f"New Ingests:  {res['new_ingests']}")
    print(DIVIDER_49)
    return 0


if __name__ == "__main__":
    sys.exit(main())
