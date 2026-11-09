#!/usr/bin/env python3
"""
Script: generate_bejson_105_presentation.py
Description: Generates a sleek, minimal 5-slide presentation explaining BEJSON 105
             using the Lib_PY.Graphics 105 family and the new clean point-focus templates.
Author: Elton Boehnen
"""

import sys
import json
from pathlib import Path

# Self-locating relative import
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from lib_bejson_Graphics_graphics_core import (
    render_slide_split_visual_svg,
    render_slide_key_points_svg,
    render_slide_visual_focus_light_svg,
    render_slide_visual_focus_dark_svg,
    render_slide_process_flow_svg,
    create_isometric_cube_svg,
    COLOR_RED
)
from lib_bejson_Graphics_graphics_schemas import create_branding_slide_deck_105a
from lib_bejson_Graphics_graphics_validator import validate_graphics_barrier


def build_bejson_105_slides(output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Slide 1: Split Visual - BEJSON 105 Overview
    cube_svg = create_isometric_cube_svg(viewbox_size=360, cube_style="104a_floating", accent_color=COLOR_RED)
    inner_visual = f"""<rect x="64" y="64" width="540" height="520" rx="6" fill="#0E0E10" stroke="#24242A" stroke-width="1.5"/>
  <path d="M 64 88 L 64 64 L 88 64" fill="none" stroke="#3A3A44" stroke-width="1.5"/>
  <path d="M 580 64 L 604 64 L 604 88" fill="none" stroke="#3A3A44" stroke-width="1.5"/>
  <path d="M 64 560 L 64 584 L 88 584" fill="none" stroke="#3A3A44" stroke-width="1.5"/>
  <path d="M 580 584 L 604 584 L 604 560" fill="none" stroke="#3A3A44" stroke-width="1.5"/>
  <g transform="translate(154, 144)">
    {cube_svg}
  </g>"""

    slide_1_svg = render_slide_split_visual_svg(
        title="BEJSON 105",
        tagline="INTEGRITY ERA SPECIFICATION",
        content="Positional column-oriented data container with cryptographically verifiable identity.",
        inner_svg=inner_visual
    )

    # 2. Slide 2: Key Points - Core Architecture
    slide_2_svg = render_slide_key_points_svg(
        title="CORE INVARIANTS",
        tagline="POSITIONAL RIGOR & IDENTITY",
        narrative="Deterministic schema declaration separated from raw positional row values.",
        key_points=[
            "UUIDv4 column headers survive renames and reordering",
            "Reserved column 0 for immutable row record_uuid",
            "O(1) cached field-map positional lookup"
        ]
    )

    # 3. Slide 3: Process Flow - Integrity Pipeline
    slide_3_svg = render_slide_process_flow_svg(
        title="INTEGRITY PIPELINE",
        steps=[
            {"label": "1. Schema Rigor", "sub": "Fields & field_uuid"},
            {"label": "2. Positional Rows", "sub": "Column 0 Identity"},
            {"label": "3. Strict Validator", "sub": "Zero Hallucination"}
        ]
    )

    # 4. Slide 4: Light Mode Visual Focus - AI-Native Token Efficiency
    slide_4_svg = render_slide_visual_focus_light_svg(
        title="AI-NATIVE EFFICIENCY",
        description="Eliminates repetitive JSON object keys, saving up to 90% in token bandwidth while guaranteeing schema integrity.",
        placeholder_text="[ TOKEN CONSUMPTION REDUCED BY 90% ]"
    )

    # 5. Slide 5: Dark Mode Visual Focus - Relational MFDB
    slide_5_svg = render_slide_visual_focus_dark_svg(
        title="ZERO-SQL RELATIONAL MFDB",
        tagline="MULTI-FILE SERVERLESS DATA ARCHITECTURE",
        placeholder_text="[ MFDB SPEC 1.40 ENFORCEMENT ]"
    )

    slides_map = [
        {"slide_type": "split_visual", "title": "BEJSON 105 Overview", "subtitle": "Integrity Era Specification", "svg_markup": slide_1_svg, "filename": "slide_01_overview.svg"},
        {"slide_type": "key_points", "title": "Core Invariants", "subtitle": "Positional Rigor & Identity", "svg_markup": slide_2_svg, "filename": "slide_02_architecture.svg"},
        {"slide_type": "process_flow", "title": "Integrity Pipeline", "subtitle": "Workflow Execution", "svg_markup": slide_3_svg, "filename": "slide_03_pipeline.svg"},
        {"slide_type": "visual_focus_light", "title": "AI-Native Efficiency", "subtitle": "Token Bandwidth Reduction", "svg_markup": slide_4_svg, "filename": "slide_04_efficiency.svg"},
        {"slide_type": "visual_focus_dark", "title": "Zero-SQL Relational MFDB", "subtitle": "Serverless Relational Integrity", "svg_markup": slide_5_svg, "filename": "slide_05_mfdb.svg"}
    ]

    # Save individual SVGs
    for item in slides_map:
        svg_file = output_dir / item["filename"]
        svg_file.write_text(item["svg_markup"], encoding="utf-8")
        print(f"Saved SVG: {svg_file}")

    # Build canonical BEJSON 105a Slide Deck document
    deck_doc = create_branding_slide_deck_105a(
        deck_name="BEJSON_105_Executive_Brief",
        slides=slides_map,
        default_duration_sec=4.0,
        remove_frame_source=True
    )

    deck_path = output_dir / "bejson_105_deck.105a.bejson"
    with open(deck_path, "w", encoding="utf-8") as f:
        json.dump(deck_doc, f, indent=2)
    print(f"Saved BEJSON 105a Deck: {deck_path}")

    # Validate against Ruthless Graphics Barrier
    res = validate_graphics_barrier(str(deck_path), is_file=True)
    if res.valid:
        print("✓ Graphics Barrier Validation PASSED: 100% compliant with Policy & BEJSON 105 standards.")
    else:
        print(f"✗ Graphics Barrier Validation FAILED: {res.errors}")
        sys.exit(1)

    # Generate interactive HTML preview
    html_slides = []
    for i, item in enumerate(slides_map):
        html_slides.append(f"""
        <div class="slide-card">
            <div class="slide-header">Slide {i+1}: {item['title']} <span class="badge">{item['slide_type']}</span></div>
            <div class="slide-viewport">
                {item['svg_markup']}
            </div>
        </div>
        """)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BEJSON 105 — Executive Presentation Deck</title>
    <style>
        body {{
            margin: 0;
            padding: 24px;
            background-color: #0A0A0C;
            color: #FFFFFF;
            font-family: system-ui, -apple-system, sans-serif;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 32px;
        }}
        .header {{
            text-align: center;
            max-width: 800px;
        }}
        h1 {{
            font-size: 32px;
            margin: 0 0 8px 0;
            letter-spacing: 1px;
        }}
        p.subtitle {{
            color: #888894;
            font-size: 16px;
            margin: 0;
        }}
        .slide-card {{
            width: 100%;
            max-width: 1080px;
            background: #111114;
            border: 1px solid #222228;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 8px 24px rgba(0,0,0,0.5);
        }}
        .slide-header {{
            padding: 12px 20px;
            background: #16161B;
            border-bottom: 1px solid #222228;
            font-size: 14px;
            font-weight: 600;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .badge {{
            background: #DE2626;
            color: #FFFFFF;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .slide-viewport {{
            width: 100%;
            display: flex;
            justify-content: center;
            align-items: center;
            line-height: 0;
        }}
        .slide-viewport svg {{
            width: 100%;
            height: auto;
            display: block;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>BEJSON 105 PRESENTATION DECK</h1>
        <p class="subtitle">Built with Lib_PY.Graphics & Sleek Point-Focus Slide Templates</p>
    </div>
    {"".join(html_slides)}
</body>
</html>"""

    html_file = output_dir / "index.html"
    html_file.write_text(html_content, encoding="utf-8")
    print(f"Saved HTML Preview: {html_file}")
    return deck_path, html_file


if __name__ == "__main__":
    target_dir = SCRIPT_DIR / "exports" / "bejson_105_presentation"
    build_bejson_105_slides(target_dir)
