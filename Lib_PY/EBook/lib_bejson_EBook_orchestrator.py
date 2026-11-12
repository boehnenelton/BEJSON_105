"""
Library:         lib_bejson_EBook_orchestrator.py
Family:          EBook
Module Purpose:  High-level isolated compilation and lifecycle orchestrator for EBook library family.
Architecture:    BEJSON 104 Ecosystem Component enforcing Multi-Page Web Architecture & Subpage Routing Invariants.
Version:         1.0.0
Release_Version: 300
Date:            2026-11-11
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Format_Creator:  Elton Boehnen
RELATIONAL_ID:   480a0005-e000-11ef-9000-000000000005
License:         PolyForm-Noncommercial-1.0.0
"""

from datetime import datetime, timezone
import logging
import os
from pathlib import Path
import shutil
from typing import Any, Dict, List, Optional, Tuple

try:
    from .lib_bejson_EBook_bejson_errors import (
        E_EBOOK_DOCUMENT_NOT_FOUND,
        E_EBOOK_WRITE_FAILED,
        EBookError,
    )
    from .lib_bejson_EBook_core import (
        EBookEntityRecord,
        bejson_atomic_write,
        compute_file_sha256,
        load_manifest,
        parse_markdown_document,
        sanitize_slug,
        save_manifest,
    )
    from .lib_bejson_EBook_renderer import (
        render_master_hub_html,
        render_subpage_html,
    )
except ImportError:
    from lib_bejson_EBook_bejson_errors import (
        E_EBOOK_DOCUMENT_NOT_FOUND,
        E_EBOOK_WRITE_FAILED,
        EBookError,
    )
    from lib_bejson_EBook_core import (
        EBookEntityRecord,
        bejson_atomic_write,
        compute_file_sha256,
        load_manifest,
        parse_markdown_document,
        sanitize_slug,
        save_manifest,
    )
    from lib_bejson_EBook_renderer import (
        render_master_hub_html,
        render_subpage_html,
    )

LOG: logging.Logger = logging.getLogger("bejson_ebook.orchestrator")


def orchestrate_ebook_compilation(
    markdown_files: List[Path],
    ebook_root_dir: Path,
    taxonomy: str = "transcripts",
    portal_title: str = "Audio & Video Transcripts E-Book",
    portal_subtitle: str = "Verbatim Dialogue Records & Semantic Subpage Portal",
    theme: str = "dark",
    move_legacy_files: Optional[List[Path]] = None,
) -> Dict[str, Any]:
    """
    Orchestrates the complete lifecycle of a multi-page e-book portal:
      1. Isolates publication inside dedicated ebook_root_dir
      2. Moves legacy monolithic exports into archive/
      3. Detects existing e-book manifest and state
      4. Ingests new or modified Markdown files
      5. Generates dedicated subpages at <ebook_root>/<taxonomy>/pages/<slug>/index.html
      6. Recompiles Master Hub (<ebook_root>/index.html), Taxonomy Hub, and Directory Index
      7. Saves updated canonical BEJSON 104a manifest
    """
    ebook_root = Path(ebook_root_dir).resolve()
    ebook_root.mkdir(parents=True, exist_ok=True)

    archive_dir = ebook_root / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)

    # 1. Clean up / move legacy monolithic files
    if move_legacy_files:
        for leg_file in move_legacy_files:
            leg_path = Path(leg_file).resolve()
            if leg_path.is_file():
                dest = archive_dir / leg_path.name
                shutil.move(str(leg_path), str(dest))
                LOG.info("[lib_bejson_ebook] Moved legacy file: %s -> %s", leg_path.name, dest)

    # 2. Detect existing manifest state
    manifest_file = ebook_root / "ebook_manifest.bejson"
    existing_records = load_manifest(manifest_file)
    record_map: Dict[str, EBookEntityRecord] = {r.slug: r for r in existing_records}

    # 3. Parse and ingest documents
    parsed_docs: Dict[str, Dict[str, Any]] = {}
    new_ingest_count = 0

    for md_file in markdown_files:
        md_path = Path(md_file).resolve()
        if not md_path.is_file():
            continue

        raw_content = md_path.read_text(encoding="utf-8")
        parsed = parse_markdown_document(raw_content)

        slug = sanitize_slug(parsed["title"])
        # Avoid slug collisions
        base_slug = slug
        collision_counter = 2
        while slug in parsed_docs and parsed_docs[slug]["source_file"] != str(md_path):
            slug = f"{base_slug}-{collision_counter}"
            collision_counter += 1

        file_sha = compute_file_sha256(md_path)
        subpage_rel = f"{taxonomy}/pages/{slug}/index.html"

        is_new = slug not in record_map or record_map[slug].source_sha256 != file_sha
        if is_new:
            new_ingest_count += 1

        rec = EBookEntityRecord(
            slug=slug,
            title=parsed["title"],
            taxonomy=taxonomy,
            source_file=str(md_path),
            source_sha256=file_sha,
            word_count=parsed["word_count"],
            reading_time_minutes=parsed["reading_time_minutes"],
            sections_count=len(parsed["sections"]),
            excerpt=parsed["excerpt"],
            subpage_rel_path=subpage_rel,
            updated_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        )
        record_map[slug] = rec
        parsed["source_file"] = str(md_path)
        parsed_docs[slug] = parsed

    # 4. Sort records deterministically (by title)
    ordered_records = sorted(record_map.values(), key=lambda r: r.title.lower())
    total_records = len(ordered_records)

    # 5. Compile dedicated subpages with Prev/Next chaining
    subpages_dir = ebook_root / taxonomy / "pages"
    subpages_dir.mkdir(parents=True, exist_ok=True)

    for idx, rec in enumerate(ordered_records, 1):
        parsed = parsed_docs.get(rec.slug)
        if not parsed:
            # Load from source file if cached
            src = Path(rec.source_file)
            if src.is_file():
                parsed = parse_markdown_document(src.read_text(encoding="utf-8"))
            else:
                continue

        prev_rec = ordered_records[idx - 2] if idx > 1 else None
        next_rec = ordered_records[idx] if idx < total_records else None

        subpage_html = render_subpage_html(
            parsed_doc=parsed,
            slug=rec.slug,
            current_index=idx,
            total_count=total_records,
            taxonomy=taxonomy,
            prev_record=prev_rec,
            next_record=next_rec,
            relative_hub_path="../../index.html",
            relative_taxonomy_path="../index.html",
            theme=theme,
        )

        subpage_dest = ebook_root / rec.subpage_rel_path
        bejson_atomic_write(subpage_dest, subpage_html)

    # 6. Recompile Navigation Hubs
    # A. Master Hub: <ebook_root>/index.html
    master_hub_html = render_master_hub_html(
        manifest_records=ordered_records,
        portal_title=portal_title,
        portal_subtitle=portal_subtitle,
        theme=theme,
        taxonomy_name=taxonomy,
    )
    bejson_atomic_write(ebook_root / "index.html", master_hub_html)

    # B. Taxonomy Hub: <ebook_root>/<taxonomy>/index.html
    taxonomy_hub = ebook_root / taxonomy
    taxonomy_hub.mkdir(parents=True, exist_ok=True)
    # Adjust relative paths for taxonomy hub
    taxonomy_records = [
        EBookEntityRecord(
            slug=r.slug,
            title=r.title,
            taxonomy=r.taxonomy,
            source_file=r.source_file,
            source_sha256=r.source_sha256,
            word_count=r.word_count,
            reading_time_minutes=r.reading_time_minutes,
            sections_count=r.sections_count,
            excerpt=r.excerpt,
            subpage_rel_path=f"pages/{r.slug}/index.html",
            updated_utc=r.updated_utc,
        )
        for r in ordered_records
    ]
    tax_hub_html = render_master_hub_html(
        manifest_records=taxonomy_records,
        portal_title=f"{portal_title} · {taxonomy.title()} Index",
        portal_subtitle=f"Directory of {taxonomy.title()} subpages",
        theme=theme,
        taxonomy_name=taxonomy,
    )
    bejson_atomic_write(taxonomy_hub / "index.html", tax_hub_html)

    # C. Subpage Directory Index: <ebook_root>/<taxonomy>/pages/index.html
    pages_hub = ebook_root / taxonomy / "pages"
    pages_hub.mkdir(parents=True, exist_ok=True)
    pages_records = [
        EBookEntityRecord(
            slug=r.slug,
            title=r.title,
            taxonomy=r.taxonomy,
            source_file=r.source_file,
            source_sha256=r.source_sha256,
            word_count=r.word_count,
            reading_time_minutes=r.reading_time_minutes,
            sections_count=r.sections_count,
            excerpt=r.excerpt,
            subpage_rel_path=f"{r.slug}/index.html",
            updated_utc=r.updated_utc,
        )
        for r in ordered_records
    ]
    pages_hub_html = render_master_hub_html(
        manifest_records=pages_records,
        portal_title=f"{portal_title} · Subpages Directory",
        portal_subtitle="Direct directory listing of all compiled document subpages",
        theme=theme,
        taxonomy_name=taxonomy,
    )
    bejson_atomic_write(pages_hub / "index.html", pages_hub_html)

    # 7. Save updated manifest
    save_manifest(manifest_file, ordered_records)
    LOG.info("[lib_bejson_ebook] Manifest synchronized: %d records (%d new/updated)", total_records, new_ingest_count)

    return {
        "ebook_root": str(ebook_root),
        "total_records": total_records,
        "new_ingests": new_ingest_count,
        "manifest_path": str(manifest_file),
        "master_hub": str(ebook_root / "index.html"),
    }
