"""
Library:        lib_bejson_Graphics_graphics_schemas.py
Family:         Graphics
Description:    BEJSON 105a Schema Definitions and Validation for Blank-Slate SVG Canvas Stages,
                Dynamic Frame Playwright Rendering, FPS Timeline Declarations, and Row-Per-Frame Animations.
BEJSON:         BEJSON stands for BOEHNEN ELTON JSON. Authoritative definition;
                do not restate or reinterpret this acronym elsewhere.
MFDB:           MFDB stands for Multi File Database. Authoritative definition;
                do not restate or reinterpret this acronym elsewhere.
Version:        1.1.0
Date:           2026-10-30
Changelog:
  1.0.1 - 2026-10-30: Records_Type key fix (was Record_Type).
Author:         Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
RELATIONAL_ID:  320bf1ac-89f0-4109-919b-0a9a1b1c34ce
Release_Version: 300
"""

from __future__ import annotations

import hashlib
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
VERSION = "1.1.0"

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
    {"name": "output_dir",          "type": "string",  "field_uuid": "9a1b2c3d-1111-4000-8000-000000000010"},
    {"name": "text_overlays_json",  "type": "string",  "field_uuid": "9a1b2c3d-1111-4000-8000-000000000011"},
    {"name": "remove_frame_source", "type": "boolean", "field_uuid": "9a1b2c3d-1111-4000-8000-000000000012"}
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

GRAPHIC_ANIMATION_TIMELINE_FIELDS: List[Dict[str, str]] = [
    {"name": "frame_index",       "type": "integer", "field_uuid": "9d4e5f6a-4444-4000-8000-000000000001"},
    {"name": "timestamp_ms",      "type": "number",  "field_uuid": "9d4e5f6a-4444-4000-8000-000000000002"},
    {"name": "frame_duration_ms", "type": "number",  "field_uuid": "9d4e5f6a-4444-4000-8000-000000000003"},
    {"name": "fps",               "type": "integer", "field_uuid": "9d4e5f6a-4444-4000-8000-000000000004"},
    {"name": "seek_progress",     "type": "number",  "field_uuid": "9d4e5f6a-4444-4000-8000-000000000005"},
    {"name": "rotation_deg",      "type": "number",  "field_uuid": "9d4e5f6a-4444-4000-8000-000000000006"},
    {"name": "scale_factor",      "type": "number",  "field_uuid": "9d4e5f6a-4444-4000-8000-000000000007"},
    {"name": "opacity",           "type": "number",  "field_uuid": "9d4e5f6a-4444-4000-8000-000000000008"},
    {"name": "svg_markup",        "type": "string",  "field_uuid": "9d4e5f6a-4444-4000-8000-000000000009"},
    {"name": "frame_filename",    "type": "string",  "field_uuid": "9d4e5f6a-4444-4000-8000-000000000010"},
    {"name": "is_rendered",       "type": "boolean", "field_uuid": "9d4e5f6a-4444-4000-8000-000000000011"},
    {"name": "checksum_sha256",   "type": "string",  "field_uuid": "9d4e5f6a-4444-4000-8000-000000000012"}
]

GRAPHIC_SLIDE_FIELDS: List[Dict[str, str]] = [
    {"name": "slide_index",         "type": "integer", "field_uuid": "9f6a7b8c-6666-4000-8000-000000000001"},
    {"name": "slide_type",          "type": "string",  "field_uuid": "9f6a7b8c-6666-4000-8000-000000000002"},
    {"name": "title",               "type": "string",  "field_uuid": "9f6a7b8c-6666-4000-8000-000000000003"},
    {"name": "subtitle",            "type": "string",  "field_uuid": "9f6a7b8c-6666-4000-8000-000000000004"},
    {"name": "duration_sec",        "type": "number",  "field_uuid": "9f6a7b8c-6666-4000-8000-000000000005"},
    {"name": "timestamp_sec",       "type": "number",  "field_uuid": "9f6a7b8c-6666-4000-8000-000000000006"},
    {"name": "width_px",            "type": "integer", "field_uuid": "9f6a7b8c-6666-4000-8000-000000000007"},
    {"name": "height_px",           "type": "integer", "field_uuid": "9f6a7b8c-6666-4000-8000-000000000008"},
    {"name": "svg_markup",          "type": "string",  "field_uuid": "9f6a7b8c-6666-4000-8000-000000000009"},
    {"name": "slide_filename",      "type": "string",  "field_uuid": "9f6a7b8c-6666-4000-8000-000000000010"},
    {"name": "is_rendered",         "type": "boolean", "field_uuid": "9f6a7b8c-6666-4000-8000-000000000011"},
    {"name": "checksum_sha256",     "type": "string",  "field_uuid": "9f6a7b8c-6666-4000-8000-000000000012"},
    {"name": "remove_frame_source", "type": "boolean", "field_uuid": "9f6a7b8c-6666-4000-8000-000000000013"}
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

def build_field_map_105(fields: Any) -> Dict[str, int]:
    """
    Compiles an O(1) field map for a BEJSON 105a table or document.
    In Format 105a, row[0] is strictly the record_uuid.
    The named fields start at row offset 1.
    If a full document is provided, format version is detected automatically.
    """
    if isinstance(fields, dict) and "Fields" in fields:
        fmt_ver = str(fields.get("Format_Version", "105"))
        field_defs = fields["Fields"]
        is_105 = fmt_ver.startswith("105")
        offset = 1 if is_105 else 0
        field_map: Dict[str, int] = {}
        if is_105:
            field_map["record_uuid"] = 0
        for col_idx, field_def in enumerate(field_defs):
            field_map[field_def["name"]] = col_idx + offset
        return field_map

    field_map_result: Dict[str, int] = {"record_uuid": 0}
    for col_idx, field_def in enumerate(fields if isinstance(fields, list) else []):
        field_map_result[field_def["name"]] = col_idx + 1
    return field_map_result


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
    text_overlays: Optional[List[Dict[str, Any]]] = None,
    remove_frame_source: bool = False,
    parent_hierarchy: Optional[str] = None
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
        overlays_json,
        bool(remove_frame_source)
    ]

    doc: Dict[str, Any] = {
        "Format": "BEJSON",
        "Format_Version": "105a",
        "Format_Creator": "Elton Boehnen",
        "Remove_Frame_Source": bool(remove_frame_source),
        "Records_Type": ["GraphicCanvasConfig"],
        "Fields": [dict(f) for f in GRAPHIC_CANVAS_CONFIG_FIELDS],
        "Values": [values_row]
    }
    if parent_hierarchy:
        doc["Parent_Hierarchy"] = parent_hierarchy
    return doc


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
    output_prefix: str = "frame_",
    remove_frame_source: bool = False,
    parent_hierarchy: Optional[str] = None
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
        "Remove_Frame_Source": bool(remove_frame_source),
        "Records_Type": ["GraphicFrameRecord"],
        "Fields": [dict(f) for f in GRAPHIC_ROW_FRAME_FIELDS],
        "Values": values_rows
    }
    if parent_hierarchy:
        doc["Parent_Hierarchy"] = parent_hierarchy
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


def create_branding_slide_deck_105a(
    deck_name: str,
    slides: List[Dict[str, Any]],
    default_duration_sec: float = 3.0,
    width_px: int = 1280,
    height_px: int = 720,
    aspect_ratio: str = "16:9",
    remove_frame_source: bool = False,
    is_entity_table: bool = False,
    parent_hierarchy: Optional[str] = None
) -> Dict[str, Any]:
    """
    Constructs a BEJSON 105a or 105 slide deck document representing a sequenced presentation.
    If is_entity_table is True, emits Format 105 entity table without custom headers (for MFDB linking).
    If is_entity_table is False, emits Format 105a document with deck metadata headers.
    """
    total_duration = 0.0
    values_rows = []
    f_map = {f["name"]: i + 1 for i, f in enumerate(GRAPHIC_SLIDE_FIELDS)}

    for s_idx, slide in enumerate(slides):
        dur = float(slide.get("duration_sec", default_duration_sec))
        s_type = slide.get("slide_type", "branding_slide")
        title = slide.get("title", f"Slide {s_idx + 1}")
        subtitle = slide.get("subtitle", "")
        svg = slide.get("svg_markup", "")
        fn = slide.get("slide_filename", f"slide_{s_idx:02d}_{s_type}.svg")
        c_hash = slide.get("checksum_sha256") or (hashlib.sha256(svg.encode("utf-8")).hexdigest() if svg else "")
        rec_uuid = str(uuid.uuid4())

        row = [None] * (len(GRAPHIC_SLIDE_FIELDS) + 1)
        row[0] = rec_uuid
        row[f_map["slide_index"]] = s_idx
        row[f_map["slide_type"]] = s_type
        row[f_map["title"]] = title
        row[f_map["subtitle"]] = subtitle
        row[f_map["duration_sec"]] = dur
        row[f_map["timestamp_sec"]] = round(total_duration, 3)
        row[f_map["width_px"]] = int(width_px)
        row[f_map["height_px"]] = int(height_px)
        row[f_map["svg_markup"]] = svg
        row[f_map["slide_filename"]] = fn
        row[f_map["is_rendered"]] = bool(slide.get("is_rendered", False))
        row[f_map["checksum_sha256"]] = c_hash
        row[f_map["remove_frame_source"]] = bool(remove_frame_source)
        values_rows.append(row)
        total_duration += dur

    if is_entity_table:
        # Standard Format 105 Entity Table (Custom keys forbidden per Policy §4.6 & MFDB v1.40)
        doc: Dict[str, Any] = {
            "Format": "BEJSON",
            "Format_Version": "105",
            "Format_Creator": "Elton Boehnen",
            "Records_Type": [deck_name],
            "Fields": [dict(f) for f in GRAPHIC_SLIDE_FIELDS],
            "Values": values_rows
        }
        if parent_hierarchy:
            doc["Parent_Hierarchy"] = parent_hierarchy
        return doc

    # Standalone Format 105a Slide Deck (Custom headers allowed)
    doc_105a: Dict[str, Any] = {
        "Format": "BEJSON",
        "Format_Version": "105a",
        "Format_Creator": "Elton Boehnen",
        "Deck_Name": deck_name,
        "Total_Slides": len(slides),
        "Total_Duration_Sec": round(total_duration, 3),
        "Width_Px": int(width_px),
        "Height_Px": int(height_px),
        "Aspect_Ratio": aspect_ratio,
        "Remove_Frame_Source": bool(remove_frame_source),
        "Records_Type": ["GraphicSlideRecord"],
        "Fields": [dict(f) for f in GRAPHIC_SLIDE_FIELDS],
        "Values": values_rows
    }
    if parent_hierarchy:
        doc_105a["Parent_Hierarchy"] = parent_hierarchy
    return doc_105a


def compute_frame_timeline_105a(
    total_frames: int = 24,
    target_fps: int = 24,
    total_duration_ms: Optional[int] = None,
    fps: Optional[int] = None,
    duration_sec: Optional[float] = None
) -> List[Dict[str, Any]]:
    """Calculates exact timestamps, frame durations, and seek progress."""
    effective_fps = fps if fps is not None else target_fps
    if duration_sec is not None and total_duration_ms is None:
        total_duration_ms = int(round(duration_sec * 1000.0))
    elif total_duration_ms is None:
        total_duration_ms = int(round((total_frames / float(effective_fps)) * 1000.0))
    duration_per_frame_ms = total_duration_ms / float(total_frames)
    timeline_records = []
    for frame_idx in range(total_frames):
        timestamp_ms = frame_idx * duration_per_frame_ms
        seek_progress = frame_idx / float(max(1, total_frames))
        rotation_deg = frame_idx * (360.0 / float(total_frames))
        timeline_records.append({
            "frame_index": frame_idx,
            "timestamp_ms": round(timestamp_ms, 2),
            "frame_duration_ms": round(duration_per_frame_ms, 2),
            "fps": effective_fps,
            "seek_progress": round(seek_progress, 4),
            "rotation_deg": round(rotation_deg, 2),
            "scale_factor": 1.0,
            "opacity": 1.0,
            "svg_markup": "",
            "frame_filename": f"frame_{frame_idx:04d}.png",
            "is_rendered": False,
            "checksum_sha256": ""
        })
    return timeline_records


def create_svg_animation_timeline_105a(
    animation_name: str,
    total_frames: int = 24,
    fps: int = 24,
    width_px: int = 400,
    height_px: int = 400,
    aspect_ratio: str = "1:1",
    dynamic_frames: Optional[List[Dict[str, Any]]] = None,
    output_prefix: str = "frame_",
    remove_frame_source: bool = False,
    parent_hierarchy: Optional[str] = None
) -> Dict[str, Any]:
    """Constructs a BEJSON 105a SVG Animation Timeline document with exact frame durations."""
    total_duration_ms = int(round((total_frames / float(fps)) * 1000.0))
    duration_per_frame_ms = round(total_duration_ms / float(total_frames), 2)
    values_rows: List[List[Any]] = []

    for idx in range(total_frames):
        rec_uuid = str(uuid.uuid4())
        ts_ms = round(idx * duration_per_frame_ms, 2)
        progress = round(idx / float(max(1, total_frames)), 4)
        rot_deg = round(idx * (360.0 / float(total_frames)), 2)
        frame_filename = f"{output_prefix}{idx:04d}.png"
        svg_markup = ""
        scale_factor = 1.0
        opacity = 1.0

        if dynamic_frames and idx < len(dynamic_frames):
            frame_item = dynamic_frames[idx]
            svg_markup = frame_item.get("svg_markup", "")
            rot_deg = frame_item.get("rotation_deg", rot_deg)
            scale_factor = frame_item.get("scale_factor", 1.0)
            opacity = frame_item.get("opacity", 1.0)

        row = [
            rec_uuid,
            idx,
            ts_ms,
            duration_per_frame_ms,
            int(fps),
            progress,
            rot_deg,
            scale_factor,
            opacity,
            svg_markup,
            frame_filename,
            bool(svg_markup),
            hashlib.sha256(svg_markup.encode()).hexdigest() if svg_markup else ""
        ]
        values_rows.append(row)

    doc: Dict[str, Any] = {
        "Format": "BEJSON",
        "Format_Version": "105a",
        "Format_Creator": "Elton Boehnen",
        "Animation_Name": animation_name,
        "Total_Duration_Ms": int(total_duration_ms),
        "FPS": int(fps),
        "Total_Frames": int(total_frames),
        "Width_Px": int(width_px),
        "Height_Px": int(height_px),
        "Aspect_Ratio": aspect_ratio,
        "Remove_Frame_Source": bool(remove_frame_source),
        "Records_Type": ["SvgAnimationTimelineRecord"],
        "Fields": [dict(f) for f in GRAPHIC_ANIMATION_TIMELINE_FIELDS],
        "Values": values_rows
    }
    if parent_hierarchy:
        doc["Parent_Hierarchy"] = parent_hierarchy
    return doc


GRAPHIC_MFDB_MANIFEST_FIELDS: List[Dict[str, str]] = [
    {"name": "entity_name",    "type": "string",  "field_uuid": "9e5f6a7b-5555-4000-8000-000000000001"},
    {"name": "file_path",      "type": "string",  "field_uuid": "9e5f6a7b-5555-4000-8000-000000000002"},
    {"name": "description",    "type": "string",  "field_uuid": "9e5f6a7b-5555-4000-8000-000000000003"},
    {"name": "record_count",   "type": "integer", "field_uuid": "9e5f6a7b-5555-4000-8000-000000000004"},
    {"name": "schema_version", "type": "string",  "field_uuid": "9e5f6a7b-5555-4000-8000-000000000005"},
    {"name": "primary_key",    "type": "string",  "field_uuid": "9e5f6a7b-5555-4000-8000-000000000006"}
]


def create_graphics_mfdb_manifest_105a(
    db_name: str,
    db_description: str,
    entities: List[Dict[str, Any]],
    remove_frame_source: bool = False,
    author: str = "Elton Boehnen"
) -> Dict[str, Any]:
    """
    Creates a canonical BEJSON 105a MFDB Master Manifest for Graphics Domain databases,
    federating stages, timeline records, frame tables, and canvas assets.
    """
    values_rows: List[List[Any]] = []
    for ent in entities:
        values_rows.append([
            ent.get("entity_name", ""),
            ent.get("file_path", ""),
            ent.get("description", ""),
            int(ent.get("record_count", 0)),
            ent.get("schema_version", "1.0.0"),
            ent.get("primary_key", "record_uuid")
        ])

    from datetime import datetime, timezone
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    return {
        "Format": "BEJSON",
        "Format_Version": "104a",
        "Format_Creator": "Elton Boehnen",
        "MFDB_Version": "1.40",
        "DB_Name": db_name,
        "DB_Description": db_description,
        "Schema_Version": "1.0.0",
        "Author": author,
        "Created_At": now_iso,
        "Modified_At": now_iso,
        "Network_Role": "Master",
        "Remove_Frame_Source": bool(remove_frame_source),
        "Records_Type": ["mfdb"],
        "Fields": [
            {"name": "entity_name",    "type": "string"},
            {"name": "file_path",      "type": "string"},
            {"name": "description",    "type": "string"},
            {"name": "record_count",   "type": "integer"},
            {"name": "schema_version", "type": "string"},
            {"name": "primary_key",    "type": "string"}
        ],
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
