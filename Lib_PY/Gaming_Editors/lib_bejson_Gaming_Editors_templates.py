"""
Library:        lib_bejson_Gaming_Editors_templates.py
Family:         Gaming_Editors
Description:    Stage Template Registry & Orchestration for Gaming_Editors 105 Family.
                Dispatches and hydrates Game Engine Blank-Slate Stages (Sprite Sheet Studio,
                Tilemap Palette Studio, HUD Stage Studio, and Animation Stage).
BEJSON:         BEJSON stands for BOEHNEN ELTON JSON. Authoritative definition;
                do not restate or reinterpret this acronym elsewhere.
                (Pronounced Bee-Jay-Son / Bay-nin Elton JSON)
MFDB:           MFDB stands for Multi File Database. Authoritative definition;
                do not restate or reinterpret this acronym elsewhere.
Version:        1.0.0
Date:           2026-11-15
Author:         Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
License:        PolyForm-Noncommercial-1.0.0
RELATIONAL_ID:  ae2d4f5a-6b7c-8d9e-0f1a-2b3c4d5e6f7a
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
from typing import Any, Dict, List, Optional

_HERE = Path(__file__).resolve().parent
for _fam in ('Core', 'Standards', 'Taxonomies', 'Graphics', 'Gaming_Editors'):
    _p = str(_HERE.parent / _fam)
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

from lib_bejson_Gaming_Editors_schemas import build_field_map_105

logger = logging.getLogger("lib_bejson_Gaming_Editors_templates")
VERSION = "1.0.0"

GAMING_EDITOR_TEMPLATES_CATALOG: List[Dict[str, Any]] = [
    {
        "template_id": "game_sprite_sheet_studio_512",
        "template_name": "template_game_sprite_sheet_studio.html",
        "category": "gaming_editor",
        "width_px": 512,
        "height_px": 512,
        "aspect_ratio": "1:1",
        "stage_selector": "#capture-stage",
        "bg_theme": "#000000",
        "description": "512x512 Game Sprite Sheet Studio blank-slate stage with 16/32/48/64px cells, pivot reticles, window.setCellSvg(r,c,svg), and #isolated-cell export."
    },
    {
        "template_id": "game_sprite_animation_stage_400",
        "template_name": "template_game_sprite_animation_stage.html",
        "category": "gaming_editor",
        "width_px": 400,
        "height_px": 400,
        "aspect_ratio": "1:1",
        "stage_selector": "#capture-stage",
        "bg_theme": "#000000",
        "description": "400x400 Game Sprite Animation Stage with 2x/4x/8x zoom, onion skinning ghost layer, 4-frame pill strip, and window.setAnimationFrames(frames,label)."
    },
    {
        "template_id": "game_tilemap_palette_stage_512",
        "template_name": "template_game_tilemap_palette_stage.html",
        "category": "gaming_editor",
        "width_px": 512,
        "height_px": 512,
        "aspect_ratio": "1:1",
        "stage_selector": "#capture-stage",
        "bg_theme": "#000000",
        "description": "512x512 Game Tilemap Palette Stage with 16/32/64px tiles, solid/passable collision badges (X/O), window.setTileSvg(r,c,svg,solid), and #isolated-tile export."
    },
    {
        "template_id": "game_hud_ui_stage_640",
        "template_name": "template_game_hud_ui_stage.html",
        "category": "gaming_editor",
        "width_px": 640,
        "height_px": 480,
        "aspect_ratio": "4:3",
        "stage_selector": "#capture-stage",
        "bg_theme": "#000000",
        "description": "640x480 Game HUD & UI Stage with hearts, MP gauge, B/Y active item boxes, virtual gamepad controls, dialog letterbox, and #isolated-element export."
    }
]


def resolve_canonical_templates_dir() -> Optional[Path]:
    """Dynamically resolves the canonical Canvas_SVG_Capture_Templates directory without hardcoding."""
    env_res = os.environ.get("ADMIN_RESOURCES", "").strip()
    if env_res:
        cand = Path(env_res) / "Templates" / "Canvas_SVG_Capture_Templates"
        if cand.is_dir():
            return cand
    admin_root = _HERE.parent.parent.parent.parent
    cand2 = admin_root / "Resources" / "Templates" / "Canvas_SVG_Capture_Templates"
    if cand2.is_dir():
        return cand2
    return None


def list_gaming_editor_templates() -> List[Dict[str, Any]]:
    """Lists all registered Gaming_Editors templates in the catalog."""
    return [dict(t) for t in GAMING_EDITOR_TEMPLATES_CATALOG]


def get_gaming_editor_template_html(template_id: str) -> Optional[str]:
    """Retrieves the HTML markup for a given editor template from disk."""
    tpl_dir = resolve_canonical_templates_dir()
    for item in GAMING_EDITOR_TEMPLATES_CATALOG:
        if item["template_id"] == template_id or item["template_name"] == template_id:
            if tpl_dir is not None:
                p = tpl_dir / item["template_name"]
                if p.is_file():
                    return p.read_text(encoding="utf-8")
    return None


def instantiate_gaming_editor_stage(
    template_id: str,
    output_path: Path
) -> Path:
    """Instantiates a stage HTML file ready for browser execution."""
    html = get_gaming_editor_template_html(template_id)
    if not html:
        raise FileNotFoundError(f"Template '{template_id}' could not be resolved from templates directory.")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return output_path


# Name_Case Architectural Component Bindings
List_Gaming_Editor_Templates = list_gaming_editor_templates
Get_Gaming_Editor_Template_Html = get_gaming_editor_template_html
Instantiate_Gaming_Editor_Stage = instantiate_gaming_editor_stage
