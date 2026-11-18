"""
Library:         test_ai_core_plugins_validator_bridge.py
Family:          AI_Core
Module Purpose:  Tests for the plugin schema/registry (gate, order, pin, trust boundary, failure isolation), the family validator (clean families, rules, allow pragma, freeze manifest) and the Core bridge.
Version:         1.0.0
Release_Version: 300
Date:            2026-11-17
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Format_Creator:  Elton Boehnen
RELATIONAL_ID:   31a44a78-53fc-45b3-8bc9-67ff6910586f
"""
from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

_AI_DIR = Path(__file__).resolve().parent.parent
if str(_AI_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_DIR))

import lib_bejson_AI_Core_core_bridge as bridge  # noqa: E402
import lib_bejson_AI_Core_validator as V  # noqa: E402
from lib_bejson_AI_Core_errors import (  # noqa: E402
    AIException,
    ERR_AI_DOCUMENT_INVALID,
    ERR_AI_FREEZE_MANIFEST_MISMATCH,
    ERR_AI_PLUGIN_DUPLICATE,
    ERR_AI_PLUGIN_NOT_FOUND,
    ERR_AI_PLUGIN_STAGE_INVALID,
    ERR_AI_PLUGIN_UNTRUSTED_DIRECTORY,
)
from lib_bejson_AI_Core_plugin_base import BasePlugin  # noqa: E402
from lib_bejson_AI_Core_plugin_registry import PluginRegistry, default_extensions_directory  # noqa: E402
from lib_bejson_AI_Core_plugin_schema import plugin_manifest_new, plugin_manifest_validate  # noqa: E402
from lib_bejson_AI_Core_tooling_registry import AIGlobalConfigManager  # noqa: E402

_EXT_DIR = _AI_DIR.parent / "AI_Extensions"


class _Tag(BasePlugin):
    stage = "pre"

    def __init__(self, plugin_id: str, tag: str):
        super().__init__()
        self.plugin_id = plugin_id
        self._tag = tag

    def process(self, payload):
        return {**payload, "trail": payload.get("trail", "") + self._tag}


class _Boom(BasePlugin):
    plugin_id = "boom"
    stage = "pre"

    def process(self, payload):
        raise RuntimeError("boom")


def _registry(tmp: str) -> PluginRegistry:
    return PluginRegistry(AIGlobalConfigManager(Path(tmp) / "cfg.105a.bejson"))


class PluginRegistryTests(unittest.TestCase):
    def test_gate_off_by_default_is_noop(self):
        with tempfile.TemporaryDirectory() as tmp:
            reg = _registry(tmp)
            reg.register_plugin(_Tag("t1", "a"))
            self.assertFalse(reg.is_enabled())
            self.assertEqual(reg.run_stage("pre", {"trail": ""}), {"trail": ""})
            reg.set_enabled(True)
            self.assertEqual(reg.run_stage("pre", {"trail": ""}), {"trail": "a"})

    def test_gate_persists_across_managers(self):
        with tempfile.TemporaryDirectory() as tmp:
            _registry(tmp).set_enabled(True)
            self.assertTrue(_registry(tmp).is_enabled())

    def test_priority_then_id_order_and_disable(self):
        with tempfile.TemporaryDirectory() as tmp:
            reg = _registry(tmp)
            reg.set_enabled(True)
            reg.register_plugin(_Tag("bbb", "B"), priority=50)
            reg.register_plugin(_Tag("aaa", "A"), priority=50)
            reg.register_plugin(_Tag("zzz", "Z"), priority=1)
            self.assertEqual(reg.list_plugins("pre"), ["zzz", "aaa", "bbb"])
            reg.set_plugin_enabled("aaa", False)
            self.assertEqual(reg.run_stage("pre", {})["trail"], "ZB")

    def test_failing_plugin_is_isolated(self):
        with tempfile.TemporaryDirectory() as tmp:
            reg = _registry(tmp)
            reg.set_enabled(True)
            reg.register_plugin(_Boom(), priority=1)
            reg.register_plugin(_Tag("ok", "x"), priority=2)
            with self.assertLogs("lib_bejson_AI_Core_plugin_registry", level="WARNING"):
                self.assertEqual(reg.run_stage("pre", {})["trail"], "x")

    def test_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            reg = _registry(tmp)
            reg.register_plugin(_Tag("dup", "a"))
            with self.assertRaises(AIException) as c1:
                reg.register_plugin(_Tag("dup", "b"))
            self.assertEqual(c1.exception.code, ERR_AI_PLUGIN_DUPLICATE)
            with self.assertRaises(AIException) as c2:
                reg.unregister_plugin("nope")
            self.assertEqual(c2.exception.code, ERR_AI_PLUGIN_NOT_FOUND)
            with self.assertRaises(AIException) as c3:
                reg.run_stage("sideways", {})
            self.assertEqual(c3.exception.code, ERR_AI_PLUGIN_STAGE_INVALID)

    def test_discovers_shipped_extensions(self):
        with tempfile.TemporaryDirectory() as tmp:
            reg = _registry(tmp)
            self.assertEqual(default_extensions_directory(), _EXT_DIR.resolve())
            found = reg.discover_plugins()
            self.assertEqual(sorted(found), ["post_think_stripper", "pre_whitespace_normalizer", "render_plain_text"])
            reg.set_enabled(True)
            self.assertEqual(reg.run_stage("post", {"text": "<think>x</think>\nhi"})["text"], "hi")

    def test_untrusted_directory_refused_and_tampered_module_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            copy_dir = Path(tmp) / "ext"
            shutil.copytree(_EXT_DIR / "pre_whitespace_normalizer", copy_dir / "pre_whitespace_normalizer")
            reg = _registry(tmp)
            with self.assertRaises(AIException) as ctx:
                reg.discover_plugins(copy_dir)
            self.assertEqual(ctx.exception.code, ERR_AI_PLUGIN_UNTRUSTED_DIRECTORY)
            self.assertEqual(reg.discover_plugins(copy_dir, allow_external_directory=True), ["pre_whitespace_normalizer"])
            module = next((copy_dir / "pre_whitespace_normalizer").glob("*.py"))
            module.write_text(module.read_text(encoding="utf-8") + "\n# tampered\n", encoding="utf-8")
            reg2 = _registry(tmp)
            with self.assertLogs("lib_bejson_AI_Core_plugin_registry", level="WARNING"):
                self.assertEqual(reg2.discover_plugins(copy_dir, allow_external_directory=True), [])


class ManifestSchemaTests(unittest.TestCase):
    def _new(self, **kw):
        base = dict(plugin_id="my_plugin", plugin_name="N", plugin_version="1.0.0", stage="pre",
                    module_file="m.py", entry_class="C")
        base.update(kw)
        return plugin_manifest_new(**base)

    def test_valid(self):
        self.assertEqual(plugin_manifest_validate(self._new()), [])

    def test_each_bad_field(self):
        cases = {"plugin_id": "Bad-Id", "plugin_version": "x", "stage": "mid", "priority": 5000,
                 "module_file": "../m.py", "entry_class": "1bad"}
        for key, value in cases.items():
            with self.subTest(field=key):
                self.assertTrue(plugin_manifest_validate(self._new(**{key: value})), key)

    def test_wrong_format_and_multi_record(self):
        doc = self._new()
        doc["Format_Version"] = "104a"
        self.assertTrue(plugin_manifest_validate(doc))


_GOOD_HEADER = "\n".join([
    '"""',
    "Library:         lib_bejson_AI_Core_sample.py",
    "Family:          AI_Core",
    "Module Purpose:  sample",
    "Version:         1.0.0",
    "Release_Version: 300",
    "Date:            2026-11-17",
    "Author:          Elton Boehnen",
    "Format_Creator:  Elton Boehnen",
    "RELATIONAL_ID:   11111111-2222-4333-8444-555555555555",
    '"""',
    "import logging",
    'VERSION = "1.0.0"',
    '_LOG = logging.getLogger("x")',
    "",
])


class ValidatorTests(unittest.TestCase):
    def _check(self, body: str, name: str = "lib_bejson_AI_Core_sample.py"):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / name).write_text(body, encoding="utf-8")
            bridge_src = (_GOOD_HEADER.replace("sample", "core_bridge")
                          .replace("11111111-2222-4333-8444-555555555555", "99999999-2222-4333-8444-555555555555"))
            (Path(tmp) / f"{V.BRIDGE_MODULE}.py").write_text(bridge_src, encoding="utf-8")
            return {v.rule for v in V.validate_family(tmp, "AI_Core").violations}

    def test_shipped_families_clean(self):
        self.assertEqual(V.validate_family(_AI_DIR, "AI_Core").violations, [])
        self.assertEqual(V.validate_family(_EXT_DIR, "AI_Extensions").violations, [])

    def test_good_sample_passes(self):
        self.assertEqual(self._check(_GOOD_HEADER), set())

    def test_rules_fire(self):
        self.assertIn("no-print", self._check(_GOOD_HEADER + "print('x')\n"))
        self.assertIn("abs-path", self._check(_GOOD_HEADER + "P = '/storage/emulated/0/x'\n"))
        self.assertIn("key-in-url", self._check(_GOOD_HEADER + "U = 'https://h/x?key=abc'\n"))
        self.assertIn("imports", self._check(_GOOD_HEADER + "import requests\n"))
        self.assertIn("core-bridge", self._check(_GOOD_HEADER + "import lib_bejson_Core_bejson_core\n"))
        self.assertIn("core-io", self._check(_GOOD_HEADER + "open('f', 'w')\n"))
        self.assertIn("version", self._check(_GOOD_HEADER.replace('VERSION = "1.0.0"', 'VERSION = "9.9.9"')))
        self.assertIn("naming", self._check(_GOOD_HEADER, "wrong_name.py"))
        no_logger = _GOOD_HEADER.replace("import logging\n", "").replace('_LOG = logging.getLogger("x")\n', "")
        self.assertIn("logging", self._check(no_logger + "try:\n    pass\nexcept Exception:\n    pass\n"))

    def test_allow_pragma_needs_reason_and_matching_rule(self):
        above = _GOOD_HEADER + "# ai-core: allow core-io -- temp file, not BEJSON\nopen('f', 'w')\n"
        self.assertNotIn("core-io", self._check(above))
        same = _GOOD_HEADER + "open('f', 'w')  # ai-core: allow core-io -- same line\n"
        self.assertNotIn("core-io", self._check(same))
        self.assertIn("core-io", self._check(_GOOD_HEADER + "# ai-core: allow core-io\nopen('f', 'w')\n"))
        self.assertIn("core-io", self._check(_GOOD_HEADER + "# ai-core: allow no-print -- wrong rule\nopen('f', 'w')\n"))

    def test_freeze_manifest_detects_change_missing_unpinned(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / "fam"
            shutil.copytree(_AI_DIR, work, ignore=shutil.ignore_patterns("tests", "__pycache__", "config", "docs", "templates"))
            manifest = Path(tmp) / "freeze.105a.bejson"
            V.freeze_manifest_write(manifest, work)
            self.assertEqual(V.freeze_manifest_verify(manifest, work), [])
            target = work / "lib_bejson_AI_Core_models.py"
            target.write_text(target.read_text(encoding="utf-8") + "\n# x\n", encoding="utf-8")
            (work / "lib_bejson_AI_Core_extra.py").write_text("x = 1\n", encoding="utf-8")
            (work / "lib_bejson_AI_Core_postprocessor.py").unlink()
            problems = V.freeze_manifest_verify(manifest, work)
            self.assertIn("changed: lib_bejson_AI_Core_models.py", problems)
            self.assertIn("unpinned: lib_bejson_AI_Core_extra.py", problems)
            self.assertIn("missing: lib_bejson_AI_Core_postprocessor.py", problems)
            with self.assertRaises(AIException) as ctx:
                V.freeze_manifest_verify_or_raise(manifest, work)
            self.assertEqual(ctx.exception.code, ERR_AI_FREEZE_MANIFEST_MISMATCH)


class BridgeTests(unittest.TestCase):
    def test_roundtrip_rows_and_field_map(self):
        doc = bridge.core_new_document("105a", "T", [("a", "string"), ("n", "integer")])
        bridge.core_add_record(doc, {"a": "x", "n": 3})
        fmap = bridge.core_field_map(doc)
        self.assertNotIn("record_uuid", fmap)  # implicit in 105 rows
        self.assertIn("a", fmap)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "t.bejson"
            bridge.core_save(path, doc)
            rows = bridge.core_rows_as_dicts(bridge.core_load(path))
            self.assertEqual((rows[0]["a"], rows[0]["n"]), ("x", 3))

    def test_save_rejects_invalid_and_load_rejects_garbage(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(AIException) as ctx:
                bridge.core_save(Path(tmp) / "bad.bejson", {"Format": "BEJSON"})
            self.assertEqual(ctx.exception.code, ERR_AI_DOCUMENT_INVALID)
            self.assertFalse((Path(tmp) / "bad.bejson").exists())
            junk = Path(tmp) / "junk.bejson"
            junk.write_text("{nope", encoding="utf-8")
            with self.assertRaises(AIException):
                bridge.core_load(junk)

    def test_quarantine_preserves_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "c.bejson"
            path.write_text("evidence", encoding="utf-8")
            backup = bridge.core_quarantine(path, "test")
            self.assertFalse(path.exists())
            self.assertEqual(backup.read_text(encoding="utf-8"), "evidence")
            self.assertIn(".corrupt-", backup.name)

    def test_write_cell_type_enforced(self):
        doc = bridge.core_new_document("105a", "T", [("n", "integer")])
        record_uuid = bridge.core_add_record(doc, {"n": 1})
        bridge.core_write_cell(doc, record_uuid, "n", 2)
        self.assertEqual(bridge.core_rows_as_dicts(doc)[0]["n"], 2)
        with self.assertRaises(AIException):
            bridge.core_write_cell(doc, record_uuid, "n", "two")


if __name__ == "__main__":
    unittest.main()
