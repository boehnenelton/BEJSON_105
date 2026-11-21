"""
Library:         lib_bejson_AI_Core_context_files.py
Family:          AI_Core
Module Purpose:  BEJSON 105 Persistent Context Imports & Active Turn Attachment Imports Manager
Architecture:    BEJSON 105 Multi-AI Gateway (Tier 2: Context Bubble Storage & Section Builders)
Version:         2.0.0
Release_Version: 300
Date:            2026-11-20
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Format_Creator:  Elton Boehnen
RELATIONAL_ID:   6f3a9c1e-8b2d-4e7f-9a1c-3d5e7f9b1c2a

Changelog:
  2.0.0 (2026-11-20) -- Ported from lib_bejson_AI_ai_context_files 1.0.0 (104 family AI) to BEJSON 105 AI_Core:
        * Context Imports stored in context_files.105a.bejson + imports/<file_id>.txt (persistent checked/unchecked state).
        * Attachment Imports stored in attachment_files.105a.bejson + attachments/<file_id>.txt (checked on import, auto-unchecked on send, supports iterative AI <file_modification> updates).
        * All BEJSON and file I/O routed strictly through lib_bejson_AI_Core_core_bridge.
"""
from __future__ import annotations

import logging
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

_SELF_DIR = Path(__file__).resolve().parent
if str(_SELF_DIR) not in sys.path:
    sys.path.insert(0, str(_SELF_DIR))

from lib_bejson_AI_Core_core_bridge import (  # noqa: E402
    core_add_record,
    core_field_map,
    core_load,
    core_new_document,
    core_rows_as_dicts,
    core_save,
    core_write_cell,
    core_write_text_file,
)
from lib_bejson_AI_Core_errors import AIException  # noqa: E402

VERSION = "2.0.0"
_logger = logging.getLogger("lib_bejson_AI_Core_context_files")

_CONTEXT_TRACKING_FILENAME = "context_files.105a.bejson"
_CONTEXT_IMPORTS_SUBDIR = "imports"

_ATTACHMENT_TRACKING_FILENAME = "attachment_files.105a.bejson"
_ATTACHMENT_IMPORTS_SUBDIR = "attachments"

_MAX_FILE_CHARS = 200_000

_FILE_FIELD_SPECS: Tuple[Tuple[str, str], ...] = (
    ("file_id", "string"),
    ("filename", "string"),
    ("enabled", "boolean"),
    ("char_count", "integer"),
    ("imported_at", "string"),
)


# ── Internal Store Helpers ────────────────────────────────────────────────────

def _tracking_path(base_dir: Path | str, tracking_filename: str) -> Path:
    return Path(base_dir) / tracking_filename


def _files_subdir(base_dir: Path | str, subdir_name: str) -> Path:
    return Path(base_dir) / subdir_name


def _content_path(base_dir: Path | str, subdir_name: str, file_id: str) -> Path:
    return _files_subdir(base_dir, subdir_name) / f"{file_id}.txt"


def _store_init(base_dir: Path | str, tracking_filename: str, subdir_name: str, records_type: str) -> Path:
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)
    _files_subdir(root, subdir_name).mkdir(parents=True, exist_ok=True)
    path = _tracking_path(root, tracking_filename)
    if not path.exists():
        doc = core_new_document(
            "105a",
            records_type,
            _FILE_FIELD_SPECS,
            Schema_Name=f"{records_type}Registry",
            Schema_Version="2.0.0",
        )
        core_save(path, doc)
    return path


def _store_load(base_dir: Path | str, tracking_filename: str, subdir_name: str, records_type: str) -> Dict[str, Any]:
    path = _store_init(base_dir, tracking_filename, subdir_name, records_type)
    try:
        return core_load(path)
    except AIException as exc:
        _logger.warning("Corrupt %s (%s); reinitializing.", path, exc)
        doc = core_new_document(
            "105a",
            records_type,
            _FILE_FIELD_SPECS,
            Schema_Name=f"{records_type}Registry",
            Schema_Version="2.0.0",
        )
        core_save(path, doc)
        return doc


def _store_save(base_dir: Path | str, tracking_filename: str, doc: Dict[str, Any]) -> None:
    core_save(_tracking_path(base_dir, tracking_filename), doc)


def _store_list(base_dir: Path | str, tracking_filename: str, subdir_name: str, records_type: str) -> List[Dict[str, Any]]:
    doc = _store_load(base_dir, tracking_filename, subdir_name, records_type)
    rows = core_rows_as_dicts(doc)
    out = [
        {
            "file_id": str(r.get("file_id") or ""),
            "filename": str(r.get("filename") or ""),
            "enabled": bool(r.get("enabled")),
            "checked": bool(r.get("enabled")),
            "char_count": int(r.get("char_count") or 0),
            "imported_at": str(r.get("imported_at") or ""),
            "record_uuid": str(r.get("record_uuid") or ""),
        }
        for r in rows
    ]
    out.sort(key=lambda r: r["imported_at"], reverse=True)
    return out


def _store_import(
    base_dir: Path | str,
    tracking_filename: str,
    subdir_name: str,
    records_type: str,
    filename: str,
    content: str,
    enabled_default: bool = True,
) -> Dict[str, Any]:
    if content is None:
        content = ""
    truncated = len(content) > _MAX_FILE_CHARS
    if truncated:
        content = content[:_MAX_FILE_CHARS]

    root = Path(base_dir)
    _store_init(root, tracking_filename, subdir_name, records_type)
    file_id = uuid.uuid4().hex[:12]
    clean_name = (filename or file_id).strip() or file_id
    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    core_write_text_file(_content_path(root, subdir_name, file_id), content)

    doc = _store_load(root, tracking_filename, subdir_name, records_type)
    rec = {
        "file_id": file_id,
        "filename": clean_name,
        "enabled": bool(enabled_default),
        "char_count": len(content),
        "imported_at": now_iso,
    }
    core_add_record(doc, rec)
    _store_save(root, tracking_filename, doc)

    if truncated:
        _logger.warning("Import '%s' truncated to %d chars.", clean_name, _MAX_FILE_CHARS)

    return {
        **rec,
        "checked": bool(enabled_default),
        "truncated": truncated,
    }


def _store_toggle(
    base_dir: Path | str,
    tracking_filename: str,
    subdir_name: str,
    records_type: str,
    file_id: str,
    explicit_state: Optional[bool] = None,
) -> Optional[bool]:
    doc = _store_load(base_dir, tracking_filename, subdir_name, records_type)
    for row in core_rows_as_dicts(doc):
        if row.get("file_id") == file_id:
            new_val = (not bool(row.get("enabled"))) if explicit_state is None else bool(explicit_state)
            core_write_cell(doc, row["record_uuid"], "enabled", new_val)
            _store_save(base_dir, tracking_filename, doc)
            return new_val
    return None


def _store_delete(
    base_dir: Path | str,
    tracking_filename: str,
    subdir_name: str,
    records_type: str,
    file_id: str,
) -> bool:
    doc = _store_load(base_dir, tracking_filename, subdir_name, records_type)
    fmap = core_field_map(doc)
    fid_idx = fmap["file_id"]
    rows = doc.get("Values", [])
    new_rows = [r for r in rows if r[fid_idx] != file_id]
    if len(new_rows) == len(rows):
        return False
    doc["Values"] = new_rows
    _store_save(base_dir, tracking_filename, doc)
    cpath = _content_path(base_dir, subdir_name, file_id)
    if cpath.exists():
        try:
            cpath.unlink()
        except OSError:
            pass
    return True


def _store_read(base_dir: Path | str, subdir_name: str, file_id: str) -> Optional[str]:
    cpath = _content_path(base_dir, subdir_name, file_id)
    if not cpath.is_file():
        return None
    try:
        return cpath.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        _logger.warning("Failed to read stored file %s: %s", file_id, exc)
        return None


# ── Context Imports Public API (Persistent Background Knowledge) ─────────────

def ai_context_files_init(context_dir: Path | str) -> Path:
    """Creates context_files.105a.bejson and imports/ if missing."""
    return _store_init(context_dir, _CONTEXT_TRACKING_FILENAME, _CONTEXT_IMPORTS_SUBDIR, "ContextFile")


def ai_context_files_list(context_dir: Path | str) -> List[Dict[str, Any]]:
    """Returns list of {file_id, filename, enabled, checked, char_count, imported_at} dicts, newest first."""
    return _store_list(context_dir, _CONTEXT_TRACKING_FILENAME, _CONTEXT_IMPORTS_SUBDIR, "ContextFile")


def ai_context_files_import(context_dir: Path | str, filename: str, content: str) -> Dict[str, Any]:
    """Stores content as a new tracked, enabled-by-default persistent context file."""
    return _store_import(
        context_dir, _CONTEXT_TRACKING_FILENAME, _CONTEXT_IMPORTS_SUBDIR, "ContextFile", filename, content, True
    )


def ai_context_files_toggle(
    context_dir: Path | str,
    file_id: str,
    enabled: Optional[bool] = None,
) -> Optional[bool]:
    """Flips or sets a persistent context file's enabled flag."""
    return _store_toggle(
        context_dir, _CONTEXT_TRACKING_FILENAME, _CONTEXT_IMPORTS_SUBDIR, "ContextFile", file_id, enabled
    )


def ai_context_files_delete(context_dir: Path | str, file_id: str) -> bool:
    """Removes a persistent context file's tracking record and stored content."""
    return _store_delete(context_dir, _CONTEXT_TRACKING_FILENAME, _CONTEXT_IMPORTS_SUBDIR, "ContextFile", file_id)


def ai_context_files_read(context_dir: Path | str, file_id: str) -> Optional[str]:
    """Reads the raw text content of a persistent context file."""
    return _store_read(context_dir, _CONTEXT_IMPORTS_SUBDIR, file_id)


def ai_context_files_build_section(
    constants: Dict[str, Any],
    cwd: str,
    config_dir: Path | str,
    context_dir: Path | str,
) -> Tuple[str, int]:
    """Concatenates the content of every enabled persistent context file."""
    files = ai_context_files_list(context_dir)
    enabled = [f for f in files if f["enabled"]]
    if not enabled:
        return "", 0

    blocks: List[str] = []
    for f in enabled:
        text = ai_context_files_read(context_dir, f["file_id"])
        if text is None:
            continue
        blocks.append(f"### {f['filename']}\n{text}")

    full_text = "\n\n".join(blocks)
    return full_text, len(full_text)


# ── Attachment Imports Public API (Active Turn Modification Sessions) ────────

def ai_attachment_files_init(context_dir: Path | str) -> Path:
    """Creates attachment_files.105a.bejson and attachments/ if missing."""
    return _store_init(context_dir, _ATTACHMENT_TRACKING_FILENAME, _ATTACHMENT_IMPORTS_SUBDIR, "AttachmentFile")


def ai_attachment_files_list(context_dir: Path | str) -> List[Dict[str, Any]]:
    """Returns list of {file_id, filename, enabled, checked, char_count, imported_at} dicts, newest first."""
    return _store_list(context_dir, _ATTACHMENT_TRACKING_FILENAME, _ATTACHMENT_IMPORTS_SUBDIR, "AttachmentFile")


def ai_attachment_files_import(context_dir: Path | str, filename: str, content: str) -> Dict[str, Any]:
    """Stores content as a new tracked attachment file (checked=True by default)."""
    return _store_import(
        context_dir,
        _ATTACHMENT_TRACKING_FILENAME,
        _ATTACHMENT_IMPORTS_SUBDIR,
        "AttachmentFile",
        filename,
        content,
        True,
    )


def ai_attachment_files_toggle(
    context_dir: Path | str,
    file_id: str,
    checked: Optional[bool] = None,
) -> Optional[bool]:
    """Flips or sets an attachment file's checked flag."""
    return _store_toggle(
        context_dir, _ATTACHMENT_TRACKING_FILENAME, _ATTACHMENT_IMPORTS_SUBDIR, "AttachmentFile", file_id, checked
    )


def ai_attachment_files_uncheck_all(
    context_dir: Path | str,
    file_ids: Optional[Iterable[str]] = None,
) -> List[str]:
    """
    Automatically unchecks attachment files after a chat prompt is sent so they
    are not re-sent on subsequent turns until explicitly checked again.
    Returns list of file_ids that were unchecked.
    """
    target_set = set(file_ids) if file_ids is not None else None
    doc = _store_load(context_dir, _ATTACHMENT_TRACKING_FILENAME, _ATTACHMENT_IMPORTS_SUBDIR, "AttachmentFile")
    unchecked_ids: List[str] = []
    for row in core_rows_as_dicts(doc):
        fid = str(row.get("file_id") or "")
        if not row.get("enabled"):
            continue
        if target_set is not None and fid not in target_set:
            continue
        core_write_cell(doc, row["record_uuid"], "enabled", False)
        unchecked_ids.append(fid)
    if unchecked_ids:
        _store_save(context_dir, _ATTACHMENT_TRACKING_FILENAME, doc)
    return unchecked_ids


def ai_attachment_files_update_content(
    context_dir: Path | str,
    filename_or_id: str,
    new_content: str,
) -> Optional[Dict[str, Any]]:
    """
    Updates an existing attachment's stored content (e.g. when applying an AI
    <file_modification> block) or imports it as a new attachment if not found.
    """
    if new_content is None:
        new_content = ""
    if len(new_content) > _MAX_FILE_CHARS:
        new_content = new_content[:_MAX_FILE_CHARS]

    doc = _store_load(context_dir, _ATTACHMENT_TRACKING_FILENAME, _ATTACHMENT_IMPORTS_SUBDIR, "AttachmentFile")
    target = (filename_or_id or "").strip()
    for row in core_rows_as_dicts(doc):
        if row.get("file_id") == target or row.get("filename") == target:
            fid = str(row["file_id"])
            core_write_text_file(_content_path(context_dir, _ATTACHMENT_IMPORTS_SUBDIR, fid), new_content)
            now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            core_write_cell(doc, row["record_uuid"], "char_count", len(new_content))
            core_write_cell(doc, row["record_uuid"], "imported_at", now_iso)
            _store_save(context_dir, _ATTACHMENT_TRACKING_FILENAME, doc)
            return {
                "file_id": fid,
                "filename": str(row["filename"]),
                "enabled": bool(row["enabled"]),
                "checked": bool(row["enabled"]),
                "char_count": len(new_content),
                "imported_at": now_iso,
            }
    return ai_attachment_files_import(context_dir, target or "modified_attachment.txt", new_content)


def ai_attachment_files_delete(context_dir: Path | str, file_id: str) -> bool:
    """Removes an attachment file's tracking record and stored content."""
    return _store_delete(
        context_dir, _ATTACHMENT_TRACKING_FILENAME, _ATTACHMENT_IMPORTS_SUBDIR, "AttachmentFile", file_id
    )


def ai_attachment_files_read(context_dir: Path | str, file_id: str) -> Optional[str]:
    """Reads the raw text content of an attachment file."""
    return _store_read(context_dir, _ATTACHMENT_IMPORTS_SUBDIR, file_id)
