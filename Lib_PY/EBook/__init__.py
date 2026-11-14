"""
Package:         EBook (lib_bejson_ebook)
Family:          EBook
Module Purpose:  Package initialization and canonical exports for the lib_bejson_ebook family.
Architecture:    BEJSON 104 Ecosystem Component enforcing Multi-Page Web Architecture & Subpage Routing Invariants.
Version:         1.0.0
Release_Version: 300
Date:            2026-11-11
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Format_Creator:  Elton Boehnen
RELATIONAL_ID:   480a0007-e000-11ef-9000-000000000007
License:         PolyForm-Noncommercial-1.0.0
"""

from .lib_bejson_EBook_bejson_errors import (
    E_EBOOK_VALIDATION_FAILED,
    E_EBOOK_MANIFEST_INVALID,
    E_EBOOK_SUBPAGE_FAILED,
    E_EBOOK_DOCUMENT_NOT_FOUND,
    E_EBOOK_WRITE_FAILED,
    E_EBOOK_DUPLICATE_SLUG,
    E_EBOOK_EMPTY_CONTENT,
    E_EBOOK_DIRECTORY_INVALID,
    E_EBOOK_RENDER_FAILED,
    E_EBOOK_ROUTING_FAILED,
    EBookError,
)

from .lib_bejson_EBook_core import (
    MANIFEST_FIELDS,
    EBookEntityRecord,
    bejson_atomic_write,
    compute_file_sha256,
    format_inline_markdown,
    load_manifest,
    parse_markdown_document,
    sanitize_slug,
    save_manifest,
)

from .lib_bejson_EBook_validator import (
    validate_manifest_records,
    validate_ebook_directory_structure,
)

from .lib_bejson_EBook_renderer import (
    get_shared_becss_tokens,
    render_master_hub_html,
    render_subpage_html,
)

from .lib_bejson_EBook_orchestrator import (
    orchestrate_ebook_compilation,
)

__all__ = [
    "EBookError",
    "E_EBOOK_VALIDATION_FAILED",
    "E_EBOOK_MANIFEST_INVALID",
    "E_EBOOK_SUBPAGE_FAILED",
    "E_EBOOK_DOCUMENT_NOT_FOUND",
    "E_EBOOK_WRITE_FAILED",
    "E_EBOOK_DUPLICATE_SLUG",
    "E_EBOOK_EMPTY_CONTENT",
    "E_EBOOK_DIRECTORY_INVALID",
    "E_EBOOK_RENDER_FAILED",
    "E_EBOOK_ROUTING_FAILED",
    "MANIFEST_FIELDS",
    "EBookEntityRecord",
    "bejson_atomic_write",
    "compute_file_sha256",
    "format_inline_markdown",
    "load_manifest",
    "parse_markdown_document",
    "sanitize_slug",
    "save_manifest",
    "validate_manifest_records",
    "validate_ebook_directory_structure",
    "get_shared_becss_tokens",
    "render_master_hub_html",
    "render_subpage_html",
    "orchestrate_ebook_compilation",
]
