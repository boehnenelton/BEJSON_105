"""
Library:         lib_bejson_BEHTML_bootstrap.py
Family:          BEHTML
Module Purpose:  Locate the canonical 105 Core library and put it on sys.path (never copied into this family).
Architecture:    BEHTML on BEJSON 105: one 105 table, one row per placed element, X0-X7 lanes, Ry=32px rows, Rz=32px layers; all field access via the Core field map.
Version:         1.0.0
Release_Version: 301
Date:            2026-11-13
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Format_Creator:  Elton Boehnen
RELATIONAL_ID:   049cff0a-1d7c-402b-8ef7-e8ea78cae8d7
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Iterator, Optional

VERSION = "1.0.0"
SCRIPT_PATH = Path(__file__).resolve().parent

# Sole permitted canonical definitions fallback: $DEFINITIONS_FILE (policy 2.4).
_DEFAULT_DEFINITIONS_FILE = "/storage/emulated/0/.env/user/definitions.json"
_CORE_MARKER = "lib_bejson_Core_bejson_core.py"


def _definitions_lookup(key: str) -> Optional[str]:
    """Read one key from $DEFINITIONS_FILE (104a var_name/var_value or plain object)."""
    def_path = os.environ.get("DEFINITIONS_FILE") or _DEFAULT_DEFINITIONS_FILE
    try:
        with open(def_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError) as exc:
        logging.debug("[BEHTML_BOOTSTRAP] definitions.json unavailable: %s", exc)
        return None
    if isinstance(data, dict) and isinstance(data.get(key), str):
        return data[key]
    fields = data.get("Fields") if isinstance(data, dict) else None
    values = data.get("Values") if isinstance(data, dict) else None
    if isinstance(fields, list) and isinstance(values, list):
        names = [f.get("name") for f in fields if isinstance(f, dict)]
        key_col = next((names.index(n) for n in ("var_name", "name", "key", "setting_name") if n in names), None)
        val_col = next((names.index(n) for n in ("var_value", "value", "path", "setting_value") if n in names), None)
        if key_col is not None and val_col is not None:
            for row in values:
                if row[key_col] == key and isinstance(row[val_col], str):
                    return row[val_col]
    return None


def _candidate_paths() -> Iterator[Path]:
    # 1. Drop-in layout: Lib_PY/Core beside Lib_PY/BEHTML.
    yield SCRIPT_PATH.parent / "Core"
    # 2. Environment override, then $DEFINITIONS_FILE.
    root = os.environ.get("ADMIN_LIBRARIES_105") or _definitions_lookup("ADMIN_LIBRARIES_105")
    if root:
        yield Path(root) / "Lib_PY" / "Core"
        yield Path(root) / "Core"


def behtml_bootstrap_ensure_core_on_path() -> str:
    """Add the canonical 105 Core directory to sys.path once. Returns the path used."""
    for candidate in _candidate_paths():
        if (candidate / _CORE_MARKER).exists():
            text = str(candidate)
            if text not in sys.path:
                sys.path.insert(0, text)
            return text
    raise ImportError(
        "BEHTML: 105 Core not found. Place this family beside Lib_PY/Core, or set "
        "ADMIN_LIBRARIES_105 (or provide it in $DEFINITIONS_FILE). Core is never copied into BEHTML."
    )


ensure_core_on_path = behtml_bootstrap_ensure_core_on_path
behtml_bootstrap_ensure_core_on_path()
