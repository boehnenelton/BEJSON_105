"""
Name:           exporter.py
Description:    Flask Blueprint for Project Exporter: packages scaffolded MTV units
                into verified standalone ZIP archives.
Version:        100
Author Credit:  Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
"""

import os
import sys
import shutil
import zipfile
from pathlib import Path
from flask import Blueprint, request, jsonify, send_file

exporter_bp = Blueprint("exporter_bp", __name__)

@exporter_bp.route("/api/export", methods=["POST"])
def export_project_zip():
    data = request.get_json() or request.form
    project_dir_str = data.get("project_directory", "").strip()
    destination_archive_path_str = data.get("destination_archive_path", "").strip()

    if not project_dir_str:
        return jsonify({"success": False, "error": "project_directory is required"}), 400

    project_dir = Path(project_dir_str).resolve()
    if not project_dir.exists() or not project_dir.is_dir():
        return jsonify({"success": False, "error": f"Directory not found: {project_dir}"}), 404

    if not destination_archive_path_str:
        destination_archive_path = project_dir.parent / f"{project_dir.name}.zip"
    else:
        destination_archive_path = Path(destination_archive_path_str).resolve()

    destination_archive_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with zipfile.ZipFile(destination_archive_path, "w", zipfile.ZIP_DEFLATED) as zip_handle:
            for root, _, files in os.walk(str(project_dir)):
                for file_name in files:
                    if file_name.endswith((".pyc", ".tmp", ".lock")):
                        continue
                    file_full_path = Path(root) / file_name
                    archive_relative_path = file_full_path.relative_to(project_dir)
                    zip_handle.write(file_full_path, archive_relative_path)

        return jsonify({
            "success": True,
            "archive_path": str(destination_archive_path),
            "archive_size_bytes": destination_archive_path.stat().st_size
        })
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500
