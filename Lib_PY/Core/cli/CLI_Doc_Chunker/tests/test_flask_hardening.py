"""
File Name : test_flask_hardening.py
Rel. Path : Lib_PY/Core/cli/CLI_Doc_Chunker/tests/test_flask_hardening.py
Purpose   : Regression tests for Doc_Chunker_Flask hardening (snapshot name validation, doc-name
            validation, import-file checks, same-origin POST gate, secret key, response headers).
VERSION   : 1.0.0
Author    : Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
RELATIONAL_ID : 3c9e1f74-8a2b-4d65-b0f3-5e7a91c4d286
Run       : python3 Lib_PY/Core/cli/CLI_Doc_Chunker/tests/test_flask_hardening.py
"""

import logging
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent
FLASK_DIR = TEST_DIR.parent
CORE_DIR = FLASK_DIR.parent.parent
for candidate in (str(FLASK_DIR), str(CORE_DIR)):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

# Doc_Chunker imports lib_bejson_utility, which is NOT shipped in libraries_105 (see dev/AUDIT report, finding CORE-CLI-1).
# The hardening under test does not use it, so a minimal stub lets the module import.
if "lib_bejson_utility" not in sys.modules:
    import types
    _stub = types.ModuleType("lib_bejson_utility")
    _stub.DEFAULT_EXTENSIONS, _stub.DEFAULT_EXCLUDES = [], []
    sys.modules["lib_bejson_utility"] = _stub

try:
    import flask  # noqa: F401
    HAVE_FLASK = True
except ImportError:
    HAVE_FLASK = False


@unittest.skipUnless(HAVE_FLASK, "flask not installed")
class TestDocChunkerFlaskHardening(unittest.TestCase):
    def setUp(self):
        logging.disable(logging.CRITICAL)
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name).resolve()
        spec_path = FLASK_DIR / "Doc_Chunker_Flask.py"
        import importlib.util
        # Doc_Chunker_Flask imports Doc_Chunker from its parent folder; load it by path.
        sys.path.insert(0, str(FLASK_DIR.parent))
        spec = importlib.util.spec_from_file_location("doc_chunker_flask_under_test", spec_path)
        self.mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.mod)
        self.DC = self.mod.DC
        self._saved = (self.DC.DOC_PROJECT_DIR, self.DC._get_active_doc, self.DC._list_doc_names)
        self.DC.DOC_PROJECT_DIR = self.base / "Document_Project"
        (self.DC.DOC_PROJECT_DIR / "Doc1" / "Snapshots").mkdir(parents=True)
        self.DC._get_active_doc = lambda: "Doc1"
        self.DC._list_doc_names = lambda: ["Doc1"]
        self.client = self.mod.app.test_client()

    def tearDown(self):
        self.DC.DOC_PROJECT_DIR, self.DC._get_active_doc, self.DC._list_doc_names = self._saved
        self.tmp.cleanup()
        logging.disable(logging.NOTSET)

    def test_secret_key_is_not_the_old_hardcoded_literal(self):
        self.assertNotEqual(self.mod.app.secret_key, "doc-chunker-flask-dev-key")

    def test_cross_origin_post_rejected(self):
        r = self.client.post("/tools/lock", data={}, headers={"Origin": "http://evil.example"})
        self.assertEqual(r.status_code, 403)

    def test_security_headers_present(self):
        r = self.client.get("/static/app.css")
        self.assertEqual(r.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(r.headers.get("X-Frame-Options"), "DENY")

    def test_restore_snapshot_rejects_traversal_and_foreign_zip(self):
        evil = self.base / "evil.zip"
        with zipfile.ZipFile(evil, "w") as zf:
            zf.writestr("Schema/pwn.txt", "x")
        called = []
        self.DC.cmd_doc_restore_snapshot = lambda p: called.append(p)
        for bad in ("../../evil.zip", "../evil.zip", str(evil), "a/b.zip", "x.txt", ""):
            r = self.client.post("/tools/restore-snapshot", data={"filename": bad})
            self.assertEqual(r.status_code, 302, bad)
        self.assertEqual(called, [], "restore must not be reached for an unsafe filename")
        good = self.DC.DOC_PROJECT_DIR / "Doc1" / "Snapshots" / "snap-1.zip"
        good.write_bytes(b"PK")
        self.client.post("/tools/restore-snapshot", data={"filename": "snap-1.zip"})
        self.assertEqual(called, [str(good.resolve())])

    def test_download_rejects_unknown_doc_name(self):
        r = self.client.get("/compile/download/..%2F..%2Fx/md")
        self.assertIn(r.status_code, (302, 404))
        r = self.client.get("/compile/download/NotADoc/md")
        self.assertEqual(r.status_code, 302)

    def test_import_file_requires_regular_small_file_and_honours_roots(self):
        called = []
        self.DC.cmd_doc_import_file = lambda *a: called.append(a)
        self.client.post("/tools/import-file", data={"file_path": str(self.base), "category": "c"})
        self.assertEqual(called, [], "a directory must be refused")
        f = self.base / "in.txt"; f.write_text("a---b", encoding="utf-8")
        os.environ["DOC_CHUNKER_IMPORT_ROOTS"] = str(self.base / "elsewhere")
        try:
            self.client.post("/tools/import-file", data={"file_path": str(f), "category": "c"})
            self.assertEqual(called, [], "outside DOC_CHUNKER_IMPORT_ROOTS must be refused")
            os.environ["DOC_CHUNKER_IMPORT_ROOTS"] = str(self.base)
            self.client.post("/tools/import-file", data={"file_path": str(f), "category": "c"})
            self.assertEqual(len(called), 1)
        finally:
            os.environ.pop("DOC_CHUNKER_IMPORT_ROOTS", None)


if __name__ == "__main__":
    unittest.main(verbosity=1)
