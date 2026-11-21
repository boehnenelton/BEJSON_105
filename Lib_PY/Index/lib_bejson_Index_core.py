"""
Name:          lib_bejson_Index_core.py
Description:   Core BEJSON 104a schema specifications, O(1) field map cache, atomic persistence, and validator bridge for the Index library family.
Version:       1.0.0
Date Created:  2026-11-18
Author Credit: Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
License:       PolyForm-Noncommercial-1.0.0
RELATIONAL_ID: 7e4a9c10-3b2d-4f88-9a11-c502e81b4501
"""

import json
import logging
import os
import sys
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("lib_bejson_Index.core")

SCHEMA_STANDARD_ID = "BEJSON-IMG-INDEX-104A-V1"
FORMAT_CREATOR = "Elton Boehnen"
_PATH_LOCKS: Dict[str, threading.Lock] = {}
_PATH_LOCKS_GUARD = threading.Lock()

# Canonical BEJSON 104a Fields (Primitives only: string, integer, number, boolean)
IMAGE_INDEX_FIELDS: List[Dict[str, str]] = [
    {"name": "image_id", "type": "string"},
    {"name": "filename", "type": "string"},
    {"name": "rel_path", "type": "string"},
    {"name": "ext", "type": "string"},
    {"name": "file_size_bytes", "type": "integer"},
    {"name": "width", "type": "integer"},
    {"name": "height", "type": "integer"},
    {"name": "aspect_ratio", "type": "number"},
    {"name": "group_id", "type": "string"},
    {"name": "group_label", "type": "string"},
    {"name": "group_size", "type": "integer"},
    {"name": "is_primary_in_group", "type": "boolean"},
    {"name": "layer_role", "type": "string"},
    {"name": "dhash_hex", "type": "string"},
    {"name": "phash_hex", "type": "string"},
    {"name": "hamming_to_primary", "type": "integer"},
    {"name": "exif_datetime_original", "type": "string"},
    {"name": "exif_datetime_ifd0", "type": "string"},
    {"name": "filename_date", "type": "string"},
    {"name": "date_anomaly_flag", "type": "boolean"},
    {"name": "exif_software", "type": "string"},
    {"name": "exif_make_model", "type": "string"},
    {"name": "confidence_score", "type": "number"},
    {"name": "match_reason", "type": "string"},
]

GROUP_SUMMARY_FIELDS: List[Dict[str, str]] = [
    {"name": "group_id", "type": "string"},
    {"name": "group_label", "type": "string"},
    {"name": "group_type", "type": "string"},
    {"name": "member_count", "type": "integer"},
    {"name": "primary_filename", "type": "string"},
    {"name": "min_width", "type": "integer"},
    {"name": "max_width", "type": "integer"},
    {"name": "total_bytes", "type": "integer"},
    {"name": "has_date_anomaly", "type": "boolean"},
    {"name": "avg_hamming_dist", "type": "number"},
    {"name": "heuristic_notes", "type": "string"},
]


def _get_path_lock(target_path: Path) -> threading.Lock:
    """Return a per-path in-process threading lock."""
    resolved_key = str(target_path.resolve())
    with _PATH_LOCKS_GUARD:
        if resolved_key not in _PATH_LOCKS:
            _PATH_LOCKS[resolved_key] = threading.Lock()
        return _PATH_LOCKS[resolved_key]


def sanitize_boundary_text(raw_value: Any) -> str:
    """Sanitize strings for BEJSON tabular cells."""
    if raw_value is None:
        return ""
    txt = str(raw_value).strip().replace("\x00", "")
    txt = txt.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
    return txt[:512]


def bejson_index_create_doc(
    records_type: List[str],
    fields: List[Dict[str, str]],
    values: List[List[Any]],
    schema_name: str = SCHEMA_STANDARD_ID,
    schema_version: str = "100",
) -> Dict[str, Any]:
    """Construct a canonical Foundational Era BEJSON 104a envelope with field map cache."""
    doc: Dict[str, Any] = {
        "Format": "BEJSON",
        "Format_Version": "104a",
        "Format_Creator": FORMAT_CREATOR,
        "Records_Type": list(records_type),
        "Schema_Name": schema_name,
        "Schema_Version": schema_version,
        "Timestamp_UTC": datetime.now(timezone.utc).isoformat(),
        "Fields": [dict(f) for f in fields],
        "Values": values,
    }
    bejson_index_get_field_map(doc)
    return doc


def bejson_index_get_field_map(doc: Dict[str, Any]) -> Dict[str, int]:
    """Populate and return the O(1) field map cache."""
    cache = doc.get("_field_map_cache")
    if isinstance(cache, dict) and len(cache) == len(doc.get("Fields", [])):
        return cache
    fmap: Dict[str, int] = {}
    for idx, field_spec in enumerate(doc.get("Fields", [])):
        name = field_spec.get("name")
        if name:
            fmap[name] = idx
    doc["_field_map_cache"] = fmap
    return fmap


def bejson_index_read_col(
    doc: Dict[str, Any],
    field_map: Dict[str, int],
    row: List[Any],
    col_name: str,
    default: Any = None,
) -> Any:
    """Read a column value using the O(1) field map cache."""
    idx = field_map.get(col_name)
    if idx is None or idx >= len(row):
        return default
    return row[idx]


def bejson_index_write_atomic(target_path: Path, doc: Dict[str, Any]) -> None:
    """Atomically persist a BEJSON document using fsync and replace."""
    target_path = target_path.resolve()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    serializable = {k: v for k, v in doc.items() if not k.startswith("_")}
    lock = _get_path_lock(target_path)

    with lock:
        fd, tmp_name = tempfile.mkstemp(
            prefix=f".{target_path.name}.",
            dir=str(target_path.parent),
            text=True,
        )
        try:
            with open(fd, "w", encoding="utf-8") as handle:
                json.dump(serializable, handle, indent=2, ensure_ascii=False)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_name, str(target_path))
        except Exception:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)
            raise


def bejson_index_load(target_path: Path) -> Dict[str, Any]:
    """Load a BEJSON 104a document and populate its O(1) field map cache."""
    with open(target_path, "r", encoding="utf-8") as handle:
        doc = json.load(handle)
    bejson_index_get_field_map(doc)
    return doc


def _resolve_libraries_104_core() -> Optional[Path]:
    """Locate canonical libraries_104/Lib_PY/Core dynamically via environment."""
    env_root = os.environ.get("ADMIN_LIBRARIES_104", "").strip()
    if env_root:
        candidate = Path(env_root) / "Lib_PY" / "Core"
        if candidate.is_dir():
            return candidate
    fallback = Path("/storage/emulated/0/Admin/Libraries/libraries_104/Lib_PY/Core")
    if fallback.is_dir():
        return fallback
    return None


def bejson_index_validate_file(target_path: Path) -> Tuple[bool, List[str], List[str]]:
    """Validate a BEJSON 104a file using the canonical libraries_104 validator."""
    core_dir = _resolve_libraries_104_core()
    if core_dir is None:
        logger.warning("Canonical libraries_104 validator not found; running fallback check.")
        doc = bejson_index_load(target_path)
        has_keys = all(k in doc for k in ("Format", "Format_Version", "Format_Creator", "Records_Type", "Fields", "Values"))
        return has_keys, ([] if has_keys else ["Missing mandatory BEJSON keys"]), []

    core_str = str(core_dir)
    if core_str not in sys.path:
        sys.path.insert(0, core_str)
    from lib_bejson_Core_bejson_validator import validate_bejson  # type: ignore

    result = validate_bejson(str(target_path), is_file=True)
    return result.valid, list(result.errors), list(result.warnings)
