"""
Library:        lib_bejson_Canvas_canvas_schemas.py
Family:         Canvas
Description:    BEJSON 105a Schema Definitions and Validation for SVG Canvas Templates,
                Animation Framerates, Dimensions, and Playwright Capture Pipelines.
BEJSON:         BEJSON stands for BOEHNEN ELTON JSON. Authoritative definition;
                do not restate or reinterpret this acronym elsewhere.
MFDB:           MFDB stands for Multi File Database. Authoritative definition;
                do not restate or reinterpret this acronym elsewhere.
Version:        1.0.0
Date:           2026-10-25
Author:         Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
RELATIONAL_ID:  4d7b8e1a-9f2c-4e3a-b851-7c9d0e1f2a3b
Release_Version: 300
"""

from __future__ import annotations

import json
import logging
import math
import os
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
for _fam in ('Core', 'Taxonomies', 'Tax_Scaffolds', 'Canvas'):
    _p = os.path.normpath(os.path.join(_HERE, "..", _fam))
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from lib_bejson_Core_bejson_core import (
        bejson_core_atomic_write,
        bejson_core_get_field_map,
        bejson_core_load_file,
    )
except ImportError:
    bejson_core_atomic_write = None
    bejson_core_get_field_map = None
    bejson_core_load_file = None

logger = logging.getLogger("lib_bejson_Canvas_canvas_schemas")
VERSION = "1.0.0"

# ---------------------------------------------------------------------------
# Canonical BEJSON 105a Field Definitions
# ---------------------------------------------------------------------------

CANVAS_STUDIO_CONFIG_FIELDS: List[Dict[str, str]] = [
    {"name": "canvas_id",         "type": "string",  "field_uuid": "7a1b2c3d-1111-4000-8000-000000000001"},
    {"name": "template_name",     "type": "string",  "field_uuid": "7a1b2c3d-1111-4000-8000-000000000002"},
    {"name": "stage_selector",    "type": "string",  "field_uuid": "7a1b2c3d-1111-4000-8000-000000000003"},
    {"name": "width_px",          "type": "integer", "field_uuid": "7a1b2c3d-1111-4000-8000-000000000004"},
    {"name": "height_px",         "type": "integer", "field_uuid": "7a1b2c3d-1111-4000-8000-000000000005"},
    {"name": "aspect_ratio",      "type": "string",  "field_uuid": "7a1b2c3d-1111-4000-8000-000000000006"},
    {"name": "bg_theme",          "type": "string",  "field_uuid": "7a1b2c3d-1111-4000-8000-000000000007"},
    {"name": "accent_color",      "type": "string",  "field_uuid": "7a1b2c3d-1111-4000-8000-000000000008"},
    {"name": "animation_name",    "type": "string",  "field_uuid": "7a1b2c3d-1111-4000-8000-000000000009"},
    {"name": "duration_sec",      "type": "number",  "field_uuid": "7a1b2c3d-1111-4000-8000-000000000010"},
    {"name": "fps",               "type": "integer", "field_uuid": "7a1b2c3d-1111-4000-8000-000000000011"},
    {"name": "total_frames",      "type": "integer", "field_uuid": "7a1b2c3d-1111-4000-8000-000000000012"},
    {"name": "device_scale",      "type": "integer", "field_uuid": "7a1b2c3d-1111-4000-8000-000000000013"},
    {"name": "export_format",     "type": "string",  "field_uuid": "7a1b2c3d-1111-4000-8000-000000000014"},
    {"name": "output_path",       "type": "string",  "field_uuid": "7a1b2c3d-1111-4000-8000-000000000015"},
    {"name": "svg_source_mode",   "type": "string",  "field_uuid": "7a1b2c3d-1111-4000-8000-000000000016"},
    {"name": "svg_inline_markup", "type": "string",  "field_uuid": "7a1b2c3d-1111-4000-8000-000000000017"}
]

CANVAS_FRAME_SEQUENCE_FIELDS: List[Dict[str, str]] = [
    {"name": "frame_index",      "type": "integer", "field_uuid": "8b2c3d4e-2222-4000-8000-000000000001"},
    {"name": "seek_progress",    "type": "number",  "field_uuid": "8b2c3d4e-2222-4000-8000-000000000002"},
    {"name": "timestamp_sec",    "type": "number",  "field_uuid": "8b2c3d4e-2222-4000-8000-000000000003"},
    {"name": "frame_filename",   "type": "string",  "field_uuid": "8b2c3d4e-2222-4000-8000-000000000004"},
    {"name": "is_rendered_flag", "type": "boolean", "field_uuid": "8b2c3d4e-2222-4000-8000-000000000005"},
    {"name": "checksum_sha256",  "type": "string",  "field_uuid": "8b2c3d4e-2222-4000-8000-000000000006"}
]

# ---------------------------------------------------------------------------
# Schema Builder Functions
# ---------------------------------------------------------------------------

def build_field_map_105(fields: List[Dict[str, Any]]) -> Dict[str, int]:
    """Compiles an O(1) field map for a 105a table where index 0 is record_uuid."""
    field_map: Dict[str, int] = {}
    for col_idx, field_def in enumerate(fields):
        # In Format 105a, row[0] is record_uuid, so field offsets are col_idx + 1
        field_map[field_def["name"]] = col_idx + 1
    return field_map

def create_canvas_config_105a(
    canvas_id: str = "canvas_stage_01",
    template_name: str = "template_square_800x800.html",
    stage_selector: str = "#capture-stage",
    width_px: int = 800,
    height_px: int = 800,
    aspect_ratio: str = "1:1",
    bg_theme: str = "#000000",
    accent_color: str = "#DE2626",
    animation_name: str = "pulseCore",
    duration_sec: float = 8.0,
    fps: int = 60,
    total_frames: Optional[int] = None,
    device_scale: int = 2,
    export_format: str = "png",
    output_path: str = "captures/stage_frame.png",
    svg_source_mode: str = "template_default",
    svg_inline_markup: str = ""
) -> Dict[str, Any]:
    """Instantiates a valid BEJSON 105a Canvas Studio configuration document."""
    if total_frames is None:
        total_frames = max(1, int(math.ceil(duration_sec * fps)))

    record_uuid = str(uuid.uuid4())
    values_row = [
        record_uuid,
        canvas_id,
        template_name,
        stage_selector,
        int(width_px),
        int(height_px),
        aspect_ratio,
        bg_theme,
        accent_color,
        animation_name,
        float(duration_sec),
        int(fps),
        int(total_frames),
        int(device_scale),
        export_format,
        output_path,
        svg_source_mode,
        svg_inline_markup
    ]

    doc: Dict[str, Any] = {
        "Format": "BEJSON",
        "Format_Version": "105a",
        "Format_Creator": "Elton Boehnen",
        "Records_Type": ["CanvasStudioConfig"],
        "Fields": [dict(f) for f in CANVAS_STUDIO_CONFIG_FIELDS],
        "Values": [values_row]
    }
    return doc

def create_frame_sequence_105a(
    duration_sec: float,
    fps: int,
    total_frames: Optional[int] = None,
    output_dir: str = "captures/frames",
    prefix: str = "frame_"
) -> Dict[str, Any]:
    """Generates a BEJSON 105a frame sequence breakdown for deterministic timeline seeking."""
    if total_frames is None or total_frames <= 0:
        total_frames = max(1, int(math.ceil(duration_sec * fps)))

    time_step_sec = duration_sec / max(1, (total_frames - 1)) if total_frames > 1 else 0.0

    values_rows: List[List[Any]] = []
    for frame_idx in range(total_frames):
        seek_progress = (frame_idx / (total_frames - 1)) if total_frames > 1 else 0.0
        timestamp_sec = frame_idx * time_step_sec
        filename = f"{prefix}{frame_idx:04d}.png"
        row = [
            str(uuid.uuid4()),
            frame_idx,
            round(seek_progress, 6),
            round(timestamp_sec, 4),
            os.path.join(output_dir, filename),
            False,
            ""
        ]
        values_rows.append(row)

    doc: Dict[str, Any] = {
        "Format": "BEJSON",
        "Format_Version": "105a",
        "Format_Creator": "Elton Boehnen",
        "Records_Type": ["CanvasFrameSequence"],
        "Fields": [dict(f) for f in CANVAS_FRAME_SEQUENCE_FIELDS],
        "Values": values_rows
    }
    return doc

def compute_frame_seek_points(
    duration_sec: float,
    fps: int,
    frames_count: Optional[int] = None
) -> List[Tuple[int, float, float]]:
    """Calculates list of (frame_index, seek_progress_ratio [0.0..1.0], timestamp_sec)."""
    if frames_count is None or frames_count <= 0:
        frames_count = max(1, int(math.ceil(duration_sec * fps)))

    step_ratio = (1.0 / (frames_count - 1)) if frames_count > 1 else 0.0
    time_step = (duration_sec / (frames_count - 1)) if frames_count > 1 else 0.0

    seek_points: List[Tuple[int, float, float]] = []
    for i in range(frames_count):
        ratio = min(1.0, max(0.0, i * step_ratio))
        timestamp = min(duration_sec, i * time_step)
        seek_points.append((i, round(ratio, 6), round(timestamp, 4)))
    return seek_points

def validate_canvas_config(doc: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Strictly validates a BEJSON 105a Canvas Studio config document."""
    errors: List[str] = []
    if not isinstance(doc, dict):
        return False, ["Root is not a valid dictionary"]

    if doc.get("Format") != "BEJSON":
        errors.append("Format must be 'BEJSON'")
    if doc.get("Format_Version") not in ("105", "105a"):
        errors.append("Format_Version must be '105' or '105a'")

    fields = doc.get("Fields")
    if not isinstance(fields, list) or len(fields) < len(CANVAS_STUDIO_CONFIG_FIELDS):
        errors.append("Missing required Fields definitions")
    else:
        field_names = {f.get("name") for f in fields if isinstance(f, dict)}
        for req_field in CANVAS_STUDIO_CONFIG_FIELDS:
            if req_field["name"] not in field_names:
                errors.append(f"Required field '{req_field['name']}' not found in Fields")

    values = doc.get("Values")
    if not isinstance(values, list) or len(values) == 0:
        errors.append("Values table must contain at least one row")
    else:
        for r_idx, row in enumerate(values):
            if not isinstance(row, list):
                errors.append(f"Row {r_idx} is not an array")
                continue
            # Format 105a requires record_uuid at row[0]
            if len(row) < len(CANVAS_STUDIO_CONFIG_FIELDS) + 1:
                errors.append(f"Row {r_idx} does not have enough columns for 105a (expected >= {len(CANVAS_STUDIO_CONFIG_FIELDS) + 1})")

    return len(errors) == 0, errors

def get_config_dict(doc: Dict[str, Any], row_idx: int = 0) -> Dict[str, Any]:
    """Extracts a row from a 105a Canvas config into a clean dictionary using the field map."""
    values = doc.get("Values", [])
    if row_idx >= len(values):
        raise IndexError(f"Row index {row_idx} out of range ({len(values)} rows)")

    row = values[row_idx]
    field_map = build_field_map_105(doc.get("Fields", []))

    result: Dict[str, Any] = {"record_uuid": row[0]}
    for f_name, col_idx in field_map.items():
        if col_idx < len(row):
            result[f_name] = row[col_idx]
    return result
