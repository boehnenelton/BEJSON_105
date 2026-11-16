# Modular Pre-Parser, Post-Parser, and Post-Renderer Architecture Guide

**Library:** `Lib_PY/AI` (`v1.6.0`)  
**Scope:** Tier 2 Configuration-Gated Pipeline Plugins (`ParserRegistry`, `ExtensionParserRegistry`, `RendererRegistry`)  
**Configuration Store:** `config/ai_global_config.105a.bejson`  
**Author:** Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton

---

## Table of Contents

1. [Overview and Architectural Goals](#1-overview-and-architectural-goals)
2. [Tier 2 Registry Topology and Config Gating](#2-tier-2-registry-topology-and-config-gating)
3. [Persistent BEJSON 105a Configuration Mechanics](#3-persistent-bejson-105a-configuration-mechanics)
4. [End-to-End Execution Order in `AIDispatcher`](#4-end-to-end-execution-order-in-aidispatcher)
5. [Data Envelopes Across Pipeline Boundaries](#5-data-envelopes-across-pipeline-boundaries)
6. [Modular Pre-Parsers (`parse_pre` and `parse_extension_pre`)](#6-modular-pre-parsers-parse_pre-and-parse_extension_pre)
7. [Modular Post-Parsers (`parse_post` and `parse_extension_post`)](#7-modular-post-parsers-parse_post-and-parse_extension_post)
8. [The `AIPostprocessor` Security and Validation Boundary](#8-the-aipostprocessor-security-and-validation-boundary)
9. [Modular Post-Renderers (`BaseRenderer` and `RendererRegistry`)](#9-modular-post-renderers-baserenderer-and-rendererregistry)
10. [Active Renderer Resolution Rules](#10-active-renderer-resolution-rules)
11. [Concrete Post-Renderer Implementations](#11-concrete-post-renderer-implementations)
12. [Chaining Pre-Parsers, Post-Parsers, and Post-Renderers](#12-chaining-pre-parsers-post-parsers-and-post-renderers)
13. [Error Handling, Fallback Semantics, and Error Codes](#13-error-handling-fallback-semantics-and-error-codes)
14. [Offline Testing with Transport Injection](#14-offline-testing-with-transport-injection)
15. [Plugin Authoring Checklist](#15-plugin-authoring-checklist)

---

## 1. Overview and Architectural Goals

The `Lib_PY/AI` gateway separates provider wire transport (Tier 3) and request routing (Tier 1) from optional request preparation, response inspection, and output presentation (Tier 2). This separation is implemented through three configuration-gated plugin registries managed by `AIGlobalConfigManager`:

1. **`ParserRegistry` (`lib_bejson_ai_parser_registry.py`)**: Executes `BaseModularParser` plugins at two points—before outbound provider translation (`parse_pre`) and after inbound provider translation (`parse_post`).
2. **`ExtensionParserRegistry` (`lib_bejson_ai_extension_parser.py`)**: Executes `BaseExtensionModuleParser` plugins supplied by external Python libraries or downstream applications (`parse_extension_pre`, `parse_extension_post`) without modifying `Lib_PY/AI` core modules.
3. **`RendererRegistry` (`lib_bejson_ai_renderer_registry.py`)**: Executes `BaseRenderer` plugins after `AIPostprocessor.process()` (`render`) to transform validated text, extracted XML blocks, and parsed JSON payloads into target presentation or export formats.

### Why Three Separate Registries Exist

- **Core vs. Downstream Separation**: `ParserRegistry` is intended for gateway-level structural parsers (such as turn-continuation tag extractors or global prompt normalizers), whereas `ExtensionParserRegistry` isolates project-specific Python module hooks so downstream codebases never collide with gateway internals.
- **Parsing vs. Rendering Separation**: Parsers inspect and normalize raw data structures (`prompt`, `messages`, `text`, control tags), while renderers consume *validated* and *sanitized* output (`structured_data`, `xml_blocks`, redacted `text`) to produce presentation artifacts (`rendered_output`).
- **Zero-Modification Extensibility**: Attaching or detaching any plugin requires zero edits to `AIDispatcher`, `AITranslator`, `GeminiRestClient`, or `GeminiInteractionsClient`.

---

## 2. Tier 2 Registry Topology and Config Gating

Every Tier 2 registry is governed by persistent `true`/`false` switches stored in `config/ai_global_config.105a.bejson`. When a gate is `false` (the default state for all optional gates), `AIDispatcher` skips the corresponding registry stage with zero overhead.

| Registry Class | Base Contract | Config Gate Key(s) | Default | Pipeline Stage |
| :--- | :--- | :--- | :--- | :--- |
| `ToolingRegistry` | `BaseToolingSystem` | `tooling_enabled`, `active_tooling_system` | `false`, `"interactions_tools"` | Tool injection & multi-turn loop |
| `ParserRegistry` (Pre) | `BaseModularParser` | `global_pre_parser_enabled` | `false` | Inbound (after `AIPreprocessor`) |
| `ParserRegistry` (Post) | `BaseModularParser` | `global_post_parser_enabled` | `false` | Outbound (before `AIPostprocessor`) |
| `ExtensionParserRegistry` | `BaseExtensionModuleParser` | `extension_parser_enabled` | `false` | Inbound & Outbound |
| `RendererRegistry` | `BaseRenderer` | `renderer_enabled`, `active_renderer` | `false`, `"default"` | Outbound (after `AIPostprocessor`) |

### `Name_Case` Compatibility

All Tier 2 classes and methods expose both `snake_case` and `Name_Case` identifiers so callers using either convention remain consistent across the ecosystem:

- `ParserRegistry` / `Parser_Registry` (`Register_Parser`, `Execute_Pre_Parsers`, `Execute_Post_Parsers`)
- `BaseModularParser` / `Base_Modular_Parser` (`Parse_Pre`, `Parse_Post`)
- `ExtensionParserRegistry` / `Extension_Parser_Registry` (`Register_Extension_Parser`, `Execute_Extension_Pre_Parsers`, `Execute_Extension_Post_Parsers`)
- `BaseExtensionModuleParser` / `Base_Extension_Module_Parser` (`Parse_Extension_Pre`, `Parse_Extension_Post`)
- `RendererRegistry` / `Renderer_Registry` (`Register_Renderer`, `Select_Renderer`, `Get_Active_Renderer`, `Execute_Renderers`)
- `BaseRenderer` / `Base_Renderer` (`Render`)
- `AIGlobalConfigManager` / `AI_Global_Config_Manager`

---

## 3. Persistent BEJSON 105a Configuration Mechanics

`AIGlobalConfigManager` (`lib_bejson_ai_tooling_registry.py`) manages `config/ai_global_config.105a.bejson` as a Format `105a` BEJSON table with `Records_Type: ["AIGlobalConfig"]` and three typed columns:

- `setting_key` (`string`)
- `setting_value_json` (`string` — JSON-encoded boolean, integer, or string literal)
- `setting_type_label` (`string` — `"bool"`, `"int"`, `"str"`)

### Path Resolution Order

1. Explicit `config_target_file_path` argument passed to `AIGlobalConfigManager(...)` (primarily used in isolated tests).
2. `BEJSON_AI_GLOBAL_CONFIG` environment variable if set.
3. Default path: `<Lib_PY/AI>/config/ai_global_config.105a.bejson`.

### Auto-Export and Atomic Writes

- On first instantiation, if the target `.105a.bejson` file does not exist, `AIGlobalConfigManager.auto_export_default_configuration()` creates parent directories and writes all `DEFAULT_SETTINGS_INITIAL_VALUES` atomically via a `.tmp` sibling file followed by `Path.replace()`.
- Every call to `set_global_pre_parser_enabled()`, `set_global_post_parser_enabled()`, `set_extension_parser_enabled()`, `set_renderer_enabled()`, or `set_active_renderer_name()` updates the in-memory cache and atomically persists the entire `105a` document to disk.

```python
from lib_bejson_ai_tooling_registry import AIGlobalConfigManager

config_manager = AIGlobalConfigManager()
config_manager.set_global_pre_parser_enabled(True)
config_manager.set_global_post_parser_enabled(True)
config_manager.set_extension_parser_enabled(True)
config_manager.set_renderer_enabled(True)
config_manager.set_active_renderer_name("html_summary")
```

---

## 4. End-to-End Execution Order in `AIDispatcher`

Inside `AIDispatcher.dispatch()` (and `dispatch_async()`, which delegates via `asyncio.to_thread`), the gateway executes a strict, deterministic pipeline:

```text
+-------------------------------------------------------------------------+
| 1. INBOUND NORMALIZATION                                                |
|    normalize_inbound_payload(payload)                                   |
|    Resolve provider & model via Resolve_Model_Identifier()              |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
| 2. TIER 2 INBOUND GATES                                                 |
|    a. AIPreprocessor.process(normalized_request_payload)                |
|    b. ParserRegistry.execute_pre_parsers(...)      [pre_parser gate]    |
|    c. ExtensionParserRegistry.execute_extension_pre_parsers(...)        |
|    d. ToolingRegistry.get_active_system() -> inject "tools" if enabled  |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
| 3. TIER 1 & TIER 3 PROVIDER EXECUTION                                   |
|    AITranslator.to_provider_payload(...)                                |
|    JITKeyHandler + KeyRotator -> BaseAIClient.execute_call(...)         |
|    AITranslator.from_provider_response(...)                             |
|    [Optional multi-turn tool execution loop up to max_tool_roundtrips]   |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
| 4. TIER 2 OUTBOUND PARSERS (PRE-VALIDATION)                             |
|    a. ParserRegistry.execute_post_parsers(...)     [post_parser gate]   |
|    b. ExtensionParserRegistry.execute_extension_post_parsers(...)       |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
| 5. TIER 2 SECURITY & SCHEMA VALIDATION                                  |
|    AIPostprocessor.process(normalized_response_envelope,                |
|                            expected_format=response_format)             |
|    - Rejects empty text                                                 |
|    - Checks blocked_patterns                                            |
|    - Redacts AIza... keys -> [REDACTED_API_KEY]                         |
|    - Extracts xml_blocks & structured_data (if response_format="json")  |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
| 6. TIER 2 POST-PROCESSING RENDERER GATE                                 |
|    RendererRegistry.execute_renderers(cleaned_response_envelope)        |
|    - Runs ONLY if renderer_enabled=true                                 |
|    - Populates rendered_output, rendered_format, rendered_by            |
|    - Preserves text, structured_data, turn_continuation_command         |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
| 7. DELIVERY                                                             |
|    a. If stdout_routing=true: write rendered_output (or fallback text)  |
|    b. If return_bejson_105=true: AITranslator.to_bejson_105_response()  |
|    c. Else: return cleaned_response_envelope dict                       |
+-------------------------------------------------------------------------+
```

---

## 5. Data Envelopes Across Pipeline Boundaries

Understanding what keys exist at each stage prevents plugins from making false assumptions.

### Inbound Request Dictionary (Stages 1–2)

After `normalize_inbound_payload()` and `AIPreprocessor.process()`, the request dictionary typically contains:

| Key | Type | Notes |
| :--- | :--- | :--- |
| `provider` | `str` | Target provider (`"geminirest"`, `"geminiinteractions"`, etc.) |
| `model` | `str` | Model identifier (resolved via `Resolve_Model_Identifier`) |
| `prompt` | `str` | Single-turn prompt text (when `messages` is not used) |
| `messages` | `List[Dict[str, str]]` | Multi-turn message list (`{"role": ..., "content": ...}`) |
| `system_instruction` | `str` | Optional system prompt |
| `temperature` | `float` | Sampling temperature |
| `max_tokens` | `int` | Output token ceiling |
| `response_format` | `str` | `"text"` (default) or `"json"` |
| `tools` | `List[Dict[str, Any]]` | Optional tool declarations |

### Outbound Response Envelope (Stages 4–6)

After `AITranslator.from_provider_response()`, the normalized response envelope contains:

| Key | Type | Populated By |
| :--- | :--- | :--- |
| `provider` | `str` | `AITranslator` |
| `model` | `str` | `AITranslator` |
| `text` | `str` | `AITranslator` (may be rewritten by post-parsers & `AIPostprocessor`) |
| `finish_reason` | `str` | `AITranslator` (e.g. `"STOP"`) |
| `usage` | `Dict[str, int]` | `AITranslator` (`prompt_tokens`, `completion_tokens`, etc.) |
| `interaction_id` | `str` | `AITranslator` (for `geminiinteractions`) |
| `tool_calls` | `List[Dict[str, Any]]` | `AITranslator` |
| `turn_continuation_command` | `Dict[str, Any]` | Modular post-parser (optional) |
| `xml_blocks` | `Dict[str, List[str]]` | `AIPostprocessor.process()` |
| `structured_data` | `Any` | `AIPostprocessor.process()` (when `response_format="json"`) |
| `rendered_output` | `str` | `RendererRegistry.execute_renderers()` (when enabled) |
| `rendered_format` | `str` | `RendererRegistry.execute_renderers()` (when enabled) |
| `rendered_by` | `str` | `RendererRegistry.execute_renderers()` (when enabled) |

---

## 6. Modular Pre-Parsers (`parse_pre` and `parse_extension_pre`)

Pre-parsers transform or enrich the inbound request dictionary **before** `AITranslator.to_provider_payload()` converts it into a provider-specific wire format.

### Potential Use Cases

1. **Dynamic System Instruction Injection**: Inject workspace rules, date/time context, or output schema constraints into `system_instruction` based on request metadata.
2. **Prompt Template Expansion**: Replace `{{placeholder}}` tokens in `prompt` or `messages` using external BEJSON stores or environment definitions.
3. **Outbound Privacy Scrubbing**: Redact local filesystem paths, internal hostnames, or accidental secret tokens from user prompts before sending them over HTTPS.
4. **Adaptive `response_format` and `model` Routing**: Inspect prompt intent or payload size and switch `response_format` to `"json"` or upgrade `model` without altering the caller.
5. **Audit Metadata Tagging**: Attach correlation IDs or caller tags to a non-wire metadata key for downstream post-parsers or loggers to inspect.

### Example: Context-Injecting Pre-Parser (`BaseModularParser`)

```python
from typing import Any, Dict
from lib_bejson_ai_parser_base import BaseModularParser


class SchemaConstraintPreParser(BaseModularParser):
    """Injects strict JSON output instructions whenever response_format='json'."""

    parser_name: str = "schema_constraint_pre_parser"

    def parse_pre(
        self,
        incoming_request_payload_dict: Dict[str, Any],
    ) -> Dict[str, Any]:
        updated_payload = dict(incoming_request_payload_dict)
        if str(updated_payload.get("response_format", "text")).lower() == "json":
            existing_instruction = str(updated_payload.get("system_instruction", "")).strip()
            json_directive = "Respond strictly with valid JSON. Do not include commentary outside the JSON object."
            if json_directive not in existing_instruction:
                updated_payload["system_instruction"] = (
                    f"{existing_instruction}\n{json_directive}".strip()
                )
        return updated_payload

    def parse_post(
        self,
        incoming_response_envelope_dict: Dict[str, Any],
    ) -> Dict[str, Any]:
        # No outbound mutation needed for this plugin
        return incoming_response_envelope_dict
```

### Example: Downstream Python Extension (`BaseExtensionModuleParser`)

External modules use `ExtensionParserRegistry` so their hooks remain isolated from gateway-level `ParserRegistry` plugins:

```python
from typing import Any, Dict
from lib_bejson_ai_extension_parser import BaseExtensionModuleParser


class WorkspaceTagExtensionParser(BaseExtensionModuleParser):
    """Prefixes outbound prompts with a project tag and records extension metadata."""

    extension_module_name: str = "workspace_tag_extension"

    def parse_extension_pre(
        self,
        incoming_request_payload_dict: Dict[str, Any],
    ) -> Dict[str, Any]:
        updated_payload = dict(incoming_request_payload_dict)
        prompt_text = str(updated_payload.get("prompt", ""))
        if prompt_text and not prompt_text.startswith("[WORKSPACE]"):
            updated_payload["prompt"] = f"[WORKSPACE] {prompt_text}"
        return updated_payload

    def parse_extension_post(
        self,
        incoming_response_envelope_dict: Dict[str, Any],
    ) -> Dict[str, Any]:
        updated_envelope = dict(incoming_response_envelope_dict)
        updated_envelope["extension_verified"] = True
        return updated_envelope
```

---

## 7. Modular Post-Parsers (`parse_post` and `parse_extension_post`)

Post-parsers run **after** the provider call (and any multi-turn tool loop) completes, and **before** `AIPostprocessor.process()`.

### Potential Use Cases

1. **Control-Tag Extraction (`<request_turn>`)**: Extract agentic control directives from raw model text, strip the control tags from `text`, and populate `turn_continuation_command` so callers can query `Get_Turn_Continuation_Command(response)`.
2. **Wrapper Stripping Before JSON Validation**: Remove provider-specific preamble or custom XML wrappers before `AIPostprocessor` runs `extract_json_payload()`.
3. **Token Usage and Telemetry Hooks**: Inspect `usage` (`prompt_tokens`, `completion_tokens`) and `finish_reason` to emit metrics to external sinks.
4. **Domain-Specific Text Normalization**: Normalize line endings, canonicalize terminology, or flag domain policy violations before rendering.

### Example: Turn-Continuation Command Post-Parser

```python
import re
from typing import Any, Dict
from lib_bejson_ai_parser_base import BaseModularParser

_REQUEST_TURN_PATTERN = re.compile(
    r"<request_turn>(.*?)</request_turn>",
    re.DOTALL | re.IGNORECASE,
)


class TurnContinuationCommandParser(BaseModularParser):
    """Extracts <request_turn>...</request_turn> directives from model output."""

    parser_name: str = "turn_continuation_command_parser"

    def parse_pre(
        self,
        incoming_request_payload_dict: Dict[str, Any],
    ) -> Dict[str, Any]:
        return incoming_request_payload_dict

    def parse_post(
        self,
        incoming_response_envelope_dict: Dict[str, Any],
    ) -> Dict[str, Any]:
        updated_envelope = dict(incoming_response_envelope_dict)
        raw_text = str(updated_envelope.get("text", ""))
        match = _REQUEST_TURN_PATTERN.search(raw_text)
        if match:
            continuation_prompt = match.group(1).strip()
            cleaned_text = _REQUEST_TURN_PATTERN.sub("", raw_text).strip()
            updated_envelope["text"] = cleaned_text
            updated_envelope["turn_continuation_command"] = {
                "request_turn": True,
                "continuation_prompt": continuation_prompt,
            }
        return updated_envelope
```

Because this parser strips `<request_turn>...</request_turn>` *before* `AIPostprocessor.process()` and `RendererRegistry.execute_renderers()`, neither JSON parsing nor HTML/Markdown rendering is polluted by raw control tags.

---

## 8. The `AIPostprocessor` Security and Validation Boundary

`AIPostprocessor.process()` (`lib_bejson_ai_postprocessor.py`) sits directly between the post-parser stage and the post-renderer stage. Placing `RendererRegistry` *after* `AIPostprocessor.process()` guarantees four invariants:

1. **Non-Empty Output Guarantee**: If the provider returned empty text (or a post-parser stripped everything), `AIPostprocessor` raises `AIException(ERR_AI_POSTPROCESS_REJECTED)` before any renderer runs.
2. **Sanitizer Enforcement**: Any response matching `blocked_patterns` raises `AIException(ERR_AI_SANITIZER_BLOCKED)` before rendering or `stdout_routing`.
3. **API Key Redaction**: When `redact_api_keys=True` (the default), `_KEY_LEAK_RE` (`AIza[0-9A-Za-z\-_]{20,}`) replaces leaked Google API keys with `[REDACTED_API_KEY]`. Renderers never accidentally format or persist raw credentials into HTML, SVG, or terminal output.
4. **Structured Data Readiness**: `AIPostprocessor` populates `out["xml_blocks"]` via `extract_xml_blocks(text)` and, when `expected_format="json"`, populates `out["structured_data"]` via `extract_json_payload(text)` (raising `ERR_AI_OUTPUT_VALIDATION_FAILED` on invalid JSON). Renderers consume `structured_data` and `xml_blocks` directly without re-parsing raw text.

---

## 9. Modular Post-Renderers (`BaseRenderer` and `RendererRegistry`)

`BaseRenderer` (`lib_bejson_ai_renderer_base.py`) and `RendererRegistry` (`lib_bejson_ai_renderer_registry.py`) decouple **model output content** from **output presentation**.

### Contract (`BaseRenderer`)

```python
class BaseRenderer(ABC):
    renderer_name: str = "generic_modular_renderer"
    output_format: str = "text"

    @abstractmethod
    def render(
        self,
        cleaned_response_envelope_dict: Dict[str, Any],
    ) -> Dict[str, Any]:
        raise NotImplementedError
```

### Envelope Contract and Helper Functions

A renderer receives `cleaned_response_envelope_dict` and returns an updated dictionary, typically setting:
- `rendered_output`: The formatted string (HTML, Markdown, ANSI terminal text, SVG, NDJSON, etc.).
- `rendered_format`: Format label (automatically defaulted to `renderer.output_format` by `RendererRegistry` if omitted).
- `rendered_by`: Renderer identifier (automatically defaulted to the registered `renderer_name` key by `RendererRegistry` if omitted).

Crucially, renderers should **preserve** `"text"`, `"structured_data"`, and `"turn_continuation_command"` in the returned dictionary so all existing dispatcher helpers remain valid:

- `Get_Response_Text(response)` -> returns raw cleaned `text`
- `Get_Response_JSON(response)` -> returns `structured_data`
- `Get_Turn_Continuation_Command(response)` -> returns `turn_continuation_command`
- `Get_Rendered_Output(response)` -> returns `rendered_output` if present, otherwise falls back to `Get_Response_Text(response)`

### `stdout_routing` and BEJSON 105 Compatibility

- When `stdout_routing=True` is passed to `AIDispatcher.dispatch()`, the dispatcher writes `cleaned_response_envelope["rendered_output"]` (if non-`None`) to `output_sink` or `sys.stdout`, falling back to `cleaned_response_envelope["text"]` when rendering is disabled or no `rendered_output` was produced.
- When `return_bejson_105=True`, `AITranslator.to_bejson_105_response()` constructs the canonical Format `105` `AI_Response` document from `provider`, `model`, `text`, `finish_reason`, `usage`, and `structured_data` without schema breakage.

---

## 10. Active Renderer Resolution Rules

`RendererRegistry` supports both single-renderer selection and multi-renderer pipelines via `active_renderer` in `config/ai_global_config.105a.bejson`:

| `renderer_enabled` | `active_renderer` Value | Behavior of `execute_renderers()` |
| :--- | :--- | :--- |
| `false` | any | Immediately returns `cleaned_response_envelope_dict` unchanged. |
| `true` | `"<registered_name>"` | Executes only the selected renderer matching `<registered_name>`. |
| `true` | `"default"`, `"all"`, or `""` | Executes all registered renderers sequentially in registration order (unless a renderer named `"default"` is explicitly registered, in which case only `"default"` runs). |
| `true` | `"<unregistered_name>"` | Logs a warning (`_LOGGER_INSTANCE.warning`) and returns the envelope unchanged. |

Calling `renderer_registry.select_renderer("name")` validates that `"name"` is currently registered—raising `AIException(ERR_AI_RENDERER_NOT_FOUND)` if missing—and persists `"active_renderer"` to `ai_global_config.105a.bejson`.

---

## 11. Concrete Post-Renderer Implementations

### A. HTML Card Renderer (Consuming `structured_data`)

```python
import html
from typing import Any, Dict
from lib_bejson_ai_renderer_base import BaseRenderer


class HtmlSummaryCardRenderer(BaseRenderer):
    """Renders validated JSON structured_data into a safe HTML card."""

    renderer_name: str = "html_summary_card"
    output_format: str = "html"

    def render(
        self,
        cleaned_response_envelope_dict: Dict[str, Any],
    ) -> Dict[str, Any]:
        updated_envelope = dict(cleaned_response_envelope_dict)
        structured = updated_envelope.get("structured_data")
        if isinstance(structured, dict):
            title_safe = html.escape(str(structured.get("title", "AI Output")))
            summary_safe = html.escape(str(structured.get("summary", updated_envelope.get("text", ""))))
            updated_envelope["rendered_output"] = (
                f"<section class=\"ai-card\">"
                f"<h2>{title_safe}</h2>"
                f"<p>{summary_safe}</p>"
                f"</section>"
            )
        else:
            body_safe = html.escape(str(updated_envelope.get("text", "")))
            updated_envelope["rendered_output"] = f"<pre class=\"ai-text\">{body_safe}</pre>"
        return updated_envelope
```

### B. Mobile Portrait Terminal Renderer (49-Column Ceiling)

```python
import textwrap
from typing import Any, Dict
from lib_bejson_ai_renderer_base import BaseRenderer


class MobileTerminal49Renderer(BaseRenderer):
    """Formats AI output within a 49-column mobile portrait terminal frame."""

    renderer_name: str = "mobile_terminal_49"
    output_format: str = "text"

    def render(
        self,
        cleaned_response_envelope_dict: Dict[str, Any],
    ) -> Dict[str, Any]:
        updated_envelope = dict(cleaned_response_envelope_dict)
        divider = "=" * 49
        subdivider = "-" * 49
        model_label = str(updated_envelope.get("model", "unknown"))[:39]
        wrapped_body = textwrap.fill(
            str(updated_envelope.get("text", "")),
            width=49,
        )
        updated_envelope["rendered_output"] = (
            f"{divider}\n"
            f"MODEL: {model_label}\n"
            f"{subdivider}\n"
            f"{wrapped_body}\n"
            f"{divider}"
        )
        return updated_envelope
```

### C. XML-Block Markdown Report Renderer (Consuming `xml_blocks`)

```python
from typing import Any, Dict
from lib_bejson_ai_renderer_base import BaseRenderer


class XmlBlockMarkdownRenderer(BaseRenderer):
    """Formats extracted <summary> and <details> XML blocks into Markdown."""

    renderer_name: str = "xml_block_markdown"
    output_format: str = "markdown"

    def render(
        self,
        cleaned_response_envelope_dict: Dict[str, Any],
    ) -> Dict[str, Any]:
        updated_envelope = dict(cleaned_response_envelope_dict)
        xml_blocks = updated_envelope.get("xml_blocks") or {}
        summaries = xml_blocks.get("summary") or []
        details = xml_blocks.get("details") or []

        if summaries or details:
            parts = []
            if summaries:
                parts.append(f"### Summary\n\n{summaries[0]}")
            if details:
                parts.append(f"### Details\n\n{details[0]}")
            updated_envelope["rendered_output"] = "\n\n".join(parts)
        else:
            updated_envelope["rendered_output"] = str(updated_envelope.get("text", ""))
        return updated_envelope
```

---

## 12. Chaining Pre-Parsers, Post-Parsers, and Post-Renderers

The full strength of the Tier 2 architecture appears when all three stages cooperate on a single `AIDispatcher` instance without touching core code:

1. **Pre-Parser** injects a structured output contract (`<summary>...</summary>` or JSON schema) into `system_instruction`.
2. **Post-Parser** intercepts `<request_turn>...</request_turn>` if the model requests another turn, strips the tag, and populates `turn_continuation_command`.
3. **`AIPostprocessor`** validates non-empty text, checks `blocked_patterns`, redacts any leaked `AIza...` keys, and parses `xml_blocks` / `structured_data`.
4. **Post-Renderer** transforms the validated `structured_data` or `xml_blocks` into HTML, Markdown, or 49-column CLI output and emits it via `stdout_routing` or `Get_Rendered_Output()`.

```python
from lib_bejson_ai_dispatcher import (
    AIDispatcher,
    Get_Rendered_Output,
    Get_Turn_Continuation_Command,
)

dispatcher = AIDispatcher()

# Enable and attach plugins
dispatcher.parser_registry.register_parser(SchemaConstraintPreParser())
dispatcher.parser_registry.register_parser(TurnContinuationCommandParser())
dispatcher.parser_registry.set_pre_parser_enabled(True)
dispatcher.parser_registry.set_post_parser_enabled(True)

dispatcher.renderer_registry.register_renderer(HtmlSummaryCardRenderer())
dispatcher.renderer_registry.set_enabled(True)
dispatcher.renderer_registry.select_renderer("html_summary_card")

response = dispatcher.dispatch(
    {"prompt": "Summarize current system state.", "response_format": "json"},
    stdout_routing=False,
)

rendered_html = Get_Rendered_Output(response)
next_turn = Get_Turn_Continuation_Command(response)
```

---

## 13. Error Handling, Fallback Semantics, and Error Codes

All Tier 2 plugins follow deterministic failure semantics using `AIException` and codes from `lib_bejson_AI_bejson_errors.py` (allocated range `200–235`):

| Constant | Code | Trigger Condition |
| :--- | :--- | :--- |
| `ERR_AI_PREPROCESS_REJECTED` | `211` | Inbound payload rejected by `AIPreprocessor` |
| `ERR_AI_TOKEN_LIMIT_EXCEEDED` | `212` | Prompt exceeds configured character/token limit |
| `ERR_AI_XML_PARSE_FAILED` | `213` | Malformed XML control block in `AIPreprocessor` |
| `ERR_AI_POSTPROCESS_REJECTED` | `214` | Provider returned empty text |
| `ERR_AI_OUTPUT_VALIDATION_FAILED` | `215` | `response_format="json"` failed JSON parsing |
| `ERR_AI_SANITIZER_BLOCKED` | `216` | Response matched `blocked_patterns` |
| `ERR_AI_RENDERER_NOT_FOUND` | `234` | `select_renderer()` called with unregistered name |
| `ERR_AI_RENDERER_FAILED` | `235` | Renderer raised an exception with `fail_on_error=True` |

### Resilient Default vs. Strict Mode

- **`ParserRegistry` & `ExtensionParserRegistry`**: Catch plugin exceptions, log a warning via `logging.Logger.warning`, and continue with the last valid envelope so a non-critical plugin does not abort a completed API call.
- **`RendererRegistry.execute_renderers(..., fail_on_error=False)`**: By default, logs a warning and falls back to the sanitized post-processed envelope (`Get_Rendered_Output()` returns raw `text`). Passing `fail_on_error=True` raises `AIException(ERR_AI_RENDERER_FAILED)` for strict CI or export pipelines.

---

## 14. Offline Testing with Transport Injection

Both `GeminiRestClient` and `GeminiInteractionsClient` accept a `transport` callable, allowing full end-to-end testing of pre-parsers, post-parsers, `AIPostprocessor`, and post-renderers offline in milliseconds without network calls or live API keys:

```python
import io
import json
import tempfile
from pathlib import Path
from lib_bejson_ai_client_geminirest import GeminiRestClient
from lib_bejson_ai_dispatcher import AIDispatcher, Get_Rendered_Output
from lib_bejson_ai_tooling_registry import AIGlobalConfigManager
from lib_bejson_ai_renderer_registry import RendererRegistry


def mock_transport(request_obj, timeout_seconds):
    payload = {
        "candidates": [
            {
                "content": {"parts": [{"text": '{"title": "Health", "summary": "All systems nominal"}'}]},
                "finishReason": "STOP",
            }
        ],
        "usageMetadata": {"promptTokenCount": 4, "candidatesTokenCount": 8},
    }
    return json.dumps(payload).encode("utf-8")


with tempfile.TemporaryDirectory() as temp_dir:
    cfg = AIGlobalConfigManager(config_target_file_path=Path(temp_dir) / "test.105a.bejson")
    renderer_registry = RendererRegistry(config_manager_instance=cfg)
    renderer_registry.register_renderer(HtmlSummaryCardRenderer())
    renderer_registry.set_enabled(True)
    renderer_registry.select_renderer("html_summary_card")

    dispatcher = AIDispatcher(renderer_registry=renderer_registry, auto_register_defaults=False)
    dispatcher.register_provider(GeminiRestClient(transport=mock_transport))

    sink = io.StringIO()
    result = dispatcher.dispatch(
        {"prompt": "Report status", "response_format": "json"},
        explicit_keys=["AIzaSyMockTestKey1234567890"],
        stdout_routing=True,
        output_sink=sink,
    )
    assert "<section class=\"ai-card\">" in Get_Rendered_Output(result)
    assert "<section class=\"ai-card\">" in sink.getvalue()
```

---

## 15. Plugin Authoring Checklist

1. **Inherit from the canonical Tier 2 base class**: `BaseModularParser`, `BaseExtensionModuleParser`, or `BaseRenderer`.
2. **Use unique lowercase `*_name` identifiers**: `parser_name`, `extension_module_name`, or `renderer_name` (normalized via `.lower().strip()`).
3. **Never mutate input dictionaries in place**: Copy with `dict(...)` before modifying and return the updated dictionary.
4. **Preserve core envelope keys**: Keep `"text"`, `"structured_data"`, and `"turn_continuation_command"` intact when enriching `"rendered_output"`.
5. **Log via `logging`, never `print()`**: Follow library telemetry standards so warnings remain capturable.
6. **Test both gate states**: Verify behavior with the config flag `False` (bypassed) and `True` (active) using transport injection and a temporary `AIGlobalConfigManager` file path.
