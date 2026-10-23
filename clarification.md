# Architectural, Procedural & Standards Clarifications (`libraries_105` & `libraries_104`)

- **Name**: `clarification.md`
- **Description**: Authoritative record of architectural boundaries, ecosystem separation rules, directory standards, GitHub repository mappings, and technical BEJSON/MFDB invariants clarified and established across the `libraries_104` and `libraries_105` audits.
- **Version**: `1.1.1` (`VERSION = 111`)
- **Release_Version**: `301` (`libraries_105` — Integrity Era)
- **Date Created**: `2026-10-18`
- **RELATIONAL_ID**: `e4f5b1a1-d227-40c9-85b6-279bcde75f3b`
- **Author Credit**: Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton

---

## Table of Contents

1. [Ecosystem Separation (`libraries_104` vs. `libraries_105`)](#1-ecosystem-separation-libraries_104-vs-libraries_105)
2. [Canonical Host Directory Topology & Environment Paths](#2-canonical-host-directory-topology--environment-paths)
3. [Canonical GitHub Repositories & Git Workflow](#3-canonical-github-repositories--git-workflow)
4. [Repository Hygiene & Subfolder Governance](#4-repository-hygiene--subfolder-governance)
5. [Core Technical & Schema Invariants](#5-core-technical--schema-invariants)
6. [Antigravity CLI (AGY) Skill Ecosystem Separation](#6-antigravity-cli-agy-skill-ecosystem-separation)

---

## 1. Ecosystem Separation (`libraries_104` vs. `libraries_105`)

### 1.1 Two Distinct Library Ecosystems
- **`libraries_104` (Release 300 — Foundational Era)** and **`libraries_105` (Release 301 — Integrity Era)** are maintained as **separate ecosystems** with distinct scopes and responsibilities.
- **`libraries_105` Scope (`Core` plus the explicitly exempted families in §1.3)**:
  - Non-Core 104 vertical families (`AI`, `Gaming`, `CMS`, `Lists`, `BEHTML`, `Diagrams`, `Bookmaker`, `HTML`, `Terminal_Menus`, etc.) **do not belong in `libraries_105`**.
  - Apart from the families exempted in §1.3, `libraries_105` contains **only** the `Core` library family (`Lib_PY/Core`, `Lib_JS/Core` + `Lib_JS/External/jszip.min.js`, `Lib_TS/Core`, `Lib_SH/Core`) and the `BEJSON/` database tracking `Core` entities (`BEJSON/data/*.bejson` and `BEJSON/104a.mfdb.bejson`).
- **`libraries_104` Scope**: Houses the Foundational Era **`Core`** family (`104`, `104a`, `104db`, Nested 104, and MFDB v1.31/v1.32/v1.39) **plus all vertical domain library families** across Python (`Lib_PY`), JavaScript (`Lib_JS`), TypeScript (`Lib_TS`), and Bash (`Lib_SH`).

### 1.2 104-Portion Parity Mandate Inside `libraries_105` Core
- While vertical families are excluded from `libraries_105`, the **104-series portion of `Core` inside `libraries_105` must maintain 100% functional and security parity with `libraries_104/Lib_*/Core`**.
- The recommended engineering procedure when synchronizing major `libraries_104` Core updates into `libraries_105` is to stage from the verified `libraries_104` `Core` baseline in a staging directory (`libraries_105_stage`), layer the Format 105 (`105`, `105a`, `105db`) and MFDB v1.40 Phase 6 Referential Integrity capabilities on top, verify 100% pass rates across both 104 and 105 test suites in all four languages, and then promote the staged build into `/storage/emulated/0/Admin/Libraries/libraries_105`.

### 1.3 Sanctioned Exemption: `Scaffold` and `Taxonomies` Families (added 2026-10-20)

- By explicit owner override, the library families **`Scaffold`** (`lib_bejson_Scaffold_*`) and **`Taxonomies`** (`lib_bejson_Taxonomies_*`) are **exempt** from the Core-only boundary in §1.1 and reside in `libraries_105` at `Lib_{PY,JS,TS,SH}/Scaffold/` and `Lib_{PY,JS,TS,SH}/Taxonomies/`.
- The exemption is **per family, not general**: no other non-Core vertical family (`AI`, `Gaming`, `CMS`, `Lists`, `BEHTML`, `Diagrams`, `Bookmaker`, `HTML`, `Terminal_Menus`, etc.) is admitted by it. Any further family requires its own recorded override.
- Both families are standalone modules that import `Core` primitives; `Core` is never modified by them.
- Both families implement the **`lattice`** taxonomy (prefix `lattice_` on every field, `Lattice` on every entity, `lattice_*` on files and `DB_Name`). Phase 1 data contracts: `lib_bejson_Lattice_Plan` V1.0.2-PKG102.
- Deployment kinds: `rebuild` (master built from scratch from a taxonomy) and `prebuilt` (instantiated from a prebuilt snapshot). A prebuilt node may be a master or a slave and may follow its own slightly different (variant) taxonomy; every taxonomy must still register the `_uuid_fk` and `_slot` suffixes.

---

## 2. Canonical Host Directory Topology & Environment Paths

All host storage paths are standardized under `/storage/emulated/0/Admin` (replacing the legacy `/storage/emulated/0/User` hierarchy) to ensure cross-device parity:

| Legacy Path | Canonical Path | Environment Variable(s) | Purpose |
|---|---|---|---|
| `/storage/emulated/0/User` | `/storage/emulated/0/Admin` | `$ADMIN` | Master administrative root |
| `/storage/emulated/0/User/core/libraries/libraries_104` | `/storage/emulated/0/Admin/Libraries/libraries_104` | `$ADMIN_LIBRARIES`, `$ADMIN_LIBRARIES_104` | Master BEJSON 104 libraries (Release 300) |
| `/storage/emulated/0/User/core/libraries/libraries_105` | `/storage/emulated/0/Admin/Libraries/libraries_105` | `$ADMIN_LIBRARIES_105` | Master BEJSON 105 Core libraries (Release 301) |
| `/storage/emulated/0/User/workspace` | `/storage/emulated/0/Admin/Dev` | `$ADMIN_DEV` | Active development workspace |
| `/storage/emulated/0/User/core` | `/storage/emulated/0/Admin/Core` | `$PROJECT_INDEX_ROOT` | Core system tools & registries |
| `/storage/emulated/0/User/ops/Projects_Archive` | `/storage/emulated/0/Admin/Core/Projects_Archive` | `$ADMIN_ARCHIVES` | Versioned project ZIP archive store |
| `/storage/emulated/0/User/ops` | `/storage/emulated/0/Admin/System` | `$ADMIN_CONTROL` | System operations & control scripts |
| `/storage/emulated/0/User/hub` | `/storage/emulated/0/Admin/Resources` | `$ADMIN_RESOURCES` | Shared resources, knowledge bases & assets |

- **Environment Truth Stores**:
  - Non-sensitive paths: `/storage/emulated/0/.env/user/paths.json` (and `~/setup_tools/env/env_setup.sh`).
  - Secure credentials: `/storage/emulated/0/.env/secure/secureenv_file.json`.

---

## 3. Canonical GitHub Repositories & Git Workflow

- **Official Remote Mapping**:
  - `/storage/emulated/0/Admin/Libraries/libraries_104` → `https://github.com/boehnenelton/BEJSON_104` (`main`)
  - `/storage/emulated/0/Admin/Libraries/libraries_105` → `https://github.com/boehnenelton/BEJSON_105` (`main`)
- **Legacy Remotes**: Deprecated or duplicate library repositories (such as `Zbejson_libraries`) are removed from the GitHub account in favor of `BEJSON_104` and `BEJSON_105`.
- **Git & GitHub Tooling**: Use the authenticated `gh` CLI (`gh auth setup-git`) for repository management, remote synchronization, and HTTPS push operations.

---

## 4. Repository Hygiene & Subfolder Governance

- **Root Directory Cleanliness**:
  - Only top-level documentation (`README.md`, `ABOUT.md`, `auditreport.md`, `clarification.md`), project metadata (`.bejson_project.json`, `.gitignore`), `BEJSON/`, and the language family roots (`Lib_PY/`, `Lib_JS/`, `Lib_TS/`, `Lib_SH/`) belong in the repository root.
  - `README.md` must be comprehensive, feature-complete, and include a Table of Contents (TOC).
- **Development Docs (`dev/`)**:
  - Internal development tracking notes (`dead_code.md`, `variable_naming_issues.md`, `security-notes.md`), bugfix postmortems, and remediation checklists must reside inside `dev/` (which is ignored by git via `.gitignore`).
- **Backups & Stale Archives (`backups/`)**:
  - Loose `.zip` snapshots, legacy chunk bundles, and superseded `.mfdb132.bejson` containers must be moved to `backups/` (ignored by git via `.gitignore`) rather than left in the root or inside `Lib_*/` directories.
- **Transient Artifact Exclusion**:
  - Always purge `__pycache__/`, `*.pyc`, `.pytest_cache/`, and `*.lock` files prior to running audits, building ZIP packages, or committing to git.

---

## 5. Core Technical & Schema Invariants

### 5.1 Provenance-Guarded O(1) Field-Map Cache
- **Policy §6.2 Mandate**: Positional row indexing (`row[0]`, `row[1]`) is strictly prohibited; all record access must resolve through the O(1) field-map cache (`bejson_core_get_field_map(doc)`).
- **104/104a/104db Provenance Verification**:
  - `_bejson_field_map` is an in-memory, provenance-guarded cache (`_FieldMap` instance in Python, `_BEJSON_OWNED_MAPS` `WeakMap` in JS, `_NestedMapTag` symbol in TS).
  - Forged, externally mutated, stale (after `Fields` mutation), or persisted `_bejson_field_map` dicts are detected by `bejson_core_field_map_is_fresh(doc)` and rejected by validators (`E_FIELD_MAP_STALE` / `E10`) or stripped and rebuilt during `bejson_core_parse` / `bejson_core_warm`.
- **105/105a/105db Multi-Index Field Cache (`libraries_105`)**:
  - Format 105 documents prepend a reserved `record_uuid` value to every row in `Values` (at index `0` for `105`/`105a`, and at index `1` immediately after `Record_Type_Parent` for `105db`).
  - `bejson_core_get_field_cache(doc)` builds and verifies `{ by_name, by_uuid, by_name_row }`, and `bejson_core_get_field_map(doc)` returns `by_name_row` so callers index `row[field_map[field_name]]` in O(1) time without manual offset arithmetic.

### 5.2 Unified Reserved `_` Key Rule (`E10`)
- Persisted BEJSON files on disk must **never** contain top-level keys prefixed with `_` (even in `104a` or `105a` where custom headers not starting with `_` are permitted).
- In-memory objects passed to `validate_bejson_object` / `bejson_validator_validate_object` permit only verified internal runtime cache keys (`_bejson_field_map`, `_bejson_field_map_fp`, `_nesting_field_map` / `_nestingFieldMap`). Any unverified or forged `_bejson_field_map` on an in-memory object fails validation immediately.

### 5.3 Consolidation of `Core_Nesting` and Removal of `Core/list_validator`
- Recursive cell nesting (`lib_bejson_Core_bejson_core_nesting.{py,js,ts,sh}`, error codes `130–139` `E_NESTING_*`, max depth `16`, uniform column schema enforcement) is consolidated directly inside `Lib_{PY,JS,TS,SH}/Core/`.
- Standalone `Core_Nesting/` directories and `Lib_*/Core/lib_bejson_Core_bejson_list_validator.*` are removed; list hierarchy validation belongs in `Lib_*/Lists/` (in `libraries_104`) and the core validator's tree verification routines.

### 5.4 MFDB `Parent_Hierarchy` Relative Depth Resolution & v1.40 Referential Integrity
- When MFDB entity tables reside in subdirectories (e.g., `BEJSON/data/*.bejson`) and reference `../104a.mfdb.bejson` in `Parent_Hierarchy`, path-escape validation (`_escapes_root` / `_escapesRoot`) must account for the entity file's directory depth (`entity_depth` relative to the MFDB root) so valid parent-manifest references pass while genuine directory-traversal escapes outside the MFDB root are blocked.
- In `libraries_105`, MFDB v1.40 Phase 6 Referential Integrity enforces cross-entity foreign-key (`_fk`) target resolution (`E39 E_MFDB_UNRESOLVED_FK`) and `fk_on_delete` behaviors (`cascade`, `null`/`set_null`, `default`/`set_default`, `restrict`) across Python, JavaScript, TypeScript, and Bash.

### 5.5 Logging & Header Compliance
- Library modules must never use `print(..., file=sys.stderr)` for operational warnings; Python modules must use `logging.warning(...)` per Policy §7.3.
- Every BEJSON data file must carry `"Format": "BEJSON"`, a valid `"Format_Version"`, and `"Format_Creator": "Elton Boehnen"`.

### 5.6 Sanctioned Use of Core Private Helpers by Exempted Families (added 2026-10-20)

- `Scaffold` and `Taxonomies` are **granted** permission to call Core's private cache helper `_bejson_core_invalidate_cache(doc)` (Python; the JS/TS/SH equivalents by parity) after an in-memory field rename, so the provenance-guarded `by_name` / `by_uuid` / `by_name_row` cache is rebuilt and dual-key resolution (`E_FIELD_INTEGRITY_MISMATCH`) stays consistent.
- The grant covers **calling** the helper only. Core source files remain frozen and unmodified; no new Core function is added.
- No other Core private symbol is covered by this grant.

---

## 6. Antigravity CLI (AGY) Skill Ecosystem Separation

- Skills interacting with BEJSON and MFDB are partitioned by Era (`104` vs. `105`) and by Layer (`L1` through `L6` under the 6-Tier Layered Skill Architecture):
  - **104 Skills** (`bejson-104-core`, `bejson-104-nesting-core`, `bejson-104-validator`, `mfdb-104-core`, `mfdb-104-chunker`, `template-104-template`, `behtml-104-builder`) target `$ADMIN_LIBRARIES_104` (`Release 300`).
  - **105 Skills** (`bejson-105-core`, `bejson-105-validator`, `bejson-105-upgrade-automator`, `mfdb-105-validator`, `template-105-template`) target `$ADMIN_LIBRARIES_105` (`Release 301`).
  - Every skill enforces pairwise negative constraint triggers ("Do NOT use for...") to prevent semantic routing collisions between 104 and 105 operations.

---

**Author Credit**: Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
