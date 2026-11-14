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
