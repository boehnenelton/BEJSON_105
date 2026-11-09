"""
Library:        lib_bejson_Graphics_graphics_core.py
Family:         Graphics
Description:    Playwright SVG Capture Engine, Dynamic Frame File-Based Animation Renderer,
                and BEJSON 105a Row-Per-Frame Animation Controller.
BEJSON:         BEJSON stands for BOEHNEN ELTON JSON. Authoritative definition;
                do not restate or reinterpret this acronym elsewhere.
                (Pronounced Bee-Jay-Son / Bay-nin Elton JSON)
MFDB:           MFDB stands for Multi File Database. Authoritative definition;
                do not restate or reinterpret this acronym elsewhere.
Version:        1.1.0
Date:           2026-10-30
Changelog:
  1.0.1 - 2026-10-30: Imports standardized to the cased module names (lowercase stubs removed).
Author:         Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
RELATIONAL_ID:  9ade1e3b-88ad-4a74-84d7-18b90b40b634
Release_Version: 300
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import math
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

_HERE = Path(__file__).resolve().parent
for _fam in ('Core', 'Taxonomies', 'Tax_Scaffolds', 'Canvas', 'Graphics'):
    _p = str(_HERE.parent / _fam)
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

from lib_bejson_Graphics_graphics_schemas import (
    GRAPHIC_CANVAS_CONFIG_FIELDS,
    GRAPHIC_ROW_FRAME_FIELDS,
    build_field_map_105,
    create_graphic_stage_config_105a,
    create_row_per_frame_animation_105a,
    validate_graphic_105a_doc,
)
from lib_bejson_Graphics_graphics_canvas_templates import (
    generate_blank_slate_html,
    get_template_html,
    instantiate_stage_file,
    list_registered_templates,
)

logger = logging.getLogger("lib_bejson_Graphics_graphics_core")
VERSION = "1.1.0"

# Policy §8.1 Tri-Color Palette
COLOR_BLACK = "#000000"
COLOR_WHITE = "#FFFFFF"
COLOR_RED = "#DE2626"


# ---------------------------------------------------------------------------
# Dynamic SVG Generation Primitives
# ---------------------------------------------------------------------------

def create_isometric_cube_svg(
    viewbox_size: int = 400,
    cube_style: str = "104a_floating",
    stroke_color: str = COLOR_WHITE,
    accent_color: str = COLOR_RED,
    pulse_intensity: float = 1.0
) -> str:
    """
    Generates dynamic Policy §8.3 compliant isometric cube SVG markup.
    Supported styles:
    - 104: Standard single cube
    - 104a_floating: Cube with floating top cap
    - 104db_pillar: Vertical pillar of stacked cubes
    - 104_nested: Outer cube enclosing inner child cubes
    - mfdb_federation: Central master cube linked to peripheral node cubes
    """
    center_x = viewbox_size / 2.0
    center_y = viewbox_size / 2.0
    size = viewbox_size * 0.28

    dx = size * math.cos(math.radians(30))
    dy = size * math.sin(math.radians(30))

    if cube_style == "104a_floating":
        float_offset = 18.0 * pulse_intensity
        # Top floating face
        p_top = [
            f"{center_x},{center_y - size - float_offset}",
            f"{center_x + dx},{center_y - dy - float_offset}",
            f"{center_x},{center_y - float_offset}",
            f"{center_x - dx},{center_y - dy - float_offset}"
        ]
        # Left face
        p_left = [
            f"{center_x},{center_y}",
            f"{center_x - dx},{center_y - dy}",
            f"{center_x - dx},{center_y + size - dy}",
            f"{center_x},{center_y + size}"
        ]
        # Right face
        p_right = [
            f"{center_x},{center_y}",
            f"{center_x + dx},{center_y - dy}",
            f"{center_x + dx},{center_y + size - dy}",
            f"{center_x},{center_y + size}"
        ]

        svg = f"""<svg viewBox="0 0 {viewbox_size} {viewbox_size}" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:100%;">
  <defs>
    <filter id="cube-glow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="6" result="blur" />
      <feMerge>
        <feMergeNode in="blur" />
        <feMergeNode in="SourceGraphic" />
      </feMerge>
    </filter>
  </defs>
  <!-- Background coordinate crosshairs -->
  <line x1="{center_x}" y1="20" x2="{center_x}" y2="{viewbox_size-20}" stroke="#1c1c24" stroke-width="1" stroke-dasharray="4,4" />
  <line x1="20" y1="{center_y}" x2="{viewbox_size-20}" y2="{center_y}" stroke="#1c1c24" stroke-width="1" stroke-dasharray="4,4" />
  <!-- Floating Cap (BEJSON 104a) -->
  <polygon points="{' '.join(p_top)}" fill="{accent_color}" fill-opacity="0.25" stroke="{accent_color}" stroke-width="2.5" filter="url(#cube-glow)" />
  <!-- Left Face -->
  <polygon points="{' '.join(p_left)}" fill="#0c0c10" stroke="{stroke_color}" stroke-width="2" />
  <!-- Right Face -->
  <polygon points="{' '.join(p_right)}" fill="#14141a" stroke="{stroke_color}" stroke-width="2" />
  <!-- Center Core Node -->
  <circle cx="{center_x}" cy="{center_y + size/2}" r="{4 * pulse_intensity}" fill="{accent_color}" />
</svg>"""
        return svg

    # Default Standard 104 Cube
    p_top = [
        f"{center_x},{center_y - size}",
        f"{center_x + dx},{center_y - dy}",
        f"{center_x},{center_y}",
        f"{center_x - dx},{center_y - dy}"
    ]
    p_left = [
        f"{center_x},{center_y}",
        f"{center_x - dx},{center_y - dy}",
        f"{center_x - dx},{center_y + size - dy}",
        f"{center_x},{center_y + size}"
    ]
    p_right = [
        f"{center_x},{center_y}",
        f"{center_x + dx},{center_y - dy}",
        f"{center_x + dx},{center_y + size - dy}",
        f"{center_x},{center_y + size}"
    ]

    return f"""<svg viewBox="0 0 {viewbox_size} {viewbox_size}" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:100%;">
  <polygon points="{' '.join(p_top)}" fill="#181822" stroke="{stroke_color}" stroke-width="2" />
  <polygon points="{' '.join(p_left)}" fill="#0e0e14" stroke="{stroke_color}" stroke-width="2" />
  <polygon points="{' '.join(p_right)}" fill="#12121a" stroke="{stroke_color}" stroke-width="2" />
  <circle cx="{center_x}" cy="{center_y}" r="{3 * pulse_intensity}" fill="{accent_color}" />
</svg>"""


def render_spinning_cube_svg(
    rotation_deg: float,
    width_px: int = 400,
    height_px: int = 400,
    accent_color: str = COLOR_RED
) -> str:
    """Renders 3D projected isometric cube SVG with floating cap, normal culling, and reticle."""
    cx = width_px / 2.0
    cy = height_px / 2.0
    size = width_px * 0.18

    rad = math.radians(rotation_deg)
    pitch = math.radians(30)
    cos_a, sin_a = math.cos(rad), math.sin(rad)
    cos_p, sin_p = math.cos(pitch), math.sin(pitch)

    verts = []
    for x in (-size, size):
        for y in (-size, size):
            for z in (-size, size):
                rx = x * cos_a + z * sin_a
                ry = y
                rz = -x * sin_a + z * cos_a
                px = rx
                py = ry * cos_p - rz * sin_p
                pz = ry * sin_p + rz * cos_p
                verts.append((cx + px, cy + py, pz))

    faces = [
        ([0, 4, 6, 2], "front",  (0, 0, -1)),
        ([4, 5, 7, 6], "right",  (1, 0, 0)),
        ([5, 1, 3, 7], "back",   (0, 0, 1)),
        ([1, 0, 2, 3], "left",   (-1, 0, 0)),
        ([0, 1, 5, 4], "top",    (0, -1, 0)),
        ([2, 6, 7, 3], "bottom", (0, 1, 0)),
    ]

    sorted_faces = []
    for face_verts_idx, face_name, (nx, ny, nz) in faces:
        rnx = nx * cos_a + nz * sin_a
        rny = ny
        rnz = -nx * sin_a + nz * cos_a
        pnz = rny * sin_p + rnz * cos_p
        cz = sum(verts[i][2] for i in face_verts_idx) / 4.0
        sorted_faces.append((cz, pnz, face_verts_idx, face_name))

    sorted_faces.sort(key=lambda item: item[0])

    svg_lines = [
        f'<svg width="{width_px}" height="{height_px}" viewBox="0 0 {width_px} {height_px}" xmlns="http://www.w3.org/2000/svg">',
        f'<rect width="{width_px}" height="{height_px}" fill="#000000"/>',
        f'<ellipse cx="{cx}" cy="{cy}" rx="{size * 2.2}" ry="{size * 0.9}" fill="none" stroke="{accent_color}" stroke-width="1.5" stroke-dasharray="8,6" opacity="0.6"/>'
    ]

    for cz, pnz, face_verts_idx, face_name in sorted_faces:
        if pnz > 0:
            pts = " ".join(f"{verts[i][0]:.1f},{verts[i][1]:.1f}" for i in face_verts_idx)
            if face_name == "top":
                fill, fill_op, stroke = accent_color, "0.4", accent_color
            elif face_name in ("front", "left"):
                fill, fill_op, stroke = "#0E0E16", "0.95", "#FFFFFF"
            else:
                fill, fill_op, stroke = "#161622", "0.95", "#FFFFFF"
            svg_lines.append(f'<polygon points="{pts}" fill="{fill}" fill-opacity="{fill_op}" stroke="{stroke}" stroke-width="2"/>')

    svg_lines.append(f'<circle cx="{cx}" cy="{cy}" r="5" fill="{accent_color}"/>')
    svg_lines.append('</svg>')
    return "\n".join(svg_lines)


def render_radar_scanner_svg(
    rotation_deg: float,
    width_px: int = 320,
    height_px: int = 320,
    accent_color: str = COLOR_RED
) -> str:
    """Renders high-contrast radar sweep scanner SVG."""
    cx = width_px / 2.0
    cy = height_px / 2.0
    r = (width_px / 2.0) - 20

    rad = math.radians(rotation_deg)
    bx = cx + r * math.cos(rad)
    by = cy + r * math.sin(rad)

    trail_rad = math.radians(rotation_deg - 45)
    tx = cx + r * math.cos(trail_rad)
    ty = cy + r * math.sin(trail_rad)

    return f"""<svg width="{width_px}" height="{height_px}" viewBox="0 0 {width_px} {height_px}" xmlns="http://www.w3.org/2000/svg">
  <rect width="{width_px}" height="{height_px}" fill="#000000"/>
  <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#2A2A38" stroke-width="1.5"/>
  <circle cx="{cx}" cy="{cy}" r="{r*0.66}" fill="none" stroke="#1C1C28" stroke-width="1"/>
  <circle cx="{cx}" cy="{cy}" r="{r*0.33}" fill="none" stroke="#1C1C28" stroke-width="1"/>
  <line x1="{cx-r}" y1="{cy}" x2="{cx+r}" y2="{cy}" stroke="#1C1C28" stroke-width="1"/>
  <line x1="{cx}" y1="{cy-r}" x2="{cx}" y2="{cy+r}" stroke="#1C1C28" stroke-width="1"/>
  <path d="M{cx},{cy} L{bx:.1f},{by:.1f} A{r},{r} 0 0,0 {tx:.1f},{ty:.1f} Z" fill="{accent_color}" fill-opacity="0.25"/>
  <line x1="{cx}" y1="{cy}" x2="{bx:.1f},{by:.1f}" stroke="{accent_color}" stroke-width="2"/>
  <circle cx="{cx}" cy="{cy}" r="4" fill="{accent_color}"/>
  <circle cx="{cx + r*0.4}" cy="{cy - r*0.3}" r="3" fill="#FFFFFF"/>
  <circle cx="{cx - r*0.5}" cy="{cy + r*0.4}" r="3" fill="#FFFFFF"/>
</svg>"""


# ---------------------------------------------------------------------------
# Canonical BEJSON Minimal Point-Focus Presentation Slide Renderers (16:9)
# ---------------------------------------------------------------------------

def bejson_logo_svg(x: int = 1030, y: int = 655, is_dark: bool = True) -> str:
    """Renders canonical BEJSON text logo with isometric 3D cube emblem."""
    txt_col = "#FFFFFF" if is_dark else "#111111"
    cutout_col = "#111113" if is_dark else "#F8F9FA"
    left_col = "#1C1C22" if is_dark else "#E5E7EB"
    return f"""<g transform="translate({x}, {y})">
    <text x="0" y="22" fill="{txt_col}" font-size="24" font-family="system-ui, -apple-system, sans-serif" font-weight="900" letter-spacing="1.5">BEJSON</text>
    <g transform="translate(112, 0)">
      <polygon points="14,2 26,8 14,14 2,8" fill="#FFFFFF" stroke="{txt_col}" stroke-width="1" stroke-linejoin="round"/>
      <polygon points="14,5 22,9 14,13 6,9" fill="{cutout_col}" opacity="0.9"/>
      <polygon points="2,8 14,14 14,28 2,22" fill="{left_col}" stroke="{txt_col}" stroke-width="1" stroke-linejoin="round"/>
      <polygon points="14,14 26,8 26,22 14,28" fill="#DE2626" stroke="{txt_col}" stroke-width="1" stroke-linejoin="round"/>
    </g>
  </g>"""


def render_slide_split_visual_svg(
    title: str = "TITLE",
    tagline: str = "TAGLINE",
    content: str = "[ INSERT CONTENT / TEXT HERE ]",
    visual_placeholder: str = "[ INSERT IMAGE OR VISUAL PLACEHOLDER ]",
    width_px: int = 1280,
    height_px: int = 720,
    inner_svg: Optional[str] = None,
    *args,
    **kwargs
) -> str:
    """
    Renders sleek, minimal 16:9 Split-Screen Visual presentation slide.
    Left: Large dedicated visual/image container with subtle corner registration tick marks.
    Right: High-impact Title, Tagline, and narrative content block.
    Bottom: Thin red accent rule with canonical BEJSON 3D cube branding.
    """
    if "subtitle" in kwargs and tagline == "TAGLINE":
        tagline = kwargs["subtitle"]

    w, h = width_px, height_px
    logo = bejson_logo_svg(x=w - 230, y=h - 60, is_dark=True)
    visual_slot = inner_svg if inner_svg else f"""<rect x="64" y="64" width="540" height="520" rx="4" fill="#0E0E10" stroke="#24242A" stroke-width="1.5"/>
  <path d="M 64 88 L 64 64 L 88 64" fill="none" stroke="#3A3A44" stroke-width="1.5"/>
  <path d="M 580 64 L 604 64 L 604 88" fill="none" stroke="#3A3A44" stroke-width="1.5"/>
  <path d="M 64 560 L 64 584 L 88 584" fill="none" stroke="#3A3A44" stroke-width="1.5"/>
  <path d="M 580 584 L 604 584 L 604 560" fill="none" stroke="#3A3A44" stroke-width="1.5"/>
  <text x="334" y="328" fill="#555562" font-size="16" font-family="system-ui, -apple-system, sans-serif" font-weight="500" letter-spacing="0.5" text-anchor="middle">{visual_placeholder}</text>"""

    return f"""<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg">
  <rect width="{w}" height="{h}" fill="#111113"/>
  {visual_slot}
  <text x="660" y="130" fill="#FFFFFF" font-size="48" font-family="system-ui, -apple-system, sans-serif" font-weight="800" letter-spacing="1">{title}</text>
  <text x="660" y="175" fill="#777782" font-size="24" font-family="system-ui, -apple-system, sans-serif" font-weight="600" letter-spacing="1">{tagline}</text>
  <text x="660" y="340" fill="#888894" font-size="18" font-family="system-ui, -apple-system, sans-serif" font-weight="400" letter-spacing="0.5">{content}</text>
  <line x1="64" y1="{h-65}" x2="{w-64}" y2="{h-65}" stroke="#DE2626" stroke-width="2"/>
  {logo}
</svg>"""


def render_slide_key_points_svg(
    title: str = "SECTION TITLE",
    tagline: str = "TAGLINE OR SUBTITLE",
    narrative: str = "[ INSERT PARAGRAPH OR NARRATIVE TEXT HERE ]",
    key_points: Optional[List[str]] = None,
    width_px: int = 1280,
    height_px: int = 720,
    *args,
    **kwargs
) -> str:
    """
    Renders sleek, minimal 16:9 Key Points presentation slide.
    Left: Bold Section Title, Tagline, and narrative paragraph.
    Right: Clean Key Points bulleted list with subtle indicator dots.
    Bottom: Thin red accent rule with canonical BEJSON 3D cube branding.
    """
    if "subtitle" in kwargs and tagline == "TAGLINE OR SUBTITLE":
        tagline = kwargs["subtitle"]

    w, h = width_px, height_px
    logo = bejson_logo_svg(x=w - 230, y=h - 60, is_dark=True)
    pts = key_points or ["[ INSERT KEY POINT 1 ]", "[ INSERT KEY POINT 2 ]", "[ INSERT KEY POINT 3 ]"]
    bullets_svg = []
    for i, pt in enumerate(pts):
        by = 335 + i * 50
        bullets_svg.append(f"""<circle cx="695" cy="{by-5}" r="3.5" fill="#777784"/>
  <text x="715" y="{by}" fill="#888894" font-size="18" font-family="system-ui, -apple-system, sans-serif" font-weight="400" letter-spacing="0.5">{pt}</text>""")
    bullets_markup = "\n  ".join(bullets_svg)

    return f"""<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg">
  <rect width="{w}" height="{h}" fill="#111113"/>
  <!-- Subtle coordinate crosshairs -->
  <path d="M 640 24 L 640 44 M 630 34 L 650 34" stroke="#222228" stroke-width="1.5"/>
  <path d="M 640 {h-44} L 640 {h-24} M 630 {h-34} L 650 {h-34}" stroke="#222228" stroke-width="1.5"/>
  <path d="M 34 350 L 34 370 M 24 360 L 44 360" stroke="#222228" stroke-width="1.5"/>
  <path d="M {w-34} 350 L {w-34} 370 M {w-44} 360 L {w-24} 360" stroke="#222228" stroke-width="1.5"/>
  <!-- Left Column -->
  <text x="64" y="130" fill="#FFFFFF" font-size="48" font-family="system-ui, -apple-system, sans-serif" font-weight="800" letter-spacing="1">{title}</text>
  <text x="64" y="175" fill="#777782" font-size="24" font-family="system-ui, -apple-system, sans-serif" font-weight="600" letter-spacing="1">{tagline}</text>
  <text x="64" y="280" fill="#666672" font-size="18" font-family="system-ui, -apple-system, sans-serif" font-weight="400" letter-spacing="0.5">{narrative}</text>
  <!-- Right Column -->
  <text x="680" y="280" fill="#FFFFFF" font-size="26" font-family="system-ui, -apple-system, sans-serif" font-weight="700" letter-spacing="1">KEY POINTS</text>
  {bullets_markup}
  <line x1="64" y1="{h-65}" x2="{w-64}" y2="{h-65}" stroke="#DE2626" stroke-width="2"/>
  {logo}
</svg>"""


def render_slide_visual_focus_light_svg(
    title: str = "TITLE OF YOUR SLIDE",
    description: str = "Add your descriptive text, notes, or bullet points in this lower section to keep the visual area open",
    placeholder_text: str = "[ INSERT VISUALS HERE ]",
    width_px: int = 1280,
    height_px: int = 720,
    inner_svg: Optional[str] = None,
    *args,
    **kwargs
) -> str:
    """
    Renders sleek, clean 16:9 Light Mode Visual Focus presentation slide.
    Top 70%: Open visual canvas area with delicate coordinate registration marks.
    Middle: Clean red horizontal divider rule.
    Bottom 30%: Bold black title, descriptive paragraph, and BEJSON branding.
    """
    if "subtitle" in kwargs and description.startswith("Add your descriptive text"):
        description = kwargs["subtitle"]

    w, h = width_px, height_px
    logo = bejson_logo_svg(x=w - 230, y=h - 85, is_dark=False)
    visual_slot = inner_svg if inner_svg else f"""<!-- Visual Area Registration Marks -->
  <path d="M 640 24 L 640 44 M 630 34 L 650 34" stroke="#D8D9E0" stroke-width="1.5"/>
  <path d="M 100 240 L 100 260 M 90 250 L 110 250" stroke="#D8D9E0" stroke-width="1.5"/>
  <path d="M {w-100} 240 L {w-100} 260 M {w-110} 250 L {w-90} 250" stroke="#D8D9E0" stroke-width="1.5"/>
  <path d="M 640 450 L 640 470 M 630 460 L 650 460" stroke="#D8D9E0" stroke-width="1.5"/>
  <path d="M 120 100 L 120 80 L 140 80" fill="none" stroke="#C0C0CA" stroke-width="1.5"/>
  <path d="M {w-120} 440 L {w-120} 460 L {w-140} 460" fill="none" stroke="#C0C0CA" stroke-width="1.5"/>
  <text x="640" y="255" fill="#888892" font-size="16" font-family="system-ui, -apple-system, sans-serif" font-weight="500" letter-spacing="0.5" text-anchor="middle">{placeholder_text}</text>"""

    return f"""<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg">
  <rect width="{w}" height="{h}" fill="#F8F9FA"/>
  {visual_slot}
  <!-- Divider -->
  <line x1="64" y1="510" x2="{w-64}" y2="510" stroke="#DE2626" stroke-width="2.5"/>
  <!-- Lower Section -->
  <text x="64" y="575" fill="#111111" font-size="36" font-family="system-ui, -apple-system, sans-serif" font-weight="800" letter-spacing="1">{title}</text>
  <text x="64" y="618" fill="#44444A" font-size="18" font-family="system-ui, -apple-system, sans-serif" font-weight="400">{description}</text>
  {logo}
</svg>"""


def render_slide_visual_focus_dark_svg(
    title: str = "TITLE",
    tagline: str = "TAGLINE",
    placeholder_text: str = "[ INSERT VISUAL HERE ]",
    width_px: int = 1280,
    height_px: int = 720,
    inner_svg: Optional[str] = None,
    *args,
    **kwargs
) -> str:
    """
    Renders sleek, clean 16:9 Dark Mode Visual Focus presentation slide.
    Top 70%: Open visual canvas area with delicate coordinate registration marks.
    Middle: Clean red horizontal divider rule.
    Bottom 30%: High-impact white Title, Tagline, and BEJSON branding.
    """
    if "subtitle" in kwargs and tagline == "TAGLINE":
        tagline = kwargs["subtitle"]

    w, h = width_px, height_px
    logo = bejson_logo_svg(x=w - 230, y=h - 85, is_dark=True)
    visual_slot = inner_svg if inner_svg else f"""<!-- Visual Area Registration Marks -->
  <path d="M 640 24 L 640 44 M 630 34 L 650 34" stroke="#222228" stroke-width="1.5"/>
  <path d="M 100 250 L 100 270 M 90 260 L 110 260" stroke="#222228" stroke-width="1.5"/>
  <path d="M {w-100} 250 L {w-100} 270 M {w-110} 260 L {w-90} 260" stroke="#222228" stroke-width="1.5"/>
  <path d="M 640 460 L 640 480 M 630 470 L 650 470" stroke="#222228" stroke-width="1.5"/>
  <path d="M 120 100 L 120 80 L 140 80" fill="none" stroke="#2A2A32" stroke-width="1.5"/>
  <path d="M {w-120} 450 L {w-120} 470 L {w-140} 470" fill="none" stroke="#2A2A32" stroke-width="1.5"/>
  <text x="640" y="260" fill="#555562" font-size="16" font-family="system-ui, -apple-system, sans-serif" font-weight="500" letter-spacing="0.5" text-anchor="middle">{placeholder_text}</text>"""

    return f"""<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg">
  <rect width="{w}" height="{h}" fill="#111113"/>
  {visual_slot}
  <!-- Divider -->
  <line x1="64" y1="520" x2="{w-64}" y2="520" stroke="#DE2626" stroke-width="2"/>
  <!-- Lower Section -->
  <text x="64" y="585" fill="#FFFFFF" font-size="44" font-family="system-ui, -apple-system, sans-serif" font-weight="800" letter-spacing="1">{title}</text>
  <text x="64" y="635" fill="#777782" font-size="24" font-family="system-ui, -apple-system, sans-serif" font-weight="600" letter-spacing="1">{tagline}</text>
  {logo}
</svg>"""


def render_slide_process_flow_svg(
    title: str = "FLOW",
    steps: Optional[List[Dict[str, Any]]] = None,
    width_px: int = 1280,
    height_px: int = 720,
    *args,
    **kwargs
) -> str:
    """
    Renders sleek, clean 16:9 Horizontal Process Flow presentation slide.
    Top-left: Red accent bar above title.
    Center: 3 clean rounded rectangular cards connected by directional red arrows.
    Bottom: Subtle footer divider line and canonical BEJSON branding.
    """
    w, h = width_px, height_px
    logo = bejson_logo_svg(x=w - 230, y=h - 60, is_dark=True)
    card_w = 270
    card_h = 180
    c1_x = 125
    c2_x = 505
    c3_x = 885
    c_y = 260
    cards_data = steps or [{"label": "Step 1", "sub": ""}, {"label": "Step 2", "sub": ""}, {"label": "Step 3", "sub": ""}]

    cards_svg = []
    positions = [c1_x, c2_x, c3_x]
    for i, c_x in enumerate(positions):
        lbl = cards_data[i].get("label", f"Step {i+1}") if i < len(cards_data) else f"Step {i+1}"
        sub = cards_data[i].get("sub", "") if i < len(cards_data) else ""
        lbl_svg = f'<text x="{c_x + card_w/2}" y="{c_y + card_h/2 + 6}" fill="#FFFFFF" font-size="18" font-family="system-ui, -apple-system, sans-serif" font-weight="600" text-anchor="middle">{lbl}</text>' if lbl else ''
        sub_svg = f'<text x="{c_x + card_w/2}" y="{c_y + card_h/2 + 30}" fill="#777782" font-size="13" font-family="system-ui, -apple-system, sans-serif" text-anchor="middle">{sub}</text>' if sub else ''
        cards_svg.append(f"""<rect x="{c_x}" y="{c_y}" width="{card_w}" height="{card_h}" rx="12" fill="#16161A" stroke="#26262E" stroke-width="1.5"/>
  {lbl_svg}
  {sub_svg}""")

    cards_markup = "\n  ".join(cards_svg)

    return f"""<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg">
  <rect width="{w}" height="{h}" fill="#111113"/>
  <!-- Red accent bar above title -->
  <rect x="64" y="60" width="44" height="4" rx="2" fill="#DE2626"/>
  <text x="64" y="115" fill="#FFFFFF" font-size="44" font-family="system-ui, -apple-system, sans-serif" font-weight="800" letter-spacing="1">{title}</text>
  <!-- Flow Cards -->
  {cards_markup}
  <!-- Directional Arrows -->
  <g transform="translate(405, 350)">
    <line x1="0" y1="0" x2="86" y2="0" stroke="#DE2626" stroke-width="2.5"/>
    <polygon points="84,-6 96,0 84,6" fill="#DE2626"/>
  </g>
  <g transform="translate(785, 350)">
    <line x1="0" y1="0" x2="86" y2="0" stroke="#DE2626" stroke-width="2.5"/>
    <polygon points="84,-6 96,0 84,6" fill="#DE2626"/>
  </g>
  <!-- Bottom divider -->
  <line x1="64" y1="{h-65}" x2="{w-64}" y2="{h-65}" stroke="#1C1C22" stroke-width="1"/>
  {logo}
</svg>"""


# Backwards-compatible aliases for legacy callers
render_branding_title_slide_svg = render_slide_split_visual_svg
render_branding_feature_slide_svg = render_slide_key_points_svg
render_branding_metrics_slide_svg = render_slide_visual_focus_light_svg
render_branding_summary_slide_svg = render_slide_visual_focus_dark_svg
render_branding_architecture_slide_svg = render_slide_process_flow_svg


# ---------------------------------------------------------------------------
# Playwright Browser Runner Primitives
# ---------------------------------------------------------------------------

async def _launch_browser_session():
    """
    Initializes a Playwright driver instance.
    Checks for native Termux Chromium wrapper first, then falls back to standard playwright.
    """
    try:
        from termux_playwright import async_playwright_termux, launch
        pw_context_manager = async_playwright_termux()
        is_termux = True
    except ImportError:
        from playwright.async_api import async_playwright
        pw_context_manager = async_playwright()
        is_termux = False

    return pw_context_manager, is_termux


# ---------------------------------------------------------------------------
# Single Still Frame Capture Engine
# ---------------------------------------------------------------------------

async def render_still_frame(
    width_px: int = 800,
    height_px: int = 800,
    output_path: str = "captures/still_frame.png",
    svg_markup: Optional[str] = None,
    template_name: str = "blank_slate_stage.html",
    bg_theme: str = "#000000",
    stage_selector: str = "#capture-stage",
    device_scale: int = 2,
    seek_progress: float = 0.0,
    text_overlays: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Renders a single still frame into a blank-slate canvas stage and saves it to disk.
    Injects dynamic coordinate-based text overlays pre-recording if declared in config.
    """
    out_file = Path(output_path).resolve()
    out_file.parent.mkdir(parents=True, exist_ok=True)

    stage_file = out_file.parent / f"_stage_{uuid.uuid4().hex[:8]}.html"
    instantiate_stage_file(
        output_path=stage_file,
        template_name=template_name,
        width_px=width_px,
        height_px=height_px,
        bg_theme=bg_theme,
        initial_svg_markup=svg_markup
    )

    pw_cm, is_termux = await _launch_browser_session()

    async with pw_cm as pw_driver:
        if is_termux:
            from termux_playwright import launch
            browser = await launch(pw_driver, headless=True)
        else:
            browser = await pw_driver.chromium.launch(headless=True)

        context = await browser.new_context(
            viewport={"width": width_px + 40, "height": height_px + 40},
            device_scale_factor=device_scale
        )
        page = await context.new_page()

        target_url = f"file://{stage_file.resolve()}"
        logger.info(f"Navigating to blank-slate stage: {target_url}")
        await page.goto(target_url, wait_until="domcontentloaded")

        try:
            await page.wait_for_function("window.isReadyToCapture === true", timeout=4000)
        except Exception:
            await page.wait_for_timeout(500)

        if svg_markup:
            await page.evaluate(f"window.setSvgContent({json.dumps(svg_markup)})")
            await page.wait_for_timeout(100)

        if seek_progress > 0.0:
            await page.evaluate(f"window.seekProgress && window.seekProgress({seek_progress}, 8.0)")
            await page.wait_for_timeout(100)

        # Pre-recording coordinate text overlay injection
        if text_overlays:
            ctx = {"frame": 0, "time": 0.0, "fps": 30, "caption": "Still Capture"}
            await page.evaluate(f"window.setTextOverlays({json.dumps(text_overlays)}, {json.dumps(ctx)})")
            await page.wait_for_timeout(80)

        stage_elem = await page.query_selector(stage_selector)
        target = stage_elem if stage_elem else page

        await target.screenshot(path=str(out_file))
        await browser.close()

    if stage_file.exists():
        try:
            stage_file.unlink()
        except OSError:
            pass

    file_bytes = out_file.read_bytes()
    sha256 = hashlib.sha256(file_bytes).hexdigest()
    logger.info(f"Rendered still frame: {out_file} ({len(file_bytes)} bytes, sha: {sha256[:8]})")

    return {
        "status": "success",
        "output_file": str(out_file),
        "bytes": len(file_bytes),
        "sha256": sha256
    }


# ---------------------------------------------------------------------------
# Row-Per-Frame Animation Engine
# ---------------------------------------------------------------------------

async def render_row_per_frame_animation(
    animation_doc: Dict[str, Any],
    output_dir: str = "captures/animation_frames",
    save_updated_doc: bool = True,
    device_scale: int = 2,
    stage_config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Renders every frame declared in a BEJSON 105a Row-Per-Frame Animation document.
    Iterates over each row in `Values`, injects dynamic SVG or timeline seek into
    the blank slate canvas, applies X,Y coordinate-based text overlays pre-recording,
    writes the frame file, computes SHA-256 hash, and records completion telemetry
    back into the BEJSON 105a document.
    """
    is_valid, errors = validate_graphic_105a_doc(animation_doc)
    if not is_valid:
        raise ValueError(f"Invalid BEJSON 105a animation document: {errors}")

    fields = animation_doc.get("Fields", [])
    fmap = build_field_map_105(fields)
    values = animation_doc.get("Values", [])

    width_px = int(animation_doc.get("Width_Px", 800))
    height_px = int(animation_doc.get("Height_Px", 800))
    anim_name = animation_doc.get("Animation_Name", "animation")
    duration_sec = float(animation_doc.get("Duration_Sec", 8.0))
    fps = int(animation_doc.get("FPS", 30))

    # Resolve active text overlays from stage config or document header
    text_overlays: List[Dict[str, Any]] = []
    if stage_config:
        raw_ov = stage_config.get("text_overlays") or stage_config.get("text_overlays_json")
        if isinstance(raw_ov, list):
            text_overlays = raw_ov
        elif isinstance(raw_ov, str):
            try:
                text_overlays = json.loads(raw_ov)
            except Exception:
                pass
    elif "Text_Overlays" in animation_doc:
        raw_ov = animation_doc["Text_Overlays"]
        text_overlays = raw_ov if isinstance(raw_ov, list) else json.loads(raw_ov)

    out_path = Path(output_dir).resolve()
    out_path.mkdir(parents=True, exist_ok=True)

    stage_file = out_path / f"_stage_{uuid.uuid4().hex[:8]}.html"
    instantiate_stage_file(
        output_path=stage_file,
        template_name="blank_slate_stage.html",
        width_px=width_px,
        height_px=height_px,
        bg_theme="#000000"
    )

    pw_cm, is_termux = await _launch_browser_session()

    rendered_count = 0
    total_bytes = 0

    async with pw_cm as pw_driver:
        if is_termux:
            from termux_playwright import launch
            browser = await launch(pw_driver, headless=True)
        else:
            browser = await pw_driver.chromium.launch(headless=True)

        context = await browser.new_context(
            viewport={"width": width_px + 40, "height": height_px + 40},
            device_scale_factor=device_scale
        )
        page = await context.new_page()

        target_url = f"file://{stage_file.resolve()}"
        logger.info(f"Navigating to blank-slate stage for {len(values)} frames: {target_url}")
        await page.goto(target_url, wait_until="domcontentloaded")

        try:
            await page.wait_for_function("window.isReadyToCapture === true", timeout=4000)
        except Exception:
            await page.wait_for_timeout(500)

        stage_elem = await page.query_selector("#capture-stage")
        target = stage_elem if stage_elem else page

        for row in values:
            f_idx = row[fmap["frame_index"]]
            ts = row[fmap["timestamp_sec"]]
            seek = row[fmap["seek_progress"]]
            filename = row[fmap["frame_filename"]]
            svg_markup = row[fmap["svg_markup"]]
            frame_file = out_path / filename

            # 1. Update dynamic SVG content if declared per frame
            if svg_markup:
                await page.evaluate(f"window.setSvgContent({json.dumps(svg_markup)})")
                await page.wait_for_timeout(60)
            elif seek is not None:
                # 2. Or seek CSS animation progress
                await page.evaluate(f"window.seekProgress && window.seekProgress({seek}, {duration_sec})")
                await page.wait_for_timeout(60)

            # 3. Pre-recording coordinate text overlay injection
            if text_overlays:
                frame_ctx = {
                    "frame": f_idx,
                    "time": ts,
                    "fps": fps,
                    "seek": seek
                }
                raw_fdata = row[fmap["frame_data_json"]]
                if raw_fdata:
                    try:
                        frame_ctx.update(json.loads(raw_fdata))
                    except Exception:
                        pass
                await page.evaluate(f"window.setTextOverlays({json.dumps(text_overlays)}, {json.dumps(frame_ctx)})")
                await page.wait_for_timeout(40)

            # 4. Capture frame screenshot
            await target.screenshot(path=str(frame_file))

            # 5. Hash and record
            f_bytes = frame_file.read_bytes()
            f_hash = hashlib.sha256(f_bytes).hexdigest()

            row[fmap["is_rendered"]] = True
            row[fmap["checksum_sha256"]] = f_hash

            rendered_count += 1
            total_bytes += len(f_bytes)

            if rendered_count % 10 == 0 or rendered_count == len(values):
                logger.info(f"Rendered frame {rendered_count}/{len(values)}: {filename} (sha: {f_hash[:8]})")

        await browser.close()

    if stage_file.exists():
        try:
            stage_file.unlink()
        except OSError:
            pass

    # Save updated BEJSON 105a document with checksums
    updated_doc_path = None
    if save_updated_doc:
        updated_doc_path = out_path / f"{anim_name}_rendered.105a.bejson"
        updated_doc_path.write_text(json.dumps(animation_doc, indent=2), encoding="utf-8")
        logger.info(f"Saved completed BEJSON 105a animation ledger: {updated_doc_path}")

    return {
        "status": "success",
        "animation_name": anim_name,
        "total_rendered": rendered_count,
        "total_bytes": total_bytes,
        "output_dir": str(out_path),
        "ledger_file": str(updated_doc_path) if updated_doc_path else None
    }


# ---------------------------------------------------------------------------
# Animated SVG Compiler
# ---------------------------------------------------------------------------

def compile_row_per_frame_to_animated_svg(
    animation_doc: Dict[str, Any],
    output_svg_path: str
) -> str:
    """
    Compiles an animated SVG document using SMIL keyframes from a row-per-frame document.
    """
    fields = animation_doc.get("Fields", [])
    fmap = build_field_map_105(fields)
    values = animation_doc.get("Values", [])

    width_px = int(animation_doc.get("Width_Px", 800))
    height_px = int(animation_doc.get("Height_Px", 800))
    duration_sec = float(animation_doc.get("Duration_Sec", 8.0))

    out_file = Path(output_svg_path).resolve()
    out_file.parent.mkdir(parents=True, exist_ok=True)

    svg_frames_content: List[str] = []
    frame_dur = duration_sec / max(1, len(values))

    for idx, row in enumerate(values):
        markup = row[fmap["svg_markup"]] or ""
        # Wrap each frame in a group with timed visibility
        svg_frames_content.append(
            f'  <g id="frame-{idx}" display="none">\n'
            f'    {markup}\n'
            f'    <set attributeName="display" to="inline" begin="{idx * frame_dur:.3f}s" dur="{frame_dur:.3f}s" />\n'
            f'  </g>'
        )

    composite_svg = (
        f'<svg viewBox="0 0 {width_px} {height_px}" width="{width_px}" height="{height_px}" '
        f'xmlns="http://www.w3.org/2000/svg">\n'
        f'  <!-- Animated Composite SVG compiled from BEJSON 105a Row-Per-Frame Animation -->\n'
        + "\n".join(svg_frames_content) + "\n</svg>\n"
    )

    out_file.write_text(composite_svg, encoding="utf-8")
    logger.info(f"Compiled animated SVG to: {out_file} ({len(composite_svg)} bytes)")
    return str(out_file)


# ---------------------------------------------------------------------------
# Multi-Format Video, GIF, WebM & APNG Exporters
# ---------------------------------------------------------------------------

def _prune_frame_sources(frames_dir_or_list: Any) -> int:
    """Removes transient frame source images (.png, .svg) after final output compilation."""
    removed_count = 0
    if isinstance(frames_dir_or_list, (str, Path)) and Path(frames_dir_or_list).is_dir():
        f_dir = Path(frames_dir_or_list).resolve()
        for pattern in ("*.png", "*.svg"):
            for frame_file in f_dir.glob(pattern):
                try:
                    frame_file.unlink()
                    removed_count += 1
                except Exception as exc:
                    logger.debug(f"Failed to remove frame {frame_file}: {exc}")
    elif isinstance(frames_dir_or_list, list):
        for f_path in frames_dir_or_list:
            p = Path(f_path)
            if p.exists() and p.is_file():
                try:
                    p.unlink()
                    removed_count += 1
                except Exception as exc:
                    logger.debug(f"Failed to remove frame {p}: {exc}")
    logger.info(f"Removed {removed_count} frame source files (remove_frame_source=True)")
    return removed_count


def compile_frames_to_gif(
    frames_dir_or_list: Any,
    output_gif_path: str,
    fps: int = 24,
    loop: int = 0,
    remove_frame_source: bool = False
) -> str:
    """
    Compiles a directory or list of PNG frame images into an optimized animated GIF.
    Uses ffmpeg with 2-pass palettegen when available; falls back to Pillow.
    If remove_frame_source is True, transient frame source files are deleted after compilation.
    """
    out_file = Path(output_gif_path).resolve()
    out_file.parent.mkdir(parents=True, exist_ok=True)

    # 1. Try ffmpeg 2-pass palettegen if directory is provided and ffmpeg exists
    ffmpeg_bin = shutil.which("ffmpeg")
    if ffmpeg_bin and isinstance(frames_dir_or_list, (str, Path)) and Path(frames_dir_or_list).is_dir():
        f_dir = Path(frames_dir_or_list).resolve()
        png_files = sorted(f_dir.glob("*.png"))
        if png_files:
            cmd = [
                ffmpeg_bin, "-y",
                "-framerate", str(fps),
                "-pattern_type", "glob",
                "-i", str(f_dir / "*.png"),
                "-filter_complex", f"fps={fps},split[s0][s1];[s0]palettegen=max_colors=128[p];[s1][p]paletteuse=dither=bayer",
                str(out_file)
            ]
            try:
                res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if res.returncode == 0 and out_file.exists():
                    logger.info(f"Compiled GIF via ffmpeg: {out_file} ({out_file.stat().st_size} bytes)")
                    if remove_frame_source:
                        _prune_frame_sources(frames_dir_or_list)
                    return str(out_file)
            except Exception as exc:
                logger.warning(f"ffmpeg GIF compilation fallback: {exc}")

    # 2. Pure Python Pillow Fallback
    try:
        from PIL import Image
        frame_paths: List[Path] = []
        if isinstance(frames_dir_or_list, (str, Path)) and Path(frames_dir_or_list).is_dir():
            frame_paths = sorted(Path(frames_dir_or_list).glob("*.png"))
        elif isinstance(frames_dir_or_list, list):
            frame_paths = [Path(p) for p in frames_dir_or_list]

        if not frame_paths:
            raise FileNotFoundError("No frames found to compile into GIF")

        images = [Image.open(p) for p in frame_paths]
        duration_ms = int(1000.0 / max(1, fps))
        images[0].save(
            out_file,
            save_all=True,
            append_images=images[1:],
            duration=duration_ms,
            loop=loop,
            optimize=True
        )
        logger.info(f"Compiled GIF via Pillow: {out_file} ({out_file.stat().st_size} bytes, {len(images)} frames)")
        if remove_frame_source:
            _prune_frame_sources(frames_dir_or_list)
        return str(out_file)
    except Exception as exc:
        logger.error(f"Failed to compile GIF: {exc}")
        raise


def _resolve_slides_and_durations(
    frames_dir_or_slides: Any,
    default_dwell_sec: Optional[float] = None,
    default_fps: int = 24
) -> Tuple[List[Tuple[Path, float]], bool]:
    """
    Normalizes inputs into a list of (image_path, duration_sec) tuples.
    Returns (tuples_list, is_slide_dwell_mode).
    """
    doc = None
    base_dir = Path.cwd()
    if isinstance(frames_dir_or_slides, (str, Path)):
        p = Path(frames_dir_or_slides).resolve()
        if p.is_file() and p.suffix.lower() == ".bejson":
            base_dir = p.parent
            with open(p, "r", encoding="utf-8") as f:
                doc = json.load(f)
    elif isinstance(frames_dir_or_slides, dict) and "Values" in frames_dir_or_slides:
        doc = frames_dir_or_slides

    if doc is not None:
        f_map = build_field_map_105(doc)
        tuples = []
        for r in doc.get("Values", []):
            fn = None
            for key in ("slide_filename", "frame_filename"):
                if key in f_map and f_map[key] < len(r):
                    fn = r[f_map[key]]
                    if fn:
                        break

            dur = None
            if default_dwell_sec is not None:
                dur = float(default_dwell_sec)
            elif "duration_sec" in f_map and f_map["duration_sec"] < len(r) and r[f_map["duration_sec"]] is not None:
                dur = float(r[f_map["duration_sec"]])
            elif "frame_duration_ms" in f_map and f_map["frame_duration_ms"] < len(r) and r[f_map["frame_duration_ms"]] is not None:
                dur = float(r[f_map["frame_duration_ms"]]) / 1000.0
            else:
                dur = 1.0 / max(1, default_fps)

            if fn:
                img_path = base_dir / fn
                if img_path.suffix.lower() == ".svg":
                    png_alt = img_path.with_suffix(".png")
                    if png_alt.exists():
                        img_path = png_alt
                tuples.append((img_path, dur))
        return tuples, True

    if isinstance(frames_dir_or_slides, (str, Path)) and Path(frames_dir_or_slides).is_dir():
        f_dir = Path(frames_dir_or_slides).resolve()
        if default_dwell_sec is not None:
            png_files = sorted(f_dir.glob("*.png"))
            return [(p, float(default_dwell_sec)) for p in png_files], True
        else:
            return [], False

    if isinstance(frames_dir_or_slides, list):
        tuples = []
        for item in frames_dir_or_slides:
            if isinstance(item, tuple) and len(item) == 2:
                p, d = item
                tuples.append((Path(p).resolve(), float(d)))
            else:
                dur = float(default_dwell_sec) if default_dwell_sec is not None else (1.0 / max(1, default_fps))
                tuples.append((Path(item).resolve(), dur))
        return tuples, True

    return [], False


def compile_frames_to_webm(
    frames_dir_or_slides: Any,
    output_webm_path: str,
    fps: int = 24,
    crf: int = 28,
    dwell_sec: Optional[float] = None,
    cpu_used: int = 4,
    deadline: str = "realtime",
    remove_frame_source: bool = False
) -> str:
    """
    Compiles rendered PNG frames or slide sequences into an optimized WebM (VP9) video using ffmpeg.
    Supports custom slide dwell durations (e.g., 4s, 8s, 12s per slide).
    """
    out_file = Path(output_webm_path).resolve()
    out_file.parent.mkdir(parents=True, exist_ok=True)

    ffmpeg_bin = shutil.which("ffmpeg")
    if not ffmpeg_bin:
        raise RuntimeError("ffmpeg is required to compile WebM video")

    slide_tuples, is_dwell_mode = _resolve_slides_and_durations(frames_dir_or_slides, dwell_sec, fps)

    if is_dwell_mode:
        if not slide_tuples:
            raise FileNotFoundError("No slide frames found for WebM compilation")

        cmd = [ffmpeg_bin, "-y"]
        filter_inputs = []
        for idx, (p, dur) in enumerate(slide_tuples):
            cmd.extend(["-loop", "1", "-t", f"{dur:.3f}", "-i", str(p)])
            filter_inputs.append(f"[{idx}:v]")

        filter_complex = f"{''.join(filter_inputs)}concat=n={len(slide_tuples)}:v=1:a=0[v]"
        cmd.extend([
            "-filter_complex", filter_complex,
            "-map", "[v]",
            "-c:v", "libvpx-vp9",
            "-deadline", deadline,
            "-cpu-used", str(cpu_used),
            "-row-mt", "1",
            "-pix_fmt", "yuv420p",
            "-b:v", "0",
            "-crf", str(crf),
            "-r", str(fps),
            str(out_file)
        ])
    else:
        f_dir = Path(frames_dir_or_slides).resolve()
        cmd = [
            ffmpeg_bin, "-y",
            "-framerate", str(fps),
            "-pattern_type", "glob",
            "-i", str(f_dir / "*.png"),
            "-c:v", "libvpx-vp9",
            "-deadline", deadline,
            "-cpu-used", str(cpu_used),
            "-row-mt", "1",
            "-pix_fmt", "yuv420p",
            "-b:v", "0",
            "-crf", str(crf),
            str(out_file)
        ]

    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"ffmpeg WebM compilation failed: {res.stderr}")

    logger.info(f"Compiled WebM video: {out_file} ({out_file.stat().st_size} bytes)")
    if remove_frame_source:
        if is_dwell_mode:
            for p, _ in slide_tuples:
                if p.exists():
                    try:
                        p.unlink()
                    except Exception as exc:
                        logger.warning(f"Failed to remove frame source {p}: {exc}")
        else:
            _prune_frame_sources(frames_dir_or_slides)
    return str(out_file)


def compile_frames_to_apng(
    frames_dir: str,
    output_apng_path: str,
    fps: int = 24
) -> str:
    """
    Compiles rendered frames into an Animated PNG (APNG) file.
    """
    out_file = Path(output_apng_path).resolve()
    out_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        from PIL import Image
        f_dir = Path(frames_dir).resolve()
        frame_paths = sorted(f_dir.glob("*.png"))
        if not frame_paths:
            raise FileNotFoundError("No frames found to compile APNG")

        images = [Image.open(p) for p in frame_paths]
        duration_ms = int(1000.0 / max(1, fps))
        images[0].save(
            out_file,
            format="PNG",
            save_all=True,
            append_images=images[1:],
            duration=duration_ms,
            loop=0
        )
        logger.info(f"Compiled APNG: {out_file} ({out_file.stat().st_size} bytes)")
        return str(out_file)
    except Exception as exc:
        logger.error(f"APNG compilation failed: {exc}")
        raise


def compile_frames_to_mp4(
    frames_dir_or_slides: Any,
    output_mp4_path: str,
    fps: int = 24,
    dwell_sec: Optional[float] = None,
    preset: str = "veryfast",
    remove_frame_source: bool = False
) -> str:
    """
    Compiles rendered PNG frames or slide sequences into an H.264 MP4 video using ffmpeg.
    Supports custom slide dwell durations (e.g., 4s, 8s, 12s per slide).
    """
    out_file = Path(output_mp4_path).resolve()
    out_file.parent.mkdir(parents=True, exist_ok=True)

    ffmpeg_bin = shutil.which("ffmpeg")
    if not ffmpeg_bin:
        raise RuntimeError("ffmpeg is required to compile MP4 video")

    slide_tuples, is_dwell_mode = _resolve_slides_and_durations(frames_dir_or_slides, dwell_sec, fps)

    if is_dwell_mode:
        if not slide_tuples:
            raise FileNotFoundError("No slide frames found for MP4 compilation")

        cmd = [ffmpeg_bin, "-y"]
        filter_inputs = []
        for idx, (p, dur) in enumerate(slide_tuples):
            cmd.extend(["-loop", "1", "-t", f"{dur:.3f}", "-i", str(p)])
            filter_inputs.append(f"[{idx}:v]")

        filter_complex = f"{''.join(filter_inputs)}concat=n={len(slide_tuples)}:v=1:a=0[v]"
        cmd.extend([
            "-filter_complex", filter_complex,
            "-map", "[v]",
            "-c:v", "libx264",
            "-preset", preset,
            "-pix_fmt", "yuv420p",
            "-r", str(fps),
            str(out_file)
        ])
    else:
        f_dir = Path(frames_dir_or_slides).resolve()
        cmd = [
            ffmpeg_bin, "-y",
            "-framerate", str(fps),
            "-pattern_type", "glob",
            "-i", str(f_dir / "*.png"),
            "-c:v", "libx264",
            "-preset", preset,
            "-pix_fmt", "yuv420p",
            str(out_file)
        ]

    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"ffmpeg MP4 compilation failed: {res.stderr}")

    logger.info(f"Compiled MP4 video: {out_file} ({out_file.stat().st_size} bytes)")
    if remove_frame_source:
        if is_dwell_mode:
            for p, _ in slide_tuples:
                if p.exists():
                    try:
                        p.unlink()
                    except Exception as exc:
                        logger.warning(f"Failed to remove frame source {p}: {exc}")
        else:
            _prune_frame_sources(frames_dir_or_slides)
    return str(out_file)


async def async_compile_presentation_slides_to_video(
    slide_deck_or_path: Any,
    output_video_path: str,
    dwell_sec: Optional[float] = 4.0,
    fps: int = 24,
    video_format: str = "mp4",
    crf: int = 28,
    preset: str = "veryfast",
    remove_frame_source: bool = False
) -> str:
    """
    Renders presentation slide SVGs via Playwright (if PNGs do not yet exist)
    and compiles them into an MP4 or WebM video demo reel honoring dwell duration.
    """
    from termux_playwright import async_playwright_termux, launch

    doc = None
    base_dir = Path.cwd()
    if isinstance(slide_deck_or_path, (str, Path)):
        p = Path(slide_deck_or_path).resolve()
        base_dir = p.parent
        with open(p, "r", encoding="utf-8") as f:
            doc = json.load(f)
    elif isinstance(slide_deck_or_path, dict):
        doc = slide_deck_or_path
    else:
        raise ValueError("slide_deck_or_path must be a file path or dict")

    f_map = build_field_map_105(doc)
    w = doc.get("Canvas_Width_Px") or doc.get("Width_Px") or 1280
    h = doc.get("Canvas_Height_Px") or doc.get("Height_Px") or 720

    slide_records = []
    for r in doc.get("Values", []):
        fn = r[f_map.get("slide_filename", 9)] if "slide_filename" in f_map else None
        svg_markup = r[f_map.get("svg_markup", 8)] if "svg_markup" in f_map else None
        dur = dwell_sec if dwell_sec is not None else float(r[f_map.get("duration_sec", 4)] or 4.0)
        slide_records.append({"filename": fn, "svg": svg_markup, "duration": dur})

    # Render SVGs to PNGs if needed
    rendered_tuples = []
    async with async_playwright_termux() as pw:
        browser = await launch(pw, headless=True)
        page = await browser.new_page(viewport={"width": w, "height": h}, device_scale_factor=1)

        for idx, srec in enumerate(slide_records):
            fn = srec["filename"]
            svg_content = srec["svg"]
            dur = srec["duration"]

            png_path = None
            if fn:
                candidate = base_dir / fn
                if candidate.suffix.lower() == ".png" and candidate.exists():
                    png_path = candidate
                elif candidate.suffix.lower() == ".svg":
                    png_alt = candidate.with_suffix(".png")
                    if png_alt.exists():
                        png_path = png_alt
                    elif not svg_content and candidate.exists():
                        svg_content = candidate.read_text(encoding="utf-8")

            if png_path is None:
                png_path = base_dir / f"slide_{idx:04d}.png"
                html = f"<!DOCTYPE html><html><head><style>html,body{{margin:0;padding:0;width:{w}px;height:{h}px;background:#000000;overflow:hidden;}}svg{{width:100%;height:100%;display:block;}}</style></head><body>{svg_content}</body></html>"
                tmp_html = base_dir / f"_tmp_render_{idx:04d}.html"
                tmp_html.write_text(html, encoding="utf-8")
                await page.goto(f"file://{tmp_html.resolve()}")
                buf = await page.screenshot()
                tmp_html.unlink()
                png_path.write_bytes(buf)

            rendered_tuples.append((png_path, dur))

        await browser.close()

    v_fmt = video_format.lower()
    if v_fmt in ("webm", ".webm"):
        return compile_frames_to_webm(
            rendered_tuples,
            output_video_path,
            fps=fps,
            crf=crf,
            remove_frame_source=remove_frame_source
        )
    else:
        return compile_frames_to_mp4(
            rendered_tuples,
            output_video_path,
            fps=fps,
            preset=preset,
            remove_frame_source=remove_frame_source
        )


def compile_presentation_slides_to_video(
    slide_deck_or_path: Any,
    output_video_path: str,
    dwell_sec: Optional[float] = 4.0,
    fps: int = 24,
    video_format: str = "mp4",
    crf: int = 28,
    preset: str = "veryfast",
    remove_frame_source: bool = False
) -> str:
    """Synchronous wrapper for async_compile_presentation_slides_to_video."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(
                asyncio.run,
                async_compile_presentation_slides_to_video(
                    slide_deck_or_path=slide_deck_or_path,
                    output_video_path=output_video_path,
                    dwell_sec=dwell_sec,
                    fps=fps,
                    video_format=video_format,
                    crf=crf,
                    preset=preset,
                    remove_frame_source=remove_frame_source
                )
            ).result()
    else:
        return asyncio.run(
            async_compile_presentation_slides_to_video(
                slide_deck_or_path=slide_deck_or_path,
                output_video_path=output_video_path,
                dwell_sec=dwell_sec,
                fps=fps,
                video_format=video_format,
                crf=crf,
                preset=preset,
                remove_frame_source=remove_frame_source
            )
        )


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="BEJSON 105a Graphics Playwright Animation & Canvas Core")
    parser.add_argument("--still", action="store_true", help="Render a single still frame capture")
    parser.add_argument("--row-animation", action="store_true", help="Create and render a row-per-frame animation")
    parser.add_argument("--slideshow", action="store_true", help="Create and render a dynamic slideshow animation")
    parser.add_argument("--diagram", type=str, help="Path to BEJSON diagram JSON file to render into canvas")
    parser.add_argument("--name", type=str, default="pulse_cube_anim", help="Animation or stage identifier")
    parser.add_argument("--width", type=int, default=800, help="Canvas width in pixels")
    parser.add_argument("--height", type=int, default=800, help="Canvas height in pixels")
    parser.add_argument("--duration", type=float, default=4.0, help="Duration in seconds")
    parser.add_argument("--fps", type=int, default=30, help="Frames per second")
    parser.add_argument("--output", "-o", type=str, default="captures/frame.png", help="Output path")
    parser.add_argument("--export-gif", action="store_true", help="Compile rendered frames into an animated GIF")
    parser.add_argument("--export-webm", action="store_true", help="Compile rendered frames into WebM video")
    parser.add_argument("--export-apng", action="store_true", help="Compile rendered frames into Animated PNG")
    parser.add_argument("--export-mp4", action="store_true", help="Compile rendered frames into MP4 video")
    parser.add_argument("--list-templates", action="store_true", help="List registered canvas blank-slate templates")
    parser.add_argument("--version", action="version", version=f"lib_bejson_Graphics_graphics_core v{VERSION}")

    args = parser.parse_args()

    if args.list_templates:
        catalog = list_registered_templates()
        print(f"\nRegistered Canvas Blank-Slate Templates ({len(catalog)} total):\n" + "=" * 70)
        for t in catalog:
            print(f"- {t['template_name']:<36} | {t['width_px']}x{t['height_px']} | {t['category']:<18}")
            print(f"  {t['description']}")
        return

    # Diagram Processing Path
    if args.diagram:
        try:
            from lib_bejson_Graphics_graphics_diagram_loader import (
                render_diagram_svg,
                create_diagram_frame_sequence_105a
            )
        except ImportError:
            from lib_bejson_Graphics_diagram_loader import (
                render_diagram_svg,
                create_diagram_frame_sequence_105a
            )
        diag_path = Path(args.diagram)
        if not diag_path.exists():
            print(f"Error: Diagram file not found: {diag_path}")
            sys.exit(1)
        diag_data = json.loads(diag_path.read_text(encoding="utf-8"))

        if args.row_animation:
            # Build automated walkthrough states from shapes
            shapes = diag_data.get("shapes", [])
            states = [
                {"name": "Overview", "active_shapes": [], "viewport": {"fit_view": True}, "badge_text": f"{diag_data.get('name', 'Architecture')} Overview"}
            ]
            for s in shapes:
                sid = s.get("id") or s.get("tempId")
                slabel = s.get("label", sid)
                states.append({
                    "name": f"Focus: {slabel}",
                    "active_shapes": [sid],
                    "inspector_shape": sid,
                    "viewport": {"focus_shape": sid, "zoom": 1.3},
                    "badge_text": f"Inspecting: {slabel}"
                })
            states.append({
                "name": "Complete Flow",
                "active_shapes": [s.get("id") or s.get("tempId") for s in shapes],
                "viewport": {"fit_view": True},
                "badge_text": "Complete System Flow Active"
            })

            anim_doc = create_diagram_frame_sequence_105a(
                diagram=diag_data,
                states_sequence=states,
                animation_name=args.name,
                fps=args.fps,
                canvas_w=args.width,
                canvas_h=args.height
            )

            out_dir = f"captures/{args.name}"
            res = asyncio.run(render_row_per_frame_animation(
                animation_doc=anim_doc,
                output_dir=out_dir
            ))
            print(f"Diagram walkthrough rendered: {res['total_rendered']} frames into {res['output_dir']}")

            if args.export_gif:
                gif_p = compile_frames_to_gif(out_dir, f"{out_dir}/{args.name}.gif", fps=args.fps)
                print(f"Exported GIF: {gif_p}")
            if args.export_webm:
                webm_p = compile_frames_to_webm(out_dir, f"{out_dir}/{args.name}.webm", fps=args.fps)
                print(f"Exported WebM: {webm_p}")
            if args.export_apng:
                apng_p = compile_frames_to_apng(out_dir, f"{out_dir}/{args.name}.png", fps=args.fps)
                print(f"Exported APNG: {apng_p}")
            if args.export_mp4:
                mp4_p = compile_frames_to_mp4(out_dir, f"{out_dir}/{args.name}.mp4", fps=args.fps)
                print(f"Exported MP4: {mp4_p}")
            return

        # Single still capture of diagram
        diag_svg = render_diagram_svg(
            diagram=diag_data,
            state={"active_shapes": [s.get("id") or s.get("tempId") for s in diag_data.get("shapes", [])[:2]], "badge_text": diag_data.get("name")},
            viewport={"fit_view": True},
            canvas_w=args.width,
            canvas_h=args.height
        )
        res = asyncio.run(render_still_frame(
            width_px=args.width,
            height_px=args.height,
            output_path=args.output,
            svg_markup=diag_svg
        ))
        print(f"Diagram still frame captured: {res['output_file']} ({res['bytes']} bytes)")
        return

    if args.still:
        # Generate sample isometric cube SVG
        svg = create_isometric_cube_svg(viewbox_size=args.width, cube_style="104a_floating", pulse_intensity=1.0)
        res = asyncio.run(render_still_frame(
            width_px=args.width,
            height_px=args.height,
            output_path=args.output,
            svg_markup=svg
        ))
        print(f"Still frame captured: {res['output_file']} ({res['bytes']} bytes)")
        return

    if args.slideshow:
        from lib_bejson_Graphics_graphics_schemas import create_slideshow_animation_105a
        # Generate 3 sample slides
        slides = [
            {
                "svg_markup": create_isometric_cube_svg(viewbox_size=args.width, cube_style="104"),
                "duration_sec": 2.0,
                "caption": "Slide 1: BEJSON 104 Standard Cube"
            },
            {
                "svg_markup": create_isometric_cube_svg(viewbox_size=args.width, cube_style="104a_floating"),
                "duration_sec": 2.0,
                "caption": "Slide 2: BEJSON 104a Floating Cube"
            },
            {
                "svg_markup": create_isometric_cube_svg(viewbox_size=args.width, cube_style="104a_floating", pulse_intensity=1.4),
                "duration_sec": 2.0,
                "caption": "Slide 3: BEJSON 104a Pulse Core"
            }
        ]

        doc = create_slideshow_animation_105a(
            slideshow_name=args.name,
            slides=slides,
            fps=args.fps,
            width_px=args.width,
            height_px=args.height
        )

        out_dir = f"captures/{args.name}"
        res = asyncio.run(render_row_per_frame_animation(
            animation_doc=doc,
            output_dir=out_dir
        ))
        print(f"Slideshow rendered: {res['total_rendered']} frames into {res['output_dir']}")

        if args.export_gif:
            gif_p = compile_frames_to_gif(out_dir, f"{out_dir}/{args.name}.gif", fps=args.fps)
            print(f"Exported GIF: {gif_p}")
        if args.export_webm:
            webm_p = compile_frames_to_webm(out_dir, f"{out_dir}/{args.name}.webm", fps=args.fps)
            print(f"Exported WebM: {webm_p}")
        if args.export_apng:
            apng_p = compile_frames_to_apng(out_dir, f"{out_dir}/{args.name}.png", fps=args.fps)
            print(f"Exported APNG: {apng_p}")
        if args.export_mp4:
            mp4_p = compile_frames_to_mp4(out_dir, f"{out_dir}/{args.name}.mp4", fps=args.fps)
            print(f"Exported MP4: {mp4_p}")
        return

    if args.row_animation:
        # Build dynamic frame data
        total_frames = max(1, int(math.ceil(args.duration * args.fps)))
        dynamic_frames = []
        for i in range(total_frames):
            pulse = 1.0 + 0.3 * math.sin(2 * math.pi * (i / total_frames))
            f_svg = create_isometric_cube_svg(viewbox_size=args.width, cube_style="104a_floating", pulse_intensity=pulse)
            dynamic_frames.append({"svg_markup": f_svg, "data": {"pulse": pulse}})

        doc = create_row_per_frame_animation_105a(
            animation_name=args.name,
            duration_sec=args.duration,
            fps=args.fps,
            width_px=args.width,
            height_px=args.height,
            dynamic_frames=dynamic_frames
        )

        out_dir = f"captures/{args.name}"
        res = asyncio.run(render_row_per_frame_animation(
            animation_doc=doc,
            output_dir=out_dir
        ))
        print(f"Animation rendered: {res['total_rendered']} frames into {res['output_dir']}")

        if args.export_gif:
            gif_p = compile_frames_to_gif(out_dir, f"{out_dir}/{args.name}.gif", fps=args.fps)
            print(f"Exported GIF: {gif_p}")
        if args.export_webm:
            webm_p = compile_frames_to_webm(out_dir, f"{out_dir}/{args.name}.webm", fps=args.fps)
            print(f"Exported WebM: {webm_p}")
        if args.export_apng:
            apng_p = compile_frames_to_apng(out_dir, f"{out_dir}/{args.name}.png", fps=args.fps)
            print(f"Exported APNG: {apng_p}")
        if args.export_mp4:
            mp4_p = compile_frames_to_mp4(out_dir, f"{out_dir}/{args.name}.mp4", fps=args.fps)
            print(f"Exported MP4: {mp4_p}")
        return

    parser.print_help()


if __name__ == "__main__":
    main()

