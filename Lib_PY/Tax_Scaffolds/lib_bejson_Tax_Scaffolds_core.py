"""
File Name : lib_bejson_Tax_Scaffolds_core.py
Rel. Path : Lib_PY/Tax_Scaffolds/lib_bejson_Tax_Scaffolds_core.py
Purpose   : Tax_Scaffolds CORE: the only code that edits other registries' entity columns: all-or-nothing wrapper, column insert before Z-space, cache invalidate (the family's only private Core import).
VERSION   : 3.0.0
Author    : Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
RELATIONAL_ID : cd4ef23e-fca3-40c1-bdc9-f4f6dd00cdc1
"""
from __future__ import annotations

import logging
import os
import shutil
import sys
import tempfile
from contextlib import contextmanager
from typing import Any, Dict, Iterator, List

# Sibling family directories (Lib_PY/Core, Lib_PY/Taxonomies, Lib_PY/Tax_Scaffolds) resolve relative to this file; nothing is hardcoded.
_HERE = os.path.dirname(os.path.abspath(__file__))
for _fam in ('Taxonomies', 'Tax_Scaffolds'):
    _p = os.path.normpath(os.path.join(_HERE, "..", _fam))
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

import lib_bejson_Taxonomies_core as txc
from lib_bejson_Core_bejson_core import (  # noqa: E402
    _bejson_core_invalidate_cache,
    bejson_core_define_field,
    bejson_core_load_file,
)

logger = logging.getLogger(__name__)
VERSION = "3.0.0"

_IGNORE = shutil.ignore_patterns("*.lock", "*.tmp", "__pycache__")
def bejson_tax_scaffolds_core_invalidate_cache(doc: dict) -> None:
    """Rebuild Core's by_name / by_uuid / by_name_row cache after an in-memory rename or reorder."""
    _bejson_core_invalidate_cache(doc)
def _is_ignored(name: str) -> bool:
    return bool(_IGNORE(os.path.dirname(name), [os.path.basename(name)]))
def _restore_from_backup(root: str, backup: str) -> None:
    """Put `root` back exactly as the backup holds it. Files the backup deliberately skipped (locks, temp files,
    caches) are left alone, so a lock this process holds is never deleted underneath it."""
    for name in os.listdir(root):
        if _is_ignored(name):
            continue
        full = os.path.join(root, name)
        shutil.rmtree(full) if os.path.isdir(full) and not os.path.islink(full) else os.remove(full)
    shutil.copytree(backup, root, dirs_exist_ok=True)
@contextmanager
def bejson_tax_scaffolds_core_all_or_nothing(manifest_path: str) -> Iterator[None]:
    """Run a multi-file change as one unit. Takes a per-registry transaction lock (so two processes cannot
    interleave), backs up the registry directory, and restores it if the block raises (any exception,
    including KeyboardInterrupt). If the restore itself fails, the backup is KEPT and its path is reported."""
    root = os.path.dirname(os.path.abspath(manifest_path))
    keep_backup = False
    backup = tempfile.mkdtemp(prefix="tax_scaffolds_backup_")
    try:
        with txc.entity_lock(os.path.join(root, ".tax_scaffolds_txn")):
            shutil.copytree(root, backup, ignore=_IGNORE, dirs_exist_ok=True)
            try:
                yield
            except BaseException:
                logger.exception("scaffold operation failed; restoring %s", root)
                try:
                    _restore_from_backup(root, backup)
                except Exception as exc:  # restoring failed: do not destroy the only good copy
                    keep_backup = True
                    logger.error("restore failed (%s); the pre-change copy is kept at %s", exc, backup)
                    raise txc.TaxonomyError(f"restore failed; pre-change copy kept at {backup}", "E_RESTORE_FAILED") from exc
                raise
    finally:
        if not keep_backup:
            shutil.rmtree(backup, ignore_errors=True)
def bejson_tax_scaffolds_core_insert_columns(
    manifest_path: str, entity_name: str, specs: List[Dict[str, Any]],
) -> List[str]:
    """Add columns [{name, type, fk_target_entity?, fk_on_delete?}] to an entity; existing rows get null.
    New columns go BEFORE a trailing Z-space slot block, so slots stay trailing. Slots are addressed by
    field_uuid, so their position change is safe; their uuids, names and data are untouched.
    Returns the new field_uuids in spec order. Callers validate first (validator.plan_graft)."""
    path = txc.entity_path(manifest_path, entity_name)
    with txc.entity_lock(path):
        doc = bejson_core_load_file(path)
        if doc is None:
            raise txc.TaxonomyError(f"cannot load {entity_name} at {path}", "E_ENTITY_NOT_FOUND")
        old_len = len(doc["Fields"])
        slots = [i for i, f in enumerate(doc["Fields"]) if f["name"].endswith(txc.SLOT_SUFFIX)]
        if slots and slots != list(range(old_len - len(slots), old_len)):
            raise txc.TaxonomyError(f"{entity_name}: existing slots are not a trailing block", "E_ZSPACE_LAYOUT")
        start = old_len - len(slots)
        new_uuids = [bejson_core_define_field(
            doc, s["name"], s["type"], fk_target_entity=s.get("fk_target_entity"), fk_on_delete=s.get("fk_on_delete"))
            for s in specs]
        if start != old_len:  # rotate the freshly appended columns in front of the slot block
            fields = doc["Fields"]
            doc["Fields"] = fields[:start] + fields[old_len:] + fields[start:old_len]
            for row in doc["Values"]:  # column 0 of a 105 row is the record_uuid
                row[:] = row[:1 + start] + row[1 + old_len:] + row[1 + start:1 + old_len]
            bejson_tax_scaffolds_core_invalidate_cache(doc)
        txc.write_doc(doc, path)
    return new_uuids
