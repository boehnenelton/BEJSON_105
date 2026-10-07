# Library Bug-Fix Report — lib_bejson_Core_bejson_list_validator.py

**Authorization:** Directive 1, explicit user instruction, this conversation, 2026-07-09.
This is the one file under `/libraries/` touched in package version 2 — everything
else in this delivery lives under `library extensions/`.

**File:** `libraries/Lib_PY/Core/lib_bejson_Core_bejson_list_validator.py`
**Version:** 1.2.0 → 1.3.1

## Change 1 — Decouple I/O from validation (as directed)

**Before:** `validate_list(doc_path: str)` loaded the file itself via
`BEJSONCore.bejson_core_load_file(doc_path)`.

**After:** `validate_list(doc_data: dict)` takes an already-loaded document
dict. The caller (typically `MFDBCore.mfdb_core_get_entity_doc()` or
`BEJSONCore.bejson_core_load_file()`) is responsible for loading it.

## Change 2 — Fix the confirmed bug (as directed)

**Before:**
```python
if not StandardValidator.bejson_validator_validate_file(doc_path):
     return {"is_valid": False, "errors": StandardValidator.bejson_validator_get_errors()}
```
`bejson_validator_get_errors()` does not exist anywhere in
`lib_bejson_Core_bejson_validator.py` — a genuine structural-validation
failure raised `AttributeError` instead of returning a clean result.

**After:**
```python
res = StandardValidator.validate_bejson(doc_data, is_file=False)
if not res.valid:
    return {"is_valid": False, "errors": res.errors}
```
`validate_bejson()` is a real function that returns a `ValidationResult`
with `.valid` (bool) and `.errors` (list[str]). It also accepts dicts
natively (`bejson_validator_check_json_syntax` passes a dict straight
through when `is_file=False`), so this change satisfies Change 1 at the
same time.

Verified with a deliberately malformed doc (missing `Format_Creator`):
returns `{'is_valid': False, 'errors': ['Missing key: Format_Creator']}`
instead of raising.

## Change 3 — Format_Version check (found while implementing Directive 2, not requested, fixed because it blocked the directive)

**Before:**
```python
if doc.get("Format_Version") != "104a":
    return {"is_valid": False, "errors": ["List Manager requires BEJSON 104a format."]}
```

Once Category/Nav moved onto the standard `MFDBCore` manifest+entity split
(Directive 2), their entity docs — returned by the new
`MFDBCore.mfdb_core_get_entity_doc()` — are legitimately `Format_Version:
"104"` (they carry `Parent_Hierarchy`, per the MFDB spec), not `"104a"`.
The old check rejected every one of them outright, which would have made
Directive 2 impossible to satisfy.

**After:**
```python
if doc.get("Format_Version") not in ("104a", "104"):
    return {"is_valid": False, "errors": ["List Manager requires BEJSON 104 or 104a format."]}
```
`"104"` was already a recognized valid version in
`lib_bejson_Core_bejson_validator.py`'s own `VALID_VERSIONS` set — this
just stops `validate_list()` from being stricter than the standard
validator it wraps. The hierarchy logic itself is unchanged: it only
depends on `id`/`parent_id` being present in the field map, not on which
of the two valid list-shaped formats the document uses.

## Verification

Ran against four cases directly: a valid two-row category tree, a
duplicate-ID case, an orphaned-parent case, and a deliberately malformed
doc missing a mandatory key. All four returned the expected result shape
with no exceptions. Also verified end-to-end against real `MFDBCore`
entity docs for all five `management_cms` taxonomies (Category, Nav, Page,
Post, Media) — `management_cms_audit()`'s `mfdb_core_deep_verify()` pass
returned zero findings for all five, confirming the fix works against the
real entity-doc shape, not just synthetic test docs.
