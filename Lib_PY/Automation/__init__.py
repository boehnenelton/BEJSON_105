"""
Library Family:  Automation (Lib_PY.Automation)
Description:     BEJSON 105a Finite State Machine Automation & Chunked Framework Libraries.
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
License:         PolyForm Noncommercial License 1.0.0
Version:         1.0.0
Date:            2026-11-11
"""

from __future__ import annotations

from .lib_bejson_Automation_automation_errors import (
    EXIT_OK,
    EXIT_PARTIAL_FAILURE,
    EXIT_PATH_FAILURE,
    EXIT_ENV_FAILURE,
    EXIT_SCHEMA_FAILURE,
    EXIT_DEP_MISSING,
    EXIT_BUSY,
    EXIT_CYCLE_DETECTED,
    EXIT_THRESHOLD_EXCEEDED,
    EXIT_TIMEOUT_EXHAUSTED,
    EXIT_INTERRUPTED,
    AutomationFSMError,
    AutomationSchemaValidationError,
    AutomationCycleError,
    AutomationTimeoutError,
    AutomationThresholdExceededError
)

from .lib_bejson_Automation_automation_schemas import (
    AUTOMATION_FSM_MANIFEST_FIELDS,
    AUTOMATION_FRAMEWORK_REGISTRY_FIELDS,
    build_field_map_105,
    create_empty_fsm_manifest_105a,
    create_empty_framework_registry_105a
)

from .lib_bejson_Automation_automation_validator import (
    validate_fsm_manifest_barrier,
    validate_framework_registry_barrier
)

from .lib_bejson_Automation_automation_core import (
    FSMStageNode,
    FSMExecutionContext,
    FSMExecutionResult,
    BEJSONAutomationFSM,
    export_automation_framework_registry,
    scaffold_pipeline_from_registry
)

__all__ = [
    "EXIT_OK",
    "EXIT_PARTIAL_FAILURE",
    "EXIT_PATH_FAILURE",
    "EXIT_ENV_FAILURE",
    "EXIT_SCHEMA_FAILURE",
    "EXIT_DEP_MISSING",
    "EXIT_BUSY",
    "EXIT_CYCLE_DETECTED",
    "EXIT_THRESHOLD_EXCEEDED",
    "EXIT_TIMEOUT_EXHAUSTED",
    "EXIT_INTERRUPTED",
    "AutomationFSMError",
    "AutomationSchemaValidationError",
    "AutomationCycleError",
    "AutomationTimeoutError",
    "AutomationThresholdExceededError",
    "AUTOMATION_FSM_MANIFEST_FIELDS",
    "AUTOMATION_FRAMEWORK_REGISTRY_FIELDS",
    "build_field_map_105",
    "create_empty_fsm_manifest_105a",
    "create_empty_framework_registry_105a",
    "validate_fsm_manifest_barrier",
    "validate_framework_registry_barrier",
    "FSMStageNode",
    "FSMExecutionContext",
    "FSMExecutionResult",
    "BEJSONAutomationFSM",
    "export_automation_framework_registry",
    "scaffold_pipeline_from_registry"
]
