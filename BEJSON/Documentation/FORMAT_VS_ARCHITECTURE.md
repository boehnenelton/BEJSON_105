# BEJSON 104db vs MFDB — read this before analyzing any Core library

Source of truth: BEJSON + MFDB Crash Course (v23). Author: Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton

Every Core library file (including the nesting modules) has a `Format_Scope:` header line. Trust it over filename guesses.

## One-sentence definitions
- **BEJSON 104 / 104a / 104db** are the three **file formats** (`Format_Version`).
- **104db** is a format: ONE file holding 2+ entity types.
- **MFDB** is NOT a format version. It is a **database architecture** built from existing formats: one 104a manifest + many 104 entity files.

## Side by side
| | BEJSON 104db | MFDB |
|---|---|---|
| What it is | File format (`Format_Version: "104db"`) | Architecture on top of 104a + 104 |
| Files | One file | Manifest `104a.mfdb.bejson` + one entity file per entity (`data/<entity>.bejson`) |
| Entities | 2+ in `Records_Type` | Manifest `Records_Type` is exactly `["mfdb"]`; each entity file has one type |
| Discriminator | `Record_Type_Parent` in column 0 of every record | None; the file itself is the entity |
| Field ownership | Every field (except the discriminator) carries `Record_Type_Parent` | Plain 104 fields |
| Null-padding | Required (fields owned by other entities are `null`) | Not used; records are dense |
| Custom top-level keys | Forbidden | Manifest (104a) carries `MFDB_Version`, `DB_Name`, ...; entity files (104) only `Parent_Hierarchy` |
| Back-reference | None | `Parent_Hierarchy`: relative path from entity file to manifest (mandatory) |
| Foreign keys | Convention: `_fk` suffix | Convention: `_fk` suffix; no enforcement |
| Best for | Small relational data in one file, LLM-editable | Larger / multi-file databases |
| Detection | `Format_Version == "104db"` | `104a` + filename ends `.mfdb.bejson` (manifest); `104` + `Parent_Hierarchy` (entity) |

## Related terms (also not 104db)
- **MFDB-132**: a whole MFDB packed into one Chunked-104a document (sticky mounts via `.mfdb132_lock`). Packaging only.
- **Chunked-104a**: a directory tree stored in one 104a document (`*_chunking` modules).
- **Nested 104** (Core nesting modules): a complete 104 document embedded in a cell of a 104 document; max depth 16. Neither 104db nor MFDB.
- **Standardization vs validation** (MFDB v1.31): structural failures are hard errors; convention failures are warnings.

## Naming traps in the code
- Error names such as `E_MFDB_CORE_LOCK_FAILED` live in the shared registry; modules outside MFDB may raise them.
- `bejson_core_create_104db` / `createEmpty104db` / `validate104db` are the 104db-only entry points in otherwise generic modules.
- `SCHEMA_MFDB_ENTITY_v5` / `SCHEMA_MFDB_MANIFEST_v5` describe MFDB entity and manifest rows. `SCHEMA_PROJECT_v140` uses a lowercase `record_type_parent` column that is not a valid 104db discriminator (the spec name is `Record_Type_Parent`).
- `Doc_Chunker` (cli) stores its documents as real 104db files (`*.104db.bejson`).
