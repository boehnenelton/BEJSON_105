"""
Library:        bejson_upgrade_cli.py
Family:         Core
Description:    CLI front-end for lib_bejson_Core_bejson_upgrade.py
                 (Format105_Master_Plan_Rev2, Phase 4, \u00a74.2). Runs the
                 104 -> 105 upgrade, or --dry-run to preview it without
                 writing anything.
Version:        1.0.1
Date:           2026-08-16
Author:         Elton Boehnen
Contact:        eltonboehnen@gmail.com | boehnenelton2024.pages.dev | github.com/boehnenelton
Format_Creator: Elton Boehnen
RELATIONAL_ID:  e1f6b3a8-7c4d-4e29-9a5f-0d3c6b8e1f47
Release_Version: 300

Changelog:
  1.0.0 - Initial delivery. --dry-run prints the 3-line template from \u00a74.2:
          (1) field/record UUID-assignment counts, (2) pre-commit validation
          PASS/FAIL, (3) dependent files to verify.
          NOTE (flagged for Elton): line 3's source, dependencies.bejson,
          tracks lib-to-lib *code import* dependencies -- it has no registry
          of which application files read/write a given *data* file. As a
          best-effort proxy this CLI looks up FROM_FILE rows whose
          DEPENDS_ON_FILE matches the target's owning library file (pass
          --owner-lib to set it) rather than the target .bejson file itself.
          If --owner-lib is omitted, line 3 reports "no dependency map
          available" instead of fabricating results.
  1.0.1 - Audit fix (2026-08-16): self-location now uses the mandated
          SCRIPT_PATH = Path(__file__).resolve().parent pattern (Policy
          \u00a74.1) instead of a bare os.path.dirname/os.path.join chain.
"""

import sys
import json
import argparse
import os
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_PATH.parent))

from lib_bejson_Core_bejson_core import bejson_core_load_file
from lib_bejson_Core_bejson_upgrade import (
    bejson_core_upgrade_to_105,
    bejson_core_upgrade_dry_run,
    BEJSONUpgradeError,
)

GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"


def _lookup_dependents(deps_bejson_path: str, owner_lib: str) -> list:
    if not deps_bejson_path or not owner_lib or not os.path.exists(deps_bejson_path):
        return []
    with open(deps_bejson_path, "r", encoding="utf-8") as f:
        deps = json.load(f)
    names = [f["name"] for f in deps["Fields"]]
    from_idx = names.index("FROM_FILE")
    depends_idx = names.index("DEPENDS_ON_FILE")
    return sorted({row[from_idx] for row in deps["Values"] if row[depends_idx] == owner_lib})


def main():
    parser = argparse.ArgumentParser(description="Upgrade a 104/104a/104db BEJSON file to 105-series.")
    parser.add_argument("path", help="Path to the 104-series .bejson file to upgrade.")
    parser.add_argument("--dry-run", action="store_true", help="Preview the upgrade; write nothing.")
    parser.add_argument("--deps-file", default=None,
                         help="Path to dependencies.bejson, for the dependent-files line (dry-run only).")
    parser.add_argument("--owner-lib", default=None,
                         help="Owning library file path (as it appears in DEPENDS_ON_FILE) to look up "
                              "dependents for. Best-effort proxy -- see file header note.")
    args = parser.parse_args()

    doc = bejson_core_load_file(args.path)
    if doc is None:
        print(f"{RED}E_FILE_NOT_FOUND: could not load {args.path}{RESET}")
        sys.exit(1)

    if args.dry_run:
        try:
            report = bejson_core_upgrade_dry_run(doc, args.path)
        except BEJSONUpgradeError as e:
            print(f"{RED}{e}{RESET}")
            sys.exit(1)

        print(f"{report['field_count']} fields and {report['record_count']} records will be assigned UUIDs.")
        if report["validation_pass"]:
            print(f"Pre-commit validation: {GREEN}PASS{RESET}")
        else:
            print(f"Pre-commit validation: {RED}FAIL{RESET}")
            for err in report["errors"][:5]:
                print(f"  - [{err['code']}] {err['detail']}")

        dependents = _lookup_dependents(args.deps_file, args.owner_lib)
        print("Dependent files to verify before live upgrade:")
        if dependents:
            for dep in dependents:
                print(f"- {dep}")
        else:
            print("- (no dependency map available -- pass --deps-file and --owner-lib)")
        return

    try:
        bejson_core_upgrade_to_105(doc, args.path)
        print(f"{GREEN}Upgraded {args.path} to 105-series. Backup written to Backups/.{RESET}")
    except BEJSONUpgradeError as e:
        print(f"{RED}{e}{RESET}")
        sys.exit(1)


if __name__ == "__main__":
    main()
