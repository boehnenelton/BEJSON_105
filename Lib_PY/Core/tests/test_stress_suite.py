"""
Library:        test_stress_suite.py
Family:         Core (tests)
Description:    Elaborate stress / fuzz suite for the adversarial-review
                 remediation. Real processes, real files, real races:
                   A. ResilientPIDLock: multi-process + multi-thread mutual
                      exclusion, stale-reclaim storms, crashed holders,
                      no-meta grace window, live-lock protection, ownership-
                      checked release, tombstone hygiene.
                   B. 105 / 105a / 105db column mapping fuzz (resolve,
                      write_cell, remove_field, public field map).
                   C. MFDB cascade-delete fuzz against an independent
                      reference model, plus injected commit failures that
                      must roll back byte-for-byte.
                   D. source_env / _parse_env_file: payload corpus + random
                      fuzz; nothing may execute, nothing partially applies.
                   E. parse_json fuzz + large-document memory ratio.

                 Knobs (environment variables):
                   STRESS_SEED   int, default random (always logged)
                   STRESS_SCALE  int >= 1, default 1 (multiplies iterations)

                 Run:  python3 tests/test_stress_suite.py
                       STRESS_SCALE=5 STRESS_SEED=1234 python3 tests/test_stress_suite.py

Version:        1.0.0
Date:           2026-10-12
Author:         Elton Boehnen
Contact:        boehnenelton2024@gmail.com | boehnenelton2024.pages.dev | github.com/boehnenelton
Format_Creator: Elton Boehnen
RELATIONAL_ID:  0d3c5a7e-91b4-4c2f-8a16-7e5f2b9d4c03
Release_Version: 300
"""

import glob
import json
import logging
import multiprocessing as mp
import os
import random
import shutil
import string
import sys
import tempfile
import threading
import time
import tracemalloc
import unittest
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import lib_bejson_Core_bejson_core as C
import lib_bejson_Core_bejson_env as Env
import lib_bejson_Core_bejson_parse as Parse
import lib_bejson_Core_mfdb_core as M

LOG = logging.getLogger("stress")
SCALE = max(1, int(os.environ.get("STRESS_SCALE", "1")))
SEED = int(os.environ.get("STRESS_SEED", str(random.SystemRandom().randrange(1, 2**31))))
CTX = mp.get_context("fork" if "fork" in mp.get_all_start_methods() else "spawn")


def setUpModule():
    LOG.info("STRESS_SEED=%d STRESS_SCALE=%d", SEED, SCALE)


def _rng(tag):
    return random.Random(f"{SEED}:{tag}")


def _dead_pid():
    pid = 4_000_000
    while C.ResilientPIDLock._pid_alive(pid):
        pid += 1
    return pid


# ===========================================================================
# A. ResilientPIDLock
# ===========================================================================

def _w_exclusive(target, iters, counter_path, marker_path, out_q, hold):
    """Increment a shared counter under the lock; detect overlapping holders.
    Always reports (violations, error) so the parent never hangs on a dead worker."""
    violations = 0
    err = None
    try:
        for _ in range(iters):
            with C.ResilientPIDLock(target, timeout_seconds=120):
                try:
                    fd = os.open(marker_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                    os.close(fd)
                except FileExistsError:
                    violations += 1
                with open(counter_path) as fh:
                    n = int(fh.read() or "0")
                if hold:
                    time.sleep(hold)
                with open(counter_path, "w") as fh:
                    fh.write(str(n + 1))
                try:
                    os.unlink(marker_path)
                except FileNotFoundError:
                    violations += 1
    except BaseException as exc:  # noqa: BLE001 - report, don't die silently
        err = f"{type(exc).__name__}: {exc}"
    out_q.put((violations, err))


def _w_crash_holder(target):
    lk = C.ResilientPIDLock(target, timeout_seconds=5)
    if lk.acquire():
        os._exit(9)           # die holding the lock, no release
    os._exit(2)


def _w_try_acquire(target, timeout, out_q):
    lk = C.ResilientPIDLock(target, timeout_seconds=timeout)
    ok = lk.acquire()
    if ok:
        lk.release()
    out_q.put(ok)


class TestLockStress(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="stress_lock_")
        self.target = os.path.join(self.tmp, "ent.bejson")
        self.counter = os.path.join(self.tmp, "counter")
        self.marker = os.path.join(self.tmp, "in_critical")
        with open(self.counter, "w") as fh:
            fh.write("0")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _plant(self, pid, token="deadbeef"):
        d = self.target + ".lockdir"
        os.mkdir(d)
        with open(os.path.join(d, "lock_meta.json"), "w") as fh:
            json.dump({"pid": pid, "timestamp": int(time.time()), "token": token}, fh)
        return d

    def _run_procs(self, nprocs, iters, hold=0.0):
        q = CTX.Queue()
        ps = [CTX.Process(target=_w_exclusive,
                          args=(self.target, iters, self.counter, self.marker, q, hold))
              for _ in range(nprocs)]
        for p in ps:
            p.start()
        res = [q.get(timeout=300) for _ in ps]
        for p in ps:
            p.join(timeout=60)
        self.assertEqual([e for _v, e in res if e], [], "worker died")
        return sum(v for v, _e in res)

    def _assert_clean(self):
        self.assertEqual(glob.glob(self.target + ".lockdir*"), [],
                         "lock dir / tombstones left behind")

    def test_multiprocess_mutual_exclusion(self):
        n, it = 8, 20 * SCALE
        viol = self._run_procs(n, it)
        self.assertEqual(viol, 0, "two processes were inside the critical section at once")
        self.assertEqual(int(open(self.counter).read()), n * it, "lost update")
        self._assert_clean()

    def test_mutual_exclusion_with_long_holds(self):
        n, it = 6, 4 * SCALE
        viol = self._run_procs(n, it, hold=0.02)
        self.assertEqual(viol, 0)
        self.assertEqual(int(open(self.counter).read()), n * it)
        self._assert_clean()

    def test_stale_reclaim_storm(self):
        """A dead owner's lock with many racers: exactly-one reclaim, no double entry."""
        for rnd in range(3 * SCALE):
            with open(self.counter, "w") as fh:
                fh.write("0")
            self._plant(_dead_pid(), token=f"dead{rnd}")
            n, it = 10, 5
            viol = self._run_procs(n, it)
            self.assertEqual(viol, 0, f"round {rnd}: overlap after stale reclaim")
            self.assertEqual(int(open(self.counter).read()), n * it, f"round {rnd}: lost update")
            self._assert_clean()

    def test_crashed_holders_never_wedge_the_lock(self):
        for rnd in range(4 * SCALE):
            p = CTX.Process(target=_w_crash_holder, args=(self.target,))
            p.start()
            p.join(timeout=30)
            self.assertEqual(p.exitcode, 9, "holder should have died holding the lock")
            self.assertTrue(os.path.isdir(self.target + ".lockdir"))
            lk = C.ResilientPIDLock(self.target, timeout_seconds=10)
            self.assertTrue(lk.acquire(), f"round {rnd}: crashed holder wedged the lock")
            lk.release()
            self._assert_clean()

    def test_crash_storm_with_live_contenders(self):
        """Holders keep dying while honest workers keep counting."""
        n, it = 6, 15 * SCALE
        q = CTX.Queue()
        workers = [CTX.Process(target=_w_exclusive,
                               args=(self.target, it, self.counter, self.marker, q, 0.0))
                   for _ in range(n)]
        for w in workers:
            w.start()
        stop = time.time() + 6
        while time.time() < stop and any(w.is_alive() for w in workers):
            c = CTX.Process(target=_w_crash_holder, args=(self.target,))
            c.start()
            c.join(timeout=15)
        res = [q.get(timeout=300) for _ in workers]
        for w in workers:
            w.join(timeout=60)
        self.assertEqual([e for _v, e in res if e], [], "worker died")
        viol = sum(v for v, _e in res)
        self.assertEqual(viol, 0, "overlap while crashers raced honest workers")
        # A crasher that dies mid-critical-section can't corrupt the counter
        # (workers write it under the lock); it can only fail to take the lock.
        self.assertEqual(int(open(self.counter).read()), n * it)

    def test_no_meta_lock_respects_grace_then_is_reclaimed(self):
        d = self.target + ".lockdir"
        os.mkdir(d)  # owner "between mkdir and meta write"
        fresh = C.ResilientPIDLock(self.target, timeout_seconds=0.6)
        self.assertFalse(fresh.acquire(), "fresh no-meta lock must not be stolen")
        self.assertTrue(os.path.isdir(d))
        old = time.time() - 60
        os.utime(d, (old, old))
        aged = C.ResilientPIDLock(self.target, timeout_seconds=3)
        self.assertTrue(aged.acquire(), "aged no-meta lock must be reclaimed")
        aged.release()
        self._assert_clean()

    def test_live_lock_is_never_reclaimed_under_pressure(self):
        holder = C.ResilientPIDLock(self.target, timeout_seconds=2)
        self.assertTrue(holder.acquire())
        meta_before = open(os.path.join(self.target + ".lockdir", "lock_meta.json")).read()
        q = CTX.Queue()
        ps = [CTX.Process(target=_w_try_acquire, args=(self.target, 1.0, q)) for _ in range(12)]
        for p in ps:
            p.start()
        results = [q.get(timeout=60) for _ in ps]
        for p in ps:
            p.join(timeout=30)
        self.assertEqual(results, [False] * 12, "a live lock was taken from its owner")
        meta_after = open(os.path.join(self.target + ".lockdir", "lock_meta.json")).read()
        self.assertEqual(meta_before, meta_after)
        holder.release()
        self._assert_clean()

    def test_release_after_being_reclaimed_leaves_new_owner_alone(self):
        for rnd in range(10 * SCALE):
            a = C.ResilientPIDLock(self.target, timeout_seconds=2)
            self.assertTrue(a.acquire())
            shutil.rmtree(self.target + ".lockdir")        # A reclaimed from under it
            b = C.ResilientPIDLock(self.target, timeout_seconds=2)
            self.assertTrue(b.acquire())
            a.release()                                      # stale release must be a no-op
            self.assertTrue(os.path.isdir(self.target + ".lockdir"), f"round {rnd}: A destroyed B's lock")
            b.release()
            self._assert_clean()

    def test_double_release_and_foreign_release_are_noops(self):
        a = C.ResilientPIDLock(self.target, timeout_seconds=1)
        a.release()  # never acquired
        self.assertTrue(a.acquire())
        a.release()
        a.release()
        d = self._plant(os.getpid(), token="someone-else")
        C.ResilientPIDLock(self.target, timeout_seconds=1).release()
        self.assertTrue(os.path.isdir(d))

    def test_thread_mutual_exclusion(self):
        n, it = 8, 25 * SCALE
        viol = []

        def work():
            for _ in range(it):
                with C.ResilientPIDLock(self.target, timeout_seconds=120):
                    try:
                        fd = os.open(self.marker, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                        os.close(fd)
                    except FileExistsError:
                        viol.append(1)
                    c = int(open(self.counter).read())
                    open(self.counter, "w").write(str(c + 1))
                    os.unlink(self.marker)

        ts = [threading.Thread(target=work) for _ in range(n)]
        for t in ts:
            t.start()
        for t in ts:
            t.join(timeout=300)
        self.assertEqual(viol, [])
        self.assertEqual(int(open(self.counter).read()), n * it)
        self._assert_clean()

    def test_unwritable_meta_does_not_leak_lock(self):
        lk = C.ResilientPIDLock(self.target, timeout_seconds=1)
        real = lk.meta_file.__class__.write_text

        def boom(self_, *a, **k):
            raise OSError("injected")

        lk.meta_file.__class__.write_text = boom
        try:
            with self.assertRaises(OSError):
                lk.acquire()
        finally:
            lk.meta_file.__class__.write_text = real
        self._assert_clean()
        self.assertTrue(C.ResilientPIDLock(self.target, timeout_seconds=1).acquire())


# ===========================================================================
# B. 105 / 105a / 105db column fuzz
# ===========================================================================

def _rand_word(r, n=6):
    return "".join(r.choice(string.ascii_lowercase) for _ in range(n))


def _build_doc(r, fmt):
    nf = r.randint(2, 12)
    names = []
    while len(names) < nf:
        w = "f_" + _rand_word(r)
        if w not in names:
            names.append(w)
    rt = "Thing"
    fields = []
    if fmt == "105db":
        fields.append({"name": "Record_Type_Parent", "type": "string", "field_uuid": str(uuid.uuid4())})
        for n in names[1:]:
            fields.append({"name": n, "type": "string", "Record_Type_Parent": rt,
                           "field_uuid": str(uuid.uuid4())})
    else:
        for n in names:
            fields.append({"name": n, "type": "string", "field_uuid": str(uuid.uuid4())})
    nrows = r.randint(1, 5)
    rows = []
    for _ in range(nrows):
        vals = [_rand_word(r, 4) for _ in fields]
        ru = str(uuid.uuid4())
        if fmt == "105db":
            rows.append([rt, ru] + vals[1:])
        else:
            rows.append([ru] + vals)
    return {"Format": "BEJSON", "Format_Version": fmt, "Format_Creator": "Elton Boehnen",
            "Records_Type": [rt], "Fields": fields, "Values": rows}


def _abs_col(fmt, i):
    if fmt == "105db":
        return 0 if i == 0 else i + 1
    return i + 1


class TestColumnFuzz(unittest.TestCase):

    def test_resolve_write_fieldmap_agree_for_every_field(self):
        r = _rng("colfuzz")
        trials = 120 * SCALE
        for t in range(trials):
            fmt = r.choice(["105", "105a", "105db"])
            doc = _build_doc(r, fmt)
            fm = C.bejson_core_get_field_map(doc)
            for i, f in enumerate(doc["Fields"]):
                want = _abs_col(fmt, i)
                self.assertEqual(C.bejson_core_resolve_field_index(doc, f["name"]), want, (t, fmt, i))
                self.assertEqual(C.bejson_core_resolve_field_index(doc, f["field_uuid"]), want, (t, fmt, i))
                for row in doc["Values"]:  # public map indexes real rows
                    self.assertEqual(fm[f["name"]], want)
                if fmt == "105db" and i == 0:
                    continue  # discriminator is not user-writable
                ri = r.randrange(len(doc["Values"]))
                row = doc["Values"][ri]
                before = list(row)
                val = "W" + _rand_word(r, 5)
                C.bejson_core_write_cell(doc, row[0 if False else (1 if fmt == "105db" else 0)],
                                         f["field_uuid"], val)
                after = doc["Values"][ri]
                self.assertEqual(len(after), len(before), (t, fmt, i, "row length changed"))
                self.assertEqual(after[want], val, (t, fmt, i, "wrong column written"))
                for c in range(len(before)):
                    if c != want:
                        self.assertEqual(after[c], before[c], (t, fmt, i, f"collateral damage col {c}"))

    def test_remove_field_removes_exactly_one_column(self):
        r = _rng("rmfuzz")
        for t in range(100 * SCALE):
            fmt = r.choice(["105", "105a", "105db"])
            doc = _build_doc(r, fmt)
            lo = 1 if fmt == "105db" else 0
            i = r.randint(lo, len(doc["Fields"]) - 1)
            col = _abs_col(fmt, i)
            names = [f["name"] for f in doc["Fields"]]
            expect_rows = [row[:col] + row[col + 1:] for row in doc["Values"]]
            expect_names = names[:i] + names[i + 1:]
            C.bejson_core_remove_field(doc, names[i])
            self.assertEqual(doc["Values"], expect_rows, (t, fmt, i))
            self.assertEqual([f["name"] for f in doc["Fields"]], expect_names, (t, fmt, i))
            # remaining fields still resolve to real columns
            for j, f in enumerate(doc["Fields"]):
                self.assertEqual(C.bejson_core_resolve_field_index(doc, f["name"]), _abs_col(fmt, j))

    def test_discriminator_is_never_removable(self):
        r = _rng("disc")
        for _ in range(20 * SCALE):
            doc = _build_doc(r, "105db")
            strip = lambda d: json.dumps({k: v for k, v in d.items() if not k.startswith("_bejson")}, sort_keys=True)
            snap = strip(doc)
            with self.assertRaises(C.BEJSONCoreError):
                C.bejson_core_remove_field(doc, "Record_Type_Parent")
            self.assertEqual(strip(doc), snap)

    def test_cache_never_goes_stale_across_mutations(self):
        r = _rng("stale")
        for _ in range(60 * SCALE):
            fmt = r.choice(["105", "105a", "105db"])
            doc = _build_doc(r, fmt)
            for _ in range(3):
                lo = 1 if fmt == "105db" else 0
                if len(doc["Fields"]) <= lo + 1:
                    break
                i = r.randint(lo, len(doc["Fields"]) - 1)
                C.bejson_core_remove_field(doc, doc["Fields"][i]["name"])
                for j, f in enumerate(doc["Fields"]):
                    self.assertEqual(C.bejson_core_resolve_field_index(doc, f["name"]), _abs_col(fmt, j))


# ===========================================================================
# C. Cascade-delete fuzz vs reference model
# ===========================================================================

MODES = ("restrict", "cascade", "null")


class _World:
    """A random forest-of-entities MFDB plus an independent in-memory model."""

    def __init__(self, tmp, r, tc):
        self.r = r
        self.tc = tc
        self.n_ent = r.randint(2, 6)
        self.parent = {}   # entity index -> (parent index, mode)
        specs = []
        for i in range(self.n_ent):
            fields = [{"name": "label", "type": "string"}]
            if i > 0:
                p = r.randrange(i)
                mode = r.choice(MODES)
                self.parent[i] = (p, mode)
                fields.append({"name": "fk", "type": "string", "fk_target_entity": f"e{p}",
                               "fk_on_delete": mode})
            specs.append({"name": f"e{i}", "fields": fields, "format_version": "105"})
        self.mp = M.mfdb_core_create_database(root_dir=tmp, db_name="fz", entities=specs)
        M.mfdb_core_enable_ref_integrity(self.mp)
        self.rows = {i: [] for i in range(self.n_ent)}   # [uuid, label, fk]
        for i in range(self.n_ent):
            for k in range(r.randint(0, 5)):
                if i == 0:
                    vals, fk = [f"L{i}.{k}"], None
                else:
                    cand = [x[0] for x in self.rows[self.parent[i][0]]]
                    fk = r.choice(cand + [None]) if cand else None
                    vals = [f"L{i}.{k}", fk]
                u = M.mfdb_core_add_entity_record_105(self.mp, f"e{i}", vals)["Values"][-1][0]
                self.rows[i].append([u, vals[0], fk])

    # -- reference model -----------------------------------------------------
    def children(self, ent):
        return [(c, m) for c, (p, m) in self.parent.items() if p == ent]

    def plan(self, ent, u, deleted, nulls):
        """Return True if blocked."""
        deleted.add((ent, u))
        for c, mode in self.children(ent):
            for row in self.rows[c]:
                if row[2] != u or (c, row[0]) in deleted:
                    continue
                if mode == "restrict":
                    return True
                if mode == "cascade":
                    if self.plan(c, row[0], deleted, nulls):
                        return True
                else:
                    nulls.add((c, row[0]))
        return False

    def apply_model(self, deleted, nulls):
        for i in self.rows:
            self.rows[i] = [[u, l, (None if (i, u) in nulls and (i, u) not in deleted else fk)]
                            for (u, l, fk) in self.rows[i] if (i, u) not in deleted]

    # -- disk ----------------------------------------------------------------
    def files(self):
        out = {"manifest": open(self.mp, "rb").read()}
        for i in range(self.n_ent):
            out[f"e{i}"] = open(M._get_entity_path(self.mp, f"e{i}"), "rb").read()
        return out

    def disk_rows(self, i):
        doc = json.load(open(M._get_entity_path(self.mp, f"e{i}")))
        return [list(r) for r in doc["Values"]]

    def manifest_counts(self):
        doc = json.load(open(self.mp))
        names = [f["name"] for f in doc["Fields"]]
        ie, ic = names.index("entity_name"), names.index("record_count")
        return {row[ie]: row[ic] for row in doc["Values"]}

    def assert_matches_model(self, ctx):
        counts = self.manifest_counts()
        for i in range(self.n_ent):
            got = self.disk_rows(i)
            want = self.rows[i]
            if i == 0:
                want = [[u, l] for (u, l, _fk) in want]
            self.tc.assertEqual(got, want, f"{ctx}: e{i} rows differ from model")
            self.tc.assertEqual(counts.get(f"e{i}"), len(want), f"{ctx}: e{i} manifest count")


class TestCascadeFuzz(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="stress_casc_")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _fresh(self, r):
        d = tempfile.mkdtemp(dir=self.tmp)
        return _World(d, r, self)

    def test_random_deletes_match_reference_model(self):
        r = _rng("cascfuzz")
        blocked_seen = ok_seen = null_seen = 0
        for t in range(40 * SCALE):
            w = self._fresh(r)
            w.assert_matches_model(f"t{t} initial")
            for step in range(r.randint(1, 8)):
                pool = [(i, row[0]) for i in w.rows for row in w.rows[i]]
                if not pool:
                    break
                ent, u = r.choice(pool)
                deleted, nulls = set(), set()
                blocked = w.plan(ent, u, deleted, nulls)
                before = w.files()
                ctx = f"t{t} step{step} delete e{ent}"
                if blocked:
                    blocked_seen += 1
                    with self.assertRaises(M.MFDBCoreError) as cm:
                        M.mfdb_core_delete_entity_record_105(w.mp, f"e{ent}", u)
                    self.assertEqual(cm.exception.code, M.E_MFDB_FK_RESTRICT_VIOLATION, ctx)
                    self.assertEqual(w.files(), before, f"{ctx}: blocked delete modified a file")
                else:
                    ok_seen += 1
                    null_seen += bool(nulls)
                    M.mfdb_core_delete_entity_record_105(w.mp, f"e{ent}", u)
                    w.apply_model(deleted, nulls)
                w.assert_matches_model(ctx)
        LOG.info("cascade fuzz: ok=%d blocked=%d with-null=%d", ok_seen, blocked_seen, null_seen)
        self.assertGreater(blocked_seen, 0, "fuzz never exercised the restrict path")
        self.assertGreater(ok_seen, 0)
        self.assertGreater(null_seen, 0, "fuzz never exercised the null path")

    def test_injected_failure_at_every_commit_step_rolls_back(self):
        r = _rng("cascfail")
        injected = 0
        # root-commit hooks are hit by every delete, so they get double weight
        names = ["_mfdb_delete_record_105_raw", "_mfdb_write_cell_105", "_write_entity_doc",
                 "_update_manifest_record_count", "_write_entity_doc", "_update_manifest_record_count"]
        for t in range(100 * SCALE):
            w = self._fresh(r)
            pool = [(i, row[0]) for i in w.rows for row in w.rows[i]]
            if not pool:
                continue
            ent, u = r.choice(pool)
            deleted, nulls = set(), set()
            if w.plan(ent, u, deleted, nulls):
                continue
            target = r.choice(names)
            kth = r.randint(1, 2)
            real = getattr(M, target)
            calls = {"n": 0}

            def flaky(*a, _real=real, _calls=calls, _k=kth, **k):
                _calls["n"] += 1
                if _calls["n"] == _k:
                    raise OSError(f"injected failure in call {_k}")
                return _real(*a, **k)

            before = w.files()
            setattr(M, target, flaky)
            try:
                try:
                    M.mfdb_core_delete_entity_record_105(w.mp, f"e{ent}", u)
                    failed = False
                except OSError:
                    failed = True
            finally:
                setattr(M, target, real)
            ctx = f"t{t} {target}#{kth} e{ent}"
            if failed:
                injected += 1
                self.assertEqual(w.files(), before, f"{ctx}: failed delete left partial state")
            else:
                w.apply_model(deleted, nulls)
                w.assert_matches_model(ctx)
        LOG.info("cascade fuzz: %d injected failures all rolled back", injected)
        self.assertGreater(injected, 15, "failure injection almost never fired")


# ===========================================================================
# D. Env-file parser
# ===========================================================================

_PAYLOADS = [
    "import os\nopen({m!r},'w').write('x')",
    "X = __import__('os').system('touch {m}')",
    "ADV_STRESS = open({m!r}, 'w')",
    "ADV_STRESS = (lambda: open({m!r}, 'w'))()",
    "ADV_STRESS = [open({m!r}, 'w') for _ in range(1)]",
    "ADV_STRESS = f\"{{open({m!r}, 'w')}}\"",
    "ADV_STRESS = (y := open({m!r}, 'w'))",
    "ADV_STRESS = 'a' if open({m!r}, 'w') else 'b'",
    "ADV_STRESS = \"{{}}\".__class__.__mro__[1].__subclasses__()",
    "ADV_STRESS = ().__class__",
    "ADV_STRESS = [1,2,3]",
    "ADV_STRESS = {{'a': 1}}",
    "ADV_STRESS = None",
    "ADV_STRESS = b'bytes'",
    "ADV_STRESS = 1 + open({m!r}, 'w').write('x')",
    "ADV_STRESS: str = open({m!r}, 'w')",
    "ADV_STRESS += open({m!r}, 'w')",
    "def f():\n    open({m!r}, 'w')\nf()",
    "class A:\n    x = open({m!r}, 'w')",
    "with open({m!r}, 'w'): pass",
    "exec(\"open({m!r}, 'w')\")",
    "eval(\"open({m!r}, 'w')\")",
    "globals()['resolve_path'] = 1",
    "resolve_path = 'x'",
    "lowercase = 'x'",
    "A, B = 1, 2",
    "A = B = 3",
    "ADV_STRESS = " + "(" * 400 + "1" + ")" * 400,
    "ADV_STRESS = " + "[" * 5000 + "]" * 5000,
    "ADV_STRESS = '" + "x" * 2_000_000 + "'",
    "ADV_STRESS = 9" * 1 + "9" * 5000,
    "\x00ADV_STRESS = 1",
    "ADV_STRESS = 1\n\x00",
    "ADV_STRESS = 'unterminated",
    "ADV_STRESS = ",
    "= 1",
    "ADV_STRESS = 1;open({m!r}, 'w')",
]


class TestEnvParserStress(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="stress_env_")
        self.marker = os.path.join(self.tmp, "PWNED")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)
        for k in list(vars(Env)):
            if k.startswith("ADV_STRESS"):
                Env.__dict__.pop(k, None)

    def _file(self, text, name="env_file.py", mode="w"):
        p = os.path.join(self.tmp, name)
        with open(p, mode, errors="surrogateescape") as fh:
            fh.write(text)
        return p

    def test_payload_corpus_never_executes_or_partially_applies(self):
        keep = {k: v for k, v in vars(Env).items() if callable(v)}
        for idx, pl in enumerate(_PAYLOADS):
            text = pl.replace("{m}", self.marker).replace("{m!r}", repr(self.marker)) \
                if "{m" in pl else pl
            text = text.replace("{{", "{").replace("}}", "}")
            p = self._file("ADV_STRESS_OK = 'first'\n" + text + "\n")
            try:
                ok = Env.source_env(p)
            except Exception as exc:  # source_env must swallow everything
                self.fail(f"payload #{idx} escaped source_env: {type(exc).__name__}: {exc}")
            self.assertFalse(os.path.exists(self.marker), f"payload #{idx} EXECUTED")
            if not ok:
                self.assertFalse(hasattr(Env, "ADV_STRESS_OK"),
                                 f"payload #{idx}: refused file was partially applied")
            Env.__dict__.pop("ADV_STRESS_OK", None)
            Env.__dict__.pop("ADV_STRESS", None)
            for k, v in keep.items():
                self.assertIs(getattr(Env, k), v, f"payload #{idx} clobbered {k}")

    def test_random_garbage_never_crashes_or_executes(self):
        r = _rng("envfuzz")
        alphabet = string.printable + "éß漢\u202e\x00\x0b"
        toks = ["import", "open", "exec", "lambda", "=", "(", ")", "[", "]", "{", "}", ":", "'", '"',
                "\n", " ", "ADV_STRESS", "__import__", "os", ".", ",", "*", "**", "@", "-", "0x", "1e999"]
        for t in range(300 * SCALE):
            if r.random() < 0.5:
                text = "".join(r.choice(alphabet) for _ in range(r.randint(0, 300)))
            else:
                text = " ".join(r.choice(toks) for _ in range(r.randint(0, 60)))
            p = self._file(text)
            try:
                ok = Env.source_env(p)
            except Exception as exc:
                self.fail(f"fuzz #{t} escaped source_env: {type(exc).__name__}: {exc}; text={text!r}")
            self.assertFalse(os.path.exists(self.marker))
            self.assertIsInstance(ok, bool)

    def test_random_valid_files_round_trip(self):
        r = _rng("envvalid")
        for t in range(120 * SCALE):
            pairs = {}
            for _ in range(r.randint(1, 8)):
                name = "ADV_STRESS_" + "".join(r.choice(string.ascii_uppercase + "_") for _ in range(r.randint(1, 8)))
                pairs[name] = r.choice([_rand_word(r, 8), r.randint(-10**6, 10**6), r.random(), r.choice([True, False])])
            if r.random() < 0.5:
                text = "\n".join(f"{k} = {v!r}" for k, v in pairs.items())
                got = Env._parse_env_file(__import__("pathlib").Path(self._file(text)))
            else:
                got = Env._parse_env_file(__import__("pathlib").Path(self._file(json.dumps(pairs), "e.json")))
            self.assertEqual(got, pairs, f"valid file #{t} did not round-trip")


# ===========================================================================
# E. parse_json
# ===========================================================================

def _rand_json(r, depth=0):
    k = r.random()
    if depth > 3 or k < 0.3:
        return r.choice([None, True, False, r.randint(-5, 5), _rand_word(r, 5), r.random()])
    if k < 0.65:
        return {_rand_word(r, 3): _rand_json(r, depth + 1) for _ in range(r.randint(0, 4))}
    return [_rand_json(r, depth + 1) for _ in range(r.randint(0, 4))]


class TestParseJsonStress(unittest.TestCase):

    def test_embedded_objects_round_trip(self):
        r = _rng("pjson")
        for t in range(300 * SCALE):
            obj = {"k": _rand_json(r)}
            body = json.dumps(obj)
            pre = r.choice(["", "Here you go:\n", "```json\n", "noise ] ) > ", "\ufeff"])
            post = r.choice(["", "\n```", " trailing } text", "\n\nThanks!"])
            got = Parse.parse_json(pre + body + post)
            self.assertEqual(got, obj, f"#{t} pre={pre!r} post={post!r}")

    def test_garbage_raises_json_error_not_something_else(self):
        r = _rng("pjgarb")
        for t in range(300 * SCALE):
            text = "".join(r.choice(string.printable) for _ in range(r.randint(0, 200)))
            try:
                Parse.parse_json(text)
            except json.JSONDecodeError:
                pass
            except Exception as exc:
                self.fail(f"#{t}: {type(exc).__name__} instead of JSONDecodeError for {text!r}")

    def test_large_prefixed_document_does_not_copy_the_text(self):
        big = {"rows": [[i, "x" * 20] for i in range(120_000 * min(SCALE, 3))]}
        body = json.dumps(big)
        text = "preamble\n" + body + "\ntrailing"

        def peak(fn):
            tracemalloc.start()
            try:
                fn()
                return tracemalloc.get_traced_memory()[1]
            finally:
                tracemalloc.stop()

        clean = peak(lambda: json.loads(body))
        prefixed = peak(lambda: Parse.parse_json(text))
        LOG.info("parse_json peak: clean=%d prefixed=%d len(text)=%d", clean, prefixed, len(text))
        # json.loads(body) fails on the prefixed text first (cheap), then raw_decode
        # parses in place. A slice-copy implementation costs an extra len(text) bytes
        # (and str is 1-4 bytes/char), so the margin below catches it.
        self.assertLess(prefixed, clean + len(text) // 2,
                        "parse_json materialised a copy of the whole text")
        self.assertEqual(Parse.parse_json(text), big)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    unittest.main(verbosity=2)
