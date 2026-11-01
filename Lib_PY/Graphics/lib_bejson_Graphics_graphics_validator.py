"""
Library:        lib_bejson_Graphics_graphics_validator.py
Family:         Graphics
Description:    Graphics Domain VALIDATOR: Enforces two-tier barrier of entry
                (Core Family Validator + Graphics Domain Validator) for blank-slate canvas stages,
                timeline schemas, frame duration quantization, Remove_Frame_Source flags, and MFDB federation.
Version:        1.1.0
Date:           2026-11-01
Author:         Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Format_Creator: Elton Boehnen
RELATIONAL_ID:  4f8a2b1c-9d3e-4f7a-8b1c-0e2f3a4b5c6d
Release_Version: 300
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

# Sibling family resolution
_HERE = os.path.dirname(os.path.abspath(__file__))
for _fam in ('Core', 'Standards', 'Taxonomies', 'Canvas', 'Graphics'):
    _p = os.path.normpath(os.path.join(_HERE, "..", _fam))
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

# Core Family validator imports (The foundational barrier of entry)
from lib_bejson_Core_bejson_validator import (
    validate_bejson,
    ValidationResult,
    BEJSONValidationError
)
from lib_bejson_Core_bejson_core import bejson_core_get_field_map

# Core MFDB validator import
try:
    from lib_bejson_Core_mfdb_validator import validate_mfdb_database
except ImportError:
    validate_mfdb_database = None

# Graphics Error registry
from lib_bejson_Graphics_graphics_errors import (
    E_GRAPHICS_CORE_VALIDATION_FAILED,
    E_GRAPHICS_INVALID_RECORDS_TYPE,
    E_GRAPHICS_INVALID_DIMENSIONS,
    E_GRAPHICS_INVALID_ASPECT_RATIO,
    E_GRAPHICS_INVALID_FPS,
    E_GRAPHICS_INVALID_DURATION,
    E_GRAPHICS_INVALID_FRAME_SEQUENCE,
    E_GRAPHICS_INVALID_TIMELINE_ROW,
    E_GRAPHICS_INVALID_SVG_MARKUP,
    E_GRAPHICS_PALETTE_VIOLATION,
    E_GRAPHICS_STAGE_CONFIG_INVALID,
    E_GRAPHICS_TEMPLATE_NOT_FOUND,
    E_GRAPHICS_BARRIER_OF_ENTRY_FAILED,
    GraphicsValidationError,
    ERROR_NAMES
)

logger = logging.getLogger("lib_bejson_Graphics_graphics_validator")
VERSION = "1.1.0"

# Canonical Graphics Records_Types
VALID_GRAPHICS_RECORDS_TYPES: Set[str] = {
    "GraphicCanvasConfig",
    "GraphicFrameRecord",
    "GraphicTimelineRecord",
    "SvgAnimationTimelineRecord",
    "GraphicCanvasTemplate",
    "CanvasTemplateRecord",
    "GraphicStageRecord",
    "GraphicTextureTile",
    "GraphicSlideshowRecord",
    "GraphicSlideRecord",
    "BrandingSlideRecord",
    "mfdb"
}

# Policy §8.1 Tri-Color Canonical Palette & Authorized Neutral Dark Accents
AUTHORIZED_PALETTE_HEX: Set[str] = {
    "#000000", "#FFFFFF", "#DE2626",  # Canonical Tri-Color
    "#08080C", "#0C0C10", "#14141A", "#14141E", "#1C1C24", "#2A2A38", "#333333"  # Neutral dark tones
}

ASPECT_RATIO_RE = re.compile(r"^\d+:\d+$")
COLOR_HEX_RE = re.compile(r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


def bejson_graphics_validator_check_palette(color_str: str) -> bool:
    """Verifies that a hex color string conforms to Policy §8.1 Tri-Color standards."""
    if not isinstance(color_str, str):
        return False
    color_upper = color_str.strip().upper()
    if color_upper in AUTHORIZED_PALETTE_HEX:
        return True
    if color_upper.startswith("RGBA(") or color_upper.startswith("RGB("):
        return True
    return False


def bejson_graphics_validator_check_svg(svg_markup: str) -> Tuple[bool, Optional[str]]:
    """Checks whether an SVG string is valid: either inline <svg> markup or .svg file reference."""
    if not isinstance(svg_markup, str):
        return False, "SVG markup is not a string"
    stripped = svg_markup.strip()
    if not stripped:
        return False, "SVG markup is empty"
    if stripped.endswith(".svg") or stripped.endswith(".SVG"):
        return True, None
    if not stripped.startswith("<svg") or "</svg>" not in stripped:
        return False, "SVG markup does not contain valid <svg> and </svg> tags or valid .svg filename"
    return True, None


def validate_graphics_barrier(
    input_data: Any,
    is_file: bool = False
) -> ValidationResult:
    """
    Two-Tier Barrier of Entry:
    1. Foundational Core Family Barrier: Runs validate_bejson() to verify structural integrity,
       mandatory keys, field types, field map cache keys, and E90-E95 UUID integrity.
    2. Graphics Domain Barrier: Runs graphics domain checks (Records_Type, Width/Height,
       FPS, Duration, frame pacing, sequential frame indices, Remove_Frame_Source boolean,
       and Policy §8.1 Tri-Color compliance).
    Documents must pass BOTH barriers to enter the Graphics pipeline.
    """
    # -------------------------------------------------------------------------
    # Barrier 1: Foundational Core Family Barrier
    # -------------------------------------------------------------------------
    core_result = validate_bejson(input_data, is_file=is_file)
    if not core_result.valid:
        core_result.errors.insert(
            0,
            f"[{ERROR_NAMES[E_GRAPHICS_CORE_VALIDATION_FAILED]}] "
            f"Core Family barrier rejected document ({len(core_result.errors)} core errors)"
        )
        return core_result

    # Load JSON document dictionary
    doc: Dict[str, Any] = {}
    if is_file:
        try:
            with open(input_data, "r", encoding="utf-8") as f:
                doc = json.load(f)
        except Exception as exc:
            core_result.add_error(f"Failed to read file for graphics validation: {exc}")
            return core_result
    elif isinstance(input_data, dict):
        doc = input_data
    elif isinstance(input_data, str):
        try:
            doc = json.loads(input_data)
        except Exception as exc:
            core_result.add_error(f"Failed to parse JSON string: {exc}")
            return core_result

    # -------------------------------------------------------------------------
    # Barrier 2: Graphics Domain Barrier
    # -------------------------------------------------------------------------
    records_types = doc.get("Records_Type", [])
    if isinstance(records_types, list):
        for r_type in records_types:
            if r_type not in VALID_GRAPHICS_RECORDS_TYPES:
                core_result.add_warning(
                    f"[{ERROR_NAMES[E_GRAPHICS_INVALID_RECORDS_TYPE]}] "
                    f"Unregistered Graphics Records_Type '{r_type}'"
                )

    # 2.1 Check MFDB Manifest if applicable
    if "mfdb" in records_types or "MFDB_Version" in doc:
        if validate_mfdb_database and is_file:
            try:
                mfdb_res = validate_mfdb_database(input_data, strict_fk=True)
                if not mfdb_res.valid:
                    for err_msg in mfdb_res.errors:
                        core_result.add_error(f"[MFDB_VALIDATION] {err_msg}")
            except Exception as exc:
                core_result.add_error(f"MFDB database validation failed: {exc}")

    # 2.2 Check Top-Level Remove_Frame_Source boolean header (105a/104a)
    if "Remove_Frame_Source" in doc:
        rfs = doc["Remove_Frame_Source"]
        if not isinstance(rfs, bool):
            core_result.add_error(
                f"[{ERROR_NAMES[E_GRAPHICS_STAGE_CONFIG_INVALID]}] "
                f"Header 'Remove_Frame_Source' must be a boolean (true/false), got {type(rfs).__name__}"
            )

    # 2.3 Check Dimensions in Header if present
    width_px = doc.get("Width_Px")
    if width_px is not None:
        if not isinstance(width_px, int) or width_px <= 0:
            core_result.add_error(
                f"[{ERROR_NAMES[E_GRAPHICS_INVALID_DIMENSIONS]}] "
                f"Width_Px must be an integer > 0, got {width_px!r}"
            )

    height_px = doc.get("Height_Px")
    if height_px is not None:
        if not isinstance(height_px, int) or height_px <= 0:
            core_result.add_error(
                f"[{ERROR_NAMES[E_GRAPHICS_INVALID_DIMENSIONS]}] "
                f"Height_Px must be an integer > 0, got {height_px!r}"
            )

    # 2.4 Check Aspect Ratio format
    aspect_ratio = doc.get("Aspect_Ratio")
    if aspect_ratio is not None:
        if not isinstance(aspect_ratio, str) or not ASPECT_RATIO_RE.match(aspect_ratio):
            core_result.add_error(
                f"[{ERROR_NAMES[E_GRAPHICS_INVALID_ASPECT_RATIO]}] "
                f"Aspect_Ratio '{aspect_ratio}' must match format 'W:H' (e.g. '1:1', '16:9')"
            )

    # 2.5 Check FPS in Header
    fps_val = doc.get("FPS")
    if fps_val is not None:
        if not isinstance(fps_val, int) or fps_val <= 0:
            core_result.add_error(
                f"[{ERROR_NAMES[E_GRAPHICS_INVALID_FPS]}] "
                f"FPS must be an integer > 0, got {fps_val!r}"
            )

    # 2.6 Check Duration in Header
    duration_sec = doc.get("Duration_Sec")
    if duration_sec is not None:
        if not isinstance(duration_sec, (int, float)) or duration_sec <= 0:
            core_result.add_error(
                f"[{ERROR_NAMES[E_GRAPHICS_INVALID_DURATION]}] "
                f"Duration_Sec must be a number > 0, got {duration_sec!r}"
            )

    total_dur_ms = doc.get("Total_Duration_Ms")
    if total_dur_ms is not None:
        if not isinstance(total_dur_ms, (int, float)) or total_dur_ms <= 0:
            core_result.add_error(
                f"[{ERROR_NAMES[E_GRAPHICS_INVALID_DURATION]}] "
                f"Total_Duration_Ms must be a number > 0, got {total_dur_ms!r}"
            )

    # 2.7 Row-Level Graphics Domain Checks via O(1) Field Map
    values_rows = doc.get("Values", [])
    if isinstance(values_rows, list) and len(values_rows) > 0:
        field_map = bejson_core_get_field_map(doc)

        has_frame_idx = "frame_index" in field_map
        has_frame_dur = "frame_duration_ms" in field_map
        has_ts_ms = "timestamp_ms" in field_map
        has_ts_sec = "timestamp_sec" in field_map
        has_seek = "seek_progress" in field_map
        has_rot = "rotation_deg" in field_map
        has_scale = "scale_factor" in field_map
        has_opacity = "opacity" in field_map
        has_svg = "svg_markup" in field_map
        has_rfs = "remove_frame_source" in field_map
        has_accent = "accent_color" in field_map
        has_theme = "bg_theme" in field_map

        last_frame_idx = -1

        for row_idx, row in enumerate(values_rows):
            if not isinstance(row, list):
                continue

            # Check sequential frame_index
            if has_frame_idx:
                col_idx = field_map["frame_index"]
                if col_idx < len(row):
                    f_idx = row[col_idx]
                    if not isinstance(f_idx, int) or f_idx < 0:
                        core_result.add_error(
                            f"[{ERROR_NAMES[E_GRAPHICS_INVALID_FRAME_SEQUENCE]}] "
                            f"Row #{row_idx} frame_index must be non-negative integer, got {f_idx!r}"
                        )
                    elif f_idx != last_frame_idx + 1:
                        core_result.add_error(
                            f"[{ERROR_NAMES[E_GRAPHICS_INVALID_FRAME_SEQUENCE]}] "
                            f"Row #{row_idx} non-sequential frame_index {f_idx}; expected {last_frame_idx + 1}"
                        )
                    last_frame_idx = f_idx

            # Check frame_duration_ms > 0
            if has_frame_dur:
                col_idx = field_map["frame_duration_ms"]
                if col_idx < len(row):
                    dur = row[col_idx]
                    if not isinstance(dur, (int, float)) or dur <= 0:
                        core_result.add_error(
                            f"[{ERROR_NAMES[E_GRAPHICS_INVALID_DURATION]}] "
                            f"Row #{row_idx} frame_duration_ms must be > 0, got {dur!r}"
                        )

            # Check timestamp >= 0
            if has_ts_ms:
                col_idx = field_map["timestamp_ms"]
                if col_idx < len(row):
                    tms = row[col_idx]
                    if not isinstance(tms, (int, float)) or tms < 0:
                        core_result.add_error(
                            f"[{ERROR_NAMES[E_GRAPHICS_INVALID_TIMELINE_ROW]}] "
                            f"Row #{row_idx} timestamp_ms must be >= 0, got {tms!r}"
                        )
            elif has_ts_sec:
                col_idx = field_map["timestamp_sec"]
                if col_idx < len(row):
                    tsec = row[col_idx]
                    if not isinstance(tsec, (int, float)) or tsec < 0:
                        core_result.add_error(
                            f"[{ERROR_NAMES[E_GRAPHICS_INVALID_TIMELINE_ROW]}] "
                            f"Row #{row_idx} timestamp_sec must be >= 0, got {tsec!r}"
                        )

            # Check seek_progress in range [0.0, 100.0]
            if has_seek:
                col_idx = field_map["seek_progress"]
                if col_idx < len(row):
                    seek = row[col_idx]
                    if not isinstance(seek, (int, float)) or seek < 0.0 or seek > 100.0:
                        core_result.add_error(
                            f"[{ERROR_NAMES[E_GRAPHICS_INVALID_TIMELINE_ROW]}] "
                            f"Row #{row_idx} seek_progress out of bounds [0.0, 1.0], got {seek!r}"
                        )

            # Check rotation_deg is numeric
            if has_rot:
                col_idx = field_map["rotation_deg"]
                if col_idx < len(row):
                    rot = row[col_idx]
                    if not isinstance(rot, (int, float)):
                        core_result.add_error(
                            f"[{ERROR_NAMES[E_GRAPHICS_INVALID_TIMELINE_ROW]}] "
                            f"Row #{row_idx} rotation_deg must be numeric, got {rot!r}"
                        )

            # Check scale_factor > 0
            if has_scale:
                col_idx = field_map["scale_factor"]
                if col_idx < len(row):
                    scale = row[col_idx]
                    if not isinstance(scale, (int, float)) or scale <= 0:
                        core_result.add_error(
                            f"[{ERROR_NAMES[E_GRAPHICS_INVALID_TIMELINE_ROW]}] "
                            f"Row #{row_idx} scale_factor must be > 0, got {scale!r}"
                        )

            # Check opacity in range [0.0, 1.0]
            if has_opacity:
                col_idx = field_map["opacity"]
                if col_idx < len(row):
                    opac = row[col_idx]
                    if not isinstance(opac, (int, float)) or opac < 0.0 or opac > 1.0:
                        core_result.add_error(
                            f"[{ERROR_NAMES[E_GRAPHICS_INVALID_TIMELINE_ROW]}] "
                            f"Row #{row_idx} opacity must be in range [0.0, 1.0], got {opac!r}"
                        )

            # Check SVG markup if populated
            if has_svg:
                col_idx = field_map["svg_markup"]
                if col_idx < len(row):
                    svg_content = row[col_idx]
                    if svg_content:
                        is_valid_svg, svg_err = bejson_graphics_validator_check_svg(svg_content)
                        if not is_valid_svg:
                            core_result.add_error(
                                f"[{ERROR_NAMES[E_GRAPHICS_INVALID_SVG_MARKUP]}] "
                                f"Row #{row_idx} {svg_err}"
                            )

            # Check remove_frame_source boolean in row
            if has_rfs:
                col_idx = field_map["remove_frame_source"]
                if col_idx < len(row):
                    rfs_val = row[col_idx]
                    if not isinstance(rfs_val, bool):
                        core_result.add_error(
                            f"[{ERROR_NAMES[E_GRAPHICS_STAGE_CONFIG_INVALID]}] "
                            f"Row #{row_idx} remove_frame_source must be a boolean, got {type(rfs_val).__name__}"
                        )

            # Check Tri-Color palette conformance on accent_color / bg_theme
            if has_accent:
                col_idx = field_map["accent_color"]
                if col_idx < len(row):
                    c_str = row[col_idx]
                    if c_str and not bejson_graphics_validator_check_palette(c_str):
                        core_result.add_warning(
                            f"[{ERROR_NAMES[E_GRAPHICS_PALETTE_VIOLATION]}] "
                            f"Row #{row_idx} accent_color '{c_str}' deviates from Policy §8.1 Tri-Color Palette"
                        )

            if has_theme:
                col_idx = field_map["bg_theme"]
                if col_idx < len(row):
                    c_str = row[col_idx]
                    if c_str and not bejson_graphics_validator_check_palette(c_str):
                        core_result.add_warning(
                            f"[{ERROR_NAMES[E_GRAPHICS_PALETTE_VIOLATION]}] "
                            f"Row #{row_idx} bg_theme '{c_str}' deviates from Policy §8.1 Tri-Color Palette"
                        )

    return core_result


def bejson_graphics_validator_validate_doc(doc: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validates a graphics document dictionary against both Core and Graphics barriers."""
    res = validate_graphics_barrier(doc, is_file=False)
    return res.valid, res.errors


def bejson_graphics_validator_validate_file(file_path: Union[str, Path]) -> bool:
    """
    Validates a file on disk against both Core and Graphics barriers.
    Raises GraphicsValidationError if validation fails; returns True on success.
    """
    f_path = Path(file_path).resolve()
    if not f_path.exists():
        raise GraphicsValidationError(f"File not found: {f_path}", E_GRAPHICS_BARRIER_OF_ENTRY_FAILED)

    res = validate_graphics_barrier(str(f_path), is_file=True)
    if not res.valid:
        first_err = res.errors[0] if res.errors else "Unknown barrier failure"
        raise GraphicsValidationError(first_err, E_GRAPHICS_BARRIER_OF_ENTRY_FAILED)
    return True


def bejson_graphics_validator_get_report(input_data: Any, is_file: bool = False) -> str:
    """Returns a formatted human-readable validation report."""
    res = validate_graphics_barrier(input_data, is_file=is_file)
    lines = ["======================================================================"]
    lines.append("  GRAPHICS DOMAIN & CORE FAMILY TWO-TIER BARRIER VALIDATION REPORT")
    lines.append("======================================================================")
    lines.append(f"  Target: {res.current_file or '<in-memory object>'}")
    lines.append(f"  Barrier Status: {'PASSED (APPROVED FOR GRAPHICS PIPELINE)' if res.valid else 'FAILED (REJECTED AT BARRIER OF ENTRY)'}")
    if res.errors:
        lines.append(f"  Errors ({len(res.errors)}):")
        for err in res.errors:
            lines.append(f"    - {err}")
    if res.warnings:
        lines.append(f"  Warnings ({len(res.warnings)}):")
        for w in res.warnings:
            lines.append(f"    - {w}")
    lines.append("======================================================================")
    return "\n".join(lines)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Graphics Domain Two-Tier Barrier Validator")
    parser.add_argument("target", help="Path to BEJSON graphics document or MFDB manifest")
    args = parser.parse_args()

    report = bejson_graphics_validator_get_report(args.target, is_file=True)
    print(report)
    sys.exit(0 if "PASSED" in report else 1)
