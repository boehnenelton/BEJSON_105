"""
Library:         lib_bejson_Job_bejson_errors.py
Family:          Job
Module Purpose:  Job family ERRORS: numeric error codes 390-419, named constants, and the JobError exception. Source of truth for this family.
Architecture:    BEJSON 105 library tier. Operates on the BEJSON 104a Job Schema (JobMaker, 11-field JobTask). No dependency on any other family.
Version:         1.0.0
Release_Version: 301
Date:            2026-11-14
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Format_Creator:  Elton Boehnen
RELATIONAL_ID:   2b713dbf-77f7-4081-a265-f91d8bb452bb

Range claim: 390-419. Free per Libraries_105 Agent Directive section 9 (free = 190-199, 236-249, 390-419, 520+).
Owned elsewhere: Core 1-99, Nesting 130-159, Extension 160-189, AI 200-235, Standards 250-269, Cognition 270-289,
BEHTML 300-359, Terminal_Menus 360-389, Diagrams 420-449, Bookmaker 450-479, Lists 480-499, Graphics 500-519.
No code from another family is borrowed or redefined here. 417-419 are reserved, unassigned.
"""
from __future__ import annotations

from typing import List, Optional

VERSION = "1.0.0"

# ---------------------------------------------------------------------------
# Job family (390-419)
# ---------------------------------------------------------------------------
E_JOB_LOAD_FAILED            = 390  # job file missing, unreadable, or not a JSON object
E_JOB_SCHEMA_MISMATCH        = 391  # Format/Format_Version/Format_Creator/Records_Type/Fields differ from the Job Schema
E_JOB_HEADER_INVALID         = 392  # header key missing, extra, mistyped, or a book-plan header rule broken
E_JOB_FORBIDDEN_COLUMN       = 393  # a Target_File or test_cmd column is present (plans never carry shell data)
E_JOB_SHELL_FORBIDDEN        = 394  # a non-empty test_cmd was found; shell commands are never run or carried
E_JOB_ROW_SHAPE              = 395  # a Values row is not a list or not exactly as wide as Fields
E_JOB_TASK_VALUE_TYPE        = 396  # a task cell has the wrong type (null is not accepted)
E_JOB_TASK_ID_INVALID        = 397  # task_id is not a canonical lowercase hyphenated UUID
E_JOB_TASK_ID_DUPLICATE      = 398  # two tasks share a task_id
E_JOB_ORDER_INVALID          = 399  # task_order values are not exactly 1..N
E_JOB_TEXT_EMPTY             = 400  # task_name or the first paragraph of task_description is empty
E_JOB_CELL_SHAPE             = 401  # task_context / task_reference is not an array of runner shapes
E_JOB_PATH_INVALID           = 402  # a ref is not a relative forward-slash path (no .., drive letter or leading slash)
E_JOB_COMPLETION_MISMATCH    = 403  # Job_Complete / Completion_Date disagree with the tasks
E_JOB_AUDIT_INCONSISTENT     = 404  # audit fields contradict each other or task_completed
E_JOB_BOOK_LINK              = 405  # plan tasks do not match the Book Document's writable chapters
E_JOB_GATE_UNKNOWN           = 406  # unknown gate rule or profile
E_JOB_NO_EXECUTOR            = 407  # step/run was asked to execute a task but no executor was supplied
E_JOB_EXECUTOR_FAILED        = 408  # the executor raised or returned something that is not text
E_JOB_STAGE_WRITE_FAILED     = 409  # the staged output file could not be written
E_JOB_WRITE_FAILED           = 410  # the atomic write of the job file did not complete
E_JOB_LOCK_TIMEOUT           = 411  # the PID lock on the job file was not acquired in time
E_JOB_TASK_NOT_FOUND         = 412  # no task with that task_id
E_JOB_VALIDATION_FAILED      = 413  # a document failed validation and was therefore not written
E_JOB_TEMPLATE_INVALID       = 414  # template payload is not a valid Job Schema document
E_JOB_CORE_NOT_FOUND         = 415  # Lib_PY/Core could not be located (sibling folder or ADMIN_LIBRARIES_105)
E_JOB_PATH_ESCAPE            = 416  # a path resolved outside the project root
# 417-419 reserved, unassigned.

ERROR_NAMES = {
    390: "E_JOB_LOAD_FAILED",
    391: "E_JOB_SCHEMA_MISMATCH",
    392: "E_JOB_HEADER_INVALID",
    393: "E_JOB_FORBIDDEN_COLUMN",
    394: "E_JOB_SHELL_FORBIDDEN",
    395: "E_JOB_ROW_SHAPE",
    396: "E_JOB_TASK_VALUE_TYPE",
    397: "E_JOB_TASK_ID_INVALID",
    398: "E_JOB_TASK_ID_DUPLICATE",
    399: "E_JOB_ORDER_INVALID",
    400: "E_JOB_TEXT_EMPTY",
    401: "E_JOB_CELL_SHAPE",
    402: "E_JOB_PATH_INVALID",
    403: "E_JOB_COMPLETION_MISMATCH",
    404: "E_JOB_AUDIT_INCONSISTENT",
    405: "E_JOB_BOOK_LINK",
    406: "E_JOB_GATE_UNKNOWN",
    407: "E_JOB_NO_EXECUTOR",
    408: "E_JOB_EXECUTOR_FAILED",
    409: "E_JOB_STAGE_WRITE_FAILED",
    410: "E_JOB_WRITE_FAILED",
    411: "E_JOB_LOCK_TIMEOUT",
    412: "E_JOB_TASK_NOT_FOUND",
    413: "E_JOB_VALIDATION_FAILED",
    414: "E_JOB_TEMPLATE_INVALID",
    415: "E_JOB_CORE_NOT_FOUND",
    416: "E_JOB_PATH_ESCAPE",
}

# Process exit codes (owner policy). Anything else a CLI needs is documented in README.
EXIT_OK = 0
EXIT_RUNTIME_FAILURE = 1
EXIT_PATH_SELECTION_FAILURE = 10
EXIT_ENVIRONMENT_FAILURE = 20
EXIT_VALIDATION_FAILURE = 30


class JobError(Exception):
    """Raised by Job core/runner. `code` is a named constant above; `issues` carries validator issues when relevant."""

    def __init__(self, message: str, code: int, issues: Optional[List] = None):
        super().__init__(f"[{ERROR_NAMES.get(code, code)}] {message}")
        self.code = code
        self.issues = list(issues or [])
