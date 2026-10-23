# lib_bejson_Taxonomies

- **File:** Lib_PY/Taxonomies/README.md
- **Purpose:** Create and audit taxonomies, track field_uuids, build compliant schemas (BEJSON 105 / MFDB v1.40).
- **VERSION:** 1.0.0
- **RELATIONAL_ID:** e29dd50a-c065-4009-a46d-737a7644c2ff
- **Author:** Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton

Imports `lib_bejson_Core` (unmodified). Part of the `lattice` taxonomy: prefix `lattice_` on every registry field, `Lattice` on every registry entity.

## Modules

| Module | Role |
|---|---|
| `lib_bejson_Taxonomies_store` | Internal: registry field/entity name constants, errors, row/lock helpers over public Core calls |
| `lib_bejson_Taxonomies_taxonomy_registry` | Create / derive (variant) / diff / delete taxonomies; check field and entity names |
| `lib_bejson_Taxonomies_uuid_tracker` | `field_uuid` ledger: track, resolve, follow renames, retire; `audit_database` |
| `lib_bejson_Taxonomies_schema_builder` | Registry schema (single source of truth); build a fresh registry DB; build compliant field defs and domain entities |

## Public API (all `bejson_taxonomies_*`)

| Function | Purpose |
|---|---|
| `build_registry_database(root_dir, db_name, network_role)` | Fresh 6-entity registry, root taxonomy + suffix rules + ledger + Z-space reservation seeded |
| `create_taxonomy(manifest, namespace_key, suffix_rules, family_name, parent_taxonomy_uuid)` | Register a taxonomy; prefix is `<namespace>_`; `_uuid_fk` and `_slot` mandatory |
| `derive_variant(manifest, parent_ref, namespace_key, suffix_overrides, suffix_removals)` | Copy a taxonomy, edit its suffix rules, link to parent |
| `diff_taxonomies(manifest, ref_a, ref_b)` | Prefix and suffix differences, parent relationship |
| `get_taxonomy` / `list_taxonomies` / `delete_taxonomy` | Lookup by uuid or namespace; delete refused while in use; variants detached |
| `check_field_name(taxonomy, name, type)` / `check_entity_name` / `match_suffix` | Compliance problems (empty list = compliant) |
| `make_field_name(taxonomy, subject, descriptor, suffix)` / `build_field_definition(...)` | Build compliant names / field dicts |
| `create_domain_entity(manifest, taxonomy_ref, entity_name, fields)` | Validate, create the 105 entity, ledger every field |
| `track_fields` / `track_entity_fields` | Add fields to the ledger (all-or-nothing compliance check) |
| `resolve_field_uuid` / `resolve_field_name` | Name <-> `field_uuid` through the live entity file |
| `record_rename` / `retire_field` / `sync_ledger` | Follow renames, retire removed fields, report unledgered fields |
| `get_field_entry` / `stamp_audit` | Ledger row lookup; refresh counts and audit timestamps |
| `audit_database(manifest)` | Taxonomy-aware audit; returns `{passed, problems, ...}`, never raises on findings |

Errors: `TaxonomyError` (`.code`), `TaxonomyComplianceError` (`.problems`).

## Rules enforced

- Every field: `<prefix><descriptor><registered suffix>`, type must match the suffix type, snake_case.
- Every taxonomy registers `_uuid_fk` and `_slot` (string). Prefixes may not overlap (`lv_` vs `lv_x_`).
- A field is judged by the taxonomy its ledger row names, so nodes on a variant taxonomy audit on their own rules.

## Tests

`python3 Lib_PY/Taxonomies/tests/test_taxonomies.py` (22 tests).

## Known Core limit

Core's `fk_on_delete: null` skips an entity's own foreign keys, so a self-referencing parent link is not cleared by Core. `delete_taxonomy` detaches variants itself.
