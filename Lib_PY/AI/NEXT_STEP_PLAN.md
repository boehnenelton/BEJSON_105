# Architecture Roadmap & Implementation Status (`v1.5.0`)

**Implemented Baseline (`v1.5.0`, 18/18 tests passing, 0 naming violations):**
- `lib_bejson_ai_dispatcher.py` (`AIDispatcher`, `AI_Dispatch`, `AI_Dispatch_Async`, `Get_Response_*`, `Get_Interaction_ID`, `Get_Tool_Calls`, `Get_Turn_Continuation_Command`)
- `lib_bejson_ai_models.py` (`Name_Case` model catalog + `Resolve_Model_Identifier`)
- `lib_bejson_ai_client_geminirest.py` & `lib_bejson_ai_client_geminiinteractions.py`
- `lib_bejson_ai_tooling_base.py`, `lib_bejson_ai_tooling_registry.py` (`AIGlobalConfigManager` + `config/ai_global_config.105a.bejson` auto-export & persistence), `lib_bejson_ai_tooling_interactions.py`
- `lib_bejson_ai_parser_base.py` (`BaseModularParser`, `Base_Modular_Parser`)
- `lib_bejson_ai_parser_registry.py` (`ParserRegistry`, `Parser_Registry` — config-gated via `global_pre_parser_enabled` and `global_post_parser_enabled`)
- `lib_bejson_ai_extension_parser.py` (`BaseExtensionModuleParser`, `Base_Extension_Module_Parser`, `ExtensionParserRegistry`, `Extension_Parser_Registry` — config-gated via `extension_parser_enabled`)
- `lib_bejson_ai_env_vault.py` (Policy §5.3.3), `lib_bejson_ai_key_rotator.py`, `lib_bejson_ai_jit_key_handler.py`

---

## Implemented Layer Specifications (`v1.5.0`)

Mirroring the `ToolingRegistry` / `BaseToolingSystem` pattern, two **configuration-gated** Tier 2 parser layers are driven by persistent switches in `config/ai_global_config.105a.bejson`:

### 1. Global Pre/Post-Processing Modular Parser Abstraction Layer
- **Config Gates (`config/ai_global_config.105a.bejson`):**
  - `global_pre_parser_enabled` (`true` / `false`)
  - `global_post_parser_enabled` (`true` / `false`)
  - Persistent toggles via `AIGlobalConfigManager` (`Set_Global_Pre_Parser_Enabled`, `Set_Global_Post_Parser_Enabled`).
- **Modular Attachment (`ParserRegistry` + `BaseModularParser`):**
  - Sits alongside `ToolingRegistry` in Tier 2 so developers can attach/detach modular parser plugins without touching `AIDispatcher` or `AITranslator`.
  - **Turn Continuation Commands:** Supports modular command parsers inspecting AI output for client commands (such as `<request_turn>...</request_turn>`) and signaling the client/dispatcher via `Get_Turn_Continuation_Command()`.
  - `ParserRegistry.execute_pre_parsers()` runs active attached modular pre-parse hooks when `global_pre_parser_enabled=true`.
  - `ParserRegistry.execute_post_parsers()` runs active attached modular post-parse hooks when `global_post_parser_enabled=true`.

### 2. Localized Custom Python Module / Library Extension Parser Layer (Sits Next to Tooling)
- **Config Gate (`config/ai_global_config.105a.bejson`):**
  - `extension_parser_enabled` (`true` / `false`)
- **Custom Python Module & Library Extensions (`ExtensionParserRegistry` + `BaseExtensionModuleParser`):**
  - Sits as its own abstraction layer next to `ToolingRegistry` and `ParserRegistry` (for **Python extension modules and custom libraries**, not AI models).
  - Allows external or project-specific Python modules/libraries (e.g., custom CLI tools, BEJSON domain extensions, or downstream library plugins) to register and attach their own localized pre/post-processing parsers through the global parser abstraction layer without modifying `Lib_PY/AI` core files.

---

## Planned Next Step (`v1.6.0`): Modular Renderer Post-Processing Abstraction Layer

Adding a **modular renderer abstraction layer** (`RendererRegistry` / `Renderer_Registry` + `BaseRenderer` / `Base_Renderer`) near the post-processing layer for custom rendering of parsed content aligns directly with the **Tier 2 config-gated registry pattern** used across `Lib_PY/AI`.

### 1. Alignment with the Existing Tier 2 Architecture
In the `v1.5.0` gateway, Tier 2 isolates optional capabilities behind persistent flags in `config/ai_global_config.105a.bejson` (managed by `AIGlobalConfigManager` / `AI_Global_Config_Manager`) so plugins can attach without modifying `AIDispatcher`, `AITranslator`, or other core files:
- **`ToolingRegistry` / `BaseToolingSystem`** handles model tools (`tooling_enabled`).
- **`ParserRegistry` / `BaseModularParser`** handles inbound/outbound structural parsing such as `<request_turn>` commands (`global_pre_parser_enabled`, `global_post_parser_enabled`).
- **`ExtensionParserRegistry` / `BaseExtensionModuleParser`** lets downstream Python modules hook into pre/post processing (`extension_parser_enabled`).

Currently, `AIDispatcher.dispatch()` supports returning a normalized dict, a **BEJSON 105 `AI_Response` envelope**, or writing raw `text` to `sys.stdout` / `output_sink` via `stdout_routing`. A **Renderer Registry** (mirroring `ParserRegistry` and `ExtensionParserRegistry`, config-gated via `renderer_enabled` and `active_renderer` in `ai_global_config.105a.bejson`) closes that gap by decoupling *what* the model produced from *how* it is presented or emitted.

### 2. Placement Relative to `AIPostprocessor`
In the outbound sequence:
1. `ParserRegistry.execute_post_parsers()`
2. `ExtensionParserRegistry.execute_extension_post_parsers()`
3. `AIPostprocessor.process()`
4. **[Planned `v1.6.0`] `RendererRegistry.execute_renderers()`**
5. `stdout_routing` / `to_bejson_105_response()`

**Placing the renderer abstraction *after* `AIPostprocessor.process()` (immediately before or replacing the raw `stdout_routing` step)** is the cleanest boundary:
- **Security & validation happen first**: `AIPostprocessor` guarantees the text is non-empty, checks `blocked_patterns`, and redacts leaked API keys before any renderer sees the output.
- **Structured inputs are already extracted**: Renderers get direct access to `cleaned_response_envelope["xml_blocks"]` and `cleaned_response_envelope["structured_data"]` (when `response_format="json"`), rather than re-parsing raw model text.
- **Control tags do not leak into rendered output**: Because `ParserRegistry` runs before `AIPostprocessor`, modular command parsers (like `<request_turn>...</request_turn>`) have already stripped their control tags and populated `turn_continuation_command` before rendering begins.
- **No false validation failures**: If a renderer transformed output into HTML, ANSI terminal text, or SVG *before* `AIPostprocessor`, `expected_format="json"` validation would fail trying to parse the rendered markup as JSON.

### 3. Synergy with Existing BEJSON Rendering Libraries
Because the rest of `libraries_105` separates data schemas from presentation, a post-processing renderer layer bridges `Lib_PY/AI` directly to them without hardcoding dependencies into core gateway files:
- **Template / HTML rendering (`Lib_PY/CMS`)**: Mirrors the `BasePageRenderer` strategy pattern (`StandardPageRenderer`, `VideoPageRenderer`, `DocumentPageRenderer`, `ShowcasePageRenderer`) for mapping structured data into HTML templates.
- **Visual / SVG / Canvas output (`Lib_PY/Graphics` & `Lib_PY/Canvas`)**: Enables downstream renderers to turn structured AI outputs into SVG slides, diagram states, or Playwright-captured frames.
- **Multi-format export (`Lib_PY/Standards`)**: Follows the pattern used in `bejson_standards_export_logs`, where one shared pipeline targets `json`, `ndjson`, `markdown`, or `html` to text, a stream, or an atomic file.

### 4. Key Design Decisions to Settle Upfront (`v1.6.0`)
- **Envelope transformer vs. output sink**: Decide whether a renderer mutates/enriches the response dict (e.g., populating `rendered_output` while preserving `text`, `structured_data`, and `_ai_turn_continuation_command`) or writes directly to an output sink like `stdout_routing` / `output_sink`, so helper functions like `Get_Response_Text()`, `Get_Response_JSON()`, and `Get_Turn_Continuation_Command()` continue to work as expected.
- **Failure behavior**: `ParserRegistry` and `ExtensionParserRegistry` catch plugin exceptions and log a warning so a broken hook does not abort the call. Decide whether a renderer error should fall back to raw `text` or raise an `AIException` in the `200–235` error range.
- **BEJSON 105 preservation**: If `return_bejson_105=True`, ensure `AITranslator.to_bejson_105_response()` either runs on the pre-render envelope or cleanly carries rendered output without breaking the `AI_Response` schema.

---

## Architectural Scorecard (`v1.5.0` Baseline: `8.5 / 10`) & Roadmap to `9.5+`

`Lib_PY/AI` (`v1.5.0`) provides clean 3-tier boundaries, strong credential isolation, and zero-dependency portability, with targeted operational milestones identified to elevate the architecture to `9.5+`:

| Dimension | Score | Assessment |
| :--- | :--- | :--- |
| **Separation of Concerns (3-Tier)** | **9.5 / 10** | Strict isolation between Tier 1 routing/translation, Tier 2 gates/registries, and Tier 3 vault/rotation/HTTP clients; adding `GeminiInteractionsClient` required zero changes to key handling or pre/post gates. |
| **Security & Key Rotation** | **9.0 / 10** | Keys stay out of URLs (`x-goog-api-key`), `AIEnvVault` parses `definitions.py` safely via `ast.literal_eval` (no `exec()`), and `KeyRotator` tracks 429 cooldowns and 401/403 quarantine using masked-only BEJSON 105a state. |
| **Extensibility & Config Gating** | **9.0 / 10** | `AIGlobalConfigManager` auto-exports `config/ai_global_config.105a.bejson` on first use and gates `ToolingRegistry`, `ParserRegistry`, and `ExtensionParserRegistry` cleanly without touching `AIDispatcher`. |
| **Portability (Termux / Pydroid 3)** | **9.0 / 10** | Pure Python stdlib (`urllib.request`, `json`, `ast`, `asyncio.to_thread`) avoids heavy third-party SDK breakage on Android. |
| **Testability & Observability** | **8.0 / 10** | Transport injection lets all 18 unit/integration tests run offline in ~20ms; however, `Lib_PY/AI` is not yet wired into `Lib_PY/Standards` structured logging, so plugin warnings/errors are not persisted to the global log sink. |
| **Concurrency & Provider Breadth** | **7.5 / 10** | `dispatch_async` uses `asyncio.to_thread` over blocking `urllib` (suitable for CLI/light use, less ideal under heavy concurrency), and `AITranslator` is currently Gemini-focused until OpenRouter/Ollama drivers are added. |

### Milestones to Reach `9.5+` (`v1.6.0` – `v1.7.0`)
1. **Wire `Lib_PY/Standards` (`bejson_standards_log`) into `Lib_PY/AI`**:
   - Connect `AIDispatcher`, `KeyRotator`, and Tier 2 registries (`ToolingRegistry`, `ParserRegistry`, `ExtensionParserRegistry`, `RendererRegistry`) to `bejson_standards_log` so 429/401 key rotation events and suppressed plugin errors are auditable in the global BEJSON telemetry sink.
2. **Implement `RendererRegistry` / `BaseRenderer` after `AIPostprocessor.process()`**:
   - Enable `Lib_PY/CMS`, `Lib_PY/Graphics`, `Lib_PY/Canvas`, and `Lib_PY/Standards` to consume validated `structured_data` and `xml_blocks` directly through config-gated post-processing renderers.
3. **Add a Second Non-Gemini Provider (`openrouter` or `ollama`)**:
   - Implement `lib_bejson_ai_client_openrouter.py` or `lib_bejson_ai_client_ollama.py` (and corresponding `AITranslator` wire adapters) to verify multi-provider translation across heterogeneous wire schemas.
