# Lib_PY/Standards

Standardized logging sink on BEJSON 104a (log schema v3). Python 3.10+. Depends on Core (unmodified); Taxonomies only for the schema-compliance check.

```python
from lib_bejson_Standards_registry import (bejson_standards_configure_sink, bejson_standards_log,
    bejson_standards_read_logs, bejson_standards_export_logs, bejson_standards_archive_now,
    bejson_standards_list_archives, bejson_standards_audit_log_file, BEJSONLogHandler)

bejson_standards_configure_sink(log_path, row_cap=10000, min_level="INFO", secure_path=secure_log_path,
                                archive_dir=archive_dir, archive_period="monthly", secure_archive_dir=secure_archive_dir)
bejson_standards_log(log_path, "ERROR", "db.connect", "refused", error_code=250, subsystem="db")   # required: level, event_key, message
bejson_standards_log(log_path, "WARN", "login.fail", "bad password", priority=2, category="auth",
                     flags=["audit"], actor="bob", secure=True, attempts=3)    # secure -> secure_path only
bejson_standards_read_logs(log_path, min_level="WARN", category="auth", flag="audit", max_priority=2, since="2026-10-01T00:00:00Z")
bejson_standards_export_logs(log_path, "html", "report.html", actor="bob", max_priority=2, sort="priority")
bejson_standards_audit_log_file(log_path)                  # {"passed": bool, "problems": [...]}
logging.getLogger().addHandler(BEJSONLogHandler(log_path)) # plain logging calls feed the sink
```

| Module | Role |
|---|---|
| `_errors` | codes 250-261 assigned (block 250-269) |
| `_validator` | pure checks, schema, period math, non-throwing audit; never writes |
| `_core` | locked read-modify-write, atomic commit, row-cap trim, archiving, secure-file hardening, migration |
| `_export` | the shared filter; json / ndjson / markdown / html; file, stream or text destinations |
| `_registry` | public API, batching, secure routing, auto-archive, handler |

## Schema v3
Names follow `log_<role>_<attribute>_<suffix>`: **event** (timestamp, level, priority, key, category, subject, message, error code, context, flags, secure flag), **sender** (subsystem, actor, session, process id), **target** (uuid fk), then a reserved slot (always null).
**Required:** timestamp (auto), level, event key, message, subsystem (sink default), process id (auto). Everything else is null unless given, and validated when present.
**Priority** 1 (now) to 4 (background); stored only if given, otherwise derived from level when read (FATAL 1, ERROR 2, WARN 3, INFO/DEBUG 4).

## Filters (read_logs and export_logs)
`min_level, max_priority, subsystem, actor, session, process_id, category, flag, event_key, since (inclusive), until (exclusive)`. One implementation, in `_export`.

## Export
`bejson_standards_export_logs(log_path, fmt, dest, ...)`: `fmt` = `json` (default, a streamed JSON array), `ndjson`, `markdown`, `html`. `dest`: `None` returns text, a stream, or a path (written atomically; `overwrite=True` by default). Refuses to overwrite a registered log or archive file. Markdown and html hold rows in memory and omit context unless `include_context=True`; every value is escaped, the html file has no script and a Content-Security-Policy meta. `sort="priority"`, `limit=N` (last N), `include_archives=True`, `theme="dark"`. Returns `{"ok", "rows", "dest", "text"}` or `{"ok": False, "error", "code"}`; never raises.

## Archiving
`archive_dir` + `archive_period` ("daily" / "weekly" ISO / "monthly", UTC). Rows older than the current period move to `<stem>-<period key>.bejson` (104a, same schema, `Log_Is_Archive`, no row cap). Checked at flush time (no thread) and by `bejson_standards_archive_now(log_path, include_current=False)`. Rows trimmed past the row cap are archived first; if the archive write fails nothing is written and the rows stay buffered. Idempotent: a retry never duplicates. `archive_keep_periods=N` deletes archives beyond the newest N (off by default; only verified archives of this log are touched). Settings are per process, like `secure_path`.

## Secure logging
`secure=True` entries are written only to `secure_path`. No `secure_path` => refused (E256), never written to the main log. The main log gets a redacted placeholder row unless `secure_placeholder=False`. Secure files are created 0600 (directory 0700); not enforceable on shared Android storage/FAT, where a warning is logged. Secure archives go only to `secure_archive_dir` (a separate tree from `archive_dir`); with none, the secure log stays ring-only. Secure exports need `secure=True`, are written 0600, and may not target the main log or the main archive tree (E261). Not encryption.

## Flush
Batch size, interval (checked on the next log call, no thread), ERROR/FATAL, `flush()`, `read_logs()`, exit. Tests: `python3 Lib_PY/Standards/tests/test_standards.py`.
