"""
Library:         lib_bejson_EBook_validator.py
Family:          EBook
Module Purpose:  Validation routines for manifest schemas, subpage routes, and directory hierarchies in EBook library family.
Architecture:    BEJSON 104 Ecosystem Component maintaining strict schema integrity and standardized runtime contracts.
Version:         1.0.0
Release_Version: 300
Date:            2026-11-11
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Format_Creator:  Elton Boehnen
RELATIONAL_ID:   480a0003-e000-11ef-9000-000000000003
License:         PolyForm-Noncommercial-1.0.0
"""

from pathlib import Path
from typing import Any, Dict, List, Tuple

try:
    from .lib_bejson_EBook_bejson_errors import (
        E_EBOOK_DUPLICATE_SLUG,
        E_EBOOK_MANIFEST_INVALID,
        E_EBOOK_ROUTING_FAILED,
        E_EBOOK_VALIDATION_FAILED,
        EBookError,
    )
    from .lib_bejson_EBook_core import EBookEntityRecord, load_manifest
except ImportError:
    from lib_bejson_EBook_bejson_errors import (
        E_EBOOK_DUPLICATE_SLUG,
        E_EBOOK_MANIFEST_INVALID,
        E_EBOOK_ROUTING_FAILED,
        E_EBOOK_VALIDATION_FAILED,
        EBookError,
    )
    from lib_bejson_EBook_core import EBookEntityRecord, load_manifest


def validate_manifest_records(records: List[EBookEntityRecord]) -> Tuple[bool, List[str]]:
    """Validate uniqueness of slugs and completeness of records in an e-book manifest."""
    errors: List[str] = []
    seen_slugs = set()

    for idx, rec in enumerate(records):
        if not rec.slug:
            errors.append(f"Record at index {idx} has an empty slug.")
        elif rec.slug in seen_slugs:
            errors.append(f"Duplicate slug detected: '{rec.slug}' at index {idx}.")
        else:
            seen_slugs.add(rec.slug)

        if not rec.title:
            errors.append(f"Record '{rec.slug}' is missing a title.")

        if not rec.subpage_rel_path:
            errors.append(f"Record '{rec.slug}' is missing subpage_rel_path.")

    return len(errors) == 0, errors


def validate_ebook_directory_structure(ebook_root: Path, records: List[EBookEntityRecord]) -> Tuple[bool, List[str]]:
    """
    Validate that an e-book portal directory strictly complies with the
    Multi-Page Web Architecture & Subpage Routing Invariant:
      - Master Hub exists at <ebook_root>/index.html
      - Every record's subpage exists at <ebook_root>/<subpage_rel_path>
      - No broken subpage endpoints
    """
    errors: List[str] = []
    ebook_root = Path(ebook_root).resolve()

    if not ebook_root.is_dir():
        errors.append(f"E-Book root directory does not exist: {ebook_root}")
        return False, errors

    master_hub = ebook_root / "index.html"
    if not master_hub.is_file():
        errors.append(f"Master index hub missing at: {master_hub}")

    for rec in records:
        expected_subpage = ebook_root / rec.subpage_rel_path
        if not expected_subpage.is_file():
            errors.append(f"Missing subpage for slug '{rec.slug}': {expected_subpage}")

    return len(errors) == 0, errors
