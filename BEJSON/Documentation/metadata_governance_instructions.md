# Metadata Entity as Governance & Clarification Hub — Instructions for AI Editors

Date: 2026-07-21
Author of this note: Claude (session work), per Elton Boehnen's direct instruction.

## Decision made this session

Elton asked: should clarifications/definitions (e.g. what "BEJSON" stands for) live
in (a) a System-family library function that prints info on call, or (b) the
MFDB database as a new entity or into existing metadata?

Decision: **use the existing `Metadata` entity** (`BEJSON/MFDB/data/metadata.bejson`,
manifest-registered in `BEJSON/MFDB/104a.mfdb.bejson`). Do not build a new
"print info" library function and do not create a new entity file.

Reasoning: the Metadata entity is already EAV-style (`RECORD_TYPE` /
`LIBRARY_FAMILY` / `LANGUAGE` / `KEY` / `VALUE` / `DESCRIPTION`) and already
holds `RULE` records for cross-cutting governance facts (Core language parity,
MFDB-is-part-of-Core). A definitional fact like the BEJSON acronym is the same
*kind* of thing — a governance/clarification fact, not per-library code. Adding
a library function would duplicate what the database already does, and would
drift out of sync with it over time. One source of truth only.

## Rule for future AI editors

When you need to record or look up a clarification, definition, or governance
rule that isn't specific to one library file's internal logic:

1. Open `BEJSON/MFDB/data/metadata.bejson`.
2. Add a row with `RECORD_TYPE = "RULE"`, set `LIBRARY_FAMILY`/`LANGUAGE` to
   `"ALL"` if it's ecosystem-wide, or to the specific family/language if scoped.
3. Put the fact in `VALUE`, and the full explanation + confirmation date/author
   in `DESCRIPTION`. Always attribute confirmation to Elton Boehnen with a date
   if he stated it directly, exactly as the existing rules do.
4. Do NOT invent or restate the fact elsewhere (e.g. don't add a second,
   slightly different acronym expansion in a code comment somewhere) — always
   point back to this entity as the authoritative source.
5. Bump the `Metadata` entity's `schema_version` and `record_count` in the
   manifest (`104a.mfdb.bejson`) whenever you add or remove rows.
6. Log the change in `BEJSON/MFDB/data/library_changes.bejson` (family `MFDB`,
   language `N/A`, file `BEJSON/MFDB/data/metadata.bejson`).

## Specific facts recorded this session

- `BEJSON_ACRONYM_DEFINITION` = "BOEHNEN ELTON JSON" (RULE, ALL/ALL). This is
  the sole authoritative expansion. It is also stated verbatim in the header
  of all four Core language files (`lib_bejson_Core_bejson_core.py/.js/.ts/.sh`)
  so it's visible even to someone reading a single file in isolation, but the
  Metadata entity is still the canonical source if the two ever disagree —
  fix the code comment to match the database, not the other way around.
- `PMS_DEPRECATED` = "true" (RULE, System/PY). `lib_bejson_System_be_pms.py`
  and `lib_bejson_System_be_project_service.py` were moved to
  `Lib_PY/System/Deprecated/` on 2026-07-21. Elton is rebuilding the
  project/package management system from scratch. Do not import, extend, or
  reference these two files in new work. They were kept (not hard-deleted)
  for historical reference only.

## Versioning bumped this session

- `Metadata` entity schema: 3.0 → 3.1
- Manifest `MFDB_Version`: 1.32 → 1.33
- Manifest `Schema_Version`: 2.1.0 → 2.2.0
- Ecosystem `CURRENT_VERSION`: 2.0.41 → 2.0.42
- Core family, all 4 languages: PY 2.0.3→2.0.4, JS 2.0.3→2.0.4, TS 2.1.1→2.1.2, SH 2.0.3→2.0.4
  (Note: these are file-internal versions on the four `bejson_core` files only —
  the Metadata entity's own `VERSION` rows for the Core family, e.g. PY 2.4.0,
  track the family's aggregate/reported version and were intentionally left
  alone since only one file per language changed, not the whole family.)
