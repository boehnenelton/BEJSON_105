"""
Library:         lib_bejson_AI_Core_validator.py
Family:          AI_Core
Module Purpose:  Family validator for AI_Core (and, with family="AI_Extensions", the extensions family).
                 Static checks (nothing is imported or executed): naming, header, VERSION sync, unique
                 RELATIONAL_ID, no print(), no literal absolute paths, no API key in URLs, stdlib-only
                 imports, Core touched only through the bridge, BEJSON written only through the bridge,
                 logger present where errors are handled, Python 3.10 syntax. Plus a SHA-256 freeze
                 manifest (105a) to pin AI_Core as immutable once Elton declares it complete.
Changelog:
  2.1.0 (2026-11-17) -- allow pragma; _family_files now returns every .py (a file not named lib_bejson_* used to
          be skipped silently instead of reported as a naming violation -- found by test_ai_core_plugins_validator_bridge).
Pragma:          A line (or the line above it) containing "# ai-core: allow <rule> -- <reason>" suppresses that one
                 rule for that line. A reason is mandatory; a bare pragma is ignored.
Architecture:    CLI: --family-dir DIR [--family AI_Core|AI_Extensions] [--write-freeze FILE | --verify-freeze FILE]
Version:         2.1.0
Release_Version: 300
Date:            2026-11-17
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Format_Creator:  Elton Boehnen
RELATIONAL_ID:   331a3a8e-70d0-464a-9d5d-dfa6d749fb84
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import logging
import re
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence

_SELF_DIR = Path(__file__).resolve().parent
if str(_SELF_DIR) not in sys.path:
    sys.path.insert(0, str(_SELF_DIR))

from lib_bejson_AI_Core_core_bridge import core_add_record, core_load, core_new_document, core_rows_as_dicts, core_save
from lib_bejson_AI_Core_errors import (
    AIException,
    ERR_AI_FAMILY_VALIDATION_FAILED,
    ERR_AI_FREEZE_MANIFEST_MISMATCH,
)

VERSION = "2.1.0"
_LOGGER = logging.getLogger("lib_bejson_AI_Core_validator")

BRIDGE_MODULE = "lib_bejson_AI_Core_core_bridge"
FREEZE_RECORDS_TYPE = "AICoreFreezeManifest"
_ABS_PATH_RE = re.compile(r"^(/storage/|/sdcard/|/data/data/|/home/|/mnt/|/Users/|[A-Za-z]:\\)")
_UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
_RAW_WRITE_ATTRS = {"write_text", "write_bytes"}
_RAW_JSON_FILE_ATTRS = {"load", "dump"}
_PRAGMA_RE = re.compile(r"#\s*ai-core:\s*allow\s+([a-z-]+)\s+--\s+\S")


@dataclass(frozen=True)
class Violation:
    rule: str
    file: str
    line: int
    message: str

    def __str__(self) -> str:
        return f"{self.file}:{self.line} [{self.rule}] {self.message}"


@dataclass
class ValidationReport:
    family: str
    files_checked: int = 0
    violations: List[Violation] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.violations

    def as_text(self) -> str:
        head = f"{self.family}: {self.files_checked} files, {len(self.violations)} violation(s)"
        return "\n".join([head] + [f"  {v}" for v in self.violations])


def _family_files(directory: Path, family: str) -> List[Path]:
    pattern = "**/*.py" if family != "AI_Core" else "*.py"
    files = [p for p in sorted(directory.glob(pattern))
             if "__pycache__" not in p.parts and "tests" not in p.relative_to(directory).parts]
    return files  # every module is checked; a stray helper.py is a naming violation, not an exemption


def _header(docstring: Optional[str]) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for line in (docstring or "").splitlines():
        match = re.match(r"^([A-Za-z_][A-Za-z_ ]*?):\s+(\S.*)$", line)
        if match and match.group(1) not in result:
            result[match.group(1)] = match.group(2).strip()
    return result


def _is_docstring(node: ast.AST, parents: Dict[ast.AST, ast.AST]) -> bool:
    parent = parents.get(node)
    grand = parents.get(parent) if parent is not None else None
    return isinstance(parent, ast.Expr) and isinstance(grand, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))


def _check_file(path: Path, family: str, allowed_internal: Sequence[str], relational_ids: Dict[str, str]) -> List[Violation]:
    out: List[Violation] = []
    name = path.name
    rel = name

    source = path.read_text(encoding="utf-8")
    source_lines = source.splitlines()

    def _allowed(rule: str, line: int) -> bool:
        for number in (line, line - 1):
            if 1 <= number <= len(source_lines):
                match = _PRAGMA_RE.search(source_lines[number - 1])
                if match and match.group(1) == rule:
                    return True
        return False

    def bad(rule: str, line: int, message: str) -> None:
        if not _allowed(rule, line):
            out.append(Violation(rule, rel, line, message))

    try:
        tree = ast.parse(source, filename=name, feature_version=(3, 10))
    except SyntaxError as exc:
        bad("syntax", exc.lineno or 0, f"not valid Python 3.10: {exc.msg}")
        return out

    is_init = name == "__init__.py"
    prefix = f"lib_bejson_{family}_"
    if not is_init and not (name.startswith(prefix) and name.endswith(".py")):
        bad("naming", 1, f"file must be named {prefix}<module>.py")
    if name.startswith("lib_bejson_ai_") or name.startswith("lib_bejson_AI_bejson_"):
        bad("naming", 1, "legacy AI family file name; rename into AI_Core / AI_Extensions naming")

    header = _header(ast.get_docstring(tree, clean=False))
    if not is_init and header.get("Library") != name:
        bad("header", 1, f"header Library must equal file name, is {header.get('Library')!r}")
    if header.get("Family") != family:
        bad("header", 1, f"header Family must be {family}, is {header.get('Family')!r}")
    for key in ("Version", "Author", "RELATIONAL_ID", "Date"):
        if key not in header:
            bad("header", 1, f"header missing {key}")
    rid = header.get("RELATIONAL_ID", "")
    if rid:
        if not _UUID_RE.match(rid):
            bad("header", 1, f"RELATIONAL_ID is not a UUID: {rid!r}")
        elif rid in relational_ids:
            bad("relational-id", 1, f"RELATIONAL_ID duplicates {relational_ids[rid]}")
        else:
            relational_ids[rid] = name

    module_version = None
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(isinstance(t, ast.Name) and t.id == "VERSION" for t in targets) and isinstance(node.value, ast.Constant):
                module_version = str(node.value.value)
    if not is_init and module_version is None:
        bad("version", 1, "module-level VERSION constant missing")
    elif module_version is not None and header.get("Version") and module_version != header["Version"]:
        bad("version", 1, f"VERSION {module_version} != header Version {header['Version']}")

    parents = {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}
    stdlib = sys.stdlib_module_names
    has_logger = False
    has_except = False
    uses_urllib = False
    is_bridge = name == f"{BRIDGE_MODULE}.py"

    for node in ast.walk(tree):
        line = getattr(node, "lineno", 0)
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id == "print":
                bad("no-print", line, "print() is forbidden; use logging")
            if isinstance(func, ast.Attribute):
                if func.attr == "getLogger":
                    has_logger = True
                if not is_bridge:
                    if func.attr in _RAW_WRITE_ATTRS:
                        bad("core-io", line, f".{func.attr}() writes a file directly; BEJSON writes go through the Core bridge")
                    if func.attr in _RAW_JSON_FILE_ATTRS and isinstance(func.value, ast.Name) and func.value.id == "json":
                        bad("core-io", line, f"json.{func.attr}() on a file; BEJSON I/O goes through the Core bridge")
            if isinstance(func, ast.Name) and func.id == "open" and not is_bridge:
                mode = node.args[1] if len(node.args) > 1 else next((k.value for k in node.keywords if k.arg == "mode"), None)
                if isinstance(mode, ast.Constant) and isinstance(mode.value, str) and set("wax+") & set(mode.value):
                    bad("core-io", line, "open() for writing; BEJSON writes go through the Core bridge")
        elif isinstance(node, ast.ExceptHandler):
            has_except = True
        elif isinstance(node, ast.Constant) and isinstance(node.value, str) and not _is_docstring(node, parents):
            text = node.value
            if _ABS_PATH_RE.match(text):
                bad("abs-path", line, f"literal absolute path {text[:60]!r}")
            if re.search(r"[?&]key=", text):
                bad("key-in-url", line, "API key must travel in x-goog-api-key, never in a URL")
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            modules = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""]
            if isinstance(node, ast.ImportFrom) and node.level:
                continue
            for module in modules:
                top = module.split(".")[0]
                if top == "urllib":
                    uses_urllib = True
                if top in stdlib or top == "__future__":
                    continue
                if top.startswith("lib_bejson_Core_"):
                    if not is_bridge:
                        bad("core-bridge", line, f"imports {top}; only {BRIDGE_MODULE} may import Core")
                    continue
                if any(top.startswith(p) for p in allowed_internal):
                    continue
                if top in {"AI_Core", "AI_Extensions"} and is_init:
                    continue
                bad("imports", line, f"non-stdlib import {top!r}")

    if (has_except or uses_urllib) and not has_logger and not is_init:
        bad("logging", 1, "module handles errors or network calls but has no logging.getLogger(...)")
    return out


def validate_family(directory: Path | str | None = None, family: str = "AI_Core") -> ValidationReport:
    """Static validation of a family directory. Never imports or executes the checked code."""
    base = Path(directory) if directory else Path(__file__).resolve().parent
    if family not in ("AI_Core", "AI_Extensions"):
        raise ValueError(f"unsupported family {family!r}")
    allowed = ("lib_bejson_AI_Core_",) if family == "AI_Core" else ("lib_bejson_AI_Core_", "lib_bejson_AI_Extensions_")
    report = ValidationReport(family=family)
    relational_ids: Dict[str, str] = {}
    for path in _family_files(base, family):
        report.files_checked += 1
        report.violations.extend(_check_file(path, family, allowed, relational_ids))
    if family == "AI_Core" and not (base / f"{BRIDGE_MODULE}.py").is_file():
        report.violations.append(Violation("core-bridge", BRIDGE_MODULE + ".py", 0, "Core bridge module missing"))
    return report


def validate_or_raise(directory: Path | str | None = None, family: str = "AI_Core") -> ValidationReport:
    report = validate_family(directory, family)
    if not report.ok:
        raise AIException(ERR_AI_FAMILY_VALIDATION_FAILED, report.as_text())
    return report


# -- freeze manifest ----------------------------------------------------------

def _frozen_files(directory: Path) -> List[Path]:
    return [p for p in sorted(directory.glob("*.py")) if p.name.startswith("lib_bejson_AI_Core_") or p.name == "__init__.py"]


def freeze_manifest_build(directory: Path | str | None = None) -> Dict[str, object]:
    """105a manifest of SHA-256 digests for every AI_Core module (tests, docs and config are not pinned)."""
    base = Path(directory) if directory else Path(__file__).resolve().parent
    doc = core_new_document("105a", FREEZE_RECORDS_TYPE,
                            [("file", "string"), ("sha256", "string"), ("bytes", "integer")],
                            Freeze_Id=str(uuid.uuid4()))
    for path in _frozen_files(base):
        data = path.read_bytes()
        core_add_record(doc, {"file": path.name, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)})
    return doc


def freeze_manifest_write(manifest_path: Path | str, directory: Path | str | None = None) -> None:
    core_save(manifest_path, freeze_manifest_build(directory))


def freeze_manifest_verify(manifest_path: Path | str, directory: Path | str | None = None) -> List[str]:
    """Differences between the pinned manifest and the files on disk ([] = identical)."""
    base = Path(directory) if directory else Path(__file__).resolve().parent
    pinned = {row["file"]: row["sha256"] for row in core_rows_as_dicts(core_load(manifest_path))}
    actual = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in _frozen_files(base)}
    problems = [f"changed: {n}" for n in sorted(pinned) if n in actual and actual[n] != pinned[n]]
    problems += [f"missing: {n}" for n in sorted(set(pinned) - set(actual))]
    problems += [f"unpinned: {n}" for n in sorted(set(actual) - set(pinned))]
    return problems


def freeze_manifest_verify_or_raise(manifest_path: Path | str, directory: Path | str | None = None) -> None:
    problems = freeze_manifest_verify(manifest_path, directory)
    if problems:
        raise AIException(ERR_AI_FREEZE_MANIFEST_MISMATCH, "; ".join(problems))


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Validate an AI_Core / AI_Extensions family directory.")
    parser.add_argument("--family-dir", default=None, help="defaults to this module's own directory")
    parser.add_argument("--family", default="AI_Core", choices=["AI_Core", "AI_Extensions"])
    parser.add_argument("--write-freeze", default=None, help="write a SHA-256 freeze manifest to this file")
    parser.add_argument("--verify-freeze", default=None, help="verify files against this freeze manifest")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    report = validate_family(args.family_dir, args.family)
    _LOGGER.info(report.as_text())
    status = 0 if report.ok else 1
    if args.write_freeze:
        freeze_manifest_write(args.write_freeze, args.family_dir)
        _LOGGER.info("freeze manifest written: %s", args.write_freeze)
    if args.verify_freeze:
        problems = freeze_manifest_verify(args.verify_freeze, args.family_dir)
        for problem in problems:
            _LOGGER.info("freeze: %s", problem)
        status = status or (1 if problems else 0)
    return status


if __name__ == "__main__":
    sys.exit(main())
