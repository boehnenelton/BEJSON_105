"""
Name:           custom_builder.py
Description:    Flask Blueprint for Custom Taxonomy Builder: interactive form to construct
                custom 105 taxonomies, define fields, assign templates, and materialize MTV units.
Version:        101
Changelog:      101 (2026-11-12) strict validation of every user-supplied identifier, template allow-list, output-root confinement, bounded custom catalog
Author Credit:  Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
RELATIONAL_ID:  cf3d219f-4d5e-4e98-99c6-20e35767142f
"""

import os
import sys
import json
import logging
from pathlib import Path
from flask import Blueprint, render_template, request, jsonify, current_app

CURRENT_DIR = Path(__file__).resolve().parent
CMS_DIR = CURRENT_DIR.parent.parent
if str(CMS_DIR) not in sys.path:
    sys.path.insert(0, str(CMS_DIR))

import lib_bejson_CMS_mtv_core as mtv_core
import lib_bejson_CMS_mtv_scaffold as mtv_scaffold

logger = logging.getLogger(__name__)
MAX_CUSTOM_ENTITIES = 32
MAX_FIELDS_PER_ENTITY = 128
MAX_CUSTOM_ARCHETYPES = 64
_BUILTIN_ARCHETYPE_IDS = frozenset(mtv_core.CANONICAL_MTV_ARCHETYPES_CATALOG.keys())
_custom_archetype_ids = []  # insertion-ordered; oldest custom entry is evicted past the cap

custom_builder_bp = Blueprint("custom_builder_bp", __name__, template_folder="../templates")

AVAILABLE_TEMPLATES_LIST = [
    "scaffold_master_index.html",
    "scaffold_feed.html",
    "scaffold_category_feed.html",
    "scaffold_video_feed.html",
    "scaffold_image_feed.html",
    "scaffold_media_grid.html",
    "scaffold_content_page.html",
    "scaffold_document.html",
    "scaffold_blog_post.html",
    "scaffold_project_showcase.html",
    "scaffold_video_player.html",
    "scaffold_image_lightbox.html",
    "scaffold_consolidated_ebook.html"
]

@custom_builder_bp.route("/custom")
def custom_builder_page():
    return render_template("custom_builder.html", available_templates=AVAILABLE_TEMPLATES_LIST)

def _validated_entities(raw_entities):
    """Returns validated entity dicts or raises ValueError."""
    if not isinstance(raw_entities, list) or not raw_entities or len(raw_entities) > MAX_CUSTOM_ENTITIES:
        raise ValueError(f"entities must be a list of 1-{MAX_CUSTOM_ENTITIES} items")
    cleaned = []
    seen_names = set()
    for ent in raw_entities:
        if not isinstance(ent, dict):
            raise ValueError("each entity must be an object")
        name = mtv_core.bejson_cms_validate_identifier("entity_name", ent.get("name"))
        if name.lower() in seen_names:
            raise ValueError(f"duplicate entity name: {name}")
        seen_names.add(name.lower())
        prefix = ent.get("prefix") or f"{name.lower()}_"
        prefix = mtv_core.bejson_cms_validate_identifier("entity_prefix", prefix)
        raw_fields = ent.get("fields", [])
        if not isinstance(raw_fields, list) or len(raw_fields) > MAX_FIELDS_PER_ENTITY:
            raise ValueError(f"fields must be a list of at most {MAX_FIELDS_PER_ENTITY} items")
        fields = []
        for fld in raw_fields:
            if not isinstance(fld, dict):
                raise ValueError("each field must be an object")
            fname, ftype = fld.get("name"), fld.get("type", "string")
            if not isinstance(fname, str) or not mtv_core.SNAKE_CASE_PATTERN_REGEX.match(fname):
                raise ValueError(f"invalid field name: {fname!r}")
            if ftype not in mtv_core.ALLOWED_BEJSON_PRIMITIVE_TYPES:
                raise ValueError(f"invalid field type: {ftype!r}")
            fields.append({"name": fname, "type": ftype, "description": str(fld.get("description", ""))[:300]})
        cleaned.append({"name": name, "prefix": prefix, "fields": fields, "description": str(ent.get("description", f"Table for {name}"))[:300]})
    return cleaned


@custom_builder_bp.route("/api/custom/materialize", methods=["POST"])
def materialize_custom_taxonomy():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"success": False, "error": "Missing JSON payload"}), 400

    try:
        target_path_str = str(payload.get("target_path", "")).strip()
        archetype_id = mtv_core.bejson_cms_validate_identifier("archetype_id", str(payload.get("archetype_id", "custom_platform")).strip().lower())
        if archetype_id in _BUILTIN_ARCHETYPE_IDS:
            raise ValueError("archetype_id collides with a built-in archetype")
        archetype_name = str(payload.get("archetype_name", "Custom Platform")).strip()[:120] or "Custom Platform"
        domain_purpose = str(payload.get("domain_purpose", "Custom taxonomy platform.")).strip()[:300]
        bound_templates = payload.get("bound_templates", ["scaffold_master_index.html"])
        if not isinstance(bound_templates, list) or any(tpl not in AVAILABLE_TEMPLATES_LIST for tpl in bound_templates):
            raise ValueError("bound_templates must be a subset of the available template list")
        entities = _validated_entities(payload.get("entities", []))
        target_path = mtv_core.bejson_cms_resolve_confined_path(target_path_str, Path(current_app.config["MTV_OUTPUT_ROOT"]))
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400

    custom_archetype_definition = {
        "archetype_id": archetype_id,
        "archetype_name": archetype_name,
        "domain_purpose": domain_purpose,
        "canonical_entity_prefixes": {e["name"]: e["prefix"] for e in entities},
        "bound_templates": bound_templates,
        "primary_renderer_class_name": "StandardPageRenderer",
        "entities": [],
    }
    for ent in entities:
        pk_col = f"{ent['prefix']}uuid"
        fields = [{"name": pk_col, "type": "string", "description": "Synthetic UUIDv4 PK"}]
        fields.extend(f for f in ent["fields"] if f["name"] != pk_col)
        custom_archetype_definition["entities"].append({
            "entity_name": ent["name"],
            "table_description": ent["description"],
            "primary_key_column_name": pk_col,
            "entity_prefix": ent["prefix"],
            "fields": fields,
        })

    try:
        # Register the custom archetype (bounded; never replaces a built-in)
        mtv_core.CANONICAL_MTV_ARCHETYPES_CATALOG[archetype_id] = custom_archetype_definition
        if archetype_id in _custom_archetype_ids:
            _custom_archetype_ids.remove(archetype_id)
        _custom_archetype_ids.append(archetype_id)
        while len(_custom_archetype_ids) > MAX_CUSTOM_ARCHETYPES:
            mtv_core.CANONICAL_MTV_ARCHETYPES_CATALOG.pop(_custom_archetype_ids.pop(0), None)
        synthesizer = mtv_scaffold.MTVScaffoldSynthesizer(target_path)
        report = synthesizer.instantiate_archetype_scaffold(archetype_id, archetype_name)
        return jsonify({"success": True, "report": report})
    except Exception:
        logger.exception("Custom materialize failed for %r", archetype_id)
        return jsonify({"success": False, "error": "Materialization failed; see server log"}), 500
