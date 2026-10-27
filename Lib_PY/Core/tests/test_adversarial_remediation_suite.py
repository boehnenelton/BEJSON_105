"""
Library:        test_adversarial_remediation_suite.py
Family:         Core (tests)
Description:    Regression tests for the 2026-10-08 adversarial-review
                 remediation: (1) 105db column mapping, (2) two-phase
                 cascade delete, (3) source_env no longer executes code,
                 (4) ResilientPIDLock stale-reclaim / ownership-checked
                 release, (5) zero-copy parse_json fallback.
                 Every test works in its own temp dir; nothing is shared.

                 Run:  python3 tests/test_adversarial_remediation_suite.py

Version:        1.0.0
Date:           2026-10-09
Author:         Elton Boehnen
Contact:        boehnenelton2024@gmail.com | boehnenelton2024.pages.dev | github.com/boehnenelton
Format_Creator: Elton Boehnen
RELATIONAL_ID:  6aa80850-ef7e-42e0-997a-f397a4a63475
Release_Version: 300
"""

import json
import logging
import os
import shutil
import sys
import tempfile
import time
import unittest
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import lib_bejson_Core_bejson_core as C
import lib_bejson_Core_bejson_env as Env
import lib_bejson_Core_bejson_parse as Parse
import lib_bejson_Core_bejson_upgrade as Upgrade
import lib_bejson_Core_bejson_validator as Validator
import lib_bejson_Core_mfdb_core as M
import lib_bejson_Core_mfdb_validator as MV


# ---------------------------------------------------------------------------
# Finding 1 -- 105db positional offset
# ---------------------------------------------------------------------------

def _make_105db(tmpdir):
    doc104 = {
        "Format": "BEJSON", "Format_Version": "104db", "Format_Creator": "Elton Boehnen",
        "Records_Type": ["User", "Role"],
        "Fields": [
            {"name": "Record_Type_Parent", "type": "string"},
            {"name": "user_id", "type": "string", "Record_Type_Parent": "User"},
            {"name": "email", "type": "string", "Record_Type_Parent": "User"},
        ],
        "Values": [["User", "usr_1", "usr@test.com"]],
    }
    path = os.path.join(tmpdir, "t.bejson")
    with open(path, "w") as fh:
        json.dump(doc104, fh)
    return Upgrade.bejson_core_upgrade_to_105(json.load(open(path)), path)


class Test105dbColumnMapping(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="adv105db_")
        self.doc = _make_105db(self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_resolve_indices(self):
        self.assertEqual(C.bejson_core_resolve_field_index(self.doc, "Record_Type_Parent"), 0)
        self.assertEqual(C.bejson_core_resolve_field_index(self.doc, "user_id"), 2)
        self.assertEqual(C.bejson_core_resolve_field_index(self.doc, "email"), 3)

    def test_write_cell_hits_the_named_field_only(self):
        ruuid = self.doc["Values"][0][1]
        fuuid = self.doc["Fields"][1]["field_uuid"]  # user_id
        res = C.bejson_core_write_cell(self.doc, ruuid, fuuid, "usr_2")
        self.assertEqual(res["col"], 2)
        self.assertEqual(self.doc["Values"][0][2:], ["usr_2", "usr@test.com"])

    def test_last_field_write_in_bounds(self):
        ruuid = self.doc["Values"][0][1]
        fuuid = self.doc["Fields"][2]["field_uuid"]  # email (last field)
        C.bejson_core_write_cell(self.doc, ruuid, fuuid, "new@test.com")
        self.assertEqual(len(self.doc["Values"][0]), 4)
        self.assertEqual(self.doc["Values"][0][3], "new@test.com")

    def test_rows_as_dicts_aligns(self):
        want = {"user_id": "usr_1", "email": "usr@test.com", "Record_Type_Parent": "User"}
        rec = MV._rows_as_dicts(self.doc)[0]
        self.assertEqual({k: rec[k] for k in want}, want)

    def test_public_field_map_is_row_position(self):
        fm = C.bejson_core_get_field_map(self.doc)
        row = self.doc["Values"][0]
        self.assertEqual(row[fm["Record_Type_Parent"]], "User")
        self.assertEqual(row[fm["user_id"]], "usr_1")
        self.assertEqual(row[fm["email"]], "usr@test.com")

    def test_remove_field_removes_correct_column(self):
        C.bejson_core_remove_field(self.doc, "user_id")
        self.assertEqual(self.doc["Values"][0][2:], ["usr@test.com"])
        self.assertEqual([f["name"] for f in self.doc["Fields"]], ["Record_Type_Parent", "email"])

    def test_cannot_remove_discriminator(self):
        with self.assertRaises(C.BEJSONCoreError):
            C.bejson_core_remove_field(self.doc, "Record_Type_Parent")

    def test_105_and_105a_unchanged(self):
        d = {"Format": "BEJSON", "Format_Version": "104", "Format_Creator": "Elton Boehnen", "Records_Type": ["T"],
             "Fields": [{"name": "a", "type": "string"}, {"name": "b", "type": "string"}],
             "Values": [["1", "2"]]}
        p = os.path.join(self.tmpdir, "p.bejson")
        json.dump(d, open(p, "w"))
        up = Upgrade.bejson_core_upgrade_to_105(d, p)
        self.assertEqual(C.bejson_core_resolve_field_index(up, "a"), 1)
        self.assertEqual(C.bejson_core_resolve_field_index(up, "b"), 2)


# ---------------------------------------------------------------------------
# Finding 2 -- cascade delete must not partially commit
# ---------------------------------------------------------------------------

class TestCascadeTwoPhase(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="advcascade_")
        orders = [{"name": "label", "type": "string"}]
        items = [{"name": "label", "type": "string"},
                 {"name": "order_fk", "type": "string", "fk_target_entity": "orders", "fk_on_delete": "cascade"}]
        resv = [{"name": "label", "type": "string"},
                {"name": "item_fk", "type": "string", "fk_target_entity": "items", "fk_on_delete": "restrict"}]
        self.mp = M.mfdb_core_create_database(
            root_dir=self.tmpdir, db_name="casc",
            entities=[{"name": "orders", "fields": orders, "format_version": "105"},
                      {"name": "items", "fields": items, "format_version": "105"},
                      {"name": "resv", "fields": resv, "format_version": "105"}])
        M.mfdb_core_enable_ref_integrity(self.mp)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def _add(self, ent, vals):
        return M.mfdb_core_add_entity_record_105(self.mp, ent, vals)["Values"][-1][0]

    def _snap(self):
        out = {}
        for name in ("orders", "items", "resv"):
            out[name] = open(M._get_entity_path(self.mp, name), "rb").read()
        out["manifest"] = open(self.mp, "rb").read()
        return out

    def test_restrict_deep_in_tree_leaves_disk_untouched(self):
        o = self._add("orders", ["O1"])
        self._add("items", ["I0-plain", o])       # sibling the old walk destroyed first
        i = self._add("items", ["I1", o])
        self._add("resv", ["R1", i])
        before = self._snap()
        with self.assertRaises(M.MFDBCoreError) as ctx:
            M.mfdb_core_delete_entity_record_105(self.mp, "orders", o)
        self.assertEqual(ctx.exception.code, M.E_MFDB_FK_RESTRICT_VIOLATION)
        self.assertEqual(self._snap(), before, "refused delete must not modify ANY file")

    def test_successful_cascade_removes_whole_tree(self):
        o = self._add("orders", ["O1"])
        self._add("items", ["I1", o])
        self._add("items", ["I2", o])
        M.mfdb_core_delete_entity_record_105(self.mp, "orders", o)
        self.assertEqual(len(M.mfdb_core_load_entity(self.mp, "orders")), 0)
        self.assertEqual(len(M.mfdb_core_load_entity(self.mp, "items")), 0)

    def test_commit_failure_rolls_back_every_file(self):
        o = self._add("orders", ["O1"])
        self._add("items", ["I1", o])
        self._add("items", ["I2", o])
        before = self._snap()
        real = M._mfdb_delete_record_105_raw
        calls = {"n": 0}

        def flaky(*a, **k):
            calls["n"] += 1
            if calls["n"] == 2:
                raise OSError("injected I/O failure")
            return real(*a, **k)

        M._mfdb_delete_record_105_raw = flaky
        try:
            with self.assertRaises(OSError):
                M.mfdb_core_delete_entity_record_105(self.mp, "orders", o)
        finally:
            M._mfdb_delete_record_105_raw = real
        self.assertEqual(self._snap(), before, "failed commit must restore every file")

    def test_diamond_is_not_reported_as_cycle(self):
        """Two cascade paths to the same record are legitimate."""
        tmp2 = tempfile.mkdtemp(prefix="advdiamond_")
        try:
            a = [{"name": "label", "type": "string"}]
            b = [{"name": "label", "type": "string"},
                 {"name": "a_fk", "type": "string", "fk_target_entity": "a", "fk_on_delete": "cascade"}]
            c = [{"name": "label", "type": "string"},
                 {"name": "a_fk", "type": "string", "fk_target_entity": "a", "fk_on_delete": "cascade"}]
            d = [{"name": "label", "type": "string"},
                 {"name": "b_fk", "type": "string", "fk_target_entity": "b", "fk_on_delete": "cascade"},
                 {"name": "c_fk", "type": "string", "fk_target_entity": "c", "fk_on_delete": "cascade"}]
            mp = M.mfdb_core_create_database(
                root_dir=tmp2, db_name="dia",
                entities=[{"name": n, "fields": f, "format_version": "105"}
                          for n, f in (("a", a), ("b", b), ("c", c), ("d", d))])
            M.mfdb_core_enable_ref_integrity(mp)
            add = lambda e, v: M.mfdb_core_add_entity_record_105(mp, e, v)["Values"][-1][0]
            ua = add("a", ["A"])
            ub = add("b", ["B", ua])
            uc = add("c", ["C", ua])
            add("d", ["D", ub, uc])
            M.mfdb_core_delete_entity_record_105(mp, "a", ua)
            for n in ("a", "b", "c", "d"):
                self.assertEqual(len(M.mfdb_core_load_entity(mp, n)), 0, n)
        finally:
            shutil.rmtree(tmp2)


# ---------------------------------------------------------------------------
# Finding 3 -- source_env must never execute code
# ---------------------------------------------------------------------------

class TestSourceEnvNoExec(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="advenv_")
        self.marker = os.path.join(self.tmpdir, "PWNED")

    def tearDown(self):
        shutil.rmtree(self.tmpdir)
        for k in ("ADV_TEST_ROOT",):
            Env.__dict__.pop(k, None)

    def _write(self, name, text):
        p = os.path.join(self.tmpdir, name)
        with open(p, "w") as fh:
            fh.write(text)
        return p

    def test_malicious_env_file_is_not_executed(self):
        p = self._write("env_file.py", f"import os\nopen({self.marker!r}, 'w').write('x')\n")
        self.assertFalse(Env.source_env(p))
        self.assertFalse(os.path.exists(self.marker))

    def test_call_expression_value_rejected(self):
        p = self._write("env_file.py", f"ADV_TEST_ROOT = open({self.marker!r}, 'w')\n")
        self.assertFalse(Env.source_env(p))
        self.assertFalse(os.path.exists(self.marker))
        self.assertFalse(hasattr(Env, "ADV_TEST_ROOT"))

    def test_legacy_literal_env_file_still_works(self):
        p = self._write("env_file.py", '"""doc"""\nADV_TEST_ROOT = "/some/where"\n')
        self.assertTrue(Env.source_env(p))
        self.assertEqual(Env.ADV_TEST_ROOT, "/some/where")

    def test_json_env_file(self):
        p = self._write("env.json", json.dumps({"ADV_TEST_ROOT": "/j"}))
        self.assertTrue(Env.source_env(p))
        self.assertEqual(Env.ADV_TEST_ROOT, "/j")

    def test_cannot_shadow_module_functions(self):
        p = self._write("env_file.py", "resolve_path = 'boom'\n")
        self.assertFalse(Env.source_env(p))
        self.assertTrue(callable(Env.resolve_path))

    def test_partial_application_never_happens(self):
        p = self._write("env_file.py", f'ADV_TEST_ROOT = "ok"\nBAD = open({self.marker!r})\n')
        self.assertFalse(Env.source_env(p))
        self.assertFalse(hasattr(Env, "ADV_TEST_ROOT"))


# ---------------------------------------------------------------------------
# Finding 4 -- ResilientPIDLock
# ---------------------------------------------------------------------------

def _dead_pid():
    pid = 4_000_000
    while C.ResilientPIDLock._pid_alive(pid):
        pid += 1
    return pid


class TestResilientPIDLock(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="advlock_")
        self.target = os.path.join(self.tmpdir, "ent.bejson")

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def _plant(self, pid, token="deadbeef"):
        lock_dir = self.target + ".lockdir"
        os.mkdir(lock_dir)
        with open(os.path.join(lock_dir, "lock_meta.json"), "w") as fh:
            json.dump({"pid": pid, "timestamp": int(time.time()), "token": token}, fh)
        return lock_dir

    def test_basic_acquire_release(self):
        lk = C.ResilientPIDLock(self.target, timeout_seconds=1)
        with lk:
            self.assertTrue(os.path.isdir(self.target + ".lockdir"))
        self.assertFalse(os.path.exists(self.target + ".lockdir"))

    def test_live_owner_blocks_and_is_not_reclaimed(self):
        lock_dir = self._plant(os.getpid())  # alive
        lk = C.ResilientPIDLock(self.target, timeout_seconds=0.4)
        self.assertFalse(lk.acquire())
        self.assertTrue(os.path.isdir(lock_dir))

    def test_stale_lock_is_reclaimed(self):
        self._plant(_dead_pid())
        lk = C.ResilientPIDLock(self.target, timeout_seconds=2)
        self.assertTrue(lk.acquire())
        lk.release()
        self.assertFalse(os.path.exists(self.target + ".lockdir"))

    def test_release_never_destroys_a_lock_it_does_not_own(self):
        a = C.ResilientPIDLock(self.target, timeout_seconds=1)
        self.assertTrue(a.acquire())
        # Simulate: A's lock was reclaimed and B now owns the directory.
        shutil.rmtree(self.target + ".lockdir")
        lock_dir = self._plant(os.getpid(), token="B-token")
        a.release()
        self.assertTrue(os.path.isdir(lock_dir), "A must not rmdir B's live lock")
        self.assertTrue(os.path.exists(os.path.join(lock_dir, "lock_meta.json")))

    def test_release_without_acquire_is_noop(self):
        lock_dir = self._plant(os.getpid(), token="someone")
        C.ResilientPIDLock(self.target).release()
        self.assertTrue(os.path.isdir(lock_dir))

    def test_reclaim_restores_directory_replaced_by_live_owner(self):
        """A observed stale owner X, but by the time it renames, a live owner Y holds it."""
        lock_dir = self._plant(os.getpid(), token="Y-live")
        lk = C.ResilientPIDLock(self.target, timeout_seconds=1)
        observed_stale = {"pid": _dead_pid(), "token": "X-dead"}
        lk._reclaim_stale(observed_stale)
        self.assertTrue(os.path.isdir(lock_dir), "live lock must be put back")
        meta = json.load(open(os.path.join(lock_dir, "lock_meta.json")))
        self.assertEqual(meta["token"], "Y-live")
        self.assertEqual([n for n in os.listdir(self.tmpdir) if ".stale-" in n], [])

    def test_permission_error_means_alive(self):
        real = os.kill

        def fake_kill(pid, sig):
            raise PermissionError(1, "Operation not permitted")

        os.kill = fake_kill
        try:
            self.assertTrue(C.ResilientPIDLock._pid_alive(12345))
        finally:
            os.kill = real

    def test_no_meta_young_dir_not_stale_old_dir_is_(self):
        lock_dir = self.target + ".lockdir"
        os.mkdir(lock_dir)
        lk = C.ResilientPIDLock(self.target, timeout_seconds=0.3)
        self.assertFalse(lk.acquire())  # mid-acquire grace
        old = time.time() - 60
        os.utime(lock_dir, (old, old))
        lk2 = C.ResilientPIDLock(self.target, timeout_seconds=2)
        self.assertTrue(lk2.acquire())
        lk2.release()


# ---------------------------------------------------------------------------
# Hardening -- parse_json fallback
# ---------------------------------------------------------------------------

class TestParseJsonFallback(unittest.TestCase):

    def test_extracts_embedded_object(self):
        self.assertEqual(Parse.parse_json('noise {"a": 1} trailing'), {"a": 1})

    def test_plain_json(self):
        self.assertEqual(Parse.parse_json('{"a": [1,2]}'), {"a": [1, 2]})

    def test_garbage_raises(self):
        with self.assertRaises(json.JSONDecodeError):
            Parse.parse_json("no braces here")
        with self.assertRaises(json.JSONDecodeError):
            Parse.parse_json("{not json}")


if __name__ == "__main__":
    logging.disable(logging.CRITICAL)
    unittest.main(verbosity=2)
