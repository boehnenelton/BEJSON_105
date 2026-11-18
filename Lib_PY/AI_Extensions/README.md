# `Lib_PY/AI_Extensions` — AI Extensions Family (`v1.0.0`)

Extension plugins, manifests, and profiles subsystem runtime, compiler, and abstraction for the BEJSON 105 AI architecture.

## Overview
- **Extension Manifest Tool**: `lib_bejson_AI_Extensions_manifest_tool.py` (CLI tool to generate and verify SHA-pinned `extension.105a.bejson` manifests).
- **Profile Subsystems**:
  - `lib_bejson_AI_Extensions_profile_runtime.py` (runtime execution and validation for persona/model behavior gates).
  - `lib_bejson_AI_Extensions_profile_compiler.py` (compiles AI persona profiles into structured model instructions).
  - `lib_bejson_AI_Extensions_profile_abstraction.py` (abstract class detection, instruction adaptation, and output sanitization).
- **Sample Plugins**:
  - `render_plain_text/` (sample modular post-processing renderer plugin with SHA-pinned manifest).

## Running Tests

```bash
python3 -m unittest discover -s Lib_PY/AI_Extensions/tests -v
```
