"""
Library:         lib_bejson_AI_Extensions_manifest_tool.py
Family:          AI_Extensions
Module Purpose:  Writes/refreshes a plugin's extension.105a.bejson (with the module SHA-256 pin) through
                 AI_Core's schema + Core write. CLI: --plugin-dir DIR --id ID --name NAME --version V
                 --stage pre|post|render --module FILE --entry CLASS [--priority N] [--description T].
Version:         1.0.0
Release_Version: 300
Date:            2026-11-17
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Format_Creator:  Elton Boehnen
RELATIONAL_ID:   4f8e1b27-d903-4a56-8c7e-5b2a9d0e6c13
"""
from __future__ import annotations

import argparse
import hashlib
import logging
import sys
from pathlib import Path
from typing import List, Optional

_AI_CORE = Path(__file__).resolve().parent.parent / "AI_Core"
if str(_AI_CORE) not in sys.path:
    sys.path.insert(0, str(_AI_CORE))

from lib_bejson_AI_Core_core_bridge import core_save  # noqa: E402
from lib_bejson_AI_Core_errors import AIException, ERR_AI_PLUGIN_MANIFEST_INVALID  # noqa: E402
from lib_bejson_AI_Core_plugin_schema import (  # noqa: E402
    PLUGIN_MANIFEST_FILENAME,
    plugin_manifest_new,
    plugin_manifest_validate,
)

VERSION = "1.0.0"
_LOGGER = logging.getLogger("lib_bejson_AI_Extensions_manifest_tool")


def write_manifest(plugin_dir: Path, plugin_id: str, plugin_name: str, plugin_version: str, stage: str,
                   module_file: str, entry_class: str, priority: int = 100, description: str = "") -> Path:
    plugin_dir = Path(plugin_dir)
    digest = hashlib.sha256((plugin_dir / module_file).read_bytes()).hexdigest()
    doc = plugin_manifest_new(plugin_id, plugin_name, plugin_version, stage, module_file, entry_class,
                              priority=priority, description=description, module_sha256=digest)
    problems = plugin_manifest_validate(doc)
    if problems:
        raise AIException(ERR_AI_PLUGIN_MANIFEST_INVALID, "; ".join(problems))
    target = plugin_dir / PLUGIN_MANIFEST_FILENAME
    core_save(target, doc)
    return target


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Write an AI plugin manifest.")
    parser.add_argument("--plugin-dir", required=True)
    parser.add_argument("--id", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--stage", required=True, choices=["pre", "post", "render"])
    parser.add_argument("--module", required=True)
    parser.add_argument("--entry", required=True)
    parser.add_argument("--priority", type=int, default=100)
    parser.add_argument("--description", default="")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    path = write_manifest(Path(args.plugin_dir), args.id, args.name, args.version, args.stage,
                          args.module, args.entry, args.priority, args.description)
    _LOGGER.info("wrote %s", path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
