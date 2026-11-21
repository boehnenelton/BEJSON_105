"""
Name:          lib_bejson_Index_scanner.py
Description:   Recursive directory scanner and image index compiler utilizing the Index library family.
Version:       1.0.0
Date Created:  2026-11-18
Author Credit: Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
License:       PolyForm-Noncommercial-1.0.0
RELATIONAL_ID: 7e4a9c10-3b2d-4f88-9a11-c502e81b4504
"""

import logging
import os
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from .lib_bejson_Index_core import (
    GROUP_SUMMARY_FIELDS,
    IMAGE_INDEX_FIELDS,
    SCHEMA_STANDARD_ID,
    bejson_index_validate_file,
)
from .lib_bejson_Index_heuristics import (
    build_h1_bejson_documents,
    cluster_h1_perceptual,
)
from .lib_bejson_Index_metadata import (
    SUPPORTED_EXTENSIONS,
    ImageMetadataRecord,
    extract_image_metadata,
)

logger = logging.getLogger("lib_bejson_Index.scanner")


def scan_directory_recursive(
    target_dir: Path,
    recursive: bool = True,
    supported_extensions: Optional[Set[str]] = None,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> Tuple[List[ImageMetadataRecord], List[str]]:
    """
    Recursively scan target_dir for supported image files and extract normalized metadata records.
    Returns (records, skipped_files).
    """
    target_dir = target_dir.resolve()
    extensions = supported_extensions or SUPPORTED_EXTENSIONS
    image_paths: List[Path] = []

    if recursive:
        for root, dirs, files in os.walk(target_dir):
            # Skip hidden folders and common index/git cache folders
            dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__"]
            for fname in files:
                p = Path(root) / fname
                if p.suffix.lower() in extensions:
                    image_paths.append(p)
    else:
        for entry in target_dir.iterdir():
            if entry.is_file() and entry.suffix.lower() in extensions:
                image_paths.append(entry)

    image_paths.sort()
    total_found = len(image_paths)
    logger.info("Found %d image candidates in %s (recursive=%s)", total_found, target_dir, recursive)

    records: List[ImageMetadataRecord] = []
    skipped: List[str] = []

    for idx, img_path in enumerate(image_paths, start=1):
        rec = extract_image_metadata(img_path, target_dir)
        if rec is not None:
            records.append(rec)
        else:
            skipped.append(str(img_path.relative_to(target_dir)))

        if progress_callback:
            progress_callback(idx, total_found, img_path.name)
        elif idx % 250 == 0 or idx == total_found:
            logger.info("Scan progress: %d / %d processed (%d valid, %d skipped)", idx, total_found, len(records), len(skipped))

    return records, skipped


def build_recursive_image_index(
    target_dir: Path,
    output_dir: Optional[Path] = None,
    recursive: bool = True,
    validate: bool = True,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> Dict[str, Any]:
    """
    Full pipeline: scan directory recursively, cluster using Index 1 visual hash heuristic,
    and persist validated BEJSON 104a index files.
    """
    start_time = time.time()
    target_dir = target_dir.resolve()
    out_dir = (output_dir or (target_dir / ".index")).resolve()

    logger.info("Commencing recursive image indexing on %s -> %s", target_dir, out_dir)

    # Step 1: Scan metadata
    records, skipped = scan_directory_recursive(
        target_dir=target_dir,
        recursive=recursive,
        progress_callback=progress_callback,
    )

    if not records:
        return {
            "success": False,
            "error": "No valid image files found in target directory.",
            "total_scanned": len(skipped),
            "valid_records": 0,
            "skipped_count": len(skipped),
            "target_dir": str(target_dir),
        }

    # Step 2: Cluster & generate BEJSON 104a files (Index 1 heuristic)
    idx_path, sum_path = build_h1_bejson_documents(records, out_dir)

    # Step 3: Validation
    idx_valid, idx_errors, idx_warnings = False, [], []
    sum_valid, sum_errors, sum_warnings = False, [], []
    if validate:
        idx_valid, idx_errors, idx_warnings = bejson_index_validate_file(idx_path)
        sum_valid, sum_errors, sum_warnings = bejson_index_validate_file(sum_path)

    elapsed_sec = round(time.time() - start_time, 2)

    return {
        "success": True,
        "schema_standard": SCHEMA_STANDARD_ID,
        "format": "BEJSON 104a",
        "heuristic": "Index 1: Visual Perceptual Hash (dHash<=7, pHash<=9)",
        "target_dir": str(target_dir),
        "output_dir": str(out_dir),
        "image_index_file": str(idx_path),
        "group_summary_file": str(sum_path),
        "total_images_scanned": len(records) + len(skipped),
        "indexed_images": len(records),
        "skipped_images": len(skipped),
        "elapsed_seconds": elapsed_sec,
        "validation": {
            "image_index_valid": idx_valid,
            "image_index_errors": idx_errors,
            "group_summary_valid": sum_valid,
            "group_summary_errors": sum_errors,
        },
    }
