#!/usr/bin/env python3
"""
Name:          lib_bejson_Metrics_metrics_errors.py
Description:   Canonical error registry (range 580-599) for the BEJSON 105 Metrics library family.
Version:       1.0.0
Date Created:  2026-11-18
Author Credit: Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
RELATIONAL_ID: lib-bejson-metrics-errors-20261118
License:       PolyForm-Noncommercial-1.0.0
"""

from __future__ import annotations

import sys

if sys.version_info < (3, 10):
    raise RuntimeError("Python 3.10+ is required.")

E_METRICS_SCHEMA_INVALID: int = 580
E_METRICS_NEGATIVE_VALUE: int = 581
E_METRICS_MISSING_SOURCE: int = 582
E_METRICS_RENDER_FAILED: int = 583
E_METRICS_LOCK_TIMEOUT: int = 584


class MetricsLibraryError(Exception):
    """Structured exception carrying canonical Metrics error codes (580-599)."""

    def __init__(self, message: str, error_code: int = E_METRICS_SCHEMA_INVALID) -> None:
        super().__init__(f"[{error_code}] {message}")
        self.error_code: int = error_code
        self.message: str = message
