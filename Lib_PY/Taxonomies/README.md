# lib_bejson_Taxonomies

- **File:** Lib_PY/Taxonomies/README.md
- **Purpose:** The shelf: naming rules (taxonomies), crayon boxes (field sets), and an id for every column. BEJSON 105 / MFDB v1.40.
- **VERSION:** 3.0.0
- **RELATIONAL_ID:** 8fcdc360-ec21-43c1-9cce-893a5519dd5a
- **Author:** Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton

Never seen this before? Read **START_HERE.md** in the project root first. It has pictures and crayons.

## What is in the box: three files

| Module | Kid version | Technical |
|---|---|---|
| `_core` | The hand and the shelf: all the reading and writing | constants and helpers, taxonomies (create, variant, diff, delete), field_uuid ledger, schema builder (registry schema 1.3.0, 9 tables, 59 columns), field-set writes (content hash, register with undo, definition files) |
| `_validator` | The teacher: only checks, never writes | set key, members, definition files, member vs taxonomy, whole-database audit |
| `_registry` | The part you actually call for field sets | define, new version, retire, list, get, export, import, entities_with_set, resolve_member, read_set_rows |

## The 10 things you will actually call

All are `bejson_taxonomies_<name>(manifest_path, ...)`.

| Call | In one line |
|---|---|
| `define_field_set(m, "media_asset", members, display_name)` | Make a new crayon box (version 1) |
| `new_version(m, "media_asset", [new_member])` | Add crayons; box becomes version 2 |
| `retire_field_set(m, "media_asset")` | Stop handing the box out (old pages keep theirs) |
| `list_field_sets(m)` / `get_field_set(m, "media_asset")` | Look at the boxes |
| `list_grafts(m)` / `entities_with_set(m, "media_asset")` | Which pages have this box? |
| `member_columns(m, "CmsVideo", "media_asset")` | What did each crayon become on this page? |
| `resolve_member(m, "CmsVideo", "media_asset", "title")` | One crayon's current column name (survives renames) |
| `read_set_rows(m, "CmsVideo", "media_asset", ["title"])` | Read rows by crayon name, same code for every page |
| `export_field_set(m, "media_asset", "x.def.bejson")` | Save a box to a file |
| `import_field_set(m, "x.def.bejson")` | Load a box from a file (same = fine, different = refused) |

`members` looks like `{"descriptor": "title", "suffix": "_name", "field_type": "string"}`.

Check everything: `bejson_taxonomies_validator_audit_database(m)` returns `{"passed": True/False, "problems": [...]}`.

## Rules to remember

1. A box has no prefix or page name. The page it is handed to supplies them.
2. A new version only adds. Never removes, never reorders.
3. Same name + same version + different content = conflict (refused).
4. Every taxonomy must have the suffixes `_uuid_fk` and `_slot`.
5. This family never edits `Core`. It only reads Core and writes registry files through Core.

## Tests

    python3 Lib_PY/Taxonomies/tests/test_taxonomies.py   # 22
    python3 Lib_PY/Taxonomies/tests/test_fieldsets.py    # 17

Some log lines such as `node_key '' is empty` are expected: tests that try bad input on purpose.
