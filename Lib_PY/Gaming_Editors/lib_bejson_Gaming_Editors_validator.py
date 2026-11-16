"""
Library:        lib_bejson_Gaming_Editors_validator.py
Family:         Gaming_Editors
Description:    Two-tier barrier of entry validator for Gaming_Editors 105 Family.
                Enforces foundational Core Family validation and domain validation
                for Sprite Studio, Tilemap Palette, HUD Stage, and Animation configurations.
BEJSON:         BEJSON stands for BOEHNEN ELTON JSON. Authoritative definition;
                do not restate or reinterpret this acronym elsewhere.
                (Pronounced Bee-Jay-Son / Bay-nin Elton JSON)
MFDB:           MFDB stands for Multi File Database. Authoritative definition;
                do not restate or reinterpret this acronym elsewhere.
Version:        1.0.0
Date:           2026-11-15
Author:         Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
License:        PolyForm-Noncommercial-1.0.0
RELATIONAL_ID:  9d1c3e4f-5a6b-7c8d-9e0f-1a2b3c4d5e6f
Release_Version: 300
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

_HERE = os.path.dirname(os.path.abspath(__file__))
for _fam in ('Core', 'Standards', 'Taxonomies', 'Graphics', 'Gaming_Editors'):
    _p = os.path.normpath(os.path.join(_HERE, "..", _fam))
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

from lib_bejson_Core_bejson_validator import (
    validate_bejson,
    ValidationResult,
    BEJSONValidationError
)
from lib_bejson_Core_bejson_core import bejson_core_get_field_map

from lib_bejson_Gaming_Editors_errors import (
    E_GAMING_EDITORS_CORE_VALIDATION_FAILED,
    E_GAMING_EDITORS_INVALID_RECORDS_TYPE,
    E_GAMING_EDITORS_INVALID_SPRITE_GRID,
    E_GAMING_EDITORS_INVALID_TILEMAP_PALETTE,
    E_GAMING_EDITORS_INVALID_COLLISION_FLAG,
    E_GAMING_EDITORS_INVALID_HUD_LAYOUT,
    E_GAMING_EDITORS_INVALID_ANIM_TIMELINE,
    E_GAMING_EDITORS_INVALID_SVG_MARKUP,
    E_GAMING_EDITORS_PALETTE_VIOLATION,
    E_GAMING_EDITORS_STAGE_NOT_FOUND,
    E_GAMING_EDITORS_BARRIER_OF_ENTRY_FAILED,
    GamingEditorsValidationError,
    ERROR_NAMES
)

logger = logging.getLogger("lib_bejson_Gaming_Editors_validator")
VERSION = "1.0.0"

VALID_GAMING_EDITORS_RECORDS_TYPES: Set[str] = {
    "GamingSpriteStudioConfig",
    "GamingTilemapPaletteConfig",
    "GamingHudStageConfig",
    "GamingAnimTimelineConfig",
    "GraphicCanvasConfig",
    "GraphicFrameRecord",
    "ProjectileImpactDynamics",
    "GamingCombatAnimationState",
    "GamingWeaponCombatRecord",
    "GamingProjectileRecord"
}

ALLOWED_CELL_SIZES: Set[int] = {16, 24, 32, 48, 64}


def validate_gaming_editors_barrier(
    input_data: Any,
    is_file: bool = False
) -> ValidationResult:
    """
    Two-Tier Barrier of Entry:
    1. Foundational Core Family Barrier: validate_bejson() checks structural envelope,
       Format=BEJSON, Format_Version, field types, and E90-E95 UUID integrity.
    2. Gaming_Editors Domain Barrier: checks editor records types, cell sizes,
       grid bounds, and collision flags.
    """
    core_result = validate_bejson(input_data, is_file=is_file)
    if not core_result.valid:
        core_result.errors.insert(
            0,
            f"[{ERROR_NAMES[E_GAMING_EDITORS_CORE_VALIDATION_FAILED]}] "
            f"Core Family barrier rejected document ({len(core_result.errors)} core errors)"
        )
        return core_result

    doc: Dict[str, Any] = {}
    if is_file:
        try:
            with open(input_data, "r", encoding="utf-8") as f:
                doc = json.load(f)
        except Exception as exc:
            core_result.add_error(f"Failed to read file for editor validation: {exc}")
            return core_result
    elif isinstance(input_data, dict):
        doc = input_data
    elif isinstance(input_data, str):
        try:
            doc = json.loads(input_data)
        except Exception as exc:
            core_result.add_error(f"Failed to parse JSON string: {exc}")
            return core_result

    records_types = doc.get("Records_Type") or doc.get("Record_Type") or []
    if isinstance(records_types, list):
        for r_type in records_types:
            if r_type not in VALID_GAMING_EDITORS_RECORDS_TYPES:
                core_result.add_warning(
                    f"[{ERROR_NAMES[E_GAMING_EDITORS_INVALID_RECORDS_TYPE]}] "
                    f"Unregistered Gaming_Editors Records_Type '{r_type}'"
                )

    values_rows = doc.get("Values", [])
    if isinstance(values_rows, list) and len(values_rows) > 0:
        field_map = bejson_core_get_field_map(doc)

        for row_idx, row in enumerate(values_rows):
            if not isinstance(row, list):
                continue

            if "cell_size_px" in field_map:
                c_idx = field_map["cell_size_px"]
                if c_idx < len(row):
                    cs = row[c_idx]
                    if not isinstance(cs, int) or cs not in ALLOWED_CELL_SIZES:
                        core_result.add_error(
                            f"[{ERROR_NAMES[E_GAMING_EDITORS_INVALID_SPRITE_GRID]}] "
                            f"Row #{row_idx} cell_size_px {cs} must be one of {sorted(ALLOWED_CELL_SIZES)}"
                        )

            if "tile_size_px" in field_map:
                t_idx = field_map["tile_size_px"]
                if t_idx < len(row):
                    ts = row[t_idx]
                    if not isinstance(ts, int) or ts not in ALLOWED_CELL_SIZES:
                        core_result.add_error(
                            f"[{ERROR_NAMES[E_GAMING_EDITORS_INVALID_TILEMAP_PALETTE]}] "
                            f"Row #{row_idx} tile_size_px {ts} must be one of {sorted(ALLOWED_CELL_SIZES)}"
                        )

    return core_result


def bejson_gaming_editors_validator_validate_doc(doc: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validates an editor document dictionary against both Core and Gaming_Editors barriers."""
    res = validate_gaming_editors_barrier(doc, is_file=False)
    return res.valid, res.errors


def bejson_gaming_editors_validator_validate_file(file_path: Union[str, Path]) -> bool:
    """Validates an editor file on disk against both Core and Gaming_Editors barriers."""
    f_path = Path(file_path).resolve()
    if not f_path.exists():
        raise GamingEditorsValidationError(f"File not found: {f_path}", E_GAMING_EDITORS_BARRIER_OF_ENTRY_FAILED)

    res = validate_gaming_editors_barrier(str(f_path), is_file=True)
    if not res.valid:
        first_err = res.errors[0] if res.errors else "Unknown barrier failure"
        raise GamingEditorsValidationError(first_err, E_GAMING_EDITORS_BARRIER_OF_ENTRY_FAILED)
    return True


# Name_Case Architectural Component Bindings
Validate_Gaming_Editors_Barrier = validate_gaming_editors_barrier
Bejson_Gaming_Editors_Validator_Validate_Doc = bejson_gaming_editors_validator_validate_doc
Bejson_Gaming_Editors_Validator_Validate_File = bejson_gaming_editors_validator_validate_file
