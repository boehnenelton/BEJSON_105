"""
Library:        lib_bejson_Core_bejson_env.py
Family:         Core
Description:    Environment and path resolution utility for the BEJSON ecosystem.
Version:        2.1.4
Date:           2026-10-09
Author:         Elton Boehnen
Contact:        eltonboehnen@gmail.com | boehnenelton2024.pages.dev | github.com/boehnenelton
Format_Creator: Elton Boehnen
RELATIONAL_ID:  2ca57c10-8b9e-4147-95fd-07e8158a95d6
Release_Version: 300

Changelog:
  2.1.4 - Adversarial-review remediation: source_env no longer exec()s the
          file; safe ast/literal_eval parser (UPPER_SNAKE names, scalar values,
          whole-file refusal on any violation).
  2.1.3 - Consolidation re-merge: the V6-PKG101 silent-exception logging fix
          (source_env search-path loop) had been reverted/lost on the
          forward V10-PKG102 branch, including the `import logging` line;
          re-applied here, no behavior change.
"""

import ast
import json
import logging
import os
import re
import sys
import threading
from pathlib import Path

logger = logging.getLogger("lib_bejson_Core_bejson_env")
VERSION = "2.3.1"

_ENV_NAME_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")

def _parse_env_file(path: Path) -> dict:
    """
    Parse an environment file as DATA ONLY -- nothing in it is ever executed.

    Accepted shapes:
      * *.json            : a flat JSON object {"NAME": value, ...}
      * anything else     : Python-style `NAME = <literal>` lines (the legacy
                            env_file.py layout). Parsed with ast and evaluated
                            with ast.literal_eval, so calls, imports,
                            comprehensions, attribute access and every other
                            non-literal construct are rejected outright.
    Names must be UPPER_SNAKE_CASE (this also makes it impossible for a file to
    shadow a function defined in this module). Values must be str/int/float/bool.
    Raises ValueError on anything else -- the whole file is refused, never
    partially applied.
    """
    text = path.read_text(encoding="utf-8")
    pairs = {}
    if path.suffix.lower() == ".json":
        raw = json.loads(text)
        if not isinstance(raw, dict):
            raise ValueError("env JSON must be a JSON object")
        if "Values" in raw and "Format" in raw and isinstance(raw.get("Values"), list):
            for row in raw["Values"]:
                if isinstance(row, list) and len(row) >= 2 and row[0] and row[1] is not None:
                    pairs[str(row[0]).strip()] = str(row[1]).strip()
        else:
            pairs = raw
    else:
        for node in ast.parse(text, filename=str(path)).body:
            if (isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant)
                    and isinstance(node.value.value, str)):
                continue  # module docstring / bare string comment
            if (not isinstance(node, ast.Assign) or len(node.targets) != 1
                    or not isinstance(node.targets[0], ast.Name)):
                raise ValueError(f"line {getattr(node, 'lineno', '?')}: only NAME = <literal> is allowed")
            pairs[node.targets[0].id] = ast.literal_eval(node.value)
    for name, value in pairs.items():
        if not isinstance(name, str) or not _ENV_NAME_RE.match(name):
            raise ValueError(f"illegal variable name {name!r} (must be UPPER_SNAKE_CASE)")
        if not isinstance(value, (str, int, float, bool)):
            raise ValueError(f"{name}: value must be str/int/float/bool, got {type(value).__name__}")
    return pairs

def source_env(override_path: str = None) -> bool:
    """
    Mandatory Environment Sourcing (Section 54).
    Priority: 1. override_path, 2. ENV_FILE_PATH, 3. Android Storage, 4. Home

    SECURITY: the env file is treated as untrusted data (it commonly lives on
    shared storage). It is parsed, never executed -- see _parse_env_file().
    A file that fails parsing is logged and skipped; the next candidate is tried.
    """
    env_path = override_path or os.environ.get("ENV_FILE_PATH")
    search_paths = [
        Path(env_path) if env_path else None,
        Path("/storage/emulated/0/env_file.py"),
        Path.home() / "env_file.py"
    ]
    for p in search_paths:
        if p and p.exists():
            try:
                globals().update(_parse_env_file(p))
                return True
            except Exception as exc:
                logging.warning("[BEJSON_ENV] Refusing env file %s: %s", p, exc)
                continue
    return False

def resolve_path(path_str: str) -> str:
    """
    Resolves system placeholders and absolute paths to environment-relative paths.
    Prioritizes environment variables (ADMIN_ROOT, BEJSON_LIB_ROOT, etc).
    """
    if not path_str:
        return path_str
    
    # Define standard roots with defaults
    home = os.environ.get("HOME", os.path.expanduser("~"))
    
    # Storage and Admin Roots
    # Fallback to HOME if storage root is unset to avoid hardcodes.
    storage_root = os.environ.get("BEJSON_STORAGE_ROOT", home)
    admin_root   = os.environ.get("ADMIN_ROOT", os.path.join(storage_root, "Admin"))
    
    # Library Root Resolution (Admin/libraries fallback to ~/libraries)
    lib_root = os.environ.get("BEJSON_LIB_ROOT")
    if not lib_root:
        candidate_admin = os.path.join(admin_root, "libraries")
        candidate_home  = os.path.join(home, "libraries")
        lib_root = candidate_admin if os.path.exists(candidate_admin) else candidate_home
    
    mappings = {
        "{BEJSON_LIB_ROOT}": lib_root,
        "{ADMIN_ROOT}": admin_root,
        "{INTERNAL_STORAGE}": storage_root,
        "{HOME}": home
    }
    
    # Legacy absolute paths to be replaced
    # Only replace if storage_root is explicitly set to avoid "Vanishing Data".
    if os.environ.get("BEJSON_STORAGE_ROOT"):
        mappings["/storage/emulated/0"] = storage_root
        mappings["/data/data/com.termux/files/home"] = home
    
    resolved = str(path_str)
    
    # Sort keys by length descending to avoid partial matches (e.g. {HOME}_STUFF)
    for placeholder in sorted(mappings.keys(), key=len, reverse=True):
        actual = mappings[placeholder]
        if actual:
            resolved = resolved.replace(placeholder, actual)
    
    # Handle home expansion
    resolved = os.path.expanduser(resolved)
    # Handle environment variables in path (e.g. $VAR)
    resolved = os.path.expandvars(resolved)
    
    return os.path.normpath(resolved)

def get_env_path(env_var: str, default: str) -> str:
    """Retrieves an environment variable and resolves it as a path."""
    val = os.getenv(env_var, default)
    return resolve_path(val)


# --- source_env_fill (2.3.0, additive) --------------------------------------
_FILL_LOCK = threading.Lock()
_FILL_REPORTS: dict = {}
_FILL_MAX_BYTES = 2 * 1024 * 1024


def _fill_pairs(p: Path) -> dict:
    """{NAME: value} from one env file. .json = BEJSON 104a Values rows [name, value]
    (same reading as _load_env_file); a plain JSON object is flattened one level;
    anything else is KEY=VALUE lines. Never exec()s. {} on any failure."""
    import json
    out: dict = {}
    try:
        if not p.is_file() or p.stat().st_size > _FILL_MAX_BYTES:
            return out
        text = p.read_text(encoding="utf-8")
        if p.suffix == ".json":
            data = json.loads(text)
            if isinstance(data, dict) and "Values" in data:
                for row in data.get("Values", []):
                    if isinstance(row, list) and len(row) >= 2:
                        k, v = str(row[0]).strip(), str(row[1]).strip()
                        if k and v and row[1] is not None:
                            out[k] = v
            elif isinstance(data, dict):
                for k, v in data.items():
                    if isinstance(v, (str, int, float)) and not isinstance(v, bool) and str(v).strip():
                        out[str(k).strip()] = str(v).strip()
        elif p.suffix != ".py":
            for line in text.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.lower().startswith("export "):
                    line = line[7:].strip()
                if "=" in line:
                    k, v = line.split("=", 1)
                    if k.strip() and v.strip().strip("\"'"):
                        out[k.strip()] = v.strip().strip("\"'")
    except Exception as e:
        logger.warning("source_env_fill: could not read %s: %s", p.name, type(e).__name__)
        return {}
    return {k: v for k, v in out.items() if k.replace("_", "a").isalnum() and not k[0].isdigit()}


# Loads the secure store into os.environ WITHOUT overwriting anything already set. Safe to call repeatedly (cached per key).
def source_env_fill(include_paths: bool = False, force: bool = False) -> dict:
    """
    Non-overwriting companion to source_env(). Real environment variables always win
    (secure-credentials-first ordering); the store only fills gaps. Cached per process,
    so library key registries can call it on every load() for free.

    Secure store candidates: $SECUREENV_FILE, then the same standard locations source_env()
    uses (.json first, plus ~/.env/secure/secureenv_file.json). .py files are NOT exec()'d here.
    include_paths=True also fills from the user paths store ($BEJSON_PATHS_FILE or the standard
    paths.json); default False because paths change how resolve_path() behaves.

    Returns a report of NAMES and counts only: {found, files, loaded, kept_existing, names}.
    Values are never logged or returned.
    """
    cache_key = bool(include_paths)
    with _FILL_LOCK:
        if cache_key in _FILL_REPORTS and not force:
            return dict(_FILL_REPORTS[cache_key])

    secure = [os.environ.get("SECUREENV_FILE"),
              "/storage/emulated/0/.env/secure/secureenv_file.json",
              os.path.join(os.path.expanduser("~"), ".env", "secure", "secureenv_file.json")]
    paths = [os.environ.get("BEJSON_PATHS_FILE"),
             "/storage/emulated/0/.env/user/paths.json",
             os.path.join(os.path.expanduser("~"), ".env", "user", "paths.json")]
    tiers = [secure] + ([paths] if include_paths else [])

    report = {"found": False, "files": [], "loaded": 0, "kept_existing": 0, "names": []}
    names = set()
    for tier in tiers:
        for cand in tier:
            if not cand:
                continue
            p = Path(os.path.expanduser(str(cand)))
            if not p.is_file():
                continue
            pairs = _fill_pairs(p)
            report["found"] = True
            report["files"].append(p.name)
            for k, v in pairs.items():
                if os.environ.get(k, "").strip():
                    report["kept_existing"] += 1
                else:
                    os.environ[k] = v
                    report["loaded"] += 1
                names.add(k)
            break  # first existing candidate per tier wins
    report["names"] = sorted(names)
    logger.info("source_env_fill: found=%s loaded=%d kept_existing=%d",
                report["found"], report["loaded"], report["kept_existing"])
    with _FILL_LOCK:
        _FILL_REPORTS[cache_key] = report
    return dict(report)
