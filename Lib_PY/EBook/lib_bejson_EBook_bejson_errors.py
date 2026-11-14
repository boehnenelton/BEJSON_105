"""
Library:         lib_bejson_EBook_bejson_errors.py
Family:          EBook
Module Purpose:  Unified numeric error-code registry and exception classes for EBook library family.
Architecture:    BEJSON 104 Ecosystem Component maintaining strict schema integrity and standardized runtime contracts.
Version:         1.0.0
Release_Version: 300
Date:            2026-11-11
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Format_Creator:  Elton Boehnen
RELATIONAL_ID:   480a0001-e000-11ef-9000-000000000001
License:         PolyForm-Noncommercial-1.0.0
"""

from typing import Any, Dict, Optional

# ---------------------------------------------------------------------------
# EBook Error Codes (480-509)
# ---------------------------------------------------------------------------
E_EBOOK_VALIDATION_FAILED       = 480  # Manifest or subpage failed structural validation
E_EBOOK_MANIFEST_INVALID        = 481  # Manifest missing mandatory keys or values
E_EBOOK_SUBPAGE_FAILED          = 482  # Subpage compilation failed
E_EBOOK_DOCUMENT_NOT_FOUND      = 483  # Ingested Markdown document does not exist
E_EBOOK_WRITE_FAILED            = 484  # Atomic write of e-book document failed
E_EBOOK_DUPLICATE_SLUG          = 485  # Two documents resolved to the same subpage slug
E_EBOOK_EMPTY_CONTENT           = 486  # Ingested document is empty or whitespace only
E_EBOOK_DIRECTORY_INVALID       = 487  # Target e-book output directory cannot be created or accessed
E_EBOOK_RENDER_FAILED           = 488  # Template rendering failed during compilation
E_EBOOK_ROUTING_FAILED          = 489  # Breadcrumb rail or relative navigation link calculation failed

# 490-509 reserved for future EBook family error codes.


class EBookError(Exception):
    """Authoritative base exception for the EBook library family."""
    def __init__(self, message: str, code: int = E_EBOOK_VALIDATION_FAILED, context: Optional[Dict[str, Any]] = None):
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message
        self.context = context or {}
