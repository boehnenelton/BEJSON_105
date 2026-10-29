"""
Library:        lib_bejson_Graphics_graphics_schemas.py
Family:         Graphics
Description:    BEJSON 105a Schema Definitions and Validation for Blank-Slate SVG Canvas Stages,
                Dynamic Frame Playwright Rendering, FPS Timeline Declarations, and Row-Per-Frame Animations.
BEJSON:         BEJSON stands for BOEHNEN ELTON JSON. Authoritative definition;
                do not restate or reinterpret this acronym elsewhere.
MFDB:           MFDB stands for Multi File Database. Authoritative definition;
                do not restate or reinterpret this acronym elsewhere.
Version:        1.0.0
Date:           2026-10-27
Author:         Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
RELATIONAL_ID:  7f1b2c3d-4e5a-4b6c-8d9e-0f1a2b3c4d5e
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
for _fam in ('Core', 'Taxonomies', 'Tax_Scaffolds', 'Canvas', 'Graphics'):
    _p = os.path.normpath(os.path.join(_HERE, "..", _fam))
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

logger = logging.getLogger("lib_bejson_Graphics_graphics_schemas")
VERSION = "1.0.0"

# ---------------------------------------------------------------------------
# Canonical BEJSON 105a Field Definitions with Unique UUIDv4 field_uuid (E90/E91)
# ---------------------------------------------------------------------------

GRAPHIC_CANVAS_CONFIG_FIELDS: List[Dict[str, str]] = [
    {"name": "canvas_id",          "type": "string",  "field_uuid": "9a1b2c3d-1111-4000-8000-000000000001"},
    {"name": "template_name",      "type": "string",  "field_uuid": "9a1b2c3d-1111-4000-8000-000000000002"},
    {"name": "stage_selector",     "type": "string",  "field_uuid": "9a1b2c3d-1111-4000-8000-000000000003"},
    {"name": "width_px",           "type": "integer", "field_uuid": "9a1b2c3d-1111-4000-8000-000000000004"},
    {"name": "height_px",          "type": "integer", "field_uuid": "9a1b2c3d-1111-4000-8000-000000000005"},
    {"name": "aspect_ratio",       "type": "string",  "field_uuid": "9a1b2c3d-1111-4000-8000-000000000006"},
    {"name": "bg_theme",           "type": "string",  "field_uuid": "9a1b2c3d-1111-4000-8000-000000000007"},
    {"name": "accent_color",       "type": "string",  "field_uuid": "9a1b2c3d-1111-4000-8000-000000000008"},
    {"name": "device_scale",       "type": "integer", "field_uuid": "9a1b2c3d-1111-4000-8000-000000000009"},
    {"name": "output_dir",         "type": "string",  "field_uuid": "9a1b2c3d-1111-4000-8000-000000000010"},
    {"name": "text_overlays_json", "type": "string",  "field_uuid": "9a1b2c3d-1111-4000-8000-000000000011"}
]

GRAPHIC_ROW_FRAME_FIELDS: List[Dict[str, str]] = [
    {"name": "frame_index",      "type": "integer", "field_uuid": "9b2c3d4e-2222-4000-8000-000000000001"},
    {"name": "timestamp_sec",    "type": "number",  "field_uuid": "9b2c3d4e-2222-4000-8000-000000000002"},
    {"name": "seek_progress",    "type": "number",  "field_uuid": "9b2c3d4e-2222-4000-8000-000000000003"},
    {"name": "fps",              "type": "integer", "field_uuid": "9b2c3d4e-2222-4000-8000-000000000004"},
    {"name": "frame_filename",   "type": "string",  "field_uuid": "9b2c3d4e-2222-4000-8000-000000000005"},
    {"name": "svg_markup",       "type": "string",  "field_uuid": "9b2c3d4e-2222-4000-8000-000000000006"},
    {"name": "frame_data_json",  "type": "string",  "field_uuid": "9b2c3d4e-2222-4000-8000-000000000007"},
    {"name": "is_rendered",      "type": "boolean", "field_uuid": "9b2c3d4e-2222-4000-8000-000000000008"},
    {"name": "checksum_sha256",  "type": "string",  "field_uuid": "9b2c3d4e-2222-4000-8000-000000000009"}
]

GRAPHIC_TEMPLATE_REGISTRY_FIELDS: List[Dict[str, str]] = [
    {"name": "template_id",      "type": "string",  "field_uuid": "9c3d4e5f-3333-4000-8000-000000000001"},
    {"name": "template_name",    "type": "string",  "field_uuid": "9c3d4e5f-3333-4000-8000-000000000002"},
    {"name": "category",         "type": "string",  "field_uuid": "9c3d4e5f-3333-4000-8000-000000000003"},
    {"name": "width_px",         "type": "integer", "field_uuid": "9c3d4e5f-3333-4000-8000-000000000004"},
    {"name": "height_px",        "type": "integer", "field_uuid": "9c3d4e5f-3333-4000-8000-000000000005"},
    {"name": "aspect_ratio",     "type": "string",  "field_uuid": "9c3d4e5f-3333-4000-8000-000000000006"},
    {"name": "stage_selector",   "type": "string",  "field_uuid": "9c3d4e5f-3333-4000-8000-000000000007"},
    {"name": "description",      "type": "string",  "field_uuid": "9c3d4e5f-3333-4000-8000-000000000008"},
    {"name": "html_template",    "type": "string",  "field_uuid": "9c3d4e5f-3333-4000-8000-000000000009"},
    {"name": "checksum_sha256",  "type": "string",  "field_uuid": "9c3d4e5f-3333-4000-8000-000000000010"}
]


# ---------------------------------------------------------------------------
# O(1) Field Map Compiler (Format 105a: index 0 is reserved for record_uuid)
# ---------------------------------------------------------------------------

def build_field_map_105(fields: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Compiles an O(1) field map for a BEJSON 105a table.
    In Format 105a, row[0] is strictly the record_uuid.
    The named fields start at row offset 1.
    """
    field_map: Dict[str, int] = {}
    for col_idx, field_def in enumerate(fields):
        field_map[field_def["name"]] = col_idx + 1
    return field_map


# ---------------------------------------------------------------------------
# Coordinate-Based Text Overlay Helper
# ---------------------------------------------------------------------------

def create_coordinate_text_overlay(
    x: Any,
    y: Any,
    text: str,
    font_size: int = 20,
    font_family: str = "monospace",
    font_weight: str = "bold",
    color: str = "#FFFFFF",
    bg_color: Optional[str] = "rgba(0, 0, 0, 0.75)",
    padding: str = "4px 10px",
    border_radius: str = "4px",
    align: str = "left",
    opacity: float = 1.0,
    z_index: int = 100
) -> Dict[str, Any]:
    """
    Creates an X,Y coordinate-based text overlay specification
    ready for embedding in active canvas schema configurations.
    x and y can be integer pixel offsets or percentage strings (e.g. 50, '50%').
    """
    return {
        "x": x,
        "y": y,
        "text": text,
        "font_size": int(font_size),
        "font_family": font_family,
        "font_weight": font_weight,
        "color": color,
        "bg_color": bg_color,
        "padding": padding,
        "border_radius": border_radius,
        "align": align,
        "opacity": float(opacity),
        "z_index": int(z_index)
    }


# ---------------------------------------------------------------------------
# Schema Builder Functions
# ---------------------------------------------------------------------------

def create_graphic_stage_config_105a(
    canvas_id: str = "stage_blank_01",
    template_name: str = "blank_slate_stage.html",
    stage_selector: str = "#capture-stage",
    width_px: int = 800,
    height_px: int = 800,
    aspect_ratio: str = "1:1",
    bg_theme: str = "#000000",
    accent_color: str = "#DE2626",
    device_scale: int = 2,
    output_dir: str = "captures/stage",
    text_overlays: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """Instantiates a valid BEJSON 105a Graphic Canvas Stage Configuration document with coordinate text overlays."""
    record_uuid = str(uuid.uuid4())
    overlays_json = json.dumps(text_overlays) if text_overlays else "[]"
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
        int(device_scale),
        output_dir,
        overlays_json
    ]

    return {
        "Format": "BEJSON",
        "Format_Version": "105a",
        "Format_Creator": "Elton Boehnen",
        "Records_Type": ["GraphicCanvasConfig"],
        "Fields": [dict(f) for f in GRAPHIC_CANVAS_CONFIG_FIELDS],
        "Values": [values_row]
    }


def create_row_per_frame_animation_105a(
    animation_name: str,
    duration_sec: float,
    fps: int,
    width_px: int = 800,
    height_px: int = 800,
    aspect_ratio: str = "1:1",
    canvas_id: str = "canvas_anim_01",
    template_name: str = "blank_slate_stage.html",
    dynamic_frames: Optional[List[Dict[str, Any]]] = None,
    output_prefix: str = "frame_"
) -> Dict[str, Any]:
    """
    Generates a valid BEJSON 105a Row-Per-Frame Animation document where EACH ROW
    declares a single frame of the animation with its timestamp, seek progress,
    dynamic SVG markup or parameters, and render completion status.
    """
    total_frames = max(1, int(math.ceil(duration_sec * fps)))
    time_step_sec = duration_sec / max(1, (total_frames - 1)) if total_frames > 1 else 0.0

    values_rows: List[List[Any]] = []

    for idx in range(total_frames):
        rec_uuid = str(uuid.uuid4())
        ts = round(idx * time_step_sec, 6)
        progress = round(idx / max(1, (total_frames - 1)), 6) if total_frames > 1 else 0.0
        frame_filename = f"{output_prefix}{idx:04d}.png"

        # Check for dynamic frame content override
        svg_markup = ""
        frame_data_json = "{}"
        if dynamic_frames and idx < len(dynamic_frames):
            frame_item = dynamic_frames[idx]
            svg_markup = frame_item.get("svg_markup", "")
            data_dict = frame_item.get("data", {})
            if data_dict:
                frame_data_json = json.dumps(data_dict)

        row = [
            rec_uuid,
            idx,
            ts,
            progress,
            int(fps),
            frame_filename,
            svg_markup,
            frame_data_json,
            False,   # is_rendered
            ""       # checksum_sha256
        ]
        values_rows.append(row)

    doc: Dict[str, Any] = {
        "Format": "BEJSON",
        "Format_Version": "105a",
        "Format_Creator": "Elton Boehnen",
        "Animation_Name": animation_name,
        "Duration_Sec": float(duration_sec),
        "FPS": int(fps),
        "Total_Frames": int(total_frames),
        "Width_Px": int(width_px),
        "Height_Px": int(height_px),
        "Aspect_Ratio": aspect_ratio,
        "Canvas_Id": canvas_id,
        "Template_Name": template_name,
        "Records_Type": ["GraphicFrameRecord"],
        "Fields": [dict(f) for f in GRAPHIC_ROW_FRAME_FIELDS],
        "Values": values_rows
    }
    return doc


def create_slideshow_animation_105a(
    slideshow_name: str,
    slides: List[Dict[str, Any]],
    default_slide_duration_sec: float = 3.0,
    transition_sec: float = 0.5,
    fps: int = 24,
    width_px: int = 800,
    height_px: int = 800,
    aspect_ratio: str = "1:1",
    canvas_id: str = "canvas_slideshow_01",
    template_name: str = "blank_slate_stage.html",
    output_prefix: str = "slide_frame_"
) -> Dict[str, Any]:
    """
    Constructs a BEJSON 105a Row-Per-Frame Slideshow Animation document.
    Sequences arbitrary image paths, SVG slides, or text panels across a timeline,
    allocating frames with hold states and cross-fade/dissolve transition interpolations.
    """
    total_duration = 0.0
    slide_specs: List[Dict[str, Any]] = []

    for s_idx, slide in enumerate(slides):
        dur = float(slide.get("duration_sec", default_slide_duration_sec))
        slide_specs.append({
            "slide_index": s_idx,
            "svg_markup": slide.get("svg_markup", ""),
            "image_path": slide.get("image_path", ""),
            "caption": slide.get("caption", f"Slide {s_idx + 1}"),
            "duration_sec": dur,
            "start_time": total_duration,
            "end_time": total_duration + dur
        })
        total_duration += dur

    total_frames = max(1, int(math.ceil(total_duration * fps)))
    time_step_sec = total_duration / max(1, (total_frames - 1)) if total_frames > 1 else 0.0

    values_rows: List[List[Any]] = []

    for f_idx in range(total_frames):
        rec_uuid = str(uuid.uuid4())
        ts = round(f_idx * time_step_sec, 6)
        progress = round(f_idx / max(1, (total_frames - 1)), 6) if total_frames > 1 else 0.0
        frame_filename = f"{output_prefix}{f_idx:04d}.png"

        # Determine active slide and transition state
        active_slide = slide_specs[-1]
        for spec in slide_specs:
            if spec["start_time"] <= ts <= spec["end_time"]:
                active_slide = spec
                break

        # Calculate opacity / crossfade if within transition window
        time_into_slide = ts - active_slide["start_time"]
        opacity = 1.0
        if transition_sec > 0 and time_into_slide < transition_sec:
            opacity = min(1.0, max(0.0, time_into_slide / transition_sec))

        frame_data = {
            "slide_index": active_slide["slide_index"],
            "caption": active_slide["caption"],
            "opacity": round(opacity, 3),
            "image_path": active_slide["image_path"]
        }

        row = [
            rec_uuid,
            f_idx,
            ts,
            progress,
            int(fps),
            frame_filename,
            active_slide["svg_markup"],
            json.dumps(frame_data),
            False,   # is_rendered
            ""       # checksum_sha256
        ]
        values_rows.append(row)

    return {
        "Format": "BEJSON",
        "Format_Version": "105a",
        "Format_Creator": "Elton Boehnen",
        "Animation_Name": slideshow_name,
        "Animation_Type": "Slideshow",
        "Total_Slides": len(slides),
        "Duration_Sec": float(total_duration),
        "FPS": int(fps),
        "Total_Frames": int(total_frames),
        "Width_Px": int(width_px),
        "Height_Px": int(height_px),
        "Aspect_Ratio": aspect_ratio,
        "Canvas_Id": canvas_id,
        "Template_Name": template_name,
        "Records_Type": ["GraphicFrameRecord"],
        "Fields": [dict(f) for f in GRAPHIC_ROW_FRAME_FIELDS],
        "Values": values_rows
    }



def validate_graphic_105a_doc(doc: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validates a BEJSON 105a document for strict structural conformance,
    E90-E95 UUID integrity, and field count alignment.
    """
    errors: List[str] = []

    if doc.get("Format") != "BEJSON":
        errors.append(f"Format mismatch: expected 'BEJSON', got '{doc.get('Format')}'")

    if doc.get("Format_Version") not in ("105", "105a", "105db"):
        errors.append(f"Version mismatch: expected 105-series, got '{doc.get('Format_Version')}'")

    fields = doc.get("Fields", [])
    if not isinstance(fields, list) or len(fields) == 0:
        errors.append("Fields array is missing or empty")

    # E90/E91: Check field_uuid on all fields
    seen_field_uuids = set()
    for col_idx, f in enumerate(fields):
        fid = f.get("field_uuid")
        if not fid:
            errors.append(f"Field #{col_idx} '{f.get('name')}' is missing mandatory 'field_uuid' (E90)")
        elif fid in seen_field_uuids:
            errors.append(f"Duplicate field_uuid '{fid}' detected at field #{col_idx} (E91)")
        else:
            seen_field_uuids.add(fid)

    expected_row_len = len(fields) + 1  # record_uuid + fields
    values = doc.get("Values", [])
    if not isinstance(values, list):
        errors.append("Values is not a list")
    else:
        seen_record_uuids = set()
        for row_idx, row in enumerate(values):
            if not isinstance(row, list):
                errors.append(f"Row #{row_idx} is not an array")
                continue
            if len(row) != expected_row_len:
                errors.append(f"Row #{row_idx} has {len(row)} elements; expected {expected_row_len}")
            # Check row[0] record_uuid
            ruuid = row[0]
            if not isinstance(ruuid, str) or len(ruuid) < 16:
                errors.append(f"Row #{row_idx} missing valid record_uuid at offset 0 (E92)")
            elif ruuid in seen_record_uuids:
                errors.append(f"Row #{row_idx} duplicate record_uuid '{ruuid}' (E93)")
            else:
                seen_record_uuids.add(ruuid)

    return len(errors) == 0, errors
