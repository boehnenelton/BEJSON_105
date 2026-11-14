# Security Notes: Audit/remediation pass (2026-11-12, V5.9.5 PKG118)

| ID | Sev | Area | Finding | Status |
|---|---|---|---|---|
| CMS-1 | High | `Lib_PY/CMS/web` `/api/export` | Unauthenticated, bound to 0.0.0.0: zips ANY server directory the process can read (`project_directory`) and writes the archive to ANY path (`destination_archive_path`); symlinks inside were followed. | fixed: confined to output root (`MTV_SCAFFOLD_OUTPUT_ROOT`, default `./scaffold_output`), `.zip` only, never inside the exported tree, symlinks skipped, atomic temp+replace |
| CMS-2 | High | `/api/instantiate`, `/api/custom/materialize` | `target_path` unconfined (arbitrary directory creation + file writes incl. an executable `build_site.py`). Custom builder: `entities[].name` became a file name (`../` traversal), `bound_templates[]` became a copy SOURCE (`shutil.copy2` of any readable file into the generated project), field types/names unvalidated, built-in archetypes could be overwritten, catalog grew without bound. | fixed: path confinement, strict identifier/field/type/template validation (`bejson_cms_validate_identifier`), template allow-list + bare-filename guard in the scaffold library, built-in collision refused, custom catalog capped at 64 |
| CMS-3 | Med | Admin server defaults | Hard-coded `SECRET_KEY`; default bind `0.0.0.0` with no authentication; no cross-origin POST protection; exception text returned to clients. | fixed: per-process random key (or `MTV_SCAFFOLD_SECRET_KEY`), default `127.0.0.1` with a warning on any other host, same-origin gate on writes, `nosniff`/`X-Frame-Options`/`Referrer-Policy`, generic 500s (details in the log) |
| CMS-4 | Med | Emitted `build_site.py` | Renderer replaced `{{tokens}}` with raw values: stored XSS in every generated page; TOC/gallery/embed URLs accepted `javascript:`/`data:`. | fixed: tokens HTML-escaped by default (explicit trusted-markup key list), `safe_url` allow-list (http, https, mailto, relative) |
| DC-1 | High | `CLI_Doc_Chunker/Doc_Chunker_Flask.py` | Default `0.0.0.0` bind, hard-coded session key, no origin check; `/tools/restore-snapshot` joined an unchecked `filename` (traversal to any zip); `/tools/import-file` read any server path; `/compile/download/<doc_name>` unvalidated doc name. | fixed: loopback default + `--host/--port`, random key, same-origin gate, snapshot name regex + parent check, import target must be a regular file <= 10 MB and (when `DOC_CHUNKER_IMPORT_ROOTS` is set) inside those roots, doc name must be a known document |
| HYG-1 | Low | Hard-coded paths | `/storage/emulated/0/...` template roots in Canvas PY/JS and Graphics, Termux `$HOME` fallback in `bejson_server.py`, Termux shebang in a Core test shim (failed 15 assertions on any non-Termux host), a previous-session scratch path in `dev/conformance/runts.sh`, Termux defaults in two admin HTML forms. | fixed (env-driven: `CANVAS_TEMPLATE_DIRS`, `ADMIN_DEV`, `TS_TYPES_ROOT`); Core env/path-guard `/storage/emulated/0` mappings are the documented environment layer and left as is |
| HYG-2 | Low | Package contents | Self-embedded `libraries_105.zip` (byte-identical copy of the tree), duplicate `dev/metrics.zip`, two EMPTY archive zips (one misspelled), shipped `__pycache__` (cpython-313/314), a nested tracker (`CLI_Doc_Chunker/.bejson_project.json`) violating the single-tier rule, no `.gitignore`. | fixed (nested tracker preserved at `dev/legacy_trackers/`) |
| CORE-1 | Med | `lib_bejson_Core_bejson_static_backend.py` | A crafted manifest `file_path` (`../outside.json` or an absolute path) makes `resolve_dataset` read files OUTSIDE the MFDB root (reproduced); plus `print()` used for an error. | NOT applied (Core frozen). Verified patch: `dev/proposed_core_patches/CORE-1_static_backend_path_confinement.patch` |
| CORE-2 | Low | `lib_bejson_Core_bejson_path_guard.py::resolve_storage_path` | Reads the deprecated `BEJSON_STORAGE_ROOT` variable that AGENTS.MD §6.10 forbids in new config. | NOT applied (Core frozen); owner decision |
| CLI-1 | Med | `CLI_Doc_Chunker/Doc_Chunker.py` | `import lib_bejson_utility` -> `sys.exit(1)`: the module is not shipped in this Core-only repository, so the app (and its Flask wrapper) cannot start here. Hardening above was verified with a stub. | open: owner decision (supply the module, move the tool to libraries_104, or delete) |

Residual risks:
- The CMS admin API and Doc_Chunker UI still have no authentication; they are loopback-only by default and the same-origin gate is not a substitute for authentication (a non-browser client can omit `Origin`).
- Doc_Chunker restore uses `zipfile.extractall` (stdlib strips `..` and absolute prefixes) rather than the Core `safe_extract_zip`, and has no decompressed-size limit.
- `scaffold_fluff_linter` audits generated files but is a content linter, not a sanitiser.

---

# Security Notes: Adversarial review verdicts (2026-10-09)

| # | Finding | PY | JS | TS | SH | Status |
|---|---|---|---|---|---|---|
| 1 | 105db positional row-offset desync | confirmed | confirmed | confirmed | confirmed | fixed |
| 2 | Non-transactional cascade delete | confirmed | confirmed | n/a (in-memory) | confirmed | fixed |
| 3 | exec() in source_env | confirmed | n/a | n/a | n/a | fixed |
| 4 | ResilientPIDLock reclaim race | confirmed | n/a | n/a | n/a | fixed |
| 5 | Plaintext password in key cache | n/a | confirmed | confirmed | n/a | fixed |

Review inaccuracies: the single-chain Order->OrderItem->StockReservation example does not corrupt; a sibling-restrict variant does. The review's helper snippet is incomplete as written.

Residual risks:
- Lock reclaim (CORRECTED 2026-10-12): the earlier claim that the token check defeats the reclaim race was wrong -- the token only protected release(); the stress suite reproduced overlapping holders. Fixed with a reclaim guard + re-verification. Remaining window: an owner stalled >5s between mkdir() and writing its meta (grace period), or a guard holder dying and two reclaimers racing at the 5s guard-expiry.
- No flock (Android shared storage; guard-file clutter). JS/TS flock declined.
- Env-file ownership is not checked; env literals can still redirect module-level settings.
- `chunked5/Chunked_libraries_105.104a.bejson.txt` is a pre-existing generated artifact and was NOT regenerated; it reflects pre-remediation sources.

---

# Security Notes

## 2026-10-16 — Field map cache and reserved `_` prefix
- Threat: a persisted or crafted `_bejson_field_map` could redirect name-based lookups to the wrong column (read or write the wrong cell), be shared between documents, or collide on comma-containing field names.
- Mitigation: provenance-guarded in-memory cache (never trusted from disk), per-document map copy, JSON-encoded cache key, persisted `_` keys rejected by every validator, `atomic_write` strips `_` keys, duplicate field names rejected. O(1) lookup preserved (timing tests in PY and JS).
- Residual: TS validator does not check manifest `file_path` for escaping the DB root (PY does via path_guard).
- JS `_atomicWrite` (new in mfdb_core 2.3.5) writes a same-directory temp file then renames; it strips `_`-prefixed keys.

**Author**: Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton

## 2026-10-06 — Persisted `_bejson_field_map` poisoning (cross-column read)
- Severity: High (data integrity / confidentiality of column-addressed reads). Reachable by any crafted .bejson file or JSON string loaded through Core.
- Root cause: in-memory cache key trusted from untrusted input; no relation check between cache and `Fields`.
- Mitigation: cache stripped on load/parse, forbidden in persisted input by validators, O(1) freshness guard on reuse, per-document copy. Regression checks recorded in `PATCH_REPORT_field_map_integrity.md`.
- Hardening (same day): freshness guard alone was forgeable; engine-built provenance (Py `_FieldMap`, JS/TS WeakMap) is now required.
- Residual: a trusted caller editing its own engine-built map or `Fields` inner entries in place without clearing the cache is not detected (affects only that document).
- Stale embedded copies of the old TS code in the two `chunked5/*.104a.bejson.txt` archives were removed from the package (2026-10-06); regenerate with the chunker if wanted.

# Security Notes: Standards logging sink (2026-10-27)

- **Secrets in logs:** `**context` and `extra={"context": ...}` are serialised verbatim into `log_event_context_payload`. Never pass tokens, keys or credentials (secrets live only in `secureenv_file.json`); no redaction is performed. Use `secure=True` for sensitive entries.
- **Secure logging:** secure entries never reach the main log; the main log holds only a redacted placeholder (event timestamp/level/priority/key, sender subsystem, flag "redacted"). The placeholder reveals THAT a secure event happened (`secure_placeholder=False` removes it). 0600/0700 are not enforceable on shared Android storage or FAT: the library warns once and the flag then gives routing and audit separation only. Not encryption.
- **Foreign/corrupt files:** a parseable file with a non-Standards schema is refused (E251), never overwritten; an unparseable file is moved aside (`*.corrupt-<ts>-<pid>`), not deleted.
- **Lock scope:** writers use `ResilientPIDLock` on the log path; readers take no lock and rely on atomic replace. Do not log to a path from code already holding its lock.
- **Crash window:** rows buffered in a killed process are lost; ERROR/FATAL entries are written immediately.

# Security Notes: Standards export and archiving (2026-10-27)

- **Markup injection:** log text is untrusted. Markdown cells escape HTML, pipes, backslashes, backticks and brackets; the html export escapes every value (including title and filter summary), contains no script, no external resource and a Content-Security-Policy meta (default-src 'none'). Do not post-process an export into a page that executes it.
- **Secure exports:** need an explicit secure=True, are created 0600, omit context from markdown/html by default, and may not target the main log or the main archive tree (E261). A caller who passes a stream or reads the returned text owns what happens next; 0600 is not enforceable on shared Android storage/FAT (warned once).
- **Overwrite protection:** an export never replaces a registered log file or a listed archive file (E259). An export to an ordinary path replaces it atomically unless overwrite=False.
- **Archives:** secure archives live only in secure_archive_dir (0700, files 0600) and are refused if the file kind mismatches (E257/E260). Pruning is off unless archive_keep_periods is set and deletes only files whose name AND header prove they are this log's archives. Archive and prune settings are per process (not persisted): a process that starts without them neither archives nor prunes.
- **Crash semantics:** archives are written before the live file is committed, so a crash leaves duplicates that the next run removes, never missing rows. Overflow past the row cap is archived first; if that fails nothing is written.
