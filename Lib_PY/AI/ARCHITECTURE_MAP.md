# Full System Architecture Map (Art Specialist Reference — `v1.5.0`)

## Tri-Color Styling Spec
- **Background:** `#000000`
- **Tier 1 Cards:** `#000000` fill, `#FFFFFF` text, `#DE2626` border
- **Tier 2 & Client Cards:** `#FFFFFF` fill, `#000000` text, `#DE2626` dashed border
- **Tier 3 Cards:** `#DE2626` fill, `#FFFFFF` text *(never black text on red)*

## Nodes by Tier
- **Client:** `Client [BEJSON 105 / AI_Dispatch / AI_Dispatch_Async]`
- **Global Config Store:** `Lib_PY/AI/config/ai_global_config.105a.bejson` *(auto-exported on first use; persistently stores `tooling_enabled`, `active_tooling_system`, `default_provider`, `default_model`, `max_tool_roundtrips`, `stdout_routing`, `global_pre_parser_enabled`, `global_post_parser_enabled`, `extension_parser_enabled`)*
- **Tier 1 — Abstraction Layers:**
  - `Dispatch Abstractor` (`lib_bejson_ai_dispatcher.py` — `AIDispatcher` / `AI_Dispatcher`)
  - `Model Catalog` (`lib_bejson_ai_models.py` — `Resolve_Model_Identifier`)
  - `Service Abstractor` (`lib_bejson_ai_translator.py` — `AITranslator` / `AI_Translator`)
- **Tier 2 — Model Features, Gates, Tooling & Modular Parsers (`v1.5.0`):**
  - `Pre-Processing Gate` (`lib_bejson_ai_preprocessor.py`)
  - `Post-Processing Gate` (`lib_bejson_ai_postprocessor.py`)
  - `Tooling/Skill Abstraction Layer` (`ToolingRegistry` / `Tooling_Registry` + `Base_Tooling_System` + `Interactions_Tooling_System`)
  - `Modular Parser Abstraction Layer` (`ParserRegistry` / `Parser_Registry` + `Base_Modular_Parser` — attachable AI/client-turn command parsers)
  - `Python Module / Library Extension Parser Layer` (`ExtensionParserRegistry` / `Extension_Parser_Registry` + `Base_Extension_Module_Parser` — sits next to `Tooling_Registry` and `Parser_Registry` so custom Python modules/libraries extend the parser pipeline)
- **Tier 3 — Service Callers & Security:**
  - `Portable Env/Vault` (`lib_bejson_ai_env_vault.py` — `AIEnvVault`)
  - `Key Rotator & Tracker` (`lib_bejson_ai_key_rotator.py` — `KeyRotator`)
  - `JIT Key Handler` (`lib_bejson_ai_jit_key_handler.py` — `JITKeyHandler`)
  - `Provider Clients` (`GeminiRestClient` / `Gemini_Rest_Client` + `GeminiInteractionsClient` / `Gemini_Interactions_Client`)
  - `Error Registry` (`lib_bejson_AI_bejson_errors.py` — Codes `200–235`)
- **External Target:** `External AI Model (Gemini REST / Interactions API)`

