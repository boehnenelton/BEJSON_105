"""
File Name : lib_bejson_Standards_core.py
Rel. Path : Lib_PY/Standards/lib_bejson_Standards_core.py
Purpose   : Standards CORE: storage engine for log files (BEJSON 104a, schema v3): row building, PID-locked read-modify-write, atomic commit, row-cap ring trim, time-period archiving, secure-file hardening, legacy migration, corrupt-file quarantine.
VERSION   : 3.1.0
Author    : Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
RELATIONAL_ID : 0ce5a5e5-a3bb-42f2-afe9-fa1f91abfd3b

One log file = one BEJSON 104a document. A batch of rows costs ONE locked read-modify-write;
callers (the registry) batch so a log call is not a full-file rewrite. Persisted header keys:
Log_Row_Cap, Log_Min_Level, Log_Schema_Version, Log_Is_Secure. Core's atomic_write already strips
'_' runtime keys. A secure file only accepts secure rows and a normal file never does (E257).
"""
from __future__ import annotations

import json
import logging
import os
import re
import stat
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

# Sibling family directories (Lib_PY/Core, Lib_PY/Standards) resolve relative to this file; nothing is hardcoded.
_HERE = os.path.dirname(os.path.abspath(__file__))
for _fam in ('Core', 'Standards'):
    _p = os.path.normpath(os.path.join(_HERE, "..", _fam))
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

from lib_bejson_Core_bejson_core import (  # noqa: E402
    ResilientPIDLock,
    bejson_core_atomic_write,
    bejson_core_create_104a,
    bejson_core_get_field_map,
    bejson_core_load_file,
)
import lib_bejson_Standards_errors as err  # noqa: E402
import lib_bejson_Standards_validator as val  # noqa: E402

logger = logging.getLogger(__name__)
VERSION = "3.1.0"

LOCK_TIMEOUT_SECONDS = 10
_SECURE_IDX = [n for n, _t in val.LOG_FIELDS].index(val.F_EVENT_SECURE)   # derived from the schema, never typed in
_TS_IDX = [n for n, _t in val.LOG_FIELDS].index(val.F_EVENT_TIMESTAMP)
_WARNED_PERMS: set = set()


def bejson_standards_core_now() -> datetime:
    """Aware UTC 'now' (single indirection so period logic is testable)."""
    return datetime.now(timezone.utc)


def bejson_standards_core_utc_now() -> str:
    """ISO-8601 UTC timestamp, millisecond precision, 'Z' suffix."""
    return bejson_standards_core_now().isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _norm_token(value: Any) -> Any:
    return value.strip().lower() if isinstance(value, str) else value


def _norm_flags(flags: Any) -> Optional[str]:
    """Flags (str or iterable of str) -> JSON array payload, lower-cased, de-duplicated; None when empty."""
    if flags is None:
        return None
    if isinstance(flags, str):
        flags = [flags]
    try:
        items = [_norm_token(f) for f in flags]
    except TypeError:
        raise err.StandardsLogError(f"flags must be a string or an iterable of strings, got {type(flags).__name__}",
                                    err.E_STANDARDS_LOG_SCHEMA_MISMATCH)
    seen: List[Any] = []
    for f in items:
        if f not in seen:
            seen.append(f)
    return json.dumps(seen) if seen else None


def bejson_standards_core_build_row(level: str, subsystem: str, event_key: str, message: str,
                                   error_code: Optional[int] = None, target_uuid: Optional[str] = None,
                                   context: Optional[Dict[str, Any]] = None,
                                   timestamp: Optional[str] = None, pid: Optional[int] = None,
                                   priority: Optional[int] = None, category: Optional[str] = None,
                                   subject: Optional[str] = None, flags: Any = None, secure: bool = False,
                                   actor: Optional[str] = None, session: Optional[str] = None) -> List[Any]:
    """Validated positional row in canonical column order. Omitted optional fields are stored as null.
    Raises StandardsLogError (250 / 251)."""
    canon = val.bejson_standards_validator_normalize_level(level)
    if canon is None:
        raise err.StandardsLogError(f"level {level!r} not in {list(val.LEVELS)}", err.E_STANDARDS_LOG_INVALID_LEVEL)
    payload = None
    if context:
        try:
            payload = json.dumps(context, sort_keys=True, default=str)
        except (TypeError, ValueError) as exc:
            raise err.StandardsLogError(f"context not serialisable: {exc}", err.E_STANDARDS_LOG_SCHEMA_MISMATCH)
    entry = {
        val.F_EVENT_TIMESTAMP: timestamp or bejson_standards_core_utc_now(),
        val.F_EVENT_LEVEL: canon,
        val.F_EVENT_PRIORITY: priority,
        val.F_SENDER_SUBSYSTEM: subsystem,
        val.F_EVENT_CATEGORY: _norm_token(category),
        val.F_EVENT_SUBJECT: subject,
        val.F_EVENT_KEY: event_key,
        val.F_EVENT_ERROR_CODE: error_code,
        val.F_EVENT_MESSAGE: "" if message is None else str(message),
        val.F_EVENT_CONTEXT: payload,
        val.F_EVENT_FLAGS: _norm_flags(flags),
        val.F_EVENT_SECURE: True if secure else None,
        val.F_SENDER_ACTOR: actor,
        val.F_SENDER_SESSION: session,
        val.F_SENDER_PID: os.getpid() if pid is None else pid,
        val.F_TARGET: target_uuid,
        val.F_ZSLOT: None,
    }
    problems = val.bejson_standards_validator_check_entry(entry)
    if problems:
        raise err.StandardsLogError("; ".join(problems), err.E_STANDARDS_LOG_SCHEMA_MISMATCH)
    return [entry[name] for name, _t in val.LOG_FIELDS]


def bejson_standards_core_new_doc(row_cap: Optional[int] = val.DEFAULT_ROW_CAP, min_level: str = val.DEFAULT_MIN_LEVEL,
                                  secure: bool = False, archive_key: Optional[str] = None) -> dict:
    """Fresh log doc. archive_key marks an archive file (Log_Is_Archive); archives carry no Log_Row_Cap."""
    headers: Dict[str, Any] = {val.HDR_MIN_LEVEL: min_level, val.HDR_SCHEMA_VERSION: val.SCHEMA_VERSION,
                               val.HDR_IS_SECURE: bool(secure)}
    if archive_key is None:
        headers[val.HDR_ROW_CAP] = row_cap
    else:
        headers[val.HDR_IS_ARCHIVE] = True
        headers[val.HDR_ARCHIVE_PERIOD_KEY] = archive_key
    return bejson_core_create_104a(val.RECORDS_TYPE, val.bejson_standards_validator_canonical_fields(), [], **headers)


def _migrate_legacy(doc: dict) -> dict:
    """v1 (10-column) or v2 (pre-domain-naming) doc -> current schema in place. Values move BY NAME through
    LEGACY_RENAMES, never by position; columns the old schema lacked are null."""
    old_names = [f.get("name") for f in doc.get("Fields", [])]
    new_rows = []
    for row in doc.get("Values", []):
        by_name = ({val.LEGACY_RENAMES.get(n, n): v for n, v in zip(old_names, row)}
                   if isinstance(row, list) and len(row) == len(old_names) else {})
        new_rows.append([by_name.get(n) for n, _t in val.LOG_FIELDS])
    doc["Fields"] = val.bejson_standards_validator_canonical_fields()
    doc["Values"] = new_rows
    doc[val.HDR_SCHEMA_VERSION] = val.SCHEMA_VERSION
    doc.setdefault(val.HDR_IS_SECURE, False)
    doc.pop("_bejson_field_map", None)
    return doc


def _quarantine(path: str) -> str:
    dest = f"{path}.corrupt-{time.strftime('%Y%m%d-%H%M%S', time.gmtime())}-{os.getpid()}"
    os.replace(path, dest)
    return dest


def _load_or_create(path: str, row_cap: int, min_level: str, secure: bool) -> Tuple[dict, Optional[str]]:
    """Existing valid-schema doc (legacy v1/v2 is migrated), or a fresh one. A file that cannot be parsed is moved
    aside (253); a parseable file with a foreign schema is refused, never overwritten (251); a secure/
    non-secure kind mismatch is refused (257)."""
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return bejson_standards_core_new_doc(row_cap, min_level, secure), None
    doc = bejson_core_load_file(path)
    if not isinstance(doc, dict):
        moved = _quarantine(path)
        logger.error("[%s] unparseable log file quarantined to %s", err.ERROR_NAMES[err.E_STANDARDS_LOG_BUFFER_CORRUPT], moved)
        return bejson_standards_core_new_doc(row_cap, min_level, secure), moved
    if doc.get("Format_Version") != val.FORMAT_VERSION or doc.get("Records_Type") != [val.RECORDS_TYPE]:
        raise err.StandardsLogError(f"{path} is not a Standards log file; refusing to modify it",
                                    err.E_STANDARDS_LOG_SCHEMA_MISMATCH)
    if not isinstance(doc.get("Values"), list):
        raise err.StandardsLogError(f"{path}: Values is not a list", err.E_STANDARDS_LOG_SCHEMA_MISMATCH)
    if val.bejson_standards_validator_is_legacy(doc.get("Fields")):
        doc = _migrate_legacy(doc)
        logger.info("migrated %s from a legacy log schema to v3", path)
    elif val.bejson_standards_validator_check_fields(doc.get("Fields")):
        raise err.StandardsLogError(f"{path} is not a Standards log file; refusing to modify it",
                                    err.E_STANDARDS_LOG_SCHEMA_MISMATCH)
    doc[val.HDR_SCHEMA_VERSION] = val.SCHEMA_VERSION
    if bool(doc.get(val.HDR_IS_SECURE, False)) != bool(secure):
        raise err.StandardsLogError(
            f"{path} is a {'secure' if doc.get(val.HDR_IS_SECURE) else 'non-secure'} log but was opened as "
            f"{'secure' if secure else 'non-secure'}", err.E_STANDARDS_LOG_SECURE_VIOLATION)
    doc[val.HDR_IS_SECURE] = bool(secure)
    return doc, None


def _locked(path: str):
    return ResilientPIDLock(path, timeout_seconds=LOCK_TIMEOUT_SECONDS)


def _commit(path: str, doc: dict) -> None:
    try:
        ok = bejson_core_atomic_write(path, doc)
    except OSError as exc:
        raise err.StandardsLogError(f"atomic write raised: {exc}", err.E_STANDARDS_LOG_WRITE_FAILED)
    if not ok:
        raise err.StandardsLogError(f"atomic write failed for {path}", err.E_STANDARDS_LOG_WRITE_FAILED)


def _harden(path: str) -> bool:
    """chmod 0600 on a secure log. Returns True if group/other access is actually off. On filesystems that
    ignore modes (shared Android storage, FAT) it cannot be enforced; warn once per path."""
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
        enforced = (os.stat(path).st_mode & 0o077) == 0
    except OSError:
        enforced = False
    if not enforced and path not in _WARNED_PERMS:
        _WARNED_PERMS.add(path)
        logger.warning("secure log permissions cannot be enforced on this filesystem: %s", path)
    return enforced


def _assert_kind(rows: List[List[Any]], secure: bool) -> None:
    """Engine-level invariant: secure and non-secure rows never mix (E257)."""
    for i, row in enumerate(rows):
        flagged = isinstance(row, list) and len(row) > _SECURE_IDX and row[_SECURE_IDX] is True
        if flagged != bool(secure):
            raise err.StandardsLogError(
                f"row {i} is {'secure' if flagged else 'non-secure'} but the target log is "
                f"{'secure' if secure else 'non-secure'}", err.E_STANDARDS_LOG_SECURE_VIOLATION)


def bejson_standards_core_append_rows(path: str, rows: List[List[Any]], row_cap: Optional[int] = None,
                                      min_level: Optional[str] = None, secure: bool = False,
                                      archive_dir: Optional[str] = None,
                                      archive_period: Optional[str] = None) -> Dict[str, int]:
    """One locked read-modify-write for a whole batch. row_cap=None keeps the file's Log_Row_Cap
    (default 10000 for a new file); a given row_cap is persisted. Oldest rows are dropped past the cap.
    secure=True targets a secure file (0600 file, 0700 directory if newly created) and requires every row
    to carry secure=true; secure=False requires none to. With archive_dir + archive_period, rows trimmed past
    the cap are written to the archive BEFORE the live file is committed; if that fails nothing is written
    (E260), so overflow is never silently lost. Returns {"written", "trimmed", "total"}.
    Raises StandardsLogError (251/252/254/257/260)."""
    path = os.path.abspath(path)
    _assert_kind(rows, secure)                           # engine-level invariant: kinds never mix
    parent = os.path.dirname(path)
    if secure:
        os.makedirs(parent, mode=0o700, exist_ok=True)
    else:
        os.makedirs(parent, exist_ok=True)
    try:
        lock = _locked(path)
        lock.__enter__()
    except OSError as exc:
        raise err.StandardsLogError(f"lock not acquired on {path}: {exc}", err.E_STANDARDS_LOG_LOCK_TIMEOUT)
    try:
        doc, _moved = _load_or_create(path, row_cap or val.DEFAULT_ROW_CAP, min_level or val.DEFAULT_MIN_LEVEL, secure)
        if row_cap is not None:
            doc[val.HDR_ROW_CAP] = row_cap
        if min_level is not None:
            doc[val.HDR_MIN_LEVEL] = min_level
        cap = doc.get(val.HDR_ROW_CAP, val.DEFAULT_ROW_CAP)
        if not isinstance(cap, int) or isinstance(cap, bool) or cap < 1:
            cap = val.DEFAULT_ROW_CAP
            doc[val.HDR_ROW_CAP] = cap
        values = doc["Values"]
        values.extend(rows)
        trimmed = max(0, len(values) - cap)
        if trimmed:
            if archive_dir:
                bejson_standards_core_write_archive_rows(archive_dir, _stem(path), values[:trimmed],
                                                         archive_period or "monthly", secure)
            del values[:trimmed]                       # sliding window: oldest first
        bejson_core_get_field_map(doc)                 # Fields untouched by rotation; keeps the cache provably fresh
        _commit(path, doc)
        if secure:
            _harden(path)
        return {"written": len(rows), "trimmed": trimmed, "total": len(values)}
    finally:
        lock.__exit__(None, None, None)


# ---------------------------------------------------------------------------
# Archiving (time periods, UTC). Archive files are 104a, same schema, Log_Is_Archive=true, no row cap.
# ---------------------------------------------------------------------------
def _stem(path: str) -> str:
    return os.path.splitext(os.path.basename(path))[0]


def bejson_standards_core_write_archive_rows(archive_dir: str, stem: str, rows: List[List[Any]], period: str,
                                             secure: bool = False) -> Dict[str, int]:
    """Append rows to the archive file of each row's own period (<stem>-<period key>.bejson). Idempotent:
    rows already present (exact match) are skipped, so a retry after a crash never duplicates. Secure
    archives are secure files (0600, directory 0700). Returns {archive_path: rows_added}.
    Raises StandardsLogError(260) and writes nothing further after the first failure."""
    if period not in val.PERIODS:
        raise err.StandardsLogError(f"archive period {period!r} not in {list(val.PERIODS)}", err.E_STANDARDS_ARCHIVE_FAILED)
    _assert_kind(rows, secure)
    archive_dir = os.path.abspath(os.fspath(archive_dir))
    groups: Dict[str, List[List[Any]]] = {}
    fallback = val.bejson_standards_validator_period_key(bejson_standards_core_now(), period)
    for row in rows:
        ts = val.bejson_standards_validator_parse_time(row[_TS_IDX] if isinstance(row, list) and len(row) > _TS_IDX else None)
        groups.setdefault(val.bejson_standards_validator_period_key(ts, period) if ts else fallback, []).append(row)
    written: Dict[str, int] = {}
    try:
        if secure:
            os.makedirs(archive_dir, mode=0o700, exist_ok=True)
        else:
            os.makedirs(archive_dir, exist_ok=True)
    except OSError as exc:
        raise err.StandardsLogError(f"cannot create archive directory {archive_dir}: {exc}", err.E_STANDARDS_ARCHIVE_FAILED)
    for key in sorted(groups):
        apath = os.path.join(archive_dir, f"{stem}-{key}.bejson")
        try:
            lock = _locked(apath)
            lock.__enter__()
        except OSError as exc:
            raise err.StandardsLogError(f"lock not acquired on {apath}: {exc}", err.E_STANDARDS_ARCHIVE_FAILED)
        try:
            if os.path.exists(apath) and os.path.getsize(apath) > 0:
                doc = bejson_core_load_file(apath)
                if not isinstance(doc, dict):
                    raise err.StandardsLogError(f"existing archive {apath} is unreadable", err.E_STANDARDS_ARCHIVE_FAILED)
                if val.bejson_standards_validator_is_legacy(doc.get("Fields")):
                    doc = _migrate_legacy(doc)
                if (doc.get("Records_Type") != [val.RECORDS_TYPE] or val.bejson_standards_validator_check_fields(doc.get("Fields"))
                        or doc.get(val.HDR_IS_ARCHIVE) is not True or bool(doc.get(val.HDR_IS_SECURE, False)) != bool(secure)
                        or not isinstance(doc.get("Values"), list)):
                    raise err.StandardsLogError(f"{apath} is not a matching Standards archive; refusing to modify it",
                                                err.E_STANDARDS_ARCHIVE_FAILED)
            else:
                doc = bejson_standards_core_new_doc(None, val.DEFAULT_MIN_LEVEL, secure, archive_key=key)
            have = {json.dumps(r, sort_keys=True) for r in doc["Values"]}
            added = 0
            for row in groups[key]:
                sig = json.dumps(row, sort_keys=True)
                if sig not in have:
                    have.add(sig)
                    doc["Values"].append(row)
                    added += 1
            if added or not os.path.exists(apath):
                try:
                    _commit(apath, doc)
                except err.StandardsLogError as exc:
                    raise err.StandardsLogError(str(exc), err.E_STANDARDS_ARCHIVE_FAILED)
                if secure:
                    _harden(apath)
            written[apath] = added
        finally:
            lock.__exit__(None, None, None)
    return written


def bejson_standards_core_archive_closed_periods(path: str, archive_dir: str, period: str, secure: bool = False,
                                                 now: Optional[datetime] = None,
                                                 before: Optional[datetime] = None) -> Dict[str, Any]:
    """Move rows older than the start of the current period (or older than 'before') from the live log into
    per-period archive files. Archives are written first, then the live file is committed: a crash in between
    leaves duplicates that the next run de-duplicates, never a loss. Returns {"moved","files","remaining"}.
    Raises StandardsLogError (254/260)."""
    path = os.path.abspath(path)
    if not os.path.exists(path):
        return {"moved": 0, "files": [], "remaining": 0}
    try:
        lock = _locked(path)
        lock.__enter__()
    except OSError as exc:
        raise err.StandardsLogError(f"lock not acquired on {path}: {exc}", err.E_STANDARDS_LOG_LOCK_TIMEOUT)
    try:
        doc, _moved = _load_or_create(path, val.DEFAULT_ROW_CAP, val.DEFAULT_MIN_LEVEL, secure)
        boundary = before or val.bejson_standards_validator_period_start(now or bejson_standards_core_now(), period)
        move: List[List[Any]] = []
        keep: List[List[Any]] = []
        for row in doc["Values"]:
            ts = val.bejson_standards_validator_parse_time(row[_TS_IDX] if isinstance(row, list) and len(row) > _TS_IDX else None)
            (move if ts is not None and ts < boundary else keep).append(row)
        if not move:
            return {"moved": 0, "files": [], "remaining": len(keep)}
        files = bejson_standards_core_write_archive_rows(archive_dir, _stem(path), move, period, secure)
        doc["Values"] = keep
        _commit(path, doc)
        if secure:
            _harden(path)
        return {"moved": len(move), "files": sorted(files), "remaining": len(keep)}
    finally:
        lock.__exit__(None, None, None)


def bejson_standards_core_list_archives(archive_dir: str, stem: str, period: Optional[str] = None) -> List[Tuple[str, str]]:
    """[(period key, path)] of files named <stem>-<key>.bejson, oldest first. Names only; see prune for verification."""
    try:
        names = os.listdir(os.fspath(archive_dir))
    except OSError:
        return []
    pats = [val.PERIOD_KEY_RE[period]] if period in val.PERIOD_KEY_RE else list(val.PERIOD_KEY_RE.values())
    out = []
    for fn in names:
        m = re.match(r"^" + re.escape(stem) + r"-(.+)\.bejson$", fn)
        if m and any(rx.match(m.group(1)) for rx in pats):
            out.append((m.group(1), os.path.join(os.path.abspath(os.fspath(archive_dir)), fn)))
    return sorted(out)


def _is_verified_archive(path: str, key: str, secure: bool) -> bool:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            doc = json.load(fh)
    except (OSError, ValueError):
        return False
    return (isinstance(doc, dict) and doc.get(val.HDR_IS_ARCHIVE) is True and doc.get(val.HDR_ARCHIVE_PERIOD_KEY) == key
            and doc.get("Records_Type") == [val.RECORDS_TYPE] and bool(doc.get(val.HDR_IS_SECURE, False)) == bool(secure))


def bejson_standards_core_is_verified_archive(path: str, key: str, secure: bool = False) -> bool:
    """True when the file's header proves it is a Standards archive for this period key and kind."""
    return _is_verified_archive(path, key, secure)


def bejson_standards_core_prune_archives(archive_dir: str, stem: str, keep: int, period: str,
                                         secure: bool = False) -> List[str]:
    """Delete the oldest archive files beyond the newest 'keep'. Only files whose name AND header prove they
    are this log's archives of this period and kind are counted or deleted; anything else is left alone.
    Raises StandardsLogError(260) if a delete fails."""
    verified = [(k, p) for k, p in bejson_standards_core_list_archives(archive_dir, stem, period)
                if _is_verified_archive(p, k, secure)]
    deleted: List[str] = []
    for _k, p in verified[:max(0, len(verified) - keep)]:
        try:
            os.remove(p)
        except OSError as exc:
            raise err.StandardsLogError(f"cannot delete archive {p}: {exc}", err.E_STANDARDS_ARCHIVE_FAILED)
        deleted.append(p)
    return deleted


def bejson_standards_core_set_header(path: str, row_cap: Optional[int] = None, min_level: Optional[str] = None,
                                     secure: bool = False) -> bool:
    """Create the file if needed and persist the sink header values. Trims immediately if the new cap is smaller."""
    bejson_standards_core_append_rows(path, [], row_cap=row_cap, min_level=min_level, secure=secure)
    return True


def bejson_standards_core_load(path: str) -> Optional[dict]:
    """Read-only load of a log doc (None if absent/unparseable). Takes no lock: writers replace atomically.
    A legacy doc is returned migrated in memory only; the file changes on the next write."""
    if not os.path.isfile(path):
        return None
    doc = bejson_core_load_file(path)
    if not isinstance(doc, dict):
        return None
    if val.bejson_standards_validator_is_legacy(doc.get("Fields")):
        doc = _migrate_legacy(doc)
    return doc


def bejson_standards_core_rows_to_dicts(doc: dict) -> List[Dict[str, Any]]:
    """Rows as dicts via the field map (column offsets are never hardcoded)."""
    fmap = bejson_core_get_field_map(doc)
    names = sorted(fmap, key=fmap.get)
    return [{n: row[fmap[n]] for n in names} for row in doc.get("Values", []) if isinstance(row, list)]
