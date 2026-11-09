"""
Name:           lib_bejson_CMS_mtv_validator.py
Family:         CMS
Module Purpose: Structural and schema validator for 105 CMS MTV packages, manifests,
                entity tables, referential integrity links, and template bindings.
Version:        100
Release_Version: 300
Date Created:   2026-11-06
Author Credit:  Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
RELATIONAL_ID:  f1839a24-8172-4e09-bca1-6284f18d7934
"""

from __future__ import annotations

import os
import sys
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

CURRENT_MODULE_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
LIBRARIES_105_ROOT_DIRECTORY = os.path.normpath(os.path.join(CURRENT_MODULE_DIRECTORY, "..", ".."))
LIB_PY_DIRECTORY = os.path.join(LIBRARIES_105_ROOT_DIRECTORY, "Lib_PY")

for sibling_family_folder_name in ("Core", "CMS", "Taxonomies", "Tax_Scaffolds", "Standards", "Canvas", "Graphics"):
    resolved_family_path = os.path.join(LIB_PY_DIRECTORY, sibling_family_folder_name)
    if os.path.isdir(resolved_family_path) and resolved_family_path not in sys.path:
        sys.path.insert(0, resolved_family_path)

import lib_bejson_CMS_mtv_core as mtv_core
from lib_bejson_Core_bejson_core import bejson_core_load_file, bejson_core_get_field_map
from lib_bejson_Core_mfdb_validator import mfdb_validator_validate_manifest, mfdb_validator_check_referential_integrity


def validate_mtv_project_scaffold(project_root_directory_path: Path) -> Dict[str, Any]:
    """
    Performs a comprehensive validation audit across Model, Template, and View:
    1. Audits MFDB v1.40 manifest (105a.mfdb.bejson).
    2. Validates Format 105 entity tables (field_uuid, record_uuid, Parent_Hierarchy).
    3. Runs referential integrity checks on foreign keys.
    4. Audits templates for zero filler using scaffold_fluff_linter.
    5. Confirms build_site.py exists.
    """
    project_root = Path(project_root_directory_path).resolve()
    problems_list: List[str] = []
    manifest_path = project_root / "storage" / "mfdb" / "105a.mfdb.bejson"
    if not manifest_path.exists():
        manifest_path = project_root / "storage" / "mfdb" / "104a.mfdb.bejson"

    # 1. Manifest verification
    if not manifest_path.exists():
        problems_list.append(f"Missing MFDB manifest at expected location: {project_root / 'storage' / 'mfdb'}")
        return {"passed": False, "problems": problems_list, "checks_executed": 1}

    try:
        manifest_doc = bejson_core_load_file(str(manifest_path))
        if manifest_doc.get("Format") != "BEJSON":
            problems_list.append("Manifest 'Format' must be 'BEJSON'.")
        if manifest_doc.get("Format_Version") not in ("105a", "104a"):
            problems_list.append(f"Manifest 'Format_Version' must be '105a' (found '{manifest_doc.get('Format_Version')}').")
        if manifest_doc.get("MFDB_Version") != "1.40":
            problems_list.append(f"Manifest 'MFDB_Version' must be '1.40' (found '{manifest_doc.get('MFDB_Version')}').")
    except Exception as exc:
        problems_list.append(f"Failed to load manifest JSON: {exc}")
        return {"passed": False, "problems": problems_list, "checks_executed": 1}

    # 2. Entity table verification
    manifest_fmap = bejson_core_get_field_map(manifest_doc)
    registered_entities = []
    for row in manifest_doc.get("Values", []):
        entity_name = row[manifest_fmap["entity_name"]]
        rel_file_path = row[manifest_fmap["file_path"]]
        registered_entities.append(entity_name)
        abs_table_path = manifest_path.parent / rel_file_path
        if not abs_table_path.exists():
            problems_list.append(f"Registered entity file missing on disk: {abs_table_path}")
            continue

        try:
            table_doc = bejson_core_load_file(str(abs_table_path))
            if table_doc.get("Format_Version") != "105":
                problems_list.append(f"Entity '{entity_name}' Format_Version must be '105' (found '{table_doc.get('Format_Version')}').")
            if table_doc.get("Parent_Hierarchy") not in ("../105a.mfdb.bejson", "../104a.mfdb.bejson"):
                problems_list.append(f"Entity '{entity_name}' Parent_Hierarchy must point to '../105a.mfdb.bejson' or '../104a.mfdb.bejson'.")

            # Check field_uuid on all fields
            for fld in table_doc.get("Fields", []):
                fuuid = fld.get("field_uuid")
                if not fuuid or not mtv_core.UUID4_PATTERN_REGEX.match(fuuid):
                    problems_list.append(f"Entity '{entity_name}' field '{fld.get('name')}' missing valid RFC 4122 v4 field_uuid.")

            # Check record_uuid at col 0 for all rows
            for row_idx, r in enumerate(table_doc.get("Values", [])):
                if not r or not mtv_core.UUID4_PATTERN_REGEX.match(str(r[0])):
                    problems_list.append(f"Entity '{entity_name}' row {row_idx} column 0 is not a valid RFC 4122 v4 record_uuid.")
        except Exception as table_exc:
            problems_list.append(f"Failed to validate entity table '{entity_name}': {table_exc}")

    # 3. Active referential integrity check
    try:
        ref_errors = mfdb_validator_check_referential_integrity(str(manifest_path))
        if ref_errors:
            for err in ref_errors:
                problems_list.append(f"Referential integrity defect: {err.get('code')}: {err.get('detail')}")
    except Exception as ref_exc:
        problems_list.append(f"Error during referential integrity audit: {ref_exc}")

    # 4. Templates & Zero-fluff check
    templates_dir = project_root / "templates"
    if not templates_dir.exists():
        problems_list.append(f"Missing templates directory at: {templates_dir}")
    else:
        try:
            try:
                from scaffold_fluff_linter import audit_template
            except ImportError:
                import importlib.util
                linter_path = os.path.join(CURRENT_MODULE_DIRECTORY, "scaffold_fluff_linter.py")
                spec = importlib.util.spec_from_file_location("scaffold_fluff_linter", linter_path)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                audit_template = mod.audit_template
            for tmpl_file in templates_dir.glob("*.html"):
                findings = audit_template(tmpl_file)
                for finding in findings:
                    problems_list.append(f"Template fluff defect in '{tmpl_file.name}': {finding}")
        except Exception as linter_exc:
            problems_list.append(f"Failed to execute fluff linter: {linter_exc}")

    # 5. Build script existence
    build_script = project_root / "build_site.py"
    if not build_script.exists():
        problems_list.append(f"Missing build script: {build_script}")

    is_valid = len(problems_list) == 0
    return {
        "passed": is_valid,
        "problems": problems_list,
        "registered_entities": registered_entities,
        "checks_executed": 5
    }
