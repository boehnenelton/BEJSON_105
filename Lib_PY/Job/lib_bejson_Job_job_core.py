"""
Library:         lib_bejson_Job_job_core.py
Family:          Job
Module Purpose:  Job CORE: build, load, read, mutate, save, template and normalise BEJSON 104a Job Schema documents (JobMaker JobTask, 11 fields). Checks live in _validator, execution in _runner.
Architecture:    BEJSON 105 library tier wrapping the frozen 105 Core. The job file stays BEJSON 104a (arrays inside task_context / task_reference are the one scoped exception, BKS-1 rule J2), so Core's stage-0 validator is not used on it. All column access goes through the Core field map; reads and writes use Core's lock and atomic writer.
Version:         1.0.0
Release_Version: 301
Date:            2026-11-14
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Format_Creator:  Elton Boehnen
RELATIONAL_ID:   97edf146-0aee-422c-b34c-155fd1ebb115
"""
from __future__ import annotations

import copy
import logging
import os
import re
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Sequence

_HERE = os.path.dirname(os.path.abspath(__file__))

from lib_bejson_Job_bejson_errors import (  # noqa: E402  (sibling module, same folder)
    E_JOB_CORE_NOT_FOUND,
    E_JOB_LOAD_FAILED,
    E_JOB_LOCK_TIMEOUT,
    E_JOB_PATH_ESCAPE,
    E_JOB_ROW_SHAPE,
    E_JOB_SCHEMA_MISMATCH,
    E_JOB_SHELL_FORBIDDEN,
    E_JOB_TASK_NOT_FOUND,
    E_JOB_TEMPLATE_INVALID,
    E_JOB_VALIDATION_FAILED,
    E_JOB_WRITE_FAILED,
    JobError,
)

logger = logging.getLogger("bejson_job")
VERSION = "1.0.0"

# ---------------------------------------------------------------------------
# Core bootstrap: Job is a consumer of Core only (never of another family). Core is located relative to this file
# (Lib_PY/Core beside Lib_PY/Job) or through ADMIN_LIBRARIES_105. Nothing absolute is hardcoded.
# ---------------------------------------------------------------------------
_CORE_IMPORT_ERROR: Optional[str] = None
_core_load_file = _core_atomic_write = _core_field_map = _core_lock_class = _core_safe_join = None


def _locate_core_dir() -> Optional[str]:
    candidates = [os.path.normpath(os.path.join(_HERE, "..", "Core"))]
    root = os.environ.get("ADMIN_LIBRARIES_105")
    if root:
        candidates.append(os.path.join(root, "Lib_PY", "Core"))
    for candidate in candidates:
        if os.path.isfile(os.path.join(candidate, "lib_bejson_Core_bejson_core.py")):
            return candidate
    return None


def _bootstrap_core() -> None:
    global _CORE_IMPORT_ERROR, _core_load_file, _core_atomic_write, _core_field_map, _core_lock_class, _core_safe_join
    core_dir = _locate_core_dir()
    if core_dir is None:
        _CORE_IMPORT_ERROR = "Lib_PY/Core not found beside Lib_PY/Job and ADMIN_LIBRARIES_105 is unset or wrong"
        return
    if core_dir not in sys.path:
        sys.path.insert(0, core_dir)
    try:
        from lib_bejson_Core_bejson_core import (
            ResilientPIDLock,
            bejson_core_atomic_write,
            bejson_core_get_field_map,
            bejson_core_load_file,
        )
        from lib_bejson_Core_bejson_path_guard import bejson_safe_join
    except Exception as exc:  # Core present but unimportable: report it, do not crash at import time
        _CORE_IMPORT_ERROR = f"Core import failed: {exc}"
        return
    _core_load_file, _core_atomic_write = bejson_core_load_file, bejson_core_atomic_write
    _core_field_map, _core_lock_class, _core_safe_join = bejson_core_get_field_map, ResilientPIDLock, bejson_safe_join


_bootstrap_core()


def bejson_job_core_require_core() -> None:
    """Raises JobError(E_JOB_CORE_NOT_FOUND) when Core could not be imported. CLIs call this first (exit 20)."""
    if _CORE_IMPORT_ERROR is not None:
        raise JobError(_CORE_IMPORT_ERROR, E_JOB_CORE_NOT_FOUND)


def bejson_job_core_field_map(doc: dict) -> Dict[str, int]:
    """Core field map (name -> row position). The only way this family locates a column."""
    bejson_job_core_require_core()
    return _core_field_map(doc)


def bejson_job_core_safe_join(base_dir: str, *parts: str) -> str:
    """Core path guard; a path that leaves base_dir becomes JobError(E_JOB_PATH_ESCAPE)."""
    bejson_job_core_require_core()
    try:
        return _core_safe_join(base_dir, *parts)
    except ValueError as exc:
        raise JobError(str(exc), E_JOB_PATH_ESCAPE) from exc


# ---------------------------------------------------------------------------
# Job Schema constants (BKS-1 Part A; JobMaker Job Schema 1.0)
# ---------------------------------------------------------------------------
JOB_FORMAT = "BEJSON"
JOB_FORMAT_VERSION = "104a"
JOB_FORMAT_CREATOR = "Elton Boehnen"
JOB_SCHEMA_NAME = "Job Schema"
JOB_SCHEMA_VERSION = "1.0"
JOB_RECORDS_TYPE = ["JobTask"]
JOB_SCHEMA_DESCRIPTION = (
    "Custom job schema for the NewAgent task creation and tracking system, managing individual task states and "
    "optional auditing. Each task carries its own task_context (embedded, chunked files), task_reference (path-only "
    "refs), and task_mandatory (marks a task as a required, built-in step for the job's Job_Type/Job_Subtype). "
    "Job_Type/Job_Subtype classify the job; Contextualize_Plan/Contextualize_Last control what each task is injected "
    "with at run time. Also reused unmodified as the Template payload shape."
)

TASK_FIELDS = (
    ("task_id", "string"),
    ("task_order", "integer"),
    ("task_name", "string"),
    ("task_description", "string"),
    ("task_completed", "boolean"),
    ("audit_enabled", "boolean"),
    ("audit_passed", "boolean"),
    ("audit_fail_reason", "string"),
    ("task_context", "array"),
    ("task_reference", "array"),
    ("task_mandatory", "boolean"),
)
TASK_FIELD_NAMES = tuple(name for name, _ in TASK_FIELDS)
CHUNK_KEYS = ("chunk_id", "chunk_label", "chunk_content", "chunk_index_pos", "chunk_status")
CONTEXT_ENTRY_KEYS = ("ref", "text_based", "chunks")
CHUNK_STATUS_DEFAULT = "draft"   # Doc_Chunker default; a chunk with status "skip" is not injected
CHUNK_STATUS_SKIP = "skip"

# Header keys other than the six mandatory ones (and Fields/Values), in canonical order.
JOB_HEADER_KEYS = (
    "Schema_Name", "Schema_Version", "Schema_Description", "Job_Goal", "Job_Type", "Job_Subtype",
    "Contextualize_Plan", "Contextualize_Last", "Job_Complete", "Creation_Date", "Completion_Date",
)
MANDATORY_KEYS = ("Format", "Format_Version", "Format_Creator", "Records_Type", "Fields", "Values")
FORBIDDEN_COLUMNS = ("Target_File", "test_cmd")          # legacy plan data (BKS-1 J5)
LEGACY_HEADER_KEYS = ("Target_File", "Execution_Traces")

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}\Z")
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\Z")


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
def bejson_job_core_today() -> str:
    """UTC date, YYYY-MM-DD (the Job Schema stores dates only)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def bejson_job_core_new_uuid() -> str:
    return str(uuid.uuid4())


def bejson_job_core_slug(text: str) -> str:
    """Filesystem-safe snake_case name: lowercase, runs of non-alphanumerics become one underscore, trimmed."""
    slug = re.sub(r"[^a-z0-9]+", "_", str(text).lower()).strip("_")
    return slug or "job"


def bejson_job_core_task_id_slug(task_id: str) -> str:
    """BKS-1 J3: task id lowercased, every non-alphanumeric character to '_'."""
    return re.sub(r"[^a-z0-9]", "_", str(task_id).lower())


def bejson_job_core_is_valid_date(value: Any) -> bool:
    if not isinstance(value, str) or not DATE_RE.match(value):
        return False
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return False
    return True


def bejson_job_core_is_relative_path(value: Any) -> bool:
    """BKS-1 V6: relative, forward slashes, no '..', no drive letter, no leading slash."""
    if not isinstance(value, str) or not value or "\x00" in value or "\\" in value:
        return False
    if value.startswith("/") or re.match(r"^[A-Za-z]:", value):
        return False
    return ".." not in value.split("/")


def bejson_job_core_split_description(description: str) -> tuple:
    """(brief, derived) -- the brief is the first paragraph; derived lines follow a blank line (BKS-1 A.3)."""
    text = str(description or "").replace("\r\n", "\n").replace("\r", "\n")
    brief, _, derived = text.partition("\n\n")
    return brief.strip(), derived.strip()


def bejson_job_core_chunk_text(ref: str, text: str, max_chars: int = 4000) -> dict:
    """Doc_Chunker-style paragraph-split context entry: {"ref", "text_based", "chunks": [...]}. chunk_index_pos is 1-based."""
    paragraphs = [p for p in re.split(r"\n\s*\n", str(text).replace("\r\n", "\n").replace("\r", "\n")) if p.strip()]
    pieces: List[str] = []
    current = ""
    for paragraph in paragraphs:
        candidate = f"{current}\n\n{paragraph}" if current else paragraph
        if current and len(candidate) > max_chars:
            pieces.append(current)
            current = paragraph
        else:
            current = candidate
    if current:
        pieces.append(current)
    chunks = [
        {
            "chunk_id": uuid.uuid4().hex[:8],
            "chunk_label": f"Chunk_{position}",
            "chunk_content": piece,
            "chunk_index_pos": position,
            "chunk_status": CHUNK_STATUS_DEFAULT,
        }
        for position, piece in enumerate(pieces, start=1)
    ]
    return {"ref": ref, "text_based": True, "chunks": chunks}


def bejson_job_core_context_text(task: dict) -> str:
    """Verbatim text of a task's embedded context: entries in order, chunks by chunk_index_pos, 'skip' chunks left out."""
    blocks: List[str] = []
    for entry in task.get("task_context") or []:
        if not isinstance(entry, dict):
            continue
        chunks = [c for c in entry.get("chunks") or [] if isinstance(c, dict) and c.get("chunk_status") != CHUNK_STATUS_SKIP]
        chunks.sort(key=lambda c: c.get("chunk_index_pos") if isinstance(c.get("chunk_index_pos"), int) else 0)
        body = "\n\n".join(str(c.get("chunk_content", "")) for c in chunks)
        blocks.append(f"[{entry.get('ref', '')}]\n{body}")
    return "\n\n".join(blocks)


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
def bejson_job_core_new_job(
    goal: str,
    tasks: Sequence[dict],
    *,
    job_type: str = "general",
    job_subtype: str = "general",
    contextualize_plan: bool = True,
    contextualize_last: bool = True,
    today: Optional[str] = None,
) -> dict:
    """
    Builds a Job Schema document. Each task dict accepts: name, description (both required), task_id, audit_enabled,
    mandatory, context (list of context entries), references (list of relative paths). Order is the list order, 1..N.
    """
    created = today or bejson_job_core_today()
    rows = []
    for order, task in enumerate(tasks, start=1):
        values = {
            "task_id": task.get("task_id") or bejson_job_core_new_uuid(),
            "task_order": order,
            "task_name": task["name"],
            "task_description": task["description"],
            "task_completed": False,
            "audit_enabled": bool(task.get("audit_enabled", False)),
            "audit_passed": False,
            "audit_fail_reason": "",
            "task_context": copy.deepcopy(list(task.get("context") or [])),
            "task_reference": list(task.get("references") or []),
            "task_mandatory": bool(task.get("mandatory", False)),
        }
        rows.append([values[name] for name in TASK_FIELD_NAMES])  # built from the canonical field list, never read back by index
    doc: Dict[str, Any] = {
        "Format": JOB_FORMAT,
        "Format_Version": JOB_FORMAT_VERSION,
        "Format_Creator": JOB_FORMAT_CREATOR,
        "Records_Type": list(JOB_RECORDS_TYPE),
        "Schema_Name": JOB_SCHEMA_NAME,
        "Schema_Version": JOB_SCHEMA_VERSION,
        "Schema_Description": JOB_SCHEMA_DESCRIPTION,
        "Job_Goal": goal,
        "Job_Type": job_type,
        "Job_Subtype": job_subtype,
        "Contextualize_Plan": bool(contextualize_plan),
        "Contextualize_Last": bool(contextualize_last),
        "Job_Complete": False,
        "Creation_Date": created,
        "Completion_Date": "",
        "Fields": [{"name": name, "type": ftype} for name, ftype in TASK_FIELDS],
        "Values": rows,
    }
    return doc


# ---------------------------------------------------------------------------
# Load / sanitise
# ---------------------------------------------------------------------------
def _strip_cell(value: Any) -> Any:
    return value.strip() if isinstance(value, str) else value


def bejson_job_core_sanitize(doc: dict) -> dict:
    """
    Boundary-layer sanitisation (policy 6.2): strips whitespace from header keys, Fields names and top-level string
    cells before any field-map work. Nested arrays (task_context / task_reference) are left byte-for-byte.
    """
    for key in [k for k in doc if isinstance(k, str) and k != k.strip()]:
        clean = key.strip()
        value = doc.pop(key)
        doc.setdefault(clean, value)
    for key, value in list(doc.items()):
        if isinstance(value, str) and key not in ("Schema_Description",):
            doc[key] = value.strip()
    fields = doc.get("Fields")
    if isinstance(fields, list):
        for field in fields:
            if isinstance(field, dict):
                for k in ("name", "type"):
                    if isinstance(field.get(k), str):
                        field[k] = field[k].strip()
    rows = doc.get("Values")
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, list):
                for i, cell in enumerate(row):
                    if isinstance(cell, str):
                        row[i] = cell.strip()
    return doc


def bejson_job_core_load(path: str) -> dict:
    """Loads and sanitises a job file with Core's loader. Does not validate (use the validator); raises on unreadable input."""
    bejson_job_core_require_core()
    if not os.path.isfile(path):
        raise JobError(f"job file not found: {path}", E_JOB_LOAD_FAILED)
    doc = _core_load_file(path)
    if not isinstance(doc, dict):
        raise JobError(f"job file is not a readable JSON object: {path}", E_JOB_LOAD_FAILED)
    return bejson_job_core_sanitize(doc)


# ---------------------------------------------------------------------------
# Read tasks
# ---------------------------------------------------------------------------
def bejson_job_core_tasks(doc: dict) -> List[dict]:
    """Tasks as dicts keyed by field name (via the field map), plus 'row_index', sorted by task_order."""
    field_map = bejson_job_core_field_map(doc)
    missing = [name for name in TASK_FIELD_NAMES if name not in field_map]
    if missing:
        raise JobError(f"Fields is missing task fields: {missing}", E_JOB_SCHEMA_MISMATCH)
    width = max(field_map.values()) + 1
    tasks: List[dict] = []
    for row_index, row in enumerate(doc.get("Values") or []):
        if not isinstance(row, list) or len(row) < width:
            raise JobError(f"Values[{row_index}] is not a full-width row", E_JOB_ROW_SHAPE)
        task = {name: row[field_map[name]] for name in TASK_FIELD_NAMES}
        task["row_index"] = row_index
        tasks.append(task)
    tasks.sort(key=lambda t: t["task_order"] if isinstance(t["task_order"], int) and not isinstance(t["task_order"], bool) else 10 ** 9)
    return tasks


def bejson_job_core_get_task(doc: dict, task_id: str) -> dict:
    for task in bejson_job_core_tasks(doc):
        if task["task_id"] == task_id:
            return task
    raise JobError(f"no task with task_id {task_id}", E_JOB_TASK_NOT_FOUND)


def bejson_job_core_next_task(doc: dict) -> Optional[dict]:
    """First task, in task_order, whose task_completed is not true; None when every task is complete."""
    for task in bejson_job_core_tasks(doc):
        if task["task_completed"] is not True:
            return task
    return None


def bejson_job_core_progress(doc: dict) -> dict:
    tasks = bejson_job_core_tasks(doc)
    done = sum(1 for t in tasks if t["task_completed"] is True)
    return {"total": len(tasks), "completed": done, "remaining": len(tasks) - done, "job_complete": doc.get("Job_Complete") is True}


# ---------------------------------------------------------------------------
# Mutate (in memory)
# ---------------------------------------------------------------------------
def bejson_job_core_set_task_state(
    doc: dict,
    task_id: str,
    *,
    completed: Optional[bool] = None,
    audit_passed: Optional[bool] = None,
    audit_fail_reason: Optional[str] = None,
) -> None:
    """Writes the only per-task fields that change at run time, through the field map."""
    field_map = bejson_job_core_field_map(doc)
    task = bejson_job_core_get_task(doc, task_id)
    row = doc["Values"][task["row_index"]]
    if completed is not None:
        row[field_map["task_completed"]] = bool(completed)
    if audit_passed is not None:
        row[field_map["audit_passed"]] = bool(audit_passed)
    if audit_fail_reason is not None:
        row[field_map["audit_fail_reason"]] = str(audit_fail_reason)


def bejson_job_core_recompute_completion(doc: dict, today: Optional[str] = None) -> None:
    """Job_Complete is true only when there is at least one task and every task is complete; Completion_Date follows it."""
    tasks = bejson_job_core_tasks(doc)
    complete = bool(tasks) and all(t["task_completed"] is True for t in tasks)
    doc["Job_Complete"] = complete
    if complete:
        existing = doc.get("Completion_Date")
        doc["Completion_Date"] = existing if bejson_job_core_is_valid_date(existing) else (today or bejson_job_core_today())
    else:
        doc["Completion_Date"] = ""


# ---------------------------------------------------------------------------
# Save (validate -> lock -> atomic write)
# ---------------------------------------------------------------------------
def _validate_or_raise(doc: dict, **validator_kwargs: Any) -> None:
    from lib_bejson_Job_job_validator import bejson_job_validator_validate_document  # lazy: validator imports this module

    result = bejson_job_validator_validate_document(doc, **validator_kwargs)
    if not result.valid:
        raise JobError(f"document failed validation ({len(result.errors)} error(s)); not written. First: {result.errors[0].message}",
                       E_JOB_VALIDATION_FAILED, issues=result.errors)


def _write_unlocked(path: str, doc: dict, validate: bool) -> None:
    if validate:
        _validate_or_raise(doc)
    if not _core_atomic_write(path, doc):
        raise JobError(f"atomic write failed for {path}", E_JOB_WRITE_FAILED)


def bejson_job_core_save(path: str, doc: dict, *, validate: bool = True, lock_timeout: int = 10) -> None:
    """Validates (an invalid document is never written), takes the file's PID lock, then writes atomically."""
    bejson_job_core_require_core()
    if validate:
        _validate_or_raise(doc)   # refuse before any directory or lock is created
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)   # the lock directory lives beside the file
    lock = _core_lock_class(path, timeout_seconds=lock_timeout)
    if not lock.acquire():
        raise JobError(f"could not lock {path} within {lock_timeout}s", E_JOB_LOCK_TIMEOUT)
    try:
        _write_unlocked(path, doc, False)
    finally:
        lock.release()


def bejson_job_core_update(path: str, mutator: Callable[[dict], Any], *, validate: bool = True, lock_timeout: int = 10, today: Optional[str] = None) -> dict:
    """
    Read-modify-write inside one lock: loads the job AFTER the lock is held, runs mutator(doc), recomputes
    Job_Complete / Completion_Date, validates, writes atomically. Returns the written document.
    """
    bejson_job_core_require_core()
    lock = _core_lock_class(path, timeout_seconds=lock_timeout)
    if not lock.acquire():
        raise JobError(f"could not lock {path} within {lock_timeout}s", E_JOB_LOCK_TIMEOUT)
    try:
        doc = bejson_job_core_load(path)
        mutator(doc)
        bejson_job_core_recompute_completion(doc, today)
        _write_unlocked(path, doc, validate)
        return doc
    finally:
        lock.release()


# ---------------------------------------------------------------------------
# Templates and legacy plans
# ---------------------------------------------------------------------------
def bejson_job_core_instantiate_template(template_doc: dict, *, today: Optional[str] = None) -> dict:
    """
    Template -> fresh job ("Save As Job Schema"): new task_id per task, task_completed / audit_passed false, audit_fail_reason "",
    Job_Complete false, Completion_Date "", Creation_Date today. task_context, task_reference and task_mandatory are kept untouched.
    """
    from lib_bejson_Job_job_validator import bejson_job_validator_validate_document

    verdict = bejson_job_validator_validate_document(template_doc)
    if not verdict.valid:
        raise JobError(f"template is not a valid Job Schema: {verdict.errors[0].message}", E_JOB_TEMPLATE_INVALID, issues=verdict.errors)
    doc = copy.deepcopy({k: v for k, v in template_doc.items() if not k.startswith("_")})
    field_map = bejson_job_core_field_map(doc)
    for row in doc["Values"]:
        row[field_map["task_id"]] = bejson_job_core_new_uuid()
        row[field_map["task_completed"]] = False
        row[field_map["audit_passed"]] = False
        row[field_map["audit_fail_reason"]] = ""
    doc["Job_Complete"] = False
    doc["Completion_Date"] = ""
    doc["Creation_Date"] = today or bejson_job_core_today()
    return doc


def bejson_job_core_normalize_legacy(doc: dict) -> dict:
    """
    BKS-1 J5: reads a legacy plan. Drops the Target_File header and column and an EMPTY test_cmd column; a test_cmd with any
    non-empty value is refused (E_JOB_SHELL_FORBIDDEN) -- no shell command is ever carried or run. Returns a new document.
    """
    out = copy.deepcopy({k: v for k, v in doc.items() if not k.startswith("_")})
    out.pop("Target_File", None)
    fields = out.get("Fields")
    if not isinstance(fields, list):
        raise JobError("Fields is not a list", E_JOB_SCHEMA_MISMATCH)
    field_map = bejson_job_core_field_map(out)
    drop: List[int] = []
    for name in FORBIDDEN_COLUMNS:
        if name not in field_map:
            continue
        index = field_map[name]
        if name == "test_cmd" and any(row[index] not in (None, "") for row in out.get("Values", [])):
            raise JobError("a non-empty test_cmd was found; shell commands are never run or carried", E_JOB_SHELL_FORBIDDEN)
        drop.append(index)
    for index in sorted(drop, reverse=True):
        del fields[index]
        for row in out.get("Values", []):
            del row[index]
    out.pop("_bejson_field_map", None)
    out.pop("_bejson_field_map_fp", None)
    return out
