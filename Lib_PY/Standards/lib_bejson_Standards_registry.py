"""
File Name : lib_bejson_Standards_registry.py
Rel. Path : Lib_PY/Standards/lib_bejson_Standards_registry.py
Purpose   : Standards REGISTRY: public logging API (log / configure_sink / flush / read_logs / export_logs / archive_now / audit) with batched writes, secure-log routing, time-period archiving and a logging.Handler bridge. log() never raises.
VERSION   : 3.1.0
Author    : Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
RELATIONAL_ID : 048bc177-91c3-4e5c-80dd-073fac59552c

Flush triggers (no background thread): buffer >= batch_size, flush_interval_seconds elapsed at the
next log() call, any ERROR/FATAL entry, flush(), read_logs() on that file, and interpreter exit.
Rows still buffered when a process is killed (SIGKILL / power loss) are lost; ERROR+ is written at once.
Last-resort fallback when the file cannot be written is sys.stderr.write, never the print builtin.

Archiving: configure_sink(archive_dir=..., archive_period="daily"|"weekly"|"monthly") moves rows older than the
current UTC period into <stem>-<period key>.bejson files, checked at flush time (no thread) and on archive_now();
rows trimmed past the row cap go to the archive first. A secure log is archived only into its own
secure_archive_dir; without one it stays ring-only. Nothing is ever pruned unless archive_keep_periods is set.

Secure routing: log(..., secure=True) goes ONLY to the sink's secure_path. With no secure_path the entry
is refused (E256); it is never written to the main log. The main log receives a redacted placeholder
row (event timestamp/level/priority/key, sender subsystem, flag "redacted") unless secure_placeholder=False.
"""
from __future__ import annotations

import atexit
import logging
import os
import sys
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

# Sibling family directories (Lib_PY/Core, Lib_PY/Standards) resolve relative to this file; nothing is hardcoded.
_HERE = os.path.dirname(os.path.abspath(__file__))
for _fam in ('Core', 'Standards'):
    _p = os.path.normpath(os.path.join(_HERE, "..", _fam))
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

import lib_bejson_Standards_core as core  # noqa: E402
import lib_bejson_Standards_errors as err  # noqa: E402
import lib_bejson_Standards_export as export  # noqa: E402
import lib_bejson_Standards_validator as val  # noqa: E402

logger = logging.getLogger(__name__)
VERSION = "3.1.0"

DEFAULT_BATCH_SIZE = 25
DEFAULT_FLUSH_INTERVAL_SECONDS = 5.0
DEFAULT_SUBSYSTEM = "app"
_FLUSH_NOW_RANK = val.LEVEL_RANK["ERROR"]


def _stderr(message: str) -> None:
    """Last-resort sink. Must never raise."""
    try:
        sys.stderr.write(f"[BEJSON_STANDARDS] {message}\n")
    except Exception:  # noqa: BLE001
        pass


class _Sink:
    def __init__(self, path: str, secure: bool = False) -> None:
        self.path = path
        self.secure = secure                          # kind of FILE this sink writes; fixed at creation
        self.row_cap: Optional[int] = None            # None = use the file's Log_Row_Cap
        self.min_level = val.DEFAULT_MIN_LEVEL
        self.batch_size = DEFAULT_BATCH_SIZE
        self.flush_interval = DEFAULT_FLUSH_INTERVAL_SECONDS
        self.default_subsystem = DEFAULT_SUBSYSTEM
        self.default_category: Optional[str] = None
        self.default_actor: Optional[str] = None
        self.default_session: Optional[str] = None
        self.secure_path: Optional[str] = None        # main sinks only
        self.secure_placeholder = True
        self.archive_dir: Optional[str] = None        # per sink: a secure sink has its own (secure) archive directory
        self.archive_period: Optional[str] = None
        self.archive_keep: Optional[int] = None
        self.archive_checked_key: Optional[str] = None
        self.buffer: List[List[Any]] = []
        self.last_flush = time.monotonic()
        self.flush_lock = threading.Lock()            # serialises flushes of this sink (keeps row order)


_STATE = threading.RLock()
_SINKS: Dict[str, _Sink] = {}


def _key(log_path: str) -> str:
    return os.path.abspath(os.fspath(log_path))


def _get_sink(log_path: str, secure: bool = False) -> _Sink:
    k = _key(log_path)
    with _STATE:
        sink = _SINKS.get(k)
        if sink is None:
            sink = _SINKS[k] = _Sink(k, secure)
        elif sink.secure != secure:
            raise err.StandardsLogError(
                f"{k} is registered as a {'secure' if sink.secure else 'non-secure'} log",
                err.E_STANDARDS_LOG_SECURE_VIOLATION)
        return sink


def _secure_sink_of(sink: _Sink) -> Optional[_Sink]:
    return _get_sink(sink.secure_path, secure=True) if sink.secure_path else None


def bejson_standards_configure_sink(log_path: str, row_cap: int = val.DEFAULT_ROW_CAP,
                                    min_level: str = val.DEFAULT_MIN_LEVEL,
                                    batch_size: int = DEFAULT_BATCH_SIZE,
                                    flush_interval_seconds: float = DEFAULT_FLUSH_INTERVAL_SECONDS,
                                    default_subsystem: str = DEFAULT_SUBSYSTEM,
                                    persist: bool = True, *,
                                    secure_path: Optional[str] = None,
                                    secure_row_cap: Optional[int] = None,
                                    secure_placeholder: bool = True,
                                    default_category: Optional[str] = None,
                                    default_actor: Optional[str] = None,
                                    default_session: Optional[str] = None,
                                    archive_dir: Optional[str] = None,
                                    archive_period: Optional[str] = None,
                                    archive_keep_periods: Optional[int] = None,
                                    secure_archive_dir: Optional[str] = None) -> bool:
    """Configure a log file. Bad arguments raise StandardsLogError(255/257): a programming error, caught at setup.
    persist=True creates the file(s) and stores Log_Row_Cap / Log_Min_Level in the header(s); a failure to
    persist is reported on stderr and the in-memory configuration still applies (returns False).
    secure_path: where secure=True entries go (own row cap, 0600 file). None disables secure logging.
    archive_dir + archive_period ("daily"/"weekly"/"monthly", UTC): closed periods move to <stem>-<key>.bejson
    files there, and row-cap overflow is archived instead of dropped. secure_archive_dir does the same for the
    secure log (never share a tree with archive_dir). archive_keep_periods=N deletes archives older than the
    newest N (off by default). Archive settings are in-memory, like secure_path."""
    problems = val.bejson_standards_validator_check_config(row_cap, min_level, batch_size, flush_interval_seconds)
    if secure_row_cap is not None:
        problems += [p.replace("row_cap", "secure_row_cap") for p in val.bejson_standards_validator_check_config(row_cap=secure_row_cap)]
    if not isinstance(default_subsystem, str) or not default_subsystem.strip():
        problems.append("default_subsystem must be a non-blank string")
    if default_category is not None:
        problems += val.bejson_standards_validator_check_value(val.F_EVENT_CATEGORY, default_category.strip().lower()
                                                               if isinstance(default_category, str) else default_category)
    for fname, v in ((val.F_SENDER_ACTOR, default_actor), (val.F_SENDER_SESSION, default_session)):
        if v is not None:
            problems += val.bejson_standards_validator_check_value(fname, v)
    if secure_path is not None:
        if not isinstance(secure_path, (str, os.PathLike)) or not str(os.fspath(secure_path)).strip():
            problems.append("secure_path must be a non-blank path")
        elif _key(secure_path) == _key(log_path):
            problems.append("secure_path must differ from log_path")
    problems += val.bejson_standards_validator_check_archive_config(archive_dir, archive_period, archive_keep_periods)
    if secure_archive_dir is not None:
        if secure_path is None:
            problems.append("secure_archive_dir requires secure_path")
        if archive_period is None:
            problems.append("secure_archive_dir requires archive_period")
        if not isinstance(secure_archive_dir, (str, os.PathLike)) or not str(os.fspath(secure_archive_dir)).strip():
            problems.append("secure_archive_dir must be a non-blank path")
        elif archive_dir is not None and isinstance(archive_dir, (str, os.PathLike)):
            a, b = os.path.abspath(os.fspath(archive_dir)), os.path.abspath(os.fspath(secure_archive_dir))
            if a == b or a.startswith(b + os.sep) or b.startswith(a + os.sep):
                problems.append("secure_archive_dir must be a separate tree from archive_dir (not equal, not nested)")
    if problems:
        raise err.StandardsLogError("; ".join(problems), err.E_STANDARDS_LOG_INVALID_CONFIG)
    canon = val.bejson_standards_validator_normalize_level(min_level)
    sink = _get_sink(log_path)
    sec_sink = _get_sink(secure_path, secure=True) if secure_path is not None else None
    with _STATE:
        sink.row_cap, sink.min_level, sink.batch_size = row_cap, canon, batch_size
        sink.flush_interval, sink.default_subsystem = float(flush_interval_seconds), default_subsystem
        sink.default_category = default_category.strip().lower() if isinstance(default_category, str) else None
        sink.default_actor, sink.default_session = default_actor, default_session
        sink.secure_path = sec_sink.path if sec_sink else None
        sink.secure_placeholder = bool(secure_placeholder)
        sink.archive_dir = os.path.abspath(os.fspath(archive_dir)) if archive_dir is not None else None
        sink.archive_period, sink.archive_keep, sink.archive_checked_key = archive_period, archive_keep_periods, None
        if sec_sink:
            sec_sink.row_cap = secure_row_cap if secure_row_cap is not None else row_cap
            sec_sink.min_level, sec_sink.batch_size = canon, batch_size
            sec_sink.flush_interval = float(flush_interval_seconds)
            sec_sink.archive_dir = os.path.abspath(os.fspath(secure_archive_dir)) if secure_archive_dir is not None else None
            sec_sink.archive_period = archive_period if secure_archive_dir is not None else None
            sec_sink.archive_keep = archive_keep_periods if secure_archive_dir is not None else None
            sec_sink.archive_checked_key = None
    if not persist:
        return True
    try:
        with sink.flush_lock:
            core.bejson_standards_core_set_header(sink.path, row_cap=row_cap, min_level=canon)
        if sec_sink:
            with sec_sink.flush_lock:
                core.bejson_standards_core_set_header(sec_sink.path, row_cap=sec_sink.row_cap, min_level=canon, secure=True)
        return True
    except Exception as exc:  # noqa: BLE001
        _stderr(f"configure_sink could not persist header for {sink.path}: {exc}")
        return False


def bejson_standards_log(log_path: str, level: str, event_key: str, message: str,
                         error_code: Optional[int] = None, target_uuid: Optional[str] = None,
                         subsystem: Optional[str] = None, *,
                         priority: Optional[int] = None, category: Optional[str] = None,
                         subject: Optional[str] = None, flags: Optional[Iterable[str]] = None,
                         secure: bool = False, actor: Optional[str] = None, session: Optional[str] = None,
                         **context: Any) -> bool:
    """Record one entry. NEVER raises. Returns True when accepted (buffered or written), False when dropped
    (invalid entry, secure entry with no secure_path, or below min_level - the last is a normal filter).
    Only level, event_key and message are required; every other field is optional and stored as null
    when omitted. Extra keyword arguments become the JSON context payload (never put secrets in it
    unless secure=True)."""
    return _log_impl(log_path, level, event_key, message, error_code, target_uuid, subsystem, context,
                     priority=priority, category=category, subject=subject, flags=flags,
                     secure=secure, actor=actor, session=session)


def _enqueue(sink: _Sink, row: List[Any], rank: int) -> None:
    with _STATE:
        sink.buffer.append(row)
        bound = sink.row_cap or val.DEFAULT_ROW_CAP
        if len(sink.buffer) > 4 * bound:                                   # failure backlog bound
            del sink.buffer[:len(sink.buffer) - bound]
        due = (rank >= _FLUSH_NOW_RANK or len(sink.buffer) >= sink.batch_size
               or time.monotonic() - sink.last_flush >= sink.flush_interval)
    if due:
        _flush_sink(sink)


def _log_impl(log_path: str, level: str, event_key: str, message: str, error_code: Optional[int],
              target_uuid: Optional[str], subsystem: Optional[str], context: Dict[str, Any], *,
              priority: Optional[int] = None, category: Optional[str] = None, subject: Optional[str] = None,
              flags: Any = None, secure: bool = False, actor: Optional[str] = None,
              session: Optional[str] = None) -> bool:
    """Shared body; takes context as a dict so context keys can never collide with parameter names."""
    try:
        canon = val.bejson_standards_validator_normalize_level(level)
        if canon is None:
            _stderr(f"{err.ERROR_NAMES[err.E_STANDARDS_LOG_INVALID_LEVEL]}: {level!r} (event {event_key!r}) dropped")
            return False
        sink = _get_sink(log_path)
        if val.LEVEL_RANK[canon] < val.LEVEL_RANK[sink.min_level]:
            return False
        sec_sink = None
        if secure:
            sec_sink = _secure_sink_of(sink)
            if sec_sink is None:
                _stderr(f"{err.ERROR_NAMES[err.E_STANDARDS_LOG_SECURE_PATH_MISSING]}: secure entry {event_key!r} refused; "
                        f"configure_sink(secure_path=...) first (it is never written to the main log)")
                return False
        sub = subsystem or sink.default_subsystem
        rank = val.LEVEL_RANK[canon]
        row = core.bejson_standards_core_build_row(
            canon, sub, event_key, message, error_code=error_code, target_uuid=target_uuid,
            context=context or None, priority=priority, category=category or sink.default_category,
            subject=subject, flags=flags, secure=secure, actor=actor or sink.default_actor,
            session=session or sink.default_session)
        if sec_sink is not None:
            placeholder = None
            if sink.secure_placeholder:
                placeholder = core.bejson_standards_core_build_row(
                    canon, sub, event_key, val.REDACTED_MESSAGE, priority=priority, flags=[val.REDACTED_FLAG])
            _enqueue(sec_sink, row, rank)
            if placeholder is not None:
                _enqueue(sink, placeholder, rank)
        else:
            _enqueue(sink, row, rank)
        return True
    except err.StandardsLogError as exc:
        _stderr(f"entry dropped: {exc}")
    except Exception as exc:  # noqa: BLE001 - logging must never take down the host workload
        _stderr(f"unexpected logging failure: {exc}")
    return False


def _flush_sink(sink: _Sink) -> bool:
    ok = True
    with sink.flush_lock:
        with _STATE:
            rows, sink.buffer = sink.buffer, []
            sink.last_flush = time.monotonic()
        if rows:
            try:
                core.bejson_standards_core_append_rows(sink.path, rows, row_cap=sink.row_cap, secure=sink.secure,
                                                       archive_dir=sink.archive_dir, archive_period=sink.archive_period)
            except Exception as exc:  # noqa: BLE001
                ok = False
                with _STATE:
                    sink.buffer[:0] = rows                      # keep for the next attempt, oldest first
                _stderr(f"flush to {sink.path} failed, {len(rows)} row(s) kept in memory: {exc}")
        if ok:
            _maybe_archive(sink)
    return ok


def _maybe_archive(sink: _Sink) -> None:
    """Archive closed periods once per period change (cheap key compare otherwise). Never raises."""
    if not (sink.archive_dir and sink.archive_period):
        return
    now = core.bejson_standards_core_now()
    key = val.bejson_standards_validator_period_key(now, sink.archive_period)
    if key == sink.archive_checked_key:
        return
    try:
        core.bejson_standards_core_archive_closed_periods(sink.path, sink.archive_dir, sink.archive_period,
                                                          secure=sink.secure, now=now)
        if sink.archive_keep:
            core.bejson_standards_core_prune_archives(sink.archive_dir, core._stem(sink.path), sink.archive_keep,
                                                      sink.archive_period, secure=sink.secure)
        sink.archive_checked_key = key
    except Exception as exc:  # noqa: BLE001 - retried at the next flush
        _stderr(f"{err.ERROR_NAMES[err.E_STANDARDS_ARCHIVE_FAILED]}: {sink.path}: {exc}")


def bejson_standards_flush(log_path: Optional[str] = None) -> bool:
    """Write buffered rows now (a main log and its secure log together). log_path=None flushes every sink.
    True only if all flushes succeeded."""
    try:
        with _STATE:
            if log_path is None:
                sinks = list(_SINKS.values())
            else:
                main = _get_sink(log_path)
                sinks = [main] + ([_get_sink(main.secure_path, secure=True)] if main.secure_path else [])
        return all([_flush_sink(s) for s in sinks])
    except Exception as exc:  # noqa: BLE001
        _stderr(f"flush failed: {exc}")
        return False


def bejson_standards_read_logs(log_path: str, min_level: Optional[str] = None, subsystem: Optional[str] = None,
                               limit: int = 100, *, category: Optional[str] = None, actor: Optional[str] = None,
                               flag: Optional[str] = None, max_priority: Optional[int] = None,
                               secure: bool = False, session: Optional[str] = None, event_key: Optional[str] = None,
                               process_id: Optional[int] = None, since: Any = None, until: Any = None
                               ) -> List[Dict[str, Any]]:
    """Newest-last list of entry dicts (the last 'limit' matches). Flushes the buffer first.
    Filters (shared with export_logs): min_level, subsystem, category, actor, session, process_id, event_key, flag,
    max_priority (effective priority <= value; null counts as its level default), since (inclusive) and until
    (exclusive) as ISO strings or datetimes. secure=True reads the sink's configured secure log; reading the main
    log never returns secure rows. Live file only (see export_logs(include_archives=True)).
    Returns [] when absent/unreadable/invalid filter; never raises."""
    try:
        main = _get_sink(log_path)
        target = main
        if secure:
            target = _secure_sink_of(main)
            if target is None:
                _stderr(f"{err.ERROR_NAMES[err.E_STANDARDS_LOG_SECURE_PATH_MISSING]}: no secure_path configured for {log_path!r}")
                return []
        rows_iter = export.bejson_standards_export_filter_rows(
            iter(()), min_level=min_level, max_priority=max_priority, since=since, until=until)   # validate arguments first
        _flush_sink(target)
        doc = core.bejson_standards_core_load(target.path)
        if doc is None:
            return []
        out = list(export.bejson_standards_export_filter_rows(
            core.bejson_standards_core_rows_to_dicts(doc), min_level=min_level, max_priority=max_priority,
            subsystem=subsystem, actor=actor, session=session, process_id=process_id, category=category,
            flag=flag, event_key=event_key, since=since, until=until, include_secure_rows=secure))
        return out[-limit:] if limit and limit > 0 else out
    except Exception as exc:  # noqa: BLE001
        _stderr(f"read_logs failed for {log_path!r}: {exc}")
        return []


_FILTER_NAMES = ("min_level", "max_priority", "subsystem", "actor", "session", "process_id", "category", "flag",
                 "event_key", "since", "until")


def bejson_standards_export_logs(log_path: str, fmt: str = "json", dest: Any = None, *, secure: bool = False,
                                 include_archives: bool = False, sort: str = "time",
                                 include_context: Optional[bool] = None, theme: str = "light",
                                 title: Optional[str] = None, overwrite: bool = True, limit: Optional[int] = None,
                                 max_message_chars: int = 2000, **filters: Any) -> Dict[str, Any]:
    """Filter and export a log. fmt: json (default, a streamed JSON array), ndjson, markdown, html.
    dest: None -> text returned in result["text"]; a writable stream; or a file path (atomic, overwrite=True
    replaces). Filters: min_level, max_priority, subsystem, actor, session, process_id, category, flag,
    event_key, since, until (same meaning as read_logs). include_archives=True also reads archive files.
    secure=True exports the secure log: the destination may not be the main log or inside the main archive
    tree (E261), files are created 0600, and markdown/html omit context unless include_context=True.
    sort: time (log order) or priority (effective priority 1 first, newest first within a priority).
    Never raises: returns {"ok": True, "rows", "dest", "text"} or {"ok": False, "error", "code"}."""
    try:
        unknown = set(filters) - set(_FILTER_NAMES)
        if unknown:
            raise err.StandardsLogError(f"unknown filter(s): {sorted(unknown)}", err.E_STANDARDS_EXPORT_FORMAT_INVALID)
        main = _get_sink(log_path)
        target = main
        if secure:
            target = _secure_sink_of(main)
            if target is None:
                raise err.StandardsLogError("no secure_path configured", err.E_STANDARDS_LOG_SECURE_PATH_MISSING)
            export.bejson_standards_export_check_secure_destination(dest, main.path, [main.archive_dir])
        _flush_sink(target)
        rows = export.bejson_standards_export_iter_rows(
            target.path, target.archive_dir if include_archives else None, target.archive_period, secure=target.secure)
        rows = export.bejson_standards_export_filter_rows(rows, include_secure_rows=secure, **filters)
        forbidden = [s.path for s in list(_SINKS.values())]
        for s in list(_SINKS.values()):
            if s.archive_dir:
                forbidden += [p for _k, p in core.bejson_standards_core_list_archives(s.archive_dir, core._stem(s.path))]
        summary = ", ".join(f"{k}={v}" for k, v in filters.items() if v is not None) or "none"
        name = os.path.basename(target.path) + (" (secure)" if secure else "")
        return export.bejson_standards_export_render(
            rows, fmt, dest, include_context=include_context, sort=sort, theme=theme,
            title=title or f"Standards log export: {name}", max_message_chars=max_message_chars, secure=secure,
            overwrite=overwrite, forbidden=forbidden, limit=limit, filters_summary=summary)
    except err.StandardsLogError as exc:
        _stderr(f"export failed: {exc}")
        return {"ok": False, "error": str(exc), "code": exc.code}
    except Exception as exc:  # noqa: BLE001
        _stderr(f"export failed unexpectedly: {exc}")
        return {"ok": False, "error": str(exc), "code": err.E_STANDARDS_EXPORT_FAILED}


def bejson_standards_archive_now(log_path: str, include_current: bool = False) -> Dict[str, Any]:
    """Archive the main log (and the secure log, when it has a secure_archive_dir) right now. Default moves
    closed periods only; include_current=True also empties the current period. Never raises.
    Returns {"ok", "moved", "files", "errors"}."""
    result: Dict[str, Any] = {"ok": True, "moved": 0, "files": [], "errors": []}
    try:
        main = _get_sink(log_path)
        targets = [main] + ([_get_sink(main.secure_path, secure=True)] if main.secure_path else [])
        before = datetime.max.replace(tzinfo=timezone.utc) if include_current else None
        for sink in targets:
            if not (sink.archive_dir and sink.archive_period):
                continue
            _flush_sink(sink)
            try:
                r = core.bejson_standards_core_archive_closed_periods(
                    sink.path, sink.archive_dir, sink.archive_period, secure=sink.secure,
                    now=core.bejson_standards_core_now(), before=before)
                result["moved"] += r["moved"]
                result["files"] += r["files"]
                if sink.archive_keep:
                    core.bejson_standards_core_prune_archives(sink.archive_dir, core._stem(sink.path),
                                                              sink.archive_keep, sink.archive_period, secure=sink.secure)
            except Exception as exc:  # noqa: BLE001
                result["ok"] = False
                result["errors"].append(f"{sink.path}: {exc}")
                _stderr(f"archive_now failed for {sink.path}: {exc}")
    except Exception as exc:  # noqa: BLE001
        result["ok"] = False
        result["errors"].append(str(exc))
    return result


def bejson_standards_list_archives(log_path: str, secure: bool = False) -> List[Tuple[str, str]]:
    """[(period key, path)] oldest first for the main (or secure) log's archive directory; [] if none."""
    try:
        main = _get_sink(log_path)
        target = _secure_sink_of(main) if secure else main
        if target is None or not target.archive_dir:
            return []
        return [(k, p) for k, p in core.bejson_standards_core_list_archives(target.archive_dir, core._stem(target.path),
                                                                          target.archive_period)
                if core.bejson_standards_core_is_verified_archive(p, k, target.secure)]
    except Exception as exc:  # noqa: BLE001
        _stderr(f"list_archives failed: {exc}")
        return []


def bejson_standards_audit_log_file(log_path: str, secure: bool = False) -> Dict[str, Any]:
    """Flush, then audit the log (secure=True: the sink's configured secure log). {"passed", "problems"};
    never raises. The audit enforces the file kind from its own header (see the validator)."""
    try:
        main = _get_sink(log_path)
        target = _secure_sink_of(main) if secure else main
        if target is None:
            return {"passed": False, "problems": [f"{err.ERROR_NAMES[err.E_STANDARDS_LOG_SECURE_PATH_MISSING]}: no secure_path configured"]}
        _flush_sink(target)
        return val.bejson_standards_validator_audit_log_file(target.path)
    except Exception:  # noqa: BLE001
        return val.bejson_standards_validator_audit_log_file(log_path)


# ---------------------------------------------------------------------------
# logging.Handler bridge: existing code that uses logging.getLogger() feeds the sink unchanged
# ---------------------------------------------------------------------------
_LEVEL_MAP = {"DEBUG": "DEBUG", "INFO": "INFO", "WARNING": "WARN", "ERROR": "ERROR", "CRITICAL": "FATAL"}
_REENTRY = threading.local()
_OWN_PREFIX = "lib_bejson_Standards"


class BEJSONLogHandler(logging.Handler):
    """Routes stdlib LogRecords into a Standards log file.
    Per-record overrides via extra=: event_key, error_code, target_uuid, context (dict), priority, category,
    subject, flags, secure, actor, session. A plain logger.info("x") needs none of them."""

    def __init__(self, log_path: str, subsystem: Optional[str] = None, level: int = logging.NOTSET) -> None:
        super().__init__(level)
        self.log_path = log_path
        self.subsystem = subsystem
        _get_sink(log_path)

    def emit(self, record: logging.LogRecord) -> None:
        if record.name.startswith(_OWN_PREFIX) or getattr(_REENTRY, "active", False):
            return                                             # never log our own diagnostics into ourselves
        _REENTRY.active = True
        try:
            context: Dict[str, Any] = {"logger": record.name, "func": record.funcName, "line": record.lineno}
            extra_ctx = getattr(record, "context", None)
            if isinstance(extra_ctx, dict):
                context.update(extra_ctx)
            if record.exc_info and record.exc_info[0] is not None:
                context["exc_type"] = record.exc_info[0].__name__
            code = getattr(record, "error_code", None)
            _log_impl(
                self.log_path, _LEVEL_MAP.get(record.levelname, "INFO"),
                str(getattr(record, "event_key", None) or record.funcName or record.name),
                record.getMessage(),
                code if isinstance(code, int) and not isinstance(code, bool) else None,
                getattr(record, "target_uuid", None),
                self.subsystem or record.name.split(".")[0] or None, context,
                priority=getattr(record, "priority", None), category=getattr(record, "category", None),
                subject=getattr(record, "subject", None), flags=getattr(record, "flags", None),
                secure=bool(getattr(record, "secure", False)), actor=getattr(record, "actor", None),
                session=getattr(record, "session", None))
        except Exception:  # noqa: BLE001
            self.handleError(record)
        finally:
            _REENTRY.active = False

    def flush(self) -> None:
        bejson_standards_flush(self.log_path)

    def close(self) -> None:
        try:
            self.flush()
        finally:
            super().close()


# ---------------------------------------------------------------------------
# Process lifecycle
# ---------------------------------------------------------------------------
def _reset_after_fork() -> None:
    """A forked child must not re-write rows its parent already buffered."""
    for sink in _SINKS.values():
        sink.buffer = []
        sink.flush_lock = threading.Lock()


if hasattr(os, "register_at_fork"):
    os.register_at_fork(after_in_child=_reset_after_fork)
atexit.register(bejson_standards_flush)
