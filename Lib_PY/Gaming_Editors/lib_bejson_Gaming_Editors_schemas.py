"""
Library:        lib_bejson_Gaming_Editors_schemas.py
Family:         Gaming_Editors
Description:    BEJSON 105a Schema Definitions and O(1) Field Map Caching for Game Editors:
                Sprite Studio, Tilemap Palette Studio, HUD Stage Studio, and Animation Studio.
BEJSON:         BEJSON stands for BOEHNEN ELTON JSON. Authoritative definition;
                do not restate or reinterpret this acronym elsewhere.
                (Pronounced Bee-Jay-Son / Bay-nin Elton JSON)
MFDB:           MFDB stands for Multi File Database. Authoritative definition;
                do not restate or reinterpret this acronym elsewhere.
Version:        1.0.0
Date:           2026-11-15
Author:         Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
License:        PolyForm-Noncommercial-1.0.0
RELATIONAL_ID:  8c0b2d3e-4f5a-6b7c-8d9e-0f1a2b3c4d5e
Release_Version: 300
"""

from __future__ import annotations

import json
import logging
import os
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
for _fam in ('Core', 'Standards', 'Taxonomies', 'Graphics', 'Gaming_Editors'):
    _p = os.path.normpath(os.path.join(_HERE, "..", _fam))
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

logger = logging.getLogger("lib_bejson_Gaming_Editors_schemas")
VERSION = "1.0.0"

# ---------------------------------------------------------------------------
# Canonical BEJSON 105a Field Definitions with Unique UUIDv4 field_uuid
# ---------------------------------------------------------------------------

GAMING_SPRITE_STUDIO_FIELDS: List[Dict[str, str]] = [
    {"name": "editor_id",        "type": "string",  "field_uuid": "c1a2b3c4-1111-4000-8000-000000000001"},
    {"name": "template_name",    "type": "string",  "field_uuid": "c1a2b3c4-1111-4000-8000-000000000002"},
    {"name": "canvas_size_px",   "type": "integer", "field_uuid": "c1a2b3c4-1111-4000-8000-000000000003"},
    {"name": "cell_size_px",     "type": "integer", "field_uuid": "c1a2b3c4-1111-4000-8000-000000000004"},
    {"name": "grid_rows",        "type": "integer", "field_uuid": "c1a2b3c4-1111-4000-8000-000000000005"},
    {"name": "grid_cols",        "type": "integer", "field_uuid": "c1a2b3c4-1111-4000-8000-000000000006"},
    {"name": "bg_theme",         "type": "string",  "field_uuid": "c1a2b3c4-1111-4000-8000-000000000007"},
    {"name": "accent_color",     "type": "string",  "field_uuid": "c1a2b3c4-1111-4000-8000-000000000008"},
    {"name": "show_grid",        "type": "boolean", "field_uuid": "c1a2b3c4-1111-4000-8000-000000000009"},
    {"name": "cells_json",       "type": "string",  "field_uuid": "c1a2b3c4-1111-4000-8000-000000000010"},
    {"name": "output_path",      "type": "string",  "field_uuid": "c1a2b3c4-1111-4000-8000-000000000011"}
]

GAMING_TILEMAP_PALETTE_FIELDS: List[Dict[str, str]] = [
    {"name": "palette_id",       "type": "string",  "field_uuid": "c2a3b4c5-2222-4000-8000-000000000001"},
    {"name": "template_name",    "type": "string",  "field_uuid": "c2a3b4c5-2222-4000-8000-000000000002"},
    {"name": "canvas_size_px",   "type": "integer", "field_uuid": "c2a3b4c5-2222-4000-8000-000000000003"},
    {"name": "tile_size_px",     "type": "integer", "field_uuid": "c2a3b4c5-2222-4000-8000-000000000004"},
    {"name": "palette_rows",     "type": "integer", "field_uuid": "c2a3b4c5-2222-4000-8000-000000000005"},
    {"name": "palette_cols",     "type": "integer", "field_uuid": "c2a3b4c5-2222-4000-8000-000000000006"},
    {"name": "show_collision",   "type": "boolean", "field_uuid": "c2a3b4c5-2222-4000-8000-000000000007"},
    {"name": "tiles_json",       "type": "string",  "field_uuid": "c2a3b4c5-2222-4000-8000-000000000008"},
    {"name": "output_path",      "type": "string",  "field_uuid": "c2a3b4c5-2222-4000-8000-000000000009"}
]

GAMING_HUD_STAGE_FIELDS: List[Dict[str, str]] = [
    {"name": "hud_id",           "type": "string",  "field_uuid": "c3a4b5c6-3333-4000-8000-000000000001"},
    {"name": "template_name",    "type": "string",  "field_uuid": "c3a4b5c6-3333-4000-8000-000000000002"},
    {"name": "width_px",         "type": "integer", "field_uuid": "c3a4b5c6-3333-4000-8000-000000000003"},
    {"name": "height_px",        "type": "integer", "field_uuid": "c3a4b5c6-3333-4000-8000-000000000004"},
    {"name": "aspect_ratio",     "type": "string",  "field_uuid": "c3a4b5c6-3333-4000-8000-000000000005"},
    {"name": "max_hearts",       "type": "integer", "field_uuid": "c3a4b5c6-3333-4000-8000-000000000006"},
    {"name": "current_hearts",   "type": "number",  "field_uuid": "c3a4b5c6-3333-4000-8000-000000000007"},
    {"name": "has_magic_gauge",  "type": "boolean", "field_uuid": "c3a4b5c6-3333-4000-8000-000000000008"},
    {"name": "item_slots_json",  "type": "string",  "field_uuid": "c3a4b5c6-3333-4000-8000-000000000009"},
    {"name": "dialog_state_json","type": "string",  "field_uuid": "c3a4b5c6-3333-4000-8000-000000000010"},
    {"name": "output_path",      "type": "string",  "field_uuid": "c3a4b5c6-3333-4000-8000-000000000011"}
]

# ---------------------------------------------------------------------------
# O(1) Field Map Compiler (Format 105a: index 0 is reserved for record_uuid)
# ---------------------------------------------------------------------------

def build_field_map_105(fields: Any) -> Dict[str, int]:
    """
    Compiles an O(1) field map for a BEJSON 105a table or document.
    In Format 105a, row[0] is strictly the record_uuid.
    The named fields start at row offset 1.
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
# Schema Builder Functions
# ---------------------------------------------------------------------------

def create_sprite_studio_config_105a(
    editor_id: str = "sprite_studio_01",
    template_name: str = "template_game_sprite_sheet_studio.html",
    canvas_size_px: int = 512,
    cell_size_px: int = 32,
    bg_theme: str = "#000000",
    accent_color: str = "#DE2626",
    show_grid: bool = True,
    cells_data: Optional[List[Dict[str, Any]]] = None,
    output_path: str = "captures/game_sprite_sheet_512x512.png"
) -> Dict[str, Any]:
    """Instantiates a valid BEJSON 105a Game Sprite Studio configuration document."""
    record_uuid = str(uuid.uuid4())
    rows = canvas_size_px // cell_size_px
    cols = canvas_size_px // cell_size_px
    cells_json = json.dumps(cells_data) if cells_data else "[]"

    values_row = [
        record_uuid,
        editor_id,
        template_name,
        int(canvas_size_px),
        int(cell_size_px),
        int(rows),
        int(cols),
        bg_theme,
        accent_color,
        bool(show_grid),
        cells_json,
        output_path
    ]

    return {
        "Format": "BEJSON",
        "Format_Version": "105a",
        "Format_Creator": "Elton Boehnen",
        "Records_Type": ["GamingSpriteStudioConfig"],
        "Fields": [dict(f) for f in GAMING_SPRITE_STUDIO_FIELDS],
        "Values": [values_row]
    }


def create_tilemap_palette_config_105a(
    palette_id: str = "tilemap_palette_01",
    template_name: str = "template_game_tilemap_palette_stage.html",
    canvas_size_px: int = 512,
    tile_size_px: int = 32,
    show_collision: bool = True,
    tiles_data: Optional[List[Dict[str, Any]]] = None,
    output_path: str = "captures/game_tilemap_palette_512x512.png"
) -> Dict[str, Any]:
    """Instantiates a valid BEJSON 105a Tilemap Palette Studio configuration document."""
    record_uuid = str(uuid.uuid4())
    rows = canvas_size_px // tile_size_px
    cols = canvas_size_px // tile_size_px
    tiles_json = json.dumps(tiles_data) if tiles_data else "[]"

    values_row = [
        record_uuid,
        palette_id,
        template_name,
        int(canvas_size_px),
        int(tile_size_px),
        int(rows),
        int(cols),
        bool(show_collision),
        tiles_json,
        output_path
    ]

    return {
        "Format": "BEJSON",
        "Format_Version": "105a",
        "Format_Creator": "Elton Boehnen",
        "Records_Type": ["GamingTilemapPaletteConfig"],
        "Fields": [dict(f) for f in GAMING_TILEMAP_PALETTE_FIELDS],
        "Values": [values_row]
    }


def create_hud_stage_config_105a(
    hud_id: str = "hud_stage_01",
    template_name: str = "template_game_hud_ui_stage.html",
    width_px: int = 640,
    height_px: int = 480,
    aspect_ratio: str = "4:3",
    max_hearts: int = 4,
    current_hearts: float = 3.0,
    has_magic_gauge: bool = True,
    item_slots: Optional[List[Dict[str, Any]]] = None,
    dialog_state: Optional[Dict[str, Any]] = None,
    output_path: str = "captures/game_hud_ui_640x480.png"
) -> Dict[str, Any]:
    """Instantiates a valid BEJSON 105a Game HUD Stage configuration document."""
    record_uuid = str(uuid.uuid4())
    items_json = json.dumps(item_slots) if item_slots else "[]"
    dialog_json = json.dumps(dialog_state) if dialog_state else "{}"

    values_row = [
        record_uuid,
        hud_id,
        template_name,
        int(width_px),
        int(height_px),
        aspect_ratio,
        int(max_hearts),
        float(current_hearts),
        bool(has_magic_gauge),
        items_json,
        dialog_json,
        output_path
    ]

    return {
        "Format": "BEJSON",
        "Format_Version": "105a",
        "Format_Creator": "Elton Boehnen",
        "Records_Type": ["GamingHudStageConfig"],
        "Fields": [dict(f) for f in GAMING_HUD_STAGE_FIELDS],
        "Values": [values_row]
    }


# ---------------------------------------------------------------------------
# 4. Projectile Impact Dynamics Schema (105a)
# ---------------------------------------------------------------------------

PROJECTILE_IMPACT_DYNAMICS_FIELDS: List[Dict[str, str]] = [
    {"name": "object_type", "type": "string", "field_uuid": "c4a5b6c7-4444-4000-8000-000000000001"},
    {"name": "surface_hardness", "type": "number", "field_uuid": "c4a5b6c7-4444-4000-8000-000000000002"},
    {"name": "penetration_behavior", "type": "string", "field_uuid": "c4a5b6c7-4444-4000-8000-000000000003"},
    {"name": "damage_multiplier", "type": "number", "field_uuid": "c4a5b6c7-4444-4000-8000-000000000004"},
    {"name": "splash_particle_count", "type": "integer", "field_uuid": "c4a5b6c7-4444-4000-8000-000000000005"},
    {"name": "kinetic_recoil_factor", "type": "number", "field_uuid": "c4a5b6c7-4444-4000-8000-000000000006"},
    {"name": "primary_particle_color", "type": "string", "field_uuid": "c4a5b6c7-4444-4000-8000-000000000007"},
    {"name": "secondary_particle_color", "type": "string", "field_uuid": "c4a5b6c7-4444-4000-8000-000000000008"},
    {"name": "impact_vfx_preset", "type": "string", "field_uuid": "c4a5b6c7-4444-4000-8000-000000000009"},
    {"name": "sound_cue_id", "type": "string", "field_uuid": "c4a5b6c7-4444-4000-8000-000000000010"},
    {"name": "quiver_vibration_ms", "type": "integer", "field_uuid": "c4a5b6c7-4444-4000-8000-000000000011"},
    {"name": "status_debuff_inflicted", "type": "string", "field_uuid": "c4a5b6c7-4444-4000-8000-000000000012"}
]

PROJECTILE_IMPACT_DYNAMICS_FIELD_MAP: Dict[str, int] = build_field_map_105(PROJECTILE_IMPACT_DYNAMICS_FIELDS)


def create_projectile_impact_registry_105a(entries: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Generates a valid BEJSON 105a Projectile Impact Dynamics registry."""
    if entries is None:
        entries = [
            {
                "object_type": "flesh_organic",
                "surface_hardness": 0.15,
                "penetration_behavior": "embed",
                "damage_multiplier": 1.5,
                "splash_particle_count": 24,
                "kinetic_recoil_factor": 0.1,
                "primary_particle_color": "#DE2626",
                "secondary_particle_color": "#000000",
                "impact_vfx_preset": "vfx_puncture_bleed",
                "sound_cue_id": "sfx_flesh_pierce_01",
                "quiver_vibration_ms": 200,
                "status_debuff_inflicted": "bleed_slow"
            },
            {
                "object_type": "stone_masonry",
                "surface_hardness": 0.90,
                "penetration_behavior": "shatter",
                "damage_multiplier": 0.25,
                "splash_particle_count": 18,
                "kinetic_recoil_factor": 0.7,
                "primary_particle_color": "#FFFFFF",
                "secondary_particle_color": "#64748B",
                "impact_vfx_preset": "vfx_flint_shatter",
                "sound_cue_id": "sfx_stone_chink_01",
                "quiver_vibration_ms": 0,
                "status_debuff_inflicted": "none"
            },
            {
                "object_type": "wood_barrier",
                "surface_hardness": 0.45,
                "penetration_behavior": "embed",
                "damage_multiplier": 0.85,
                "splash_particle_count": 14,
                "kinetic_recoil_factor": 0.4,
                "primary_particle_color": "#A16207",
                "secondary_particle_color": "#78350F",
                "impact_vfx_preset": "vfx_grain_splinter",
                "sound_cue_id": "sfx_wood_thud_01",
                "quiver_vibration_ms": 350,
                "status_debuff_inflicted": "none"
            },
            {
                "object_type": "metal_shield",
                "surface_hardness": 0.98,
                "penetration_behavior": "ricochet",
                "damage_multiplier": 0.05,
                "splash_particle_count": 32,
                "kinetic_recoil_factor": 0.95,
                "primary_particle_color": "#FDE047",
                "secondary_particle_color": "#FFFFFF",
                "impact_vfx_preset": "vfx_shield_ricochet",
                "sound_cue_id": "sfx_metal_clang_01",
                "quiver_vibration_ms": 0,
                "status_debuff_inflicted": "stun_deflect"
            }
        ]

    rows = []
    for idx, e in enumerate(entries):
        rec_uuid = f"a0110001-{idx+1:04d}-4000-8000-{idx+1:012d}"
        row = [None] * (len(PROJECTILE_IMPACT_DYNAMICS_FIELDS) + 1)
        row[PROJECTILE_IMPACT_DYNAMICS_FIELD_MAP["record_uuid"]] = rec_uuid
        row[PROJECTILE_IMPACT_DYNAMICS_FIELD_MAP["object_type"]] = str(e.get("object_type", "unknown"))
        row[PROJECTILE_IMPACT_DYNAMICS_FIELD_MAP["surface_hardness"]] = float(e.get("surface_hardness", 0.5))
        row[PROJECTILE_IMPACT_DYNAMICS_FIELD_MAP["penetration_behavior"]] = str(e.get("penetration_behavior", "embed"))
        row[PROJECTILE_IMPACT_DYNAMICS_FIELD_MAP["damage_multiplier"]] = float(e.get("damage_multiplier", 1.0))
        row[PROJECTILE_IMPACT_DYNAMICS_FIELD_MAP["splash_particle_count"]] = int(e.get("splash_particle_count", 10))
        row[PROJECTILE_IMPACT_DYNAMICS_FIELD_MAP["kinetic_recoil_factor"]] = float(e.get("kinetic_recoil_factor", 0.5))
        row[PROJECTILE_IMPACT_DYNAMICS_FIELD_MAP["primary_particle_color"]] = str(e.get("primary_particle_color", "#FFFFFF"))
        row[PROJECTILE_IMPACT_DYNAMICS_FIELD_MAP["secondary_particle_color"]] = str(e.get("secondary_particle_color", "#000000"))
        row[PROJECTILE_IMPACT_DYNAMICS_FIELD_MAP["impact_vfx_preset"]] = str(e.get("impact_vfx_preset", "default"))
        row[PROJECTILE_IMPACT_DYNAMICS_FIELD_MAP["sound_cue_id"]] = str(e.get("sound_cue_id", "default"))
        row[PROJECTILE_IMPACT_DYNAMICS_FIELD_MAP["quiver_vibration_ms"]] = int(e.get("quiver_vibration_ms", 0))
        row[PROJECTILE_IMPACT_DYNAMICS_FIELD_MAP["status_debuff_inflicted"]] = str(e.get("status_debuff_inflicted", "none"))
        rows.append(row)

    return {
        "Format": "BEJSON",
        "Format_Version": "105a",
        "Format_Creator": "Elton Boehnen",
        "Records_Type": ["ProjectileImpactDynamics"],
        "Schema_Name": "Projectile_Impact_Dynamics_Registry",
        "Schema_Version": "10501",
        "Fields": [dict(f) for f in PROJECTILE_IMPACT_DYNAMICS_FIELDS],
        "Values": rows
    }


# Name_Case Architectural Component Bindings
Build_Field_Map_105 = build_field_map_105
Create_Sprite_Studio_Config_105a = create_sprite_studio_config_105a
Create_Tilemap_Palette_Config_105a = create_tilemap_palette_config_105a
Create_Hud_Stage_Config_105a = create_hud_stage_config_105a
Create_Projectile_Impact_Registry_105a = create_projectile_impact_registry_105a

