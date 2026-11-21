"""
Library:         lib_bejson_AI_Core_context_bubble.py
Family:          AI_Core
Module Purpose:  BEJSON 105 Context Bubble Engine & Preprocessor (Ranked Allotments, Spill-Up Allocator, Two-Level Chunk Verification)
Architecture:    BEJSON 105 Multi-AI Gateway (Tier 2: Inbound Context Bubble & Preprocessor Gate)
Version:         3.0.0
Release_Version: 300
Date:            2026-11-20
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Format_Creator:  Elton Boehnen
RELATIONAL_ID:   2de45989-c5ac-499d-ada9-7378ff3f2508

Changelog:
  3.0.0 (2026-11-20) -- Ported from lib_bejson_AI_ai_context_bubble 2.2.0 (104 family AI) to BEJSON 105 AI_Core:
        * Config persisted as Format 105a (config/context_bubble.105a.bejson) with automatic migration from 104a context_bubble.bejson.
        * All BEJSON and chunking I/O routed strictly through lib_bejson_AI_Core_core_bridge.
        * Default Rebuild_Interval_Turns set to 7 (configurable in context_bubble.105a.bejson or per-call interval_override).
        * Added ContextBubblePreParser (BaseModularParser) for Tier 2 preprocessor pipeline integration.
"""
from __future__ import annotations

import hashlib
import json
import logging
import math
import re
import shutil
import sys
import tempfile
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

_SELF_DIR = Path(__file__).resolve().parent
if str(_SELF_DIR) not in sys.path:
    sys.path.insert(0, str(_SELF_DIR))

from lib_bejson_AI_Core_core_bridge import (  # noqa: E402
    core_add_record,
    core_atomic_write_json,
    core_chunk_bump_package_version,
    core_chunk_create,
    core_chunk_hash_bytes,
    core_field_map,
    core_load,
    core_load_json,
    core_new_document,
    core_quarantine,
    core_rows_as_dicts,
    core_save,
    core_write_bytes_file,
    core_write_cell,
    core_write_text_file,
)
from lib_bejson_AI_Core_errors import AIException  # noqa: E402
from lib_bejson_AI_Core_parser_base import BaseModularParser  # noqa: E402

VERSION = "3.0.0"
logger = logging.getLogger("lib_bejson_AI_Core_context_bubble")

# ── Declared constants ────────────────────────────────────────────────────────

BUBBLE_MAX_ALLOTMENTS = 8

DEFAULT_REBUILD_INTERVAL_TURNS = 7
DEFAULT_MAX_CONTEXT_TOKENS = 16000
DEFAULT_CHARS_PER_TOKEN = 4

CONFIG_FILENAME = "context_bubble.105a.bejson"
LEGACY_CONFIG_FILENAME = "context_bubble.bejson"
BUBBLE_DIRNAME = "bubble"
ALLOTMENTS_SUBDIR = "allotments"
STAGE_SUBDIR = "_stage"
BUBBLE_CHUNK_FILENAME = "Context_Bubble.104a.bejson"
STATE_FILENAME = "bubble_state.json"
_POLICY_FILENAME = "Persistent_Policy.md"
_AMNESIA_FILENAME = "amnesia_recap.txt"

REFRESH_STABLE = "stable"   # change => rebuild + counter reset
REFRESH_TURN = "turn"       # re-chunked every turn, never triggers rebuild
KEEP_START = "start"
KEEP_END = "end"

_NAME_RE = re.compile(r"^[a-z][a-z0-9_]{0,31}$")
_UNASSIGNED = "(unassigned)"
_MIN_USEFUL_CHARS = 40
_SOURCE_SLACK_CHARS = 1024
_MAX_RANK = 1_000_000
_MAX_INTERVAL = 1_000_000
_TRUNC_MARK_TAIL = "\n[...truncated: over allotment budget]"
_TRUNC_MARK_HEAD = "[...earlier content truncated: over allotment budget]\n"
_WRAP_OPEN = "[CONTEXT BUBBLE]\n"
_WRAP_CLOSE = "\n[END CONTEXT BUBBLE]"

_CONFIG_FIELD_SPECS: Tuple[Tuple[str, str], ...] = (
    ("name", "string"),
    ("rank", "integer"),
    ("pct", "number"),
    ("enabled", "boolean"),
    ("refresh", "string"),
    ("keep", "string"),
    ("label", "string"),
    ("directive", "string"),
)

_LOCK = threading.RLock()


class BubbleIntegrityError(Exception):
    """A chunk row's SHA-256 File_Hash did not match its content."""


# ── Plugin hook / registry ────────────────────────────────────────────────────

@dataclass
class BubbleContext:
    """Everything a builder may need. extras carries caller data
    (attached_file_ids, history, profile_instruction, url_context, ...)."""
    user_msg: str
    turn: int
    constants: Dict[str, Any]
    context_dir: Path
    config_dir: Path
    budget_chars: int = 0
    extras: Dict[str, Any] = field(default_factory=dict)


@dataclass
class _Registered:
    name: str
    label: str
    builder: Callable[[BubbleContext], str]
    pct: Optional[float]
    rank: Optional[int]
    enabled: bool
    refresh: str
    keep: str
    directive: str
    group: str = ""


_registry: Dict[str, _Registered] = {}
_warned: set = set()


def _warn_once(key: str, msg: str, *args: Any) -> None:
    if key not in _warned:
        _warned.add(key)
        logger.warning(msg, *args)


def _clean_str(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ("" if value is None else str(value).strip())


def ai_bubble_register_allotment(
    name: str,
    builder_fn: Callable[[BubbleContext], str],
    *,
    label: Optional[str] = None,
    pct: Optional[float] = None,
    rank: Optional[int] = None,
    enabled: bool = True,
    refresh: str = REFRESH_STABLE,
    keep: str = KEEP_START,
    directive: str = "",
    group: str = "",
) -> bool:
    """
    Plugin hook. Registers an allotment. pct/rank/enabled/... are defaults
    used to add a row to context_bubble.105a.bejson the first time the name
    is seen; afterwards the file is authoritative.
    """
    name = (name or "").strip()
    if not _NAME_RE.match(name):
        logger.error("[AIContextBubble] Invalid allotment name %r (use a-z, 0-9, _).", name)
        return False
    if not callable(builder_fn):
        logger.error("[AIContextBubble] Allotment '%s': builder_fn is not callable.", name)
        return False
    with _LOCK:
        if name not in _registry and len(_registry) >= BUBBLE_MAX_ALLOTMENTS:
            logger.error(
                "[AIContextBubble] Cannot register '%s': BUBBLE_MAX_ALLOTMENTS=%d reached.",
                name,
                BUBBLE_MAX_ALLOTMENTS,
            )
            return False
        if refresh not in (REFRESH_STABLE, REFRESH_TURN):
            refresh = REFRESH_STABLE
        if keep not in (KEEP_START, KEEP_END):
            keep = KEEP_START
        _registry[name] = _Registered(
            name=name,
            label=(label or name).strip(),
            builder=builder_fn,
            pct=pct,
            rank=rank,
            enabled=enabled,
            refresh=refresh,
            keep=keep,
            directive=(directive or "").strip(),
            group=_clean_str(group).lower(),
        )
    return True


def ai_bubble_unregister_allotment(name: str) -> bool:
    with _LOCK:
        return _registry.pop(name, None) is not None


def ai_bubble_clear_allotments() -> None:
    """Removes every registered allotment (tests / re-init)."""
    with _LOCK:
        _registry.clear()
        _warned.clear()


def ai_bubble_registered_names() -> List[str]:
    with _LOCK:
        return list(_registry)


# ── Config (context_bubble.105a.bejson) ───────────────────────────────────────

def _to_bool(value: Any, default: bool = True) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("true", "1", "yes", "on")
    if value is None:
        return default
    return bool(value)


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        v = float(value)
    except (TypeError, ValueError, OverflowError):
        return default
    if not math.isfinite(v):
        return default
    return min(100.0, max(0.0, v))


def _to_int(value: Any, default: int, maximum: int = _MAX_RANK) -> int:
    try:
        f = float(value)
        if not math.isfinite(f):
            return default
        v = int(f)
    except (TypeError, ValueError, OverflowError):
        return default
    return min(maximum, v) if v >= 1 else default


def _dict_from_registered(reg: _Registered, pct: float, rank: int) -> Dict[str, Any]:
    return {
        "name": reg.name,
        "rank": rank,
        "pct": float(pct),
        "enabled": bool(reg.enabled),
        "refresh": reg.refresh,
        "keep": reg.keep,
        "label": reg.label,
        "directive": reg.directive,
    }


def _config_path(config_dir: Path) -> Path:
    return Path(config_dir) / CONFIG_FILENAME


def _legacy_config_path(config_dir: Path) -> Path:
    return Path(config_dir) / LEGACY_CONFIG_FILENAME


def _build_config_doc_105a(
    records: List[Dict[str, Any]],
    interval: int,
    normalize: bool = True,
) -> Dict[str, Any]:
    doc = core_new_document(
        "105a",
        "Allotment",
        _CONFIG_FIELD_SPECS,
        Schema_Name="ContextBubbleConfig",
        Schema_Version="3.0.0",
        Rebuild_Interval_Turns=int(interval),
        Normalize_Baselines=bool(normalize),
    )
    for rec in records:
        core_add_record(doc, rec)
    return doc


def _migrate_legacy_104_config(legacy_path: Path, target_105_path: Path) -> bool:
    """Convert an existing 104a context_bubble.bejson into 105a context_bubble.105a.bejson."""
    try:
        raw_doc = core_load_json(legacy_path)
        if not isinstance(raw_doc, dict) or not isinstance(raw_doc.get("Values"), list):
            return False
        interval = _to_int(raw_doc.get("Rebuild_Interval_Turns"), DEFAULT_REBUILD_INTERVAL_TURNS, _MAX_INTERVAL)
        normalize = _to_bool(raw_doc.get("Normalize_Baselines"), True)
        fmap = {str(f.get("name", "")).strip(): idx for idx, f in enumerate(raw_doc.get("Fields", []))}
        records: List[Dict[str, Any]] = []
        for row in raw_doc.get("Values", []):
            def _cell(col: str, default: Any = None) -> Any:
                pos = fmap.get(col)
                return row[pos] if pos is not None and pos < len(row) else default
            name = _clean_str(_cell("name"))
            if not _NAME_RE.match(name):
                continue
            refresh = _clean_str(_cell("refresh")).lower()
            keep = _clean_str(_cell("keep")).lower()
            records.append({
                "name": name,
                "rank": _to_int(_cell("rank"), 99),
                "pct": _to_float(_cell("pct"), 0.0),
                "enabled": _to_bool(_cell("enabled"), True),
                "refresh": refresh if refresh in (REFRESH_STABLE, REFRESH_TURN) else REFRESH_STABLE,
                "keep": keep if keep in (KEEP_START, KEEP_END) else KEEP_START,
                "label": _clean_str(_cell("label")) or name,
                "directive": _clean_str(_cell("directive")),
            })
        doc_105 = _build_config_doc_105a(records, interval, normalize)
        core_save(target_105_path, doc_105)
        return True
    except Exception as exc:
        logger.warning("[AIContextBubble] Legacy config migration failed (%s).", exc)
        return False


def ai_bubble_config_init(config_dir: Path, default_interval: Optional[int] = None) -> Path:
    """Creates context_bubble.105a.bejson if absent (even split across registered
    allotments) and appends rows for registered allotments missing from an existing file."""
    config_dir = Path(config_dir)
    config_dir.mkdir(parents=True, exist_ok=True)
    path = _config_path(config_dir)
    legacy_path = _legacy_config_path(config_dir)
    regs = list(_registry.values())
    effective_interval = _to_int(default_interval, DEFAULT_REBUILD_INTERVAL_TURNS, _MAX_INTERVAL)

    if not path.exists() and legacy_path.exists():
        _migrate_legacy_104_config(legacy_path, path)

    if not path.exists():
        n = len(regs)
        even = round(100.0 / n, 2) if n else 0.0
        used_ranks: set = set()
        records: List[Dict[str, Any]] = []
        for i, reg in enumerate(regs, start=1):
            rank = reg.rank if reg.rank and reg.rank not in used_ranks else i
            while rank in used_ranks:
                rank += 1
            used_ranks.add(rank)
            records.append(
                _dict_from_registered(reg, reg.pct if reg.pct is not None else even, rank)
            )
        try:
            core_save(path, _build_config_doc_105a(records, effective_interval))
        except AIException as exc:
            logger.error("[AIContextBubble] Could not write %s: %s", path, exc)
        return path

    try:
        doc = core_load(path)
    except AIException as exc:
        logger.error("[AIContextBubble] %s unreadable (%s); leaving it untouched.", path, exc)
        return path

    rows = core_rows_as_dicts(doc)
    present = {_clean_str(r.get("name")) for r in rows}
    ranks = [_to_int(r.get("rank"), 0) for r in rows]
    missing = [r for r in regs if r.name not in present]
    if missing:
        next_rank = max(ranks + [0]) + 1
        for reg in missing:
            chosen_rank = reg.rank or next_rank
            core_add_record(
                doc,
                _dict_from_registered(
                    reg,
                    reg.pct if reg.pct is not None else 0.0,
                    chosen_rank,
                ),
            )
            next_rank = max(next_rank, chosen_rank) + 1
        try:
            core_save(path, doc)
        except AIException as exc:
            logger.error("[AIContextBubble] Failed to update missing allotments in %s: %s", path, exc)
    return path


def ai_bubble_config_load(config_dir: Path, interval_override: Optional[int] = None) -> Dict[str, Any]:
    """Returns {"interval": int, "rows": [dict, ...], "normalize": bool} sorted by rank."""
    path = ai_bubble_config_init(Path(config_dir), default_interval=interval_override)
    try:
        doc = core_load(path)
    except AIException:
        doc = None

    interval = _to_int(interval_override, DEFAULT_REBUILD_INTERVAL_TURNS, _MAX_INTERVAL)
    normalize = _to_bool(doc.get("Normalize_Baselines"), True) if isinstance(doc, dict) else True
    rows: List[Dict[str, Any]] = []

    if not isinstance(doc, dict) or not isinstance(doc.get("Values"), list):
        _warn_once("cfg-corrupt", "[AIContextBubble] %s unreadable; using registered defaults in memory.", path)
        with _LOCK:
            regs = list(_registry.values())
        even = round(100.0 / len(regs), 2) if regs else 0.0
        for i, reg in enumerate(regs, start=1):
            rows.append({
                "name": reg.name,
                "rank": reg.rank or i,
                "pct": reg.pct if reg.pct is not None else even,
                "enabled": reg.enabled,
                "refresh": reg.refresh,
                "keep": reg.keep,
                "label": reg.label,
                "directive": reg.directive,
            })
        rows.sort(key=lambda r: (r["rank"], r["name"]))
        return {"interval": interval, "rows": rows, "normalize": normalize}

    if interval_override is None:
        interval = _to_int(doc.get("Rebuild_Interval_Turns"), DEFAULT_REBUILD_INTERVAL_TURNS, _MAX_INTERVAL)
    seen = set()
    for raw_row in core_rows_as_dicts(doc):
        name = _clean_str(raw_row.get("name"))
        if not _NAME_RE.match(name) or name in seen:
            logger.warning("[AIContextBubble] Skipping bad/duplicate config row %r.", name)
            continue
        seen.add(name)
        refresh = _clean_str(raw_row.get("refresh")).lower()
        keep = _clean_str(raw_row.get("keep")).lower()
        rows.append({
            "name": name,
            "rank": _to_int(raw_row.get("rank"), 99),
            "pct": _to_float(raw_row.get("pct"), 0.0),
            "enabled": _to_bool(raw_row.get("enabled"), True),
            "refresh": refresh if refresh in (REFRESH_STABLE, REFRESH_TURN) else REFRESH_STABLE,
            "keep": keep if keep in (KEEP_START, KEEP_END) else KEEP_START,
            "label": _clean_str(raw_row.get("label")) or name,
            "directive": _clean_str(raw_row.get("directive")),
        })
    rows.sort(key=lambda r: (r["rank"], r["name"]))
    return {"interval": interval, "rows": rows, "normalize": normalize}


# ── Allocator (pure) ──────────────────────────────────────────────────────────

def _split_evenly(capacity: Dict[str, int], amount: int) -> Dict[str, int]:
    """Takes `amount` from the keys, as equally as their capacities allow."""
    give = {k: 0 for k in capacity}
    remaining = min(max(0, amount), sum(capacity.values()))
    while remaining > 0:
        open_keys = sorted(k for k, c in capacity.items() if c - give[k] > 0)
        if not open_keys:
            break
        share = remaining // len(open_keys)
        if share == 0:
            for k in open_keys[:remaining]:
                give[k] += 1
            break
        for k in open_keys:
            g = min(share, capacity[k] - give[k])
            give[k] += g
            remaining -= g
    return give


def _normalise_pcts(pcts: Dict[str, float]) -> Dict[str, float]:
    """If the baselines add up to more than 100, cut EVENLY until they sum to 100."""
    out = dict(pcts)
    excess = sum(out.values()) - 100.0
    while excess > 1e-9:
        open_keys = [k for k, v in out.items() if v > 1e-12]
        if not open_keys:
            break
        cut = excess / len(open_keys)
        for k in open_keys:
            c = min(cut, out[k])
            out[k] -= c
            excess -= c
    return out


def ai_bubble_allocate(total_chars: int, items: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    items: [{"name", "rank", "pct", "demand"}] -- demand in chars (header
    included). Returns name -> {budget, demand, grant, spill_in, spill_out,
    sources: {donor: chars}, truncated}.
    """
    total_chars = max(0, int(total_chars))
    pcts = _normalise_pcts({i["name"]: float(i["pct"]) for i in items})
    result: Dict[str, Dict[str, Any]] = {}
    capacity: Dict[str, int] = {}
    for it in items:
        budget = int(total_chars * pcts[it["name"]] / 100.0)
        demand = max(0, int(it["demand"]))
        keep_own = min(demand, budget)
        result[it["name"]] = {
            "budget": budget,
            "demand": demand,
            "grant": keep_own,
            "spill_in": 0,
            "spill_out": 0,
            "sources": {},
            "truncated": False,
        }
        if budget - keep_own > 0:
            capacity[it["name"]] = budget - keep_own
    unassigned = total_chars - sum(r["budget"] for r in result.values())
    if unassigned > 0:
        capacity[_UNASSIGNED] = unassigned

    for it in sorted(items, key=lambda i: (i["rank"], i["name"])):
        r = result[it["name"]]
        need = r["demand"] - r["budget"]
        if need <= 0:
            continue
        taken = _split_evenly(capacity, need)
        total_taken = 0
        for donor, amt in taken.items():
            if amt <= 0:
                continue
            capacity[donor] -= amt
            r["sources"][donor] = amt
            total_taken += amt
            if donor in result:
                result[donor]["spill_out"] += amt
        r["spill_in"] = total_taken
        r["grant"] = r["budget"] + total_taken
    for r in result.values():
        r["truncated"] = r["demand"] > r["grant"]
    return result


# ── Truncation / rendering ────────────────────────────────────────────────────

def _truncate(text: str, room: int, keep: str) -> str:
    if len(text) <= room:
        return text
    mark = _TRUNC_MARK_HEAD if keep == KEEP_END else _TRUNC_MARK_TAIL
    keep_chars = room - len(mark)
    if keep_chars < _MIN_USEFUL_CHARS:
        return ""
    if keep == KEEP_END:
        piece = text[-keep_chars:]
        nl = piece.find("\n", 0, 200)
        if nl != -1:
            piece = piece[nl + 1:]
        return mark + piece
    piece = text[:keep_chars]
    nl = piece.rfind("\n", max(0, keep_chars - 200))
    if nl > 0:
        piece = piece[:nl]
    return piece + mark


def _header(row: Dict[str, Any]) -> str:
    h = f"## {row['label']}\n"
    if row["directive"]:
        h += f"{row['directive']}\n"
    return h


_SEP = "\n\n"


# ── Paths / state ─────────────────────────────────────────────────────────────

def _paths(root: Path) -> Dict[str, Path]:
    root = Path(root)
    bdir = root / BUBBLE_DIRNAME
    return {
        "dir": bdir,
        "allotments": bdir / ALLOTMENTS_SUBDIR,
        "stage": bdir / STAGE_SUBDIR,
        "chunk": root / BUBBLE_CHUNK_FILENAME,
        "state": root / STATE_FILENAME,
        "policy": root / _POLICY_FILENAME,
    }


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", "replace")).hexdigest()


def _clean_text(text: Any) -> str:
    if not isinstance(text, str):
        return ""
    text = text.encode("utf-8", "replace").decode("utf-8").strip()
    if "CONTEXT BUBBLE]" in text:
        text = (
            text.replace("[END CONTEXT BUBBLE]", "[END CONTEXT-BUBBLE]")
            .replace("[CONTEXT BUBBLE]", "[CONTEXT-BUBBLE]")
        )
    return text


def _cap_source(text: str, limit: int, keep: str) -> str:
    if len(text) <= limit:
        return text
    return text[-limit:] if keep == KEEP_END else text[:limit]


def _load_state(root: Path) -> Dict[str, Any]:
    p = _paths(root)["state"]
    if not p.is_file():
        return {}
    data = core_load_json(p)
    if not isinstance(data, dict):
        return {}
    for key in ("turn", "turns_since_rebuild", "rebuild_count"):
        v = data.get(key, 0)
        data[key] = v if isinstance(v, int) and not isinstance(v, bool) and v >= 0 else 0
    for key in ("stable", "volatile"):
        v = data.get(key)
        data[key] = (
            {k: x for k, x in v.items() if isinstance(k, str) and isinstance(x, str)}
            if isinstance(v, dict)
            else {}
        )
    if not isinstance(data.get("config_sig"), str):
        data.pop("config_sig", None)
    data["package_version"] = str(data.get("package_version", "0"))
    return data


def _save_state(root: Path, state: Dict[str, Any]) -> None:
    if not core_atomic_write_json(_paths(root)["state"], state):
        logger.error("[AIContextBubble] Could not persist bubble state.")


def ai_bubble_destroy(root: Path) -> bool:
    """Deletes the bubble directory and the bubble chunk. The next prepare
    rebuilds from scratch. Returns True if anything was removed."""
    p = _paths(Path(root))
    removed = False
    if p["dir"].exists():
        shutil.rmtree(p["dir"], ignore_errors=True)
        removed = True
    if p["chunk"].exists():
        try:
            p["chunk"].unlink()
            removed = True
        except OSError as exc:
            logger.warning("[AIContextBubble] Could not remove bubble chunk: %s", exc)
    return removed


# ── Chunking ──────────────────────────────────────────────────────────────────

def _remove_allotment_chunk(root: Path, name: str) -> None:
    adir = _paths(root)["allotments"]
    if adir.is_dir():
        for f in adir.glob(f"*_{name}.104a.bejson"):
            try:
                f.unlink()
            except OSError:
                pass


def _chunk_allotment(root: Path, rank: int, name: str, text: str, file_version: str, pkg: str) -> None:
    """Writes the allotment text to a stage dir, chunks it via the Core bridge,
    stores the chunk in bubble/allotments/, and removes the stage."""
    p = _paths(root)
    stage = p["stage"] / name
    shutil.rmtree(stage, ignore_errors=True)
    stage.mkdir(parents=True, exist_ok=True)
    core_write_bytes_file(stage / f"{name}.txt", text.encode("utf-8"))
    try:
        doc = core_chunk_create(
            stage,
            version=file_version,
            extensions=[".txt"],
            exclude_dirs=[],
            package_version=pkg,
        )
    finally:
        shutil.rmtree(stage, ignore_errors=True)
    _remove_allotment_chunk(root, name)
    p["allotments"].mkdir(parents=True, exist_ok=True)
    target = p["allotments"] / f"{rank:02d}_{name}.104a.bejson"
    if not core_atomic_write_json(target, doc):
        raise OSError(f"could not write allotment chunk {target}")


def _chunk_bubble(root: Path, file_version: str, pkg: str) -> None:
    """Chunks the whole bubble directory into one Chunked-104a document."""
    p = _paths(root)
    p["dir"].mkdir(parents=True, exist_ok=True)
    shutil.rmtree(p["stage"], ignore_errors=True)
    doc = core_chunk_create(
        p["dir"],
        version=file_version,
        extensions=[".bejson"],
        exclude_dirs=[STAGE_SUBDIR],
        package_version=pkg,
    )
    if not core_atomic_write_json(p["chunk"], doc):
        raise OSError(f"could not write bubble chunk {p['chunk']}")


def _read_bubble(root: Path) -> Dict[str, str]:
    """Reads the bubble chunk, verifies every File_Hash at both levels, and
    returns {allotment_name: text}. Raises BubbleIntegrityError."""
    chunk_path = _paths(root)["chunk"]
    doc = core_load_json(chunk_path) if chunk_path.exists() else None
    if not isinstance(doc, dict):
        raise BubbleIntegrityError("bubble chunk missing or unreadable")
    fm = core_field_map(doc)
    out: Dict[str, str] = {}
    for row in doc.get("Values", []):
        rel = str(row[fm["Relative_Path"]]).replace("\\", "/")
        content = row[fm["File_Content"]]
        if core_chunk_hash_bytes(content.encode("utf-8")) != row[fm["File_Hash"]]:
            raise BubbleIntegrityError(f"hash mismatch in bubble chunk row {rel}")
        m = re.match(rf"^{ALLOTMENTS_SUBDIR}/\d+_([a-z][a-z0-9_]*)\.104a\.bejson$", rel)
        if not m:
            continue
        name = m.group(1)
        try:
            inner = json.loads(content)
            ifm = {f["name"]: i for i, f in enumerate(inner["Fields"])}
            irow = next(r for r in inner["Values"] if r[ifm["File_Name"]] == f"{name}.txt")
        except (ValueError, KeyError, StopIteration) as exc:
            raise BubbleIntegrityError(f"allotment chunk '{name}' malformed: {exc}") from exc
        text = irow[ifm["File_Content"]]
        if core_chunk_hash_bytes(text.encode("utf-8")) != irow[ifm["File_Hash"]]:
            raise BubbleIntegrityError(f"hash mismatch in allotment chunk '{name}'")
        out[name] = text
    return out


# ── Prepare (per-turn entry point) ────────────────────────────────────────────

def _constants(config_dir: Path, overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    c: Dict[str, Any] = dict(overrides or {})
    try:
        c["max_context_tokens"] = max(1, int(c.get("max_context_tokens", DEFAULT_MAX_CONTEXT_TOKENS)))
    except (TypeError, ValueError):
        c["max_context_tokens"] = DEFAULT_MAX_CONTEXT_TOKENS
    try:
        cpt = int(c.get("chars_per_token", DEFAULT_CHARS_PER_TOKEN))
    except (TypeError, ValueError):
        cpt = 0
    if cpt <= 0:
        cpt = DEFAULT_CHARS_PER_TOKEN
    c["chars_per_token"] = cpt
    return c


def _run_builders(active: List[Dict[str, Any]], ctx: BubbleContext) -> Dict[str, str]:
    texts: Dict[str, str] = {}
    limit = ctx.budget_chars + _SOURCE_SLACK_CHARS
    for row in active:
        reg = _registry.get(row["name"])
        if reg is None:
            texts[row["name"]] = ""
            continue
        try:
            texts[row["name"]] = _cap_source(_clean_text(reg.builder(ctx)), limit, row["keep"])
        except Exception as exc:
            logger.warning("[AIContextBubble] Allotment '%s' builder failed: %s", row["name"], exc)
            texts[row["name"]] = ""
    return texts


def _select_active(cfg: Dict[str, Any], skip: Tuple[str, ...]) -> List[Dict[str, Any]]:
    active = [
        r for r in cfg["rows"]
        if r["enabled"] and r["name"] in _registry and r["name"] not in skip
    ]
    if len(active) > BUBBLE_MAX_ALLOTMENTS:
        _warn_once(
            "max-allot",
            "[AIContextBubble] %d active allotments exceed BUBBLE_MAX_ALLOTMENTS=%d; dropping lowest ranks.",
            len(active),
            BUBBLE_MAX_ALLOTMENTS,
        )
        active = active[:BUBBLE_MAX_ALLOTMENTS]
    return active


def _effective_pcts(active: List[Dict[str, Any]], normalize: bool) -> Dict[str, float]:
    raw = {r["name"]: float(r["pct"]) for r in active}
    if not raw:
        return {}
    if not normalize:
        return _normalise_pcts(raw)
    total = sum(raw.values())
    if total <= 1e-9:
        return {k: 100.0 / len(raw) for k in raw}
    return {k: v * 100.0 / total for k, v in raw.items()}


def _render(
    active: List[Dict[str, Any]],
    chunk_texts: Dict[str, str],
    constants: Dict[str, Any],
    turn: int,
    normalize: bool = True,
    include_text: bool = False,
) -> Dict[str, Any]:
    cpt = constants["chars_per_token"]
    total_chars = constants["max_context_tokens"] * cpt
    room_total = max(0, total_chars - len(_WRAP_OPEN) - len(_WRAP_CLOSE))
    dropped: set = set()
    alloc: Dict[str, Dict[str, Any]] = {}
    blocks: Dict[str, str] = {}
    shares = _effective_pcts(active, normalize)
    for _ in range(len(active) + 1):
        items = []
        for row in active:
            text = chunk_texts.get(row["name"], "")
            demand = (
                (len(_header(row)) + len(text) + len(_SEP))
                if text and row["name"] not in dropped
                else 0
            )
            items.append({
                "name": row["name"],
                "rank": row["rank"],
                "pct": shares[row["name"]],
                "demand": demand,
            })
        alloc = ai_bubble_allocate(room_total, items)
        blocks = {}
        newly: set = set()
        for row in active:
            name = row["name"]
            text = chunk_texts.get(name, "")
            if not text or name in dropped:
                continue
            head = _header(row)
            room = alloc[name]["grant"] - len(head) - len(_SEP)
            body = _truncate(text, room, row["keep"]) if room > 0 else ""
            if body:
                blocks[name] = head + body
            else:
                newly.add(name)
        if not newly:
            break
        dropped |= newly

    stats: List[Dict[str, Any]] = []
    for row in active:
        a = alloc[row["name"]]
        text = chunk_texts.get(row["name"], "")
        block = blocks.get(row["name"], "")
        stats.append({
            "name": row["name"],
            "label": row["label"],
            "rank": row["rank"],
            "pct": row["pct"],
            "share_pct": round(shares[row["name"]], 2),
            "refresh": row["refresh"],
            "keep": row["keep"],
            "budget_tokens": a["budget"] // cpt,
            "demand_tokens": a["demand"] // cpt,
            "granted_tokens": a["grant"] // cpt,
            "used_tokens": len(block) // cpt,
            "spill_in_tokens": a["spill_in"] // cpt,
            "spill_out_tokens": a["spill_out"] // cpt,
            "sources": {k: v // cpt for k, v in a["sources"].items()},
            "truncated": bool(text) and (a["truncated"] or row["name"] in dropped),
            "empty": not text,
            "dropped": row["name"] in dropped,
        })
        if include_text:
            stats[-1]["text"] = block
    ordered = [blocks[r["name"]] for r in active if r["name"] in blocks]
    payload = (_WRAP_OPEN + _SEP.join(ordered) + _WRAP_CLOSE) if ordered else ""
    return {
        "text": payload,
        "allotments": stats,
        "normalize": normalize,
        "used_tokens": len(payload) // cpt,
        "max_context_tokens": constants["max_context_tokens"],
        "chars_per_token": cpt,
    }


def _config_signature(cfg: Dict[str, Any]) -> str:
    return _sha(json.dumps([cfg["interval"], cfg.get("normalize", True), cfg["rows"]], sort_keys=True))


def ai_bubble_prepare(
    context_dir: Path | str,
    config_dir: Path | str,
    user_msg: str,
    extras: Optional[Dict[str, Any]] = None,
    skip: Tuple[str, ...] = (),
    interval_override: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Per-turn entry point. Advances the turn counter, rebuilds the bubble if
    due (interval reached, content change, or missing), refreshes volatile
    allotments, and returns the payload plus stats.
    """
    context_dir, config_dir = Path(context_dir), Path(config_dir)
    extras, skip = extras or {}, tuple(skip)
    with _LOCK:
        try:
            try:
                return _prepare_locked(
                    context_dir, config_dir, user_msg, extras, skip, interval_override=interval_override
                )
            except BubbleIntegrityError as exc:
                logger.error("[AIContextBubble] Integrity failure (%s); rebuilding once.", exc)
                ai_bubble_destroy(context_dir)
                return _prepare_locked(
                    context_dir,
                    config_dir,
                    user_msg,
                    extras,
                    skip,
                    forced_reason="integrity",
                    interval_override=interval_override,
                )
        except Exception as exc:
            logger.error(
                "[AIContextBubble] Bubble build failed (%s: %s); sending an unchunked bubble.",
                type(exc).__name__,
                exc,
            )
            return _degraded(context_dir, config_dir, user_msg, extras, skip, exc, interval_override=interval_override)


def _degraded(
    context_dir: Path,
    config_dir: Path,
    user_msg: str,
    extras: Dict[str, Any],
    skip: Tuple[str, ...],
    exc: Exception,
    interval_override: Optional[int] = None,
) -> Dict[str, Any]:
    try:
        constants = _constants(config_dir, extras.get("constants"))
        cfg = ai_bubble_config_load(config_dir, interval_override=interval_override)
        active = _select_active(cfg, skip)
        ctx = BubbleContext(
            user_msg=user_msg,
            turn=int(_load_state(context_dir).get("turn", 0)) + 1,
            constants=constants,
            context_dir=context_dir,
            config_dir=config_dir,
            budget_chars=constants["max_context_tokens"] * constants["chars_per_token"],
            extras=extras,
        )
        texts = _run_builders(active, ctx)
        out = _render(active, texts, constants, ctx.turn, cfg.get("normalize", True))
        out.update({
            "rebuilt": False,
            "reason": f"degraded: {type(exc).__name__}",
            "turn": ctx.turn,
            "rebuild_interval": cfg["interval"],
            "turns_until_rebuild": 0,
            "chunk_path": "",
        })
        return out
    except Exception as exc2:
        logger.error("[AIContextBubble] Unchunked bubble failed too (%s); policy only.", exc2)
        out = ai_bubble_minimal(context_dir)
        out["reason"] = f"degraded: {type(exc2).__name__}"
        return out


def _prepare_locked(
    context_dir: Path,
    config_dir: Path,
    user_msg: str,
    extras: Dict[str, Any],
    skip: Tuple[str, ...],
    forced_reason: Optional[str] = None,
    interval_override: Optional[int] = None,
) -> Dict[str, Any]:
    context_dir.mkdir(parents=True, exist_ok=True)
    constants = _constants(config_dir, extras.get("constants"))
    cfg = ai_bubble_config_load(config_dir, interval_override=interval_override)
    active = _select_active(cfg, skip)
    state = _load_state(context_dir)
    turn = int(state.get("turn", 0)) + 1
    ctx = BubbleContext(
        user_msg=user_msg,
        turn=turn,
        constants=constants,
        context_dir=context_dir,
        config_dir=config_dir,
        budget_chars=constants["max_context_tokens"] * constants["chars_per_token"],
        extras=extras,
    )
    texts = _run_builders(active, ctx)

    stable = {r["name"]: _sha(texts[r["name"]]) for r in active if r["refresh"] == REFRESH_STABLE}
    volatile = {r["name"]: _sha(texts[r["name"]]) for r in active if r["refresh"] == REFRESH_TURN}
    cfg_sig = _config_signature(cfg)
    paths = _paths(context_dir)
    interval = cfg["interval"]
    since = int(state.get("turns_since_rebuild", 0))

    changed = sorted(
        n for n in set(stable) | set(state.get("stable", {}))
        if stable.get(n) != state.get("stable", {}).get(n)
    )
    if forced_reason:
        reason = forced_reason
    elif not state or "stable" not in state:
        reason = "first"
    elif not paths["chunk"].exists() or not paths["allotments"].is_dir():
        reason = "missing"
    elif state.get("config_sig") != cfg_sig:
        reason = "changed: config"
    elif changed:
        reason = "changed: " + ",".join(changed)
    elif since + 1 >= interval:
        reason = "interval"
    else:
        reason = "reuse"
    rebuilt = reason != "reuse"

    rebuild_count = int(state.get("rebuild_count", 0))
    pkg = str(state.get("package_version", "0"))
    if rebuilt:
        ai_bubble_destroy(context_dir)
        rebuild_count += 1
        pkg = core_chunk_bump_package_version({"Package_Version": pkg})
        fv = str(rebuild_count)
        for row in active:
            if texts[row["name"]]:
                _chunk_allotment(context_dir, row["rank"], row["name"], texts[row["name"]], fv, pkg)
        _chunk_bubble(context_dir, fv, pkg)
        since = 0
    else:
        since += 1
        dirty = [
            r for r in active
            if r["refresh"] == REFRESH_TURN
            and state.get("volatile", {}).get(r["name"]) != volatile[r["name"]]
        ]
        if dirty:
            pkg = core_chunk_bump_package_version({"Package_Version": pkg})
            fv = str(rebuild_count)
            for row in dirty:
                if texts[row["name"]]:
                    _chunk_allotment(context_dir, row["rank"], row["name"], texts[row["name"]], fv, pkg)
                else:
                    _remove_allotment_chunk(context_dir, row["name"])
            _chunk_bubble(context_dir, fv, pkg)

    chunk_texts = _read_bubble(context_dir)
    for row in active:
        want = texts[row["name"]]
        if want and chunk_texts.get(row["name"]) != want:
            raise BubbleIntegrityError(f"allotment '{row['name']}' missing or stale in bubble chunk")
    rendered = _render(active, chunk_texts, constants, turn, cfg.get("normalize", True))

    _save_state(context_dir, {
        "turn": turn,
        "turns_since_rebuild": since,
        "rebuild_count": rebuild_count,
        "package_version": pkg,
        "stable": stable,
        "volatile": volatile,
        "config_sig": cfg_sig,
    })
    rendered.update({
        "rebuilt": rebuilt,
        "reason": reason,
        "turn": turn,
        "turns_since_rebuild": since,
        "rebuild_count": rebuild_count,
        "rebuild_interval": interval,
        "turns_until_rebuild": max(0, interval - 1 - since),
        "chunk_path": str(paths["chunk"]),
    })
    return rendered


def _group_map() -> Dict[str, str]:
    with _LOCK:
        regs = dict(_registry)
    tokens: Dict[str, int] = {}
    for name in regs:
        tok = name.split("_")[0]
        tokens[tok] = tokens.get(tok, 0) + 1
    out: Dict[str, str] = {}
    for name, reg in regs.items():
        tok = name.split("_")[0]
        out[name] = reg.group or (tok if tokens[tok] >= 2 else "")
    return out


def _catalog(cfg: Dict[str, Any], skip: Tuple[str, ...] = ()) -> List[Dict[str, Any]]:
    groups = _group_map()
    with _LOCK:
        available = set(_registry)
    return [
        {
            "name": r["name"],
            "label": r["label"],
            "rank": r["rank"],
            "pct": r["pct"],
            "enabled": r["enabled"],
            "available": r["name"] in available,
            "group": groups.get(r["name"], ""),
            "refresh": r["refresh"],
            "keep": r["keep"],
            "skipped": r["name"] in skip,
        }
        for r in cfg["rows"]
    ]


def ai_bubble_config_update(
    config_dir: Path | str,
    changes: Optional[Dict[str, Dict[str, Any]]] = None,
    normalize: Optional[bool] = None,
    rebuild_interval: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Validated, atomic edit of context_bubble.105a.bejson via Core's write_cell.
      changes: {allotment_name: {"enabled": bool, "pct": number}}
      normalize: optional new value for Normalize_Baselines
      rebuild_interval: optional new value for Rebuild_Interval_Turns
    """
    config_dir = Path(config_dir)
    with _LOCK:
        path = ai_bubble_config_init(config_dir)
        try:
            doc = core_load(path)
        except AIException as exc:
            raise ValueError(f"context_bubble.105a.bejson is unreadable: {exc}") from exc

        rows = core_rows_as_dicts(doc)
        uuid_by_name = {_clean_str(r.get("name")): r["record_uuid"] for r in rows if r.get("record_uuid")}
        staged: List[Tuple[str, str, Any]] = []
        for name, ch in (changes or {}).items():
            if name not in uuid_by_name:
                raise ValueError(f"unknown allotment: {name!r}")
            if not isinstance(ch, dict):
                raise ValueError(f"changes for {name!r} must be an object")
            rec_uuid = uuid_by_name[name]
            if "enabled" in ch:
                if not isinstance(ch["enabled"], bool):
                    raise ValueError(f"'enabled' for {name!r} must be true or false")
                staged.append((rec_uuid, "enabled", ch["enabled"]))
            if "pct" in ch:
                v = ch["pct"]
                if (
                    isinstance(v, bool)
                    or not isinstance(v, (int, float))
                    or not math.isfinite(v)
                    or not 0 <= v <= 100
                ):
                    raise ValueError(f"'pct' for {name!r} must be a number from 0 to 100")
                staged.append((rec_uuid, "pct", float(v)))
        if normalize is not None and not isinstance(normalize, bool):
            raise ValueError("'normalize' must be true or false")
        if rebuild_interval is not None:
            if isinstance(rebuild_interval, bool) or not isinstance(rebuild_interval, int) or rebuild_interval < 1:
                raise ValueError("'rebuild_interval' must be a positive integer")
        for rec_uuid, field_name, value in staged:
            core_write_cell(doc, rec_uuid, field_name, value)
        if normalize is not None:
            doc["Normalize_Baselines"] = normalize
        if rebuild_interval is not None:
            doc["Rebuild_Interval_Turns"] = int(rebuild_interval)
        if staged or normalize is not None or rebuild_interval is not None:
            core_save(path, doc)
        return ai_bubble_config_load(config_dir)


def ai_bubble_preview(
    context_dir: Path | str,
    config_dir: Path | str,
    user_msg: str = "",
    extras: Optional[Dict[str, Any]] = None,
    skip: Tuple[str, ...] = (),
    interval_override: Optional[int] = None,
) -> Dict[str, Any]:
    """Builds the bubble the way the next prompt would see it, in a throw-away
    temp directory. Touches no live bubble, no counter, no state."""
    context_dir, config_dir = Path(context_dir), Path(config_dir)
    extras = extras or {}
    with _LOCK:
        constants = _constants(config_dir, extras.get("constants"))
        cfg = ai_bubble_config_load(config_dir, interval_override=interval_override)
        active = _select_active(cfg, tuple(skip))
        live = _load_state(context_dir)
        turn = int(live.get("turn", 0)) + 1
        ctx = BubbleContext(
            user_msg=user_msg,
            turn=turn,
            constants=constants,
            context_dir=context_dir,
            config_dir=config_dir,
            budget_chars=constants["max_context_tokens"] * constants["chars_per_token"],
            extras=extras,
        )
        texts = _run_builders(active, ctx)
        with tempfile.TemporaryDirectory(prefix="bubble_preview_") as tmp:
            tmp_root = Path(tmp)
            for row in active:
                if texts[row["name"]]:
                    _chunk_allotment(tmp_root, row["rank"], row["name"], texts[row["name"]], "preview", "1")
            _chunk_bubble(tmp_root, "preview", "1")
            rendered = _render(
                active,
                _read_bubble(tmp_root),
                constants,
                turn,
                cfg.get("normalize", True),
                include_text=True,
            )
        since = int(live.get("turns_since_rebuild", 0))
        rendered.update({
            "rebuilt": False,
            "reason": "preview",
            "turn": int(live.get("turn", 0)),
            "next_turn": turn,
            "turns_since_rebuild": since,
            "rebuild_count": int(live.get("rebuild_count", 0)),
            "catalog": _catalog(cfg, tuple(skip)),
            "rebuild_interval": cfg["interval"],
            "turns_until_rebuild": max(0, cfg["interval"] - 1 - since) if live else 0,
            "chunk_path": "",
        })
        return rendered


def ai_bubble_get_state(context_dir: Path | str, config_dir: Path | str, interval_override: Optional[int] = None) -> Dict[str, Any]:
    """Return lightweight current bubble turn state without running builders."""
    context_dir, config_dir = Path(context_dir), Path(config_dir)
    with _LOCK:
        cfg = ai_bubble_config_load(config_dir, interval_override=interval_override)
        live = _load_state(context_dir)
        interval = cfg["interval"]
        since = int(live.get("turns_since_rebuild", 0))
        turn = int(live.get("turn", 0))
        return {
            "turn": turn,
            "turns_since_rebuild": since,
            "rebuild_count": int(live.get("rebuild_count", 0)),
            "rebuild_interval": interval,
            "turns_until_rebuild": max(0, interval - 1 - since) if live else 0,
            "normalize": cfg.get("normalize", True),
            "catalog": _catalog(cfg),
        }


def ai_bubble_init(
    context_dir: Path | str,
    config_dir: Path | str,
    policy_text: Optional[str] = None,
    default_interval: Optional[int] = None,
) -> Dict[str, str]:
    """Creates the directories, context_bubble.105a.bejson (for registered allotments),
    and a default Persistent_Policy.md (only if absent). Returns the path dict."""
    context_dir, config_dir = Path(context_dir), Path(config_dir)
    context_dir.mkdir(parents=True, exist_ok=True)
    config_dir.mkdir(parents=True, exist_ok=True)
    ai_bubble_config_init(config_dir, default_interval=default_interval)
    p = _paths(context_dir)
    if policy_text and not p["policy"].exists():
        core_write_text_file(p["policy"], policy_text)
    return {k: str(v) for k, v in p.items()} | {"config": str(_config_path(config_dir))}


def ai_bubble_minimal(context_dir: Path | str) -> Dict[str, Any]:
    """Degraded-mode fallback: Persistent Policy only."""
    policy_path = _paths(Path(context_dir))["policy"]
    try:
        policy_text = policy_path.read_text("utf-8", errors="replace")[:4000]
    except OSError:
        policy_text = ""
    text = f"{_WRAP_OPEN}## Persistent Policy\n{policy_text}{_WRAP_CLOSE}" if policy_text else ""
    return {"text": text, "allotments": [], "rebuilt": False, "reason": "degraded"}


# ── Compression / amnesia helpers ─────────────────────────────────────────────

_observer_compressor: Optional[Callable[[str], Optional[str]]] = None


def ai_bubble_set_compressor(fn: Callable[[str], Optional[str]]) -> None:
    global _observer_compressor
    _observer_compressor = fn


def ai_bubble_compress_history(
    history: List[Dict[str, Any]],
    compressor_fn: Callable[[str], Optional[str]],
) -> Optional[str]:
    if not history:
        return None
    transcript = "\n\n".join(f"[{t.get('role', '?')}]: {t.get('content', '')}" for t in history)
    if not transcript.strip():
        return None
    try:
        result = compressor_fn(transcript)
        if result and result.strip():
            return result.strip()
    except Exception as exc:
        logger.warning("[AIContextBubble] History compression failed: %s", exc)
    return None


def ai_bubble_save_amnesia_recap(context_dir: Path | str, recap: str) -> None:
    context_dir = Path(context_dir)
    context_dir.mkdir(parents=True, exist_ok=True)
    core_write_text_file(context_dir / _AMNESIA_FILENAME, recap)


def ai_bubble_load_amnesia_recap(context_dir: Path | str) -> Optional[str]:
    target = Path(context_dir) / _AMNESIA_FILENAME
    if not target.is_file():
        return None
    text = target.read_text(encoding="utf-8").strip()
    return text or None


def ai_bubble_rebirth(history: List[Dict[str, Any]], recap: str) -> None:
    history.clear()
    history.append({"role": "user", "content": f"[Rebirth -- compressed session recap]\n{recap}"})


# ── Tier 2 Modular Pre-Parser Integration ─────────────────────────────────────

class ContextBubblePreParser(BaseModularParser):
    """
    Tier 2 Modular Pre-Parser wrapping the BEJSON 105 Context Bubble engine.
    Can be registered directly in `AIDispatcher.parser_registry` or invoked
    by `AIPreprocessor`.
    """

    parser_name: str = "context_bubble_pre_parser"

    def __init__(
        self,
        context_dir: Optional[Path | str] = None,
        config_dir: Optional[Path | str] = None,
        rebuild_interval_override: Optional[int] = None,
        skip_allotments: Tuple[str, ...] = (),
    ) -> None:
        self.context_dir = Path(context_dir) if context_dir else None
        self.config_dir = Path(config_dir) if config_dir else None
        self.rebuild_interval_override = rebuild_interval_override
        self.skip_allotments = tuple(skip_allotments)

    def parse_pre(self, incoming_request_payload_dict: Dict[str, Any]) -> Dict[str, Any]:
        out = dict(incoming_request_payload_dict)
        ctx_dir = out.get("bubble_context_dir") or self.context_dir
        cfg_dir = out.get("bubble_config_dir") or self.config_dir
        if not ctx_dir or not cfg_dir:
            return out

        user_prompt = str(out.get("prompt", "") or "")
        extras = dict(out.get("bubble_extras") or {})
        if "url_context" in out and "url_context" not in extras:
            extras["url_context"] = out["url_context"]
        if "attached_file_ids" in out and "attached_file_ids" not in extras:
            extras["attached_file_ids"] = out["attached_file_ids"]
        if "history" in out and "history" not in extras:
            extras["history"] = out["history"]
        if "profile_instruction" in out and "profile_instruction" not in extras:
            extras["profile_instruction"] = out["profile_instruction"]

        skip = tuple(out.get("bubble_skip") or self.skip_allotments)
        interval_override = out.get("bubble_interval_override") or self.rebuild_interval_override

        bubble_result = ai_bubble_prepare(
            context_dir=Path(ctx_dir),
            config_dir=Path(cfg_dir),
            user_msg=user_prompt,
            extras=extras,
            skip=skip,
            interval_override=interval_override,
        )
        bubble_text = str(bubble_result.get("text") or "").strip()
        if bubble_text:
            existing_sys = str(out.get("system_instruction") or "").strip()
            out["system_instruction"] = (
                f"{existing_sys}\n\n{bubble_text}".strip() if existing_sys else bubble_text
            )
        out["_context_bubble"] = bubble_result
        return out

    def parse_post(self, incoming_response_envelope_dict: Dict[str, Any]) -> Dict[str, Any]:
        return incoming_response_envelope_dict
