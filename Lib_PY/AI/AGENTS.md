# AGENTS.md - Lib_PY/AI

**Description:** Local standing rules for changes to the AI gateway, created from the 2026-11-17 gap-audit remediation (report: `$ADMIN_REPORTS/Audits/AI_Libraries_Gap_Audit.md`).
**Author:** Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
**License:** PolyForm-Noncommercial-1.0.0

## Root causes addressed
1. Secrets and paths handled ad hoc per call site (key placed in a URL, literal `/storage/emulated/0/.env/...` fallbacks).
2. Exception handling written to "keep going" without preserving evidence (config reset, double handler execution, unbounded provider bodies in exceptions).
3. Dynamic import of caller-supplied directories without a trust boundary.
4. Docs, version strings, and tests allowed to drift from code.

## Rules
- API keys travel only in the `x-goog-api-key` header. Never build a URL, log line, or exception message containing a key.
- Any provider text placed in an `AIException` must pass through `redact_provider_error_text()` (`lib_bejson_ai_features_common.py`).
- No literal absolute paths. Resolve through `$DEFINITIONS_FILE`, `BEJSON_*` overrides, or `SECUREENV_FILE` from definitions.
- Never discard unreadable persisted state: preserve it (`.corrupt-<epoch>`), log a warning, then regenerate.
- Decide call shape before invoking user-supplied callables (`inspect.signature().bind`); never retry a callable after it raised.
- `discover_providers()` imports code. It scans only this package directory unless `allow_external_directory=True` is passed explicitly.
- Every module that handles errors, keys, or provider calls must have a `logging.getLogger(...)`; no `print()`.
- Any behavior change ships with a test in `tests/` in the same change; update README test counts and `NEXT_STEP_PLAN.md` version text at the same time.
- Run `python3 -m unittest discover -s Lib_PY/AI/tests` before reporting completion.

## Relocated from ~/.gemini/GEMINI.md (2026-11-17)

- **Model resolution:** Clients, tests, and dispatchers targeting Gemini REST must resolve models through `lib_bejson_ai_models.py` (`Resolve_Model_Identifier`, `ACTIVE_TEXT_MODELS_REGISTRY`). That registry is the single source of truth for model IDs; do not copy model lists into docs or policy. Dispatching an unverified or deprecated model ID without dynamic validation is prohibited.
- **Dispatch surface:** Every AI module offers synchronous and non-blocking dispatch (`dispatch_async`), optional stdout routing (`stdout_routing=True`), and `Name_Case` bindings.
- **Name_Case exports:** Tier 1-3 classes keep their canonical aliases (`Tooling_Registry`, `AI_Global_Config_Manager`, `Base_Tooling_System`, `Interactions_Tooling_System`, `AI_Dispatcher`, `AI_Translator`, `Gemini_Interactions_Client`, `Gemini_Rest_Client`) and method accessors (`Register_Tooling_System`, `Select_Tooling_System`, `Get_Active_System`, `Enable_Tooling`, `Disable_Tooling`, `Get_Setting`, `Update_Setting`).
- **Tooling:** Config-gated through `config/ai_global_config.105a.bejson`; no hardcoded application tools in core libraries; tool loops run autonomously and the active system is switchable. Skills: `code-taxonomy-architect`, `cli-ai-standardizer`, `bejson-enforcement-suite-builder`.
