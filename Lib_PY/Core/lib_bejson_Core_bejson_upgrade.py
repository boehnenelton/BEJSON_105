"""
Library:        lib_bejson_Core_bejson_upgrade.py
Family:         Core
Description:    Canonical 104/104a/104db -> 105/105a/105db migration utility
                 (Format105_Master_Plan_Rev2, Phase 4, \u00a74.1). The one
                 function every existing database passes through exactly
                 once. Never mutates the source file directly: the new
                 105-series document is built entirely in memory, validated,
                 backed up, and only then atomically swapped into place.
Version:        1.0.2
Date:           2026-08-15
Author:         Elton Boehnen
Contact:        eltonboehnen@gmail.com | boehnenelton2024.pages.dev | github.com/boehnenelton
Format_Creator: Elton Boehnen
RELATIONAL_ID:  e32f5844-3372-4c5c-b12a-12068eee4c0e
Release_Version: 300

Changelog:
  1.0.2 - upgrade_to_105() returns a document whose field map is already
          built (born warm); see core.py 3.4.0 self-maintaining field map.

Changelog:
  1.0.0 - Initial delivery. Rollback (Rev. 2, Finding 2.1): the original file
          is copied verbatim to Backups/<filename>.104.bak, a dedicated
          directory sibling to the source, before the atomic swap -- so a
          downgrade is a plain file copy, not a re-derivation.
  1.0.1 - Audit fix (2026-08-16): 104a sources were silently collapsing to
          "105" instead of "105a" -- a bug inherited verbatim from the
          master plan's own \u00a74.1 example code (is_multi only distinguished
          104db, never 104a). Both upgrade_to_105() and upgrade_dry_run()
          now map 104->105 / 104a->105a / 104db->105db explicitly. Also
          removed an unused `from typing import Optional` import (nothing
          in this file uses typing; all hints are builtin `dict`).
"""

import os
import json
import uuid as _uuid
import tempfile
import shutil

from lib_bejson_Core_bejson_core import bejson_core_serialize, _bejson_get_field_map_cache
from lib_bejson_Core_bejson_validator import bejson_validator_check_105_strict_integrity
from lib_bejson_Core_bejson_errors import E_FORMAT_UNSUPPORTED, E_UPGRADE_VALIDATION_FAILED


class BEJSONUpgradeError(Exception):
    def __init__(self, message: str, code: int = None):
        super().__init__(message)
        self.code = code


def bejson_core_upgrade_to_105(doc_data: dict, source_path: str) -> dict:
    """
    Upgrades a 104/104a/104db document to 105/105a/105db in memory, validates
    it, backs up the original to Backups/<filename>.104.bak, then atomically
    swaps the upgraded document into place at source_path. Raises
    BEJSONUpgradeError (E_UPGRADE_VALIDATION_FAILED) and leaves the original
    file completely untouched if the built document fails strict-integrity
    validation -- there is no partial-upgrade state observable on disk.
    """
    if doc_data.get("Format_Version") not in ("104", "104a", "104db"):
        raise BEJSONUpgradeError(
            f"E_FORMAT_UNSUPPORTED: upgrade_to_105 takes a 104-series doc, "
            f"got {doc_data.get('Format_Version')!r}",
            code=E_FORMAT_UNSUPPORTED,
        )

    src_version = doc_data["Format_Version"]
    is_multi = src_version == "104db"
    target_version = {"104": "105", "104a": "105a", "104db": "105db"}[src_version]
    new_doc = dict(doc_data)  # shallow copy; Fields/Values rebuilt below

    new_fields = []
    for field in doc_data["Fields"]:
        new_fields.append({**field, "field_uuid": str(_uuid.uuid4())})
    new_doc["Fields"] = new_fields

    new_values = []
    for row in doc_data["Values"]:
        record_uuid = str(_uuid.uuid4())
        if is_multi:
            new_row = [row[0], record_uuid] + list(row[1:])  # keep discriminator at 0
        else:
            new_row = [record_uuid] + list(row)
        new_values.append(new_row)
    new_doc["Values"] = new_values

    new_doc["Format_Version"] = target_version

    errors = bejson_validator_check_105_strict_integrity(new_doc)
    if errors:
        raise BEJSONUpgradeError(f"E_UPGRADE_VALIDATION_FAILED: {errors}",
                                  code=E_UPGRADE_VALIDATION_FAILED)

    # Rev. 2 (Finding 2.1): dedicated .104.bak before the swap, not the active workspace.
    backups_dir = os.path.join(os.path.dirname(source_path) or ".", "Backups")
    os.makedirs(backups_dir, exist_ok=True)
    backup_path = os.path.join(backups_dir, os.path.basename(source_path) + ".104.bak")
    shutil.copy2(source_path, backup_path)

    # Atomic write: temp file in the same directory, fsync, then replace.
    tmp_fd, tmp_path = tempfile.mkstemp(dir=os.path.dirname(source_path) or ".", suffix=".105tmp")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            json.dump(bejson_core_serialize(new_doc), f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, source_path)  # atomic on POSIX
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise

    _bejson_get_field_map_cache(new_doc)  # born warm: field map ready before the caller touches it
    return new_doc


def bejson_core_upgrade_dry_run(doc_data: dict, source_path: str) -> dict:
    """
    Runs bejson_core_upgrade_to_105's build + validation only -- skips the
    backup and the atomic swap. Returns a report dict consumed by
    bejson_upgrade_cli.py's --dry-run (\u00a74.2) for the 3-line terminal template.
    Never touches disk.
    """
    if doc_data.get("Format_Version") not in ("104", "104a", "104db"):
        raise BEJSONUpgradeError(
            f"E_FORMAT_UNSUPPORTED: dry-run takes a 104-series doc, got {doc_data.get('Format_Version')!r}",
            code=E_FORMAT_UNSUPPORTED,
        )

    is_multi = doc_data["Format_Version"] == "104db"
    target_version = {"104": "105", "104a": "105a", "104db": "105db"}[doc_data["Format_Version"]]
    new_doc = dict(doc_data)
    new_doc["Fields"] = [{**f, "field_uuid": str(_uuid.uuid4())} for f in doc_data["Fields"]]

    new_values = []
    for row in doc_data["Values"]:
        record_uuid = str(_uuid.uuid4())
        new_values.append([row[0], record_uuid] + list(row[1:]) if is_multi else [record_uuid] + list(row))
    new_doc["Values"] = new_values
    new_doc["Format_Version"] = target_version

    errors = bejson_validator_check_105_strict_integrity(new_doc)

    return {
        "field_count": len(new_doc["Fields"]),
        "record_count": len(new_doc["Values"]),
        "validation_pass": len(errors) == 0,
        "errors": errors,
        "source_path": source_path,
        "target_version": target_version,
    }
