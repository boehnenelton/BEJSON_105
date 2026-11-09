"""
Name:           custom_builder.py
Description:    Flask Blueprint for Custom Taxonomy Builder: interactive form to construct
                custom 105 taxonomies, define fields, assign templates, and materialize MTV units.
Version:        100
Author Credit:  Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
"""

import os
import sys
import json
from pathlib import Path
from flask import Blueprint, render_template, request, jsonify

CURRENT_DIR = Path(__file__).resolve().parent
CMS_DIR = CURRENT_DIR.parent.parent
if str(CMS_DIR) not in sys.path:
    sys.path.insert(0, str(CMS_DIR))

import lib_bejson_CMS_mtv_core as mtv_core
import lib_bejson_CMS_mtv_scaffold as mtv_scaffold

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

@custom_builder_bp.route("/api/custom/materialize", methods=["POST"])
def materialize_custom_taxonomy():
    payload = request.get_json()
    if not payload:
        return jsonify({"success": False, "error": "Missing JSON payload"}), 400

    target_path_str = payload.get("target_path", "").strip()
    archetype_id = payload.get("archetype_id", "custom_platform").strip().lower()
    archetype_name = payload.get("archetype_name", "Custom Platform").strip()
    domain_purpose = payload.get("domain_purpose", "Custom taxonomy platform.").strip()
    bound_templates = payload.get("bound_templates", ["scaffold_master_index.html"])
    entities_data = payload.get("entities", [])

    if not target_path_str or not entities_data:
        return jsonify({"success": False, "error": "target_path and entities are required"}), 400

    custom_archetype_definition = {
        "archetype_id": archetype_id,
        "archetype_name": archetype_name,
        "domain_purpose": domain_purpose,
        "canonical_entity_prefixes": {e.get("name"): e.get("prefix", f"{e.get('name').lower()}_") for e in entities_data},
        "bound_templates": bound_templates,
        "primary_renderer_class_name": "StandardPageRenderer",
        "entities": []
    }

    for ent in entities_data:
        ent_name = ent.get("name")
        prefix = ent.get("prefix", f"{ent_name.lower()}_")
        pk_col = f"{prefix}uuid"
        fields = [{"name": pk_col, "type": "string", "description": "Synthetic UUIDv4 PK"}]
        for fld in ent.get("fields", []):
            if fld.get("name") != pk_col:
                fields.append(fld)

        custom_archetype_definition["entities"].append({
            "entity_name": ent_name,
            "table_description": ent.get("description", f"Table for {ent_name}"),
            "primary_key_column_name": pk_col,
            "entity_prefix": prefix,
            "fields": fields
        })

    try:
        # Dynamically register custom archetype
        mtv_core.CANONICAL_MTV_ARCHETYPES_CATALOG[archetype_id] = custom_archetype_definition
        target_path = Path(target_path_str).resolve()
        synthesizer = mtv_scaffold.MTVScaffoldSynthesizer(target_path)
        report = synthesizer.instantiate_archetype_scaffold(archetype_id, archetype_name)
        return jsonify({"success": True, "report": report})
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500
