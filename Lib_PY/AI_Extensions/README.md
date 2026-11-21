# `Lib_PY/AI_Extensions` — plugins and tools for `AI_Core` (`v1.0.0`)

Sibling family of [`AI_Core`](../AI_Core/README.md). Everything optional lives here so the gateway core stays small. No error codes of its own (uses AI_Core `200–249`). Files are `lib_bejson_AI_Extensions_<module>.py`; the same validator checks them (`validate_family(dir, "AI_Extensions")`, 0 violations).

## Plugins (stage, gate `plugins_enabled`)

| Folder | Stage | What it does |
|---|---|---|
| `pre_whitespace_normalizer/` | pre | collapses runs of blank lines and trailing spaces in the prompt |
| `post_think_stripper/` | post | removes `<think>…</think>` blocks from the reply text |
| `render_plain_text/` | render | strips Markdown emphasis/heading/fence markers into terminal-friendly text (`rendered_output`, `rendered_format=text`) |

Each plugin folder holds the module plus `extension.105a.bejson` (id, version, stage, priority, entry class, module SHA-256). Edit a module and the pin no longer matches, so discovery skips it until the manifest is regenerated with `lib_bejson_AI_Extensions_manifest_tool.py`. `PluginRegistry.discover_plugins()` loads only from this directory (or `BEJSON_AI_EXTENSIONS_DIR`) unless `allow_external_directory=True`.

## Profile modules (AI Profile 2.0 on BEJSON 105)

| Module | Purpose |
|---|---|
| `profile_compiler` | compiles a Profile 2.0 row into a system instruction: job contract first, invisible temper state, trigger taxonomy, knowledge block, safety block (temper and trigger blocks are omitted when affective features are disabled). `compiler_compile_profile(profile_doc, ...)` |
| `profile_abstraction` | cloud vs on-device (SLM) adaptation: model-class detection, instruction condensing, JSON output sanitizing, gated parser dispatch |
| `profile_runtime` | validates and runs embedded Python/JavaScript `Parser` and `Renderer` code; fingerprint approval gate; sandbox `srcdoc` builder |

Embedded code never runs unless its fingerprint (`ai_profiles_embedded_fingerprint`) is in the approved list you pass in. Python parsers are statically checked (allowed imports only, no `open`, no dunder access) and run with a timeout; JavaScript parsers are syntax-checked and only ever rendered inside `sandbox="allow-scripts"`.

Ported from the 104 family `AI`: `profile_2_compiler`, `profiles_abstraction`, `profile_parser_runtime`. Differences: 105 profiles (no `Record_Type_Parent`), null-safe numeric cells, runtime dispatch instead of the removed `gemini_profiles_run_parser`.

## Tests

```bash
python3 -m unittest discover -s Lib_PY/AI_Extensions/tests -v   # 21 tests
```
