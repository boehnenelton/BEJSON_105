"""
File Name : test_standards.py
Rel. Path : Lib_PY/Standards/tests/test_standards.py
Purpose   : Tests for lib_bejson_Standards v3 (errors, validator, core, export, registry; 17-column schema, optional fields, priority, secure routing, filters, export, archiving) against unmodified Core.
VERSION   : 3.1.0
Author    : Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
RELATIONAL_ID : 98b6b9ef-18d1-4c7b-9e1d-613e409efccf
Run       : python3 Lib_PY/Standards/tests/test_standards.py
"""
import io
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from datetime import datetime, timezone
from html.parser import HTMLParser

_HERE = os.path.dirname(os.path.abspath(__file__))
_STD = os.path.normpath(os.path.join(_HERE, ".."))
sys.path.insert(0, _STD)

import lib_bejson_Standards_core as core  # noqa: E402
import lib_bejson_Standards_errors as err  # noqa: E402
import lib_bejson_Standards_export as export  # noqa: E402
import lib_bejson_Standards_registry as reg  # noqa: E402
import lib_bejson_Standards_validator as val  # noqa: E402
import lib_bejson_Core_bejson_errors as core_err  # noqa: E402

UUID4 = "3f2b8c1e-5a4d-4e7b-9c10-2d6e8f0a1b3c"


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="std_test_")
        self.path = os.path.join(self.tmp, "logs", "app.bejson")

    def jload(self):
        with open(self.path, encoding="utf-8") as fh:
            return json.load(fh)

    def jdump(self, doc):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as fh:
            json.dump(doc, fh)

    def tearDown(self):
        reg._SINKS.clear()
        shutil.rmtree(self.tmp, ignore_errors=True)


class TestErrorsAndSchema(unittest.TestCase):
    def test_codes_in_block_and_unique(self):
        codes = [v for k, v in vars(err).items() if k.startswith("E_STANDARDS_")]
        self.assertEqual(len(codes), len(set(codes)))
        self.assertTrue(all(250 <= c <= 269 for c in codes))
        self.assertEqual(set(codes), set(err.ERROR_NAMES))

    def test_no_collision_with_core(self):
        core_codes = {v for k, v in vars(core_err).items() if k.startswith("E_") and isinstance(v, int)}
        self.assertFalse(core_codes & set(err.ERROR_NAMES))

    def test_schema_complies_with_taxonomy_rules(self):
        self.assertEqual(val.bejson_standards_validator_check_schema_taxonomy(), [])

    def test_trailing_slot_is_last(self):
        self.assertEqual(val.LOG_FIELDS[-1][0], val.F_ZSLOT)

    def test_canonical_fields_are_fresh_copies(self):
        a = val.bejson_standards_validator_canonical_fields()
        a[0]["name"] = "x"
        self.assertEqual(val.bejson_standards_validator_canonical_fields()[0]["name"], val.F_EVENT_TIMESTAMP)


class TestValidator(Base):
    def row(self, **kw):
        args = dict(level="INFO", subsystem="s", event_key="k", message="m")
        args.update(kw)
        return core.bejson_standards_core_build_row(**args)

    def test_levels(self):
        n = val.bejson_standards_validator_normalize_level
        self.assertEqual(n("warning"), "WARN")
        self.assertEqual(n("Critical"), "FATAL")
        self.assertIsNone(n("LOUD"))
        self.assertIsNone(n(3))

    def test_good_row(self):
        self.assertEqual(val.bejson_standards_validator_check_row(self.row(error_code=7, target_uuid=UUID4)), [])

    def test_bad_values(self):
        c = val.bejson_standards_validator_check_value
        self.assertTrue(c(val.F_EVENT_ERROR_CODE, True))             # bool is not an integer
        self.assertTrue(c(val.F_EVENT_ERROR_CODE, "7"))
        self.assertTrue(c(val.F_TARGET, "not-a-uuid"))
        self.assertTrue(c(val.F_EVENT_TIMESTAMP, "yesterday"))
        self.assertTrue(c(val.F_ZSLOT, "x"))
        self.assertTrue(c(val.F_EVENT_CONTEXT, "{broken"))
        self.assertTrue(c(val.F_EVENT_KEY, "  "))
        self.assertTrue(c(val.F_SENDER_PID, -1))
        self.assertEqual(c(val.F_ZSLOT, None), [])

    def test_unknown_entry_key_flagged(self):
        e = {n: None for n, _ in val.LOG_FIELDS}
        e.update({val.F_EVENT_TIMESTAMP: core.bejson_standards_core_utc_now(), val.F_EVENT_LEVEL: "INFO",
                  val.F_SENDER_SUBSYSTEM: "s", val.F_EVENT_KEY: "k", val.F_EVENT_MESSAGE: "m", val.F_SENDER_PID: 1, "extra": 1})
        self.assertTrue(any("extra" in p for p in val.bejson_standards_validator_check_entry(e)))

    def test_config(self):
        c = val.bejson_standards_validator_check_config
        self.assertEqual(c(10, "info", 5, 0), [])
        self.assertTrue(c(row_cap=0))
        self.assertTrue(c(row_cap=True))
        self.assertTrue(c(min_level="x"))
        self.assertTrue(c(batch_size=-1))
        self.assertTrue(c(flush_interval_seconds=-1))

    def test_audit_missing_and_garbage_never_raise(self):
        self.assertFalse(val.bejson_standards_validator_audit_log_file(self.path)["passed"])
        os.makedirs(os.path.dirname(self.path))
        with open(self.path, "w") as fh:
            fh.write("{nope")
        res = val.bejson_standards_validator_audit_log_file(self.path)
        self.assertFalse(res["passed"])
        self.assertFalse(val.bejson_standards_validator_audit_log_file(None)["passed"])

    def test_audit_is_read_only(self):
        core.bejson_standards_core_append_rows(self.path, [self.row()])
        with open(self.path, "rb") as fh:
            before = fh.read()
        mtime = os.stat(self.path).st_mtime_ns
        self.assertTrue(val.bejson_standards_validator_audit_log_file(self.path)["passed"])
        with open(self.path, "rb") as fh:
            self.assertEqual(fh.read(), before)
        self.assertEqual(os.stat(self.path).st_mtime_ns, mtime)

    def test_audit_catches_tampering(self):
        core.bejson_standards_core_append_rows(self.path, [self.row()])
        doc = self.jload()
        doc["Values"][0][-1] = "not null"                       # reserved slot filled
        doc["Values"][0][1] = "LOUD"
        doc["_bejson_field_map"] = {}
        self.jdump(doc)
        problems = val.bejson_standards_validator_audit_log_file(self.path)["problems"]
        self.assertTrue(any("reserved slot" in p for p in problems))
        self.assertTrue(any("LOUD" in p for p in problems))
        self.assertTrue(any("'_'" in p for p in problems))

    def test_audit_catches_over_cap_and_schema(self):
        core.bejson_standards_core_append_rows(self.path, [self.row()] * 3)
        doc = self.jload()
        doc[val.HDR_ROW_CAP] = 2
        doc["Fields"][0]["name"] = "renamed"
        self.jdump(doc)
        problems = val.bejson_standards_validator_audit_log_file(self.path)["problems"]
        self.assertTrue(any("exceed" in p for p in problems))
        self.assertTrue(any("canonical" in p for p in problems))


class TestCore(Base):
    def row(self, i=0):
        return core.bejson_standards_core_build_row("INFO", "s", "k", f"m{i}")

    def test_build_row_errors(self):
        with self.assertRaises(err.StandardsLogError) as cm:
            core.bejson_standards_core_build_row("LOUD", "s", "k", "m")
        self.assertEqual(cm.exception.code, err.E_STANDARDS_LOG_INVALID_LEVEL)
        with self.assertRaises(err.StandardsLogError) as cm:
            core.bejson_standards_core_build_row("INFO", "s", "k", "m", target_uuid="x")
        self.assertEqual(cm.exception.code, err.E_STANDARDS_LOG_SCHEMA_MISMATCH)
        with self.assertRaises(err.StandardsLogError) as cm:
            core.bejson_standards_core_build_row("INFO", "", "k", "m")
        self.assertEqual(cm.exception.code, err.E_STANDARDS_LOG_SCHEMA_MISMATCH)

    def test_context_non_json_types_are_stringified(self):
        r = core.bejson_standards_core_build_row("INFO", "s", "k", "m", context={"p": object})
        self.assertEqual(val.bejson_standards_validator_check_row(r), [])

    def test_ring_trim_keeps_newest(self):
        for i in range(0, 10, 5):
            core.bejson_standards_core_append_rows(self.path, [self.row(j) for j in range(i, i + 5)], row_cap=6)
        doc = core.bejson_standards_core_load(self.path)
        msgs = [d[val.F_EVENT_MESSAGE] for d in core.bejson_standards_core_rows_to_dicts(doc)]
        self.assertEqual(msgs, [f"m{i}" for i in range(4, 10)])
        self.assertEqual(doc[val.HDR_ROW_CAP], 6)

    def test_cap_persists_without_resupply(self):
        core.bejson_standards_core_append_rows(self.path, [self.row()], row_cap=3)
        res = core.bejson_standards_core_append_rows(self.path, [self.row()] * 5)
        self.assertEqual(res["total"], 3)

    def test_shrinking_cap_trims_immediately(self):
        core.bejson_standards_core_append_rows(self.path, [self.row()] * 8, row_cap=100)
        core.bejson_standards_core_set_header(self.path, row_cap=2)
        self.assertEqual(len(core.bejson_standards_core_load(self.path)["Values"]), 2)

    def test_no_runtime_keys_persisted(self):
        core.bejson_standards_core_append_rows(self.path, [self.row()])
        self.assertFalse([k for k in self.jload() if k.startswith("_")])

    def test_field_map_matches_schema_after_rotation(self):
        core.bejson_standards_core_append_rows(self.path, [self.row()] * 4, row_cap=2)
        doc = core.bejson_standards_core_load(self.path)
        fmap = core.bejson_core_get_field_map(doc)
        self.assertEqual([n for n, _ in sorted(fmap.items(), key=lambda kv: kv[1])], [n for n, _ in val.LOG_FIELDS])

    def test_corrupt_file_quarantined_and_replaced(self):
        os.makedirs(os.path.dirname(self.path))
        with open(self.path, "w") as fh:
            fh.write("{truncated")
        with redirect_stderr(io.StringIO()):
            core.bejson_standards_core_append_rows(self.path, [self.row()])
        siblings = os.listdir(os.path.dirname(self.path))
        self.assertTrue(any(".corrupt-" in s for s in siblings))
        self.assertTrue(val.bejson_standards_validator_audit_log_file(self.path)["passed"])

    def test_foreign_file_refused_not_overwritten(self):
        os.makedirs(os.path.dirname(self.path))
        foreign = {"Format": "BEJSON", "Format_Version": "104a", "Format_Creator": "Elton Boehnen",
                   "Records_Type": ["Other"], "Fields": [{"name": "a", "type": "string"}], "Values": [["x"]]}
        self.jdump(foreign)
        with self.assertRaises(err.StandardsLogError) as cm:
            core.bejson_standards_core_append_rows(self.path, [self.row()])
        self.assertEqual(cm.exception.code, err.E_STANDARDS_LOG_SCHEMA_MISMATCH)
        self.assertEqual(self.jload(), foreign)

    def test_lock_timeout_maps_to_184(self):
        from lib_bejson_Core_bejson_core import ResilientPIDLock
        old = core.LOCK_TIMEOUT_SECONDS
        core.LOCK_TIMEOUT_SECONDS = 1
        os.makedirs(os.path.dirname(self.path))
        try:
            with ResilientPIDLock(os.path.abspath(self.path), timeout_seconds=5):
                with self.assertRaises(err.StandardsLogError) as cm:
                    core.bejson_standards_core_append_rows(self.path, [self.row()])
            self.assertEqual(cm.exception.code, err.E_STANDARDS_LOG_LOCK_TIMEOUT)
        finally:
            core.LOCK_TIMEOUT_SECONDS = old

    def test_write_failure_maps_to_182(self):
        real = core.bejson_core_atomic_write
        core.bejson_core_atomic_write = lambda p, d: False
        try:
            with self.assertRaises(err.StandardsLogError) as cm:
                core.bejson_standards_core_append_rows(self.path, [self.row()])
            self.assertEqual(cm.exception.code, err.E_STANDARDS_LOG_WRITE_FAILED)
        finally:
            core.bejson_core_atomic_write = real

    def test_multiprocess_no_lost_rows(self):
        procs, per = 4, 40
        code = (
            "import sys;sys.path.insert(0,%r);import lib_bejson_Standards_registry as r;"
            "p=sys.argv[1];r.bejson_standards_configure_sink(p,row_cap=10000,batch_size=5,persist=False)\n"
            "for i in range(%d): r.bejson_standards_log(p,'INFO','mp','m',i=i)\n"
            "sys.exit(0 if r.bejson_standards_flush() else 3)" % (_STD, per))
        ps = [subprocess.Popen([sys.executable, "-c", code, self.path], stderr=subprocess.PIPE) for _ in range(procs)]
        for p in ps:
            _o, e = p.communicate(timeout=120)
            self.assertEqual(p.returncode, 0, e.decode())
        doc = core.bejson_standards_core_load(self.path)
        self.assertEqual(len(doc["Values"]), procs * per)
        self.assertTrue(val.bejson_standards_validator_audit_log_file(self.path)["passed"])


class TestRegistry(Base):
    def test_batching_defers_write_until_threshold(self):
        reg.bejson_standards_configure_sink(self.path, batch_size=5, flush_interval_seconds=3600, persist=False)
        for i in range(4):
            reg.bejson_standards_log(self.path, "INFO", "k", f"m{i}")
        self.assertFalse(os.path.exists(self.path))
        reg.bejson_standards_log(self.path, "INFO", "k", "m4")
        self.assertEqual(len(core.bejson_standards_core_load(self.path)["Values"]), 5)

    def test_error_flushes_immediately(self):
        reg.bejson_standards_configure_sink(self.path, batch_size=100, flush_interval_seconds=3600, persist=False)
        reg.bejson_standards_log(self.path, "INFO", "k", "buffered")
        reg.bejson_standards_log(self.path, "ERROR", "k", "boom", error_code=182)
        self.assertEqual(len(core.bejson_standards_core_load(self.path)["Values"]), 2)

    def test_interval_flush(self):
        reg.bejson_standards_configure_sink(self.path, batch_size=100, flush_interval_seconds=0, persist=False)
        reg.bejson_standards_log(self.path, "INFO", "k", "m")
        self.assertEqual(len(core.bejson_standards_core_load(self.path)["Values"]), 1)

    def test_min_level_filters(self):
        reg.bejson_standards_configure_sink(self.path, min_level="WARN")
        self.assertFalse(reg.bejson_standards_log(self.path, "INFO", "k", "m"))
        self.assertTrue(reg.bejson_standards_log(self.path, "WARNING", "k", "m"))
        self.assertEqual(len(reg.bejson_standards_read_logs(self.path)), 1)

    def test_invalid_level_dropped_never_raises(self):
        buf = io.StringIO()
        with redirect_stderr(buf):
            self.assertFalse(reg.bejson_standards_log(self.path, "LOUD", "k", "m"))
        self.assertIn("E_STANDARDS_LOG_INVALID_LEVEL", buf.getvalue())

    def test_bad_config_raises_185(self):
        with self.assertRaises(err.StandardsLogError) as cm:
            reg.bejson_standards_configure_sink(self.path, row_cap=0)
        self.assertEqual(cm.exception.code, err.E_STANDARDS_LOG_INVALID_CONFIG)

    def test_log_never_raises_when_unwritable(self):
        blocker = os.path.join(self.tmp, "blocker")
        open(blocker, "w").close()
        bad = os.path.join(blocker, "sub", "x.bejson")            # parent is a file: makedirs fails
        buf = io.StringIO()
        with redirect_stderr(buf):
            self.assertTrue(reg.bejson_standards_log(bad, "FATAL", "k", "m"))
        self.assertIn("kept in memory", buf.getvalue())
        self.assertEqual(len(reg._get_sink(bad).buffer), 1)       # retained for retry

    def test_failed_flush_retries_then_succeeds(self):
        real = core.bejson_core_atomic_write
        core.bejson_core_atomic_write = lambda p, d: False
        try:
            with redirect_stderr(io.StringIO()):
                reg.bejson_standards_log(self.path, "ERROR", "k", "first")
        finally:
            core.bejson_core_atomic_write = real
        reg.bejson_standards_log(self.path, "ERROR", "k", "second")
        msgs = [r[val.F_EVENT_MESSAGE] for r in reg.bejson_standards_read_logs(self.path)]
        self.assertEqual(msgs, ["first", "second"])

    def test_read_filters_and_limit(self):
        reg.bejson_standards_configure_sink(self.path, min_level="DEBUG")
        reg.bejson_standards_log(self.path, "DEBUG", "k", "d", subsystem="a")
        reg.bejson_standards_log(self.path, "ERROR", "k", "e", subsystem="b")
        reg.bejson_standards_log(self.path, "WARN", "k", "w", subsystem="b")
        self.assertEqual(len(reg.bejson_standards_read_logs(self.path, min_level="WARN")), 2)
        self.assertEqual([r[val.F_EVENT_MESSAGE] for r in reg.bejson_standards_read_logs(self.path, subsystem="b")], ["e", "w"])
        self.assertEqual([r[val.F_EVENT_MESSAGE] for r in reg.bejson_standards_read_logs(self.path, limit=1)], ["w"])
        self.assertEqual(reg.bejson_standards_read_logs(os.path.join(self.tmp, "none.bejson")), [])

    def test_context_and_fields_roundtrip(self):
        reg.bejson_standards_log(self.path, "INFO", "k", "m", error_code=9, target_uuid=UUID4, user="u", n=3)
        r = reg.bejson_standards_read_logs(self.path)[0]
        self.assertEqual(json.loads(r[val.F_EVENT_CONTEXT]), {"n": 3, "user": "u"})
        self.assertEqual((r[val.F_EVENT_ERROR_CODE], r[val.F_TARGET], r[val.F_SENDER_PID]), (9, UUID4, os.getpid()))
        self.assertIsNone(r[val.F_ZSLOT])

    def test_audit_after_use_passes(self):
        for i in range(30):
            reg.bejson_standards_log(self.path, "INFO", "k", f"m{i}")
        self.assertEqual(reg.bejson_standards_audit_log_file(self.path), {"passed": True, "problems": []})

    def test_handler_bridge(self):
        h = reg.BEJSONLogHandler(self.path, subsystem="svc")
        lg = logging.getLogger("std_test.bridge")
        lg.handlers = [h]
        lg.propagate = False
        lg.setLevel(logging.DEBUG)
        lg.warning("careful %d", 1, extra={"event_key": "w.k", "error_code": 12})
        lg.critical("dead")
        try:
            raise ValueError("x")
        except ValueError:
            lg.error("caught", exc_info=True)
        rows = reg.bejson_standards_read_logs(self.path)
        self.assertEqual([r[val.F_EVENT_LEVEL] for r in rows], ["WARN", "FATAL", "ERROR"])
        self.assertEqual(rows[0][val.F_EVENT_KEY], "w.k")
        self.assertEqual(rows[0][val.F_EVENT_ERROR_CODE], 12)
        self.assertEqual(rows[0][val.F_SENDER_SUBSYSTEM], "svc")
        self.assertIn("ValueError", rows[2][val.F_EVENT_CONTEXT])
        lg.handlers = []

    def test_handler_context_keys_cannot_collide(self):
        h = reg.BEJSONLogHandler(self.path)
        lg = logging.getLogger("std_test.collide")
        lg.handlers = [h]
        lg.propagate = False
        lg.warning("x", extra={"context": {"level": "bogus", "subsystem": "z", "message": "m2"}})
        rows = reg.bejson_standards_read_logs(self.path)
        self.assertEqual(len(rows), 1)
        self.assertEqual(json.loads(rows[0][val.F_EVENT_CONTEXT])["level"], "bogus")
        lg.handlers = []

    def test_handler_ignores_own_diagnostics(self):
        h = reg.BEJSONLogHandler(self.path)
        rec = logging.LogRecord("lib_bejson_Standards_core", logging.ERROR, "f", 1, "self", None, None)
        h.emit(rec)
        self.assertEqual(reg.bejson_standards_read_logs(self.path), [])

    def test_no_print_calls_in_family(self):
        import ast
        for name in os.listdir(_STD):
            if name.endswith(".py"):
                with open(os.path.join(_STD, name), encoding="utf-8") as fh:
                    tree = ast.parse(fh.read())
                calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
                         and isinstance(n.func, ast.Name) and n.func.id == "print"]
                self.assertEqual(calls, [], name)


class TestSchemaV2(Base):
    def test_seventeen_columns_required_tier(self):
        self.assertEqual(len(val.LOG_FIELDS), 17)
        self.assertEqual(val.REQUIRED_FIELDS, {val.F_EVENT_TIMESTAMP, val.F_EVENT_LEVEL, val.F_SENDER_SUBSYSTEM,
                                                val.F_EVENT_KEY, val.F_EVENT_MESSAGE, val.F_SENDER_PID})

    def test_required_only_row_has_nulls_everywhere_else(self):
        r = core.bejson_standards_core_build_row("INFO", "s", "k", "m")
        d = dict(zip([n for n, _ in val.LOG_FIELDS], r))
        for name in val.OPTIONAL_FIELDS:
            self.assertIsNone(d[name], name)
        self.assertEqual(val.bejson_standards_validator_check_row(r), [])

    def test_all_fields_used_row_is_valid(self):
        r = core.bejson_standards_core_build_row(
            "WARN", "s", "k", "m", error_code=3, target_uuid=UUID4, context={"a": 1}, priority=2,
            category=" Net ", subject="/tmp/x", flags=["Audit", "audit", "retry"], actor="bob", session="s-1")
        d = dict(zip([n for n, _ in val.LOG_FIELDS], r))
        self.assertEqual(d[val.F_EVENT_CATEGORY], "net")
        self.assertEqual(json.loads(d[val.F_EVENT_FLAGS]), ["audit", "retry"])
        self.assertIsNone(d[val.F_EVENT_SECURE])
        self.assertEqual(val.bejson_standards_validator_check_row(r), [])

    def test_priority_validation_and_effective_default(self):
        c = val.bejson_standards_validator_check_value
        self.assertEqual(c(val.F_EVENT_PRIORITY, 1), [])
        self.assertTrue(c(val.F_EVENT_PRIORITY, 0))
        self.assertTrue(c(val.F_EVENT_PRIORITY, 5))
        self.assertTrue(c(val.F_EVENT_PRIORITY, True))
        e = val.bejson_standards_validator_effective_priority
        self.assertEqual([e("FATAL"), e("ERROR"), e("WARN"), e("INFO"), e("DEBUG")], [1, 2, 3, 4, 4])
        self.assertEqual(e("INFO", 1), 1)
        self.assertEqual(e("INFO", 9), 4)

    def test_optional_field_formats(self):
        c = val.bejson_standards_validator_check_value
        self.assertTrue(c(val.F_EVENT_CATEGORY, "Has Space"))
        self.assertTrue(c(val.F_EVENT_CATEGORY, "UPPER"))
        self.assertTrue(c(val.F_SENDER_ACTOR, "  "))
        self.assertTrue(c(val.F_SENDER_SESSION, "x" * 300))
        self.assertTrue(c(val.F_EVENT_FLAGS, "[]"))
        self.assertTrue(c(val.F_EVENT_FLAGS, '["A"]'))
        self.assertTrue(c(val.F_EVENT_FLAGS, '["a","a"]'))
        self.assertTrue(c(val.F_EVENT_FLAGS, "not json"))
        self.assertTrue(c(val.F_EVENT_SECURE, "yes"))
        self.assertEqual(c(val.F_EVENT_SECURE, True), [])
        self.assertEqual(c(val.F_EVENT_FLAGS, '["a","b"]'), [])

    def test_bad_optional_values_rejected_by_builder(self):
        for kw in ({"priority": 9}, {"category": "bad cat"}, {"flags": 5}, {"actor": " "}, {"session": 3}):
            with self.assertRaises(err.StandardsLogError) as cm:
                core.bejson_standards_core_build_row("INFO", "s", "k", "m", **kw)
            self.assertEqual(cm.exception.code, err.E_STANDARDS_LOG_SCHEMA_MISMATCH, kw)

    def test_new_error_codes(self):
        self.assertEqual((err.E_STANDARDS_LOG_SECURE_PATH_MISSING, err.E_STANDARDS_LOG_SECURE_VIOLATION), (256, 257))

    def test_schema_version_and_secure_header(self):
        core.bejson_standards_core_append_rows(self.path, [])
        doc = self.jload()
        self.assertEqual(doc[val.HDR_SCHEMA_VERSION], "3.0.0")
        self.assertIs(doc[val.HDR_IS_SECURE], False)

    def test_domain_naming_grammar(self):
        names = [n for n, _ in val.LOG_FIELDS]
        for n in names:
            self.assertRegex(n, r"^log_(%s)_[a-z0-9_]+$" % "|".join(val.ROLES), n)
        roles = [n.split("_")[1] for n in names]
        self.assertEqual(roles, sorted(roles, key=val.ROLES.index))        # event, sender, target, zspace in column order
        self.assertEqual(roles.count("event"), 11)
        self.assertEqual(roles.count("sender"), 4)
        self.assertEqual(names[-1], val.F_ZSLOT)
        self.assertEqual(val.bejson_standards_validator_check_schema_taxonomy(), [])

    def test_v2_file_migrates_by_name_not_position(self):
        names = [n for n, _ in val.LOG_FIELDS_V2]
        row = dict.fromkeys(names)
        row.update({"log_event_timestamp": "2026-10-26T00:00:00.000Z", "log_level_kind": "ERROR",
                    "log_event_priority_metric": 1, "log_subsystem_name": "db", "log_event_key": "ev",
                    "log_error_code_metric": 7, "log_event_message_text": "boom", "log_actor_name": "bob",
                    "log_session_key": "s1", "log_process_id_metric": 99, "log_event_flags_payload": '["a"]'})
        doc = {"Format": "BEJSON", "Format_Version": "104a", "Format_Creator": "Elton Boehnen",
               "Records_Type": [val.RECORDS_TYPE], "Log_Row_Cap": 77, "Log_Min_Level": "INFO",
               "Log_Schema_Version": "2.0.0", "Log_Is_Secure": False,
               "Fields": [{"name": n, "type": t} for n, t in val.LOG_FIELDS_V2], "Values": [[row[n] for n in names]]}
        self.jdump(doc)
        self.assertFalse(val.bejson_standards_validator_audit_log_file(self.path)["passed"])
        core.bejson_standards_core_append_rows(self.path, [core.bejson_standards_core_build_row("INFO", "s", "k", "new")])
        rows = core.bejson_standards_core_rows_to_dicts(core.bejson_standards_core_load(self.path))
        old = rows[0]
        self.assertEqual((old[val.F_EVENT_LEVEL], old[val.F_EVENT_PRIORITY], old[val.F_SENDER_SUBSYSTEM],
                          old[val.F_EVENT_ERROR_CODE], old[val.F_SENDER_ACTOR], old[val.F_SENDER_SESSION],
                          old[val.F_SENDER_PID], old[val.F_EVENT_MESSAGE]),
                         ("ERROR", 1, "db", 7, "bob", "s1", 99, "boom"))
        self.assertEqual(old[val.F_EVENT_FLAGS], '["a"]')
        self.assertEqual(self.jload()[val.HDR_ROW_CAP], 77)
        self.assertEqual(val.bejson_standards_validator_audit_log_file(self.path), {"passed": True, "problems": []})

    def test_v1_file_migrates_on_first_write(self):
        v1_rows = [["2026-10-20T00:00:00.000Z", "INFO", "old", "ev", 5, "hello", '{"a": 1}', 42, UUID4, None]]
        doc = {"Format": "BEJSON", "Format_Version": "104a", "Format_Creator": "Elton Boehnen",
               "Records_Type": [val.RECORDS_TYPE], "Log_Row_Cap": 50, "Log_Min_Level": "INFO",
               "Fields": [{"name": n, "type": t} for n, t in val.LOG_FIELDS_V1], "Values": v1_rows}
        self.jdump(doc)
        self.assertFalse(val.bejson_standards_validator_audit_log_file(self.path)["passed"])
        loaded = core.bejson_standards_core_load(self.path)          # read-only view is already v2
        self.assertEqual(len(loaded["Fields"]), 17)
        self.assertEqual(len(self.jload()["Fields"]), 10)            # ...but the file is untouched
        core.bejson_standards_core_append_rows(self.path, [core.bejson_standards_core_build_row("INFO", "s", "k", "new")])
        rows = core.bejson_standards_core_rows_to_dicts(core.bejson_standards_core_load(self.path))
        self.assertEqual([r[val.F_EVENT_MESSAGE] for r in rows], ["hello", "new"])
        self.assertEqual((rows[0][val.F_EVENT_ERROR_CODE], rows[0][val.F_SENDER_PID], rows[0][val.F_TARGET]), (5, 42, UUID4))
        self.assertIsNone(rows[0][val.F_EVENT_PRIORITY])
        self.assertEqual(self.jload()[val.HDR_ROW_CAP], 50)
        self.assertEqual(val.bejson_standards_validator_audit_log_file(self.path), {"passed": True, "problems": []})


class TestPriorityAndFilters(Base):
    def test_defaults_applied_from_sink(self):
        reg.bejson_standards_configure_sink(self.path, default_category="Ops", default_actor="svc",
                                            default_session="run-1", persist=False)
        reg.bejson_standards_log(self.path, "INFO", "k", "m")
        reg.bejson_standards_log(self.path, "INFO", "k", "m2", category="db", actor="bob")
        a, b = reg.bejson_standards_read_logs(self.path)
        self.assertEqual((a[val.F_EVENT_CATEGORY], a[val.F_SENDER_ACTOR], a[val.F_SENDER_SESSION]), ("ops", "svc", "run-1"))
        self.assertEqual((b[val.F_EVENT_CATEGORY], b[val.F_SENDER_ACTOR]), ("db", "bob"))

    def test_filters(self):
        reg.bejson_standards_configure_sink(self.path, min_level="DEBUG", persist=False)
        reg.bejson_standards_log(self.path, "INFO", "a", "1", category="net", actor="x", flags=["audit"])
        reg.bejson_standards_log(self.path, "INFO", "b", "2", category="db", actor="y", priority=1)
        reg.bejson_standards_log(self.path, "FATAL", "c", "3", category="net", actor="y")
        keys = lambda **kw: [r[val.F_EVENT_KEY] for r in reg.bejson_standards_read_logs(self.path, **kw)]   # noqa: E731
        self.assertEqual(keys(category="NET"), ["a", "c"])
        self.assertEqual(keys(actor="y"), ["b", "c"])
        self.assertEqual(keys(flag="Audit"), ["a"])
        self.assertEqual(keys(max_priority=1), ["b", "c"])          # explicit 1, and FATAL's level default 1
        self.assertEqual(keys(max_priority=3), ["b", "c"])          # INFO without priority defaults to 4
        self.assertEqual(keys(category="net", actor="y"), ["c"])

    def test_invalid_optional_dropped_not_raised(self):
        with redirect_stderr(io.StringIO()) as buf:
            self.assertFalse(reg.bejson_standards_log(self.path, "INFO", "k", "m", priority=9))
        self.assertIn("E_STANDARDS_LOG_SCHEMA_MISMATCH", buf.getvalue())

    def test_handler_extras_map_to_new_fields(self):
        h = reg.BEJSONLogHandler(self.path, subsystem="svc")
        lg = logging.getLogger("std_test.extras")
        lg.handlers = [h]
        lg.propagate = False
        lg.warning("x", extra={"priority": 1, "category": "Auth", "subject": "u1", "flags": ["Audit"],
                               "actor": "bob", "session": "s9"})
        r = reg.bejson_standards_read_logs(self.path)[0]
        self.assertEqual((r[val.F_EVENT_PRIORITY], r[val.F_EVENT_CATEGORY], r[val.F_EVENT_SUBJECT], r[val.F_SENDER_ACTOR], r[val.F_SENDER_SESSION]),
                         (1, "auth", "u1", "bob", "s9"))
        self.assertEqual(json.loads(r[val.F_EVENT_FLAGS]), ["audit"])
        lg.handlers = []


class TestSecure(Base):
    def setUp(self):
        super().setUp()
        self.spath = os.path.join(self.tmp, "vault", "secure.bejson")

    def cfg(self, **kw):
        args = dict(secure_path=self.spath, batch_size=100, flush_interval_seconds=3600)
        args.update(kw)
        return reg.bejson_standards_configure_sink(self.path, **args)

    def test_secure_without_path_fails_closed(self):
        reg.bejson_standards_configure_sink(self.path, persist=False)
        with redirect_stderr(io.StringIO()) as buf:
            self.assertFalse(reg.bejson_standards_log(self.path, "ERROR", "k", "secret", secure=True))
        self.assertIn("E_STANDARDS_LOG_SECURE_PATH_MISSING", buf.getvalue())
        self.assertEqual(reg.bejson_standards_read_logs(self.path), [])
        self.assertFalse(os.path.exists(self.path))                       # nothing leaked into the main log

    def test_secure_routing_and_placeholder(self):
        self.cfg()
        reg.bejson_standards_log(self.path, "INFO", "plain", "visible")
        reg.bejson_standards_log(self.path, "ERROR", "tok.rotate", "key is hunter2", secure=True,
                                 category="auth", actor="bob", subject="acct", priority=1, secret="s3cr3t")
        main = reg.bejson_standards_read_logs(self.path)
        self.assertEqual([r[val.F_EVENT_KEY] for r in main], ["plain", "tok.rotate"])
        ph = main[1]
        self.assertEqual(ph[val.F_EVENT_MESSAGE], val.REDACTED_MESSAGE)
        self.assertEqual(json.loads(ph[val.F_EVENT_FLAGS]), [val.REDACTED_FLAG])
        for name in (val.F_EVENT_CONTEXT, val.F_EVENT_CATEGORY, val.F_SENDER_ACTOR, val.F_EVENT_SUBJECT, val.F_EVENT_ERROR_CODE, val.F_EVENT_SECURE):
            self.assertIsNone(ph[name], name)
        with open(self.path, encoding="utf-8") as fh:
            main_text = fh.read()
        for leaked in ("hunter2", "s3cr3t", "bob", "acct"):
            self.assertNotIn(leaked, main_text)
        sec = reg.bejson_standards_read_logs(self.path, secure=True)
        self.assertEqual(len(sec), 1)
        self.assertEqual((sec[0][val.F_EVENT_MESSAGE], sec[0][val.F_EVENT_SECURE], sec[0][val.F_SENDER_ACTOR]), ("key is hunter2", True, "bob"))
        self.assertEqual(json.loads(sec[0][val.F_EVENT_CONTEXT]), {"secret": "s3cr3t"})

    def test_placeholder_can_be_disabled(self):
        self.cfg(secure_placeholder=False)
        reg.bejson_standards_log(self.path, "ERROR", "k", "m", secure=True)
        self.assertEqual(reg.bejson_standards_read_logs(self.path), [])
        self.assertEqual(len(reg.bejson_standards_read_logs(self.path, secure=True)), 1)

    def test_secure_file_permissions(self):
        self.cfg()
        reg.bejson_standards_log(self.path, "ERROR", "k", "m", secure=True)
        self.assertEqual(os.stat(self.spath).st_mode & 0o777, 0o600)
        self.assertEqual(os.stat(os.path.dirname(self.spath)).st_mode & 0o777, 0o700)

    def test_secure_has_own_row_cap(self):
        self.cfg(row_cap=100, secure_row_cap=2)
        for i in range(5):
            reg.bejson_standards_log(self.path, "ERROR", "k", f"m{i}", secure=True)
        self.assertEqual([r[val.F_EVENT_MESSAGE] for r in reg.bejson_standards_read_logs(self.path, secure=True)], ["m3", "m4"])
        self.assertEqual(len(reg.bejson_standards_read_logs(self.path)), 5)

    def test_audits_enforce_file_kind(self):
        self.cfg()
        reg.bejson_standards_log(self.path, "ERROR", "k", "m", secure=True)
        reg.bejson_standards_log(self.path, "INFO", "k", "plain")
        self.assertEqual(reg.bejson_standards_audit_log_file(self.path), {"passed": True, "problems": []})
        self.assertEqual(reg.bejson_standards_audit_log_file(self.path, secure=True), {"passed": True, "problems": []})
        # tamper: a secure row appears in the main log
        main = self.jload()
        idx = [n for n, _ in val.LOG_FIELDS].index(val.F_EVENT_SECURE)
        main["Values"][0][idx] = True
        self.jdump(main)
        self.assertTrue(any("E_STANDARDS_LOG_SECURE_VIOLATION" in p
                            for p in val.bejson_standards_validator_audit_log_file(self.path)["problems"]))
        # tamper: a non-secure row appears in the secure log
        with open(self.spath, encoding="utf-8") as fh:
            sec = json.load(fh)
        sec["Values"][0][idx] = None
        with open(self.spath, "w", encoding="utf-8") as fh:
            json.dump(sec, fh)
        self.assertTrue(any("non-secure row in a secure log" in p
                            for p in val.bejson_standards_validator_audit_log_file(self.spath)["problems"]))

    def test_main_read_never_returns_secure_rows(self):
        self.cfg()
        reg.bejson_standards_log(self.path, "INFO", "k", "plain")
        reg.bejson_standards_flush(self.path)
        main = self.jload()
        row = list(main["Values"][0])
        row[[n for n, _ in val.LOG_FIELDS].index(val.F_EVENT_SECURE)] = True
        main["Values"].append(row)
        self.jdump(main)
        reg._SINKS.clear()
        self.assertEqual(len(reg.bejson_standards_read_logs(self.path)), 1)

    def test_engine_refuses_kind_mixing(self):
        srow = core.bejson_standards_core_build_row("ERROR", "s", "k", "m", secure=True)
        nrow = core.bejson_standards_core_build_row("ERROR", "s", "k", "m")
        with self.assertRaises(err.StandardsLogError) as cm:
            core.bejson_standards_core_append_rows(self.path, [srow])
        self.assertEqual(cm.exception.code, err.E_STANDARDS_LOG_SECURE_VIOLATION)
        with self.assertRaises(err.StandardsLogError) as cm:
            core.bejson_standards_core_append_rows(self.spath, [nrow], secure=True)
        self.assertEqual(cm.exception.code, err.E_STANDARDS_LOG_SECURE_VIOLATION)
        core.bejson_standards_core_append_rows(self.path, [nrow])
        with self.assertRaises(err.StandardsLogError) as cm:                # opening a normal file as secure
            core.bejson_standards_core_append_rows(self.path, [srow], secure=True)
        self.assertEqual(cm.exception.code, err.E_STANDARDS_LOG_SECURE_VIOLATION)

    def test_config_rejects_same_path_and_path_reuse(self):
        with self.assertRaises(err.StandardsLogError) as cm:
            reg.bejson_standards_configure_sink(self.path, secure_path=self.path)
        self.assertEqual(cm.exception.code, err.E_STANDARDS_LOG_INVALID_CONFIG)
        self.cfg()
        other = os.path.join(self.tmp, "other.bejson")
        with self.assertRaises(err.StandardsLogError) as cm:                # a secure path cannot become a main log
            reg.bejson_standards_configure_sink(other, secure_path=self.path)
            reg.bejson_standards_configure_sink(self.spath)
        self.assertEqual(cm.exception.code, err.E_STANDARDS_LOG_SECURE_VIOLATION)

    def test_secure_read_without_path_returns_empty(self):
        reg.bejson_standards_configure_sink(self.path, persist=False)
        with redirect_stderr(io.StringIO()):
            self.assertEqual(reg.bejson_standards_read_logs(self.path, secure=True), [])
            self.assertFalse(reg.bejson_standards_audit_log_file(self.path, secure=True)["passed"])

    def test_flush_covers_both_files(self):
        self.cfg()
        reg.bejson_standards_log(self.path, "INFO", "k", "m", secure=True)      # INFO: buffered in both sinks
        self.assertFalse(os.path.exists(self.spath) and bool(self.sec_rows()))
        self.assertTrue(reg.bejson_standards_flush(self.path))
        self.assertEqual(len(self.sec_rows()), 1)
        self.assertEqual(len(core.bejson_standards_core_load(self.path)["Values"]), 1)

    def sec_rows(self):
        doc = core.bejson_standards_core_load(self.spath)
        return doc["Values"] if doc else []


def T(y, m, d, h=0, mi=0):
    return datetime(y, m, d, h, mi, tzinfo=timezone.utc)


def iso(dt):
    return dt.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def mkrow(ts, msg="m", level="INFO", **kw):
    return core.bejson_standards_core_build_row(level, kw.pop("subsystem", "s"), kw.pop("event_key", "k"), msg,
                                                timestamp=ts if isinstance(ts, str) else iso(ts), **kw)


def mkdict(*a, **kw):
    return dict(zip([n for n, _ in val.LOG_FIELDS], mkrow(*a, **kw)))


class ClockBase(Base):
    def setUp(self):
        super().setUp()
        self._real_now = core.bejson_standards_core_now
        self.arch = os.path.join(self.tmp, "arch")

    def tearDown(self):
        core.bejson_standards_core_now = self._real_now
        super().tearDown()

    def at(self, dt):
        core.bejson_standards_core_now = lambda: dt

    def arch_rows(self, key, stem="app"):
        doc = core.bejson_standards_core_load(os.path.join(self.arch, f"{stem}-{key}.bejson"))
        return core.bejson_standards_core_rows_to_dicts(doc) if doc else []


class TestPeriodsAndCodes(unittest.TestCase):
    def test_new_codes(self):
        self.assertEqual((err.E_STANDARDS_EXPORT_FORMAT_INVALID, err.E_STANDARDS_EXPORT_FAILED,
                          err.E_STANDARDS_ARCHIVE_FAILED, err.E_STANDARDS_EXPORT_SECURE_DESTINATION), (258, 259, 260, 261))
        self.assertTrue(all(250 <= c <= 269 for c in err.ERROR_NAMES))

    def test_period_keys_and_starts(self):
        k, st = val.bejson_standards_validator_period_key, val.bejson_standards_validator_period_start
        self.assertEqual([k(T(2026, 10, 27, 10), p) for p in val.PERIODS], ["2026-10-27", "2026-W44", "2026-10"])
        self.assertEqual(k(T(2026, 12, 31, 23, 59), "weekly"), "2026-W53")
        self.assertEqual(k(T(2027, 1, 1), "weekly"), "2026-W53")           # ISO year differs from calendar year
        self.assertEqual(st(T(2026, 10, 27, 10), "weekly"), T(2026, 10, 26))
        self.assertEqual(st(T(2026, 10, 27, 10), "monthly"), T(2026, 10, 1))
        self.assertEqual(st(T(2026, 10, 27, 10), "daily"), T(2026, 10, 27))
        with self.assertRaises(ValueError):
            st(T(2026, 1, 1), "hourly")

    def test_parse_time(self):
        p = val.bejson_standards_validator_parse_time
        self.assertEqual(p("2026-10-27T10:00:00Z"), T(2026, 10, 27, 10))
        self.assertEqual(p(datetime(2026, 10, 27, 10)), T(2026, 10, 27, 10))        # naive = UTC
        self.assertIsNone(p("nope"))
        self.assertIsNone(p(5))

    def test_option_checks(self):
        c = val.bejson_standards_validator_check_archive_config
        self.assertEqual(c("d", "daily", 2), [])
        self.assertTrue(c("d", None))
        self.assertTrue(c(None, "daily"))
        self.assertTrue(c("d", "hourly"))
        self.assertTrue(c("d", "daily", 0))
        self.assertTrue(c(None, None, 3))
        o = val.bejson_standards_validator_check_export_options
        self.assertEqual(o("html", "priority", "dark"), [])
        self.assertEqual(len(o("pdf", "x", "blue")), 3)


class TestFilters(Base):
    def seed(self):
        rows = [mkrow(T(2026, 10, 25, 10), "a", event_key="e1", session="s1", pid=11, subsystem="db"),
                mkrow(T(2026, 10, 26, 10), "b", event_key="e2", session="s2", pid=22, level="ERROR", category="net"),
                mkrow(T(2026, 10, 27, 10), "c", event_key="e1", session="s1", pid=22, flags=["audit"], actor="bob")]
        core.bejson_standards_core_append_rows(self.path, rows)

    def msgs(self, **kw):
        return [r[val.F_EVENT_MESSAGE] for r in reg.bejson_standards_read_logs(self.path, **kw)]

    def test_time_window_inclusive_exclusive(self):
        self.seed()
        self.assertEqual(self.msgs(since="2026-10-26T10:00:00Z"), ["b", "c"])
        self.assertEqual(self.msgs(until="2026-10-26T10:00:00Z"), ["a"])
        self.assertEqual(self.msgs(since=T(2026, 10, 26), until=T(2026, 10, 27)), ["b"])

    def test_sender_and_event_filters(self):
        self.seed()
        self.assertEqual(self.msgs(session="s1"), ["a", "c"])
        self.assertEqual(self.msgs(process_id=22), ["b", "c"])
        self.assertEqual(self.msgs(event_key="e1"), ["a", "c"])
        self.assertEqual(self.msgs(subsystem="db"), ["a"])
        self.assertEqual(self.msgs(actor="bob", flag="AUDIT"), ["c"])
        self.assertEqual(self.msgs(session="s1", process_id=22, since="2026-10-27T00:00:00Z"), ["c"])

    def test_invalid_filters(self):
        self.seed()
        with redirect_stderr(io.StringIO()):
            self.assertEqual(reg.bejson_standards_read_logs(self.path, since="soon"), [])
            self.assertEqual(reg.bejson_standards_read_logs(self.path, max_priority=9), [])
        with self.assertRaises(err.StandardsLogError) as cm:
            export.bejson_standards_export_filter_rows([], max_priority=0)          # raises at call time, not lazily
        self.assertEqual(cm.exception.code, err.E_STANDARDS_EXPORT_FORMAT_INVALID)
        with self.assertRaises(err.StandardsLogError):
            export.bejson_standards_export_filter_rows([], process_id="x")
        with self.assertRaises(err.StandardsLogError):
            export.bejson_standards_export_filter_rows([], min_level="LOUD")

    def test_secure_rows_dropped_unless_asked(self):
        rows = [mkdict(T(2026, 10, 27), "pub"), mkdict(T(2026, 10, 27), "sec", secure=True)]
        self.assertEqual([r[val.F_EVENT_MESSAGE] for r in export.bejson_standards_export_filter_rows(rows)], ["pub"])
        self.assertEqual(len(list(export.bejson_standards_export_filter_rows(rows, include_secure_rows=True))), 2)


class TestExport(Base):
    def seed(self):
        reg.bejson_standards_configure_sink(self.path, min_level="DEBUG", persist=False)
        reg.bejson_standards_log(self.path, "INFO", "login", "a | b\nline2 <script>alert(1)</script> `x` [l](u)",
                                 category="net", actor="bob", flags=["audit"], token="t")
        reg.bejson_standards_log(self.path, "ERROR", "boom", "failed", priority=1, session="s1", subsystem="db")
        reg.bejson_standards_log(self.path, "DEBUG", "tick", "noise")

    def export(self, fmt="json", **kw):
        res = reg.bejson_standards_export_logs(self.path, fmt, **kw)
        self.assertTrue(res["ok"], res)
        return res

    def test_json_default_is_a_valid_array_with_context(self):
        self.seed()
        res = self.export()
        data = json.loads(res["text"])
        self.assertEqual((res["rows"], len(data)), (3, 3))
        self.assertEqual(json.loads(data[0][val.F_EVENT_CONTEXT]), {"token": "t"})
        self.assertEqual(json.loads(self.export(min_level="ERROR")["text"])[0][val.F_EVENT_KEY], "boom")

    def test_json_empty_and_ndjson(self):
        self.seed()
        self.assertEqual(json.loads(self.export(subsystem="none")["text"]), [])
        lines = self.export("ndjson")["text"].splitlines()
        self.assertEqual(len(lines), 3)
        self.assertTrue(all(isinstance(json.loads(x), dict) for x in lines))

    def test_markdown_escaping(self):
        self.seed()
        text = self.export("markdown", category="net")["text"]
        self.assertIn("| Time (UTC) | Level | Pri | Sender | Category | Event | Message |", text)
        self.assertNotIn("<script>", text)
        self.assertIn("&lt;script&gt;", text)
        self.assertIn("a \\| b line2", text)                      # pipe escaped, newline flattened
        self.assertIn("\\`x\\`", text)
        self.assertIn("\\[l\\]", text)
        self.assertNotIn("Context", text)                          # context off by default for markdown
        self.assertIn("Filters: category=net", text)

    def test_markdown_empty(self):
        self.seed()
        self.assertIn("_No entries._", self.export("markdown", subsystem="none")["text"])

    def test_html_is_inert_and_complete(self):
        self.seed()
        text = self.export("html", title="T <b>x</b>")["text"]
        seen = []

        class P(HTMLParser):
            def handle_starttag(self, tag, attrs):
                seen.append((tag, dict(attrs)))
        P().feed(text)
        tags = {t for t, _ in seen}
        self.assertFalse(tags & {"script", "iframe", "img", "a", "link", "object", "form"}, tags)
        self.assertTrue(any(t == "meta" and "default-src 'none'" in (a.get("content") or "") for t, a in seen))
        self.assertTrue(any(t == "meta" and a.get("name") == "viewport" for t, a in seen))
        self.assertIn("&lt;script&gt;", text)
        self.assertIn("&lt;b&gt;x&lt;/b&gt;", text)
        self.assertIn('class="hot"', text)                          # the ERROR row
        self.assertIn("boehnenelton2024@gmail.com", text)
        self.assertIn("#DE2626", text)
        self.assertNotIn("--bg:#000000", text)
        self.assertIn("--bg:#000000", self.export("html", theme="dark")["text"])

    def test_context_default_per_format_and_override(self):
        self.seed()
        self.assertNotIn(val.F_EVENT_CONTEXT, json.loads(self.export(include_context=False)["text"])[0])
        self.assertIn("Context", self.export("markdown", include_context=True)["text"])
        self.assertNotIn("Context</th>", self.export("html")["text"])
        self.assertIn("Context</th>", self.export("html", include_context=True)["text"])

    def test_sort_priority_and_limit(self):
        self.seed()
        keys = [r[val.F_EVENT_KEY] for r in json.loads(self.export(sort="priority")["text"])]
        self.assertEqual(keys[0], "boom")                           # explicit priority 1 first
        self.assertEqual([r[val.F_EVENT_KEY] for r in json.loads(self.export(limit=1)["text"])], ["tick"])
        self.assertEqual(self.export(limit=2)["rows"], 2)

    def test_by_sender_flag_and_priority(self):
        self.seed()
        self.assertEqual([r[val.F_EVENT_KEY] for r in json.loads(self.export(actor="bob")["text"])], ["login"])
        self.assertEqual([r[val.F_EVENT_KEY] for r in json.loads(self.export(flag="audit")["text"])], ["login"])
        self.assertEqual([r[val.F_EVENT_KEY] for r in json.loads(self.export(max_priority=1)["text"])], ["boom"])
        self.assertEqual([r[val.F_EVENT_KEY] for r in json.loads(self.export(session="s1")["text"])], ["boom"])

    def test_dest_stream_and_path(self):
        self.seed()
        buf = io.StringIO()
        res = self.export(dest=buf)
        self.assertEqual((res["dest"], res["text"]), ("stream", None))
        self.assertEqual(len(json.loads(buf.getvalue())), 3)
        out = os.path.join(self.tmp, "exports", "log.html")
        res = self.export("html", dest=out)
        self.assertEqual(res["dest"], os.path.abspath(out))
        with open(out, encoding="utf-8") as fh:
            self.assertIn("<table>", fh.read())
        self.assertFalse([n for n in os.listdir(os.path.dirname(out)) if ".tmp-" in n])

    def test_overwrite_rules(self):
        self.seed()
        out = os.path.join(self.tmp, "x.json")
        self.export(dest=out)
        with redirect_stderr(io.StringIO()):
            res = reg.bejson_standards_export_logs(self.path, "json", dest=out, overwrite=False)
        self.assertEqual((res["ok"], res["code"]), (False, err.E_STANDARDS_EXPORT_FAILED))
        self.assertTrue(self.export(dest=out)["ok"])               # default overwrite=True replaces atomically

    def test_never_overwrites_a_registered_log(self):
        self.seed()
        reg.bejson_standards_flush(self.path)
        with open(self.path, "rb") as fh:
            before = fh.read()
        with redirect_stderr(io.StringIO()):
            res = reg.bejson_standards_export_logs(self.path, "json", dest=self.path)
        self.assertEqual((res["ok"], res["code"]), (False, err.E_STANDARDS_EXPORT_FAILED))
        with open(self.path, "rb") as fh:
            self.assertEqual(fh.read(), before)

    def test_bad_options_return_error_dicts(self):
        self.seed()
        with redirect_stderr(io.StringIO()):
            for kw in ({"fmt": "pdf"}, {"sort": "x"}, {"theme": "blue"}, {"limit": 0}, {"bogus": 1}, {"max_priority": 9}):
                fmt = kw.pop("fmt", "json")
                res = reg.bejson_standards_export_logs(self.path, fmt, **kw)
                self.assertEqual((res["ok"], res["code"]), (False, err.E_STANDARDS_EXPORT_FORMAT_INVALID), kw)

    def test_json_streams_without_materialising(self):
        calls = []

        def gen():
            for i in range(3):
                calls.append(i)
                yield mkdict(T(2026, 10, 27), f"m{i}")

        class Spy(io.StringIO):
            def write(self, s):
                self.seen = getattr(self, "seen", []) + [len(calls)]
                return super().write(s)
        spy = Spy()
        export.bejson_standards_export_render(gen(), "json", spy)
        self.assertEqual(len(calls), 3)
        self.assertGreater(len(set(spy.seen)), 1)                   # output began before the generator was drained


class TestExportSecure(Base):
    def setUp(self):
        super().setUp()
        self.spath = os.path.join(self.tmp, "vault", "secure.bejson")
        self.arch = os.path.join(self.tmp, "arch")
        reg.bejson_standards_configure_sink(self.path, secure_path=self.spath, archive_dir=self.arch,
                                            archive_period="daily", batch_size=100, flush_interval_seconds=3600)
        reg.bejson_standards_log(self.path, "ERROR", "tok", "hunter2 leaked", secure=True, secret="s3cr3t", actor="bob")
        reg.bejson_standards_log(self.path, "INFO", "plain", "visible")

    def test_secure_export_file_mode_and_context_default(self):
        out = os.path.join(self.tmp, "sec_out", "s.html")
        res = reg.bejson_standards_export_logs(self.path, "html", out, secure=True)
        self.assertTrue(res["ok"], res)
        self.assertEqual(os.stat(out).st_mode & 0o777, 0o600)
        self.assertEqual(os.stat(os.path.dirname(out)).st_mode & 0o777, 0o700)
        with open(out, encoding="utf-8") as fh:
            body = fh.read()
        self.assertIn("hunter2 leaked", body)
        self.assertNotIn("s3cr3t", body)                            # context omitted by default
        res = reg.bejson_standards_export_logs(self.path, "markdown", secure=True, include_context=True)
        self.assertIn("s3cr3t", res["text"])

    def test_secure_destination_rules(self):
        with redirect_stderr(io.StringIO()):
            for dest in (self.path, os.path.join(self.arch, "x.json"), self.arch):
                res = reg.bejson_standards_export_logs(self.path, "json", dest, secure=True)
                self.assertEqual((res["ok"], res["code"]), (False, err.E_STANDARDS_EXPORT_SECURE_DESTINATION), dest)

    def test_secure_export_without_secure_path(self):
        reg.bejson_standards_configure_sink(self.path, persist=False)
        with redirect_stderr(io.StringIO()):
            res = reg.bejson_standards_export_logs(self.path, "json", secure=True)
        self.assertEqual((res["ok"], res["code"]), (False, err.E_STANDARDS_LOG_SECURE_PATH_MISSING))

    def test_main_export_carries_only_the_placeholder(self):
        text = reg.bejson_standards_export_logs(self.path, "json", include_context=True)["text"]
        for leaked in ("hunter2", "s3cr3t", "bob"):
            self.assertNotIn(leaked, text)
        self.assertEqual(len(json.loads(text)), 2)                  # placeholder + the plain entry


class TestArchiveCore(ClockBase):
    def write(self, rows, **kw):
        return core.bejson_standards_core_append_rows(os.path.join(self.tmp, "app.bejson"), rows, **kw)

    @property
    def live(self):
        return os.path.join(self.tmp, "app.bejson")

    def test_moves_only_closed_periods_and_is_idempotent(self):
        self.write([mkrow(T(2026, 10, 25, 9), "a"), mkrow(T(2026, 10, 26, 9), "b"), mkrow(T(2026, 10, 27, 9), "c")])
        r = core.bejson_standards_core_archive_closed_periods(self.live, self.arch, "daily", now=T(2026, 10, 27, 12))
        self.assertEqual((r["moved"], r["remaining"], len(r["files"])), (2, 1, 2))
        self.assertEqual([x[val.F_EVENT_MESSAGE] for x in self.arch_rows("2026-10-25")], ["a"])
        self.assertEqual([x[val.F_EVENT_MESSAGE] for x in self.arch_rows("2026-10-26")], ["b"])
        self.assertEqual([x[val.F_EVENT_MESSAGE] for x in core.bejson_standards_core_rows_to_dicts(core.bejson_standards_core_load(self.live))], ["c"])
        again = core.bejson_standards_core_archive_closed_periods(self.live, self.arch, "daily", now=T(2026, 10, 27, 12))
        self.assertEqual(again["moved"], 0)
        for f in r["files"] + [self.live]:
            self.assertEqual(val.bejson_standards_validator_audit_log_file(f), {"passed": True, "problems": []}, f)

    def test_weekly_and_monthly_grouping(self):
        self.write([mkrow(T(2026, 10, 5), "w1"), mkrow(T(2026, 10, 14), "w2"), mkrow(T(2026, 9, 30), "sep")])
        r = core.bejson_standards_core_archive_closed_periods(self.live, self.arch, "weekly", now=T(2026, 10, 27))
        self.assertEqual(sorted(os.path.basename(f) for f in r["files"]), ["app-2026-W40.bejson", "app-2026-W41.bejson", "app-2026-W42.bejson"])
        self.write([mkrow(T(2026, 9, 3), "s1"), mkrow(T(2026, 9, 4), "s2")])
        core.bejson_standards_core_archive_closed_periods(self.live, self.arch, "monthly", now=T(2026, 10, 27))
        self.assertEqual(len(self.arch_rows("2026-09")), 2)

    def test_archive_header_and_cap_exemption(self):
        self.write([mkrow(T(2026, 10, 1), "a")])
        r = core.bejson_standards_core_archive_closed_periods(self.live, self.arch, "daily", now=T(2026, 10, 2))
        with open(r["files"][0], encoding="utf-8") as fh:
            doc = json.load(fh)
        self.assertIs(doc[val.HDR_IS_ARCHIVE], True)
        self.assertEqual(doc[val.HDR_ARCHIVE_PERIOD_KEY], "2026-10-01")
        self.assertNotIn(val.HDR_ROW_CAP, doc)
        doc[val.HDR_ROW_CAP] = 1
        doc["Values"] = doc["Values"] * 3
        with open(r["files"][0], "w", encoding="utf-8") as fh:
            json.dump(doc, fh)
        self.assertTrue(val.bejson_standards_validator_audit_log_file(r["files"][0])["passed"])    # archives are not row-capped

    def test_retry_after_crash_does_not_duplicate(self):
        rows = [mkrow(T(2026, 10, 25), "a"), mkrow(T(2026, 10, 26), "b")]
        self.write(rows)
        core.bejson_standards_core_write_archive_rows(self.arch, "app", rows[:1], "daily")     # archive written, live commit "crashed"
        core.bejson_standards_core_archive_closed_periods(self.live, self.arch, "daily", now=T(2026, 10, 27))
        self.assertEqual(len(self.arch_rows("2026-10-25")), 1)
        self.assertEqual(len(self.arch_rows("2026-10-26")), 1)

    def test_archive_failure_leaves_live_untouched(self):
        self.write([mkrow(T(2026, 10, 25), "a")])
        with open(self.live, "rb") as fh:
            before = fh.read()
        blocker = os.path.join(self.tmp, "blocker")
        open(blocker, "w").close()
        with self.assertRaises(err.StandardsLogError) as cm:
            core.bejson_standards_core_archive_closed_periods(self.live, os.path.join(blocker, "sub"), "daily", now=T(2026, 10, 27))
        self.assertEqual(cm.exception.code, err.E_STANDARDS_ARCHIVE_FAILED)
        with open(self.live, "rb") as fh:
            self.assertEqual(fh.read(), before)

    def test_foreign_file_at_archive_path_refused(self):
        os.makedirs(self.arch)
        foreign = os.path.join(self.arch, "app-2026-10-25.bejson")
        with open(foreign, "w") as fh:
            json.dump({"Format": "BEJSON", "Format_Version": "104a", "Records_Type": ["Other"], "Fields": [], "Values": []}, fh)
        self.write([mkrow(T(2026, 10, 25), "a")])
        with self.assertRaises(err.StandardsLogError) as cm:
            core.bejson_standards_core_archive_closed_periods(self.live, self.arch, "daily", now=T(2026, 10, 27))
        self.assertEqual(cm.exception.code, err.E_STANDARDS_ARCHIVE_FAILED)
        self.assertEqual(len(core.bejson_standards_core_load(self.live)["Values"]), 1)

    def test_overflow_goes_to_archive_before_trim(self):
        self.write([mkrow(T(2026, 10, 27, i), f"m{i}") for i in range(5)], row_cap=2, archive_dir=self.arch, archive_period="daily")
        self.assertEqual([x[val.F_EVENT_MESSAGE] for x in self.arch_rows("2026-10-27")], ["m0", "m1", "m2"])
        self.assertEqual(len(core.bejson_standards_core_load(self.live)["Values"]), 2)

    def test_overflow_archive_failure_aborts_the_write(self):
        self.write([mkrow(T(2026, 10, 27), "keep")], row_cap=2)
        blocker = os.path.join(self.tmp, "blocker")
        open(blocker, "w").close()
        with self.assertRaises(err.StandardsLogError) as cm:
            self.write([mkrow(T(2026, 10, 27), "x"), mkrow(T(2026, 10, 27), "y")], archive_dir=os.path.join(blocker, "a"), archive_period="daily")
        self.assertEqual(cm.exception.code, err.E_STANDARDS_ARCHIVE_FAILED)
        self.assertEqual([x[val.F_EVENT_MESSAGE] for x in core.bejson_standards_core_rows_to_dicts(core.bejson_standards_core_load(self.live))], ["keep"])

    def test_list_and_prune_only_verified_archives(self):
        for mth in (6, 7, 8, 9):
            core.bejson_standards_core_write_archive_rows(self.arch, "app", [mkrow(T(2026, mth, 10), f"m{mth}")], "monthly")
        look_alike = os.path.join(self.arch, "app-2026-05.bejson")          # right name, no archive header: not ours
        with open(look_alike, "w") as fh:
            fh.write("{}")
        keys = [k for k, _ in core.bejson_standards_core_list_archives(self.arch, "app", "monthly")]
        self.assertEqual(keys, ["2026-05", "2026-06", "2026-07", "2026-08", "2026-09"])
        deleted = core.bejson_standards_core_prune_archives(self.arch, "app", 2, "monthly")
        self.assertEqual(sorted(os.path.basename(d) for d in deleted), ["app-2026-06.bejson", "app-2026-07.bejson"])
        self.assertTrue(os.path.exists(look_alike))
        self.assertEqual(core.bejson_standards_core_prune_archives(self.arch, "app", 5, "monthly"), [])

    def test_secure_archive_kind_and_permissions(self):
        srow = mkrow(T(2026, 10, 25), "s", secure=True)
        files = core.bejson_standards_core_write_archive_rows(os.path.join(self.tmp, "vault_arch"), "sec", [srow], "daily", secure=True)
        (path,) = files
        self.assertEqual(os.stat(path).st_mode & 0o777, 0o600)
        self.assertEqual(os.stat(os.path.dirname(path)).st_mode & 0o777, 0o700)
        self.assertTrue(val.bejson_standards_validator_audit_log_file(path)["passed"])
        with self.assertRaises(err.StandardsLogError) as cm:                  # a non-secure row can't enter a secure archive
            core.bejson_standards_core_write_archive_rows(os.path.join(self.tmp, "vault_arch"), "sec", [mkrow(T(2026, 10, 25), "n")], "daily", secure=True)
        self.assertEqual(cm.exception.code, err.E_STANDARDS_LOG_SECURE_VIOLATION)
        with self.assertRaises(err.StandardsLogError):                        # nor a secure row into a normal archive
            core.bejson_standards_core_write_archive_rows(self.arch, "app", [srow], "daily")


class TestArchiveRegistry(ClockBase):
    def cfg(self, **kw):
        args = dict(archive_dir=self.arch, archive_period="daily", batch_size=100, flush_interval_seconds=3600, persist=False)
        args.update(kw)
        reg.bejson_standards_configure_sink(self.live, **args)

    @property
    def live(self):
        return os.path.join(self.tmp, "app.bejson")

    def test_config_validation(self):
        bad = ({"archive_period": "daily"}, {"archive_dir": "x"}, {"archive_dir": "x", "archive_period": "hourly"},
               {"archive_dir": "x", "archive_period": "daily", "archive_keep_periods": 0},
               {"secure_archive_dir": "y"},
               {"secure_path": "/tmp/_s.bejson", "secure_archive_dir": "y"},
               {"secure_path": "/tmp/_s.bejson", "archive_dir": os.path.join("a"), "archive_period": "daily",
                "secure_archive_dir": os.path.join("a", "inner")})
        for kw in bad:
            with self.assertRaises(err.StandardsLogError, msg=kw) as cm:
                reg.bejson_standards_configure_sink(self.live, persist=False, **kw)
            self.assertEqual(cm.exception.code, err.E_STANDARDS_LOG_INVALID_CONFIG, kw)

    def test_auto_archive_on_period_change(self):
        self.cfg()
        self.at(T(2026, 10, 26, 12))
        for i in range(3):
            reg.bejson_standards_log(self.live, "INFO", "k", f"d1-{i}")
        reg.bejson_standards_flush(self.live)
        self.assertEqual(reg.bejson_standards_list_archives(self.live), [])
        self.assertEqual(len(reg.bejson_standards_read_logs(self.live)), 3)
        self.at(T(2026, 10, 27, 9))
        reg.bejson_standards_log(self.live, "INFO", "k", "d2")
        reg.bejson_standards_flush(self.live)
        arch = reg.bejson_standards_list_archives(self.live)
        self.assertEqual([k for k, _ in arch], ["2026-10-26"])
        self.assertEqual(len(self.arch_rows("2026-10-26")), 3)
        self.assertEqual([r[val.F_EVENT_MESSAGE] for r in reg.bejson_standards_read_logs(self.live)], ["d2"])

    def test_archive_now_and_include_current(self):
        self.cfg()
        self.at(T(2026, 10, 27, 9))
        reg.bejson_standards_log(self.live, "INFO", "k", "today")
        res = reg.bejson_standards_archive_now(self.live)
        self.assertEqual((res["ok"], res["moved"]), (True, 0))
        res = reg.bejson_standards_archive_now(self.live, include_current=True)
        self.assertEqual((res["ok"], res["moved"], len(res["files"])), (True, 1, 1))
        self.assertEqual(reg.bejson_standards_read_logs(self.live), [])
        self.assertEqual(len(self.arch_rows("2026-10-27")), 1)

    def test_archive_now_without_config_is_a_noop(self):
        reg.bejson_standards_configure_sink(self.live, persist=False)
        self.assertEqual(reg.bejson_standards_archive_now(self.live), {"ok": True, "moved": 0, "files": [], "errors": []})
        self.assertEqual(reg.bejson_standards_list_archives(self.live), [])

    def test_overflow_archived_instead_of_dropped(self):
        self.cfg(row_cap=2)
        self.at(T(2026, 10, 27, 9))
        for i in range(5):
            reg.bejson_standards_log(self.live, "INFO", "k", f"m{i}")
        reg.bejson_standards_flush(self.live)
        self.assertEqual([r[val.F_EVENT_MESSAGE] for r in reg.bejson_standards_read_logs(self.live)], ["m3", "m4"])
        self.assertEqual([r[val.F_EVENT_MESSAGE] for r in self.arch_rows("2026-10-27")], ["m0", "m1", "m2"])

    def test_overflow_archive_failure_keeps_rows_in_memory(self):
        blocker = os.path.join(self.tmp, "blocker")
        open(blocker, "w").close()
        self.cfg(row_cap=1, archive_dir=os.path.join(blocker, "a"))
        self.at(T(2026, 10, 27, 9))
        reg.bejson_standards_log(self.live, "INFO", "k", "one")
        buf = io.StringIO()
        with redirect_stderr(buf):
            reg.bejson_standards_log(self.live, "INFO", "k", "two")
            self.assertFalse(reg.bejson_standards_flush(self.live))
        self.assertIn("kept in memory", buf.getvalue())
        self.assertEqual(len(reg._get_sink(self.live).buffer), 2)           # nothing silently lost
        self.assertFalse(os.path.exists(self.live))

    def test_export_include_archives_in_order(self):
        self.cfg()
        self.at(T(2026, 10, 26, 12))
        reg.bejson_standards_log(self.live, "INFO", "k", "old")
        reg.bejson_standards_flush(self.live)
        self.at(T(2026, 10, 27, 12))
        reg.bejson_standards_log(self.live, "INFO", "k", "new")
        live_only = json.loads(reg.bejson_standards_export_logs(self.live)["text"])
        both = json.loads(reg.bejson_standards_export_logs(self.live, include_archives=True)["text"])
        self.assertEqual([r[val.F_EVENT_MESSAGE] for r in live_only], ["new"])
        self.assertEqual([r[val.F_EVENT_MESSAGE] for r in both], ["old", "new"])
        window = json.loads(reg.bejson_standards_export_logs(self.live, include_archives=True, until="2026-10-27T00:00:00Z")["text"])
        self.assertEqual([r[val.F_EVENT_MESSAGE] for r in window], ["old"])

    def test_retention_prunes_only_when_set(self):
        self.cfg(archive_keep_periods=1)
        for d in (24, 25, 26):
            self.at(T(2026, 10, d, 9))
            reg.bejson_standards_log(self.live, "INFO", "k", f"d{d}")
            reg.bejson_standards_flush(self.live)
        self.at(T(2026, 10, 27, 9))
        reg.bejson_standards_flush(self.live)
        self.assertEqual([k for k, _ in reg.bejson_standards_list_archives(self.live)], ["2026-10-26"])
        reg._SINKS.clear()
        self.cfg()                                                          # no keep: nothing is ever deleted
        for d in (27, 28):
            self.at(T(2026, 10, d, 9))
            reg.bejson_standards_log(self.live, "INFO", "k", f"d{d}")
            reg.bejson_standards_flush(self.live)
        self.at(T(2026, 10, 29, 9))
        reg.bejson_standards_flush(self.live)
        self.assertEqual(len(reg.bejson_standards_list_archives(self.live)), 3)

    def test_secure_archive_stays_in_its_own_tree(self):
        spath, sarch = os.path.join(self.tmp, "vault", "s.bejson"), os.path.join(self.tmp, "vault_arch")
        self.cfg(secure_path=spath, secure_archive_dir=sarch)
        self.at(T(2026, 10, 26, 9))
        reg.bejson_standards_log(self.live, "ERROR", "tok", "hunter2", secure=True)
        reg.bejson_standards_log(self.live, "INFO", "k", "plain")
        reg.bejson_standards_flush(self.live)
        self.at(T(2026, 10, 27, 9))
        reg.bejson_standards_flush(self.live)
        self.assertEqual([k for k, _ in reg.bejson_standards_list_archives(self.live, secure=True)], ["2026-10-26"])
        (sfile,) = [p for _k, p in reg.bejson_standards_list_archives(self.live, secure=True)]
        self.assertEqual(os.stat(sfile).st_mode & 0o777, 0o600)
        self.assertEqual(os.stat(sarch).st_mode & 0o777, 0o700)
        for name in os.listdir(self.arch):
            with open(os.path.join(self.arch, name), encoding="utf-8") as fh:
                self.assertNotIn("hunter2", fh.read())
        self.assertTrue(reg.bejson_standards_audit_log_file(self.live, secure=True)["passed"])
        self.assertTrue(val.bejson_standards_validator_audit_log_file(sfile)["passed"])

    def test_secure_log_without_secure_archive_dir_is_ring_only(self):
        spath = os.path.join(self.tmp, "vault", "s.bejson")
        self.cfg(secure_path=spath, row_cap=2)
        self.at(T(2026, 10, 27, 9))
        for i in range(4):
            reg.bejson_standards_log(self.live, "ERROR", "k", f"s{i}", secure=True)
        self.assertEqual([r[val.F_EVENT_MESSAGE] for r in reg.bejson_standards_read_logs(self.live, secure=True)], ["s2", "s3"])
        self.assertEqual(reg.bejson_standards_list_archives(self.live, secure=True), [])
        self.assertFalse(os.path.exists(os.path.join(self.arch, "s-2026-10-27.bejson")))


if __name__ == "__main__":
    unittest.main(verbosity=2)
