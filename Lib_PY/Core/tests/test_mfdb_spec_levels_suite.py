"""
Library:        test_mfdb_spec_levels_suite.py
Family:         Core (tests)
Description:    Pins the MFDB spec Level 1/2/3 validation rules (104 crash course)
                for BOTH 104 and 105 entity files: entity Records_Type match (34),
                bidirectional manifest<->entity (38), orphan (37), missing
                Parent_Hierarchy (36), duplicates (35), missing field (40), nulls
                (41), record_count drift = warning only.
                Run: python3 tests/test_mfdb_spec_levels_suite.py
Version:        1.0.0
Date:           2026-10-27
Author:         Elton Boehnen
Format_Creator: Elton Boehnen
RELATIONAL_ID:  b7d41c0e-52a9-4e6f-8d13-0a9c5e7f2b64
Release_Version: 300
"""
import json, os, shutil, sys, tempfile, unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import lib_bejson_Core_mfdb_core as M
import lib_bejson_Core_mfdb_validator as MV

S = lambda n: {"name": n, "type": "string"}


def jl(p):
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def jd(doc, p):
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(doc, fh)


class Base:
    FMT = "104"

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="mfdbspec_")
        self.m = self._make("a")
        self.ent = M._get_entity_path(self.m, "Order")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _make(self, name):
        m = M.mfdb_core_create_database(os.path.join(self.tmp, name), "Shop", [
            {"name": "Customer", "fields": [S("cust_name")], "format_version": self.FMT},
            {"name": "Order", "fields": [S("code")], "format_version": self.FMT}], mfdb_version="1.40")
        add = M.mfdb_core_add_entity_record_105 if self.FMT == "105" else M.mfdb_core_add_entity_record
        add(m, "Customer", ["ann"])
        add(m, "Order", ["O1"])
        return m

    def errs(self, **kw):
        r = MV.validate_mfdb_database(self.m, **kw)
        return r, " | ".join(r.errors)

    def test_clean_database_valid_no_warnings(self):
        r, _ = self.errs()
        self.assertTrue(r.valid, r.errors)
        self.assertEqual(r.warnings, [])

    # ---- Level 2
    def test_records_type_must_match_entity_name(self):
        d = jl(self.ent); d["Records_Type"] = ["WrongName"]; jd(d, self.ent)
        r, e = self.errs(); self.assertFalse(r.valid); self.assertIn("[34]", e)

    def test_records_type_case_sensitive(self):
        d = jl(self.ent); d["Records_Type"] = ["order"]; jd(d, self.ent)
        r, e = self.errs(); self.assertIn("[34]", e)

    def test_records_type_exactly_one(self):
        d = jl(self.ent); d["Records_Type"] = ["Order", "Extra"]; jd(d, self.ent)
        r, e = self.errs(); self.assertFalse(r.valid)

    def test_parent_hierarchy_missing(self):
        d = jl(self.ent); d.pop("Parent_Hierarchy"); jd(d, self.ent)
        r, e = self.errs(); self.assertFalse(r.valid); self.assertIn("Parent_Hierarchy", e)

    def test_orphan_parent_hierarchy_nonexistent_manifest(self):
        d = jl(self.ent); d["Parent_Hierarchy"] = "../nope.mfdb.bejson"; jd(d, self.ent)
        r, e = self.errs(); self.assertIn("[37]", e)

    def test_bidirectional_entity_points_to_other_manifest(self):
        other = self._make("b")
        d = jl(self.ent)
        d["Parent_Hierarchy"] = os.path.relpath(other, os.path.dirname(self.ent)); jd(d, self.ent)
        r, e = self.errs(); self.assertFalse(r.valid); self.assertIn("[38]", e)

    def test_bidirectional_standalone_entity_not_listed(self):
        # copy the entity file next to the manifest's data dir under a name no manifest row lists
        stray = os.path.join(os.path.dirname(self.ent), "stray.bejson")
        shutil.copy(self.ent, stray)
        r = MV.validate_mfdb_entity_file(stray)
        self.assertFalse(r.valid); self.assertIn("[38]", " ".join(r.errors))
        self.assertTrue(MV.validate_mfdb_entity_file(self.ent).valid)

    def test_entity_standalone_name_check_uses_manifest_row(self):
        d = jl(self.ent); d["Records_Type"] = ["Nope"]; jd(d, self.ent)
        r = MV.validate_mfdb_entity_file(self.ent)
        self.assertIn("[34]", " ".join(r.errors))

    def test_entity_format_105db_rejected(self):
        d = jl(self.ent); d["Format_Version"] = "105db"; jd(d, self.ent)
        self.assertFalse(MV.validate_mfdb_database(self.m).valid)

    # ---- Level 3
    def test_record_count_drift_is_warning_only(self):
        mf = jl(self.m)
        names = [f["name"] for f in mf["Fields"]]
        mf["Values"][1][names.index("record_count")] = 99; jd(mf, self.m)
        r, _ = self.errs()
        self.assertTrue(r.valid, r.errors)
        self.assertTrue(any("record_count" in w for w in r.warnings))

    # ---- Level 1
    def test_manifest_level1_codes(self):
        mf = jl(self.m); names = [f["name"] for f in mf["Fields"]]
        i = names.index("entity_name")
        bad = json.loads(json.dumps(mf)); bad["Values"][1][i] = bad["Values"][0][i]; jd(bad, self.m)
        self.assertIn("[35]", self.errs()[1])
        bad = json.loads(json.dumps(mf)); bad["Values"][0][i] = None; jd(bad, self.m)
        self.assertIn("[41]", self.errs()[1])
        bad = json.loads(json.dumps(mf)); bad["Values"][0][names.index("file_path")] = "data/missing.bejson"; jd(bad, self.m)
        self.assertIn("[33]", self.errs()[1])
        bad = json.loads(json.dumps(mf)); bad["Records_Type"] = ["other"]; jd(bad, self.m)
        self.assertFalse(self.errs()[0].valid)


class TestSpec104(Base, unittest.TestCase):
    FMT = "104"


class TestSpec105(Base, unittest.TestCase):
    FMT = "105"


if __name__ == "__main__":
    unittest.main(verbosity=1)
