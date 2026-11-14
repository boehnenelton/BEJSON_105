"""
File Name : test_job_family.py
Rel. Path : Lib_PY/Job/tests/test_job_family.py
Purpose   : Tests for the Job family (errors, core, validator, runner, CLI) against the unmodified libraries_105 Core.
VERSION   : 1.0.0
Author    : Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
RELATIONAL_ID : 702fee68-d30d-4331-b233-37a7764bff95
Run       : python3 Lib_PY/Job/tests/test_job_family.py   (Job beside Core in libraries_105/Lib_PY), or set ADMIN_LIBRARIES_105 to the libraries_105 root
"""
import copy
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

_JOB = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, _JOB)

import lib_bejson_Job_bejson_errors as err  # noqa: E402
import lib_bejson_Job_job_core as jc  # noqa: E402
import lib_bejson_Job_job_runner as jr  # noqa: E402
import lib_bejson_Job_job_validator as jv  # noqa: E402

OWNED = [(1, 99), (130, 159), (160, 189), (200, 235), (250, 269), (270, 289), (300, 359), (360, 389),
         (420, 449), (450, 479), (480, 499), (500, 519), (520, 579)]
WORDS = "alpha beta gamma delta " * 5
IDX = {n: i for i, n in enumerate(jc.TASK_FIELD_NAMES)}


def _tasks(n=3, audit=True):
    return [{"name": f"Task {i}", "description": f"Brief {i}.\n\nTarget length: about 20 words.", "audit_enabled": audit}
            for i in range(1, n + 1)]


def _codes(doc, **kw):
    return jv.bejson_job_validator_validate_document(doc, **kw).codes


class TestErrors(unittest.TestCase):
    def test_range_and_uniqueness(self):
        codes = list(err.ERROR_NAMES)
        self.assertEqual(len(codes), len(set(codes)))
        for c in codes:
            self.assertTrue(390 <= c <= 419, c)
            for lo, hi in OWNED:
                self.assertFalse(lo <= c <= hi, f"{c} collides with {lo}-{hi}")
        for name, code in vars(err).items():
            if name.startswith("E_JOB_"):
                self.assertEqual(err.ERROR_NAMES[code], name)


class TestCoreAndValidator(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.doc = jc.bejson_job_core_new_job("Do the thing", _tasks())

    def test_new_job_is_valid_and_field_order_exact(self):
        self.assertEqual([f["name"] for f in self.doc["Fields"]], list(jc.TASK_FIELD_NAMES))
        self.assertEqual(len(self.doc["Fields"]), 11)
        r = jv.bejson_job_validator_validate_document(self.doc)
        self.assertTrue(r.valid, jv.bejson_job_validator_get_report(r))

    def test_save_load_roundtrip_has_no_cache_keys(self):
        p = os.path.join(self.tmp, "jobs", "j.bejson")
        jc.bejson_job_core_save(p, self.doc)
        raw = json.load(open(p, encoding="utf-8"))
        self.assertFalse([k for k in raw if k.startswith("_")])
        self.assertTrue(jv.bejson_job_validator_validate_file(p).valid)
        self.assertEqual(jc.bejson_job_core_progress(jc.bejson_job_core_load(p))["total"], 3)

    def test_invalid_document_is_never_written(self):
        p = os.path.join(self.tmp, "bad.bejson")
        bad = copy.deepcopy(self.doc)
        bad["Values"][0][IDX["task_order"]] = 7
        with self.assertRaises(err.JobError) as cm:
            jc.bejson_job_core_save(p, bad)
        self.assertEqual(cm.exception.code, err.E_JOB_VALIDATION_FAILED)
        self.assertFalse(os.path.exists(p))

    def test_every_check_fires(self):
        def mutate(fn):
            d = copy.deepcopy(self.doc)
            fn(d)
            return _codes(d)

        def cell(name, value):
            return lambda d: d["Values"][0].__setitem__(IDX[name], value)

        self.assertIn(err.E_JOB_SCHEMA_MISMATCH, mutate(lambda d: d.update(Format_Version="104")))
        self.assertIn(err.E_JOB_SCHEMA_MISMATCH, mutate(lambda d: d.update(Records_Type=["X"])))
        self.assertIn(err.E_JOB_SCHEMA_MISMATCH, mutate(lambda d: d.update(Format_Creator="Someone")))
        self.assertIn(err.E_JOB_HEADER_INVALID, mutate(lambda d: d.update(Target_File="x")))
        self.assertIn(err.E_JOB_HEADER_INVALID, mutate(lambda d: d.pop("Job_Goal")))
        self.assertIn(err.E_JOB_HEADER_INVALID, mutate(lambda d: d.update(Creation_Date="2026-13-40")))
        self.assertIn(err.E_JOB_ROW_SHAPE, mutate(lambda d: d["Values"][0].pop()))
        self.assertIn(err.E_JOB_TASK_VALUE_TYPE, mutate(cell("task_completed", None)))
        self.assertIn(err.E_JOB_TASK_VALUE_TYPE, mutate(cell("task_order", True)))
        self.assertIn(err.E_JOB_TASK_ID_INVALID, mutate(cell("task_id", "nope")))
        self.assertIn(err.E_JOB_TASK_ID_DUPLICATE, mutate(lambda d: d["Values"][1].__setitem__(IDX["task_id"], d["Values"][0][IDX["task_id"]])))
        self.assertIn(err.E_JOB_ORDER_INVALID, mutate(lambda d: d["Values"][2].__setitem__(IDX["task_order"], 2)))
        self.assertIn(err.E_JOB_TEXT_EMPTY, mutate(cell("task_description", "\n\nonly derived")))
        self.assertIn(err.E_JOB_TEXT_EMPTY, mutate(cell("task_name", "  ")))
        self.assertIn(err.E_JOB_CELL_SHAPE, mutate(cell("task_context", "[]")))
        self.assertIn(err.E_JOB_CELL_SHAPE, mutate(cell("task_context", [{"ref": "a.txt"}])))
        self.assertIn(err.E_JOB_CELL_SHAPE, mutate(cell("task_reference", "a.txt")))
        self.assertIn(err.E_JOB_PATH_INVALID, mutate(cell("task_reference", ["../x"])))
        self.assertIn(err.E_JOB_PATH_INVALID, mutate(cell("task_reference", ["/etc/x"])))
        self.assertIn(err.E_JOB_PATH_INVALID, mutate(cell("task_reference", ["C:/x"])))
        self.assertIn(err.E_JOB_COMPLETION_MISMATCH, mutate(lambda d: d.update(Job_Complete=True)))
        self.assertIn(err.E_JOB_COMPLETION_MISMATCH, mutate(lambda d: d.update(Completion_Date="2026-11-14")))
        self.assertIn(err.E_JOB_AUDIT_INCONSISTENT, mutate(lambda d: (d["Values"][0].__setitem__(IDX["audit_passed"], True),
                                                                      d["Values"][0].__setitem__(IDX["audit_fail_reason"], "x"))))

    def test_completed_but_unaudited_is_a_warning_not_an_error(self):
        d = copy.deepcopy(self.doc)
        d["Values"][0][IDX["task_completed"]] = True
        r = jv.bejson_job_validator_validate_document(d)
        self.assertTrue(r.valid)
        self.assertIn(err.E_JOB_AUDIT_INCONSISTENT, {w.code for w in r.warnings})

    def test_valid_context_and_reference_cells(self):
        d = jc.bejson_job_core_new_job("g", [{"name": "a", "description": "b", "references": ["src/x.py"],
                                              "context": [jc.bejson_job_core_chunk_text("docs/a.md", "p1\n\np2")]}])
        self.assertTrue(jv.bejson_job_validator_validate_document(d).valid)

    def test_legacy_columns(self):
        d = copy.deepcopy(self.doc)
        d["Fields"].append({"name": "test_cmd", "type": "string"})
        for row in d["Values"]:
            row.append("")
        d["Target_File"] = "x.md"
        self.assertIn(err.E_JOB_FORBIDDEN_COLUMN, _codes(d))
        clean = jc.bejson_job_core_normalize_legacy(d)
        self.assertNotIn("Target_File", clean)
        self.assertEqual(len(clean["Fields"]), 11)
        self.assertTrue(jv.bejson_job_validator_validate_document(clean).valid)
        d["Values"][0][-1] = "rm -rf /"
        with self.assertRaises(err.JobError) as cm:
            jc.bejson_job_core_normalize_legacy(d)
        self.assertEqual(cm.exception.code, err.E_JOB_SHELL_FORBIDDEN)

    def test_book_plan_header_rules(self):
        d = jc.bejson_job_core_new_job("g", _tasks(1), job_type="writing", job_subtype="book")
        self.assertIn(err.E_JOB_HEADER_INVALID, _codes(d))   # goal prefix missing
        d["Job_Goal"] = 'Write the book "T" for everyone, in English (en). Goal: x'
        self.assertTrue(jv.bejson_job_validator_validate_document(d).valid)
        d["Contextualize_Last"] = False
        self.assertIn(err.E_JOB_HEADER_INVALID, _codes(d))
        self.assertTrue(jv.bejson_job_validator_validate_document(d, expect_book=False).valid)

    def _book(self, ids_kinds):
        fields = [{"name": "Record_Type_Parent", "type": "string"}] + [
            {"name": n, "type": t, "Record_Type_Parent": "Chapter"}
            for n, t in (("chapter_uuid", "string"), ("chapter_kind_text", "string"), ("chapter_order_index", "integer"))]
        rows = [["Chapter", u, k, i] for i, (u, k) in enumerate(ids_kinds, start=1)]
        return {"Format": "BEJSON", "Format_Version": "104db", "Format_Creator": "Elton Boehnen",
                "Records_Type": ["Chapter", "Book"], "Fields": fields, "Values": rows}

    def test_book_link(self):
        ids = [row[IDX["task_id"]] for row in self.doc["Values"]]
        book = self._book([("part-uuid", "part")] + [(i, "chapter") for i in ids])
        self.assertTrue(jv.bejson_job_validator_validate_document(self.doc, book_doc=book).valid)
        self.assertIn(err.E_JOB_BOOK_LINK, _codes(self.doc, book_doc=self._book([(ids[0], "chapter")])))
        self.assertIn(err.E_JOB_BOOK_LINK, _codes(self.doc, book_doc=self._book([(i, "chapter") for i in reversed(ids)])))
        self.assertIn(err.E_JOB_BOOK_LINK, _codes(self.doc, book_doc={"Fields": [], "Values": []}))

    def test_template_instantiation(self):
        t = copy.deepcopy(self.doc)
        t["Values"][0][IDX["task_context"]] = [jc.bejson_job_core_chunk_text("a.md", "x")]
        t["Values"][0][IDX["task_mandatory"]] = True
        job = jc.bejson_job_core_instantiate_template(t, today="2030-01-02")
        self.assertEqual(job["Creation_Date"], "2030-01-02")
        self.assertNotEqual(job["Values"][0][IDX["task_id"]], t["Values"][0][IDX["task_id"]])
        self.assertEqual(job["Values"][0][IDX["task_context"]], t["Values"][0][IDX["task_context"]])
        self.assertTrue(job["Values"][0][IDX["task_mandatory"]])
        self.assertTrue(jv.bejson_job_validator_validate_document(job).valid)
        with self.assertRaises(err.JobError) as cm:
            jc.bejson_job_core_instantiate_template({"Format": "BEJSON"})
        self.assertEqual(cm.exception.code, err.E_JOB_TEMPLATE_INVALID)

    def test_chunking_and_skip(self):
        entry = jc.bejson_job_core_chunk_text("a.md", "\n\n".join(f"para{i} " * 30 for i in range(6)), max_chars=400)
        self.assertGreater(len(entry["chunks"]), 1)
        self.assertEqual([c["chunk_index_pos"] for c in entry["chunks"]], list(range(1, len(entry["chunks"]) + 1)))
        entry["chunks"][0]["chunk_status"] = "skip"
        text = jc.bejson_job_core_context_text({"task_context": [entry]})
        self.assertNotIn(entry["chunks"][0]["chunk_content"], text)

    def test_sanitize_strips_boundary_whitespace(self):
        d = copy.deepcopy(self.doc)
        d["Job_Goal"] = "  goal  "
        d["Values"][0][IDX["task_name"]] = "  Name  "
        jc.bejson_job_core_sanitize(d)
        self.assertEqual(d["Job_Goal"], "goal")
        self.assertEqual(d["Values"][0][IDX["task_name"]], "Name")

    def test_path_guard(self):
        with self.assertRaises(err.JobError) as cm:
            jc.bejson_job_core_safe_join(self.tmp, "..", "escape")
        self.assertEqual(cm.exception.code, err.E_JOB_PATH_ESCAPE)

    def test_missing_file_is_a_load_error_in_validate_file(self):
        r = jv.bejson_job_validator_validate_file(os.path.join(self.tmp, "nope.bejson"))
        self.assertEqual(r.codes, {err.E_JOB_LOAD_FAILED})


class TestGate(unittest.TestCase):
    def test_rules(self):
        std = jr.bejson_job_runner_gate_rules(jr.GateConfig("standard", min_words=5))
        self.assertTrue(jr.bejson_job_runner_run_gate(WORDS, std)[0])
        self.assertFalse(jr.bejson_job_runner_run_gate("two words", std)[0])
        self.assertFalse(jr.bejson_job_runner_run_gate(WORDS + " TODO", std)[0])
        self.assertFalse(jr.bejson_job_runner_run_gate(WORDS + " [insert name]", std)[0])
        strict = jr.bejson_job_runner_gate_rules(jr.GateConfig("strict", min_words=5, must_include=("Summary",)))
        self.assertFalse(jr.bejson_job_runner_run_gate(WORDS, strict)[0])
        self.assertTrue(jr.bejson_job_runner_run_gate("## Summary\n\n" + WORDS, strict)[0])
        self.assertFalse(jr.bejson_job_runner_run_gate("## Summary\n\n" + WORDS + "\n```\ncode", strict)[0])
        self.assertTrue(jr.bejson_job_runner_run_gate("", jr.bejson_job_runner_gate_rules(jr.GateConfig("none")))[0])
        self.assertFalse(jr.bejson_job_runner_run_gate(WORDS, {"max_words": 3})[0])

    def test_code_fences_do_not_count_as_words(self):
        self.assertEqual(jr.bejson_job_runner_word_count("a b\n```\nx y z\n```\nc"), 3)

    def test_unknown_refused(self):
        for bad in (jr.GateConfig("bogus"), jr.GateConfig(rules={"run_shell": "ls"})):
            with self.assertRaises(err.JobError) as cm:
                jr.bejson_job_runner_gate_rules(bad)
            self.assertEqual(cm.exception.code, err.E_JOB_GATE_UNKNOWN)
        with self.assertRaises(err.JobError):
            jr.bejson_job_runner_run_gate("x", {"test_cmd": "ls"})


class TestRunner(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root, True)
        self.job_rel = "jobs/My Job.bejson"
        jc.bejson_job_core_save(os.path.join(self.root, self.job_rel), jc.bejson_job_core_new_job("Ship it", _tasks(3)))
        self.seen = []

    def runner(self, executor=None, gate=None):
        return jr.JobRunner(self.root, self.job_rel, executor=executor, gate=gate or jr.GateConfig("standard", min_words=5))

    def good(self, package):
        self.seen.append(package)
        return f"Output for {package['task']['task_name']}. " + WORDS

    def test_full_run_one_task_at_a_time_with_context_chaining(self):
        r = self.runner(self.good)
        first = r.step()
        self.assertTrue(first.passed)
        self.assertEqual(r.inspect()["completed"], 1)
        self.assertEqual(first.staged_path, f"runs/my_job/{jc.bejson_job_core_task_id_slug(first.task_id)}.md")
        second = r.step()
        self.assertEqual(self.seen[1]["last_output"]["task_name"], "Task 1")
        self.assertIn("Output for Task 1", self.seen[1]["prompt"])
        self.assertIn("Ship it", self.seen[1]["prompt"])
        self.assertIsNone(self.seen[0]["last_output"])
        self.assertFalse(second.job_complete)
        third = r.step()
        self.assertTrue(third.job_complete)
        self.assertIsNone(r.step())
        done = r.load()
        self.assertTrue(done["Job_Complete"])
        self.assertEqual(done["Completion_Date"], jc.bejson_job_core_today())
        self.assertTrue(jv.bejson_job_validator_validate_file(r.job_path).valid)

    def test_gate_failure_keeps_task_open_and_halts_run(self):
        calls = []

        def bad(package):
            calls.append(package["task"]["task_order"])
            return "too short TODO"

        r = self.runner(bad)
        results = r.run()
        self.assertEqual(len(results), 1)
        self.assertFalse(results[0].passed)
        task = jc.bejson_job_core_tasks(r.load())[0]
        self.assertFalse(task["task_completed"])
        self.assertFalse(task["audit_passed"])
        self.assertIn("too short", task["audit_fail_reason"])
        self.assertTrue(os.path.isfile(r.staged_path(task["task_id"])))
        self.assertEqual(calls, [1])
        r.executor = self.good
        self.assertTrue(r.step().passed)
        self.assertEqual(jc.bejson_job_core_tasks(r.load())[0]["audit_fail_reason"], "")

    def test_audit_disabled_skips_gate(self):
        jc.bejson_job_core_save(os.path.join(self.root, "jobs/na.bejson"), jc.bejson_job_core_new_job("g", _tasks(1, audit=False)))
        r = jr.JobRunner(self.root, "jobs/na.bejson", executor=lambda p: "x", gate=jr.GateConfig("strict", min_words=50))
        self.assertTrue(r.step().passed)

    def test_executor_failure_leaves_job_untouched(self):
        path = os.path.join(self.root, self.job_rel)
        before = open(path, "rb").read()

        def boom(_):
            raise RuntimeError("provider down")

        with self.assertRaises(err.JobError) as cm:
            self.runner(boom).step()
        self.assertEqual(cm.exception.code, err.E_JOB_EXECUTOR_FAILED)
        self.assertEqual(open(path, "rb").read(), before)
        with self.assertRaises(err.JobError) as cm:
            self.runner(lambda p: 42).step()
        self.assertEqual(cm.exception.code, err.E_JOB_EXECUTOR_FAILED)
        with self.assertRaises(err.JobError) as cm:
            self.runner().step()
        self.assertEqual(cm.exception.code, err.E_JOB_NO_EXECUTOR)

    def test_ingest_gates_staged_files(self):
        r = self.runner()
        tasks = jc.bejson_job_core_tasks(r.load())
        r.stage_output(tasks[0]["task_id"], "Good. " + WORDS)
        r.stage_output(tasks[1]["task_id"], "TODO")
        r.stage_output(tasks[2]["task_id"], "Never reached. " + WORDS)
        self.assertEqual([x.passed for x in r.ingest()], [True, False])        # stops at the first failure
        self.assertEqual([t["task_completed"] for t in jc.bejson_job_core_tasks(r.load())], [True, False, False])
        r.stage_output(tasks[1]["task_id"], "Fixed. " + WORDS)
        self.assertEqual([x.passed for x in r.ingest()], [True, True])          # task 1 already verified: not redone
        self.assertTrue(r.load()["Job_Complete"])

    def test_ingest_sends_back_a_task_completed_elsewhere_that_fails_the_gate(self):
        r = self.runner()
        tid = jc.bejson_job_core_tasks(r.load())[0]["task_id"]
        jc.bejson_job_core_update(r.job_path, lambda d: jc.bejson_job_core_set_task_state(d, tid, completed=True))  # another runner's mark
        self.assertTrue(jc.bejson_job_core_tasks(r.load())[0]["task_completed"])
        r.stage_output(tid, "TBD")
        result = r.ingest()
        self.assertFalse(result[0].passed)
        task = jc.bejson_job_core_tasks(r.load())[0]
        self.assertFalse(task["task_completed"])
        self.assertIn("placeholder", task["audit_fail_reason"])

    def test_references_listed_never_read(self):
        os.makedirs(os.path.join(self.root, "src"))
        open(os.path.join(self.root, "src", "a.py"), "w").write("SECRET_CONTENT")
        doc = jc.bejson_job_core_new_job("g", [{"name": "a", "description": "b", "references": ["src/a.py", "src/missing.py"]}])
        jc.bejson_job_core_save(os.path.join(self.root, "jobs/refs.bejson"), doc)
        r = jr.JobRunner(self.root, "jobs/refs.bejson", executor=lambda p: "x")
        d = r.load()
        pkg = r.build_package(d, jc.bejson_job_core_next_task(d))
        self.assertEqual([x["exists"] for x in pkg["references"]], [True, False])
        self.assertNotIn("SECRET_CONTENT", json.dumps(pkg))

    def test_runner_refuses_job_path_outside_root(self):
        with self.assertRaises(err.JobError) as cm:
            jr.JobRunner(self.root, "../elsewhere.bejson")
        self.assertEqual(cm.exception.code, err.E_JOB_PATH_ESCAPE)

    def test_lock_is_released_after_write(self):
        self.runner(self.good).step()
        self.assertFalse(os.path.exists(os.path.join(self.root, self.job_rel) + ".lockdir"))


class TestCLI(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root, True)
        self.path = os.path.join(self.root, "jobs", "c.bejson")
        jc.bejson_job_core_save(self.path, jc.bejson_job_core_new_job("g", _tasks(1)))

    def call(self, *argv):
        out, errbuf = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(errbuf):
            code = jr.main(list(argv))
        return code, out.getvalue()

    def test_exit_codes(self):
        self.assertEqual(self.call("--version")[0], 0)
        self.assertEqual(self.call("--validate", self.path)[0], 0)
        self.assertEqual(self.call("--inspect", self.path)[0], 0)
        bad = json.load(open(self.path))
        bad["Format_Creator"] = "Someone"
        json.dump(bad, open(self.path, "w"))
        self.assertEqual(self.call("--validate", self.path)[0], 30)
        self.assertEqual(self.call("--inspect", self.path)[0], 30)
        self.assertEqual(self.call("--validate", os.path.join(self.root, "none.bejson"))[0], 30)

    def test_ingest_cli(self):
        tid = jc.bejson_job_core_tasks(jc.bejson_job_core_load(self.path))[0]["task_id"]
        jr.JobRunner(self.root, self.path).stage_output(tid, "Good. " + WORDS)
        code, out = self.call("--ingest", self.path, "--min-words", "5")
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(out)[0]["job_complete"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
