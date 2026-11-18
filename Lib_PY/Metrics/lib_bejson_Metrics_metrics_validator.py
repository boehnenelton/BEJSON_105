#!/usr/bin/env python3
"""
Name:          lib_bejson_Metrics_metrics_validator.py
Description:   Standardization and integrity validator for BEJSON 105a metrics ledgers.
Version:       1.0.0
Date Created:  2026-11-18
Author Credit: Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
RELATIONAL_ID: lib-bejson-metrics-validator-20261118
License:       PolyForm-Noncommercial-1.0.0
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

if sys.version_info < (3, 10):
    raise RuntimeError("Python 3.10+ is required.")

_CORE_DIR: Path = Path(__file__).resolve().parent.parent / "Core"
if str(_CORE_DIR) not in sys.path:
    sys.path.insert(0, str(_CORE_DIR))

from lib_bejson_Core_bejson_core import bejson_core_get_field_map
from lib_bejson_Core_bejson_validator import validate_bejson
from lib_bejson_Metrics_metrics_errors import (
    E_METRICS_MISSING_SOURCE,
    E_METRICS_NEGATIVE_VALUE,
    E_METRICS_SCHEMA_INVALID,
    MetricsLibraryError,
)
from lib_bejson_Metrics_metrics_schemas import METRICS_RUN_FIELD_SPECS

LOGGER_INSTANCE = logging.getLogger("lib_bejson_Metrics.validator")

_NON_NEGATIVE_NUMERIC_FIELDS: Tuple[str, ...] = (
    "primary_value",
    "baseline_value",
    "speedup_factor",
    "peak_rss_mb",
)


def validate_metrics_document(document_payload: Dict[str, Any]) -> Dict[str, Any]:
    """Validate BEJSON 105a structure, required fields, O(1) field map, and non-negative bounds."""
    validation_result = validate_bejson(document_payload, is_file=False)
    if not validation_result.is_valid:
        raise MetricsLibraryError(
            f"BEJSON validation failed: {validation_result.errors}",
            error_code=E_METRICS_SCHEMA_INVALID,
        )

    field_map = bejson_core_get_field_map(document_payload)
    required_names = [spec_name for spec_name, _ in METRICS_RUN_FIELD_SPECS]
    missing_fields = [name for name in required_names if name not in field_map]
    if missing_fields:
        raise MetricsLibraryError(
            f"Missing required metrics fields: {missing_fields}",
            error_code=E_METRICS_SCHEMA_INVALID,
        )

    # 105-series rows include implicit column-0 record_uuid; field_map maps data fields by column index
    rows_list: List[List[Any]] = document_payload.get("Values", [])
    for row_index, row_values in enumerate(rows_list):
        for numeric_field in _NON_NEGATIVE_NUMERIC_FIELDS:
            col_idx = field_map[numeric_field]
            cell_value = row_values[col_idx]
            if isinstance(cell_value, (int, float)) and cell_value < 0:
                raise MetricsLibraryError(
                    f"Row {row_index} field '{numeric_field}' has negative value {cell_value}",
                    error_code=E_METRICS_NEGATIVE_VALUE,
                )

    LOGGER_INSTANCE.info("Validated metrics ledger with %d record(s).", len(rows_list))
    return {
        "valid": True,
        "record_count": len(rows_list),
        "field_count": len(required_names),
    }


def validate_metrics_file(ledger_file_path: Path) -> Dict[str, Any]:
    """Load and validate a BEJSON 105a metrics ledger file from disk."""
    if not ledger_file_path.is_file():
        raise MetricsLibraryError(
            f"Metrics ledger file not found: {ledger_file_path}",
            error_code=E_METRICS_MISSING_SOURCE,
        )
    loaded_document = json.loads(ledger_file_path.read_text(encoding="utf-8"))
    return validate_metrics_document(loaded_document)
