# Library Instructions: JavaScript (Lib_JS)
**Relational ID:** gcli-lib-js-001

## JS Standards
- **Error Handling**: Throw `BEJSONError` with standard integer codes (Sec. 46).
- **Asynchronicity**: Ensure atomic disk operations are awaited or handled via POSIX-equivalent locks.
- **Portability**: Avoid hardcoded paths; use environment variables or registry lookups.
- **Data Integrity**: 
    - **Validation**: Enforce structural correctness (Level 1-3). Failures result in hard errors.
    - **Standardization**: Enforce architectural compliance (snake_case, _fk suffixes). Failures result in warnings only.
    - **Structure**: Always use `null` for absent values. Treat field reordering as a breaking change.
- **Field Mapping**: Field Map Indexing is the authoritative standard for field access. Positional hard-coding is deprecated. Use "Safe Get" fallbacks for legacy compatibility.

---
*Refer to the Project Root GEMINI.md for the Field Map Migration Plan.*
