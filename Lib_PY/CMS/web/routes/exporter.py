"""
Name:           exporter.py
Description:    Flask Blueprint for Project Exporter: packages scaffolded MTV units into verified standalone ZIP archives (confined to the configured output root).
Version:        101
Changelog:      101 (2026-11-12) output-root confinement, input validation, no exception text leaked to clients
Author Credit:  Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
RELATIONAL_ID:  c2c8a410-98ba-40e6-8e00-8b8fea2e4599
"""

import os
import sys
import logging
import zipfile
from pathlib import Path
from flask import Blueprint, request, jsonify, current_app

CURRENT_DIR = Path(__file__).resolve().parent
CMS_DIR = CURRENT_DIR.parent.parent
if str(CMS_DIR) not in sys.path:
    sys.path.insert(0, str(CMS_DIR))

import lib_bejson_CMS_mtv_core as mtv_core

logger = logging.getLogger(__name__)
exporter_bp = Blueprint("exporter_bp", __name__)

SKIPPED_FILE_SUFFIXES = (".pyc", ".tmp", ".lock")


def _output_root() -> Path:
    return Path(current_app.config["MTV_OUTPUT_ROOT"]).resolve()


@exporter_bp.route("/api/export", methods=["POST"])
def export_project_zip():
    data = request.get_json(silent=True) or request.form
    project_dir_str = str(data.get("project_directory", "")).strip()
    destination_archive_path_str = str(data.get("destination_archive_path", "")).strip()

    if not project_dir_str:
        return jsonify({"success": False, "error": "project_directory is required"}), 400

    root = _output_root()
    try:
        project_dir = mtv_core.bejson_cms_resolve_confined_path(project_dir_str, root)
        if project_dir == root:
            raise ValueError("project_directory must be a sub-directory of the output root")
        if destination_archive_path_str:
            destination_archive_path = mtv_core.bejson_cms_resolve_confined_path(destination_archive_path_str, root)
        else:
            destination_archive_path = root / f"{project_dir.name}.zip"
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400

    if not project_dir.is_dir():
        return jsonify({"success": False, "error": "Directory not found inside the output root"}), 404
    if destination_archive_path.suffix.lower() != ".zip":
        return jsonify({"success": False, "error": "destination_archive_path must end with .zip"}), 400
    if destination_archive_path == project_dir or project_dir in destination_archive_path.parents:
        return jsonify({"success": False, "error": "archive may not be written inside the project being exported"}), 400

    try:
        destination_archive_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_archive_path = destination_archive_path.with_name(destination_archive_path.name + f".{os.getpid()}.tmp")
        with zipfile.ZipFile(temporary_archive_path, "w", zipfile.ZIP_DEFLATED) as zip_handle:
            for walk_root, _, files in os.walk(str(project_dir), followlinks=False):
                for file_name in files:
                    if file_name.endswith(SKIPPED_FILE_SUFFIXES):
                        continue
                    file_full_path = Path(walk_root) / file_name
                    if file_full_path.is_symlink():
                        continue  # never follow links out of the project tree
                    zip_handle.write(file_full_path, file_full_path.relative_to(project_dir))
        os.replace(temporary_archive_path, destination_archive_path)
        return jsonify({
            "success": True,
            "archive_path": str(destination_archive_path),
            "archive_size_bytes": destination_archive_path.stat().st_size,
        })
    except Exception:
        logger.exception("Export failed for %s", project_dir)
        return jsonify({"success": False, "error": "Export failed; see server log"}), 500
