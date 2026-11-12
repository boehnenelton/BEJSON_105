"""
Library:        lib_bejson_Automation_automation_errors.py
Family:         Automation
Description:    Deterministic exit-code registry and error definitions for BEJSON Automation FSM pipelines.
BEJSON:         BEJSON stands for BOEHNEN ELTON JSON. Authoritative definition;
                do not restate or reinterpret this acronym elsewhere.
                (Pronounced Bee-Jay-Son / Bay-nin Elton JSON)
MFDB:           MFDB stands for Multi File Database. Authoritative definition;
                do not restate or reinterpret this acronym elsewhere.
Version:        1.0.0
Date:           2026-11-11
Author:         Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
RELATIONAL_ID:  a4e18b02-73df-4821-b841-86105f9cb531
License:        PolyForm Noncommercial License 1.0.0
"""

from __future__ import annotations

from typing import Final

# Deterministic Process Exit Codes
EXIT_OK: Final[int] = 0                    # Execution succeeded cleanly
EXIT_PARTIAL_FAILURE: Final[int] = 1       # One or more stages or assets encountered recoverable failure
EXIT_PATH_FAILURE: Final[int] = 10          # Required path, directory, or asset missing
EXIT_ENV_FAILURE: Final[int] = 20           # Malformed environment or missing configuration
EXIT_SCHEMA_FAILURE: Final[int] = 30        # BEJSON structural validation or hash mismatch
EXIT_DEP_MISSING: Final[int] = 40           # Required binary, command, or module missing
EXIT_BUSY: Final[int] = 50                  # Concurrency lock held by active process
EXIT_CYCLE_DETECTED: Final[int] = 60        # Recursive DAG loop or cycle encountered
EXIT_THRESHOLD_EXCEEDED: Final[int] = 70    # Max repetition count exceeded without resolution
EXIT_TIMEOUT_EXHAUSTED: Final[int] = 80     # Stage wall-clock execution timeout exceeded
EXIT_INTERRUPTED: Final[int] = 130          # Interrupted via POSIX SIGINT/SIGTERM


class AutomationFSMError(Exception):
    """Base exception for all BEJSON Automation FSM pipeline errors."""
    def __init__(self, message: str, exit_code: int = EXIT_PARTIAL_FAILURE) -> None:
        super().__init__(message)
        self.exit_code = exit_code


class AutomationSchemaValidationError(AutomationFSMError):
    """Raised when an FSM manifest or signal violates canonical BEJSON 105a schema."""
    def __init__(self, message: str) -> None:
        super().__init__(message, exit_code=EXIT_SCHEMA_FAILURE)


class AutomationCycleError(AutomationFSMError):
    """Raised when an infinite transition loop or recursive trace cycle is detected."""
    def __init__(self, message: str) -> None:
        super().__init__(message, exit_code=EXIT_CYCLE_DETECTED)


class AutomationTimeoutError(AutomationFSMError):
    """Raised when a stage node exceeds its configured wall-clock timeout ceiling."""
    def __init__(self, message: str) -> None:
        super().__init__(message, exit_code=EXIT_TIMEOUT_EXHAUSTED)


class AutomationThresholdExceededError(AutomationFSMError):
    """Raised when a repetition count ceiling is exceeded with no conditional route."""
    def __init__(self, message: str) -> None:
        super().__init__(message, exit_code=EXIT_THRESHOLD_EXCEEDED)
