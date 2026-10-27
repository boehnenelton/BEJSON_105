"""
Library:        lib_bejson_Graphics_graphics_canvas_templates.py
Family:         Graphics
Description:    Blank-Slate Canvas Stage Templates & Embedded BEJSON 105a Scaffold Registry.
                Provides dynamic blank-slate capture stages for arbitrary image sizes,
                parameterized aspect ratios, and dynamic row-per-frame SVG animations.
BEJSON:         BEJSON stands for BOEHNEN ELTON JSON. Authoritative definition;
                do not restate or reinterpret this acronym elsewhere.
MFDB:           MFDB stands for Multi File Database. Authoritative definition;
                do not restate or reinterpret this acronym elsewhere.
Version:        1.0.0
Date:           2026-10-27
Author:         Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
RELATIONAL_ID:  2c3d4e5f-6a7b-4c8d-9e0f-1a2b3c4d5e6f
Release_Version: 300
"""

from __future__ import annotations

import hashlib
import json
import logging
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
        GRAPHIC_TEMPLATE_REGISTRY_FIELDS,
        build_field_map_105,
    )
except ImportError:
    GRAPHIC_TEMPLATE_REGISTRY_FIELDS = []
    def build_field_map_105(fields): return {f["name"]: i + 1 for i, f in enumerate(fields)}

logger = logging.getLogger("lib_bejson_Graphics_graphics_canvas_templates")
VERSION = "1.0.0"

# ---------------------------------------------------------------------------
# Canonical Blank-Slate Stage Template Generator
# ---------------------------------------------------------------------------

def generate_blank_slate_html(
    width_px: int = 800,
    height_px: int = 800,
    bg_theme: str = "#000000",
    accent_color: str = "#DE2626",
    title: str = "Blank Slate Canvas Stage",
    initial_svg_markup: Optional[str] = None
) -> str:
    """
    Generates a production-ready, zero-filler Blank Slate HTML canvas stage.
    The stage provides an unopinionated blank canvas designed to host arbitrary
    dynamic SVGs, images, and frame states at any resolution.
    Exposes window.setSvgContent(), window.seekProgress(), and window.isReadyToCapture.
    """
    svg_body = initial_svg_markup or (
        f'<svg id="dynamic-svg" viewBox="0 0 {width_px} {height_px}" '
        f'xmlns="http://www.w3.org/2000/svg" style="width:100%;height:100%;display:block;">'
        f'<!-- Dynamic Blank Slate Canvas -->'
        f'</svg>'
    )

    bg_css = bg_theme
    border_css = "none" if bg_theme == "transparent" else "1px solid #1c1c24"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <style>
    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }}
    html, body {{
      width: 100vw;
      height: 100vh;
      background: {bg_css};
      display: flex;
      align-items: center;
      justify-content: center;
      overflow: hidden;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace;
    }}
    #capture-stage {{
      position: relative;
      width: {width_px}px;
      height: {height_px}px;
      background: {bg_css};
      border: {border_css};
      overflow: hidden;
      display: flex;
      align-items: center;
      justify-content: center;
    }}
    .canvas-slot {{
      width: 100%;
      height: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
      position: relative;
    }}
    .canvas-slot > svg, .canvas-slot > img {{
      width: 100%;
      height: 100%;
      display: block;
      object-fit: contain;
    }}
  </style>
</head>
<body>
  <div id="capture-stage" data-width="{width_px}" data-height="{height_px}">
    <div class="canvas-slot" id="stage-slot">
      {svg_body}
    </div>
    <!-- Pre-recording Coordinate-Based Text Overlay Layer -->
    <div id="overlay-layer" style="position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:100;overflow:hidden;"></div>
  </div>

  <script>
    window.isReadyToCapture = true;
    window._activeOverlays = [];

    // Dynamically replace the SVG / graphic content in the blank slate
    window.setSvgContent = function(svgMarkup) {{
      const slot = document.getElementById('stage-slot');
      if (slot) {{
        slot.innerHTML = svgMarkup;
        window.isReadyToCapture = true;
      }}
    }};

    // Update dimensions dynamically
    window.setDimensions = function(width, height) {{
      const stage = document.getElementById('capture-stage');
      if (stage) {{
        stage.style.width = width + 'px';
        stage.style.height = height + 'px';
        stage.setAttribute('data-width', width);
        stage.setAttribute('data-height', height);
      }}
    }};

    // Pre-recording Coordinate-Based Text Overlay Injection
    window.setTextOverlays = function(overlays, context) {{
      const layer = document.getElementById('overlay-layer');
      if (!layer) return;
      layer.innerHTML = '';
      window._activeOverlays = overlays || [];
      const ctx = context || {{}};

      (window._activeOverlays).forEach(o => {{
        const item = document.createElement('div');
        item.style.position = 'absolute';
        item.style.left = typeof o.x === 'number' ? o.x + 'px' : o.x;
        item.style.top = typeof o.y === 'number' ? o.y + 'px' : o.y;
        item.style.fontSize = (o.font_size || 20) + 'px';
        item.style.fontFamily = o.font_family || 'monospace';
        item.style.fontWeight = o.font_weight || 'bold';
        item.style.color = o.color || '#FFFFFF';
        if (o.bg_color) item.style.backgroundColor = o.bg_color;
        if (o.padding) item.style.padding = o.padding;
        if (o.border_radius) item.style.borderRadius = o.border_radius;
        if (o.opacity !== undefined) item.style.opacity = o.opacity;
        if (o.z_index) item.style.zIndex = o.z_index;
        if (o.align) item.style.textAlign = o.align;

        let rawText = o.text || '';
        // Token interpolation
        rawText = rawText.replace(/{{frame}}/g, ctx.frame !== undefined ? ctx.frame : '')
                         .replace(/{{time}}/g, ctx.time !== undefined ? Number(ctx.time).toFixed(2) : '')
                         .replace(/{{fps}}/g, ctx.fps || '')
                         .replace(/{{caption}}/g, ctx.caption || '');
        item.textContent = rawText;
        layer.appendChild(item);
      }});
      window.isReadyToCapture = true;
    }};

    // Timeline seeking hook for CSS/SMIL animations inside the dynamic SVG
    window.seekProgress = function(progress, durationSeconds) {{
      const dur = durationSeconds || 8.0;
      const targetTimeSec = progress * dur;
      document.querySelectorAll('#capture-stage *').forEach(el => {{
        el.style.animationDelay = `-${{targetTimeSec}}s`;
        el.style.animationPlayState = 'paused';
      }});
    }};

    // Dynamic Diagram View Loader
    window.loadDiagram = function(diagramData, state, viewport) {{
      const slot = document.getElementById('stage-slot');
      if (!slot) return;
      window._activeDiagram = diagramData;
      window.setDiagramState(state, viewport);
    }};

    window.setDiagramState = function(state, viewport) {{
      const slot = document.getElementById('stage-slot');
      if (!slot || !window._activeDiagram) return;
      const diag = window._activeDiagram;
      const st = state || {{}};
      const vp = viewport || {{}};

      const activeShapes = new Set(st.active_shapes || []);
      const dimmedShapes = new Set(st.dimmed_shapes || []);
      const activeConns = new Set(st.active_connectors || []);

      const stage = document.getElementById('capture-stage');
      const cw = parseInt(stage.getAttribute('data-width') || 800, 10);
      const ch = parseInt(stage.getAttribute('data-height') || 800, 10);

      const panX = vp.pan_x !== undefined ? vp.pan_x : 0;
      const panY = vp.pan_y !== undefined ? vp.pan_y : 0;
      const zoom = vp.zoom !== undefined ? vp.zoom : 1.0;

      // Build internal SVG representation
      let svg = `<svg viewBox="0 0 ${{cw}} ${{ch}}" width="${{cw}}" height="${{ch}}" xmlns="http://www.w3.org/2000/svg" style="background:#000000;width:100%;height:100%;">
        <defs>
          <marker id="arr" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#FFFFFF" />
          </marker>
          <marker id="arr-red" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path d="M 0 1 L 9 5 L 0 9 z" fill="#DE2626" />
          </marker>
          <filter id="red-glow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="6" result="blur" />
            <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>
        <g id="viewport-group" transform="translate(${{panX}}, ${{panY}}) scale(${{zoom}})">`;

      const shapeMap = {{}};
      (diag.shapes || []).forEach(s => {{
        const sid = s.id || s.tempId;
        if (sid) shapeMap[sid] = s;
      }});

      // Territories
      (diag.territories || []).forEach(t => {{
        const sz = t.size || 200;
        const color = t.color || '#DE2626';
        svg += `<rect x="${{t.cx - sz/2}}" y="${{t.cy - sz/2}}" width="${{sz}}" height="${{sz}}" rx="16" fill="${{color}}" fill-opacity="0.05" stroke="${{color}}" stroke-opacity="0.3" stroke-width="1.5" stroke-dasharray="6,4" />`;
        if (t.label) {{
          svg += `<text x="${{t.cx}}" y="${{t.cy - sz/2 + 20}}" fill="${{color}}" font-size="11" font-family="monospace" font-weight="bold" letter-spacing="1" text-anchor="middle">${{t.label.toUpperCase()}}</text>`;
        }}
      }});

      // Connectors
      (diag.connectors || []).forEach(c => {{
        const fid = c.from || c.fromTempId;
        const tid = c.to || c.toTempId;
        if (shapeMap[fid] && shapeMap[tid]) {{
          const s1 = shapeMap[fid];
          const s2 = shapeMap[tid];
          const isAct = activeConns.has(`${{fid}}->${{tid}}`) || (activeShapes.has(fid) && activeShapes.has(tid));
          const col = isAct ? '#DE2626' : '#FFFFFF';
          const mkr = isAct ? 'url(#arr-red)' : 'url(#arr)';
          svg += `<line x1="${{s1.cx}}" y1="${{s1.cy}}" x2="${{s2.cx}}" y2="${{s2.cy}}" stroke="${{col}}" stroke-width="${{isAct ? 2.5 : 1.5}}" stroke-opacity="${{isAct ? 1 : 0.4}}" marker-end="${{mkr}}" />`;
        }}
      }});

      // Shapes
      (diag.shapes || []).forEach(s => {{
        const sid = s.id || s.tempId;
        const w = s.sizeClass === 'small' ? 120 : (s.sizeClass === 'large' ? 300 : 200);
        const h = s.sizeClass === 'small' ? 70 : (s.sizeClass === 'large' ? 150 : 100);
        const isAct = activeShapes.has(sid);
        const isDim = dimmedShapes.has(sid);
        const col = isAct ? '#DE2626' : '#FFFFFF';
        const bg = isAct ? '#1c0d0d' : '#121218';
        const glow = isAct ? 'filter="url(#red-glow)"' : '';
        const op = isDim ? '0.25' : '1.0';

        svg += `<g id="s-${{sid}}" opacity="${{op}}">
          <rect x="${{s.cx - w/2}}" y="${{s.cy - h/2}}" width="${{w}}" height="${{h}}" rx="8" fill="${{bg}}" stroke="${{col}}" stroke-width="${{isAct ? 2.5 : 1.2}}" ${{glow}} />
          <text x="${{s.cx - w/2 + 12}}" y="${{s.cy - h/2 + 24}}" fill="#FFFFFF" font-size="12" font-family="-apple-system, sans-serif" font-weight="bold">${{s.label || sid}}</text>`;
        if (s.text) {{
          svg += `<text x="${{s.cx - w/2 + 12}}" y="${{s.cy - h/2 + 42}}" fill="#737373" font-size="10" font-family="-apple-system, sans-serif">${{(s.text || '').substring(0, 32)}}</text>`;
        }}
        if (isAct) {{
          svg += `<circle cx="${{s.cx + w/2 - 12}}" cy="${{s.cy - h/2 + 12}}" r="4" fill="#DE2626" />`;
        }}
        svg += `</g>`;
      }});

      svg += `</g>`;

      if (st.badge_text) {{
        svg += `<g id="canvas-hud">
          <rect x="20" y="20" width="300" height="34" rx="4" fill="#0c0c12" fill-opacity="0.9" stroke="#22222c" stroke-width="1" />
          <circle cx="34" cy="37" r="4" fill="#DE2626" />
          <text x="48" y="41" fill="#FFFFFF" font-size="11" font-family="monospace" font-weight="bold">${{st.badge_text.toUpperCase()}}</text>
        </g>`;
      }}

      svg += `</svg>`;
      slot.innerHTML = svg;
      window.isReadyToCapture = true;
    }};

    window.pauseAnimation = function() {{
      document.querySelectorAll('#capture-stage *').forEach(el => {{
        el.style.animationPlayState = 'paused';
      }});
    }};

    window.playAnimation = function() {{
      document.querySelectorAll('#capture-stage *').forEach(el => {{
        el.style.animationPlayState = 'running';
      }});
    }};
  </script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Canonical Standard Blank-Slate Archetypes
# ---------------------------------------------------------------------------

BLANK_SLATE_ARCHETYPES: List[Dict[str, Any]] = [
    {
        "template_id": "blank_slate_universal",
        "template_name": "blank_slate_stage.html",
        "category": "blank_slate",
        "width_px": 800,
        "height_px": 800,
        "aspect_ratio": "dynamic",
        "stage_selector": "#capture-stage",
        "description": "Universal dynamic blank slate stage with runtime dimension and SVG injection hooks."
    },
    {
        "template_id": "blank_slate_square_800",
        "template_name": "blank_slate_square_800x800.html",
        "category": "blank_slate_fixed",
        "width_px": 800,
        "height_px": 800,
        "aspect_ratio": "1:1",
        "stage_selector": "#capture-stage",
        "description": "1:1 Square 800x800 blank slate canvas for square assets, cards, and avatars."
    },
    {
        "template_id": "blank_slate_banner_840",
        "template_name": "blank_slate_banner_840x420.html",
        "category": "blank_slate_fixed",
        "width_px": 840,
        "height_px": 420,
        "aspect_ratio": "2:1",
        "stage_selector": "#capture-stage",
        "description": "2:1 Banner 840x420 blank slate canvas for banners, headers, and social cards."
    },
    {
        "template_id": "blank_slate_hd_1280",
        "template_name": "blank_slate_widescreen_1280x720.html",
        "category": "blank_slate_fixed",
        "width_px": 1280,
        "height_px": 720,
        "aspect_ratio": "16:9",
        "stage_selector": "#capture-stage",
        "description": "16:9 HD 1280x720 blank slate canvas for widescreen landscapes and video thumbnails."
    },
    {
        "template_id": "blank_slate_hero_1280",
        "template_name": "blank_slate_article_hero_1280x640.html",
        "category": "blank_slate_fixed",
        "width_px": 1280,
        "height_px": 640,
        "aspect_ratio": "2:1",
        "stage_selector": "#capture-stage",
        "description": "2:1 Article Hero 1280x640 blank slate canvas for CMS article headers."
    },
    {
        "template_id": "blank_slate_portrait_720",
        "template_name": "blank_slate_portrait_720x1280.html",
        "category": "blank_slate_fixed",
        "width_px": 720,
        "height_px": 1280,
        "aspect_ratio": "9:16",
        "stage_selector": "#capture-stage",
        "description": "9:16 Portrait 720x1280 blank slate canvas for mobile vertical assets."
    },
    {
        "template_id": "blank_slate_kpi_320",
        "template_name": "blank_slate_kpi_card_320x320.html",
        "category": "blank_slate_fixed",
        "width_px": 320,
        "height_px": 320,
        "aspect_ratio": "1:1",
        "stage_selector": "#capture-stage",
        "description": "1:1 KPI Card 320x320 blank slate canvas for dashboard telemetry widgets."
    },
    {
        "template_id": "blank_slate_badge_400",
        "template_name": "blank_slate_badge_400x200.html",
        "category": "blank_slate_fixed",
        "width_px": 400,
        "height_px": 200,
        "aspect_ratio": "2:1",
        "stage_selector": "#capture-stage",
        "description": "2:1 Brand Badge 400x200 blank slate canvas for system status badges."
    },
    {
        "template_id": "blank_slate_button_240",
        "template_name": "blank_slate_button_240x80.html",
        "category": "blank_slate_fixed",
        "width_px": 240,
        "height_px": 80,
        "aspect_ratio": "3:1",
        "stage_selector": "#capture-stage",
        "description": "3:1 Graphic Button 240x80 blank slate canvas for call-to-action buttons."
    },
    {
        "template_id": "blank_slate_icon_512",
        "template_name": "blank_slate_icon_512x512.html",
        "category": "blank_slate_icon",
        "width_px": 512,
        "height_px": 512,
        "aspect_ratio": "1:1",
        "stage_selector": "#capture-stage",
        "description": "1:1 App Icon 512x512 blank slate canvas for high-resolution iconography."
    },
    {
        "template_id": "blank_slate_tile_128",
        "template_name": "blank_slate_texture_tile_128x128.html",
        "category": "blank_slate_tile",
        "width_px": 128,
        "height_px": 128,
        "aspect_ratio": "1:1",
        "stage_selector": "#capture-stage",
        "description": "1:1 Seamless Tile 128x128 blank slate canvas for repeating texture pattern generation."
    }
]


# ---------------------------------------------------------------------------
# Embedded BEJSON 105a Scaffold & Template Registry
# ---------------------------------------------------------------------------

_REGISTRY_CACHE: Optional[Dict[str, Any]] = None

def get_canvas_template_registry_105a(
    include_legacy_source_dir: Optional[str] = "/storage/emulated/0/Admin/Dev/Templates/Canvas_SVG_Capture_Templates"
) -> Dict[str, Any]:
    """
    Returns the canonical BEJSON 105a Scaffold & Template Registry.
    Contains both the core blank slate canvas stages and any historical
    exemplar templates harvested from the dev directory.
    """
    global _REGISTRY_CACHE
    if _REGISTRY_CACHE is not None:
        return _REGISTRY_CACHE

    values_rows: List[List[Any]] = []

    # 1. Register canonical blank slate archetypes
    for arc in BLANK_SLATE_ARCHETYPES:
        html = generate_blank_slate_html(
            width_px=arc["width_px"],
            height_px=arc["height_px"],
            bg_theme="#000000",
            title=arc["description"]
        )
        h_hash = hashlib.sha256(html.encode("utf-8")).hexdigest()
        rec_uuid = str(uuid.uuid4())
        row = [
            rec_uuid,
            arc["template_id"],
            arc["template_name"],
            arc["category"],
            arc["width_px"],
            arc["height_px"],
            arc["aspect_ratio"],
            arc["stage_selector"],
            arc["description"],
            html,
            h_hash
        ]
        values_rows.append(row)

    # 2. Ingest legacy/exemplar templates if directory exists
    if include_legacy_source_dir and os.path.isdir(include_legacy_source_dir):
        legacy_dir = Path(include_legacy_source_dir)
        for html_file in sorted(legacy_dir.glob("*.html")):
            t_name = html_file.name
            # Avoid duplicating blank slates
            if any(r[2] == t_name for r in values_rows):
                continue
            try:
                content = html_file.read_text(encoding="utf-8")
                c_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
                rec_uuid = str(uuid.uuid4())

                # Deduce dimensions
                w, h = 800, 800
                import re
                m = re.search(r'(\d+)x(\d+)', html_file.stem)
                if m:
                    w, h = int(m.group(1)), int(m.group(2))

                row = [
                    rec_uuid,
                    f"legacy_{html_file.stem}",
                    t_name,
                    "legacy_exemplar",
                    w,
                    h,
                    f"{w}:{h}",
                    "#capture-stage",
                    f"Exemplar template {t_name} from {include_legacy_source_dir}",
                    content,
                    c_hash
                ]
                values_rows.append(row)
            except Exception as exc:
                logger.warning(f"Could not ingest template {t_name}: {exc}")

    doc: Dict[str, Any] = {
        "Format": "BEJSON",
        "Format_Version": "105a",
        "Format_Creator": "Elton Boehnen",
        "Schema_Name": "CanvasTemplateScaffoldRegistry",
        "Record_Type": ["CanvasTemplateRecord"],
        "Fields": [dict(f) for f in GRAPHIC_TEMPLATE_REGISTRY_FIELDS],
        "Values": values_rows
    }

    _REGISTRY_CACHE = doc
    return doc


def list_registered_templates() -> List[Dict[str, Any]]:
    """Lists all templates registered in the BEJSON 105a template registry."""
    reg = get_canvas_template_registry_105a()
    fmap = build_field_map_105(reg["Fields"])
    result = []
    for row in reg["Values"]:
        result.append({
            "template_id": row[fmap["template_id"]],
            "template_name": row[fmap["template_name"]],
            "category": row[fmap["category"]],
            "width_px": row[fmap["width_px"]],
            "height_px": row[fmap["height_px"]],
            "aspect_ratio": row[fmap["aspect_ratio"]],
            "stage_selector": row[fmap["stage_selector"]],
            "description": row[fmap["description"]],
            "checksum_sha256": row[fmap["checksum_sha256"]][:8]
        })
    return result


def get_template_html(
    template_name: str = "blank_slate_stage.html",
    width_px: Optional[int] = None,
    height_px: Optional[int] = None,
    bg_theme: str = "#000000"
) -> str:
    """
    Retrieves the HTML markup for a registered template, or dynamically generates
    a blank slate canvas of the specified dimensions.
    """
    reg = get_canvas_template_registry_105a()
    fmap = build_field_map_105(reg["Fields"])

    for row in reg["Values"]:
        if row[fmap["template_name"]] == template_name or row[fmap["template_id"]] == template_name:
            html = row[fmap["html_template"]]
            if width_px is not None and height_px is not None:
                # If custom dimensions are supplied on a blank slate, re-generate clean
                return generate_blank_slate_html(width_px, height_px, bg_theme)
            return html

    # Fallback: Generate custom blank slate on demand
    w = width_px or 800
    h = height_px or 800
    return generate_blank_slate_html(w, h, bg_theme)


def instantiate_stage_file(
    output_path: Path,
    template_name: str = "blank_slate_stage.html",
    width_px: int = 800,
    height_px: int = 800,
    bg_theme: str = "#000000",
    initial_svg_markup: Optional[str] = None
) -> Path:
    """
    Writes a self-contained blank slate stage HTML file to disk, ready for Playwright navigation.
    """
    html = generate_blank_slate_html(
        width_px=width_px,
        height_px=height_px,
        bg_theme=bg_theme,
        initial_svg_markup=initial_svg_markup
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return output_path
