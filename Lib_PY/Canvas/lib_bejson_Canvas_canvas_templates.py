"""
Library:        lib_bejson_Canvas_canvas_templates.py
Family:         Canvas
Description:    Fixed-Size Canvas and Seamless Texture Tile Template Manager for
                SVG Animations and Deterministic Playwright Screenshot Captures.
BEJSON:         BEJSON stands for BOEHNEN ELTON JSON. Authoritative definition;
                do not restate or reinterpret this acronym elsewhere.
MFDB:           MFDB stands for Multi File Database. Authoritative definition;
                do not restate or reinterpret this acronym elsewhere.
Version:        1.0.0
Date:           2026-10-25
Author:         Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
RELATIONAL_ID:  9c4a8b1d-2e3f-4a5b-b789-0c1d2e3f4a5b
Release_Version: 300
"""

from __future__ import annotations

import logging
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
for _fam in ('Core', 'Taxonomies', 'Tax_Scaffolds', 'Canvas'):
    _p = os.path.normpath(os.path.join(_HERE, "..", _fam))
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

logger = logging.getLogger("lib_bejson_Canvas_canvas_templates")
VERSION = "1.0.0"

# Standard repository and system search paths for templates
TEMPLATE_ROOT_CANDIDATES: List[Path] = [
    Path("/storage/emulated/0/Admin/Dev/Templates/Canvas_SVG_Capture_Templates"),
    Path("/storage/emulated/0/Admin/Dev/Skills/agy-consolidated/playwright-termux-automation/assets/canvas_templates"),
    Path.home() / ".gemini/config/skills/canvas-animation-studio/assets/canvas_templates",
    Path(_HERE) / "templates"
]

CANVAS_TEMPLATE_CATALOG: Dict[str, Dict[str, Any]] = {
    "template_square_800x800.html": {
        "name": "template_square_800x800.html",
        "category": "fixed_stage",
        "width_px": 800,
        "height_px": 800,
        "aspect_ratio": "1:1",
        "selector": "#capture-stage",
        "motif": "Isometric 3D cube matrix, rotating reticle rings, telemetry HUD",
        "default_duration_sec": 8.0,
        "bg_theme": "#000000"
    },
    "template_banner_840x420.html": {
        "name": "template_banner_840x420.html",
        "category": "fixed_stage",
        "width_px": 840,
        "height_px": 420,
        "aspect_ratio": "2:1",
        "selector": "#capture-stage",
        "motif": "8-lane production grid, scanning data waves, 420p downscale target",
        "default_duration_sec": 6.0,
        "bg_theme": "#000000"
    },
    "template_widescreen_1280x720.html": {
        "name": "template_widescreen_1280x720.html",
        "category": "fixed_stage",
        "width_px": 1280,
        "height_px": 720,
        "aspect_ratio": "16:9",
        "selector": "#capture-stage",
        "motif": "6-Tier Layered Architecture visual matrix, bus lines, pulse nodes",
        "default_duration_sec": 10.0,
        "bg_theme": "#000000"
    },
    "template_portrait_720x1280.html": {
        "name": "template_portrait_720x1280.html",
        "category": "fixed_stage",
        "width_px": 720,
        "height_px": 1280,
        "aspect_ratio": "9:16",
        "selector": "#capture-stage",
        "motif": "Vertical telemetry rail, waterfall stream, stacked layer status cards",
        "default_duration_sec": 8.0,
        "bg_theme": "#000000"
    },
    "template_universal_stage.html": {
        "name": "template_universal_stage.html",
        "category": "dynamic_stage",
        "width_px": 800,
        "height_px": 800,
        "aspect_ratio": "dynamic",
        "selector": "#capture-stage",
        "motif": "Parameterized dynamic stage with query parameter controls (?size=, ?bg=, ?svg=)",
        "default_duration_sec": 8.0,
        "bg_theme": "#000000"
    },
    "template_texture_isometric_cube.html": {
        "name": "template_texture_isometric_cube.html",
        "category": "seamless_tile",
        "width_px": 800,
        "height_px": 800,
        "tile_unit_size": 128,
        "aspect_ratio": "1:1",
        "selector": "#capture-stage",
        "unit_selector": "#tile-unit svg",
        "motif": "104a Isometric cube complex with floating top and pulsing vertices",
        "default_duration_sec": 4.0,
        "bg_theme": "#000000"
    },
    "template_texture_checkerboard.html": {
        "name": "template_texture_checkerboard.html",
        "category": "seamless_tile",
        "width_px": 840,
        "height_px": 420,
        "tile_unit_size": 64,
        "aspect_ratio": "2:1",
        "selector": "#capture-stage",
        "unit_selector": "#tile-unit svg",
        "motif": "Dual-tone checkerboard with micro-crosshairs and pulsing red reticles",
        "default_duration_sec": 4.0,
        "bg_theme": "#000000"
    },
    "template_texture_circuit_grid.html": {
        "name": "template_texture_circuit_grid.html",
        "category": "seamless_tile",
        "width_px": 1280,
        "height_px": 720,
        "tile_unit_size": 64,
        "aspect_ratio": "16:9",
        "selector": "#capture-stage",
        "unit_selector": "#tile-unit svg",
        "motif": "Continuous electronic PCB bus traces with pulsing transmission tracks",
        "default_duration_sec": 6.0,
        "bg_theme": "#000000"
    },
    "template_texture_tile_studio.html": {
        "name": "template_texture_tile_studio.html",
        "category": "interactive_studio",
        "width_px": 840,
        "height_px": 420,
        "tile_unit_size": 128,
        "aspect_ratio": "multi",
        "selector": "#capture-stage",
        "unit_selector": "#tile-unit svg",
        "motif": "Master interactive studio: Cube, Checkerboard, Circuit, Hex Mesh, Dots",
        "default_duration_sec": 4.0,
        "bg_theme": "#000000"
    },
    "template_icon_512x512.html": {
        "name": "template_icon_512x512.html",
        "category": "icon_stage",
        "width_px": 512,
        "height_px": 512,
        "aspect_ratio": "1:1",
        "selector": "#capture-stage",
        "motif": "512px Master App Icon / PWA splash icon, floating 104a cube and reticle rings",
        "default_duration_sec": 4.0,
        "bg_theme": "#000000"
    },
    "template_icon_256x256.html": {
        "name": "template_icon_256x256.html",
        "category": "icon_stage",
        "width_px": 256,
        "height_px": 256,
        "aspect_ratio": "1:1",
        "selector": "#capture-stage",
        "motif": "256px Application launcher icon, hexagonal aperture and glowing cube nucleus",
        "default_duration_sec": 3.5,
        "bg_theme": "#000000"
    },
    "template_icon_128x128.html": {
        "name": "template_icon_128x128.html",
        "category": "icon_stage",
        "width_px": 128,
        "height_px": 128,
        "aspect_ratio": "1:1",
        "selector": "#capture-stage",
        "motif": "128px System icon / widget badge, high-contrast isometric cube glyph",
        "default_duration_sec": 3.0,
        "bg_theme": "#000000"
    },
    "template_icon_64x64.html": {
        "name": "template_icon_64x64.html",
        "category": "icon_stage",
        "width_px": 64,
        "height_px": 64,
        "aspect_ratio": "1:1",
        "selector": "#capture-stage",
        "motif": "64px Toolbar / navigation micro-icon, pixel-snapped cube silhouette",
        "default_duration_sec": 2.0,
        "bg_theme": "#000000"
    },
    "template_icon_32x32.html": {
        "name": "template_icon_32x32.html",
        "category": "icon_stage",
        "width_px": 32,
        "height_px": 32,
        "aspect_ratio": "1:1",
        "selector": "#capture-stage",
        "motif": "32px Favicon / terminal prompt glyph, micro isometric cube and red pip",
        "default_duration_sec": 1.8,
        "bg_theme": "#000000"
    },
    "template_graphic_badge_400x200.html": {
        "name": "template_graphic_badge_400x200.html",
        "category": "small_graphic",
        "width_px": 400,
        "height_px": 200,
        "aspect_ratio": "2:1",
        "selector": "#capture-stage",
        "motif": "400x200 Component badge, chamfered frame, scanline sweep and telemetry readout",
        "default_duration_sec": 3.0,
        "bg_theme": "#000000"
    },
    "template_graphic_kpi_card_320x320.html": {
        "name": "template_graphic_kpi_card_320x320.html",
        "category": "small_graphic",
        "width_px": 320,
        "height_px": 320,
        "aspect_ratio": "1:1",
        "selector": "#capture-stage",
        "motif": "320x320 Compact KPI metric card, radial dial gauge with red indicator arc",
        "default_duration_sec": 3.0,
        "bg_theme": "#000000"
    },
    "template_graphic_button_240x80.html": {
        "name": "template_graphic_button_240x80.html",
        "category": "small_graphic",
        "width_px": 240,
        "height_px": 80,
        "aspect_ratio": "3:1",
        "selector": "#capture-stage",
        "motif": "240x80 Cyber action button / control pill, glowing perimeter and micro-cube",
        "default_duration_sec": 2.5,
        "bg_theme": "#000000"
    },
    "template_graphic_chip_160x48.html": {
        "name": "template_graphic_chip_160x48.html",
        "category": "small_graphic",
        "width_px": 160,
        "height_px": 48,
        "aspect_ratio": "10:3",
        "selector": "#capture-stage",
        "motif": "160x48 Micro chip tag / tier badge, pulsing status pip and circuit trace",
        "default_duration_sec": 2.0,
        "bg_theme": "#000000"
    },
    "template_icon_studio.html": {
        "name": "template_icon_studio.html",
        "category": "dynamic_studio",
        "width_px": 256,
        "height_px": 256,
        "aspect_ratio": "dynamic",
        "selector": "#capture-stage",
        "motif": "Dynamic Icon & Graphic Studio with URL query controls (?size=, ?bg=)",
        "default_duration_sec": 3.0,
        "bg_theme": "#000000"
    },
    "template_icon_bejson_104_standard.html": {
        "name": "template_icon_bejson_104_standard.html",
        "category": "bejson_cube_icon",
        "width_px": 512,
        "height_px": 512,
        "aspect_ratio": "1:1",
        "selector": "#capture-stage",
        "motif": "BEJSON 104 Standard Monolith Cube: solid isometric cube, pulsing vertices, telemetry ring",
        "default_duration_sec": 4.0,
        "bg_theme": "#000000"
    },
    "template_icon_bejson_104a_floating.html": {
        "name": "template_icon_bejson_104a_floating.html",
        "category": "bejson_cube_icon",
        "width_px": 512,
        "height_px": 512,
        "aspect_ratio": "1:1",
        "selector": "#capture-stage",
        "motif": "BEJSON 104a Floating Cap Cube: signature levitating floating diamond top, plasma energy beams",
        "default_duration_sec": 3.5,
        "bg_theme": "#000000"
    },
    "template_icon_bejson_104db_pillar.html": {
        "name": "template_icon_bejson_104db_pillar.html",
        "category": "bejson_cube_icon",
        "width_px": 512,
        "height_px": 512,
        "aspect_ratio": "1:1",
        "selector": "#capture-stage",
        "motif": "BEJSON 104db Stacked Pillar: vertical monolithic pillar of 3 cubes with cascading red data pulses",
        "default_duration_sec": 3.0,
        "bg_theme": "#000000"
    },
    "template_icon_bejson_104_nested.html": {
        "name": "template_icon_bejson_104_nested.html",
        "category": "bejson_cube_icon",
        "width_px": 512,
        "height_px": 512,
        "aspect_ratio": "1:1",
        "selector": "#capture-stage",
        "motif": "BEJSON Nested Cube: wireframe outer container cube with spinning inner luminous child cube",
        "default_duration_sec": 4.0,
        "bg_theme": "#000000"
    },
    "template_icon_bejson_mfdb_federation.html": {
        "name": "template_icon_bejson_mfdb_federation.html",
        "category": "bejson_cube_icon",
        "width_px": 512,
        "height_px": 512,
        "aspect_ratio": "1:1",
        "selector": "#capture-stage",
        "motif": "BEJSON MFDB Federated Network: large central master cube transmitting to 4 orbiting slave cubes",
        "default_duration_sec": 3.5,
        "bg_theme": "#000000"
    }
}

def resolve_template_root() -> Path:
    """Finds the primary directory containing the HTML canvas templates."""
    for candidate in TEMPLATE_ROOT_CANDIDATES:
        if candidate.is_dir():
            return candidate
    return TEMPLATE_ROOT_CANDIDATES[0]

def list_canvas_templates() -> List[Dict[str, Any]]:
    """Returns catalog information for all supported canvas templates."""
    root_path = resolve_template_root()
    catalog_list: List[Dict[str, Any]] = []

    for template_name, meta in CANVAS_TEMPLATE_CATALOG.items():
        entry = dict(meta)
        target_path = root_path / template_name
        entry["exists_on_disk"] = target_path.exists()
        entry["disk_path"] = str(target_path) if target_path.exists() else None
        catalog_list.append(entry)

    return catalog_list

def get_template_path(template_name: str) -> Path:
    """Resolves the absolute path to a canvas template file."""
    if not template_name.endswith(".html"):
        template_name = f"{template_name}.html"

    # Search candidates
    for candidate_root in TEMPLATE_ROOT_CANDIDATES:
        cand_path = candidate_root / template_name
        if cand_path.exists():
            return cand_path

    # Fallback to resolved root
    return resolve_template_root() / template_name

def load_template(template_name: str) -> str:
    """Loads raw HTML template text."""
    path = get_template_path(template_name)
    if not path.exists():
        raise FileNotFoundError(f"Canvas template '{template_name}' not found at {path}")
    return path.read_text(encoding="utf-8")

def render_canvas_html(
    template_name: str,
    custom_svg_markup: Optional[str] = None,
    width_px: Optional[int] = None,
    height_px: Optional[int] = None,
    bg_theme: Optional[str] = None,
    accent_color: Optional[str] = None,
    duration_sec: Optional[float] = None
) -> str:
    """Renders canvas template HTML with optional parameter replacements."""
    html_content = load_template(template_name)

    # Replace SVG if custom markup provided
    if custom_svg_markup:
        # Match <div class="svg-container">...</div> or <svg id="tile-unit">...</svg>
        container_pattern = re.compile(r'(<div class="svg-container">)(.*?)(</div>)', re.DOTALL)
        if container_pattern.search(html_content):
            html_content = container_pattern.sub(f'\\1\n{custom_svg_markup}\n\\3', html_content)
        else:
            tile_pattern = re.compile(r'(<div id="tile-unit"[^>]*>)(.*?)(</div>)', re.DOTALL)
            if tile_pattern.search(html_content):
                html_content = tile_pattern.sub(f'\\1\n{custom_svg_markup}\n\\3', html_content)

    # Override dimensions in CSS if specified
    if width_px is not None:
        html_content = re.sub(r'width:\s*\d+px;', f'width: {width_px}px;', html_content, count=1)
    if height_px is not None:
        html_content = re.sub(r'height:\s*\d+px;', f'height: {height_px}px;', html_content, count=1)

    # Override duration in seekProgress hook if specified
    if duration_sec is not None and duration_sec > 0:
        html_content = re.sub(
            r'const totalDurationSec\s*=\s*[\d\.]+;',
            f'const totalDurationSec = {duration_sec};',
            html_content
        )

    # Override colors if requested
    if accent_color:
        html_content = html_content.replace('#DE2626', accent_color)

    return html_content

def instantiate_stage_html(
    template_name: str,
    target_output_file: Path,
    custom_svg_markup: Optional[str] = None,
    width_px: Optional[int] = None,
    height_px: Optional[int] = None,
    bg_theme: Optional[str] = None,
    accent_color: Optional[str] = None,
    duration_sec: Optional[float] = None
) -> Path:
    """Renders template HTML and writes it to disk ready for Playwright capture."""
    rendered_html = render_canvas_html(
        template_name=template_name,
        custom_svg_markup=custom_svg_markup,
        width_px=width_px,
        height_px=height_px,
        bg_theme=bg_theme,
        accent_color=accent_color,
        duration_sec=duration_sec
    )
    target_output_file.parent.mkdir(parents=True, exist_ok=True)
    target_output_file.write_text(rendered_html, encoding="utf-8")
    return target_output_file
