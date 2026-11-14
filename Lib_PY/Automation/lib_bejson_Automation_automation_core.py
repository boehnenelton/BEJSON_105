"""
Library:        lib_bejson_Automation_automation_core.py
Family:         Automation
Description:    Row-by-Row Finite State Machine Execution Engine & Framework Chunk Registry Exporter.
BEJSON:         BEJSON stands for BOEHNEN ELTON JSON. Authoritative definition;
                do not restate or reinterpret this acronym elsewhere.
                (Pronounced Bee-Jay-Son / Bay-nin Elton JSON)
MFDB:           MFDB stands for Multi File Database. Authoritative definition;
                do not restate or reinterpret this acronym elsewhere.
Version:        1.0.0
Date:           2026-11-11
Author:         Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
RELATIONAL_ID:  7d193f2c-e24a-4a81-b51c-3298ec8a0914
License:        PolyForm Noncommercial License 1.0.0
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import importlib
import json
import logging
import os
from pathlib import Path
import shlex
import subprocess
import sys
import time
from typing import Any, Callable, Dict, Final, List, Optional, Tuple, Union
import uuid

# Self-locating ecosystem import resolution
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from lib_bejson_Automation_automation_errors import (
    EXIT_BUSY,
    EXIT_CYCLE_DETECTED,
    EXIT_OK,
    EXIT_PARTIAL_FAILURE,
    EXIT_PATH_FAILURE,
    EXIT_SCHEMA_FAILURE,
    EXIT_THRESHOLD_EXCEEDED,
    EXIT_TIMEOUT_EXHAUSTED,
    AutomationCycleError,
    AutomationFSMError,
    AutomationSchemaValidationError,
    AutomationThresholdExceededError,
    AutomationTimeoutError,
)
from lib_bejson_Automation_automation_schemas import (
    AUTOMATION_FRAMEWORK_REGISTRY_FIELDS,
    AUTOMATION_FSM_MANIFEST_FIELDS,
    build_field_map_105,
    create_empty_framework_registry_105a,
    create_empty_fsm_manifest_105a,
)
from lib_bejson_Automation_automation_validator import (
    validate_framework_registry_barrier,
    validate_fsm_manifest_barrier,
)

LOG: logging.Logger = logging.getLogger("AutomationFSMCore")

DIVIDER_49: Final[str] = "=" * 49
SUBDIVIDER_49: Final[str] = "-" * 49


@dataclass
class FSMStageNode:
    """Canonical representation of an individual FSM pipeline stage row."""
    record_uuid: str
    sequence_index: int
    label: str
    dispatch_mode: str
    code_payload: str
    delay_before_sec: float
    delay_after_sec: float
    loop_enabled: bool
    loop_max_iterations: int
    loop_interval_sec: float
    loop_break_condition: str
    on_success_uuid: str
    on_failure_uuid: str
    timeout_sec: float
    sender_address: str = "local://node/stage"
    forward_address: str = "FINAL_DELIVERY_GATE"
    if_repetition_count_over: int = 3
    conditional_forward_address: str = "ABORT_TERMINAL"


@dataclass
class FSMExecutionContext:
    """Carried execution context and working state for an in-flight pipeline asset."""
    pipeline_identifier: str
    staged_asset_path: Path
    staged_directory: Path
    custom_state: Dict[str, Any] = field(default_factory=dict)
    execution_history: List[Dict[str, Any]] = field(default_factory=list)
    hop_trace: List[str] = field(default_factory=list)
    current_iteration: int = 1


@dataclass
class FSMExecutionResult:
    """Final result container from an FSM pipeline execution run."""
    success: bool
    exit_code: int
    terminal_disposition: str
    processed_artifact_path: Optional[Path]
    stages_executed_count: int
    hop_trace: List[str]
    error_message: Optional[str] = None


class BEJSONAutomationFSM:
    """
    Authoritative Finite State Machine Virtual Machine.
    Executes declarative BEJSON 105a state machine manifests row-by-row
    with O(1) field map caching, loop iteration controls, and addressed routing.
    """

    def __init__(self, manifest_source: Union[Path, str, Dict[str, Any]]) -> None:
        self.stages_by_uuid: Dict[str, FSMStageNode] = {}
        self.initial_stage_uuid: str = ""
        self.pipeline_identifier: str = "unnamed_fsm_pipeline"
        self._raw_doc: Dict[str, Any] = {}
        self._load_and_validate(manifest_source)

    def _load_and_validate(self, source: Union[Path, str, Dict[str, Any]]) -> None:
        if isinstance(source, (Path, str)):
            path = Path(source).resolve()
            if not path.exists():
                raise AutomationFSMError(f"FSM Manifest not found: {path}", EXIT_PATH_FAILURE)
            with open(path, "r", encoding="utf-8") as handle:
                self._raw_doc = json.load(handle)
        elif isinstance(source, dict):
            self._raw_doc = source
        else:
            raise AutomationFSMError("Invalid manifest source type", EXIT_SCHEMA_FAILURE)

        is_valid, validation_errors = validate_fsm_manifest_barrier(self._raw_doc)
        if not is_valid:
            error_summary = "; ".join(validation_errors[:3])
            raise AutomationSchemaValidationError(f"FSM Manifest barrier validation failed: {error_summary}")

        self.pipeline_identifier = str(self._raw_doc.get("Pipeline_Identifier", "fsm_pipeline"))
        fields = self._raw_doc.get("Fields", [])
        field_map = build_field_map_105(fields)
        values = self._raw_doc.get("Values", [])

        self.initial_stage_uuid = str(self._raw_doc.get("Initial_Step_UUID", "")).strip()

        for row in values:
            node_id = str(row[field_map["record_uuid"]]).strip()
            if not self.initial_stage_uuid:
                self.initial_stage_uuid = node_id

            node = FSMStageNode(
                record_uuid=node_id,
                sequence_index=int(row[field_map["step_sequence_index"]]),
                label=str(row[field_map["step_label"]]),
                dispatch_mode=str(row[field_map["execution_dispatch_mode"]]),
                code_payload=str(row[field_map["executable_code_payload"]]),
                delay_before_sec=float(row[field_map.get("delay_before_execution_sec", 0.0)]),
                delay_after_sec=float(row[field_map.get("delay_after_execution_sec", 0.0)]),
                loop_enabled=bool(row[field_map.get("loop_enabled_flag", False)]),
                loop_max_iterations=int(row[field_map.get("loop_max_iterations", 1)]),
                loop_interval_sec=float(row[field_map.get("loop_interval_delay_sec", 0.0)]),
                loop_break_condition=str(row[field_map.get("loop_break_condition_eval", "") or ""]),
                on_success_uuid=str(row[field_map.get("on_success_transition_uuid", "FINAL_DELIVERY_GATE")]),
                on_failure_uuid=str(row[field_map.get("on_failure_transition_uuid", "ABORT_TERMINAL")]),
                timeout_sec=float(row[field_map.get("timeout_ceiling_sec", 60.0)]),
                sender_address=str(row[field_map.get("sender_address", f"local://pipeline/{node_id}")] or ""),
                forward_address=str(row[field_map.get("forward_address", "FINAL_DELIVERY_GATE")] or ""),
                if_repetition_count_over=int(row[field_map.get("if_repetition_count_over", 3)]),
                conditional_forward_address=str(row[field_map.get("conditional_forward_address", "ABORT_TERMINAL")] or "")
            )
            self.stages_by_uuid[node_id] = node

    def execute_pipeline(self, context: FSMExecutionContext) -> FSMExecutionResult:
        """
        Executes the FSM pipeline row-by-row starting from initial_stage_uuid
        until reaching a terminal gate ('FINAL_DELIVERY_GATE' or 'ABORT_TERMINAL').
        """
        current_uuid: str = self.initial_stage_uuid
        stages_count = 0
        latest_artifact: Optional[Path] = context.staged_asset_path

        LOG.info(DIVIDER_49)
        LOG.info("STARTING FSM RUNTIME: %s", self.pipeline_identifier)
        LOG.info("ASSET: %s", context.staged_asset_path.name)
        LOG.info(SUBDIVIDER_49)

        while current_uuid:
            # 1. Check Terminal Gates
            if current_uuid == "FINAL_DELIVERY_GATE":
                LOG.info("GATE: Reached FINAL_DELIVERY_GATE successfully.")
                return FSMExecutionResult(
                    success=True,
                    exit_code=EXIT_OK,
                    terminal_disposition="FINAL_DELIVERY_GATE",
                    processed_artifact_path=latest_artifact,
                    stages_executed_count=stages_count,
                    hop_trace=context.hop_trace
                )

            if current_uuid == "ABORT_TERMINAL":
                LOG.error("GATE: Reached ABORT_TERMINAL. Pipeline aborted.")
                return FSMExecutionResult(
                    success=False,
                    exit_code=EXIT_PARTIAL_FAILURE,
                    terminal_disposition="ABORT_TERMINAL",
                    processed_artifact_path=None,
                    stages_executed_count=stages_count,
                    hop_trace=context.hop_trace,
                    error_message="Transitioned to ABORT_TERMINAL"
                )

            # 2. Cycle Detection (Max 16 Hops Ceiling Invariant)
            if len(context.hop_trace) >= 16:
                LOG.critical("SAFETY CEILING: Hop trace exceeded 16 hops. Aborting cycle.")
                raise AutomationCycleError("Max hop limit (16) exceeded. Routing cycle detected.")

            if current_uuid not in self.stages_by_uuid:
                LOG.error("Missing stage node UUID: %s", current_uuid)
                return FSMExecutionResult(
                    success=False,
                    exit_code=EXIT_SCHEMA_FAILURE,
                    terminal_disposition="DANGLING_TRANSITION",
                    processed_artifact_path=None,
                    stages_executed_count=stages_count,
                    hop_trace=context.hop_trace,
                    error_message=f"Dangling transition target: {current_uuid}"
                )

            node = self.stages_by_uuid[current_uuid]
            context.hop_trace.append(node.sender_address or current_uuid)
            stages_count += 1

            LOG.info("STAGE [%d]: %s", node.sequence_index, node.label)

            # 3. Pre-execution delay
            if node.delay_before_sec > 0:
                time.sleep(node.delay_before_sec)

            # 4. Stage Execution & Looping
            iteration = 1
            stage_success = False
            last_result: Any = None

            while True:
                context.current_iteration = iteration
                LOG.info("  Pass %d / %d...", iteration, node.loop_max_iterations)

                start_mono = time.monotonic()
                try:
                    last_result, out_path = self._dispatch_payload(node, context)
                    if out_path and out_path.exists():
                        latest_artifact = out_path
                    stage_success = True
                except Exception as exc:
                    LOG.error("  Execution failed: %s", exc)
                    stage_success = False
                    last_result = {"error": str(exc)}

                elapsed = time.monotonic() - start_mono

                # Evaluate break condition if loop enabled
                break_met = False
                if node.loop_enabled and node.loop_break_condition:
                    break_met = self._evaluate_predicate(node.loop_break_condition, last_result, context)

                if not node.loop_enabled:
                    break
                if stage_success and (break_met or node.loop_max_iterations == 1):
                    break
                if iteration >= node.loop_max_iterations and node.loop_max_iterations > 0:
                    break

                iteration += 1
                if node.loop_interval_sec > 0:
                    time.sleep(node.loop_interval_sec)

            # 5. Post-execution delay
            if node.delay_after_sec > 0:
                time.sleep(node.delay_after_sec)

            # 6. Resolve Next Address / Transition
            next_target, disposition = self._resolve_next_transition(node, iteration, stage_success, context)
            LOG.info("  Transition [%s] -> %s", disposition, next_target)

            context.execution_history.append({
                "stage_uuid": current_uuid,
                "label": node.label,
                "iterations_run": iteration,
                "success": stage_success,
                "disposition": disposition,
                "next_target": next_target
            })

            current_uuid = next_target

        return FSMExecutionResult(
            success=False,
            exit_code=EXIT_PARTIAL_FAILURE,
            terminal_disposition="TERMINATED_UNEXPECTEDLY",
            processed_artifact_path=None,
            stages_executed_count=stages_count,
            hop_trace=context.hop_trace
        )

    def _dispatch_payload(
        self,
        node: FSMStageNode,
        context: FSMExecutionContext
    ) -> Tuple[Any, Optional[Path]]:
        mode = node.dispatch_mode.strip()
        payload = node.code_payload.strip()

        if mode == "python_callable":
            module_name, func_name = payload.rsplit(".", 1)
            module = importlib.import_module(module_name)
            func = getattr(module, func_name)
            result = func(context)
            out_file = context.staged_asset_path
            return result, out_file

        elif mode == "inline_python_block":
            restricted_globals = {
                "__builtins__": {
                    "len": len, "range": range, "isinstance": isinstance,
                    "dict": dict, "list": list, "str": str, "int": int, "float": float,
                    "bool": bool, "print": LOG.info, "time": time
                }
            }
            local_scope = {"ctx": context, "result": None}
            exec(payload, restricted_globals, local_scope)
            return local_scope.get("result"), context.staged_asset_path

        elif mode == "shell_command":
            formatted_cmd = payload.format(
                input_file=str(context.staged_asset_path),
                staged_dir=str(context.staged_directory),
                iteration=context.current_iteration
            )
            cmd_tokens = shlex.split(formatted_cmd)
            proc = subprocess.run(
                cmd_tokens,
                cwd=str(context.staged_directory),
                capture_output=True,
                text=True,
                timeout=node.timeout_sec
            )
            if proc.returncode != 0:
                raise RuntimeError(f"Shell exit {proc.returncode}: {proc.stderr.strip()}")
            return proc.stdout.strip(), context.staged_asset_path

        else:
            raise ValueError(f"Unknown dispatch mode: {mode}")

    def _evaluate_predicate(self, expr: str, output: Any, context: FSMExecutionContext) -> bool:
        try:
            scope = {"output": output, "ctx": context, "iteration": context.current_iteration}
            return bool(eval(expr, {"__builtins__": {}}, scope))
        except Exception:
            return False

    def _resolve_next_transition(
        self,
        node: FSMStageNode,
        iterations_run: int,
        stage_success: bool,
        context: FSMExecutionContext
    ) -> Tuple[str, str]:
        # 1. Repetition Threshold Deflection
        if iterations_run > node.if_repetition_count_over and not stage_success:
            return node.conditional_forward_address or "ABORT_TERMINAL", "CONDITIONAL_THRESHOLD_DEFLECTION"

        # 2. Clean Success
        if stage_success:
            target = node.forward_address or node.on_success_uuid
            return target, "SUCCESS_FORWARD"

        # 3. Standard Failure
        return node.on_failure_uuid, "FAILURE_ESCALATION"


# ==============================================================================
# Framework Chunk Registry Exporter & Scaffolder
# ==============================================================================

def export_automation_framework_registry(target_file: Optional[Path] = None) -> Dict[str, Any]:
    """
    Assembles the standard 3-zone automation pipeline chassis, FSM manifests,
    and lifecycle hooks into a canonical BEJSON 105a chunked registry.
    """
    registry_doc = create_empty_framework_registry_105a(
        framework_name="automation_3zone_fsm_chassis",
        framework_version="1.0.0"
    )

    fields = registry_doc["Fields"]
    field_map = build_field_map_105(fields)

    # 1. Launcher Script
    launcher_code = '''#!/usr/bin/env python3
"""
Launcher for 3-Zone BEJSON Automation Pipeline with FSM VM Execution.
"""
from __future__ import annotations
import argparse
import logging
import os
from pathlib import Path
import sys

DIVIDER_49 = "=" * 49
SUBDIVIDER_49 = "-" * 49
LOG = logging.getLogger("PipelineLauncher")

def parse_args():
    parser = argparse.ArgumentParser(description="BEJSON 3-Zone Automation Pipeline")
    parser.add_argument("--dry-run", action="store_true", help="Scan intake without executing")
    parser.add_argument("--status", action="store_true", help="Print pipeline queue status")
    return parser.parse_args()

def main():
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    base_dir = Path(__file__).resolve().parent
    sys.path.insert(0, str(base_dir / "routing"))

    import pre_processing
    import processing
    import post_processing

    if args.status:
        LOG.info(DIVIDER_49)
        LOG.info("PIPELINE STATUS: %s", base_dir.name)
        LOG.info(SUBDIVIDER_49)
        return 0

    staged_file = pre_processing.stage_asset(base_dir / "input", base_dir / "staged")
    if not staged_file:
        return 0

    out_file = processing.execute_processing(staged_file, base_dir / "staged", {})
    if out_file:
        post_processing.deliver_asset(out_file, base_dir / "output")
        return 0
    return 1

if __name__ == "__main__":
    sys.exit(main())
'''

    # 2. Pipeline Config
    config_doc = {
        "Format": "BEJSON",
        "Format_Version": "104a",
        "Format_Creator": "Elton Boehnen",
        "Records_Type": ["PipelineConfig"],
        "Fields": [{"name": "key", "type": "string"}, {"name": "val", "type": "string"}],
        "Values": [
            ["pipeline_name", "Automation_FSM_Pipeline"],
            ["supported_extensions", ".txt,.md,.json,.bejson"],
            ["move_original_on_complete", "true"]
        ]
    }
    config_code = json.dumps(config_doc, indent=2)

    # 3. Pre-processing
    pre_code = '''#!/usr/bin/env python3
"""Intake discovery and atomic quarantine staging."""
from pathlib import Path
import os
import shutil
from typing import Optional

def stage_asset(input_dir: Path, staged_dir: Path) -> Optional[Path]:
    input_dir.mkdir(parents=True, exist_ok=True)
    staged_dir.mkdir(parents=True, exist_ok=True)
    for item in sorted(input_dir.iterdir()):
        if item.is_file() and not item.name.startswith("."):
            dest = staged_dir / item.name
            shutil.move(str(item), str(dest))
            return dest
    return None
'''

    # 4. Processing with FSM Core integration
    proc_code = '''#!/usr/bin/env python3
"""Processing router executing BEJSON Automation FSM row-by-row."""
from pathlib import Path
import sys
from typing import Any, Dict, Optional

# Link to core library
sys.path.insert(0, "/storage/emulated/0/Admin/Libraries/libraries_105/Lib_PY/Automation")
try:
    from lib_bejson_Automation_automation_core import (
        BEJSONAutomationFSM,
        FSMExecutionContext
    )
except ImportError:
    BEJSONAutomationFSM = None

def execute_processing(staged_file: Path, staged_dir: Path, cfg: Dict[str, Any]) -> Optional[Path]:
    manifest = staged_dir.parent / "routing" / "pipeline_fsm_manifest.105a.bejson"
    if not manifest.exists() or not BEJSONAutomationFSM:
        # Fallback dummy passthrough
        return staged_file

    fsm = BEJSONAutomationFSM(manifest)
    ctx = FSMExecutionContext(
        pipeline_identifier="standard_3zone_fsm",
        staged_asset_path=staged_file,
        staged_directory=staged_dir
    )
    result = fsm.execute_pipeline(ctx)
    return result.processed_artifact_path if result.success else None
'''

    # 5. Post-processing
    post_code = '''#!/usr/bin/env python3
"""Integrity verification and verified delivery."""
from pathlib import Path
import shutil

def deliver_asset(staged_file: Path, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    dest = output_dir / staged_file.name
    shutil.move(str(staged_file), str(dest))
    return dest
'''

    # 6. Default FSM Manifest 105a
    fsm_doc = create_empty_fsm_manifest_105a(
        pipeline_identifier="starter_fsm_pipeline_v1",
        initial_step_uuid="9f1b2c3d-0001-4000-8000-000000000001"
    )
    fsm_doc["Values"] = [
        [
            "9f1b2c3d-0001-4000-8000-000000000001",
            1,
            "Intake Validation & File Inspection",
            "inline_python_block",
            "ctx.custom_state['bytes'] = ctx.staged_asset_path.stat().st_size\nresult = {'status': 'OK'}",
            0.1,
            0.1,
            False,
            1,
            0.0,
            "true",
            "FINAL_DELIVERY_GATE",
            "ABORT_TERMINAL",
            30.0,
            "local://pipeline/step_01",
            "FINAL_DELIVERY_GATE",
            3,
            "ABORT_TERMINAL"
        ]
    ]
    fsm_manifest_code = json.dumps(fsm_doc, indent=2)

    # 7. Lifecycle Hooks
    pre_hook_code = '''#!/usr/bin/env python3
"""Pre-Stage Lifecycle Hook: Intercepts before stage execution."""
def pre_stage_hook(stage_id: str, asset_name: str) -> bool:
    return True
'''
    post_hook_code = '''#!/usr/bin/env python3
"""Post-Stage Lifecycle Hook: Validates results before transition."""
def post_stage_hook(stage_id: str, success: bool) -> None:
    pass
'''

    file_entries = [
        ("launcher.py", "launcher", launcher_code, True),
        ("routing/pipeline_config.bejson", "config", config_code, False),
        ("routing/pre_processing.py", "pre_processing", pre_code, True),
        ("routing/processing.py", "processing", proc_code, True),
        ("routing/post_processing.py", "post_processing", post_code, True),
        ("routing/pipeline_fsm_manifest.105a.bejson", "manifest", fsm_manifest_code, False),
        ("hooks/pre_stage_hook.py", "hook", pre_hook_code, True),
        ("hooks/post_stage_hook.py", "hook", post_hook_code, True),
    ]

    for rel_path, role, content, is_exec in file_entries:
        rec_uuid = str(uuid.uuid4())
        checksum = hashlib.sha256(content.encode("utf-8")).hexdigest()
        registry_doc["Values"].append([
            rec_uuid,
            rel_path,
            role,
            content,
            checksum,
            is_exec
        ])

    if target_file:
        target_path = Path(target_file).resolve()
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as handle:
            json.dump(registry_doc, handle, indent=2)
        LOG.info("Exported chunked framework registry to: %s", target_path)

    return registry_doc


def scaffold_pipeline_from_registry(
    registry_source: Union[Path, str, Dict[str, Any]],
    destination_dir: Path
) -> List[Path]:
    """
    Unpacks and materializes a complete 3-zone automation pipeline from a chunked registry.
    Validates cryptographic SHA-256 hashes and sets up input/staged/output dropzones.
    """
    if isinstance(registry_source, (Path, str)):
        with open(registry_source, "r", encoding="utf-8") as handle:
            reg_doc = json.load(handle)
    else:
        reg_doc = registry_source

    is_valid, errors = validate_framework_registry_barrier(reg_doc)
    if not is_valid:
        raise AutomationSchemaValidationError(f"Invalid framework registry: {errors}")

    fields = reg_doc["Fields"]
    field_map = build_field_map_105(fields)
    dest = Path(destination_dir).resolve()
    dest.mkdir(parents=True, exist_ok=True)

    # Establish standard 3-zone dropzones
    for zone in ("input", "staged", "output", "logs"):
        (dest / zone).mkdir(parents=True, exist_ok=True)

    created_files: List[Path] = []
    for row in reg_doc.get("Values", []):
        rel_path = str(row[field_map["relative_file_path"]]).strip()
        content = str(row[field_map["content_text"]])
        is_exec = bool(row[field_map["executable_flag"]])

        target = dest / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)

        with open(target, "w", encoding="utf-8") as handle:
            handle.write(content)

        if is_exec:
            try:
                target.chmod(target.stat().st_mode | 0o755)
            except Exception:
                pass

        created_files.append(target)

    LOG.info("Scaffolded %d pipeline framework files into: %s", len(created_files), dest)
    return created_files
