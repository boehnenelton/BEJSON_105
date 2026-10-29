"""
File Name : lib_bejson_Standards_validator.py
Rel. Path : Lib_PY/Standards/lib_bejson_Standards_validator.py
Purpose   : Standards VALIDATOR: pure integrity gates for log entries, rows, config and whole log files (schema v3, 17 columns). Never writes; the audit never raises.
VERSION   : 3.0.0
Author    : Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
RELATIONAL_ID : 7879bfe6-7c9c-40ba-8b73-7cd9322b2e6a

Required tier: timestamp, level, subsystem, event key, message, process id. Every other column is
optional: stored as null when omitted, format-checked when present.
"""
from __future__ import annotations

import json
import logging
import os
import re
import sys
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

# Sibling family directories (Lib_PY/Core, Lib_PY/Standards) resolve relative to this file; nothing is hardcoded.
_HERE = os.path.dirname(os.path.abspath(__file__))
for _fam in ('Core', 'Standards', 'Taxonomies', 'Tax_Scaffolds'):
    _p = os.path.normpath(os.path.join(_HERE, "..", _fam))
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

import lib_bejson_Standards_errors as err  # noqa: E402

logger = logging.getLogger(__name__)
VERSION = "3.0.0"

# ---------------------------------------------------------------------------
# Canonical contract
# ---------------------------------------------------------------------------
FORMAT_VERSION = "104a"
RECORDS_TYPE = "StandardsLogEntry"
SCHEMA_VERSION = "3.0.0"
HDR_ROW_CAP = "Log_Row_Cap"
HDR_MIN_LEVEL = "Log_Min_Level"
HDR_SCHEMA_VERSION = "Log_Schema_Version"
HDR_IS_SECURE = "Log_Is_Secure"
HDR_IS_ARCHIVE = "Log_Is_Archive"
HDR_ARCHIVE_PERIOD_KEY = "Log_Archive_Period_Key"
DEFAULT_ROW_CAP = 10000
DEFAULT_MIN_LEVEL = "INFO"

LEVELS: Tuple[str, ...] = ("DEBUG", "INFO", "WARN", "ERROR", "FATAL")
LEVEL_RANK: Dict[str, int] = {name: i for i, name in enumerate(LEVELS)}
_LEVEL_ALIASES = {"WARNING": "WARN", "CRITICAL": "FATAL"}

# Priority: 1 = look now ... 4 = background. Stored only when the caller supplies it;
# otherwise the effective value is derived from the level at read time.
PRIORITY_MIN, PRIORITY_MAX = 1, 4
LEVEL_DEFAULT_PRIORITY: Dict[str, int] = {"FATAL": 1, "ERROR": 2, "WARN": 3, "INFO": 4, "DEBUG": 4}

PERIODS: Tuple[str, ...] = ("daily", "weekly", "monthly")
EXPORT_FORMATS: Tuple[str, ...] = ("json", "ndjson", "markdown", "html")
EXPORT_SORTS: Tuple[str, ...] = ("time", "priority")
EXPORT_THEMES: Tuple[str, ...] = ("light", "dark")
PERIOD_KEY_RE = {"daily": re.compile(r"^\d{4}-\d{2}-\d{2}$"), "weekly": re.compile(r"^\d{4}-W\d{2}$"),
                 "monthly": re.compile(r"^\d{4}-\d{2}$")}

REDACTED_MESSAGE = "[redacted: secure entry]"
REDACTED_FLAG = "redacted"

# Taxonomy: namespace "log", prefix "log_". _text, _payload and _flag are declared here (not in
# the Taxonomies defaults); the rest are the Taxonomies default suffixes.
TAXONOMY_NAMESPACE = "log"
TAXONOMY_PREFIX = "log_"
SUFFIX_RULES: Dict[str, Tuple[str, str]] = {
    "_timestamp": ("string",  "ISO-8601 UTC timestamp"),
    "_kind":      ("string",  "enumerated value"),
    "_name":      ("string",  "display label"),
    "_key":       ("string",  "natural identifier"),
    "_metric":    ("integer", "count or measure"),
    "_text":      ("string",  "free text"),
    "_payload":   ("string",  "serialized JSON payload"),
    "_flag":      ("boolean", "true/false marker"),
    "_uuid_fk":   ("string",  "foreign key to another row's record_uuid"),
    "_slot":      ("string",  "reserved, unbound Z-space column"),
}

# Domain grammar: log_<role>_<attribute>_<suffix>, role in {event, sender, target, zspace}.
#   event  = what happened     sender = who/what logged it     target = what it affects
F_EVENT_TIMESTAMP = "log_event_timestamp"
F_EVENT_LEVEL = "log_event_level_kind"
F_EVENT_PRIORITY = "log_event_priority_metric"
F_EVENT_KEY = "log_event_key"
F_EVENT_CATEGORY = "log_event_category_key"
F_EVENT_SUBJECT = "log_event_subject_key"
F_EVENT_MESSAGE = "log_event_message_text"
F_EVENT_ERROR_CODE = "log_event_error_code_metric"
F_EVENT_CONTEXT = "log_event_context_payload"
F_EVENT_FLAGS = "log_event_flags_payload"
F_EVENT_SECURE = "log_event_secure_flag"
F_SENDER_SUBSYSTEM = "log_sender_subsystem_name"
F_SENDER_ACTOR = "log_sender_actor_name"
F_SENDER_SESSION = "log_sender_session_key"
F_SENDER_PID = "log_sender_process_id_metric"
F_TARGET = "log_target_uuid_fk"
F_ZSLOT = "log_zspace_01_reserved_slot"   # trailing reserved slot, null in every data row
ROLES = ("event", "sender", "target", "zspace")

LOG_FIELDS: Tuple[Tuple[str, str], ...] = (
    (F_EVENT_TIMESTAMP, "string"), (F_EVENT_LEVEL, "string"), (F_EVENT_PRIORITY, "integer"),
    (F_EVENT_KEY, "string"), (F_EVENT_CATEGORY, "string"), (F_EVENT_SUBJECT, "string"),
    (F_EVENT_MESSAGE, "string"), (F_EVENT_ERROR_CODE, "integer"), (F_EVENT_CONTEXT, "string"),
    (F_EVENT_FLAGS, "string"), (F_EVENT_SECURE, "boolean"),
    (F_SENDER_SUBSYSTEM, "string"), (F_SENDER_ACTOR, "string"), (F_SENDER_SESSION, "string"),
    (F_SENDER_PID, "integer"),
    (F_TARGET, "string"), (F_ZSLOT, "string"),
)
# Legacy schemas, as LITERAL names so a later rename can never rewrite history. v1 = PKG105, v2 = PKG106.
LOG_FIELDS_V1: Tuple[Tuple[str, str], ...] = (
    ("log_event_timestamp", "string"), ("log_level_kind", "string"), ("log_subsystem_name", "string"),
    ("log_event_key", "string"), ("log_error_code_metric", "integer"), ("log_event_message_text", "string"),
    ("log_event_context_payload", "string"), ("log_process_id_metric", "integer"),
    ("log_target_uuid_fk", "string"), ("log_zspace_01_reserved_slot", "string"),
)
LOG_FIELDS_V2: Tuple[Tuple[str, str], ...] = (
    ("log_event_timestamp", "string"), ("log_level_kind", "string"), ("log_event_priority_metric", "integer"),
    ("log_subsystem_name", "string"), ("log_event_category_key", "string"), ("log_event_subject_key", "string"),
    ("log_event_key", "string"), ("log_error_code_metric", "integer"), ("log_event_message_text", "string"),
    ("log_event_context_payload", "string"), ("log_event_flags_payload", "string"),
    ("log_event_secure_flag", "boolean"), ("log_actor_name", "string"), ("log_session_key", "string"),
    ("log_process_id_metric", "integer"), ("log_target_uuid_fk", "string"), ("log_zspace_01_reserved_slot", "string"),
)
# Old name -> current name (v1/v2 -> v3). Names not listed are unchanged.
LEGACY_RENAMES: Dict[str, str] = {
    "log_level_kind": F_EVENT_LEVEL, "log_error_code_metric": F_EVENT_ERROR_CODE,
    "log_subsystem_name": F_SENDER_SUBSYSTEM, "log_actor_name": F_SENDER_ACTOR,
    "log_session_key": F_SENDER_SESSION, "log_process_id_metric": F_SENDER_PID,
}
REQUIRED_FIELDS = {F_EVENT_TIMESTAMP, F_EVENT_LEVEL, F_SENDER_SUBSYSTEM, F_EVENT_KEY, F_EVENT_MESSAGE, F_SENDER_PID}
OPTIONAL_FIELDS = {n for n, _ in LOG_FIELDS} - REQUIRED_FIELDS      # includes the reserved slot (always null)

_TOKEN_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,63}$")              # category and flag tokens
_FLAG_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,31}$")
MAX_FLAGS = 16
MAX_FREE_LEN = 256


def bejson_standards_validator_canonical_fields() -> List[Dict[str, str]]:
    """Fresh Fields list (new dicts every call, so callers cannot mutate the contract)."""
    return [{"name": n, "type": t} for n, t in LOG_FIELDS]


def bejson_standards_validator_normalize_level(level: Any) -> Optional[str]:
    """Canonical level name, or None when unrecognised. Accepts any case plus WARNING/CRITICAL."""
    if not isinstance(level, str):
        return None
    up = level.strip().upper()
    up = _LEVEL_ALIASES.get(up, up)
    return up if up in LEVEL_RANK else None


def bejson_standards_validator_effective_priority(level: Any, stored: Any = None) -> int:
    """Stored priority if present and valid, else the level default (unknown level -> lowest priority)."""
    if isinstance(stored, int) and not isinstance(stored, bool) and PRIORITY_MIN <= stored <= PRIORITY_MAX:
        return stored
    return LEVEL_DEFAULT_PRIORITY.get(level, PRIORITY_MAX)


def bejson_standards_validator_parse_flags(payload: Any) -> List[str]:
    """Flags list from a stored payload ([] when null or unparseable)."""
    if not isinstance(payload, str):
        return []
    try:
        data = json.loads(payload)
    except ValueError:
        return []
    return [f for f in data if isinstance(f, str)] if isinstance(data, list) else []


# ---------------------------------------------------------------------------
# Leaf checks
# ---------------------------------------------------------------------------
def _is_int(v: Any) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _check_timestamp(v: Any) -> bool:
    if not isinstance(v, str) or not v:
        return False
    try:
        datetime.fromisoformat(v.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def _check_uuid4(v: Any) -> bool:
    if not isinstance(v, str):
        return False
    try:
        u = uuid.UUID(v)
    except ValueError:
        return False
    return u.version == 4 and str(u) == v.lower()


def _check_flags_payload(v: str) -> List[str]:
    try:
        data = json.loads(v)
    except ValueError:
        return ["not valid JSON"]
    if not isinstance(data, list) or not data:
        return ["must be a non-empty JSON array (use null for no flags)"]
    if len(data) > MAX_FLAGS:
        return [f"more than {MAX_FLAGS} flags"]
    problems = [f"flag {f!r} must match {_FLAG_RE.pattern}" for f in data
                if not isinstance(f, str) or not _FLAG_RE.match(f)]
    if len(set(map(str, data))) != len(data):
        problems.append("duplicate flags")
    return problems


def bejson_standards_validator_check_value(name: str, value: Any) -> List[str]:
    """Problems (empty = ok) for one value in one named column."""
    types = dict(LOG_FIELDS)
    if name not in types:
        return [f"{name!r}: not a log column"]
    if value is None:
        return [] if name in OPTIONAL_FIELDS else [f"{name}: must not be null"]
    want = types[name]
    if want == "integer" and not _is_int(value):
        return [f"{name}: expected integer, got {type(value).__name__}"]
    if want == "string" and not isinstance(value, str):
        return [f"{name}: expected string, got {type(value).__name__}"]
    if want == "boolean" and not isinstance(value, bool):
        return [f"{name}: expected boolean, got {type(value).__name__}"]
    if name == F_EVENT_TIMESTAMP and not _check_timestamp(value):
        return [f"{name}: {value!r} is not an ISO-8601 timestamp"]
    if name == F_EVENT_LEVEL and value not in LEVEL_RANK:
        return [f"{name}: {value!r} not in {list(LEVELS)}"]
    if name == F_EVENT_PRIORITY and not PRIORITY_MIN <= value <= PRIORITY_MAX:
        return [f"{name}: {value} not in {PRIORITY_MIN}..{PRIORITY_MAX}"]
    if name in (F_SENDER_SUBSYSTEM, F_EVENT_KEY, F_EVENT_SUBJECT, F_SENDER_ACTOR, F_SENDER_SESSION):
        if not value.strip():
            return [f"{name}: must not be blank"]
        if name != F_SENDER_SUBSYSTEM and name != F_EVENT_KEY and len(value) > MAX_FREE_LEN:
            return [f"{name}: longer than {MAX_FREE_LEN} characters"]
    if name == F_EVENT_CATEGORY and not _TOKEN_RE.match(value):
        return [f"{name}: {value!r} must match {_TOKEN_RE.pattern}"]
    if name == F_SENDER_PID and value < 0:
        return [f"{name}: must be >= 0"]
    if name == F_TARGET and not _check_uuid4(value):
        return [f"{name}: {value!r} is not a UUIDv4"]
    if name == F_EVENT_CONTEXT:
        try:
            json.loads(value)
        except ValueError:
            return [f"{name}: not valid JSON"]
    if name == F_EVENT_FLAGS:
        return [f"{name}: {p}" for p in _check_flags_payload(value)]
    if name == F_ZSLOT:
        return [f"{name}: reserved slot must be null in data rows"]
    return []


def bejson_standards_validator_check_entry(entry: Dict[str, Any]) -> List[str]:
    """Problems for an entry dict keyed by column name. Unknown keys are problems (no silent drops)."""
    if not isinstance(entry, dict):
        return ["entry must be a dict"]
    problems: List[str] = []
    known = {n for n, _ in LOG_FIELDS}
    for k in entry:
        if k not in known:
            problems.append(f"{k!r}: not a log column")
    for name, _t in LOG_FIELDS:
        problems += bejson_standards_validator_check_value(name, entry.get(name))
    return problems


def bejson_standards_validator_check_row(row: Any) -> List[str]:
    """Problems for one positional row in canonical column order."""
    if not isinstance(row, list):
        return ["row must be a list"]
    if len(row) != len(LOG_FIELDS):
        return [f"row has {len(row)} values, expected {len(LOG_FIELDS)}"]
    problems: List[str] = []
    for (name, _t), value in zip(LOG_FIELDS, row):
        problems += bejson_standards_validator_check_value(name, value)
    return problems


def bejson_standards_validator_check_config(row_cap: Any = None, min_level: Any = None,
                                            batch_size: Any = None, flush_interval_seconds: Any = None) -> List[str]:
    """Problems for sink configuration values; None means 'not supplied'."""
    problems: List[str] = []
    if row_cap is not None and (not _is_int(row_cap) or row_cap < 1):
        problems.append(f"row_cap must be an integer >= 1, got {row_cap!r}")
    if min_level is not None and bejson_standards_validator_normalize_level(min_level) is None:
        problems.append(f"min_level {min_level!r} not in {list(LEVELS)}")
    if batch_size is not None and (not _is_int(batch_size) or batch_size < 1):
        problems.append(f"batch_size must be an integer >= 1, got {batch_size!r}")
    if flush_interval_seconds is not None and (
            isinstance(flush_interval_seconds, bool) or not isinstance(flush_interval_seconds, (int, float))
            or flush_interval_seconds < 0):
        problems.append(f"flush_interval_seconds must be a number >= 0, got {flush_interval_seconds!r}")
    return problems


def bejson_standards_validator_is_legacy(fields: Any) -> bool:
    """True when Fields is exactly the v1 (10-column) or v2 (17-column, pre-domain-naming) schema."""
    if not isinstance(fields, list):
        return False
    got = [(f.get("name"), f.get("type")) if isinstance(f, dict) else (None, None) for f in fields]
    return got == list(LOG_FIELDS_V1) or got == list(LOG_FIELDS_V2)


def bejson_standards_validator_check_fields(fields: Any) -> List[str]:
    """Problems when a document's Fields differ from the canonical log schema."""
    if not isinstance(fields, list):
        return ["Fields must be a list"]
    got = [(f.get("name"), f.get("type")) if isinstance(f, dict) else (None, None) for f in fields]
    if got == list(LOG_FIELDS):
        return []
    if bejson_standards_validator_is_legacy(fields):
        return ["legacy log schema (v1/v2); the next write migrates it to v3"]
    return [f"Fields do not match the canonical log schema (got {[g[0] for g in got]})"]


def bejson_standards_validator_check_schema_taxonomy() -> List[str]:
    """Every canonical field must satisfy the Taxonomies naming rules for namespace 'log'.
    Imports Taxonomies lazily so the logging hot path never loads it."""
    try:
        import lib_bejson_Taxonomies_core as txc  # noqa: WPS433
    except Exception as exc:  # pragma: no cover - Taxonomies family absent
        return [f"Taxonomies unavailable: {exc}"]
    taxonomy = {
        "namespace_key": TAXONOMY_NAMESPACE,
        "prefix_key": TAXONOMY_PREFIX,
        "suffix_rules": {tok: {"field_type": t, "meaning": m} for tok, (t, m) in SUFFIX_RULES.items()},
    }
    problems: List[str] = []
    for name, ftype in LOG_FIELDS:
        problems += txc.bejson_taxonomies_check_field_name(taxonomy, name, ftype)
    return problems


# ---------------------------------------------------------------------------
# Period math (UTC) and option checks: pure
# ---------------------------------------------------------------------------
def bejson_standards_validator_parse_time(value: Any) -> Optional[datetime]:
    """Aware UTC datetime from a datetime or ISO-8601 string (naive is taken as UTC); None if unparseable."""
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str) and value.strip():
        try:
            dt = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def bejson_standards_validator_period_start(ts: datetime, period: str) -> datetime:
    """UTC start of the period containing ts: daily 00:00, weekly Monday 00:00 (ISO), monthly the 1st."""
    if period not in PERIODS:
        raise ValueError(f"period {period!r} not in {list(PERIODS)}")
    d: date = ts.astimezone(timezone.utc).date()
    if period == "weekly":
        d = d - timedelta(days=d.weekday())
    elif period == "monthly":
        d = d.replace(day=1)
    return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)


def bejson_standards_validator_period_key(ts: datetime, period: str) -> str:
    """Archive key: daily YYYY-MM-DD, weekly ISO YYYY-Www, monthly YYYY-MM. Keys sort chronologically."""
    start = bejson_standards_validator_period_start(ts, period)
    if period == "daily":
        return start.strftime("%Y-%m-%d")
    if period == "monthly":
        return start.strftime("%Y-%m")
    iso = start.isocalendar()
    return f"{iso[0]:04d}-W{iso[1]:02d}"


def bejson_standards_validator_check_archive_config(archive_dir: Any = None, period: Any = None,
                                                    keep_periods: Any = None) -> List[str]:
    problems: List[str] = []
    if period is not None and period not in PERIODS:
        problems.append(f"archive_period {period!r} not in {list(PERIODS)}")
    if (archive_dir is None) != (period is None):
        problems.append("archive_dir and archive_period must be given together")
    if archive_dir is not None and (not isinstance(archive_dir, (str, os.PathLike)) or not str(os.fspath(archive_dir)).strip()):
        problems.append("archive_dir must be a non-blank path")
    if keep_periods is not None:
        if archive_dir is None:
            problems.append("archive_keep_periods requires archive_dir")
        if not _is_int(keep_periods) or keep_periods < 1:
            problems.append(f"archive_keep_periods must be an integer >= 1, got {keep_periods!r}")
    return problems


def bejson_standards_validator_check_export_options(fmt: Any = None, sort: Any = None, theme: Any = None) -> List[str]:
    problems: List[str] = []
    if fmt is not None and fmt not in EXPORT_FORMATS:
        problems.append(f"fmt {fmt!r} not in {list(EXPORT_FORMATS)}")
    if sort is not None and sort not in EXPORT_SORTS:
        problems.append(f"sort {sort!r} not in {list(EXPORT_SORTS)}")
    if theme is not None and theme not in EXPORT_THEMES:
        problems.append(f"theme {theme!r} not in {list(EXPORT_THEMES)}")
    return problems


# ---------------------------------------------------------------------------
# Whole-file audit (read-only, never raises)
# ---------------------------------------------------------------------------
def bejson_standards_validator_audit_log_file(log_path: str) -> Dict[str, Any]:
    """Audit a log file. Returns {"passed": bool, "problems": [str, ...]}. Never writes, never raises.
    A file whose header says Log_Is_Secure=true must hold only secure rows; any other file must hold none.
    Archive files (Log_Is_Archive=true) are not row-capped."""
    problems: List[str] = []
    try:
        if not isinstance(log_path, (str, os.PathLike)) or not os.path.isfile(log_path):
            return {"passed": False, "problems": [f"file not found: {log_path!r}"]}
        try:
            with open(log_path, "r", encoding="utf-8") as fh:
                doc = json.load(fh)
        except (OSError, ValueError) as exc:
            return {"passed": False, "problems": [f"cannot parse JSON ({err.ERROR_NAMES[err.E_STANDARDS_LOG_BUFFER_CORRUPT]}): {exc}"]}
        if not isinstance(doc, dict):
            return {"passed": False, "problems": ["document root must be an object"]}

        for key in doc:
            if isinstance(key, str) and key.startswith("_"):
                problems.append(f"reserved '_' key persisted: {key!r}")
        if doc.get("Format") != "BEJSON" or doc.get("Format_Version") != FORMAT_VERSION:
            problems.append(f"expected BEJSON {FORMAT_VERSION}, got {doc.get('Format')} {doc.get('Format_Version')}")
        if doc.get("Records_Type") != [RECORDS_TYPE]:
            problems.append(f"Records_Type must be [{RECORDS_TYPE!r}], got {doc.get('Records_Type')!r}")
        if doc.get(HDR_SCHEMA_VERSION) != SCHEMA_VERSION:
            problems.append(f"{HDR_SCHEMA_VERSION} must be {SCHEMA_VERSION!r}, got {doc.get(HDR_SCHEMA_VERSION)!r}")
        is_secure = doc.get(HDR_IS_SECURE, False)
        if not isinstance(is_secure, bool):
            problems.append(f"{HDR_IS_SECURE} must be boolean, got {is_secure!r}")
            is_secure = False
        is_archive = doc.get(HDR_IS_ARCHIVE, False)
        if not isinstance(is_archive, bool):
            problems.append(f"{HDR_IS_ARCHIVE} must be boolean, got {is_archive!r}")
            is_archive = False
        if is_archive:
            key = doc.get(HDR_ARCHIVE_PERIOD_KEY)
            if not isinstance(key, str) or not any(rx.match(key) for rx in PERIOD_KEY_RE.values()):
                problems.append(f"{HDR_ARCHIVE_PERIOD_KEY} must be a period key (YYYY-MM-DD / YYYY-Www / YYYY-MM), got {key!r}")
        field_problems = bejson_standards_validator_check_fields(doc.get("Fields"))
        problems += field_problems

        cap = doc.get(HDR_ROW_CAP, DEFAULT_ROW_CAP)
        problems += bejson_standards_validator_check_config(row_cap=cap, min_level=doc.get(HDR_MIN_LEVEL))
        values = doc.get("Values")
        if not isinstance(values, list):
            problems.append("Values must be a list")
        else:
            if not is_archive and _is_int(cap) and cap >= 1 and len(values) > cap:
                problems.append(f"{len(values)} rows exceed {HDR_ROW_CAP}={cap}")
            if not field_problems:
                idx = [n for n, _t in LOG_FIELDS].index(F_EVENT_SECURE)
                for i, row in enumerate(values):
                    row_problems = bejson_standards_validator_check_row(row)
                    if not row_problems:
                        flagged = row[idx] is True
                        if flagged and not is_secure:
                            row_problems.append(f"{err.ERROR_NAMES[err.E_STANDARDS_LOG_SECURE_VIOLATION]}: secure row in a non-secure log")
                        if is_secure and not flagged:
                            row_problems.append(f"{err.ERROR_NAMES[err.E_STANDARDS_LOG_SECURE_VIOLATION]}: non-secure row in a secure log")
                    for p in row_problems:
                        problems.append(f"row {i}: {p}")
                    if len(problems) > 200:
                        problems.append("... more problems truncated")
                        return {"passed": False, "problems": problems}

        try:  # generic BEJSON rules from Core, on top of the log-specific ones
            from lib_bejson_Core_bejson_validator import validate_bejson
            res = validate_bejson(str(log_path), is_file=True)
            if not res.valid:
                problems += [f"core: {e}" for e in res.errors]
        except Exception as exc:  # pragma: no cover - Core validator failure must not escape
            problems.append(f"core validator unavailable: {exc}")
    except Exception as exc:  # the audit contract: never raise
        problems.append(f"audit aborted: {exc}")
    return {"passed": not problems, "problems": problems}
