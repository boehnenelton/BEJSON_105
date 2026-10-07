"""
Library:        lib_bejson_Core_bejson_core.py
Family:         Core
Description:    Low-level atomic operations and data structure management.
BEJSON:         BEJSON stands for BOEHNEN ELTON JSON. Authoritative definition;
                do not restate or reinterpret this acronym elsewhere.
MFDB:           MFDB stands for Multi File Database. Authoritative definition;
                do not restate or reinterpret this acronym elsewhere.
Version:        3.5.1
Date:           2026-10-06
Author:         Elton Boehnen
Contact:        eltonboehnen@gmail.com | boehnenelton2024.pages.dev | github.com/boehnenelton
Format_Creator: Elton Boehnen
RELATIONAL_ID:  b530a553-d89f-453a-a2c0-7c0fb9172d14
Release_Version: 300

Changelog:
  3.5.1 - Consolidation re-merge: the V6-PKG101 silent-exception logging fix
          (lock-owner liveness retry, field-map cache attach) had been
          reverted/lost on the forward V10-PKG102 branch; re-applied on top
          of the current 3.5.0 content, no behavior change.
  3.5.0 - SELF-VALIDATING 104 FIELD MAP. The 104/104a/104db map is now
          self-validating like 105: checked against the live field-layout
          fingerprint on every read, so a map can no longer go stale after
          add_field / out-of-band Fields edits (it used to return the old map
          forever). Built lazily on first lookup -- 104 load stays untouched
          per the standing contract. Runtime keys _bejson_field_map/_bejson_field_map_fp are stripped
          on serialize/atomic_write like every other '_' key.
  3.4.0 - SELF-MAINTAINING FIELD MAP for 105-series. No caller ever builds or
          refreshes it: every lookup/read/mutation checks the cache against
          the document's live field layout (cheap name+uuid fingerprint) and
          rebuilds if missing, wrong-shaped or stale; 105 documents are warmed
          the moment they are loaded (load_file/load_string) or upgraded.
          FIXED two real bugs from the old two-caches-one-slot design:
          (a) after any 105 operation, bejson_core_get_field_index() returned
          -1 (row[-1] = silently the LAST column); (b) a plain lookup followed
          by a 105 call crashed with KeyError 'content_hash'.
          bejson_core_get_field_map()/get_field_index() on a 105 doc now
          return name -> ROW position (record_uuid/discriminator offset
          applied), so row[idx] is right on every Format_Version. Cache gains
          'by_name_row' + 'fingerprint'; old by_name/by_uuid/content_hash
          unchanged. 104-series behavior untouched.
  3.3.0 - REMOVED bejson_core_upsert_105, bejson_core_row_checksum,
          bejson_core_verify_row_checksums, bejson_core_paginate_105 per
          Be25 -- only UUID features, FK referential integrity and the
          UUID-aware field map cache are kept in 105. The field map
          (_bejson_core_build_field_map: by_name + by_uuid + content_hash)
          is unchanged and still drives resolve_field_index/write_cell.
  3.2.0 - bejson_core_define_field(): removed required/unique/enum/min/max/
          minLength/maxLength keyword params and their option-shape checks,
          per Be25. field_type validation, name-uniqueness check, and the
          fk_target_entity/fk_on_delete params + their validation are
          unchanged -- FK/cascade is explicitly kept. row_checksum,
          verify_row_checksums, upsert_105, and paginate_105 are untouched;
          none of them ever enforced schema constraints (that lived solely
          in the validator, see lib_bejson_Core_bejson_validator.py 3.3.0).
  3.1.0 - Phase 8: 4 functions selected as highest-impact/lowest-effort from
          the Core Library Function Enhancements proposal --
          bejson_core_define_field() (the one sanctioned, eagerly-validated
          way to add a field to a 105-series doc under construction),
          bejson_core_upsert_105(), bejson_core_row_checksum()/
          verify_row_checksums() (104+105, tamper detection), and
          bejson_core_paginate_105() (cursor-based, stable under
          concurrent inserts/deletes -- the reason it's 105-only).
  3.0.0 - Format_Version 105 / 105a / 105db ("Integrity Era") support
          landed per Format105_Master_Plan_Rev2 Phase 2 (\u00a72.1-\u00a72.6):
          hybrid field-index resolver, dual-key write_cell with coordinate
          healing, UUID-addressed add_field/remove_field/delete_record,
          content-hash field-map cache + bejson_core_transaction() batching,
          bejson_core_serialize() strip-on-serialize, and a zero-write
          bejson_core_verify_105_integrity() health check. Strictly additive:
          every 104/104a/104db code path is untouched byte-for-byte.
          Deviation from plan naming (flagged for Elton): bejson_core_add_record
          already exists (live callers: mfdb_core.py, cms_config.py, MD family)
          with an incompatible bool-return/fixed-length signature, so the new
          105-series record adder ships as bejson_core_add_record_105 instead
          of overloading that name. remove_field/delete_record also gained the
          bejson_core_ family prefix (bejson_core_remove_field /
          bejson_core_delete_record) for consistency with every other public
          function in this file.
  3.0.1 - Audit fix (2026-08-16): removed two dead imports introduced in
          3.0.0 (E_UPGRADE_VALIDATION_FAILED belongs only to bejson_upgrade.py;
          E_DUPLICATE_FIELD_UUID was reserved but never actually raised --
          add_field's collision loop regenerates silently instead of raising).
"""

import json
import os
import sys
import time
import shutil
import tempfile
import hashlib
import uuid as _uuid
import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from lib_bejson_Core_bejson_errors import (
    E_FIELD_INTEGRITY_MISMATCH,
    E_FORMAT_UNSUPPORTED,
    E_RECORD_NOT_FOUND,
    E_DUPLICATE_FIELD_NAME,
)

_105_SERIES = ("105", "105a", "105db")

# Universal library release line (Policy 2026-08-14). Only this file --
# the Core BEJSON file -- defines Release_Version as a real code variable;
# all other library files declare it in the header comment only.
RELEASE_VERSION: int = 300

class BEJSONCoreError(Exception):
    """Raised when a BEJSON core operation fails."""
    def __init__(self, message: str, code: int = None):
        super().__init__(message)
        self.code = code

class ResilientPIDLock:
    def __init__(self, target_path: Union[str, Path], timeout_seconds: int = 10):
        self.target    = Path(target_path)
        self.lock_dir  = Path(f"{target_path}.lockdir")
        self.meta_file = self.lock_dir / "lock_meta.json"
        self.timeout   = timeout_seconds

    def acquire(self) -> bool:
        start_time = time.time()
        while time.time() - start_time < self.timeout:
            try:
                self.lock_dir.mkdir(exist_ok=False)
                self.meta_file.write_text(json.dumps({
                    "pid":       os.getpid(),
                    "timestamp": int(time.time())
                }))
                return True
            except FileExistsError:
                if self.meta_file.exists():
                    try:
                        meta      = json.loads(self.meta_file.read_text())
                        owner_pid = meta.get("pid")
                        if owner_pid:
                            os.kill(owner_pid, 0)  # Signal 0: check if alive
                    except (ProcessLookupError, OSError):
                        # Owner is dead — safely reclaim
                        self.release()
                        continue
                    except Exception as e:
                        logging.debug(f"[Core] Could not verify lock-owner liveness, will retry: {e}")
                time.sleep(0.1)
        return False

    def release(self):
        if self.meta_file.exists():
            try:
                self.meta_file.unlink()
            except OSError:
                pass
        try:
            self.lock_dir.rmdir()
        except OSError:
            pass

    def __enter__(self):
        if not self.acquire():
            raise OSError(53, "Mutex lock timeout expired (E_MFDB_CORE_LOCK_FAILED)")
        return self

    def __exit__(self, *_):
        self.release()

from lib_bejson_Core_bejson_env import resolve_path

def _bejson_warm_on_load(doc):
    """105-series documents get their field map built the moment they are
    read, so the first lookup is already warm. 104-series documents are left
    untouched on load (standing contract) -- their map is built lazily, and
    self-validated, on the first lookup. Anything else is untouched."""
    if isinstance(doc, dict) and doc.get("Format_Version") in _105_SERIES and isinstance(doc.get("Fields"), list):
        _bejson_get_field_map_cache(doc)
    return doc

def bejson_core_load_file(path: str) -> Optional[dict]:
    """Loads a BEJSON file and returns the dictionary."""
    path = resolve_path(path)
    if not path:
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return _bejson_warm_on_load(json.load(f))
    except Exception as e:
        logging.error(f"[BEJSON_CORE] Failed to load {path}: {e}")
        return None

def bejson_core_atomic_write(path: str, data: dict) -> bool:
    """Writes a BEJSON file atomically using a temp file and sync."""
    target_dir = os.path.dirname(os.path.abspath(path))
    os.makedirs(target_dir, exist_ok=True)

    # Strip internal metadata keys (starting with _) before write
    clean_data = {k: v for k, v in data.items() if not k.startswith("_")}

    fd, tmp_path = tempfile.mkstemp(dir=target_dir, suffix=".tmp")
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(clean_data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
        return True
    except Exception as e:
        logging.error(f"[BEJSON_CORE] Atomic write failed for {path}: {e}")
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        return False

def bejson_core_acquire_lock(file_path: str, timeout: int = 10) -> bool:
    """Acquire a simple directory-based lock."""
    lock_path = file_path + ".lock"
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            os.mkdir(lock_path)
            return True
        except FileExistsError:
            time.sleep(0.1)
    return False

def bejson_core_release_lock(file_path: str) -> None:
    """Release the simple directory-based lock."""
    lock_path = file_path + ".lock"
    try:
        os.rmdir(lock_path)
    except OSError:
        pass

# Global Field Map Cache
# Key: tuple of field names (sorted or as-is)
# Value: dict of {name: index}
_FIELD_MAP_CACHE: Dict[tuple, Dict[str, int]] = {}

def bejson_core_get_field_map(doc: dict) -> Dict[str, int]:
    """
    Returns a mapping of field name to index.
    Utilizes both in-document caching and a global cache for performance.
    """
    # 105-series: same call, self-maintaining cache. Returns name -> ROW
    # position (record_uuid / discriminator offset already applied), so
    # row[get_field_map(doc)[name]] is correct on every Format_Version.
    if doc.get("Format_Version") in _105_SERIES:
        return _bejson_get_field_map_cache(doc)["by_name_row"]

    # 104-series: SELF-VALIDATING in-document cache. The cached map is only
    # trusted while the doc's live field layout still matches the fingerprint
    # it was built from, so add_field / an out-of-band Fields edit can never
    # leave a stale map behind (3.5.0 -- this was the 104-series half of the
    # self-maintaining design; 105 got it in 3.4.0).
    fields = doc.get("Fields", [])
    if not fields:
        return {}
    fp = _bejson_fields_fingerprint(doc)
    cached = doc.get("_bejson_field_map")
    if (isinstance(cached, dict) and not _bejson_is_105_cache(cached)
            and doc.get("_bejson_field_map_fp") == fp):
        return cached

    # Create a unique key for this field structure for the global cache
    field_names = tuple(f["name"] for f in fields)
    cache_key = (doc.get("Format_Version"), field_names)

    if cache_key in _FIELD_MAP_CACHE:
        field_map = _FIELD_MAP_CACHE[cache_key]
    else:
        # Build and update global cache
        field_map = {f["name"]: i for i, f in enumerate(fields)}
        _FIELD_MAP_CACHE[cache_key] = field_map

    # Inject into document for subsequent O(1) lookups
    try:
        doc["_bejson_field_map"] = field_map
        doc["_bejson_field_map_fp"] = fp
    except Exception as e:
        logging.debug(f"[Core] Could not attach field-map cache to document (immutable or not a dict): {e}")

    return field_map

def bejson_core_get_field_index(doc: dict, field_name: str) -> int:
    """Returns the positional index of a field name using the cache."""
    field_map = bejson_core_get_field_map(doc)
    return field_map.get(field_name, -1)

def bejson_core_create_104(record_type: str, fields: list, values: list) -> dict:
    return {
        "Format": "BEJSON",
        "Format_Version": "104",
        "Format_Creator": "Elton Boehnen",
        "Records_Type": [record_type],
        "Fields": fields,
        "Values": values
    }

def bejson_core_create_104a(record_type: str, fields: list, values: list, **custom) -> dict:
    doc = {
        "Format": "BEJSON",
        "Format_Version": "104a",
        "Format_Creator": "Elton Boehnen",
        "Records_Type": [record_type],
        "Fields": fields,
        "Values": values
    }
    doc.update(custom)
    return doc

def bejson_core_create_104db(record_types: list, fields: list, values: list) -> dict:
    return {
        "Format": "BEJSON",
        "Format_Version": "104db",
        "Format_Creator": "Elton Boehnen",
        "Records_Type": record_types,
        "Fields": fields,
        "Values": values
    }

# --- Missing Functions for MFDB and Parser Compatibility ---

def bejson_core_load_string(content: str) -> Optional[dict]:
    try:
        return _bejson_warm_on_load(json.loads(content))
    except Exception as e:
        logging.error(f"[BEJSON_CORE] Failed to load JSON string: {e}")
        return None

def bejson_core_get_record_count(doc: dict) -> int:
    return len(doc.get("Values", []))

def bejson_core_add_record(doc: dict, record: list) -> bool:
    if len(record) != len(doc.get("Fields", [])):
        return False
    doc.setdefault("Values", []).append(record)
    return True

def bejson_core_remove_record(doc: dict, index: int) -> bool:
    values = doc.get("Values", [])
    if 0 <= index < len(values):
        values.pop(index)
        return True
    return False

def bejson_core_update_field(doc: dict, row_index: int, field_name: str, value: Any) -> bool:
    idx = bejson_core_get_field_index(doc, field_name)
    if idx == -1: return False
    values = doc.get("Values", [])
    if 0 <= row_index < len(values):
        values[row_index][idx] = value
        return True
    return False

def bejson_core_filter_rows(doc: dict, field_name: str, value: Any) -> list:
    idx = bejson_core_get_field_index(doc, field_name)
    if idx == -1: return []
    return [row for row in doc.get("Values", []) if row[idx] == value]

def bejson_core_sort_by_field(doc: dict, field_name: str, reverse: bool = False) -> None:
    idx = bejson_core_get_field_index(doc, field_name)
    if idx == -1: return
    doc["Values"].sort(key=lambda x: x[idx] if x[idx] is not None else "", reverse=reverse)

def bejson_core_is_valid(doc: dict) -> bool:
    # Simplified validity check
    required = ["Format", "Format_Version", "Format_Creator", "Records_Type", "Fields", "Values"]
    return all(k in doc for k in required)

def bejson_core_get_version(doc: dict) -> str:
    return doc.get("Format_Version", "unknown")

def bejson_core_get_stats(doc: dict) -> dict:
    return {
        "record_count": bejson_core_get_record_count(doc),
        "field_count": len(doc.get("Fields", [])),
        "version": bejson_core_get_version(doc)
    }

# ---------------------------------------------------------------------------
# Format_Version 105 / 105a / 105db ("Integrity Era")
# Master Plan: Format105_Master_Plan_Rev2, Phase 2 (\u00a72.1-\u00a72.6)
# Strictly opt-in. Every function below either version-dispatches with the
# 104-series path fully unchanged, or is 105-series-only and raises
# E_FORMAT_UNSUPPORTED otherwise. No 104/104a/104db caller is affected.
# ---------------------------------------------------------------------------

# --- \u00a72.4 Write-through caching & transactional batching -----------------

def _bejson_content_hash(doc: dict) -> str:
    raw = json.dumps(doc.get("Fields", []), sort_keys=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]

def _bejson_row_offset(doc: dict) -> int:
    """Reserved leading columns in a row that Fields does not describe:
    0 for 104-series, 1 for 105/105a (record_uuid), 2 for 105db
    (discriminator + record_uuid)."""
    fmt = doc.get("Format_Version")
    return 2 if fmt == "105db" else (1 if fmt in ("105", "105a") else 0)

def _bejson_fields_fingerprint(doc: dict) -> tuple:
    """Cheap identity of the field layout (version + name/uuid per field).
    Compared on every cache read, so an out-of-band edit to Fields is
    always noticed -- no json dump / hash on the hot path."""
    return (doc.get("Format_Version"),
            tuple((f.get("name"), f.get("field_uuid")) for f in doc.get("Fields", [])))

def _bejson_core_build_field_map(doc: dict) -> dict:
    by_name, by_uuid = {}, {}
    for idx, field in enumerate(doc.get("Fields", [])):
        by_name[field["name"]] = idx
        by_uuid[field.get("field_uuid")] = idx
    offset = _bejson_row_offset(doc)
    return {
        "by_name": by_name,                                     # name -> Fields index
        "by_uuid": by_uuid,                                     # field_uuid -> Fields index
        "by_name_row": {n: i + offset for n, i in by_name.items()},  # name -> row position
        "content_hash": _bejson_content_hash(doc),
        "fingerprint": _bejson_fields_fingerprint(doc),
    }

def _bejson_is_105_cache(cached) -> bool:
    """True only for a 105-shaped cache. A 104-style name->index dict can sit
    in the same slot (e.g. after a plain lookup on a doc that was then
    upgraded in place); it must be rebuilt, never read as a 105 cache."""
    return isinstance(cached, dict) and isinstance(cached.get("by_name"), dict) and "fingerprint" in cached

def _bejson_core_invalidate_cache(doc: dict) -> None:
    """Rebuilds the 105-series field map cache, unless inside an open
    bejson_core_transaction() block -- then it just flags dirty and defers."""
    if doc.get("_bejson_txn_active"):
        doc["_bejson_txn_dirty"] = True
        return
    doc["_bejson_field_map"] = _bejson_core_build_field_map(doc)

def _bejson_get_field_map_cache(doc: dict) -> dict:
    """105-series field map cache. SELF-MAINTAINING: every read checks the
    cache against the document's current field layout and (re)builds it if
    it is missing, the wrong shape, or out of date -- callers never build or
    refresh it. Every 105 lookup, load and mutation goes through here."""
    cached = doc.get("_bejson_field_map")
    if not _bejson_is_105_cache(cached) or cached["fingerprint"] != _bejson_fields_fingerprint(doc):
        cached = doc["_bejson_field_map"] = _bejson_core_build_field_map(doc)
    return cached

@contextmanager
def bejson_core_transaction(doc: dict):
    """
    Batches N mutations into exactly one field-map rebuild, applied at exit.
    Use for bulk pastes / CSV imports against a 105-series doc:

        with bejson_core_transaction(doc):
            for row in csv_rows:
                bejson_core_add_record_105(doc, row)
    """
    doc["_bejson_txn_active"] = True
    doc["_bejson_txn_dirty"] = False
    try:
        yield doc
    finally:
        doc["_bejson_txn_active"] = False
        if doc.get("_bejson_txn_dirty"):
            doc["_bejson_field_map"] = _bejson_core_build_field_map(doc)
        doc.pop("_bejson_txn_dirty", None)

def bejson_core_serialize(doc: dict) -> dict:
    """Strip-on-Serialize: drop every runtime key ('_' / '*' prefix) before
    writing to disk. _bejson_txn_active/_bejson_txn_dirty are runtime keys
    too, so a transaction left open across a crash never reaches disk."""
    return {k: v for k, v in doc.items() if not (k.startswith("_") or k.startswith("*"))}

def _bejson_core_find_row_by_uuid(doc: dict, record_uuid: str) -> Optional[int]:
    uuid_col = 1 if doc.get("Format_Version") == "105db" else 0
    for i, row in enumerate(doc.get("Values", [])):
        if len(row) > uuid_col and row[uuid_col] == record_uuid:
            return i
    return None

# --- \u00a72.1 Hybrid Index Resolver ------------------------------------------

def bejson_core_resolve_field_index(doc: dict, field_target: Union[str, Dict[str, str]]) -> int:
    """
    Resolve a field's positional index using its field_uuid, its name, or
    both (double-verification dict). Never trust a hardcoded position for a
    105-series document -- the field map cache is the only source of truth.

    field_target forms:
      "author_name"                                  -> resolve by name
      "6e1c2b4a-...-uuid"                             -> resolve by field_uuid
      {"name": "author_name", "field_uuid": "6e1..."} -> both must agree
    """
    fmt = doc.get("Format_Version")
    if fmt not in _105_SERIES:
        raise BEJSONCoreError(
            f"E_FORMAT_UNSUPPORTED: resolve_field_index requires a 105-series document, got {fmt!r}",
            code=E_FORMAT_UNSUPPORTED,
        )

    field_map = _bejson_get_field_map_cache(doc)
    offset = 2 if fmt == "105db" else 1  # 105db reserves index 0 (discriminator) + 1 (record_uuid)

    if isinstance(field_target, dict):
        name, fuuid = field_target.get("name"), field_target.get("field_uuid")
        by_name = field_map["by_name"].get(name)
        by_uuid = field_map["by_uuid"].get(fuuid)
        if by_name is None or by_uuid is None or by_name != by_uuid:
            raise BEJSONCoreError(
                f"E_FIELD_INTEGRITY_MISMATCH: name={name!r} resolves to {by_name!r}, "
                f"field_uuid={fuuid!r} resolves to {by_uuid!r}",
                code=E_FIELD_INTEGRITY_MISMATCH,
            )
        return by_name + offset

    if field_target in field_map["by_uuid"]:
        return field_map["by_uuid"][field_target] + offset
    if field_target in field_map["by_name"]:
        return field_map["by_name"][field_target] + offset

    raise BEJSONCoreError(
        f"E_FIELD_INTEGRITY_MISMATCH: unresolvable target {field_target!r}",
        code=E_FIELD_INTEGRITY_MISMATCH,
    )

# --- \u00a72.2 Dual-Key Write Verification ------------------------------------

def bejson_core_write_cell(
    doc: dict,
    record_uuid: str,
    field_uuid: str,
    new_value,
    *,
    expected_row: int = None,
    expected_col: int = None,
) -> dict:
    """
    Write new_value into the cell identified by (record_uuid, field_uuid).
    expected_row/expected_col are the caller's last-known coordinates -- a
    mismatch does not fail the write; it re-locates and heals it, reporting
    healed: true so the caller can refresh its cached coordinates.
    """
    if doc.get("Format_Version") not in _105_SERIES:
        raise BEJSONCoreError(
            f"E_FORMAT_UNSUPPORTED: write_cell requires a 105-series document, "
            f"got {doc.get('Format_Version')!r}. Use bejson_core_update_field() for 104-series.",
            code=E_FORMAT_UNSUPPORTED,
        )

    field_map = _bejson_get_field_map_cache(doc)
    col = field_map["by_uuid"].get(field_uuid)
    if col is None:
        raise BEJSONCoreError(f"E_FIELD_INTEGRITY_MISMATCH: unknown field_uuid {field_uuid!r}",
                               code=E_FIELD_INTEGRITY_MISMATCH)

    row = _bejson_core_find_row_by_uuid(doc, record_uuid)
    if row is None:
        raise BEJSONCoreError(f"E_RECORD_NOT_FOUND: unknown record_uuid {record_uuid!r}",
                               code=E_RECORD_NOT_FOUND)

    offset = 2 if doc["Format_Version"] == "105db" else 1
    abs_col = col + offset

    healed = False
    if expected_row is not None and expected_row != row:
        healed = True
    if expected_col is not None and expected_col != abs_col:
        healed = True

    doc["Values"][row][abs_col] = new_value
    _bejson_core_invalidate_cache(doc)  # deferred instead if inside a transaction -- see \u00a72.4

    return {
        "row": row, "col": abs_col, "healed": healed,
        "field_map_version": doc["_bejson_field_map"]["content_hash"],
    }

# --- \u00a72.3 Automatic UUID Schema Generation -------------------------------

def _bejson_core_add_field_legacy_104(doc: dict, name: str, field_type: str) -> None:
    """No add_field precedent existed for 104-series prior to this plan;
    this is a new, self-contained capability -- append the field and pad
    every existing row with None so structural validity (E_RECORD_LENGTH_MISMATCH)
    is preserved. Does not touch bejson_core_add_record or any other
    existing 104-series function."""
    doc.setdefault("Fields", []).append({"name": name, "type": field_type})
    for row in doc.get("Values", []):
        row.append(None)
    bejson_core_get_field_map(doc)  # self-validating: fingerprint changed -> rebuilt now, not on next lookup

def bejson_core_add_field(doc: dict, name: str, field_type: str) -> Optional[str]:
    """Version-dispatched field adder. 104-series: appends + pads rows,
    returns None (no UUID concept). 105-series: generates a field_uuid."""
    if doc.get("Format_Version") not in _105_SERIES:
        _bejson_core_add_field_legacy_104(doc, name, field_type)
        return None

    existing_names = {f["name"] for f in doc.get("Fields", [])}
    existing_uuids = {f.get("field_uuid") for f in doc.get("Fields", [])}
    if name in existing_names:
        raise BEJSONCoreError(f"E_DUPLICATE_FIELD_NAME: {name!r} already exists",
                               code=E_DUPLICATE_FIELD_NAME)

    new_uuid = str(_uuid.uuid4())
    while new_uuid in existing_uuids:  # collision is ~impossible; regenerate defensively anyway
        new_uuid = str(_uuid.uuid4())

    doc.setdefault("Fields", []).append({"name": name, "type": field_type, "field_uuid": new_uuid})
    # Bugfix vs. Master_Plan_Rev2 \u00a72.3 draft: the plan's add_field never padded
    # existing rows, which desyncs positional integrity the moment an older
    # row is addressed by absolute column (write_cell, remove_field) after a
    # newer row picks up the field. Every row gets None for the new column,
    # matching what the 104-series legacy path already does above.
    for row in doc.get("Values", []):
        row.append(None)
    _bejson_core_invalidate_cache(doc)
    return new_uuid

def bejson_core_add_record_105(doc: dict, values: list) -> str:
    """105-series record adder (UUID-addressed). Named _105 rather than
    overloading bejson_core_add_record -- see file Changelog for why. For
    104-series documents, use the existing bejson_core_add_record()."""
    if doc.get("Format_Version") not in _105_SERIES:
        raise BEJSONCoreError(
            f"E_FORMAT_UNSUPPORTED: add_record_105 requires a 105-series document, "
            f"got {doc.get('Format_Version')!r}. Use bejson_core_add_record() for 104-series.",
            code=E_FORMAT_UNSUPPORTED,
        )

    record_uuid = str(_uuid.uuid4())
    if doc["Format_Version"] == "105db":
        # Index 0 = Record_Type_Parent discriminator (caller-supplied); record_uuid goes at Index 1.
        row = [values[0], record_uuid] + list(values[1:])
    else:
        row = [record_uuid] + list(values)

    doc.setdefault("Values", []).append(row)
    _bejson_core_invalidate_cache(doc)
    return record_uuid

# --- \u00a72.5 Additional Core Mutators (remove_field / delete_record) -------

def bejson_core_remove_field(doc: dict, field_target: str) -> None:
    """Version-dispatched field remover.
    105-series: removed by field_uuid or name (never by index, so a
    concurrent edit can't remove the wrong column); cache evicted immediately.
    104-series: new capability (no prior remove_field existed) -- removed by
    name only, since 104 Fields align 1:1 with Values columns with no offset."""
    if doc.get("Format_Version") not in _105_SERIES:
        fields = doc.get("Fields", [])
        col = next((i for i, f in enumerate(fields) if f.get("name") == field_target), None)
        if col is None:
            raise BEJSONCoreError(f"E_FIELD_INTEGRITY_MISMATCH: unknown field {field_target!r}",
                                   code=E_FIELD_INTEGRITY_MISMATCH)
        del fields[col]
        for row in doc.get("Values", []):
            if len(row) > col:
                del row[col]
        return

    field_map = _bejson_get_field_map_cache(doc)
    col = field_map["by_uuid"].get(field_target)
    if col is None:
        col = field_map["by_name"].get(field_target)
    if col is None:
        raise BEJSONCoreError(f"E_FIELD_INTEGRITY_MISMATCH: unknown field {field_target!r}",
                               code=E_FIELD_INTEGRITY_MISMATCH)

    del doc["Fields"][col]
    offset = 2 if doc["Format_Version"] == "105db" else 1
    for row in doc["Values"]:
        del row[col + offset]

    _bejson_core_invalidate_cache(doc)

def bejson_core_delete_record(doc: dict, record_uuid: str) -> None:
    """105-series only: removed by record_uuid (never by row offset, so
    removal is immune to coordinate drift from other in-flight writes).
    104-series has no record_uuid concept -- use bejson_core_remove_record(doc, index)."""
    if doc.get("Format_Version") not in _105_SERIES:
        raise BEJSONCoreError(
            f"E_FORMAT_UNSUPPORTED: delete_record requires a 105-series document, "
            f"got {doc.get('Format_Version')!r}. Use bejson_core_remove_record() for 104-series.",
            code=E_FORMAT_UNSUPPORTED,
        )

    row = _bejson_core_find_row_by_uuid(doc, record_uuid)
    if row is None:
        raise BEJSONCoreError(f"E_RECORD_NOT_FOUND: unknown record_uuid {record_uuid!r}",
                               code=E_RECORD_NOT_FOUND)

    del doc["Values"][row]
    _bejson_core_invalidate_cache(doc)  # Values change doesn't touch Fields hash,
                                         # but row-lookup caches (if any) must drop too

# --- \u00a72.6 Read-Only Integrity Verification -------------------------------

def bejson_core_verify_105_integrity(doc: dict) -> dict:
    """
    Read-only health check for a 105-series document. Never writes to disk,
    never mutates doc. Safe for cron / background-service use.
    """
    if doc.get("Format_Version") not in _105_SERIES:
        return {"ok": False, "reason": "E_FORMAT_UNSUPPORTED", "errors": []}

    from lib_bejson_Core_bejson_validator import bejson_validator_check_105_strict_integrity
    errors = bejson_validator_check_105_strict_integrity(doc)
    field_map = _bejson_core_build_field_map(doc)  # built fresh, cache untouched

    return {
        "ok": len(errors) == 0,
        "field_count": len(doc.get("Fields", [])),
        "record_count": len(doc.get("Values", [])),
        "field_map_content_hash": field_map["content_hash"],
        "errors": errors,
    }

# ---------------------------------------------------------------------------
# Phase 8 (2026-08-22): Core Library Function Enhancements -- the 4 functions
# selected as highest-impact / lowest-effort from that proposal. Same rule
# as everything above: 105-series only where noted, and every function
# gates on Format_Version up front.
# ---------------------------------------------------------------------------

def bejson_core_define_field(
    doc: dict,
    name: str,
    field_type: str,
    *,
    fk_target_entity: str = None,
    fk_on_delete: str = None,
) -> str:
    """
    The one sanctioned way to add a field to a 105-series document under
    construction. Validates EAGERLY, before the field is ever appended --
    nothing is written to doc["Fields"] on a failed call:
      - field_type must be one of BEJSON's 6 canonical types
      - name must not already exist on this document
      - fk_on_delete, if given, requires fk_target_entity and must be one
        of restrict/cascade/null (Phase 6 convention)
    Returns the generated field_uuid.
    """
    if doc.get("Format_Version") not in _105_SERIES:
        raise BEJSONCoreError(
            f"E_FORMAT_UNSUPPORTED: define_field requires a 105-series document, "
            f"got {doc.get('Format_Version')!r}",
            code=E_FORMAT_UNSUPPORTED,
        )

    from lib_bejson_Core_bejson_validator import VALID_FIELD_TYPES
    if field_type not in VALID_FIELD_TYPES:
        raise BEJSONCoreError(
            f"E_FIELD_INTEGRITY_MISMATCH: field_type must be one of {sorted(VALID_FIELD_TYPES)}, "
            f"got {field_type!r}",
            code=E_FIELD_INTEGRITY_MISMATCH,
        )

    existing_names = {f["name"] for f in doc.get("Fields", [])}
    if name in existing_names:
        raise BEJSONCoreError(f"E_DUPLICATE_FIELD_NAME: {name!r} already exists",
                               code=E_DUPLICATE_FIELD_NAME)

    if fk_on_delete is not None:
        if fk_target_entity is None:
            raise BEJSONCoreError(
                f"E_FIELD_INTEGRITY_MISMATCH: fk_on_delete requires fk_target_entity to also be set",
                code=E_FIELD_INTEGRITY_MISMATCH,
            )
        if fk_on_delete not in ("restrict", "cascade", "null"):
            raise BEJSONCoreError(
                f"E_FIELD_INTEGRITY_MISMATCH: fk_on_delete must be restrict/cascade/null, "
                f"got {fk_on_delete!r}",
                code=E_FIELD_INTEGRITY_MISMATCH,
            )

    new_uuid = str(_uuid.uuid4())
    while new_uuid in {f.get("field_uuid") for f in doc.get("Fields", [])}:
        new_uuid = str(_uuid.uuid4())  # collision is ~impossible; regenerate defensively anyway

    field = {"name": name, "type": field_type, "field_uuid": new_uuid}
    if fk_target_entity is not None: field["fk_target_entity"] = fk_target_entity
    if fk_on_delete is not None:    field["fk_on_delete"] = fk_on_delete

    doc.setdefault("Fields", []).append(field)
    for row in doc.get("Values", []):
        row.append(None)  # positional integrity -- same fix applied to add_field in Phase 2
    _bejson_core_invalidate_cache(doc)
    return new_uuid
