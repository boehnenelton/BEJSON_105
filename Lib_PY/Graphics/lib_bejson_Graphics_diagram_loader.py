"""
Library:        lib_bejson_Graphics_diagram_loader.py
Family:         Graphics
Description:    BEJSON Diagram View Loader & Multi-State Frame-by-Frame SVG Renderer.
                Loads canonical systems architecture diagrams into dynamic canvas stages
                at arbitrary camera viewports and state machine transitions frame-by-frame.
BEJSON:         BEJSON stands for BOEHNEN ELTON JSON. Authoritative definition;
                do not restate or reinterpret this acronym elsewhere.
MFDB:           MFDB stands for Multi File Database. Authoritative definition;
                do not restate or reinterpret this acronym elsewhere.
Version:        1.0.0
Date:           2026-10-27
Author:         Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
RELATIONAL_ID:  5b6c7d8e-9f0a-4b1c-c2d3-e4f5a6b7c8d9
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

_HERE = Path(__file__).resolve().parent
for _fam in ('Core', 'Taxonomies', 'Tax_Scaffolds', 'Canvas', 'Graphics'):
    _p = str(_HERE.parent / _fam)
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from lib_bejson_Graphics_graphics_schemas import (
        build_field_map_105,
        create_row_per_frame_animation_105a,
    )
except ImportError:
    from lib_bejson_graphics_schemas import (  # type: ignore
        build_field_map_105,
        create_row_per_frame_animation_105a,
    )

logger = logging.getLogger("lib_bejson_Graphics_diagram_loader")
VERSION = "1.0.0"

# Policy §8.1 Tri-Color Palette
COLOR_BLACK = "#000000"
COLOR_WHITE = "#FFFFFF"
COLOR_RED = "#DE2626"
COLOR_MUTED = "#737373"
COLOR_SURFACE = "#121218"
COLOR_BORDER = "#22222c"

SIZE_CLASSES = {
    "small":  {"w": 120, "h": 70},
    "medium": {"w": 200, "h": 100},
    "large":  {"w": 300, "h": 150},
    "huge":   {"w": 480, "h": 240}
}


# ---------------------------------------------------------------------------
# Diagram Geometry & Viewport Math
# ---------------------------------------------------------------------------

def calculate_diagram_bounds(diagram: Dict[str, Any]) -> Dict[str, float]:
    """Calculates the bounding box enclosing all shapes and territories."""
    min_x = float("inf")
    min_y = float("inf")
    max_x = float("-inf")
    max_y = float("-inf")

    shapes = diagram.get("shapes", [])
    for s in shapes:
        cx = float(s.get("cx", 0))
        cy = float(s.get("cy", 0))
        sc = SIZE_CLASSES.get(s.get("sizeClass", "medium"), SIZE_CLASSES["medium"])
        hw = sc["w"] / 2.0
        hh = sc["h"] / 2.0
        min_x = min(min_x, cx - hw)
        max_x = max(max_x, cx + hw)
        min_y = min(min_y, cy - hh)
        max_y = max(max_y, cy + hh)

    territories = diagram.get("territories", [])
    for t in territories:
        tcx = float(t.get("cx", 0))
        tcy = float(t.get("cy", 0))
        size = float(t.get("size", 200))
        min_x = min(min_x, tcx - size / 2.0)
        max_x = max(max_x, tcx + size / 2.0)
        min_y = min(min_y, tcy - size / 2.0)
        max_y = max(max_y, tcy + size / 2.0)

    if min_x == float("inf"):
        return {"min_x": 0, "min_y": 0, "max_x": 800, "max_y": 800, "width": 800, "height": 800}

    # Add 60px padding
    pad = 60.0
    return {
        "min_x": min_x - pad,
        "min_y": min_y - pad,
        "max_x": max_x + pad,
        "max_y": max_y + pad,
        "width": (max_x - min_x) + (pad * 2),
        "height": (max_y - min_y) + (pad * 2)
    }


def compute_fit_viewport(
    bounds: Dict[str, float],
    canvas_w: int = 800,
    canvas_h: int = 800
) -> Dict[str, float]:
    """Computes pan and zoom values to center and fit the bounding box into canvas."""
    b_w = max(100.0, bounds["width"])
    b_h = max(100.0, bounds["height"])

    scale_x = canvas_w / b_w
    scale_y = canvas_h / b_h
    zoom = min(scale_x, scale_y) * 0.92

    b_cx = bounds["min_x"] + b_w / 2.0
    b_cy = bounds["min_y"] + b_h / 2.0

    pan_x = (canvas_w / 2.0) - (b_cx * zoom)
    pan_y = (canvas_h / 2.0) - (b_cy * zoom)

    return {
        "pan_x": round(pan_x, 2),
        "pan_y": round(pan_y, 2),
        "zoom": round(zoom, 4)
    }


def compute_shape_focus_viewport(
    shape: Dict[str, Any],
    zoom: float = 1.3,
    canvas_w: int = 800,
    canvas_h: int = 800
) -> Dict[str, float]:
    """Computes pan and zoom values centered on a single target shape."""
    cx = float(shape.get("cx", 0))
    cy = float(shape.get("cy", 0))
    pan_x = (canvas_w / 2.0) - (cx * zoom)
    pan_y = (canvas_h / 2.0) - (cy * zoom)
    return {
        "pan_x": round(pan_x, 2),
        "pan_y": round(pan_y, 2),
        "zoom": round(zoom, 4)
    }


def resolve_viewport(
    diagram: Dict[str, Any],
    viewport_def: Optional[Dict[str, Any]] = None,
    canvas_w: int = 800,
    canvas_h: int = 800
) -> Dict[str, float]:
    """Resolves fit_view, focus_shape, or manual pan/zoom into concrete pan_x, pan_y, and zoom values."""
    bounds = calculate_diagram_bounds(diagram)
    vp = viewport_def or {}
    if not vp or vp.get("fit_view"):
        return compute_fit_viewport(bounds, canvas_w, canvas_h)
    elif vp.get("focus_shape"):
        target_s = None
        for s in diagram.get("shapes", []):
            sid = s.get("id") or s.get("tempId")
            if sid == vp["focus_shape"]:
                target_s = s
                break
        if target_s:
            return compute_shape_focus_viewport(
                target_s,
                zoom=float(vp.get("zoom", 1.3)),
                canvas_w=canvas_w,
                canvas_h=canvas_h
            )
        else:
            return compute_fit_viewport(bounds, canvas_w, canvas_h)
    else:
        return {
            "pan_x": float(vp.get("pan_x", 0.0)),
            "pan_y": float(vp.get("pan_y", 0.0)),
            "zoom": float(vp.get("zoom", 1.0))
        }


# ---------------------------------------------------------------------------
# High-Fidelity Standalone SVG Diagram Renderer
# ---------------------------------------------------------------------------

def render_diagram_svg(
    diagram: Dict[str, Any],
    state: Optional[Dict[str, Any]] = None,
    viewport: Optional[Dict[str, Any]] = None,
    canvas_w: int = 800,
    canvas_h: int = 800
) -> str:
    """
    Renders a canonical BEJSON systems diagram model into a pure standalone SVG string.
    Applies state highlights, active connector flows, and camera viewport pan/zoom transforms.
    """
    state = state or {}
    viewport = viewport or {}

    active_shapes = set(state.get("active_shapes", []))
    dimmed_shapes = set(state.get("dimmed_shapes", []))
    active_connectors = set(state.get("active_connectors", []))
    flow_progress = float(state.get("flow_progress", 0.0))
    inspector_id = state.get("inspector_shape")

    # Viewport resolution
    vp = resolve_viewport(diagram, viewport, canvas_w, canvas_h)

    # Shape index for connector routing
    shape_map: Dict[str, Dict[str, Any]] = {}
    for s in diagram.get("shapes", []):
        sid = s.get("id") or s.get("tempId")
        if sid:
            shape_map[sid] = s

    svg_lines: List[str] = [
        f'<svg id="diagram-stage" viewBox="0 0 {canvas_w} {canvas_h}" width="{canvas_w}" height="{canvas_h}" '
        f'xmlns="http://www.w3.org/2000/svg" style="background:#000000;width:100%;height:100%;display:block;">',
        '  <defs>',
        '    <!-- Arrow Markers -->',
        f'    <marker id="arrow-forward" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">',
        f'      <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="{COLOR_WHITE}" />',
        '    </marker>',
        f'    <marker id="arrow-active" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">',
        f'      <path d="M 0 1 L 9 5 L 0 9 z" fill="{COLOR_RED}" />',
        '    </marker>',
        '    <!-- Glow Filter for Active Nodes -->',
        '    <filter id="node-red-glow" x="-20%" y="-20%" width="140%" height="140%">',
        '      <feGaussianBlur stdDeviation="8" result="blur" />',
        '      <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>',
        '    </filter>',
        '    <pattern id="diag-grid" width="50" height="50" patternUnits="userSpaceOnUse">',
        '      <circle cx="25" cy="25" r="1" fill="#181822" />',
        '    </pattern>',
        '  </defs>',
        f'  <!-- Background Canvas Grid -->',
        f'  <rect width="{canvas_w}" height="{canvas_h}" fill="url(#diag-grid)" />',
        f'  <!-- Main Viewport Transform Group -->',
        f'  <g id="viewport-group" transform="translate({vp["pan_x"]}, {vp["pan_y"]}) scale({vp["zoom"]})">'
    ]

    # 1. Render Territories
    for t in diagram.get("territories", []):
        tcx = float(t.get("cx", 0))
        tcy = float(t.get("cy", 0))
        size = float(t.get("size", 200))
        color = t.get("color", COLOR_RED)
        label = t.get("label", "")
        kind = t.get("kind", "rect")

        if kind == "circle":
            r = size / 2.0
            svg_lines.append(
                f'    <circle cx="{tcx}" cy="{tcy}" r="{r}" fill="{color}" fill-opacity="0.05" '
                f'stroke="{color}" stroke-opacity="0.3" stroke-width="1.5" stroke-dasharray="6,4" />'
            )
        else:
            w = size
            h = size
            x = tcx - w / 2.0
            y = tcy - h / 2.0
            svg_lines.append(
                f'    <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="16" fill="{color}" fill-opacity="0.04" '
                f'stroke="{color}" stroke-opacity="0.25" stroke-width="1.5" stroke-dasharray="6,4" />'
            )
        if label:
            svg_lines.append(
                f'    <text x="{tcx}" y="{tcy - size/2.0 + 20}" fill="{color}" fill-opacity="0.8" font-size="12" '
                f'font-family="monospace" letter-spacing="1.5" text-anchor="middle" font-weight="bold">{label.upper()}</text>'
            )

    # 2. Render Connectors
    for c in diagram.get("connectors", []):
        from_id = c.get("from") or c.get("fromTempId")
        to_id = c.get("to") or c.get("toTempId")
        flow = c.get("flow", "forward")
        cid = f"{from_id}->{to_id}"

        if from_id not in shape_map or to_id not in shape_map:
            continue

        s_from = shape_map[from_id]
        s_to = shape_map[to_id]

        fx = float(s_from.get("cx", 0))
        fy = float(s_from.get("cy", 0))
        tx = float(s_to.get("cx", 0))
        ty = float(s_to.get("cy", 0))

        is_active = (cid in active_connectors) or (from_id in active_shapes and to_id in active_shapes)
        conn_color = COLOR_RED if is_active else COLOR_WHITE
        marker_id = "arrow-active" if is_active else "arrow-forward"
        stroke_w = "2.5" if is_active else "1.5"

        # Midpoint curve calculation
        mid_x = (fx + tx) / 2.0
        mid_y = (fy + ty) / 2.0

        marker_attr = f'marker-end="url(#{marker_id})"' if flow == "forward" else ""
        if flow == "bidirectional":
            marker_attr = f'marker-start="url(#{marker_id})" marker-end="url(#{marker_id})"'

        svg_lines.append(
            f'    <!-- Connector {cid} -->'
            f'    <line x1="{fx}" y1="{fy}" x2="{tx}" y2="{ty}" stroke="{conn_color}" '
            f'stroke-width="{stroke_w}" stroke-opacity="{1.0 if is_active else 0.4}" {marker_attr} />'
        )

        # Active Data Flow Particle
        if is_active and flow_progress > 0.0:
            px = fx + (tx - fx) * flow_progress
            py = fy + (ty - fy) * flow_progress
            svg_lines.append(
                f'    <circle cx="{px}" cy="{py}" r="5" fill="{COLOR_RED}" filter="url(#node-red-glow)" />'
            )

    # 3. Render Shapes (Nodes)
    for s in diagram.get("shapes", []):
        sid = s.get("id") or s.get("tempId")
        cx = float(s.get("cx", 0))
        cy = float(s.get("cy", 0))
        label = s.get("label", "Node")
        text = s.get("text", "")
        kind = s.get("kind", "rect")
        sc = SIZE_CLASSES.get(s.get("sizeClass", "medium"), SIZE_CLASSES["medium"])
        w = sc["w"]
        h = sc["h"]

        is_active = sid in active_shapes
        is_dimmed = sid in dimmed_shapes
        opacity = "0.2" if is_dimmed else "1.0"

        border_color = COLOR_RED if is_active else COLOR_WHITE
        border_w = "2.5" if is_active else "1.2"
        glow_filter = 'filter="url(#node-red-glow)"' if is_active else ""
        bg_fill = "#1c0d0d" if is_active else COLOR_SURFACE

        if kind == "circle":
            r = min(w, h) / 2.0
            svg_lines.append(
                f'    <!-- Shape {sid} -->'
                f'    <g id="shape-{sid}" opacity="{opacity}">'
                f'      <circle cx="{cx}" cy="{cy}" r="{r}" fill="{bg_fill}" stroke="{border_color}" '
                f'stroke-width="{border_w}" {glow_filter} />'
                f'      <text x="{cx}" y="{cy + 4}" fill="{COLOR_WHITE}" font-size="12" font-family="-apple-system, sans-serif" '
                f'font-weight="bold" text-anchor="middle">{label}</text>'
                f'    </g>'
            )
        else:
            x = cx - w / 2.0
            y = cy - h / 2.0
            svg_lines.append(
                f'    <!-- Shape {sid} -->'
                f'    <g id="shape-{sid}" opacity="{opacity}">'
                f'      <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{bg_fill}" '
                f'stroke="{border_color}" stroke-width="{border_w}" {glow_filter} />'
                f'      <text x="{x + 12}" y="{y + 24}" fill="{COLOR_WHITE}" font-size="12" font-family="-apple-system, sans-serif" '
                f'font-weight="bold">{label}</text>'
            )
            if text:
                short_text = text[:36] + ("..." if len(text) > 36 else "")
                svg_lines.append(
                    f'      <text x="{x + 12}" y="{y + 42}" fill="{COLOR_MUTED}" font-size="10" font-family="-apple-system, sans-serif">{short_text}</text>'
                )
            # Active Indicator Pip
            if is_active:
                svg_lines.append(
                    f'      <circle cx="{x + w - 12}" cy="{y + 12}" r="4" fill="{COLOR_RED}" />'
                )
            svg_lines.append('    </g>')

    # 4. Render Inspector Card (if shape is inspected)
    if inspector_id and inspector_id in shape_map:
        ins_s = shape_map[inspector_id]
        icx = float(ins_s.get("cx", 0))
        icy = float(ins_s.get("cy", 0))
        ilabel = ins_s.get("label", "Node Inspector")
        itext = ins_s.get("text", "")

        card_w = 260
        card_h = 90
        card_x = icx - card_w / 2.0
        card_y = icy - card_h - 20

        svg_lines.append(
            f'    <!-- Inspector Card for {inspector_id} -->'
            f'    <g id="inspector-{inspector_id}">'
            f'      <rect x="{card_x}" y="{card_y}" width="{card_w}" height="{card_h}" rx="6" '
            f'fill="#0a0a0e" stroke="{COLOR_RED}" stroke-width="1.5" filter="url(#node-red-glow)" />'
            f'      <text x="{card_x + 12}" y="{card_y + 22}" fill="{COLOR_RED}" font-size="12" font-family="monospace" font-weight="bold">INSPECT: {inspector_id}</text>'
            f'      <text x="{card_x + 12}" y="{card_y + 40}" fill="{COLOR_WHITE}" font-size="11" font-family="-apple-system, sans-serif" font-weight="bold">{ilabel}</text>'
            f'      <text x="{card_x + 12}" y="{card_y + 58}" fill="{COLOR_MUTED}" font-size="9" font-family="-apple-system, sans-serif">{itext[:60]}</text>'
            f'    </g>'
        )

    svg_lines.append('  </g>')

    # 5. Canvas HUD Header / State Badge
    badge_text = state.get("badge_text") or diagram.get("name")
    if badge_text:
        svg_lines.append(
            f'  <!-- Canvas Status Telemetry Badge -->'
            f'  <g id="canvas-hud">'
            f'    <rect x="20" y="20" width="320" height="36" rx="4" fill="#0c0c12" fill-opacity="0.9" stroke="#22222c" stroke-width="1" />'
            f'    <circle cx="36" cy="38" r="4" fill="{COLOR_RED}" />'
            f'    <text x="52" y="42" fill="{COLOR_WHITE}" font-size="11" font-family="monospace" font-weight="bold" letter-spacing="1">{badge_text[:35].upper()}</text>'
            f'  </g>'
        )

    svg_lines.append('</svg>')
    return "\n".join(svg_lines)


# ---------------------------------------------------------------------------
# Multi-State Row-Per-Frame Animation Builder
# ---------------------------------------------------------------------------

def create_diagram_frame_sequence_105a(
    diagram: Dict[str, Any],
    states_sequence: List[Dict[str, Any]],
    animation_name: Optional[str] = None,
    fps: int = 30,
    hold_sec_per_state: float = 2.0,
    transition_sec: float = 0.6,
    canvas_w: int = 800,
    canvas_h: int = 800
) -> Dict[str, Any]:
    """
    Constructs a BEJSON 105a Row-Per-Frame Animation document for a diagram.
    Iterates through sequential states, interpolating camera pan/zoom viewports
    and active connector data-flow progress frame-by-frame.
    """
    anim_name = animation_name or f"{diagram.get('diagramId', 'diag')}_walkthrough"
    total_states = len(states_sequence)
    if total_states == 0:
        states_sequence = [{"name": "default", "active_shapes": [], "viewport": {"fit_view": True}}]
        total_states = 1

    total_duration_sec = total_states * (hold_sec_per_state + transition_sec)
    total_frames = max(1, int(math.ceil(total_duration_sec * fps)))
    time_step_sec = total_duration_sec / max(1, (total_frames - 1)) if total_frames > 1 else 0.0

    dynamic_frames: List[Dict[str, Any]] = []

    state_step_dur = hold_sec_per_state + transition_sec

    for f_idx in range(total_frames):
        cur_time = f_idx * time_step_sec
        state_idx = min(total_states - 1, int(cur_time // state_step_dur))
        time_in_state = cur_time - (state_idx * state_step_dur)

        cur_state_def = states_sequence[state_idx]
        next_state_def = states_sequence[min(total_states - 1, state_idx + 1)]

        # Viewport interpolation
        cur_vp = cur_state_def.get("viewport", {"fit_view": True})
        next_vp = next_state_def.get("viewport", {"fit_view": True})

        # Resolve viewport bounds
        c_v = resolve_viewport(diagram, cur_vp, canvas_w, canvas_h)
        n_v = resolve_viewport(diagram, next_vp, canvas_w, canvas_h)

        # Linear camera pan & zoom interpolation during transition window
        if time_in_state > hold_sec_per_state and transition_sec > 0:
            tr_ratio = (time_in_state - hold_sec_per_state) / transition_sec
            eff_pan_x = c_v["pan_x"] + (n_v["pan_x"] - c_v["pan_x"]) * tr_ratio
            eff_pan_y = c_v["pan_y"] + (n_v["pan_y"] - c_v["pan_y"]) * tr_ratio
            eff_zoom = c_v["zoom"] + (n_v["zoom"] - c_v["zoom"]) * tr_ratio
        else:
            eff_pan_x = c_v["pan_x"]
            eff_pan_y = c_v["pan_y"]
            eff_zoom = c_v["zoom"]

        eff_viewport = {
            "pan_x": round(eff_pan_x, 2),
            "pan_y": round(eff_pan_y, 2),
            "zoom": round(eff_zoom, 4)
        }

        # Data flow particle progress along active connectors
        flow_progress = (cur_time % 1.0)  # repeating pulse every second

        eff_state = {
            "active_shapes": cur_state_def.get("active_shapes", []),
            "dimmed_shapes": cur_state_def.get("dimmed_shapes", []),
            "active_connectors": cur_state_def.get("active_connectors", []),
            "flow_progress": flow_progress,
            "badge_text": cur_state_def.get("badge_text", cur_state_def.get("name")),
            "inspector_shape": cur_state_def.get("inspector_shape")
        }

        # Render frame SVG
        frame_svg = render_diagram_svg(
            diagram=diagram,
            state=eff_state,
            viewport=eff_viewport,
            canvas_w=canvas_w,
            canvas_h=canvas_h
        )

        dynamic_frames.append({
            "svg_markup": frame_svg,
            "data": {
                "state_index": state_idx,
                "state_name": cur_state_def.get("name", f"state_{state_idx}"),
                "pan_x": eff_viewport["pan_x"],
                "pan_y": eff_viewport["pan_y"],
                "zoom": eff_viewport["zoom"]
            }
        })

    return create_row_per_frame_animation_105a(
        animation_name=anim_name,
        duration_sec=total_duration_sec,
        fps=fps,
        width_px=canvas_w,
        height_px=canvas_h,
        dynamic_frames=dynamic_frames,
        output_prefix="diag_frame_"
    )
