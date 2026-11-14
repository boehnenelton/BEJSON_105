# libraries_105 Change Log (Unified 104 + 105 Parity Build)

## 2026-11-14 - V5.9.6 PKG119: Multi-AI Provider Gateway (`Lib_PY/AI` v1.5.0), Config-Gated Tooling/Parser/Extension Layers, Canvas/JS Test Suites & Architecture Documentation
- **NEW `Lib_PY/AI/` (`v1.5.0` 3-Tier Multi-AI Provider Gateway):**
  - **Tier 1 (`lib_bejson_ai_dispatcher.py`, `lib_bejson_ai_translator.py`, `lib_bejson_ai_models.py`):** Implemented `AIDispatcher` (`AI_Dispatcher`), `AI_Dispatch`, `AI_Dispatch_Async`, `AITranslator` (`AI_Translator`), and modern Gemini model catalog (`Gemini_3_1_Flash_Lite`, `Gemini_3_5_Flash_Lite`, `Gemini_3_8_Flash`, `Gemini_4_Argon`, `Gemini_4_Hydrogen`, `Resolve_Model_Identifier`, `List_Active_Gemini_Models`, `Query_Live_Gemini_Models`) with response extractors (`Get_Response_Text`, `Get_Response_JSON`, `Get_Response_Usage`, `Get_Interaction_ID`, `Get_Tool_Calls`, `Get_Turn_Continuation_Command`).
  - **Tier 2 (`lib_bejson_ai_tooling_base.py`, `lib_bejson_ai_tooling_registry.py`, `lib_bejson_ai_tooling_interactions.py`, `lib_bejson_ai_parser_base.py`, `lib_bejson_ai_parser_registry.py`, `lib_bejson_ai_extension_parser.py`, `lib_bejson_ai_preprocessor.py`, `lib_bejson_ai_postprocessor.py`, `lib_bejson_ai_features_common.py`):** Implemented persistent Format 105a configuration (`config/ai_global_config.105a.bejson`) via `AIGlobalConfigManager` (`AI_Global_Config_Manager`), config-gated `ToolingRegistry` (`Tooling_Registry`) + `InteractionsToolingSystem` (`Interactions_Tooling_System`) with autonomous multi-turn tool loop, config-gated `ParserRegistry` (`Parser_Registry`) + `BaseModularParser` (`Base_Modular_Parser`) for modular pre/post-parsers and `<request_turn>` client-turn continuation commands, and `ExtensionParserRegistry` (`Extension_Parser_Registry`) + `BaseExtensionModuleParser` (`Base_Extension_Module_Parser`) for downstream Python module/library parser extensions.
  - **Tier 3 (`lib_bejson_ai_client_base.py`, `lib_bejson_ai_client_geminirest.py`, `lib_bejson_ai_client_geminiinteractions.py`, `lib_bejson_ai_env_vault.py`, `lib_bejson_ai_key_rotator.py`, `lib_bejson_ai_jit_key_handler.py`, `lib_bejson_AI_bejson_errors.py`):** Implemented `GeminiRestClient` (`Gemini_Rest_Client`, `generateContent`) and `GeminiInteractionsClient` (`Gemini_Interactions_Client`, `v1beta/interactions` with `previous_interaction_id`), portable `AIEnvVault` (`definitions.json`/`.py` -> `secureenv_file.json`), `KeyRotator` (round-robin, 429 cooldown, 401 quarantine, Format 105a persistence), `JITKeyHandler` (silent `x-goog-api-key` delivery), and error registry codes `200-235`.
  - **Unit Tests (`Lib_PY/AI/tests/test_ai_gateway_prototypes.py`):** 18 unit tests covering config auto-export, tooling gates, switchable systems, autonomous multi-turn tool loops, 429 key rotation, parser toggles, `<request_turn>` continuation command extraction, and Python module extension parsers (18/18 passing).
- **Canvas & JS Test Suites:** Added `Lib_PY/Canvas/tests/test_canvas_schemas.py` (7/7 passing), `Lib_JS/Canvas/tests/test_canvas_schemas.js`, `Lib_JS/Graphics/tests/test_graphics_validator.js`, and `Lib_JS/External/tests/test_external_core.js`.
- **Architecture Diagrams & Documentation:** Added `images/ai_gateway/ai_gateway_part1_tiers_1_2.jpg` and `images/ai_gateway/ai_gateway_part2_tier_3.jpg`, updated `Lib_PY/AI/README.md`, `Lib_PY/AI/ARCHITECTURE.md`, `Lib_PY/AI/ARCHITECTURE_MAP.md`, `Lib_PY/AI/NEXT_STEP_PLAN.md`, extended root `README.md`, and hardened `.gitignore` to exclude logs, API keys, credentials, rotation state files, caches, and archives.
---

## 2026-11-12 - V5.9.5 PKG118: audit, harden, remediate (CMS admin server, Doc_Chunker UI, hygiene, README)
- **SECURITY (CMS admin server, `Lib_PY/CMS`):** all API paths confined to an output root; strict validation of archetype ids, entity names, prefixes, field names/types and template names; template-name guard in `lib_bejson_CMS_mtv_scaffold.py` (101); emitted `build_site.py` now HTML-escapes tokens and allow-lists URL schemes; loopback bind by default, per-process secret key, same-origin POST gate, security headers, no exception text in responses; exporter skips symlinks and writes atomically. New helpers `bejson_cms_resolve_confined_path` / `bejson_cms_validate_identifier` in `lib_bejson_CMS_mtv_core.py` (101). New `Lib_PY/CMS/tests/test_cms_admin_security.py` (11 tests; 10 fail on the V5.9.4 code).
- **SECURITY (`CLI_Doc_Chunker/Doc_Chunker_Flask.py` 1.1.1 -> 1.2.0):** loopback default + `--host/--port`, random secret key, same-origin gate, snapshot-name and doc-name validation, import-file checks (+ optional `DOC_CHUNKER_IMPORT_ROOTS`). New `CLI_Doc_Chunker/tests/test_flask_hardening.py` (6 tests; 5 fail on 1.1.1). Fresh RELATIONAL_ID (it duplicated `Doc_Chunker.py`'s).
- **Hard-coded paths removed:** Canvas PY/JS (1.0.1) and Graphics canvas templates (1.0.1) resolve template roots from `CANVAS_TEMPLATE_DIRS` / `ADMIN_DEV`; `bejson_server.py` (2.1.2) uses `Path.home()`; Core test shim shebang is `#!/usr/bin/env bash` (the Bash suite `test_auto_field_map.sh` went from 4 passed / 15 failed to all passing off-Termux); `dev/conformance/runts.sh` takes `TS_TYPES_ROOT`; admin HTML default paths are relative.
- **Headers:** RELATIONAL_ID added to 13 files that had none (CMS routes/linter, Graphics/Canvas inits and JS, three test files, presentation script); touched files carry version, changelog line and a fresh RELATIONAL_ID.
- **Docs:** README quickstarts replaced with examples that were executed (PY, JS, TS, Bash); removed `E90-E95`, `105a.mfdb.bejson`, `bejson_105_cli.py`, `upgrade_mfdb_to_105.py`, `test_bejson_core_105.py` and the declared-`record_uuid` example; repository tree and parity claims corrected. AGENTS.MD / Directive (10101): real file paths, JS vs Python return shape of `mfdb_core_add_entity_record_105`, test status. `Lib_TS/tsconfig.json` no longer lists non-existent families.
- **Package hygiene:** removed the self-embedded `libraries_105.zip`, duplicate `dev/metrics.zip`, two empty archive zips, all `__pycache__`; moved the nested tracker to `dev/legacy_trackers/`; added `.gitignore`.
- **NOT changed (Core frozen):** `lib_bejson_Core_*` untouched. Findings CORE-1 (static_backend arbitrary-file read) and CORE-2 are documented in `dev/security-notes.md` with a verified patch in `dev/proposed_core_patches/`.
- **Ledger:** `BEJSON/` Library_Changes +11 rows for the library files changed here (the 5.9.x CMS/Graphics/Standards ledger rows were never written and remain a backlog).
- **Tests:** 50 of 50 entry points pass (Python 19, JS 10, Bash 9, TS strict compile + 9 compiled tests). Baseline before this work: 49 of 50 (Bash `test_auto_field_map`), and the TS type-check only worked once `@types/node` was installed.
---

## 2026-11-06 - V5.9.4 PKG117 (backfilled from `bejson_project.json`; no entry was written at the time)
- Integrate CMS MTV Scaffolding Engine family (Lib_PY/CMS), pre-built taxonomy archetypes, 105 MFDB v1.40 models, 13 canonical BEHTML templates, and admin dashboard.
---

## 2026-11-02 - V5.9.3 PKG116 (backfilled from `bejson_project.json`)
- Add Standards stateful loaded chamber logging module, unit tests, and multi-language conformance suite.
---

## 2026-11-01 - V5.9.2 PKG115: Automated Video Presentation Export & Custom Slide Dwell Durations
- **Slide Dwell Duration Video Compilation (`Lib_PY/Graphics/lib_bejson_Graphics_graphics_core.py` 1.1.0 -> 1.2.0):** Extended `compile_frames_to_mp4()` and `compile_frames_to_webm()` to support slide dwell durations (4s, 8s, 12s, etc.) via dynamic loop + concat filter complexes, and added high-level `compile_presentation_slides_to_video()` and `async_compile_presentation_slides_to_video()`.
- **Field Map Doc Detection (`Lib_PY/Graphics/lib_bejson_Graphics_graphics_schemas.py`):** Enhanced `build_field_map_105()` to accept both raw `fields` arrays and full BEJSON document dictionaries across 104 and 105 series.
- **Unit Testing Suite (`Lib_PY/Graphics/tests/test_graphics_validator.py`):** Added `test_video_compilation_with_dwell_durations` verifying frame-accurate MP4 video compilation under custom dwell constraints (12/12 unit tests passing).

---
- **Graphics Domain Slide Archetypes & Family Registry Storage (`Lib_PY/Graphics/lib_bejson_Graphics_graphics_canvas_templates.py`, `Lib_PY/Graphics/canvas_templates_registry.105a.bejson`):** Registered 5 canonical 16:9 (`1280x720`) branding slide archetypes (`title_cover`, `architecture_3_pillar`, `feature_matrix`, `metrics_kpi_dashboard`, `summary_conclusion`) into the family registry `canvas_templates_registry.105a.bejson` with live HTML/SVG stage generation, category `branding_slide`, dynamic renderer resolution, and zero circular import overhead.
- **Procedural Branding Slide Renderers (`Lib_PY/Graphics/lib_bejson_Graphics_graphics_core.py`):** Added 5 vector renderers adhering to Policy §8.1 Tri-Color palette (`render_branding_title_slide_svg`, `render_branding_architecture_slide_svg`, `render_branding_feature_slide_svg`, `render_branding_metrics_slide_svg`, `render_branding_summary_slide_svg`).
- **Slide Timeline Schemas & Header Differentiation (`Lib_PY/Graphics/lib_bejson_Graphics_graphics_schemas.py`, `Lib_JS/Graphics/lib_bejson_Graphics_graphics_schemas.js`):** Added `GRAPHIC_SLIDE_FIELDS` with unique UUIDs (`9f6a7b8c-6666-4000-8000-000000000001`..`0013`) including `remove_frame_source` boolean column. Added `create_branding_slide_deck_105a` enforcing custom headers for Format 105a and strict entity table standard (no custom headers) for Format 105.
- **Two-Tier Barrier Validation & Records Type Expansion (`Lib_PY/Graphics/lib_bejson_Graphics_graphics_validator.py`, `Lib_JS/Graphics/lib_bejson_Graphics_graphics_validator.js`):** Added `GraphicSlideRecord` and `BrandingSlideRecord` to `VALID_GRAPHICS_RECORDS_TYPES`, passing both Core family and Graphics domain validation with 0 errors.

---

## 2026-11-01 - V5.9.0 PKG113: Graphics Domain timeline schema, frame duration quantization, Barrier of Entry validators, and procedural SVG renderers
- **Graphics Domain Timeline Schemas & MFDB Manifest (`Lib_PY/Graphics/lib_bejson_Graphics_graphics_schemas.py` 1.0.1 -> 1.1.0, `Lib_JS/Graphics/lib_bejson_Graphics_graphics_schemas.js`):** Added canonical `GRAPHIC_ANIMATION_TIMELINE_FIELDS` definition (`frame_index`, `timestamp_ms`, `frame_duration_ms`, `fps`, `seek_progress`, `rotation_deg`, `scale_factor`, `opacity`, `svg_markup`, `frame_filename`, `is_rendered`, `checksum_sha256`), `remove_frame_source` boolean column, `compute_frame_timeline_105a()`, `create_svg_animation_timeline_105a()`, and `create_graphics_mfdb_manifest_105a()` supporting `Remove_Frame_Source: true` in 104a manifest headers.
- **Two-Tier Barrier of Entry Validators & Error Codes (`Lib_PY/Graphics/lib_bejson_Graphics_graphics_validator.py`, `Lib_JS/Graphics/lib_bejson_Graphics_graphics_validator.js`, `lib_bejson_Graphics_graphics_errors.py`):** Established dedicated Graphics Domain validator sourcing Core family validators (`validate_bejson`, `validate_mfdb_database`), enforcing error codes 500-519 (`E_GRAPHICS_CORE_VALIDATION_FAILED`, `E_GRAPHICS_INVALID_DIMENSIONS`, `E_GRAPHICS_INVALID_FRAME_SEQUENCE`, `E_GRAPHICS_INVALID_SVG_MARKUP`, etc.).
- **Procedural Vector Renderers & Frame Pruning (`Lib_PY/Graphics/lib_bejson_Graphics_graphics_core.py` 1.0.1 -> 1.1.0):** Added `render_spinning_cube_svg()` (isometric 3D vector wireframe with rotating faces and Tri-Color laser accents) and `render_radar_scanner_svg()` (tactical sweep arc with concentric reticles and sweep blips), and frame source pruning via `_prune_frame_sources()` when `remove_frame_source=True`.
- **Package Exports (`Lib_PY/Graphics/__init__.py` 1.0.1 -> 1.1.0):** Exported `compute_frame_timeline_105a`, `create_svg_animation_timeline_105a`, `create_graphics_mfdb_manifest_105a`, `render_spinning_cube_svg`, `render_radar_scanner_svg`, `validate_graphics_barrier`, `bejson_graphics_validator_validate_doc`, and error constants.
---

## 2026-10-30 - V5.8.1 PKG112: review fixes after third-party audit (versioning, FK/escape parity, absolute-path hole)
- **Versioning:** bumped the 14 files edited by the V5.8.0 work without a header change (MFDB validators in PY 2.4.1 / JS 2.2.0 / TS 2.4.0 / SH 2.5.0, `mfdb_core` TS 2.3.5 / SH 2.3.1, TS types 2.9.1, Canvas/Graphics 1.0.1); each has a per-file changelog line and a fresh RELATIONAL_ID. Removed shipped `__pycache__` folders.
- **SECURITY (all languages):** an absolute `file_path` (or `Parent_Hierarchy`) pointing at an existing file outside the database root validated as VALID in the Python reference and JS. `lib_bejson_Core_bejson_path_guard.py` 1.3.1, JS/TS `_escapesRoot` and the SH validator now treat absolute paths as escaping the root. The escape error carries `[33]` in PY and SH (JS/TS already did).
- **Parity fixes found by the extended conformance corpus (98 manifest + 11 FK cases, PY/JS/TS/SH):** explicit `fk_on_delete: null` is invalid (TS/SH silently defaulted it to `restrict`; PY/JS reject); SH now stops at manifest-level errors before entity checks like PY (no cascading [34] on a duplicate); TS reports a root-escaping `Parent_Hierarchy` as [38] only (was [36]+[38]) and an orphan as [37] when `resolvedPaths` is given.
- **Cross-checked, no change needed:** JS `mfdb_validator_check_referential_integrity` equals Python on all 11 FK cases; TS empty `entity_name`/`file_path` rule (41) and path-escape rule equal Python.
- **Tests:** PY +2, JS +1, TS +4 (spec levels) +1 section (phase 6), SH +2 (spec levels) +2 (phase 6). The new TS/SH `fk_on_delete` tests and the PY absolute-path test fail on the pre-fix code.
- **Not changed (by design):** TS `checkReferentialIntegrity` is a pure function over loaded documents, so it does not report an unreadable entity file ([33]); `validateDatabase` does. Where an entity is not valid base BEJSON, each language reports it in its native registry (PY no code, JS [31], TS BEJSON numeric codes); only the verdict is compared.
- **Not done:** `BEJSON/` self-tracking MFDB ledger was not regenerated for this entry.
---

## 2026-10-30 - V5.8.0 PKG111: Taxonomies suffix-only rules, Canvas/Graphics cased module standardization & README reconciliation
- **Section 3 (`Taxonomies` suffix-only rules):** Updated `Lib_PY/Taxonomies/lib_bejson_Taxonomies_core.py` (`3.0.0` -> `3.1.0`) to register 7 additional suffix-only rules in `DEFAULT_SUFFIX_RULES` (`_amount` -> `number`, `_ratio` -> `number`, `_date` -> `string`, `_duration` -> `number`, `_hash` -> `string`, `_json` -> `string`, `_list` -> `array`) without altering `VALID_FIELD_TYPES`, and replaced positional row indexing in `bejson_taxonomies_core_read_definition` with O(1) `bejson_core_get_field_map(doc)`. Verified 22/22 `test_taxonomies.py`, 17/17 `test_fieldsets.py`, and 53/53 `Tax_Scaffolds` tests.
- **Section 4 (`Canvas` & `Graphics` cased name standardization & `Records_Type` fix):** Fixed `"Record_Type"` -> `"Records_Type"` in `Lib_PY/Canvas/lib_bejson_Canvas_canvas_schemas.py`, `Lib_JS/Canvas/lib_bejson_Canvas_canvas_schemas.js`, and `Lib_JS/Graphics/lib_bejson_Graphics_graphics_schemas.js`. Standardized all imports and removed 8 lowercase forwarding stubs (`lib_bejson_graphics_*.py`, `lib_bejson_canvas_*.{py,js}`) and 2 redundant `.104a.bejson.txt` chunk dumps in `Taxonomies/` and `Tax_Scaffolds/`.
- **Section 6 (`README.md` & `BEJSON/` reconciliation):** Reconciled all `libraries_105/README.md` discrepancies (version/package badge `V5.8.0-PKG111`, module versions across PY/JS/TS/SH, `bejson_core_define_field` signature without `fk_target_field_uuid`, canonical `E80`–`E85` error codes, `mfdb_version="1.40"` note, Nested 104 serialized string cell note, and complete directory tree including `Standards`, `Taxonomies`, `Tax_Scaffolds`, `Canvas`, and `Graphics`). Synced `BEJSON/` self-tracking MFDB (`12` families, `121` changes).
---

## 2026-10-29 - V5.7.0 PKG110: MFDB spec + 104/105 parity patch v3 & data validation
- **Applied `bejson_mfdb_spec_js_ts_sh_patch_v3`:** `Lib_JS/Core/lib_bejson_Core_bejson_validator.js` (3.4.0 -> 3.4.1), `lib_bejson_Core_mfdb_validator.js` (2.1.4 -> 2.1.5), `Lib_TS/Core/lib_bejson_Core_bejson_validators.ts` (2.3.0), `lib_bejson_Core_bejson_core_105.ts` (1.4.0), `lib_bejson_Core_bejson_core.ts` (2.3.0), `lib_bejson_Core_mfdb_validators.ts` (2.3.0), `Lib_SH/Core/lib_bejson_Core_bejson_validator.sh` (2.5.0), `lib_bejson_Core_mfdb_validator.sh` (2.4.0), `lib_bejson_Core_bejson_core.sh` (2.2.0), `lib_bejson_Core_mfdb_core.sh`, plus new SH (37 + 17) and TS (18 + 14) test suites.
- **Validated all 11 BEJSON files and `BEJSON/104a.mfdb.bejson`:** Fixed `"Record_Type"` -> `"Records_Type"` key in `Lib_PY/Graphics/canvas_templates_registry.105a.bejson`, `lib_bejson_Graphics_graphics_canvas_templates.py`, and `lib_bejson_Graphics_graphics_schemas.py`.
- **Cleaned repo:** Deleted stray `Core.zip` and `Lib_JS.zip` inside `Lib_JS/`.
---

## 2026-10-27 - V5.6.1 PKG109: package cleanup
- **Applied** the Standards family and ledger updates (V5.6.0 PKG108) on top of Libraries_1.zip. Your Graphics edits and every other file in the upload are untouched.
- **Removed (verified redundant or regenerable; all ignored by .gitignore):** all `__pycache__/` and `.pytest_cache/` folders; `Lib_JS/Core.zip` and `Lib_JS/Lib_JS.zip` (snapshots from 2026-10-17: 16/17 members identical to the tree, the other 4 are older versions, e.g. JS Core 2.2.2 vs 3.6.0 in the tree; nothing unique); `Lib_PY/Taxonomies/Chunked_Taxonomies.104a.bejson.txt` and `Lib_PY/Tax_Scaffolds/Chunked_Tax_Scaffolds.104a.bejson.txt` (every embedded file is byte-identical to the live source; regenerate with the chunker if needed).
- **Left alone, for your decision:** `Lib_PY/Graphics/` holds two naming lineages side by side (`lib_bejson_Graphics_graphics_*` and `lib_bejson_graphics_*`, both git-modified).
---

## 2026-10-27 - V5.6.0 PKG108: Standards finished (filters, export, archiving)
- **Shared filters:** one implementation (`_export.bejson_standards_export_filter_rows`) behind `read_logs` and `export_logs`: min_level, max_priority, subsystem, actor, **session, process_id, event_key, since/until** (new), category, flag. Invalid values raise 258 at call time; the public functions return [] / an error dict instead of raising.
- **NEW `lib_bejson_Standards_export.py`:** json (default, streamed array), ndjson (streamed), markdown, html. Destinations: text, stream, or file (atomic replace; 0600 from the first byte when secure; refuses to overwrite a registered log or archive file). Markdown/html escape every value, omit context unless asked; html is self-contained with no script and a CSP meta; light/dark tri-colour palette; `sort="priority"`, `limit`, `include_archives`.
- **Secure export:** `secure=True` required; destination may not be the main log or inside the main archive tree (E261); no `secure_path` => E256.
- **Archiving:** `archive_dir` + `archive_period` (daily / ISO weekly / monthly, UTC) on `configure_sink`; closed periods move to `<stem>-<key>.bejson` (104a, same schema, `Log_Is_Archive`, `Log_Archive_Period_Key`, no row cap) at flush time or via `bejson_standards_archive_now(include_current=)`; `bejson_standards_list_archives`. Row-cap overflow is archived before the trim; an archive failure aborts the write and the rows stay buffered (E260). Idempotent (exact-row de-duplication); archives written before the live commit. `archive_keep_periods` prunes only verified archives of this log and is off by default. Secure logs archive only into `secure_archive_dir` (separate tree, 0600/0700); without one they stay ring-only.
- **Validator:** period math (`period_start`, `period_key`), archive-aware audit (archives are not row-capped; header key checked), option checks. **Core:** archive write/close/list/prune, overflow hook, single clock (`bejson_standards_core_now`).
- **Error codes 258-261** (block 250-269, 250-261 assigned). Registries: libraries_105 `errors.bejson` +4 (290 rows); libraries_104 aggregate +12 (250-261, now reserved; manifest 416) with its own tracker/change-log entry (5.2.1 / PKG9).
- **Tests:** 112 (Standards); Core (11 suites) and Taxonomies (2) re-run green against this tree's Core. TS/Bash parity still deferred.

---

## 2026-10-27 - V5.5.0 PKG107: Lib_PY/Standards (standardized logging sink)
- **NEW `Lib_PY/Standards/`** (PY only; TS/Bash parity deferred): `_errors`, `_validator`, `_core`, `_registry` modules, `__init__.py`, `README.md`, `tests/test_standards.py` (67 tests). Consolidates the in-chat drafts PKG105 (v1) and PKG106 (v2); this is the first release of it in the tree.
- **Storage:** one BEJSON 104a document per log file (`Records_Type ["StandardsLogEntry"]`); header keys `Log_Row_Cap` (default 10000), `Log_Min_Level`, `Log_Schema_Version` ("3.0.0"), `Log_Is_Secure`. No `_` keys persisted.
- **Schema v3 (17 columns), domain grammar `log_<role>_<attribute>_<suffix>`:** `event` (timestamp, level, priority, key, category, subject, message, error code, context, flags, secure flag), `sender` (subsystem, actor, session, process id), `target` (uuid fk), reserved Z-space slot (always null). Required tier: timestamp, level, key, message, subsystem, process id; everything else null unless supplied, validated when present. `_text`, `_payload`, `_flag` suffixes declared locally; all 17 names pass `bejson_taxonomies_check_field_name`.
- **Priority:** integer 1-4, stored only when given; effective value derived from level at read time (FATAL 1, ERROR 2, WARN 3, INFO/DEBUG 4); `read_logs(max_priority=...)`.
- **Writes:** buffered; one PID-locked read-modify-write per batch (size 25 / 5 s / ERROR+ / flush / read / exit). Measured: 1000 logs 3.25 s unbatched vs 0.16 s at batch 25. Oldest rows trimmed past the cap.
- **Secure routing:** `secure=True` goes only to `secure_path` (own row cap, 0600 file, 0700 new directory; warns once where modes are unenforceable). No secure_path => refused (E256); engine refuses secure/non-secure mixing (E257); main log gets a redacted placeholder row unless `secure_placeholder=False`; audits enforce file kind from `Log_Is_Secure`.
- **Filters:** `read_logs(min_level, subsystem, category, actor, flag, max_priority, secure)`. **Handler:** `BEJSONLogHandler` maps stdlib records and `extra=` onto all fields.
- **Migration:** v1 (10-col) and v2 files migrate on first write BY NAME via `LEGACY_RENAMES`; audit flags legacy files.
- **Error block 250-269** (250-257 assigned). Checked against both trees: Core 1-99, Core_Nesting 130-159, Core_Extension 160-189, AI 200-235, Cognition 270-289, BEHTML 300-329, BEHTML_IDE 330-359, Terminal_Menus 360-389, Diagrams 420-435, Bookmaker 450-479, Lists 480-499. An earlier draft used 180-199, which overlaps Core_Extension.
- **Registries:** `errors.bejson` +8 rows, `families.bejson` +1, manifest counts synced (Errors 286, Families 6). libraries_104's aggregate registry was NOT touched: add the 250-257 rows there to reserve the block.
- **Core / Taxonomies / Canvas / Graphics:** untouched; Core (11 suites) and Taxonomies (2 suites) re-run green against this tree's Core.

---

## 2026-10-25 — Canvas Family & SVG Animation Studio Integration
- **NEW `Lib_PY/Canvas/`:**
  - `lib_bejson_Canvas_canvas_schemas.py`: Canonical BEJSON 105a `CanvasStudioConfig` and `CanvasFrameSequence` schemas with UUIDv4 `field_uuid` allocations, offset row caching, and sequence math.
  - `lib_bejson_Canvas_canvas_templates.py`: Catalog, discovery, and runtime HTML instantiation for 9 production canvas stages and seamless repeating texture tiles.
  - Sibling aliases `lib_bejson_canvas_schemas.py` and `lib_bejson_canvas_templates.py`.
- **NEW `Lib_JS/Canvas/`:**
  - `lib_bejson_Canvas_canvas_schemas.js`: Full Node.js/browser parity for 105a canvas config creation, field mapping, and validation.
  - `lib_bejson_Canvas_canvas_templates.js`: Template catalog, root discovery, and stage HTML renderer.
  - Sibling aliases `lib_bejson_canvas_schemas.js` and `lib_bejson_canvas_templates.js`.
- **NEW SVG Graphic Animation Studio:**
  - `playwright_canvas_studio.py`: Deterministic headless capture engine controlling animation duration, FPS, seek ratio (`window.seekProgress`), dimensions, and multi-frame sequence rendering.
- **NEW Skill `canvas-animation-studio`:**
  - Installed at `~/.gemini/config/skills/canvas-animation-studio/` and `/storage/emulated/0/Admin/Dev/Skills/agy-consolidated/canvas-animation-studio/`.

---

## 2026-10-18 — Unified 104 (v5.2.0 PKG8) + 105 (Integrity Era) Parity Build in Stage
- **Rebuilt** `libraries_105_stage` from the full `libraries_104` v5.2.0 PKG8 baseline (all 20 Python families, 8 JS families, 6 TS families, 7 SH families, plus `Lists` split and `Core` nesting merge) combined with all `libraries_105` Format 105 ("Integrity Era") and MFDB v1.40 Referential Integrity modules, functions, and test suites.
- **Core Parity (PY/JS/TS/SH):**
  - Preserved O(1) `_FieldMap` / `_BEJSON_OWNED_MAPS` / `WeakMap` field-map caching across 104/104a/104db and `by_name` / `by_uuid` / `by_name_row` self-maintaining caches across 105/105a/105db.
  - Unified validator rules across all 4 languages: reserved `_` key rejection on persisted files, in-memory `_bejson_field_map` integrity verification, strict `Format_Creator === "Elton Boehnen"` enforcement, `bejson_validator_validate_object` for nested cells, and `check_105_strict_integrity` (E90-E95 / Fail-on-Switch).
  - Unified `Core_Nesting` into `Core` (`lib_bejson_Core_bejson_core_nesting.{py,js,ts,sh}`) and `Lists` into `Lib_*/Lists/lib_bejson_Lists_list_validator.{py,js,ts,sh}` (removed obsolete `Lib_*/Core/lib_bejson_Core_bejson_list_validator.*`).
  - Merged `BEJSON/data/*.bejson` MFDB registries (`errors.bejson` = 426 rows, `dependencies.bejson` = 225 rows, `library_changes.bejson` = 178 rows, `families.bejson` = 37 rows, `metadata.bejson` = 28 rows) and synced `BEJSON/104a.mfdb.bejson`.
- **Verification:** All Python (229 tests), JavaScript (8 suites), TypeScript (8 suites), and Bash (8 suites) tests pass 100%.

---

# Change Log

## Stress-suite follow-up (2026-10-12)
- NEW `Lib_PY/Core/tests/run_stress.py`: one-click launcher, no arguments/prompts/paths. Picks a fresh seed, scale 3, runs the whole stress suite, prints a summary, writes `tests/stress_reports/` (log per run + `last_run.json`), exits 0/1. If the previous run FAILED, that seed is replayed first automatically. Optional `--scale/--seed/--runs`.
- NEW `Lib_PY/Core/tests/test_stress_suite.py` (23 tests; STRESS_SEED / STRESS_SCALE): multi-process + thread lock races, stale-reclaim storms, crashed holders, 105/105a/105db column fuzz, cascade fuzz vs independent reference model with injected commit failures, env-parser payload corpus + fuzz, parse_json fuzz and large-doc memory ratio.
- FIX (found by the suite) PY `ResilientPIDLock` 3.5.2->3.5.3: reclaim was identity-blind between observe and rename; under crash storms ~3 of 25 runs showed two processes inside the critical section or a worker dying on a vanished lock dir. Reclaimers are now serialised by a short-lived `.reclaim` guard dir and re-verify (token+pid) under it; `acquire()` retries if its lock dir vanishes before meta is written. 30/30 clean runs at STRESS_SCALE=3 afterwards.
- FIX (found by the suite) PY `mfdb_core_delete_entity_record_105` 3.0.2->3.0.3 and JS `mfdb_core_delete_entity_record_105` 2.4.2->2.4.3: snapshot/rollback now always taken. Previously a leaf delete (no cascade ops) that failed while syncing the manifest count left the entity file changed and the manifest stale. SH already snapshotted unconditionally.

## Adversarial-review remediation (2026-10-09)
Base: `533afcae-libraries_105.zip` (latest upload; the review targets this base).
No `bejson_project.json` in the archive, so no Project/Package version bump; per-file Version patch-bumped.

- F1 105db row-offset desync (PY/JS/TS/SH): absolute column = 0 for Fields[0] (Record_Type_Parent), i+1 for 105/105a, i+2 elsewhere in 105db. PY core, mfdb_core, mfdb_validator; JS core, mfdb_core; TS core_105, field_map, mfdb_core, mfdb_validators; SH core, mfdb_core, mfdb_validator. `remove_field` refuses the 105db discriminator.
- F2 non-transactional cascade delete (PY/JS/SH): plan-then-commit with byte snapshot and rollback; sibling restrict now leaves every file untouched. TS is in-memory/immutable, unaffected.
- F3 `exec()` in `source_env` (PY): replaced with ast/literal_eval parser; whole-file refusal.
- F4 `ResilientPIDLock` (PY): atomic tombstone-rename reclaim, per-acquisition token, ownership-verified release; `PermissionError` = alive.
- F5 plaintext password in PBKDF2 key cache (JS/TS): HMAC-SHA-256 fingerprint under a non-extractable per-process key; `clearKeyCache()` exported.
- Hardening: PY `parse_json` uses `raw_decode` (no full-text slice copy). JS/TS flock declined (no stdlib flock in Node).
- Tests: new `test_adversarial_remediation*` for PY (29), JS (6), TS (5), SH (6); three tests that asserted the old buggy offset corrected (PY format105, JS cache, TS/SH auto_field_map).

## V11-PKG103 — Consolidation merge (2026-10-06)
Merged the two diverged tracks: V10-PKG102 (this package's own forward work —
Phase 6 Referential Integrity, validator fixes, error codes 43-47/80-85, etc.,
all of it kept as-is) + the 7 silent-exception logging fixes from V6-PKG101
that had been reverted/lost somewhere along V10's history. Nothing from
V10-PKG102 was removed or rewritten — only logging.debug()/console.debug()
calls were re-added to the specific except/catch blocks listed below.

### Re-applied (previously lost)
- PY `lib_bejson_Core_bejson_chunking.py` 1.9.0→1.9.1: 3 sites (scan skip, sticky-manifest fast path, lock-release header-clear cleanup).
- PY `lib_bejson_Core_bejson_core.py` 3.5.0→3.5.1: 2 sites (lock-owner liveness retry, field-map cache attach).
- PY `lib_bejson_Core_bejson_env.py` 2.1.2→2.1.3: 1 site (source_env search-path loop); `import logging` restored.
- PY `lib_bejson_Core_mfdb_core.py` 3.0.0→3.0.1: 14 sites across _read_file_content, mount's sticky fast path, resurrect_file, mfdb_core_discover, _mfdb_core_repair_hierarchy, mfdb_federation_push_config cleanup, 3 debug-flag helpers, _mfdb_meta_auto_trim, _mfdb_debug_schema_snapshot (inner catch), mfdb_core_get_debug_log, mfdb_core_clear_debug_log, mfdb_core_detect_schema_drift.
- JS `lib_bejson_Core_bejson_chunking.js` 1.8.0→1.8.1: unmount's lock-release header-clear cleanup.
- JS `lib_bejson_Core_bejson_core.js` 2.2.0→2.2.1: `_bejson_hide` field-map cache attach (re-applied onto the newer Object.defineProperty implementation).
- JS `lib_bejson_Core_mfdb_core.js` 2.4.0→2.4.1: 5 sites (federation temp-cleanup, meta auto-trim, nested schema-snapshot x2, schema-drift check).

All 7 PY files re-verified with `python3 -m py_compile`, all 3 JS files with `node -c`, before packaging.

### Verified already intact from V6-PKG101 (no action needed)
- C1 error-code renumbering (90-94→110-114): superseded cleanly by 2.9.0's later removal of the schema-constraint codes; no collision.
- H1 SH `mfdb_validator_validate_database`/`validate_entity_file`: present.
- H3 (8 Gaming-labeled JS files under Lib_JS/Core): still absent.
- M2 TS index exports (`bejson_core_105`, `check105StrictIntegrity`, `check105SchemaConstraints`): present.

## V10-PKG102 (supersedes three earlier deliveries that were all mislabeled V10-PKG101; this one contains everything below)
##   (history: V10-PKG101 content) - 2026-10-03
### Fixed (verified defects)
- JS mfdb_core 2.4.0: unconditional `window.JSZip` crashed Node on load (ReferenceError).
- TS mfdb_core 2.3.3: registerEntity default record_count 0 (was null -> NaN -> "Coercion failed").
- TS mfdb_core 2.3.3 (NEW finding): debug section used un-imported `fs`/`path`; debug system could never enable in Node. Also fixed a TS2352 cast.
- SH bejson_validator 2.2.0 (NEW finding): record-length check ignored 105 row offsets, so every populated 105 file failed validation (also broke validate_database on 105 MFDBs).
- PY schema 2.3.0: extract() was a shallow copy aliasing Fields.
- JS validator 2.1.0 (NEW finding): module had NO exports, so parse.js / list_validator.js / mfdb_validator.js received undefined and JS validation was dead. Exports added.
- SH validator 2.3.0 (NEW finding): no field-type check at all, so type "any" was accepted. Closed set enforced (E_INVALID_FIELDS=6).
### Verified clean (no change needed)
- No Gaming (or any non-Core family) import/require/source in TS, JS, PY or SH; only comments mention it.
- PY and TS validators already reject type "any".
- JS validator 2.2.0: now accepts 105/105a/105db (parity with PY/TS): strict integrity (unique field_uuid, unique record_uuid, Fail-on-Switch), 105-aware row length and type checks, 105db discriminator check. 28 tests, including documents produced by the real PY upgrader.
- SH validator 2.2.0 row-length fix corrected during verification: 105db rows are fields+1, not fields+2 (real PY-upgraded 105/105a/105db docs now validate in SH, JS and TS).
### Known gap / needs your decision
- PY core (and the JS/TS/SH field-map caches mirroring it) treat 105db as a +2 offset: resolve_field_index('val') returns 3 and test_offset_is_2_for_105db asserts it. But the PY upgrader and add_record_105 produce rows [discriminator, uuid, ...Fields] where Record_Type_Parent is Fields[0], so 'val' actually lives at column 2. Result: field-index/write_cell on 105db would hit the wrong column. NOT changed (the PY test encodes it and it touches core semantics) -- confirm which layout is canonical.
### Added
- JS: 105 uuid CRUD in core 2.2.0; Phase 6 RI in mfdb_core; error codes 43-47, 80-85 (errors 2.4.0).
- SH: Phase 6 RI in mfdb_core 2.3.0; mfdb_validator_check_referential_integrity + live strict_fk (validator 2.3.0).
- PY: schema API parity. Tests: JS/SH test_phase6_ref_integrity, PY test_schema_api.
- Release_Version 300 on PY __init__, JS bejson_cache.test, TS index; showcase headers completed.
### Audit items found STALE
- "11 PY test modules use exec()": archive contains 3 PY test modules, none use exec(); all 148 tests pass. Nothing to rewrite.
- SH tests "hardcoded paths / duplicate folders": only one SH test file ships (test_auto_field_map.sh); not reproduced.
### Not done
- dependencies.bejson / families.bejson regeneration; JS/SH Phase 4 upgrade-to-105.
- Header Contact email (eltonboehnen@gmail.com) differs from policy (boehnenelton2024@gmail.com) across all files; left as-is, needs your call.

---

# libraries_104 Change Log

## 2026-10-16 — v5.2.0 PKG8: nesting_query merged into core_nesting; nesting uses Core validator/field map; Bash + cache fixes

- **Merged** `lib_bejson_Core_bejson_nesting_query.{py,js,ts,sh}` into `lib_bejson_Core_bejson_core_nesting.*` (0.6.0). Query files removed, **no alias** (breaking; nothing in the bundle used them but the tests). Query API (`bejson_nesting_query`, `_get_path`, `_query_summary`, `QueryMatch`) is now in core_nesting; JS and TS export `E_NESTING_QUERY_*` from it too.
- **Core reuse (PY/JS/TS):** nested-cell validation calls the Core validator (PY `validate_bejson`, JS new `bejson_validator_validate_object`, TS `validate104`); field maps use the Core field-map cache (key `_bejson_field_map` replaces `_nesting_field_map` / `_nestingFieldMap`). Local `_build_field_map` / `_quick_validate_104` copies removed. **Bash** keeps its local validator: the Core Bash validator is file-based and cannot validate an in-memory cell.
- **Fixed — stale cache:** with no `RELATIONAL_ID` the fingerprint hashed only `Fields`, so two different documents with the same schema shared NestMap cache entries (the second scan returned the first one's results) and same-schema nesting could look circular. Now hashes Fields + Values (all four languages).
- **Fixed — Bash:** (1) the mandatory-key jq test ran against the key string, so every nested doc was rejected and scan found 0 cells; (2) `(( valid++ )) || (( invalid++ ))` also counted every first valid cell as invalid; (3) query skipped null/false cells and returned strings — now raw JSON, 2 matches in the smoke fixture like PY/JS/TS. Both former expected-failure checks are real passing checks.
- **Core JS:** validator `Format_Creator` must equal `Elton Boehnen` (was any string; PY/TS/SH already enforced it); new `bejson_validator_validate_object` (isolated, preserves the caller's validator state).
- **Error registries:** JS +4 codes (MFDB 57-60), Bash +7 (17-19, 57-60); PY, JS, Bash, TS now agree (66 codes).
- **Tests:** two new behavior tests per language (Core validator rules reach nested cells; no cache sharing). PY 7, JS 7, TS 7, Bash 6 nesting checks pass; all other suites pass; `tsc` 0 errors.
- Registries: dependencies (6 rows replaced), library_changes (+7), manifest counts. Not touched: `MFDB_Libraries.mfdb132.bejson` snapshot, `_nestingFieldMap` allowance in the PY/TS/JS validators (harmless, kept for compatibility), `Lib_TS/Lib_TS.zip` and `Lib_TS2.zip` (old snapshots from your copy, carried over as-is).

## 2026-10-16 — v5.1.0 PKG7: nesting errors folded into Core error files; Lib_PY/AI synced to CLI_AI V2.13.2 PKG33

### 1. Core nesting error codes now live in the standard Core error file
- Codes `E_NESTING_*` 130-139 (names and values unchanged) moved into `Lib_PY/Core/lib_bejson_Core_bejson_errors.py` (2.5.0), `Lib_JS/Core/lib_bejson_Core_bejson_errors.js` (2.4.0), `Lib_SH/Core/lib_bejson_Core_bejson_errors.sh` (1.6.0) and, for TS (which has no errors file; its Core codes live in `types.ts`), `Lib_TS/Core/lib_bejson_Core_bejson_types.ts` (2.5.0, `CORE_NESTING_ERRORS`).
- **Removed:** `lib_bejson_Core_bejson_nesting_errors.{py,js,ts,sh}`. **Breaking, no shims:** anything importing/sourcing those files must use the Core error file (TS: `CORE_NESTING_ERRORS` from `lib_bejson_Core_bejson_types`). Nothing inside this bundle still references them.
- Re-pointed: `core_nesting` 0.5.0 -> 0.5.1 and `nesting_query` 0.2.0 -> 0.2.1 in all four languages (in-code VERSION constants updated to match); smoke tests 1.0.0 -> 1.0.1. JS keeps its exported `NESTING_ERRORS` as the `E_NESTING_*` subset so that API is unchanged.
- Registries: 8 `dependencies` edges re-pointed, 4 Core `families` notes reworded, 12 `library_changes` rows added, manifest record counts updated. Error-registry rows for 130-139 unchanged (still family Core).
- Verified: nesting smoke tests PY 5/5, JS 5/5, TS 5/5, SH 3 ok + 2 expected-fail (identical to the pre-change baseline); full PY/JS/SH/TS test suites green; `tsc` 0 errors.

### 2. Lib_PY/AI updated from CLI_AI V2.13.2 PKG33 (verbatim copies)
- Updated: `ai_constants` 1.0.0 -> 1.2.1, `ai_dispatch` 1.7.0 (same version number, newer content: adds `geminirest`), `bejson_grok` 2.1.0, `bejson_groq` 3.1.0, `bejson_huggingface` 2.1.0, `bejson_ollama` 1.1.0, `bejson_openrouter` 3.2.0, `bejson_tokenrouter` 1.1.0, `gemini_standard_profiles` 3.1.0.
- New: `ai_context_files` 1.0.0, `ai_structured_instruction` 1.0.0, `ai_structured_reception` 1.0.0, `bejson_geminirest` 1.1.0; config defaults `ai_constants.bejson` (15 rows), `ai_keywords.bejson`, `ai_knowledge_pool.bejson` (both empty).
- All 13 files are byte-identical to CLI_AI; all 32 `lib_bejson_AI_*` modules import cleanly.
- **Not changed (left for your decision):** `bejson_provocative.py` (CLI_AI removed this provider on 2026-08-21), `ai_tool_system.py`, `bejson_gemini_tts.py` and root `gemini_model_registry.104a.bejson` exist only here, so they stay untouched. `ai_dispatch`, `gemini_standard_profiles` and `ai_context_files` headers have no `Release_Version: 300` line (CLI_AI's content copied as-is). The library's previous `ai_dispatch` carried the same 1.7.0 / RELATIONAL_ID but lacked the `geminirest` adapter.
- Not touched: `BEJSON/MFDB_Libraries.mfdb132.bejson` snapshot (already stale before this change), `Core/__pycache__`, tracker's second `Values` row.

## 2026-10-16 — v5.0.0 PKG6: field-map integrity follow-up (five open items)
- **`_`-key rule unified** (CLI 1.4.3, PY validator 2.2.7, JS 2.0.6, TS validators 2.0.6, Bash validator 2.1.5): persisted input rejects any top-level `_` key; in-memory objects accept only `_bejson_field_map` (verified against Fields), `_nesting_field_map` (PY), `_nestingFieldMap` (JS/TS). **Behaviour change:** 104a files carrying other `_` custom headers are now rejected by the library validators (they were accepted before; the CLI already rejected them).
- **JS validator exports** its API (UMD-like). mfdb_validator, parse and Lists were receiving `undefined` functions before. The appended-export workaround in the JS test is gone; the Lists test that asserted "exports nothing" now asserts the exports exist.
- **MFDB tests added** (PY, JS, TS, Bash). Bugs they exposed and fixed: JS `mfdb_core` threw ReferenceError on load under Node (`window.JSZip` unguarded, now 2.3.5); JS `_atomicWrite` was called 13 times and never defined, so federation and debug were dead (now defined, strips `_` keys); JS `create_connected_slave_entity` called `init_entity_file` with the wrong arguments (now takes an options argument); TS validator rejected every valid `../104a.mfdb.bejson` Parent_Hierarchy (depth now starts at the entity's directory, validators 2.1.5); Bash schema snapshot piped plain-text names through `jq '.[]'` and wrote nothing, and add/remove record were never debug-logged (now 2.2.5).
- **tsc: 0 errors** with `@types/node` (`Lib_TS/tsconfig.json` added). The 35 errors were `mfdb_core.ts` using `fs`/`path` it never imported (a real bug: the debug helpers threw and `catch {}` hid it) plus one bad cast. The remaining 15 without `@types/node` were only missing Node typings.
- README section 2.4 documents the field-map rules and test commands. Tracker bumped to 5.0.0 / PKG6, Project_GUID unchanged.
- Open: tracker's second `Values` row (user's PKG5 note, 3 cells) makes the 104a tracker fail validation (pre-existing; not touched). Not fixed, out of scope: `lib_bejson_Core_bejson_bejson.js` contains ESM `export` lines (parse error under require()); `lib_bejson_Core_bejson_parse.js` line 157 uses `__filename` unguarded; TS validator does not check manifest `file_path` escaping the DB root (PY does).

## 2026-10-14 — Merge + registry/doc drift remediation
- **Merged** `libraries_104-nesting-in-core.zip` (Lists split + nesting-in-Core) onto the newer `libraries_104.zip` (env-fill / AI work of 2026-10-13). Three-way, file by file: every upstream change (Core `env` 2.3.0, AI `registry_base` 2.1.0, `genai` 2.2.0, `dev/Testing/env_fill`, `dev/change-log.md`, `checklist-20261013-223000`) kept byte-identical; nothing in Core logic altered by the merge. (The three "both changed" docs were git-untracked baseline files; content = baseline + my edits only.)
- **Registry reconciled with code** (`BEJSON/data`): families +4 (Animation SH, Bookmaker PY, Core_Extension PY, Projects PY were in the tree but unregistered); errors +35 rows (AI 220-224 transcribe / 230-235 TTS, Bookmaker 450-459, Core_Extension 160-166, Diagrams 420-421 / 431-435); Terminal_Menus 7 rows renumbered 340-346 -> 360-366 to match `lib_bejson_TerminalMenus_bejson_errors.sh`; AI `registry_base` -> Core `core`/`env` dependency rows added; library_changes +4 (env 2.3.0, registry_base 2.1.0, genai 2.2.0, this reconcile); manifest counts/Modified_At. Totals: families 33, errors 404, dependencies 215, library_changes 95.
- **Version sync:** in-code `VERSION` constants of the 7 nesting modules (PY/JS/TS core_nesting + nesting_query, SH nesting_query) now match their header versions (0.5.0 / 0.2.0); they had still said 0.4.1 / 0.1.1 after the move.
- **Docs:** README `Core_bejson_env.py` section 2.0.1 -> 2.3.0 and documents `source_env_fill()`.
- **Intended state (confirmed):** list validator = its own **Lists** family (removed from Core); nested = part of **Core** (`Lib_*/Core/lib_bejson_Core_bejson_{core_nesting,nesting_query,nesting_errors}.*`).
- **Not changed / still open:** see `BEJSON/dev/change-log.md` (2026-10-14 entries) — MFDB-132 snapshot, `.bejson_project.json` version mismatch, SH nesting `jq` defect, Core JS validator exports, 4 stale comments in frozen Core error files, README sections still describing pre-audit numbering, dependency-registry coverage gaps.

## 2026-10-14 — Core_Nesting family dissolved into Core (see BEJSON/dev/change-log.md for full detail)
12 files moved into `Lib_*/Core/` as `lib_bejson_Core_bejson_{core_nesting,nesting_query,nesting_errors}.*` (0.5.0 / 0.2.0 / 1.1.0); codes 130-139 unchanged; tests `Lib_*/Core/tests/test_nesting_smoke.*`.

## 2026-10-13 — Lists family split out of Core (see BEJSON/dev/change-log.md for full detail)
New `Lib_PY|JS|TS|SH/Lists/` (`lib_bejson_Lists_list_validator.*` 2.0.0, own errors 480-499, array-field check ported to all four); old `lib_bejson_Core_bejson_list_validator.*` removed from Core. Breaking rename, no shims. Tests: PY 12, JS 11, TS 9, SH 25.

## 2026-10-13 — Environment fill (3 files, additive)
- `Lib_PY/Core/lib_bejson_Core_bejson_env.py` 2.2.4 -> 2.3.0: new `source_env_fill()`; existing functions byte-for-byte unchanged.
- `Lib_PY/AI/lib_bejson_AI_ai_registry_base.py` 2.0.1 -> 2.1.0: fixed numbered-slot env scan being nested under `if self.env_var:`; registries now call `source_env_fill()` so secureenv_file.json keys are found; env keys de-duplicated.
- `Lib_PY/AI/lib_bejson_AI_bejson_genai.py` 2.1.5 -> 2.2.0: `GenAIKeyManager` reads `GEMINI_KEY_1..21` + secure-store fill.
- Added `dev/Testing/env_fill/test_env_fill.py` (13 tests) and `dev/checklist-20261013-223000.md`.
- Verified: all 43 Lib_PY AI/Core modules import before and after. Downstream consumers (every subclass of RoundRobinKeyRegistry: groq, openrouter, grok, huggingface, tokenrouter, ollama, ollamalocal, gemini; interactions, provocative, brain_helper) use unchanged signatures.
- Not changed: JS/TS/SH families (no equivalent code there), your uncommitted edits to Core core.py / .gitignore etc. were left exactly as uploaded.
- Tracker note: `.bejson_project.json` was NOT bumped — its header (2.0.0 / PKG 5) and its row (4.0.0 / PKG 4) already disagree, so I left the tracker for your registration CLI to reconcile.
