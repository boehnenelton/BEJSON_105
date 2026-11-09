"""
Name:           blueprints.py
Description:    Flask Blueprint for Blueprint Catalog: lists archetypes, previews schemas,
                and provides single-click instant instantiation.
Version:        100
Author Credit:  Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
"""

import os
import sys
from pathlib import Path
from flask import Blueprint, render_template, request, jsonify, redirect, url_for

# Ensure parent packages are in path
CURRENT_DIR = Path(__file__).resolve().parent
CMS_DIR = CURRENT_DIR.parent.parent
if str(CMS_DIR) not in sys.path:
    sys.path.insert(0, str(CMS_DIR))

import lib_bejson_CMS_mtv_core as mtv_core
import lib_bejson_CMS_mtv_scaffold as mtv_scaffold

blueprints_bp = Blueprint("blueprints_bp", __name__, template_folder="../templates")

@blueprints_bp.route("/")
def index():
    archetypes = mtv_core.bejson_cms_list_archetypes()
    return render_template("catalog.html", archetypes=archetypes)

@blueprints_bp.route("/archetype/<archetype_id>")
def archetype_detail(archetype_id):
    try:
        archetype = mtv_core.bejson_cms_get_archetype(archetype_id)
        return render_template("archetype_detail.html", archetype=archetype)
    except KeyError:
        return redirect(url_for("blueprints_bp.index"))

@blueprints_bp.route("/api/instantiate", methods=["POST"])
def instantiate_scaffold():
    data = request.get_json() or request.form
    archetype_id = data.get("archetype_id")
    target_path_str = data.get("target_path", "").strip()
    project_title = data.get("project_title", "").strip()

    if not archetype_id or not target_path_str:
        return jsonify({"success": False, "error": "archetype_id and target_path are required"}), 400

    target_path = Path(target_path_str).resolve()
    try:
        synthesizer = mtv_scaffold.MTVScaffoldSynthesizer(target_path)
        report = synthesizer.instantiate_archetype_scaffold(archetype_id, project_title)
        return jsonify({"success": True, "report": report})
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500
