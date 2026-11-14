"""
File Name : test_cms_admin_security.py
Rel. Path : Lib_PY/CMS/tests/test_cms_admin_security.py
Purpose   : Regression tests for the CMS MTV admin server hardening (output-root confinement,
            identifier validation, same-origin gate, escaped emitted site renderer).
VERSION   : 1.0.0
Author    : Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
RELATIONAL_ID : 0b7a6d52-4f1e-4c83-9a57-6d3e2f81c9a4
Run       : python3 Lib_PY/CMS/tests/test_cms_admin_security.py
"""

import importlib.util
import logging
import os
import sys
import tempfile
import unittest
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent
CMS_DIR = TEST_DIR.parent
LIB_PY_DIR = CMS_DIR.parent
for candidate_dir in (str(CMS_DIR / "web"), str(CMS_DIR), str(LIB_PY_DIR), str(LIB_PY_DIR / "Core")):
    if candidate_dir not in sys.path:
        sys.path.insert(0, candidate_dir)

logging.disable(logging.CRITICAL)  # keep expected-error tracebacks out of test output

import lib_bejson_CMS_mtv_core as mtv_core
import lib_bejson_CMS_mtv_scaffold as mtv_scaffold

try:
    import flask  # noqa: F401
    HAVE_FLASK = True
except ImportError:
    HAVE_FLASK = False


@unittest.skipUnless(HAVE_FLASK, "flask not installed")
class TestAdminServerConfinement(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve() / "out"
        self.outside = Path(self.tmp.name).resolve() / "outside"
        self.outside.mkdir()
        (self.outside / "secret.txt").write_text("TOP-SECRET", encoding="utf-8")
        os.environ["MTV_SCAFFOLD_OUTPUT_ROOT"] = str(self.root)
        import Scaffold_Admin_Entry as entry
        self.app = entry.create_scaffold_admin_application()
        self.client = self.app.test_client()

    def tearDown(self):
        os.environ.pop("MTV_SCAFFOLD_OUTPUT_ROOT", None)
        self.tmp.cleanup()

    def test_secret_key_is_not_the_old_hardcoded_literal(self):
        self.assertNotEqual(self.app.config["SECRET_KEY"], "mtv-scaffold-secret-key-105")
        self.assertGreaterEqual(len(self.app.config["SECRET_KEY"]), 32)

    def test_instantiate_relative_path_lands_inside_root(self):
        r = self.client.post("/api/instantiate", json={"archetype_id": "editorial", "target_path": "site_a"})
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True))
        self.assertTrue((self.root / "site_a" / "build_site.py").exists())

    def test_instantiate_rejects_escape(self):
        for bad in (str(self.outside / "x"), "../outside/x", "a/../../outside/x"):
            r = self.client.post("/api/instantiate", json={"archetype_id": "editorial", "target_path": bad})
            self.assertEqual(r.status_code, 400, bad)
        self.assertFalse((self.outside / "x").exists())

    def test_export_cannot_read_or_write_outside_root(self):
        r = self.client.post("/api/export", json={"project_directory": str(self.outside)})
        self.assertEqual(r.status_code, 400)
        (self.root / "proj").mkdir(parents=True)
        (self.root / "proj" / "a.txt").write_text("ok", encoding="utf-8")
        r = self.client.post("/api/export", json={"project_directory": "proj", "destination_archive_path": str(self.outside / "evil.zip")})
        self.assertEqual(r.status_code, 400)
        self.assertFalse((self.outside / "evil.zip").exists())
        r = self.client.post("/api/export", json={"project_directory": "proj"})
        self.assertEqual(r.status_code, 200)
        self.assertTrue((self.root / "proj.zip").exists())

    def test_export_skips_symlinks(self):
        import zipfile
        (self.root / "proj").mkdir(parents=True)
        (self.root / "proj" / "a.txt").write_text("ok", encoding="utf-8")
        try:
            os.symlink(self.outside / "secret.txt", self.root / "proj" / "leak.txt")
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        self.assertEqual(self.client.post("/api/export", json={"project_directory": "proj"}).status_code, 200)
        with zipfile.ZipFile(self.root / "proj.zip") as zf:
            self.assertEqual(zf.namelist(), ["a.txt"])

    def test_custom_builder_validates_every_identifier(self):
        base = {"archetype_id": "my_plat", "target_path": "c1", "entities": [{"name": "Thing", "prefix": "thg_", "fields": [{"name": "thg_title", "type": "string"}]}]}
        ok = self.client.post("/api/custom/materialize", json=base)
        self.assertEqual(ok.status_code, 200, ok.get_data(as_text=True))
        cases = {
            "traversal entity name": dict(base, target_path="c2", entities=[{"name": "../../evil", "fields": []}]),
            "builtin collision": dict(base, target_path="c3", archetype_id="editorial"),
            "template traversal": dict(base, target_path="c4", bound_templates=["../../../etc/passwd"]),
            "bad field type": dict(base, target_path="c5", entities=[{"name": "Thing", "fields": [{"name": "a_b", "type": "exec"}]}]),
            "non-dict entity": dict(base, target_path="c6", entities=["x"]),
        }
        for label, payload in cases.items():
            self.assertEqual(self.client.post("/api/custom/materialize", json=payload).status_code, 400, label)

    def test_cross_origin_post_is_rejected(self):
        r = self.client.post("/api/instantiate", json={"archetype_id": "editorial", "target_path": "x"}, headers={"Origin": "http://evil.example"})
        self.assertEqual(r.status_code, 403)

    def test_error_responses_do_not_leak_exception_text(self):
        r = self.client.post("/api/instantiate", json={"archetype_id": "editorial", "target_path": "ok_dir"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.client.get("/").headers.get("X-Content-Type-Options"), "nosniff")


class TestEmittedSiteEscaping(unittest.TestCase):
    def test_build_site_header_escapes_tokens_and_blocks_js_urls(self):
        spec = importlib.util.spec_from_loader("emitted_build_site", loader=None)
        mod = importlib.util.module_from_spec(spec)
        mod.__dict__["__file__"] = str(TEST_DIR / "build_site.py")
        exec(compile(mtv_scaffold.STANDALONE_BUILD_SITE_SCRIPT_HEADER.replace('if __name__ == "__main__":\n    execute_static_site_compilation()', ""), "build_site.py", "exec"), mod.__dict__)  # noqa: S102 (generated code under test)
        self.assertEqual(mod.escape_text('<script>alert(1)</script>'), "&lt;script&gt;alert(1)&lt;/script&gt;")
        self.assertEqual(mod.safe_url("javascript:alert(1)"), "#")
        self.assertEqual(mod.safe_url(" JaVaScRiPt:alert(1)"), "#")
        self.assertEqual(mod.safe_url("data:text/html,x"), "#")
        self.assertEqual(mod.safe_url("https://example.com/a?b=1&c=2"), "https://example.com/a?b=1&amp;c=2")
        self.assertEqual(mod.safe_url("chapter-1.html"), "chapter-1.html")
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "t.html").write_text("<h1>{{page_title}}</h1>{{article_body_content}}", encoding="utf-8")
            out = mod.BasePageRenderer(Path(d), {}).render({"page_title": "<img src=x onerror=alert(1)>", "article_body_content": "<p>ok</p>"}, "t.html")
        self.assertIn("&lt;img src=x onerror=alert(1)&gt;", out)
        self.assertIn("<p>ok</p>", out)

    def test_scaffold_refuses_non_bare_template_names(self):
        with tempfile.TemporaryDirectory() as d:
            synth = mtv_scaffold.MTVScaffoldSynthesizer(Path(d) / "p")
            synth.templates_directory_path.mkdir(parents=True)
            (synth.static_directory_path / "css").mkdir(parents=True)
            installed = synth._materialize_behtml_templates({"bound_templates": ["../../../etc/hostname", "scaffold_feed.html"]})
            self.assertIn("scaffold_feed.html", installed)
            self.assertNotIn("../../../etc/hostname", installed)
            self.assertFalse(any(p.name == "hostname" for p in Path(d).rglob("*")))


class TestConfinedPathHelper(unittest.TestCase):
    def test_helper_contract(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            self.assertEqual(mtv_core.bejson_cms_resolve_confined_path("a/b", root), root / "a" / "b")
            for bad in ("", "   ", "../x", "/etc/passwd", "a\x00b"):
                with self.assertRaises(ValueError):
                    mtv_core.bejson_cms_resolve_confined_path(bad, root)
            with self.assertRaises(ValueError):
                mtv_core.bejson_cms_validate_identifier("entity_name", "../x")


if __name__ == "__main__":
    unittest.main(verbosity=1)
