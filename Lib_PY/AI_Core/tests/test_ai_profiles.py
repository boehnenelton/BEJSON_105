"""
Library:         test_ai_profiles.py
Family:          AI_Core
Module Purpose:  Tests for lib_bejson_AI_Core_profiles: 105 create/validate/update, optional parser columns, 104->105 conversion (never in place, lossless), save/load.
Version:         1.0.0
Release_Version: 300
Date:            2026-11-17
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Format_Creator:  Elton Boehnen
RELATIONAL_ID:   0ed9378b-f9d8-47f5-8fdc-8fa4f51355cd
"""
from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path

_AI_DIR = Path(__file__).resolve().parent.parent
if str(_AI_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_DIR))

import lib_bejson_AI_Core_profiles as P  # noqa: E402
from lib_bejson_AI_Core_errors import (  # noqa: E402
    AIException,
    ERR_AI_PROFILE_INVALID,
    ERR_AI_PROFILE_MIGRATION_FAILED,
)


def _doc104(v2: bool = False, extra: bool = False) -> dict:
    schema = P.PROFILE_2_FIELDS if v2 else P.PROFILE_FIELDS
    fields = [{"name": "Record_Type_Parent", "type": "string"}] + [{"name": n, "type": t} for n, t in schema]
    if extra:
        fields += [{"name": "Parser_Language", "type": "string"}, {"name": "Parser", "type": "string"}]
    values = {n: P.PROFILE_DEFAULTS.get(n) for n, _ in schema}
    values.update({"Name": "Legacy", "Archetype": "Old", "Persona": "p", "System_Instruction": "si", "Job": "Chat", "Max_Response_Tokens": 16384})
    row = ["AI_Profile_v2" if v2 else "AI_Profile"] + [values[n] for n, _ in schema]
    if extra:
        row += ["python", "def parse(t):\n    return t"]
    return {"Format": "BEJSON", "Format_Version": "104", "Format_Creator": "Elton Boehnen",
            "Records_Type": ["AI_Profile_v2" if v2 else "AI_Profile"], "Fields": fields, "Values": [row]}


class CreateValidateTests(unittest.TestCase):
    def test_v1_shape(self):
        doc = P.ai_profiles_create("A", "Arch", "persona", "instr")
        self.assertTrue(P.ai_profiles_validate(doc))
        self.assertEqual(doc["Format_Version"], "105")
        self.assertEqual(len([f for f in doc["Fields"] if f["name"] in {n for n, _ in P.PROFILE_FIELDS}]), 22)
        self.assertNotIn("record_uuid", {f["name"] for f in doc["Fields"]})
        self.assertNotIn("Record_Type_Parent", {f["name"] for f in doc["Fields"]})

    def test_v2_shape(self):
        doc = P.ai_profiles_create("B", "Arch", "persona", "instr", v2=True, Job="Auditor")
        self.assertTrue(P.ai_profiles_is_v2(doc))
        self.assertTrue(P.ai_profiles_validate(doc))
        self.assertEqual(len(P.PROFILE_2_FIELDS), 31)
        self.assertEqual(P.ai_profiles_get_value(doc, "Job"), "Auditor")

    def test_unknown_kwarg_rejected(self):
        with self.assertRaises(AIException) as ctx:
            P.ai_profiles_create("A", "x", "p", "i", Bogus=1)
        self.assertEqual(ctx.exception.code, ERR_AI_PROFILE_INVALID)

    def test_problems_lists_missing_and_wrong_type(self):
        doc = P.ai_profiles_create("A", "x", "p", "i")
        doc["Fields"] = [f for f in doc["Fields"] if f["name"] != "Creativity"]
        self.assertTrue(any("Creativity" in p for p in P.ai_profiles_problems(doc)))
        self.assertTrue(P.ai_profiles_problems("nope"))

    def test_update_value_is_type_checked(self):
        doc = P.ai_profiles_create("A", "x", "p", "i")
        self.assertTrue(P.ai_profiles_update_value(doc, "Creativity", 0.2))
        self.assertEqual(P.ai_profiles_get_value(doc, "Creativity"), 0.2)
        self.assertFalse(P.ai_profiles_update_value(doc, "Creativity", "hot"))
        self.assertFalse(P.ai_profiles_update_value(doc, "No_Such_Field", 1))
        self.assertFalse(P.ai_profiles_update_value(doc, "Creativity", 0.1, record_index=9))
        self.assertEqual(P.ai_profiles_get_value(doc, "Creativity"), 0.2)


class OptionalCodeTests(unittest.TestCase):
    def test_parser_and_renderer_roundtrip_and_fingerprint(self):
        doc = P.ai_profiles_create("A", "x", "p", "i")
        self.assertIsNone(P.ai_profiles_embedded_fingerprint(doc))
        self.assertTrue(P.ai_profiles_set_parser(doc, "Python", "def parse(t):\n    return t"))
        self.assertTrue(P.ai_profiles_set_renderer(doc, "function render(x){return x}"))
        self.assertEqual(P.ai_profiles_get_parser(doc)["language"], "python")
        fp = P.ai_profiles_embedded_fingerprint(doc)
        self.assertEqual(len(fp), 64)
        P.ai_profiles_set_renderer(doc, "function render(x){return x+1}")
        self.assertNotEqual(fp, P.ai_profiles_embedded_fingerprint(doc))
        self.assertTrue(P.ai_profiles_validate(doc))

    def test_validator_hook_rejects_without_writing(self):
        doc = P.ai_profiles_create("A", "x", "p", "i")
        self.assertFalse(P.ai_profiles_set_parser(doc, "python", "x", code_validator=lambda lang, code: ["bad"]))
        self.assertIsNone(P.ai_profiles_get_parser(doc))
        self.assertNotIn("Parser", P.ai_profiles_get_field_map(doc))

    def test_blank_code_clears(self):
        doc = P.ai_profiles_create("A", "x", "p", "i", Parser_Language="python", Parser="def parse(t):\n    return t")
        self.assertIsNotNone(P.ai_profiles_get_parser(doc))
        P.ai_profiles_set_parser(doc, None, "")
        self.assertIsNone(P.ai_profiles_get_parser(doc))


class ConversionTests(unittest.TestCase):
    def test_104_v1_to_105_lossless_and_source_untouched(self):
        src = _doc104(v2=False)
        before = copy.deepcopy(src)
        out = P.ai_profiles_convert_104_to_105(src)
        self.assertEqual(src, before)
        self.assertEqual(out["Format_Version"], "105")
        self.assertTrue(P.ai_profiles_validate(out))
        self.assertNotIn("Record_Type_Parent", P.ai_profiles_get_field_map(out))
        row = P.ai_profiles_row(out)
        self.assertEqual((row["Name"], row["Persona"], row["Max_Response_Tokens"]), ("Legacy", "p", 16384))

    def test_104_v2_with_parser_columns(self):
        out = P.ai_profiles_convert_104_to_105(_doc104(v2=True, extra=True))
        self.assertTrue(P.ai_profiles_is_v2(out))
        self.assertEqual(P.ai_profiles_get_parser(out)["language"], "python")
        self.assertTrue(P.ai_profiles_validate(out))

    def test_rejects_non_104_and_incomplete(self):
        with self.assertRaises(AIException) as ctx:
            P.ai_profiles_convert_104_to_105(P.ai_profiles_create("A", "x", "p", "i"))
        self.assertEqual(ctx.exception.code, ERR_AI_PROFILE_MIGRATION_FAILED)
        broken = _doc104()
        broken["Fields"] = [f for f in broken["Fields"] if f["name"] != "Persona"]
        broken["Values"] = [[v for i, v in enumerate(broken["Values"][0]) if i != 3]]
        with self.assertRaises(AIException):
            P.ai_profiles_convert_104_to_105(broken)

    def test_convert_file_never_in_place(self):
        import json
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "p104.bejson"
            src.write_text(json.dumps(_doc104()), encoding="utf-8")
            original = src.read_bytes()
            with self.assertRaises(AIException):
                P.ai_profiles_convert_file(src, src)
            dst = Path(tmp) / "p105.bejson"
            P.ai_profiles_convert_file(src, dst)
            self.assertEqual(src.read_bytes(), original)
            self.assertEqual(P.ai_profiles_get_value(P.ai_profiles_load(dst), "Name"), "Legacy")


class PersistenceTests(unittest.TestCase):
    def test_save_load_query(self):
        with tempfile.TemporaryDirectory() as tmp:
            P.ai_profiles_save(P.ai_profiles_create("Alpha", "x", "p", "i"), Path(tmp) / "a.bejson")
            P.ai_profiles_save(P.ai_profiles_create("Beta", "x", "p", "i", v2=True), Path(tmp) / "b.bejson")
            (Path(tmp) / "junk.bejson").write_text("{not json", encoding="utf-8")
            self.assertEqual(P.ai_profiles_get_value(P.ai_profiles_query_by_name(tmp, "Beta"), "Name"), "Beta")
            self.assertIsNone(P.ai_profiles_query_by_name(tmp, "Gamma"))

    def test_save_refuses_invalid_and_load_refuses_104(self):
        import json
        with tempfile.TemporaryDirectory() as tmp:
            bad = P.ai_profiles_create("A", "x", "p", "i")
            bad["Records_Type"] = ["Wrong"]
            with self.assertRaises(AIException):
                P.ai_profiles_save(bad, Path(tmp) / "x.bejson")
            self.assertFalse((Path(tmp) / "x.bejson").exists())
            old = Path(tmp) / "old.bejson"
            old.write_text(json.dumps(_doc104()), encoding="utf-8")
            with self.assertRaises(AIException):
                P.ai_profiles_load(old)


class AffectiveBypassTests(unittest.TestCase):
    def tearDown(self):
        P.ai_profiles_set_affective_features_disabled(False)

    def test_bypass_affective_features_rules_entries_null(self):
        doc = P.ai_profiles_create(
            "V2Agent", "Arch", "persona", "instr", v2=True,
            Starting_Temper=25, Stability=3, Irritations=["bugs"], Pleasures=["tea"]
        )
        bypassed = P.ai_profiles_bypass_affective_features(doc)
        row = P.ai_profiles_row(bypassed)
        self.assertIsNone(row["Starting_Temper"])
        self.assertIsNone(row["Stability"])
        self.assertIsNone(row["Irritations"])
        self.assertIsNone(row["Pleasures"])
        self.assertFalse(row["Emotional_Expression_Enabled"])

    def test_global_disable_affective_features(self):
        doc = P.ai_profiles_create(
            "V2Agent", "Arch", "persona", "instr", v2=True,
            Starting_Temper=25, Stability=3, Irritations=["bugs"], Pleasures=["tea"]
        )
        # Normally present
        self.assertEqual(P.ai_profiles_row(doc)["Starting_Temper"], 25)
        # Globally disabled
        P.ai_profiles_set_affective_features_disabled(True)
        self.assertTrue(P.ai_profiles_get_affective_features_disabled())
        row = P.ai_profiles_row(doc)
        self.assertIsNone(row["Starting_Temper"])
        self.assertIsNone(row["Stability"])
        self.assertIsNone(row["Irritations"])
        self.assertIsNone(row["Pleasures"])

    def test_mode_field_strictly_forbidden(self):
        doc = P.ai_profiles_create("A", "B", "C", "D")
        doc["Fields"].append({"name": "Mode", "type": "string"})
        doc["Values"][0].append("chat")
        problems = P.ai_profiles_problems(doc)
        self.assertTrue(any("Mode is deprecated and forbidden" in p for p in problems))
        self.assertFalse(P.ai_profiles_validate(doc))


if __name__ == "__main__":
    unittest.main()
