# Job family (libraries_105, Release_Version 301)

Reads, validates and runs **BEJSON 104a Job Schema** files (JobMaker `JobTask`, 11 fields) from the 105 library tier. Wraps the frozen Core; touches nothing in it. Credit: Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton

Install: copy this `Job/` folder into `libraries_105/Lib_PY/`. Needs Python 3.10+ and `Lib_PY/Core` beside it (or `ADMIN_LIBRARIES_105` set).

| File | Job |
|---|---|
| `lib_bejson_Job_bejson_errors.py` | Codes 390-419, `JobError` |
| `lib_bejson_Job_job_core.py` | Build, load, read, mutate, locked save/update, template, legacy normalise |
| `lib_bejson_Job_job_validator.py` | Plan check, collects all errors; optional Book Document link check |
| `lib_bejson_Job_job_runner.py` | `JobRunner` (step/run/ingest), gates, CLI |

```python
import sys; sys.path.insert(0, "Lib_PY/Job")
import lib_bejson_Job_job_core as jc, lib_bejson_Job_job_runner as jr, lib_bejson_Job_job_validator as jv

doc = jc.bejson_job_core_new_job("Ship it", [{"name": "Draft", "description": "Write the draft.", "audit_enabled": True}])
jc.bejson_job_core_save("proj/jobs/ship.bejson", doc)            # validates, locks, writes atomically
runner = jr.JobRunner("proj", "jobs/ship.bejson", executor=lambda pkg: "Draft text " * 10,
                      gate=jr.GateConfig("standard", min_words=5))
runner.run()                                                       # one task at a time; stops on a gate failure
print(jv.bejson_job_validator_get_report(jv.bejson_job_validator_validate_file("proj/jobs/ship.bejson")))
```

CLI: `python3 lib_bejson_Job_job_runner.py --validate|--inspect|--prompt|--step|--run|--ingest JOB [--executor mod:fn] [--project-root DIR]`.
Exit codes: 0 ok, 1 runtime failure or gate failed, 20 Core not found, 30 validation failure.

Rules baked in: no shell command is ever run or carried (`test_cmd`/`Target_File` refused); `task_reference` paths are listed, never read; staged outputs go to `runs/<job slug>/<task id>.md`; an invalid document is never written; the file stays 104a (arrays in `task_context`/`task_reference` are the one scoped exception, so Core's stage-0 validator is not used on job files).
Tests: `python3 Lib_PY/Job/tests/test_job_family.py` (29 tests).
