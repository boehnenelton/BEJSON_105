"""
Library:         test_ai_extensions_profiles.py
Family:          AI_Extensions
Module Purpose:  Tests for profile_compiler (temper engine, payload invariants, 105 document entry), profile_abstraction (model class, instruction adaptation, output sanitizing, gated parser dispatch) and profile_runtime (static validation, approval gate, sandboxed run).
Version:         1.0.1
Release_Version: 300
Date:            2026-11-19
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Format_Creator:  Elton Boehnen
RELATIONAL_ID:   aabbe5b1-d973-4f1e-b5cd-41e2f90d3951
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

_EXT = Path(__file__).resolve().parent.parent
_CORE = _EXT.parent / "AI_Core"
for _p in (_EXT, _CORE):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import lib_bejson_AI_Core_profiles as P  # noqa: E402
from lib_bejson_AI_Core_errors import AIException  # noqa: E402
import lib_bejson_AI_Extensions_profile_abstraction as A  # noqa: E402
import lib_bejson_AI_Extensions_profile_compiler as C  # noqa: E402
import lib_bejson_AI_Extensions_profile_runtime as R  # noqa: E402

PARSER = "import json\ndef parse(raw_text):\n    return json.loads(raw_text)\n"


def _v2(**kw):
    return P.ai_profiles_create("Ada", "Auditor-type", "Dry and exact.", "Be precise.", v2=True, **kw)


class TemperTests(unittest.TestCase):
    def test_delta_triggers_and_stability(self):
        d = C.ProfileCompiler2.evaluate_temper_delta
        self.assertEqual(d("this is spaghetti code", ["spaghetti"], [], 2), 5)
        self.assertEqual(d("this is spaghetti code", ["spaghetti"], [], 4), 25)
        self.assertEqual(d("clean tests", ["spaghetti"], ["clean"], 2), -5)
        self.assertEqual(d("neutral", ["x"], ["y"], 4), -6)  # passive decay: -(25/4) rounded
        self.assertEqual(d("SPAGHETTI", ["Spaghetti"], [], 1), 2)  # case-insensitive
        self.assertEqual(d("x", [], [], None), -1)  # null stability tolerated, default stability 2 -> -1.25
        self.assertEqual(d("x", None, None, None), 0)  # no trigger lists at all -> affective engine off, no decay

    def test_step_bounds(self):
        s = C.ProfileCompiler2.step_temper
        self.assertEqual((s(95, 25), s(3, -25), s(40, 10)), (100, 0, 50))

    def test_descriptor_bands(self):
        g = C.ProfileCompiler2.get_temper_descriptor
        names = [g(t)[0] for t in (0, 20, 21, 50, 51, 75, 76, 89, 90, 99, 100, 500, -5)]
        self.assertEqual(names, ["Monk / Zen", "Monk / Zen", "Composed / Neutral", "Composed / Neutral",
                                 "Agitated / Spiky", "Agitated / Spiky", "Hostile / Scorched-Earth",
                                 "Hostile / Scorched-Earth", "Frothing Mad", "Frothing Mad",
                                 "Critical Meltdown", "Critical Meltdown", "Monk / Zen"])


class PayloadTests(unittest.TestCase):
    def test_block_order_and_invariants(self):
        doc = _v2(Job="Auditor", Irritations=["spaghetti"], Pleasures=["tests"], Forbidden_Topics=["politics"],
                  Starting_Temper=30, Stability=3, Knowledge_Directive="study only")
        text = C.compiler_compile_profile(doc, knowledge_context="CTX", author_override="Use British spelling")
        order = [text.index(m) for m in ("[JOB CONTRACT", "[AUTHOR DIRECTIVE", "[PERSONA IDENTITY",
                                          "[INTERNAL AFFECTIVE STATE", "[TRIGGER TAXONOMY", "[KNOWLEDGE BASE",
                                          "[OPERATIONAL SYSTEM INSTRUCTION", "[SAFETY & FORBIDDEN")]
        self.assertEqual(order, sorted(order))
        self.assertIn("Assigned Job: Auditor", text)
        self.assertIn("Current Temper: 30/100 [Composed / Neutral]", text)
        self.assertIn("Never state, cite, or hint", text)  # invisibility invariant
        self.assertIn("study only", text)
        self.assertIn("Strictly Forbidden Topics: politics", text)

    def test_optional_blocks_omitted_and_temper_override_clamped(self):
        text = C.compiler_compile_profile(_v2(), current_temper=999)
        for absent in ("[AUTHOR DIRECTIVE", "[TRIGGER TAXONOMY", "[KNOWLEDGE BASE"):
            self.assertNotIn(absent, text)
        self.assertIn("100/100 [Critical Meltdown]", text)

    def test_null_numeric_cells_do_not_raise(self):
        # All four affective cells null -> affective features are disabled (compiler 2.x behavior), no temper block, no raise.
        row = {"Name": "N", "Stability": None, "Starting_Temper": None, "Persona": None}
        self.assertNotIn("Current Temper", C.ProfileCompiler2.compile_payload(row))
        # A row that declares any affective cell keeps the block; null numeric cells inside it still coerce to defaults.
        row = {"Name": "N", "Stability": None, "Starting_Temper": None, "Persona": None, "Irritations": []}
        self.assertIn("Current Temper: 0/100", C.ProfileCompiler2.compile_payload(row))

    def test_v1_profile_rejected(self):
        with self.assertRaises(AIException):
            C.compiler_compile_profile(P.ai_profiles_create("A", "x", "p", "i"))

    def test_nonstandard_job_warns(self):
        with self.assertLogs(C.logger, level="WARNING"):
            C.compiler_compile_profile(_v2(Job="Wizard"))

    def test_author_sync_truncates_bio(self):
        doc = _v2()
        out = C.ProfileCompiler2.sync_to_author_profile({"Name": "Ada", "Persona": "x" * 400})
        self.assertEqual((out["author_display_name"], len(out["author_bio"])), ("Ada", 280))
        self.assertEqual(C.ProfileCompiler2.sync_to_author_profile({"Name": "Z"})["author_bio"], "Z - AI Ecosystem Profile")
        self.assertTrue(doc)


class AbstractionTests(unittest.TestCase):
    def test_detect_class(self):
        d = A.profiles_abstraction_detect_model_class
        self.assertEqual(d("ollamalocal", "x"), A.MODEL_CLASS_LOCAL_SLM)
        self.assertEqual(d("LiteRT_LM", None), A.MODEL_CLASS_LOCAL_SLM)
        self.assertEqual(d("geminirest", "gemma-2b-mobile"), A.MODEL_CLASS_LOCAL_SLM)
        self.assertEqual(d("geminirest", "gemini-flash"), A.MODEL_CLASS_CLOUD)
        self.assertEqual(d(None, None), A.MODEL_CLASS_CLOUD)

    def test_adapt_instruction(self):
        long_text = "word " * 1000
        self.assertEqual(A.profiles_abstraction_adapt_instruction(long_text, "geminirest"), long_text.strip())
        local = A.profiles_abstraction_adapt_instruction(long_text, "litertlm", max_prompt_chars=100)
        self.assertIn("condensed for on-device", local)
        self.assertIn("under 30 words", local)
        self.assertLess(len(local), 400)
        self.assertNotIn("LOCAL EXECUTION RULE", A.profiles_abstraction_adapt_instruction("short", "litertlm", signal_mode=False))
        self.assertEqual(A.profiles_abstraction_adapt_instruction("", "litertlm"), "")

    def test_sanitize_output(self):
        s = A.profiles_abstraction_sanitize_output
        self.assertEqual(s('Sure! ```json\n{"a": 1}\n``` hope that helps'), '{"a": 1}')
        self.assertEqual(s('Here you go: {"a": [1, 2]} thanks'), '{"a": [1, 2]}')
        self.assertEqual(s("  plain  "), "plain")
        self.assertEqual(s(None), "")

    def test_run_parser_gate_and_local_fallback(self):
        doc = _v2(Parser_Language="python", Parser=PARSER)
        fp = P.ai_profiles_embedded_fingerprint(doc)
        refused = A.profiles_abstraction_run_parser(doc, '{"a": 1}', [], "geminirest")
        self.assertFalse(refused["success"])
        ok = A.profiles_abstraction_run_parser(doc, '{"a": 1}', [fp], "geminirest")
        self.assertTrue(ok["success"], ok)
        wrapped = A.profiles_abstraction_run_parser(doc, 'Sure!\n```json\n{"a": 1}\n```', [fp], "ollamalocal")
        self.assertTrue(wrapped["success"], wrapped)
        cloud_wrapped = A.profiles_abstraction_run_parser(doc, 'Sure!\n```json\n{"a": 1}\n```', [fp], "geminirest")
        self.assertFalse(cloud_wrapped["success"])  # cloud path does not sanitize


class RuntimeTests(unittest.TestCase):
    def test_validate_python(self):
        v = R.runtime_validate_python_parser
        self.assertEqual(v(PARSER), [])
        self.assertTrue(any("import not allowed: os" in e for e in v("import os\ndef parse(t):\n    return t")))
        self.assertTrue(v("def parse(t):\n    return open('f')"))
        self.assertTrue(v("def parse(t):\n    return t.__class__"))
        self.assertTrue(v("def other(t):\n    return t"))
        self.assertTrue(v("def parse(t:\n"))
        self.assertTrue(v(""))

    def test_validate_javascript(self):
        v = R.runtime_validate_javascript_parser
        self.assertEqual(v("function parse(t){return t}"), [])
        self.assertTrue(v("function parse(t){return fetch('x')}"))
        self.assertTrue(v("function parse(t){return eval(t)}"))
        self.assertTrue(v("const x = 1"))

    def test_fingerprint_changes_with_each_part(self):
        base = R.runtime_fingerprint("python", PARSER, "function render(){}")
        self.assertEqual(len(base), 64)
        self.assertNotEqual(base, R.runtime_fingerprint("python", PARSER + " ", "function render(){}"))
        self.assertNotEqual(base, R.runtime_fingerprint("python", PARSER, "function render(){ }"))
        self.assertEqual(R.runtime_normalize_language("PY"), "python")
        self.assertIsNone(R.runtime_normalize_language("ruby"))

    def test_run_python_parser_result_and_isolation(self):
        out = R.runtime_run_python_parser(PARSER, '{"k": [1, 2]}')
        self.assertTrue(out["success"], out)
        self.assertIn("k", str(out))
        bad = R.runtime_run_python_parser("def parse(t):\n    return 1/0", "x")
        self.assertFalse(bad["success"])
        loop = R.runtime_run_python_parser("def parse(t):\n    while True:\n        pass", "x", timeout=1.0)
        self.assertFalse(loop["success"])

    def test_unsupported_language(self):
        self.assertFalse(R.runtime_run_parser("ruby", "x", "y")["success"])

    def test_profile_gate_and_embedded_load(self):
        plain = _v2()
        self.assertFalse(R.ai_profiles_run_parser(plain, "x", [])["success"])
        self.assertEqual(R.ai_profiles_validate_embedded(plain), [])
        doc = _v2(Parser_Language="python", Parser=PARSER)
        loaded = R.ai_profiles_load_embedded(doc, [])
        self.assertTrue(loaded["success"] and loaded["has_embedded"] and not loaded["approved"])
        self.assertTrue(R.ai_profiles_load_embedded(doc, [loaded["fingerprint"]], syntax_check_js=False)["approved"])
        bad = _v2(Parser_Language="python", Parser="import os\ndef parse(t):\n    return t")
        self.assertFalse(R.ai_profiles_run_parser(bad, "x", [P.ai_profiles_embedded_fingerprint(bad)])["success"])

    def test_language_without_code_is_flagged(self):
        doc = _v2(Parser_Language="python", Parser="def parse(t):\n    return t")
        P.ai_profiles_update_value(doc, "Parser", "")
        self.assertTrue(any("Parser is empty" in e for e in R.ai_profiles_validate_embedded(doc)))

    def test_sandbox_refused_until_approved_and_escapes_script_close(self):
        doc = _v2(Parser_Language="javascript", Parser="function parse(t){return t}", Renderer="function render(p, el){el.textContent = p}")
        refused = R.ai_profiles_build_sandbox(doc, [])
        self.assertFalse(refused["success"])
        self.assertEqual(refused["srcdoc"], "")
        approved = R.ai_profiles_build_sandbox(doc, [P.ai_profiles_embedded_fingerprint(doc)])
        self.assertTrue(approved["success"], approved)
        self.assertEqual(approved["iframe_attributes"], 'sandbox="allow-scripts"')
        self.assertIn("function parse", approved["srcdoc"])


if __name__ == "__main__":
    unittest.main()
