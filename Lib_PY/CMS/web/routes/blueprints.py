"""
Name:           blueprints.py
Description:    Flask Blueprint for Blueprint Catalog: lists archetypes, previews schemas,
                and provides single-click instant instantiation.
Version:        101
Changelog:      101 (2026-11-12) output-root confinement, input validation, no exception text leaked to clients
Author Credit:  Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
RELATIONAL_ID:  6ae4684a-2731-416b-99cf-3b46aaf03ade
"""

import os
import sys
import logging
from pathlib import Path
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, current_app

# Ensure parent packages are in path
CURRENT_DIR = Path(__file__).resolve().parent
CMS_DIR = CURRENT_DIR.parent.parent
if str(CMS_DIR) not in sys.path:
    sys.path.insert(0, str(CMS_DIR))

import lib_bejson_CMS_mtv_core as mtv_core
import lib_bejson_CMS_mtv_scaffold as mtv_scaffold

logger = logging.getLogger(__name__)
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
    data = request.get_json(silent=True) or request.form
    archetype_id = str(data.get("archetype_id", "")).strip()
    target_path_str = str(data.get("target_path", "")).strip()
    project_title = str(data.get("project_title", "")).strip()[:200]

    if not archetype_id or not target_path_str:
        return jsonify({"success": False, "error": "archetype_id and target_path are required"}), 400

    try:
        target_path = mtv_core.bejson_cms_resolve_confined_path(target_path_str, Path(current_app.config["MTV_OUTPUT_ROOT"]))
        synthesizer = mtv_scaffold.MTVScaffoldSynthesizer(target_path)
        report = synthesizer.instantiate_archetype_scaffold(archetype_id, project_title)
        return jsonify({"success": True, "report": report})
    except KeyError as exc:
        return jsonify({"success": False, "error": str(exc.args[0]) if exc.args else "Unknown archetype"}), 404
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception:
        logger.exception("Instantiate failed for archetype %r", archetype_id)
        return jsonify({"success": False, "error": "Instantiation failed; see server log"}), 500
