"""
Library:         lib_bejson_AI_Core_core_bridge.py
Family:          AI_Core
Module Purpose:  The single point where AI_Core touches the main Core family. Core is used
                 ONLY for reading and writing BEJSON (load, validate, atomic write, field
                 map, add record). Nothing else in AI_Core opens a BEJSON file directly.
Architecture:    AI_Core depends on Core for BEJSON data handling; Core never depends on AI_Core.
Version:         2.1.0
Release_Version: 300
Date:            2026-11-20
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Format_Creator:  Elton Boehnen
RELATIONAL_ID:   5b0c7e1d-3a64-4f2b-9d85-c1a47e90b2f3
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

_SELF_DIR = Path(__file__).resolve().parent
if str(_SELF_DIR) not in sys.path:
    sys.path.insert(0, str(_SELF_DIR))

from lib_bejson_AI_Core_errors import (
    AIException,
    ERR_AI_CORE_DEP_UNAVAILABLE,
    ERR_AI_DOCUMENT_INVALID,
    ERR_AI_DOCUMENT_WRITE_FAILED,
)

VERSION = "2.1.0"
_LOGGER = logging.getLogger("lib_bejson_AI_Core_core_bridge")
_HERE = Path(__file__).resolve().parent
_CORE_MARKER = "lib_bejson_Core_bejson_core.py"


def core_locate_directory() -> Path:
    """Find the Core family: $BEJSON_CORE_DIR, a vendored copy beside this file
    (projects copy families into lib/), a sibling ../Core, or $ADMIN_LIBRARIES_105/Lib_PY/Core."""
    candidates: List[Path] = []
    override = os.environ.get("BEJSON_CORE_DIR")
    if override:
        candidates.append(Path(override).expanduser())
    candidates += [_HERE, _HERE.parent / "Core"]
    root = os.environ.get("ADMIN_LIBRARIES_105")
    if root:
        candidates.append(Path(root).expanduser() / "Lib_PY" / "Core")
    for candidate in candidates:
        if (candidate / _CORE_MARKER).is_file():
            return candidate.resolve()
    raise AIException(ERR_AI_CORE_DEP_UNAVAILABLE, "searched: " + ", ".join(str(c) for c in candidates))


_CORE_DIR = core_locate_directory()
if str(_CORE_DIR) not in sys.path:
    sys.path.insert(0, str(_CORE_DIR))

import lib_bejson_Core_bejson_core as _core  # noqa: E402
import lib_bejson_Core_bejson_chunking as _chunking  # noqa: E402
import lib_bejson_Core_bejson_validator as _validator  # noqa: E402


def core_directory() -> Path:
    return _CORE_DIR


def core_field_map(doc: Dict[str, Any]) -> Dict[str, int]:
    """name -> row position (record_uuid offset already applied on 105-series)."""
    return _core.bejson_core_get_field_map(doc)


def core_validate(doc: Dict[str, Any]) -> List[str]:
    """Core validation errors for an in-memory document ([] = valid)."""
    result = _validator.validate_bejson(doc)
    return list(result.errors)


def core_new_document(
    format_version: str,
    records_type: str,
    fields: Sequence[Tuple[str, str]],
    **custom_headers: Any,
) -> Dict[str, Any]:
    """New empty 105 / 105a document; fields get Core-stamped field_uuids. Custom headers only on 105a."""
    if format_version not in ("105", "105a"):
        raise AIException(ERR_AI_DOCUMENT_INVALID, f"unsupported format {format_version!r}")
    if custom_headers and format_version != "105a":
        raise AIException(ERR_AI_DOCUMENT_INVALID, "custom headers require Format 105a")
    doc: Dict[str, Any] = {
        "Format": "BEJSON",
        "Format_Version": format_version,
        "Format_Creator": "Elton Boehnen",
        "Records_Type": [records_type],
    }
    doc.update(custom_headers)
    doc["Fields"] = []
    doc["Values"] = []
    for name, field_type in fields:
        _core.bejson_core_define_field(doc, name, field_type)
    return doc


def core_add_record(doc: Dict[str, Any], values_by_name: Dict[str, Any]) -> str:
    """Append a row from a name->value dict (missing fields become null). Returns record_uuid."""
    names = [f["name"] for f in doc["Fields"]]
    unknown = set(values_by_name) - set(names)
    if unknown:
        raise AIException(ERR_AI_DOCUMENT_INVALID, f"unknown fields: {sorted(unknown)}")
    return _core.bejson_core_add_record_105(doc, [values_by_name.get(n) for n in names])


def core_write_cell(doc: Dict[str, Any], record_uuid: str, field_name: str, value: Any) -> None:
    """Type-checked cell write addressed by (record_uuid, field name) through Core's write_cell."""
    field_uuid = next((f.get("field_uuid") for f in doc.get("Fields", []) if f.get("name") == field_name), None)
    if field_uuid is None:
        raise AIException(ERR_AI_DOCUMENT_INVALID, f"unknown field {field_name!r}")
    try:
        _core.bejson_core_write_cell(doc, record_uuid, field_uuid, value)
    except _core.BEJSONCoreError as exc:
        raise AIException(ERR_AI_DOCUMENT_INVALID, str(exc)) from exc


def core_define_field(doc: Dict[str, Any], name: str, field_type: str) -> str:
    """Append a field (null-padding existing rows) through Core; returns the field_uuid."""
    try:
        return _core.bejson_core_define_field(doc, name, field_type)
    except _core.BEJSONCoreError as exc:
        raise AIException(ERR_AI_DOCUMENT_INVALID, str(exc)) from exc


def core_rows_as_dicts(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Rows as name->value dicts plus 'record_uuid', read through the field map."""
    fmap = core_field_map(doc)
    return [
        {**{name: row[idx] for name, idx in fmap.items() if idx < len(row)}, "record_uuid": row[0]}
        for row in doc.get("Values", [])
    ]


def core_load(path: Path | str, *, validate: bool = True) -> Dict[str, Any]:
    """Read a BEJSON file through Core. Raises AIException(ERR_AI_DOCUMENT_INVALID) on read/validation failure."""
    doc = _core.bejson_core_load_file(str(path))
    if doc is None:
        raise AIException(ERR_AI_DOCUMENT_INVALID, f"unreadable: {path}")
    if validate:
        result = _validator.validate_bejson(str(path), is_file=True)
        if not result.valid:
            raise AIException(ERR_AI_DOCUMENT_INVALID, f"{path}: {'; '.join(result.errors)}")
    return doc


def core_save(path: Path | str, doc: Dict[str, Any], *, validate: bool = True) -> None:
    """Validate then write atomically through Core. Raises AIException(ERR_AI_DOCUMENT_WRITE_FAILED)."""
    if validate:
        errors = core_validate(doc)
        if errors:
            raise AIException(ERR_AI_DOCUMENT_INVALID, "; ".join(errors))
    if not _core.bejson_core_atomic_write(str(path), doc):
        raise AIException(ERR_AI_DOCUMENT_WRITE_FAILED, str(path))


def core_lock(path: Path | str, timeout_seconds: int = 10):
    """Core's stale-safe lock for read-modify-write cycles: `with core_lock(p): ...`."""
    return _core.ResilientPIDLock(str(path), timeout_seconds)


def core_quarantine(path: Path | str, reason: Any) -> Optional[Path]:
    """Preserve an unreadable persisted file as <name>.corrupt-<epoch>, log, and return the new path."""
    import time
    source = Path(path)
    backup = source.with_name(f"{source.name}.corrupt-{int(time.time())}")
    try:
        source.replace(backup)
        _LOGGER.warning("%s unreadable (%s); preserved as %s", source, reason, backup)
        return backup
    except OSError as exc:
        _LOGGER.warning("%s unreadable (%s) and backup failed (%s)", source, reason, exc)
        return None


def core_chunk_create(
    target_dir: Path | str,
    version: str = "latest",
    extensions: Optional[List[str]] = None,
    exclude_dirs: Optional[List[str]] = None,
    package_version: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a Chunked-104a container document from a directory via Core's chunking engine."""
    return _chunking.bejson_core_chunking_create_chunked_104(
        str(target_dir),
        version=version,
        extensions=extensions,
        exclude_dirs=exclude_dirs,
        package_version=package_version,
    )


def core_chunk_hash_bytes(raw_bytes: bytes) -> str:
    """Compute SHA-256 hex digest of raw bytes via Core's chunking engine."""
    return _chunking.bejson_core_chunking_hash_file_bytes(raw_bytes)


def core_chunk_bump_package_version(prior_doc: Optional[Dict[str, Any]]) -> str:
    """Increment package version string via Core's chunking engine."""
    return _chunking.bejson_core_chunking_bump_package_version(prior_doc)


def core_atomic_write_json(path: Path | str, payload: Dict[str, Any]) -> bool:
    """Write a JSON/BEJSON dictionary atomically via Core without schema validation."""
    return bool(_core.bejson_core_atomic_write(str(path), payload))


def core_load_json(path: Path | str) -> Optional[Dict[str, Any]]:
    """Read a JSON/BEJSON dictionary via Core without schema validation."""
    doc = _core.bejson_core_load_file(str(path))
    return doc if isinstance(doc, dict) else None


def core_write_text_file(path: Path | str, text: str) -> None:
    """Atomically write a UTF-8 plain-text file via temporary sibling replacement."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp_target = target.with_suffix(target.suffix + ".tmp")
    tmp_target.write_text(text, encoding="utf-8")
    tmp_target.replace(target)


def core_write_bytes_file(path: Path | str, raw_bytes: bytes) -> None:
    """Write raw bytes to a file path."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw_bytes)

