# Library:        lib_bejson_Core_bejson_errors.sh
# Family:         Core
# Description:    Centralized error code registry for all Bash BEJSON libraries. Mirrors lib_bejson_Core_bejson_errors.js and lib_bejson_Core_bejson_errors.py.
# Version:        1.7.0
# Date:           2026-09-25
# Author:         Elton Boehnen
# Contact:        eltonboehnen@gmail.com | boehnenelton2024.pages.dev | github.com/boehnenelton
# Format_Creator: Elton Boehnen
# RELATIONAL_ID:  78351cc8-b634-483e-b350-a90fafd1bfad
# Release_Version: 300
#
# Changelog:
#   1.7.0 - Removed 110-114 (Schema Constraints) per Be25. 43-47 (FK/
#           cascade) and 80-85 (field identity guards) unchanged.
#   1.6.0 - AUDIT FIX (H2): SH was three generations behind PY/TS/JS, ending
#           at code 72. Added the three missing ranges verbatim from the
#           canonical PY registry: 43-47 (MFDB Referential Integrity), 80-85
#           (Format 105 Integrity Era), 110-114 (Format 105 Schema
#           Constraints, added directly at the post-collision numbers --
#           see C1). SH now has the same error surface as PY/JS/TS.
#   1.5.0 - LEGACY ALIASES section deleted (Step 2 — 1.32 finalization).
#           E_VAL_NOT_JSON, E_VAL_MISSING_KEY, E_VAL_BAD_FORMAT,
#           E_VAL_BAD_VERSION, E_VAL_BAD_CREATOR, E_VAL_SCHEMA_MISMATCH,
#           E_VAL_INVALID_TYPE removed. lib_bejson_Core_bejson_validator.sh
#           updated to use primary unified codes at all return sites.
#   1.4.0 - Removed Core_Nesting range (130-159) — that family now owns its
#           codes in lib_bejson_CoreNesting_bejson_errors.sh. MFDB codes
#           (30-49, 50-79) remain here: MFDB is implemented as part of the
#           Core family, not a separate family directory.

# ===========================================================================
# BEJSON VALIDATOR ERRORS (1–19)  — mirrors E_* in lib_bejson_Core_bejson_errors.js / .py
# ===========================================================================
[[ -v E_INVALID_JSON                ]] || readonly E_INVALID_JSON=1
[[ -v E_MISSING_MANDATORY_KEY       ]] || readonly E_MISSING_MANDATORY_KEY=2
[[ -v E_INVALID_FORMAT              ]] || readonly E_INVALID_FORMAT=3
[[ -v E_INVALID_VERSION             ]] || readonly E_INVALID_VERSION=4
[[ -v E_INVALID_RECORDS_TYPE        ]] || readonly E_INVALID_RECORDS_TYPE=5
[[ -v E_INVALID_FIELDS              ]] || readonly E_INVALID_FIELDS=6
[[ -v E_INVALID_VALUES              ]] || readonly E_INVALID_VALUES=7
[[ -v E_TYPE_MISMATCH               ]] || readonly E_TYPE_MISMATCH=8
[[ -v E_RECORD_LENGTH_MISMATCH      ]] || readonly E_RECORD_LENGTH_MISMATCH=9
[[ -v E_RESERVED_KEY_COLLISION      ]] || readonly E_RESERVED_KEY_COLLISION=10
[[ -v E_INVALID_RECORD_TYPE_PARENT  ]] || readonly E_INVALID_RECORD_TYPE_PARENT=11
[[ -v E_NULL_VIOLATION              ]] || readonly E_NULL_VIOLATION=12
[[ -v E_FILE_NOT_FOUND              ]] || readonly E_FILE_NOT_FOUND=13
[[ -v E_PERMISSION_DENIED           ]] || readonly E_PERMISSION_DENIED=14
[[ -v E_ATOMIC_WRITE_FAILED         ]] || readonly E_ATOMIC_WRITE_FAILED=15
[[ -v E_INVALID_FORMAT_CREATOR      ]] || readonly E_INVALID_FORMAT_CREATOR=16

# ===========================================================================
# BEJSON CORE ERRORS (20–29)
# ===========================================================================
[[ -v E_CORE_INVALID_VERSION        ]] || readonly E_CORE_INVALID_VERSION=20
[[ -v E_CORE_INVALID_OPERATION      ]] || readonly E_CORE_INVALID_OPERATION=21
[[ -v E_CORE_INDEX_OUT_OF_BOUNDS    ]] || readonly E_CORE_INDEX_OUT_OF_BOUNDS=22
[[ -v E_CORE_FIELD_NOT_FOUND        ]] || readonly E_CORE_FIELD_NOT_FOUND=23
[[ -v E_CORE_TYPE_CONVERSION_FAILED ]] || readonly E_CORE_TYPE_CONVERSION_FAILED=24
[[ -v E_CORE_BACKUP_FAILED          ]] || readonly E_CORE_BACKUP_FAILED=25
[[ -v E_CORE_WRITE_FAILED           ]] || readonly E_CORE_WRITE_FAILED=26
[[ -v E_CORE_QUERY_FAILED           ]] || readonly E_CORE_QUERY_FAILED=27
[[ -v E_CORE_ENCRYPTION_FAILED      ]] || readonly E_CORE_ENCRYPTION_FAILED=28
[[ -v E_CORE_DECRYPTION_FAILED      ]] || readonly E_CORE_DECRYPTION_FAILED=29

# ===========================================================================
# MFDB VALIDATOR ERRORS (30–49)
# ===========================================================================
[[ -v E_MFDB_NOT_MANIFEST           ]] || readonly E_MFDB_NOT_MANIFEST=30
[[ -v E_MFDB_NOT_ENTITY_FILE        ]] || readonly E_MFDB_NOT_ENTITY_FILE=31
[[ -v E_MFDB_MANIFEST_RECORDS_TYPE  ]] || readonly E_MFDB_MANIFEST_RECORDS_TYPE=32
[[ -v E_MFDB_ENTITY_NOT_FOUND       ]] || readonly E_MFDB_ENTITY_NOT_FOUND=33
[[ -v E_MFDB_ENTITY_NAME_MISMATCH   ]] || readonly E_MFDB_ENTITY_NAME_MISMATCH=34
[[ -v E_MFDB_DUPLICATE_ENTRY        ]] || readonly E_MFDB_DUPLICATE_ENTRY=35
[[ -v E_MFDB_NO_PARENT_HIERARCHY    ]] || readonly E_MFDB_NO_PARENT_HIERARCHY=36
[[ -v E_MFDB_MANIFEST_NOT_FOUND     ]] || readonly E_MFDB_MANIFEST_NOT_FOUND=37
[[ -v E_MFDB_BIDIRECTIONAL_FAIL     ]] || readonly E_MFDB_BIDIRECTIONAL_FAIL=38
[[ -v E_MFDB_FK_UNRESOLVED          ]] || readonly E_MFDB_FK_UNRESOLVED=39
[[ -v E_MFDB_MISSING_REQUIRED_FIELD ]] || readonly E_MFDB_MISSING_REQUIRED_FIELD=40
[[ -v E_MFDB_NULL_REQUIRED          ]] || readonly E_MFDB_NULL_REQUIRED=41
[[ -v E_MFDB_INVALID_ARCHIVE        ]] || readonly E_MFDB_INVALID_ARCHIVE=42

# ===========================================================================
# MFDB REFERENTIAL INTEGRITY (43–47) — AUDIT FIX (H2), added 2026-09-13
# Mirrors PY 2.6.0 / TS 2.6.0. FK_UNRESOLVED (39) reused, not duplicated,
# same as PY/TS did.
# ===========================================================================
[[ -v E_MFDB_FK_TARGET_ENTITY_UNKNOWN    ]] || readonly E_MFDB_FK_TARGET_ENTITY_UNKNOWN=43
[[ -v E_MFDB_FK_RESTRICT_VIOLATION       ]] || readonly E_MFDB_FK_RESTRICT_VIOLATION=44
[[ -v E_MFDB_FK_CASCADE_CYCLE            ]] || readonly E_MFDB_FK_CASCADE_CYCLE=45
[[ -v E_MFDB_FK_ENTITY_STILL_REFERENCED  ]] || readonly E_MFDB_FK_ENTITY_STILL_REFERENCED=46
[[ -v E_MFDB_FK_INVALID_ON_DELETE        ]] || readonly E_MFDB_FK_INVALID_ON_DELETE=47

# ===========================================================================
# MFDB CORE ERRORS (50–79)
# ===========================================================================
# MFDB Core error codes — aligned with canonical PY/JS registry
[[ -v E_MFDB_CORE_MANIFEST_NOT_FOUND ]] || readonly E_MFDB_CORE_MANIFEST_NOT_FOUND=50
[[ -v E_MFDB_CORE_ENTITY_NOT_FOUND  ]] || readonly E_MFDB_CORE_ENTITY_NOT_FOUND=51
[[ -v E_MFDB_CORE_WRITE_FAILED      ]] || readonly E_MFDB_CORE_WRITE_FAILED=52
[[ -v E_MFDB_CORE_LOCK_FAILED       ]] || readonly E_MFDB_CORE_LOCK_FAILED=53
[[ -v E_MFDB_CORE_INVALID_OPERATION ]] || readonly E_MFDB_CORE_INVALID_OPERATION=54
[[ -v E_MFDB_CORE_INDEX_OUT_OF_BOUNDS ]] || readonly E_MFDB_CORE_INDEX_OUT_OF_BOUNDS=55
[[ -v E_MFDB_CORE_JOIN_FAILED       ]] || readonly E_MFDB_CORE_JOIN_FAILED=56
[[ -v E_MFDB_CORE_ARCHIVE_ERROR     ]] || readonly E_MFDB_CORE_ARCHIVE_ERROR=70
[[ -v E_MFDB_CORE_MOUNT_CONFLICT    ]] || readonly E_MFDB_CORE_MOUNT_CONFLICT=71
[[ -v E_MFDB_CORE_CREATE_FAILED     ]] || readonly E_MFDB_CORE_CREATE_FAILED=72

# ===========================================================================
# FORMAT 105 INTEGRITY ERA (80–85) — AUDIT FIX (H2), added 2026-09-13
# Mirrors PY 2.5.0 / TS 2.5.0. 86–89 held unassigned, same as PY.
# ===========================================================================
[[ -v E_FIELD_INTEGRITY_MISMATCH    ]] || readonly E_FIELD_INTEGRITY_MISMATCH=80
[[ -v E_FORMAT_UNSUPPORTED          ]] || readonly E_FORMAT_UNSUPPORTED=81
[[ -v E_RECORD_NOT_FOUND            ]] || readonly E_RECORD_NOT_FOUND=82
[[ -v E_UPGRADE_VALIDATION_FAILED   ]] || readonly E_UPGRADE_VALIDATION_FAILED=83
[[ -v E_DUPLICATE_FIELD_NAME        ]] || readonly E_DUPLICATE_FIELD_NAME=84
[[ -v E_DUPLICATE_FIELD_UUID        ]] || readonly E_DUPLICATE_FIELD_UUID=85

# FORMAT 105 SCHEMA CONSTRAINTS (110-114) REMOVED 2026-09-25 per Be25 --
# value-level schema constraints were never wanted as a permanent
# feature. Field UUIDs (84-85) and FK/cascade referential integrity
# (43-47 above) are the entire kept 105-series feature set now.

# Core_Nesting codes moved to lib_bejson_CoreNesting_bejson_errors.sh (v1.4.0)
