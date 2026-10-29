"""
File Name : lib_bejson_Standards_errors.py
Rel. Path : Lib_PY/Standards/lib_bejson_Standards_errors.py
Purpose   : Standards ERRORS: numeric error codes 250-269 for the standardized logging sink. Source of truth for this family.
VERSION   : 3.0.0
Author    : Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
RELATIONAL_ID : c23a2c11-3480-4fe7-87e0-c424926ba67f

Range claim: 250-269. Checked against libraries_104 + libraries_105: Core 1-99 (MD 90-99), Core_Nesting
130-159, Core_Extension 160-189, AI 200-235, Cognition 270-289, BEHTML 300-329, BEHTML_IDE 330-359,
Terminal_Menus 360-389, Diagrams 420-435, Bookmaker 450-479, Lists 480-499: no overlap. (An earlier
draft used 180-199, which overlaps Core_Extension's 160-189; re-check this table when claiming new blocks.)
"""
from __future__ import annotations

VERSION = "3.0.0"

# ---------------------------------------------------------------------------
# Standards Logging (250-269)
# ---------------------------------------------------------------------------
E_STANDARDS_LOG_INVALID_LEVEL    = 250  # level is not one of DEBUG/INFO/WARN/ERROR/FATAL
E_STANDARDS_LOG_SCHEMA_MISMATCH  = 251  # an entry, row or existing file does not match the canonical log schema
E_STANDARDS_LOG_WRITE_FAILED     = 252  # the atomic write did not complete
E_STANDARDS_LOG_BUFFER_CORRUPT   = 253  # an existing log file could not be parsed (quarantined, fresh file started)
E_STANDARDS_LOG_LOCK_TIMEOUT     = 254  # the PID lock on the log file was not acquired in time
E_STANDARDS_LOG_INVALID_CONFIG   = 255  # row_cap / min_level / batch settings are invalid
E_STANDARDS_LOG_SECURE_PATH_MISSING = 256  # secure entry logged but the sink has no secure_path (refused, never routed to the main log)
E_STANDARDS_LOG_SECURE_VIOLATION = 257  # secure/non-secure mix: wrong file kind, or a secure row headed for a non-secure file
E_STANDARDS_EXPORT_FORMAT_INVALID = 258      # unknown export format / sort / theme, or bad filter value
E_STANDARDS_EXPORT_FAILED = 259              # export could not be produced or written (includes refusing to overwrite a registered log file)
E_STANDARDS_ARCHIVE_FAILED = 260             # archive write, move or prune failed (the live log is left untouched)
E_STANDARDS_EXPORT_SECURE_DESTINATION = 261  # secure export aimed at the main log or inside the main archive tree
# 262-269 reserved, unassigned.

ERROR_NAMES = {
    250: "E_STANDARDS_LOG_INVALID_LEVEL",
    251: "E_STANDARDS_LOG_SCHEMA_MISMATCH",
    252: "E_STANDARDS_LOG_WRITE_FAILED",
    253: "E_STANDARDS_LOG_BUFFER_CORRUPT",
    254: "E_STANDARDS_LOG_LOCK_TIMEOUT",
    255: "E_STANDARDS_LOG_INVALID_CONFIG",
    256: "E_STANDARDS_LOG_SECURE_PATH_MISSING",
    257: "E_STANDARDS_LOG_SECURE_VIOLATION",
    258: "E_STANDARDS_EXPORT_FORMAT_INVALID",
    259: "E_STANDARDS_EXPORT_FAILED",
    260: "E_STANDARDS_ARCHIVE_FAILED",
    261: "E_STANDARDS_EXPORT_SECURE_DESTINATION",
}


class StandardsLogError(Exception):
    """Raised by core/validator helpers. The public log() facade catches it and never re-raises."""

    def __init__(self, message: str, code: int):
        super().__init__(f"[{ERROR_NAMES.get(code, code)}] {message}")
        self.code = code
