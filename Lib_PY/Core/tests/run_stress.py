"""
Library:        run_stress.py
Family:         Core (tests)
Description:    One-click stress-test launcher. Just run this file (Pydroid3 play
                 button, `python3 run_stress.py`, double-click, anything): it picks
                 a fresh random seed, chooses a scale, runs the whole stress suite
                 (tests/test_stress_suite.py), prints a summary and writes a report.

                 Zero required arguments, zero prompts, zero paths to type.
                 If the PREVIOUS run failed, that failing seed is replayed first so
                 a flaky failure is reproduced automatically instead of lost.

                 Optional (you never need them):
                   --scale N    iteration multiplier (default 3; 1 = quick)
                   --seed N     force a seed
                   --runs N     repeat with N fresh seeds (default 1)

                 Reports: tests/stress_reports/stress-<UTC timestamp>-seed<seed>.log
                          tests/stress_reports/last_run.json
                 Exit code 0 = all green, 1 = failures.

Version:        1.0.0
Date:           2026-10-12
Author:         Elton Boehnen
Contact:        boehnenelton2024@gmail.com | boehnenelton2024.pages.dev | github.com/boehnenelton
Format_Creator: Elton Boehnen
RELATIONAL_ID:  5b8e2f61-c4a7-4d90-9e13-2a6d7f0b84c5
Release_Version: 300
"""

import argparse
import datetime
import importlib
import io
import json
import logging
import os
import random
import sys
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
CORE = os.path.dirname(HERE)
REPORT_DIR = os.path.join(HERE, "stress_reports")
LAST_RUN = os.path.join(REPORT_DIR, "last_run.json")
DEFAULT_SCALE = 3

LOG = logging.getLogger("run_stress")


def _parse_args(argv):
    ap = argparse.ArgumentParser(description="One-click stress test (all arguments optional).")
    ap.add_argument("--scale", type=int, default=None)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--runs", type=int, default=1)
    # parse_known_args: IDEs / launchers sometimes inject stray arguments.
    args, _unknown = ap.parse_known_args(argv)
    return args


def _load_last_failure():
    try:
        with open(LAST_RUN, encoding="utf-8") as fh:
            data = json.load(fh)
        if data.get("status") == "FAILED" and isinstance(data.get("seed"), int):
            return data
    except (OSError, ValueError):
        pass
    return None


def _run_once(seed, scale, log_path):
    """Run the whole suite in-process with the given seed/scale. Returns a result dict."""
    os.environ["STRESS_SEED"] = str(seed)
    os.environ["STRESS_SCALE"] = str(scale)
    if CORE not in sys.path:
        sys.path.insert(0, CORE)
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    sys.modules.pop("test_stress_suite", None)          # re-read seed/scale from env
    suite_mod = importlib.import_module("test_stress_suite")
    suite = unittest.defaultTestLoader.loadTestsFromModule(suite_mod)

    stream = io.StringIO()
    runner = unittest.TextTestRunner(stream=stream, verbosity=2)
    t0 = time.time()
    result = runner.run(suite)
    elapsed = time.time() - t0
    text = stream.getvalue()
    with open(log_path, "w", encoding="utf-8") as fh:
        fh.write(text)
    failed = [str(t) for t, _ in result.failures] + [str(t) for t, _ in result.errors]
    return {
        "seed": seed, "scale": scale, "tests": result.testsRun,
        "failures": len(result.failures), "errors": len(result.errors),
        "skipped": len(result.skipped), "seconds": round(elapsed, 1),
        "failed_tests": failed, "log": log_path,
        "status": "PASSED" if result.wasSuccessful() else "FAILED",
        "_text": text,
    }


def main(argv=None):
    # Console shows only this tool's summary; the libraries' (intentional, fuzz-
    # provoked) warnings are swallowed here -- they are not failures.
    logging.getLogger().addHandler(logging.NullHandler())
    LOG.setLevel(logging.INFO)
    LOG.propagate = False
    if not LOG.handlers:
        _h = logging.StreamHandler(sys.stdout)
        _h.setFormatter(logging.Formatter("%(message)s"))
        LOG.addHandler(_h)
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    os.makedirs(REPORT_DIR, exist_ok=True)

    scale = max(1, args.scale if args.scale is not None else DEFAULT_SCALE)
    plan = []
    prior = _load_last_failure()
    if args.seed is not None:
        plan.append((args.seed, "forced seed"))
    else:
        if prior:
            plan.append((prior["seed"], "replaying the seed that FAILED last time"))
        for _ in range(max(1, args.runs)):
            plan.append((random.SystemRandom().randrange(1, 2**31), "fresh seed"))

    LOG.info("=" * 64)
    LOG.info("BEJSON STRESS TEST  |  scale=%d  |  %d run(s) planned", scale, len(plan))
    LOG.info("=" * 64)

    overall_ok = True
    last = None
    for seed, why in plan:
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S")
        log_path = os.path.join(REPORT_DIR, f"stress-{stamp}-seed{seed}.log")
        LOG.info("")
        LOG.info("-> seed %d (%s) ... running, takes about %d-%ds", seed, why, 5 * scale, 15 * scale)
        res = _run_once(seed, scale, log_path)
        last = res
        LOG.info("   %s  %d tests, %d failures, %d errors in %.1fs",
                 res["status"], res["tests"], res["failures"], res["errors"], res["seconds"])
        if res["status"] != "PASSED":
            overall_ok = False
            for name in res["failed_tests"]:
                LOG.info("   FAILED: %s", name)
            LOG.info("   full details: %s", log_path)
            LOG.info("   this seed will be replayed automatically on your next run")
        persist = {k: v for k, v in res.items() if not k.startswith("_")}
        persist["finished_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with open(LAST_RUN, "w", encoding="utf-8") as fh:
            json.dump(persist, fh, indent=2)

    LOG.info("")
    LOG.info("=" * 64)
    LOG.info("RESULT: %s", "ALL GREEN" if overall_ok else "FAILURES FOUND (see above)")
    LOG.info("Reports: %s", REPORT_DIR)
    LOG.info("=" * 64)
    return 0 if overall_ok else 1


if __name__ == "__main__":
    sys.exit(main())
