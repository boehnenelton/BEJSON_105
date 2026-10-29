"""
File Name : lib_bejson_Standards_export.py
Rel. Path : Lib_PY/Standards/lib_bejson_Standards_export.py
Purpose   : Standards EXPORT: the shared row filter plus json / ndjson / markdown / html exporters and file, stream or text destinations.
VERSION   : 1.0.0
Author    : Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
RELATIONAL_ID : 7de0ef3b-4bff-4754-a448-dc53ad59780a

json (a JSON array) and ndjson stream row by row; markdown and html hold the (filtered) rows in memory
because they print a count and may sort. Every value is escaped for the target format; the html file is
self-contained, has no script, and carries a Content-Security-Policy meta that forbids everything but inline CSS.
"""
from __future__ import annotations

import html
import io
import json
import logging
import os
import sys
import uuid
from collections import deque
from typing import Any, Callable, Dict, Iterable, Iterator, List, Optional, Tuple

# Sibling family directories (Lib_PY/Core, Lib_PY/Standards) resolve relative to this file; nothing is hardcoded.
_HERE = os.path.dirname(os.path.abspath(__file__))
for _fam in ('Core', 'Standards'):
    _p = os.path.normpath(os.path.join(_HERE, "..", _fam))
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

import lib_bejson_Standards_core as core  # noqa: E402
import lib_bejson_Standards_errors as err  # noqa: E402
import lib_bejson_Standards_validator as val  # noqa: E402

logger = logging.getLogger(__name__)
VERSION = "1.0.0"

AUTHOR_CREDIT = "Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton"
_HOT_LEVELS = ("ERROR", "FATAL")


def _bad(message: str, code: int = err.E_STANDARDS_EXPORT_FORMAT_INVALID) -> err.StandardsLogError:
    return err.StandardsLogError(message, code)


# ---------------------------------------------------------------------------
# Shared filter (read_logs and every exporter use this one function)
# ---------------------------------------------------------------------------
def bejson_standards_export_filter_rows(rows: Iterable[Dict[str, Any]], *, min_level: Optional[str] = None,
                                        max_priority: Optional[int] = None, subsystem: Optional[str] = None,
                                        actor: Optional[str] = None, session: Optional[str] = None,
                                        process_id: Optional[int] = None, category: Optional[str] = None,
                                        flag: Optional[str] = None, event_key: Optional[str] = None,
                                        since: Any = None, until: Any = None,
                                        include_secure_rows: bool = False) -> Iterator[Dict[str, Any]]:
    """Rows (dicts) that satisfy every given filter. since is inclusive, until exclusive (ISO string or datetime,
    naive = UTC). category/flag compare lower-cased. Rows flagged secure are dropped unless include_secure_rows.
    Raises StandardsLogError(258) for an invalid filter value, at call time (not lazily)."""
    floor = 0
    if min_level is not None:
        canon = val.bejson_standards_validator_normalize_level(min_level)
        if canon is None:
            raise _bad(f"min_level {min_level!r} not in {list(val.LEVELS)}")
        floor = val.LEVEL_RANK[canon]
    if max_priority is not None and (not isinstance(max_priority, int) or isinstance(max_priority, bool)
                                     or not val.PRIORITY_MIN <= max_priority <= val.PRIORITY_MAX):
        raise _bad(f"max_priority must be an integer {val.PRIORITY_MIN}..{val.PRIORITY_MAX}, got {max_priority!r}")
    if process_id is not None and (not isinstance(process_id, int) or isinstance(process_id, bool)):
        raise _bad(f"process_id must be an integer, got {process_id!r}")
    t_since = t_until = None
    if since is not None:
        t_since = val.bejson_standards_validator_parse_time(since)
        if t_since is None:
            raise _bad(f"since {since!r} is not a datetime or ISO-8601 string")
    if until is not None:
        t_until = val.bejson_standards_validator_parse_time(until)
        if t_until is None:
            raise _bad(f"until {until!r} is not a datetime or ISO-8601 string")
    want_cat = category.strip().lower() if isinstance(category, str) else category
    want_flag = flag.strip().lower() if isinstance(flag, str) else flag

    def keep(row: Dict[str, Any]) -> bool:
        if not include_secure_rows and row.get(val.F_EVENT_SECURE) is True:
            return False                                    # defence in depth: secure rows never leak via a main-log query
        level = row.get(val.F_EVENT_LEVEL)
        if val.LEVEL_RANK.get(level, -1) < floor:
            return False
        if max_priority is not None and val.bejson_standards_validator_effective_priority(
                level, row.get(val.F_EVENT_PRIORITY)) > max_priority:
            return False
        if subsystem is not None and row.get(val.F_SENDER_SUBSYSTEM) != subsystem:
            return False
        if actor is not None and row.get(val.F_SENDER_ACTOR) != actor:
            return False
        if session is not None and row.get(val.F_SENDER_SESSION) != session:
            return False
        if process_id is not None and row.get(val.F_SENDER_PID) != process_id:
            return False
        if want_cat is not None and row.get(val.F_EVENT_CATEGORY) != want_cat:
            return False
        if event_key is not None and row.get(val.F_EVENT_KEY) != event_key:
            return False
        if want_flag is not None and want_flag not in val.bejson_standards_validator_parse_flags(row.get(val.F_EVENT_FLAGS)):
            return False
        if t_since is not None or t_until is not None:
            ts = val.bejson_standards_validator_parse_time(row.get(val.F_EVENT_TIMESTAMP))
            if ts is None or (t_since is not None and ts < t_since) or (t_until is not None and ts >= t_until):
                return False
        return True

    return (row for row in rows if keep(row))


def bejson_standards_export_iter_rows(live_path: str, archive_dir: Optional[str] = None, period: Optional[str] = None,
                                      secure: bool = False) -> Iterator[Dict[str, Any]]:
    """Entry dicts, oldest first: verified archive files (when archive_dir given), then the live log."""
    if archive_dir:
        for key, apath in core.bejson_standards_core_list_archives(archive_dir, core._stem(live_path), period):
            if core.bejson_standards_core_is_verified_archive(apath, key, secure):
                adoc = core.bejson_standards_core_load(apath)
                if adoc is not None:
                    yield from core.bejson_standards_core_rows_to_dicts(adoc)
    doc = core.bejson_standards_core_load(live_path)
    if doc is not None:
        yield from core.bejson_standards_core_rows_to_dicts(doc)


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------
def _eff(row: Dict[str, Any]) -> int:
    return val.bejson_standards_validator_effective_priority(row.get(val.F_EVENT_LEVEL), row.get(val.F_EVENT_PRIORITY))


def _shape(row: Dict[str, Any], include_context: bool) -> Dict[str, Any]:
    return row if include_context else {k: v for k, v in row.items() if k != val.F_EVENT_CONTEXT}


def _trunc(text: str, limit: int) -> str:
    return text if limit <= 0 or len(text) <= limit else text[:limit - 1] + "…"


def _sender(row: Dict[str, Any]) -> str:
    sub, act = row.get(val.F_SENDER_SUBSYSTEM) or "", row.get(val.F_SENDER_ACTOR)
    return f"{sub} / {act}" if act else sub


def _write_json(rows: Iterable[Dict[str, Any]], out, include_context: bool) -> None:
    out.write("[")
    first = True
    for row in rows:
        out.write(("\n  " if first else ",\n  ") + json.dumps(_shape(row, include_context), ensure_ascii=False))
        first = False
    out.write("\n]\n" if not first else "]\n")


def _write_ndjson(rows: Iterable[Dict[str, Any]], out, include_context: bool) -> None:
    for row in rows:
        out.write(json.dumps(_shape(row, include_context), ensure_ascii=False) + "\n")


def _md_cell(value: Any, limit: int = 0) -> str:
    text = "" if value is None else str(value)
    text = _trunc(text.replace("\r", " ").replace("\n", " "), limit)
    text = html.escape(text, quote=False)
    for ch in ("\\", "|", "`", "[", "]"):
        text = text.replace(ch, "\\" + ch)
    return text


def _write_markdown(rows: List[Dict[str, Any]], out, include_context: bool, title: str, summary: str, limit: int) -> None:
    out.write(f"# {_md_cell(title)}\n\nGenerated {core.bejson_standards_core_utc_now()} · {len(rows)} entries\n\n")
    out.write(f"Filters: {_md_cell(summary)}\n\n")
    head = ["Time (UTC)", "Level", "Pri", "Sender", "Category", "Event", "Message"] + (["Context"] if include_context else [])
    out.write("| " + " | ".join(head) + " |\n|" + "|".join(["---"] * len(head)) + "|\n")
    for r in rows:
        cells = [_md_cell(r.get(val.F_EVENT_TIMESTAMP)), _md_cell(r.get(val.F_EVENT_LEVEL)), str(_eff(r)),
                 _md_cell(_sender(r)), _md_cell(r.get(val.F_EVENT_CATEGORY)), _md_cell(r.get(val.F_EVENT_KEY)),
                 _md_cell(r.get(val.F_EVENT_MESSAGE), limit)]
        if include_context:
            cells.append(_md_cell(r.get(val.F_EVENT_CONTEXT), limit))
        out.write("| " + " | ".join(cells) + " |\n")
    if not rows:
        out.write("\n_No entries._\n")


_CSS = """:root{color-scheme:light dark;--bg:#FFFFFF;--fg:#000000;--accent:#DE2626}
%s
body{background:var(--bg);color:var(--fg);font:14px/1.45 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;margin:0;padding:12px}
h1{font-size:1.25rem;margin:0 0 4px;border-bottom:3px solid var(--accent);padding-bottom:6px}
.meta{margin:6px 0 12px}
.wrap{overflow-x:auto}
table{border-collapse:collapse;width:100%%;min-width:640px}
th,td{border:1px solid var(--fg);padding:4px 6px;text-align:left;vertical-align:top}
th{background:var(--fg);color:var(--bg);position:sticky;top:0}
tr.hot td:first-child{border-left:6px solid var(--accent)}
tr.hot .lvl{color:var(--accent);font-weight:700}
.msg{white-space:pre-wrap;word-break:break-word}
footer{margin-top:14px;font-size:.8rem;border-top:3px solid var(--accent);padding-top:6px}
"""


def _write_html(rows: List[Dict[str, Any]], out, include_context: bool, title: str, summary: str, theme: str, limit: int) -> None:
    esc = lambda v: html.escape("" if v is None else str(v), quote=True)   # noqa: E731
    dark = ":root{--bg:#000000;--fg:#FFFFFF}" if theme == "dark" else ""
    head = ["Time (UTC)", "Level", "Pri", "Sender", "Category", "Event", "Message"] + (["Context"] if include_context else [])
    out.write('<!DOCTYPE html>\n<html lang="en"><head><meta charset="utf-8">\n'
              '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
              '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'">\n'
              f"<title>{esc(title)}</title>\n<style>\n{_CSS % dark}</style></head><body>\n")
    out.write(f"<h1>{esc(title)}</h1>\n<p class=\"meta\">Generated {esc(core.bejson_standards_core_utc_now())} UTC · "
              f"{len(rows)} entries · Filters: {esc(summary)}</p>\n<div class=\"wrap\"><table>\n<thead><tr>")
    out.write("".join(f"<th>{esc(h)}</th>" for h in head) + "</tr></thead>\n<tbody>\n")
    for r in rows:
        hot = r.get(val.F_EVENT_LEVEL) in _HOT_LEVELS or _eff(r) == 1
        cells = [f"<td>{esc(r.get(val.F_EVENT_TIMESTAMP))}</td>",
                 f'<td class="lvl">{esc(r.get(val.F_EVENT_LEVEL))}</td>', f"<td>{_eff(r)}</td>",
                 f"<td>{esc(_sender(r))}</td>", f"<td>{esc(r.get(val.F_EVENT_CATEGORY))}</td>",
                 f"<td>{esc(r.get(val.F_EVENT_KEY))}</td>",
                 f'<td class="msg">{esc(_trunc(str(r.get(val.F_EVENT_MESSAGE) or ""), limit))}</td>']
        if include_context:
            cells.append(f'<td class="msg">{esc(_trunc(str(r.get(val.F_EVENT_CONTEXT) or ""), limit))}</td>')
        out.write(f'<tr class="{"hot" if hot else "row"}">' + "".join(cells) + "</tr>\n")
    if not rows:
        out.write(f'<tr><td colspan="{len(head)}">No entries.</td></tr>\n')
    out.write(f"</tbody></table></div>\n<footer>{esc(AUTHOR_CREDIT)}</footer>\n</body></html>\n")


# ---------------------------------------------------------------------------
# Destinations
# ---------------------------------------------------------------------------
def bejson_standards_export_check_secure_destination(dest: Any, main_log_path: str,
                                                     non_secure_archive_dirs: Iterable[Optional[str]] = ()) -> None:
    """A secure export may not target the main log file or anything inside the main archive tree (E261).
    Streams and text (dest=None) are the caller's own responsibility."""
    if dest is None or hasattr(dest, "write"):
        return
    real = os.path.realpath(os.fspath(dest))
    if real == os.path.realpath(main_log_path):
        raise _bad(f"secure export destination is the main log {main_log_path}", err.E_STANDARDS_EXPORT_SECURE_DESTINATION)
    for d in non_secure_archive_dirs:
        if d:
            root = os.path.realpath(os.fspath(d))
            if real == root or real.startswith(root + os.sep):
                raise _bad(f"secure export destination is inside the non-secure archive tree {d}",
                           err.E_STANDARDS_EXPORT_SECURE_DESTINATION)


def _deliver(dest: Any, produce: Callable[[Any], None], secure: bool, overwrite: bool,
             forbidden: Iterable[str]) -> Tuple[Optional[str], Optional[str]]:
    """Run produce(out) into text, a stream, or an atomically replaced file. Returns (dest label, text)."""
    if dest is None:
        buf = io.StringIO()
        produce(buf)
        return None, buf.getvalue()
    if hasattr(dest, "write"):
        produce(dest)
        return "stream", None
    path = os.path.abspath(os.fspath(dest))
    real = os.path.realpath(path)
    if real in {os.path.realpath(f) for f in forbidden}:
        raise _bad(f"refusing to overwrite a registered log file: {path}", err.E_STANDARDS_EXPORT_FAILED)
    if os.path.exists(path) and not overwrite:
        raise _bad(f"{path} exists and overwrite=False", err.E_STANDARDS_EXPORT_FAILED)
    parent = os.path.dirname(path)
    tmp = f"{path}.tmp-{os.getpid()}-{uuid.uuid4().hex[:8]}"
    try:
        if secure:
            os.makedirs(parent, mode=0o700, exist_ok=True)
        else:
            os.makedirs(parent, exist_ok=True)
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600 if secure else 0o666)   # 0600 from the first byte
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            produce(fh)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
        if secure:
            core._harden(path)
    except Exception as exc:  # noqa: BLE001
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise _bad(f"could not write export to {path}: {exc}", err.E_STANDARDS_EXPORT_FAILED)
    return path, None


def bejson_standards_export_render(rows: Iterable[Dict[str, Any]], fmt: str = "json", dest: Any = None, *,
                                   include_context: Optional[bool] = None, sort: str = "time", theme: str = "light",
                                   title: Optional[str] = None, max_message_chars: int = 2000, secure: bool = False,
                                   overwrite: bool = True, forbidden: Iterable[str] = (), limit: Optional[int] = None,
                                   filters_summary: str = "none") -> Dict[str, Any]:
    """Write rows (already filtered dicts) in fmt to dest: None -> returned as text, a stream, or a file path
    (written atomically, 0600 from creation when secure, parent directory 0700 if created).
    include_context defaults to True for json/ndjson and False for markdown/html. limit keeps the last N rows.
    Returns {"ok": True, "rows": n, "dest": path|"stream"|None, "text": str|None}. Raises StandardsLogError (258/259)."""
    problems = val.bejson_standards_validator_check_export_options(fmt, sort, theme)
    if limit is not None and (not isinstance(limit, int) or isinstance(limit, bool) or limit < 1):
        problems.append(f"limit must be an integer >= 1, got {limit!r}")
    if problems:
        raise _bad("; ".join(problems))
    ctx = (fmt in ("json", "ndjson")) if include_context is None else bool(include_context)
    heading = title or "Standards log export"
    count = [0]

    def counted(it: Iterable[Dict[str, Any]]) -> Iterator[Dict[str, Any]]:
        for row in it:
            count[0] += 1
            yield row

    if fmt in ("json", "ndjson") and sort == "time" and limit is None:
        source: Any = counted(rows)                              # streamed, never held in memory
    else:
        items = list(deque(rows, maxlen=limit)) if limit else list(rows)
        if sort == "priority":
            items.sort(key=lambda r: str(r.get(val.F_EVENT_TIMESTAMP) or ""), reverse=True)   # newest first within a priority
            items.sort(key=_eff)                                                                  # stable: priority 1 first
        count[0] = len(items)
        source = items

    def produce(out: Any) -> None:
        if fmt == "json":
            _write_json(source, out, ctx)
        elif fmt == "ndjson":
            _write_ndjson(source, out, ctx)
        elif fmt == "markdown":
            _write_markdown(source, out, ctx, heading, filters_summary, max_message_chars)
        else:
            _write_html(source, out, ctx, heading, filters_summary, theme, max_message_chars)

    label, text = _deliver(dest, produce, secure, overwrite, forbidden)
    return {"ok": True, "rows": count[0], "dest": label, "text": text}
