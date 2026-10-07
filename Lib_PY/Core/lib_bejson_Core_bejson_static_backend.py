"""
Library:        lib_bejson_Core_bejson_static_backend.py
Family:         Core
Description:    Flat-file persistence layer for BEJSON datasets.
Version:        2.1.1
Date:           2026-09-15
Author:         Elton Boehnen
Contact:        eltonboehnen@gmail.com | boehnenelton2024.pages.dev | github.com/boehnenelton
Format_Creator: Elton Boehnen
RELATIONAL_ID:  2ef744c1-23c7-48ed-9844-341b88208696
Release_Version: 300

Changelog:
  2.1.1 - AUDIT FIX (best-practices sweep): replaced print() with
          logging.error() in _load_mfdb's malformed-manifest branch --
          policy 7.3 forbids print() for logging; this ran inside real
          library logic, not a __main__ guard. Return-{} contract on
          failure left unchanged (out of scope for this fix).
"""

import os
import json
import datetime
import logging

class BEJSONBackend:
    def __init__(self, root_path=None):
        # Use {ADMIN_ROOT} standard (Phase 6.5)
        self.root = root_path or "{ADMIN_ROOT}"

    def _load_json(self, path):
        if not os.path.exists(path): return None
        with open(path, 'r') as f: return json.load(f)

    def resolve_dataset(self, source_path):
        data = self._load_json(source_path)
        if not data: return {}
        is_mfdb = os.path.basename(source_path) == "104a.mfdb.bejson"
        if is_mfdb:
            return self._load_mfdb(source_path, data)
        else:
            name = os.path.splitext(os.path.basename(source_path))[0]
            return {
                name: {
                    "fields": data.get("Fields", []),
                    "values": data.get("Values", []),
                    "metadata": {"Format": data.get("Format"), "Version": data.get("Format_Version"), "Path": source_path}
                }
            }

    def _load_mfdb(self, manifest_path, manifest_data):
        mfdb_root = os.path.dirname(manifest_path)
        entities = {}
        headers = [f['name'] for f in manifest_data['Fields']]
        
        # SPEC FIX: Changed PascalCase to snake_case to match MFDB standard
        try:
            idx_name = headers.index("entity_name")
            idx_path = headers.index("file_path")
        except ValueError:
            # Fallback for older non-standard manifests if they exist
            try:
                idx_name = headers.index("Entity_Name")
                idx_path = headers.index("Entity_File_Path")
            except ValueError:
                logging.error(f"[StaticBackend] Invalid MFDB Manifest structure at {manifest_path}")
                return {}

        for row in manifest_data['Values']:
            e_name = row[idx_name]
            e_rel_path = row[idx_path]
            e_abs_path = os.path.join(mfdb_root, e_rel_path)
            e_data = self._load_json(e_abs_path)
            if e_data:
                entities[e_name] = {
                    "fields": e_data.get("Fields", []),
                    "values": e_data.get("Values", []),
                    "metadata": {"Entity_Name": e_name, "Path": e_abs_path, "Parent_MFDB": manifest_path}
                }
        return entities

    def get_static_context(self, source_path):
        datasets = self.resolve_dataset(source_path)
        contexts = []
        for name, data in datasets.items():
            contexts.append({
                "page_title": name.replace("_", " ").title(),
                "file_name": f"{name.lower()}.html",
                "headers": [f['name'] for f in data['fields']],
                "rows": data['values'],
                "metadata": data['metadata']
            })
        return contexts

if __name__ == "__main__":
    backend = BEJSONBackend()
    print("Backend Library Loaded.")
