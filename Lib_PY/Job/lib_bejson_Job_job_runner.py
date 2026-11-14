"""
Library:         lib_bejson_Job_job_runner.py
Family:          Job
Module Purpose:  Job RUNNER: runs a BEJSON 104a Job Schema one task at a time (identify -> assemble context -> execute -> gate -> atomic save), stages every output under runs/<job slug>/, and ingests staged outputs through an in-process gate. Also the family CLI.
Architecture:    Executor-agnostic: the caller supplies `executor(package) -> text` (an AI client, a script, a person). No shell command is ever run for a job (BKS-1 J5); gates are declarative and in-process (BKS-1 C.4). task_reference paths are listed to the executor and never read (BKS-1 A.3). State changes go through core's lock + atomic writer, and an invalid document is never written.
Version:         1.0.0
Release_Version: 301
Date:            2026-11-14
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Format_Creator:  Elton Boehnen
RELATIONAL_ID:   c076bd27-de3c-4472-92db-f81eeefb8490
"""
from __future__ import annotations

import argparse
import importlib
import json
import logging
import os
import re
import sys
import tempfile
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from lib_bejson_Job_bejson_errors import (
    E_JOB_EXECUTOR_FAILED,
    E_JOB_GATE_UNKNOWN,
    E_JOB_NO_EXECUTOR,
    E_JOB_STAGE_WRITE_FAILED,
    EXIT_ENVIRONMENT_FAILURE,
    EXIT_OK,
    EXIT_RUNTIME_FAILURE,
    EXIT_VALIDATION_FAILURE,
    E_JOB_CORE_NOT_FOUND,
    JobError,
)
import lib_bejson_Job_job_core as jc
from lib_bejson_Job_job_validator import bejson_job_validator_get_report, bejson_job_validator_validate_file

logger = logging.getLogger("bejson_job")
VERSION = "1.0.0"
CREDIT = "Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton"

# ---------------------------------------------------------------------------
# Gates (BKS-1 C.4): declarative, in-process, never a shell
# ---------------------------------------------------------------------------
GATE_PROFILES = ("none", "nonempty", "standard", "strict")   # nonempty is this family's own: min_words 1, nothing else
KNOWN_RULES = ("min_words", "max_words", "must_include", "no_placeholders", "md_wellformed")
_PLACEHOLDER_RE = re.compile(r"\bTODO\b|\bTBD\b|\bFIXME\b|lorem ipsum|\[insert[^\]]*\]|\[\.\.\.\]", re.IGNORECASE)
_FENCE_RE = re.compile(r"^\s{0,3}```", re.MULTILINE)
_FENCED_BLOCK_RE = re.compile(r"^\s{0,3}```.*?^\s{0,3}```[^\n]*$", re.MULTILINE | re.DOTALL)
_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}[ \t]+(.+?)[ \t]*#*[ \t]*$", re.MULTILINE)


@dataclass
class GateConfig:
    """profile: none | nonempty | standard | strict. rules, when given, replaces the profile entirely (unknown keys refused, E_JOB_GATE_UNKNOWN)."""
    profile: str = "standard"
    min_words: int = 1
    max_words: Optional[int] = None
    must_include: Sequence[str] = field(default_factory=tuple)
    rules: Optional[Dict[str, Any]] = None


def bejson_job_runner_normalise_text(text: str) -> str:
    """BKS-1 V8: CRLF and CR to LF, trailing whitespace of the whole body stripped."""
    return str(text).replace("\r\n", "\n").replace("\r", "\n").rstrip()


def bejson_job_runner_word_count(text: str) -> int:
    """BKS-1 V9: fenced code blocks removed, then whitespace-separated tokens."""
    return len(_FENCED_BLOCK_RE.sub(" ", bejson_job_runner_normalise_text(text)).split())


def bejson_job_runner_gate_rules(config: GateConfig) -> Dict[str, Any]:
    if config.rules is not None:
        unknown = [k for k in config.rules if k not in KNOWN_RULES]
        if unknown:
            raise JobError(f"unknown gate rule(s): {unknown}", E_JOB_GATE_UNKNOWN)
        return dict(config.rules)
    if config.profile not in GATE_PROFILES:
        raise JobError(f"unknown gate profile {config.profile!r}; expected one of {GATE_PROFILES}", E_JOB_GATE_UNKNOWN)
    rules: Dict[str, Any] = {}
    if config.profile == "nonempty":
        rules["min_words"] = 1
    elif config.profile in ("standard", "strict"):
        rules.update({"min_words": config.min_words, "no_placeholders": True})
        if config.profile == "strict":
            rules["md_wellformed"] = True
            if config.must_include:
                rules["must_include"] = list(config.must_include)
    if config.max_words is not None and config.profile != "none":
        rules["max_words"] = config.max_words
    return rules


def bejson_job_runner_run_gate(text: str, rules: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Returns (passed, reasons). reasons is empty when passed."""
    unknown = [k for k in rules if k not in KNOWN_RULES]
    if unknown:
        raise JobError(f"unknown gate rule(s): {unknown}", E_JOB_GATE_UNKNOWN)
    body = bejson_job_runner_normalise_text(text)
    reasons: List[str] = []
    words = bejson_job_runner_word_count(body)
    if "min_words" in rules and words < rules["min_words"]:
        reasons.append(f"too short: {words} words, at least {rules['min_words']} required")
    if "max_words" in rules and words > rules["max_words"]:
        reasons.append(f"too long: {words} words, at most {rules['max_words']} allowed")
    if rules.get("no_placeholders") and _PLACEHOLDER_RE.search(body):
        reasons.append(f"placeholder text found: {_PLACEHOLDER_RE.search(body).group(0)!r}")
    if rules.get("md_wellformed") and len(_FENCE_RE.findall(body)) % 2 != 0:
        reasons.append("unbalanced code fence")
    if rules.get("must_include"):
        headings = {h.strip().lower() for h in _HEADING_RE.findall(body)}
        missing = [h for h in rules["must_include"] if str(h).strip().lower() not in headings]
        if missing:
            reasons.append(f"missing required heading(s): {missing}")
    return (not reasons, reasons)


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------
Executor = Callable[[Dict[str, Any]], str]


@dataclass
class StepResult:
    task_id: str
    task_order: int
    task_name: str
    passed: bool
    reasons: List[str]
    staged_path: str
    job_complete: bool

    def as_dict(self) -> dict:
        return dict(self.__dict__)


class JobRunner:
    """
    project_root: folder holding jobs/ and runs/ (every path below is resolved under it and path-guarded).
    job_path: the job file, absolute or relative to project_root.
    """

    def __init__(self, project_root: str, job_path: str, *, executor: Optional[Executor] = None,
                 gate: Optional[GateConfig] = None, lock_timeout: int = 10):
        jc.bejson_job_core_require_core()
        self.project_root = os.path.abspath(project_root)
        self.job_path = jc.bejson_job_core_safe_join(self.project_root, job_path) if not os.path.isabs(job_path) else os.path.abspath(job_path)
        self.job_slug = jc.bejson_job_core_slug(re.sub(r"\.bejson\Z", "", os.path.basename(self.job_path)))
        self.executor = executor
        self.gate = gate or GateConfig()
        self.lock_timeout = lock_timeout
        bejson_job_runner_gate_rules(self.gate)   # refuse an unknown profile / rule up front

    # -- paths --------------------------------------------------------------
    def staged_relative_path(self, task_id: str) -> str:
        return f"runs/{self.job_slug}/{jc.bejson_job_core_task_id_slug(task_id)}.md"

    def staged_path(self, task_id: str) -> str:
        return jc.bejson_job_core_safe_join(self.project_root, "runs", self.job_slug, jc.bejson_job_core_task_id_slug(task_id) + ".md")

    def read_staged(self, task_id: str) -> Optional[str]:
        path = self.staged_path(task_id)
        if not os.path.isfile(path):
            return None
        with open(path, "r", encoding="utf-8") as handle:
            return handle.read()

    def stage_output(self, task_id: str, text: str) -> str:
        """Staging only (BKS-1 J3): atomic text write, temp file in the same folder + fsync + replace. Returns the relative path."""
        path = self.staged_path(task_id)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(str(text))
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp, path)
        except OSError as exc:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise JobError(f"could not stage output for {task_id}: {exc}", E_JOB_STAGE_WRITE_FAILED) from exc
        return self.staged_relative_path(task_id)

    # -- reading ------------------------------------------------------------
    def load(self) -> dict:
        return jc.bejson_job_core_load(self.job_path)

    def inspect(self) -> dict:
        doc = self.load()
        nxt = jc.bejson_job_core_next_task(doc)
        info = {"job": self.job_slug, "goal": doc.get("Job_Goal"), "job_type": doc.get("Job_Type"), "job_subtype": doc.get("Job_Subtype"),
                **jc.bejson_job_core_progress(doc)}
        info["next_task"] = None if nxt is None else {"task_id": nxt["task_id"], "task_order": nxt["task_order"], "task_name": nxt["task_name"]}
        return info

    def build_package(self, doc: dict, task: dict) -> dict:
        """Everything the executor gets for ONE task. References are listed with an `exists` flag and never read."""
        plan = None
        if doc.get("Contextualize_Plan") is True:
            plan = {"goal": doc.get("Job_Goal"),
                    "tasks": [{"task_order": t["task_order"], "task_name": t["task_name"], "task_description": t["task_description"]}
                              for t in jc.bejson_job_core_tasks(doc)]}
        last = None
        if doc.get("Contextualize_Last") is True and task["task_order"] > 1:
            previous = next((t for t in jc.bejson_job_core_tasks(doc) if t["task_order"] == task["task_order"] - 1), None)
            if previous is not None:
                text = self.read_staged(previous["task_id"])
                if text is not None:
                    last = {"task_id": previous["task_id"], "task_name": previous["task_name"], "output": text}
        references = []
        for ref in task["task_reference"]:
            try:
                exists = os.path.exists(jc.bejson_job_core_safe_join(self.project_root, ref))
            except JobError:
                exists = False
            references.append({"ref": ref, "exists": exists})
        package = {
            "job": self.job_slug,
            "task": {k: task[k] for k in ("task_id", "task_order", "task_name", "task_description", "audit_enabled", "task_mandatory")},
            "context_text": jc.bejson_job_core_context_text(task),
            "references": references,
            "plan": plan,
            "last_output": last,
        }
        package["prompt"] = self.render_prompt(package)
        return package

    @staticmethod
    def render_prompt(package: dict) -> str:
        task = package["task"]
        parts: List[str] = []
        if package.get("plan"):
            parts.append("# Job goal\n" + str(package["plan"]["goal"]))
            parts.append("# All tasks in this job\n" + "\n".join(f"{t['task_order']}. {t['task_name']}" for t in package["plan"]["tasks"]))
        parts.append(f"# Your task: {task['task_order']}. {task['task_name']}\n{task['task_description']}")
        if package.get("context_text"):
            parts.append("# Context\n" + package["context_text"])
        if package.get("references"):
            parts.append("# Files to consult (not included)\n" + "\n".join(f"- {r['ref']}" for r in package["references"]))
        if package.get("last_output"):
            parts.append(f"# Output of the previous task ({package['last_output']['task_name']})\n" + package["last_output"]["output"])
        parts.append("Do only this task. Return the deliverable as plain Markdown text.")
        return "\n\n".join(parts)

    # -- state changes ------------------------------------------------------
    def _evaluate(self, task: dict, text: str) -> Tuple[bool, List[str]]:
        if task["audit_enabled"] is not True:
            return True, []
        return bejson_job_runner_run_gate(text, bejson_job_runner_gate_rules(self.gate))

    def _record(self, task: dict, passed: bool, reasons: List[str]) -> dict:
        audit = task["audit_enabled"] is True
        reason_text = "; ".join(reasons)

        def mutate(doc: dict) -> None:
            jc.bejson_job_core_set_task_state(
                doc, task["task_id"], completed=passed,
                audit_passed=(passed if audit else False),
                audit_fail_reason=("" if passed else reason_text))

        return jc.bejson_job_core_update(self.job_path, mutate, lock_timeout=self.lock_timeout)

    def _result(self, task: dict, passed: bool, reasons: List[str], doc: dict) -> StepResult:
        return StepResult(task["task_id"], task["task_order"], task["task_name"], passed, reasons,
                          self.staged_relative_path(task["task_id"]), doc.get("Job_Complete") is True)

    def step(self) -> Optional[StepResult]:
        """Executes exactly ONE task (the first not complete). Returns None when the job is already complete."""
        doc = self.load()
        task = jc.bejson_job_core_next_task(doc)
        if task is None:
            return None
        if self.executor is None:
            raise JobError("step() needs an executor; use ingest() for outputs produced elsewhere", E_JOB_NO_EXECUTOR)
        package = self.build_package(doc, task)
        try:
            output = self.executor(package)
        except Exception as exc:  # executor is caller code; any failure leaves the job untouched
            logger.error("executor failed on task %s: %s", task["task_id"], exc)
            raise JobError(f"executor raised {type(exc).__name__}: {exc}", E_JOB_EXECUTOR_FAILED) from exc
        if not isinstance(output, str):
            raise JobError(f"executor returned {type(output).__name__}, expected text", E_JOB_EXECUTOR_FAILED)
        self.stage_output(task["task_id"], output)
        passed, reasons = self._evaluate(task, output)
        logger.info("task %s (%s): %s", task["task_order"], task["task_name"], "complete" if passed else "gate failed: " + "; ".join(reasons))
        return self._result(task, passed, reasons, self._record(task, passed, reasons))

    def run(self, max_steps: Optional[int] = None, stop_on_fail: bool = True) -> List[StepResult]:
        results: List[StepResult] = []
        while max_steps is None or len(results) < max_steps:
            outcome = self.step()
            if outcome is None:
                break
            results.append(outcome)
            if not outcome.passed and stop_on_fail:
                break
        return results

    def ingest(self, stop_on_fail: bool = True) -> List[StepResult]:
        """
        BKS-1 J4: for each task, in order, that has a staged file and is not already verified (complete, and with an audit
        that passed when audit is enabled): gate the staged text. Pass -> complete; fail -> task_completed false and the
        reason recorded. By default stops at the first failure so later tasks never complete ahead of an earlier one.
        """
        results: List[StepResult] = []
        for task in jc.bejson_job_core_tasks(self.load()):
            verified = task["task_completed"] is True and (task["audit_enabled"] is not True or task["audit_passed"] is True)
            text = None if verified else self.read_staged(task["task_id"])
            if verified or text is None:
                continue
            passed, reasons = self._evaluate(task, text)
            doc = self._record(task, passed, reasons)
            results.append(self._result(task, passed, reasons, doc))
            if not passed and stop_on_fail:
                break
        return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _load_executor(spec: str) -> Executor:
    """'module:callable' -- caller-trusted code, importable from the current directory or PYTHONPATH."""
    module_name, _, attr = spec.partition(":")
    if not module_name or not attr:
        raise JobError(f"--executor must look like module:callable, got {spec!r}", E_JOB_NO_EXECUTOR)
    sys.path.insert(0, os.getcwd())
    return getattr(importlib.import_module(module_name), attr)


def _default_project_root(job_path: str) -> str:
    parent = os.path.dirname(os.path.abspath(job_path))
    return os.path.dirname(parent) if os.path.basename(parent) == "jobs" else parent


def _emit(payload: Any, as_json: bool) -> None:
    text = json.dumps(payload, indent=2, ensure_ascii=False) if as_json or not isinstance(payload, str) else payload
    sys.stdout.write(text + "\n")


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="lib_bejson_Job_job_runner", description="Run and check BEJSON 104a Job Schema files, one task at a time.")
    parser.add_argument("--version", action="store_true", help="print version and credit")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--validate", metavar="JOB", help="validate a job file (plan check P)")
    action.add_argument("--inspect", metavar="JOB", help="progress and next task")
    action.add_argument("--prompt", metavar="JOB", help="print the assembled prompt for the next task")
    action.add_argument("--step", metavar="JOB", help="execute exactly one task (needs --executor)")
    action.add_argument("--run", metavar="JOB", help="execute tasks until done or a gate fails (needs --executor)")
    action.add_argument("--ingest", metavar="JOB", help="gate staged outputs in runs/<job>/ and record the result")
    parser.add_argument("--executor", metavar="MODULE:CALLABLE", help="callable(package) -> text; trusted code you choose")
    parser.add_argument("--project-root", metavar="DIR", help="folder holding jobs/ and runs/ (default: derived from the job path)")
    parser.add_argument("--book", metavar="BOOK", help="with --validate: also check the plan against this Book Document")
    parser.add_argument("--gate-profile", default="standard", choices=GATE_PROFILES)
    parser.add_argument("--min-words", type=int, default=1)
    parser.add_argument("--max-words", type=int, default=None)
    parser.add_argument("--must-include", action="append", default=[], metavar="HEADING", help="required heading (strict profile); repeatable")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="%(levelname)s %(name)s: %(message)s")
    if args.version:
        _emit(f"lib_bejson_Job_job_runner {VERSION} (Release_Version 301)\n{CREDIT}", False)
        return EXIT_OK
    try:
        jc.bejson_job_core_require_core()
    except JobError as exc:
        logger.error("%s", exc)
        return EXIT_ENVIRONMENT_FAILURE

    job = args.validate or args.inspect or args.prompt or args.step or args.run or args.ingest
    if not job:
        parser.print_help(sys.stderr)
        return EXIT_OK
    try:
        if args.validate:
            result = bejson_job_validator_validate_file(args.validate, book_path=args.book)
            _emit({"valid": result.valid, "errors": [str(i) for i in result.errors], "warnings": [str(i) for i in result.warnings]}
                  if args.json else bejson_job_validator_get_report(result), args.json)
            return EXIT_OK if result.valid else EXIT_VALIDATION_FAILURE

        gate = GateConfig(profile=args.gate_profile, min_words=args.min_words, max_words=args.max_words, must_include=tuple(args.must_include))
        executor = _load_executor(args.executor) if args.executor else None
        runner = JobRunner(args.project_root or _default_project_root(job), job, executor=executor, gate=gate)
        checked = bejson_job_validator_validate_file(runner.job_path)
        if not checked.valid:
            _emit(bejson_job_validator_get_report(checked), False)
            return EXIT_VALIDATION_FAILURE

        if args.inspect:
            _emit(runner.inspect(), True)
        elif args.prompt:
            doc = runner.load()
            task = jc.bejson_job_core_next_task(doc)
            _emit("job complete" if task is None else runner.build_package(doc, task)["prompt"], False)
        elif args.step:
            outcome = runner.step()
            _emit("job complete" if outcome is None else outcome.as_dict(), True)
            return EXIT_OK if outcome is None or outcome.passed else EXIT_RUNTIME_FAILURE
        elif args.run:
            outcomes = runner.run()
            _emit([o.as_dict() for o in outcomes], True)
            return EXIT_OK if all(o.passed for o in outcomes) else EXIT_RUNTIME_FAILURE
        elif args.ingest:
            outcomes = runner.ingest()
            _emit([o.as_dict() for o in outcomes], True)
            return EXIT_OK if all(o.passed for o in outcomes) else EXIT_RUNTIME_FAILURE
        return EXIT_OK
    except JobError as exc:
        logger.error("%s", exc)
        return EXIT_ENVIRONMENT_FAILURE if exc.code == E_JOB_CORE_NOT_FOUND else EXIT_RUNTIME_FAILURE


if __name__ == "__main__":
    sys.exit(main())
