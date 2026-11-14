"""
Library:         lib_bejson_Job_job_validator.py
Family:          Job
Module Purpose:  Job VALIDATOR: collects every problem in a BEJSON 104a Job Schema document (plan check "P", BKS-1 J6) without stopping at the first, optionally against a Book Document. Never mutates, never raises on document content.
Architecture:    Scoped replacement for Core's stage-0 validator on job files only: Core rejects `array` cells inside 104a, and the Job Schema needs them in task_context / task_reference (BKS-1 J2). Everything else Core would check (mandatory keys, Format_Creator, positional integrity) is checked here too. Columns are found through the Core field map.
Version:         1.0.0
Release_Version: 301
Date:            2026-11-14
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Format_Creator:  Elton Boehnen
RELATIONAL_ID:   31266078-09db-4586-9c34-a647d89554d2
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from lib_bejson_Job_bejson_errors import (
    E_JOB_AUDIT_INCONSISTENT,
    E_JOB_BOOK_LINK,
    E_JOB_CELL_SHAPE,
    E_JOB_COMPLETION_MISMATCH,
    E_JOB_FORBIDDEN_COLUMN,
    E_JOB_HEADER_INVALID,
    E_JOB_LOAD_FAILED,
    E_JOB_ORDER_INVALID,
    E_JOB_PATH_INVALID,
    E_JOB_ROW_SHAPE,
    E_JOB_SCHEMA_MISMATCH,
    E_JOB_TASK_ID_DUPLICATE,
    E_JOB_TASK_ID_INVALID,
    E_JOB_TASK_VALUE_TYPE,
    E_JOB_TEXT_EMPTY,
    E_JOB_VALIDATION_FAILED,
    ERROR_NAMES,
    JobError,
)
from lib_bejson_Job_job_core import (
    CHUNK_KEYS,
    CONTEXT_ENTRY_KEYS,
    FORBIDDEN_COLUMNS,
    JOB_FORMAT,
    JOB_FORMAT_CREATOR,
    JOB_FORMAT_VERSION,
    JOB_HEADER_KEYS,
    JOB_RECORDS_TYPE,
    JOB_SCHEMA_DESCRIPTION,
    JOB_SCHEMA_NAME,
    JOB_SCHEMA_VERSION,
    MANDATORY_KEYS,
    TASK_FIELD_NAMES,
    TASK_FIELDS,
    UUID_RE,
    bejson_job_core_field_map,
    bejson_job_core_is_relative_path,
    bejson_job_core_is_valid_date,
    bejson_job_core_load,
    bejson_job_core_split_description,
)

logger = logging.getLogger("bejson_job")
VERSION = "1.0.0"

_ALLOWED_TOP_LEVEL = set(MANDATORY_KEYS) | set(JOB_HEADER_KEYS)
_BOOK_TYPE, _BOOK_SUBTYPE = "writing", "book"
_BOOK_GOAL_PREFIX = 'Write the book "'


@dataclass
class JobIssue:
    code: int
    message: str
    where: str = ""

    @property
    def name(self) -> str:
        return ERROR_NAMES.get(self.code, str(self.code))

    def __str__(self) -> str:
        return f"{self.name} ({self.code}){' @ ' + self.where if self.where else ''}: {self.message}"


@dataclass
class JobValidationResult:
    errors: List[JobIssue] = field(default_factory=list)
    warnings: List[JobIssue] = field(default_factory=list)
    task_count: int = 0

    @property
    def valid(self) -> bool:
        return not self.errors

    @property
    def codes(self) -> Set[int]:
        return {issue.code for issue in self.errors}


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_str(value: Any) -> bool:
    return isinstance(value, str)


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
def _check_header(doc: dict, result: JobValidationResult, expect_book: Optional[bool]) -> None:
    err = result.errors
    if doc.get("Format") != JOB_FORMAT:
        err.append(JobIssue(E_JOB_SCHEMA_MISMATCH, f"Format must be {JOB_FORMAT!r}", "Format"))
    if doc.get("Format_Version") != JOB_FORMAT_VERSION:
        err.append(JobIssue(E_JOB_SCHEMA_MISMATCH, f"Format_Version must be {JOB_FORMAT_VERSION!r}", "Format_Version"))
    if doc.get("Format_Creator") != JOB_FORMAT_CREATOR:
        err.append(JobIssue(E_JOB_SCHEMA_MISMATCH, f"Format_Creator must be {JOB_FORMAT_CREATOR!r}", "Format_Creator"))
    if doc.get("Records_Type") != JOB_RECORDS_TYPE:
        err.append(JobIssue(E_JOB_SCHEMA_MISMATCH, f"Records_Type must be {JOB_RECORDS_TYPE}", "Records_Type"))

    present = {k for k in doc if isinstance(k, str) and not k.startswith("_")}
    for key in sorted(set(JOB_HEADER_KEYS) - present):
        err.append(JobIssue(E_JOB_HEADER_INVALID, "required header is missing", key))
    for key in sorted(present - _ALLOWED_TOP_LEVEL):
        err.append(JobIssue(E_JOB_HEADER_INVALID, "header is not part of the Job Schema (JobMaker erases extras on save)", key))

    if "Schema_Name" in doc and doc["Schema_Name"] != JOB_SCHEMA_NAME:
        err.append(JobIssue(E_JOB_HEADER_INVALID, f"Schema_Name must be {JOB_SCHEMA_NAME!r}", "Schema_Name"))
    if "Schema_Version" in doc and doc["Schema_Version"] != JOB_SCHEMA_VERSION:
        err.append(JobIssue(E_JOB_HEADER_INVALID, f"Schema_Version must be {JOB_SCHEMA_VERSION!r}", "Schema_Version"))
    if "Schema_Description" in doc:
        description = doc["Schema_Description"]
        if not _is_str(description) or not description.strip():
            err.append(JobIssue(E_JOB_HEADER_INVALID, "Schema_Description must be a non-empty string", "Schema_Description"))
        elif description != JOB_SCHEMA_DESCRIPTION:
            result.warnings.append(JobIssue(E_JOB_HEADER_INVALID, "Schema_Description differs from JobMaker's canonical text", "Schema_Description"))
    for key in ("Job_Goal", "Job_Type", "Job_Subtype"):
        if key in doc and (not _is_str(doc[key]) or not doc[key].strip()):
            err.append(JobIssue(E_JOB_HEADER_INVALID, "must be a non-empty string", key))
    for key in ("Contextualize_Plan", "Contextualize_Last", "Job_Complete"):
        if key in doc and not isinstance(doc[key], bool):
            err.append(JobIssue(E_JOB_HEADER_INVALID, "must be a boolean", key))
    if "Creation_Date" in doc and not bejson_job_core_is_valid_date(doc["Creation_Date"]):
        err.append(JobIssue(E_JOB_HEADER_INVALID, "must be a real date, YYYY-MM-DD", "Creation_Date"))
    if "Completion_Date" in doc and doc["Completion_Date"] != "" and not bejson_job_core_is_valid_date(doc["Completion_Date"]):
        err.append(JobIssue(E_JOB_HEADER_INVALID, 'must be "" until complete, then a real date, YYYY-MM-DD', "Completion_Date"))

    is_book = (doc.get("Job_Type") == _BOOK_TYPE and doc.get("Job_Subtype") == _BOOK_SUBTYPE) if expect_book is None else expect_book
    if is_book:
        if doc.get("Job_Type") != _BOOK_TYPE or doc.get("Job_Subtype") != _BOOK_SUBTYPE:
            err.append(JobIssue(E_JOB_HEADER_INVALID, "a book plan must be Job_Type 'writing' / Job_Subtype 'book'", "Job_Type"))
        if doc.get("Contextualize_Plan") is not True or doc.get("Contextualize_Last") is not True:
            err.append(JobIssue(E_JOB_HEADER_INVALID, "a book plan must have Contextualize_Plan and Contextualize_Last true", "Contextualize_Plan"))
        if not (_is_str(doc.get("Job_Goal")) and doc["Job_Goal"].startswith(_BOOK_GOAL_PREFIX)):
            err.append(JobIssue(E_JOB_HEADER_INVALID, f"a book plan Job_Goal must start with {_BOOK_GOAL_PREFIX!r}", "Job_Goal"))


# ---------------------------------------------------------------------------
# Fields / rows
# ---------------------------------------------------------------------------
def _check_fields(doc: dict, result: JobValidationResult) -> bool:
    """Returns True when Fields is usable for row checks."""
    err = result.errors
    fields = doc.get("Fields")
    if not isinstance(fields, list) or not all(isinstance(f, dict) for f in fields):
        err.append(JobIssue(E_JOB_SCHEMA_MISMATCH, "Fields must be a list of {name, type} objects", "Fields"))
        return False
    names = [f.get("name") for f in fields]
    forbidden = [n for n in names if n in FORBIDDEN_COLUMNS]
    for name in forbidden:
        err.append(JobIssue(E_JOB_FORBIDDEN_COLUMN, "plans never carry this column (normalise a legacy plan first)", f"Fields.{name}"))
    expected = [{"name": n, "type": t} for n, t in TASK_FIELDS]
    actual = [{"name": f.get("name"), "type": f.get("type")} for f in fields]
    if actual != expected and not (forbidden and [a for a in actual if a["name"] not in FORBIDDEN_COLUMNS] == expected):
        err.append(JobIssue(E_JOB_SCHEMA_MISMATCH, f"Fields must be exactly the 11 JobTask fields in order: {list(TASK_FIELD_NAMES)}", "Fields"))
    return actual == expected


def _check_context_cell(value: Any, where: str, err: List[JobIssue]) -> None:
    if isinstance(value, str):
        err.append(JobIssue(E_JOB_CELL_SHAPE, "task_context is a JSON string; it must be a real array", where))
        return
    if not isinstance(value, list):
        err.append(JobIssue(E_JOB_CELL_SHAPE, "task_context must be an array", where))
        return
    for i, entry in enumerate(value):
        spot = f"{where}[{i}]"
        if not isinstance(entry, dict) or set(entry) != set(CONTEXT_ENTRY_KEYS):
            err.append(JobIssue(E_JOB_CELL_SHAPE, f"entry must be an object with exactly {list(CONTEXT_ENTRY_KEYS)}", spot))
            continue
        if not bejson_job_core_is_relative_path(entry["ref"]):
            err.append(JobIssue(E_JOB_PATH_INVALID, f"ref {entry['ref']!r} is not a relative forward-slash path", spot + ".ref"))
        if not isinstance(entry["text_based"], bool):
            err.append(JobIssue(E_JOB_CELL_SHAPE, "text_based must be a boolean", spot + ".text_based"))
        chunks = entry["chunks"]
        if not isinstance(chunks, list):
            err.append(JobIssue(E_JOB_CELL_SHAPE, "chunks must be an array", spot + ".chunks"))
            continue
        for j, chunk in enumerate(chunks):
            cspot = f"{spot}.chunks[{j}]"
            if not isinstance(chunk, dict) or set(chunk) != set(CHUNK_KEYS):
                err.append(JobIssue(E_JOB_CELL_SHAPE, f"chunk must be an object with exactly {list(CHUNK_KEYS)}", cspot))
                continue
            for key in ("chunk_id", "chunk_label", "chunk_content", "chunk_status"):
                if not _is_str(chunk[key]):
                    err.append(JobIssue(E_JOB_CELL_SHAPE, f"{key} must be a string", f"{cspot}.{key}"))
            if not _is_int(chunk["chunk_index_pos"]):
                err.append(JobIssue(E_JOB_CELL_SHAPE, "chunk_index_pos must be an integer", f"{cspot}.chunk_index_pos"))


def _check_reference_cell(value: Any, where: str, err: List[JobIssue]) -> None:
    if isinstance(value, str):
        err.append(JobIssue(E_JOB_CELL_SHAPE, "task_reference is a JSON string; it must be a real array", where))
        return
    if not isinstance(value, list):
        err.append(JobIssue(E_JOB_CELL_SHAPE, "task_reference must be an array of path strings", where))
        return
    for i, ref in enumerate(value):
        if not _is_str(ref):
            err.append(JobIssue(E_JOB_CELL_SHAPE, "reference must be a string", f"{where}[{i}]"))
        elif not bejson_job_core_is_relative_path(ref):
            err.append(JobIssue(E_JOB_PATH_INVALID, f"{ref!r} is not a relative forward-slash path", f"{where}[{i}]"))


def _check_rows(doc: dict, result: JobValidationResult) -> None:
    err = result.errors
    rows = doc.get("Values")
    if not isinstance(rows, list):
        err.append(JobIssue(E_JOB_SCHEMA_MISMATCH, "Values must be a list of rows", "Values"))
        return
    field_map = bejson_job_core_field_map(doc)
    width = len(TASK_FIELD_NAMES)
    seen_ids: Dict[str, int] = {}
    orders: List[int] = []
    completed_flags: List[bool] = []
    result.task_count = len(rows)

    for i, row in enumerate(rows):
        base = f"Values[{i}]"
        if not isinstance(row, list) or len(row) != width:
            err.append(JobIssue(E_JOB_ROW_SHAPE, f"row must be a list of exactly {width} values", base))
            continue
        cell = {name: row[field_map[name]] for name in TASK_FIELD_NAMES}

        task_id = cell["task_id"]
        if not _is_str(task_id):
            err.append(JobIssue(E_JOB_TASK_VALUE_TYPE, "task_id must be a string", f"{base}.task_id"))
        elif not UUID_RE.match(task_id):
            err.append(JobIssue(E_JOB_TASK_ID_INVALID, f"{task_id!r} is not a canonical lowercase hyphenated UUID", f"{base}.task_id"))
        elif task_id in seen_ids:
            err.append(JobIssue(E_JOB_TASK_ID_DUPLICATE, f"{task_id} already used by Values[{seen_ids[task_id]}]", f"{base}.task_id"))
        else:
            seen_ids[task_id] = i

        if _is_int(cell["task_order"]):
            orders.append(cell["task_order"])
        else:
            err.append(JobIssue(E_JOB_TASK_VALUE_TYPE, "task_order must be an integer", f"{base}.task_order"))

        if not _is_str(cell["task_name"]):
            err.append(JobIssue(E_JOB_TASK_VALUE_TYPE, "task_name must be a string", f"{base}.task_name"))
        elif not cell["task_name"].strip():
            err.append(JobIssue(E_JOB_TEXT_EMPTY, "task_name is empty", f"{base}.task_name"))

        if not _is_str(cell["task_description"]):
            err.append(JobIssue(E_JOB_TASK_VALUE_TYPE, "task_description must be a string", f"{base}.task_description"))
        elif not bejson_job_core_split_description(cell["task_description"])[0]:
            err.append(JobIssue(E_JOB_TEXT_EMPTY, "the first paragraph of task_description (the brief) is empty", f"{base}.task_description"))

        for key in ("task_completed", "audit_enabled", "audit_passed", "task_mandatory"):
            if not isinstance(cell[key], bool):
                err.append(JobIssue(E_JOB_TASK_VALUE_TYPE, f"{key} must be a boolean", f"{base}.{key}"))
        if not _is_str(cell["audit_fail_reason"]):
            err.append(JobIssue(E_JOB_TASK_VALUE_TYPE, "audit_fail_reason must be a string (use \"\" when none)", f"{base}.audit_fail_reason"))

        _check_context_cell(cell["task_context"], f"{base}.task_context", err)
        _check_reference_cell(cell["task_reference"], f"{base}.task_reference", err)

        if isinstance(cell["audit_passed"], bool) and isinstance(cell["audit_fail_reason"], str):
            if cell["audit_passed"] and cell["audit_fail_reason"]:
                err.append(JobIssue(E_JOB_AUDIT_INCONSISTENT, "audit_passed is true but audit_fail_reason is set", f"{base}.audit_fail_reason"))
        if cell["task_completed"] is True and cell["audit_enabled"] is True and cell["audit_passed"] is not True:
            # Legal pre-ingest state (BKS-1 J4: another runner marked it complete; the gate has not run yet) -> warning, not error.
            result.warnings.append(JobIssue(E_JOB_AUDIT_INCONSISTENT, "completed with audit enabled but not yet audited; ingest will gate it", f"{base}.task_completed"))
        if isinstance(cell["task_completed"], bool):
            completed_flags.append(cell["task_completed"])

    expected_orders = list(range(1, len(rows) + 1))
    if len(orders) == len(rows) and sorted(orders) != expected_orders:
        err.append(JobIssue(E_JOB_ORDER_INVALID, f"task_order must be exactly 1..{len(rows)} with no gaps or repeats; found {sorted(orders)}", "task_order"))

    all_done = bool(rows) and len(completed_flags) == len(rows) and all(completed_flags)
    job_complete, completion_date = doc.get("Job_Complete"), doc.get("Completion_Date")
    if isinstance(job_complete, bool) and job_complete != all_done:
        err.append(JobIssue(E_JOB_COMPLETION_MISMATCH, f"Job_Complete is {job_complete} but the tasks say {all_done}", "Job_Complete"))
    if isinstance(completion_date, str):
        if all_done and not bejson_job_core_is_valid_date(completion_date):
            err.append(JobIssue(E_JOB_COMPLETION_MISMATCH, "every task is complete but Completion_Date is not a date", "Completion_Date"))
        if not all_done and completion_date != "":
            err.append(JobIssue(E_JOB_COMPLETION_MISMATCH, 'Completion_Date must be "" until every task is complete', "Completion_Date"))


# ---------------------------------------------------------------------------
# Book link (BKS-1 J6, last clause)
# ---------------------------------------------------------------------------
def bejson_job_validator_check_book_link(job_doc: dict, book_doc: dict) -> List[JobIssue]:
    """
    Task ids and order must equal the Book Document's writable chapters (every Chapter row whose kind is not 'part',
    in chapter_order_index order). The book is read through its own field map and is never modified.
    """
    issues: List[JobIssue] = []
    try:
        book_map = bejson_job_core_field_map(book_doc)
        needed = ("Record_Type_Parent", "chapter_uuid", "chapter_kind_text", "chapter_order_index")
        absent = [n for n in needed if n not in book_map]
        if absent or not isinstance(book_doc.get("Values"), list):
            return [JobIssue(E_JOB_BOOK_LINK, f"not a Book Document (missing {absent})", "book")]
        chapters = []
        for row in book_doc["Values"]:
            if isinstance(row, list) and row and row[book_map["Record_Type_Parent"]] == "Chapter":
                chapters.append((row[book_map["chapter_order_index"]], row[book_map["chapter_uuid"]], row[book_map["chapter_kind_text"]]))
        chapters.sort(key=lambda c: c[0] if _is_int(c[0]) else 10 ** 9)
        writable = [uuid_ for _, uuid_, kind in chapters if kind != "part"]
        from lib_bejson_Job_job_core import bejson_job_core_tasks  # local import keeps the top clean

        planned = [t["task_id"] for t in bejson_job_core_tasks(job_doc)]
    except JobError as exc:
        return [JobIssue(exc.code, str(exc), "link")]
    if planned != writable:
        missing = [c for c in writable if c not in planned]
        extra = [c for c in planned if c not in writable]
        detail = f"{len(missing)} writable chapter(s) have no task, {len(extra)} task(s) have no chapter" if (missing or extra) else "same chapters, different order"
        issues.append(JobIssue(E_JOB_BOOK_LINK, f"plan tasks do not match the book's writable chapters: {detail}", "link"))
    return issues


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------
def bejson_job_validator_validate_document(doc: Any, *, expect_book: Optional[bool] = None, book_doc: Optional[dict] = None) -> JobValidationResult:
    """
    Plan check "P". expect_book=None auto-detects (Job_Type 'writing' + Job_Subtype 'book' turns the book-plan header rules on);
    True / False force them on / off. With book_doc, task ids and order are also checked against the book (E_JOB_BOOK_LINK).
    """
    result = JobValidationResult()
    if not isinstance(doc, dict):
        result.errors.append(JobIssue(E_JOB_SCHEMA_MISMATCH, "document is not a JSON object", ""))
        return result
    for key in MANDATORY_KEYS:
        if key not in doc:
            result.errors.append(JobIssue(E_JOB_SCHEMA_MISMATCH, "mandatory BEJSON key is missing", key))
    _check_header(doc, result, expect_book)
    if _check_fields(doc, result):
        _check_rows(doc, result)
        if book_doc is not None:
            result.errors.extend(bejson_job_validator_check_book_link(doc, book_doc))
    return result


def bejson_job_validator_validate_file(path: str, *, expect_book: Optional[bool] = None, book_path: Optional[str] = None) -> JobValidationResult:
    """Loads with the Job loader (a load failure is reported as E_JOB_LOAD_FAILED in the result, not raised)."""
    result = JobValidationResult()
    try:
        doc = bejson_job_core_load(path)
        book = bejson_job_core_load(book_path) if book_path else None
    except JobError as exc:
        result.errors.append(JobIssue(exc.code if exc.code else E_JOB_LOAD_FAILED, str(exc), os.path.basename(path)))
        return result
    return bejson_job_validator_validate_document(doc, expect_book=expect_book, book_doc=book)


def bejson_job_validator_assert_valid(doc: Any, **kwargs: Any) -> None:
    result = bejson_job_validator_validate_document(doc, **kwargs)
    if not result.valid:
        raise JobError(f"{len(result.errors)} validation error(s); first: {result.errors[0].message}", E_JOB_VALIDATION_FAILED, issues=result.errors)


def bejson_job_validator_get_report(result: JobValidationResult) -> str:
    lines = [f"Result: {'VALID' if result.valid else 'INVALID'}{' WITH WARNINGS' if result.valid and result.warnings else ''}",
             f"Format: BEJSON 104a (Job Schema)  Tasks: {result.task_count}  Errors: {len(result.errors)}  Warnings: {len(result.warnings)}"]
    lines += [f"ERROR   {issue}" for issue in result.errors]
    lines += [f"WARNING {issue}" for issue in result.warnings]
    return "\n".join(lines)
