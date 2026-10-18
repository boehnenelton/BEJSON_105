# -----------------------------------------------------------------------------
# Library:         lib_bejson_Core_bejson_errors.sh
# Family:          Core
# Module Purpose:  Unified numeric error-code registry shared by the BEJSON, MFDB and Nesting modules.
# Architecture:    Shared numeric error-code registry. Codes are grouped by layer (BEJSON validation/core, MFDB, Nesting); a code name containing MFDB does not make the module that raises it MFDB-specific.
# Format_Scope:    All layers (registry only)
# Glossary:        BEJSON 104, 104a and 104db are the three file formats (Format_Version). 104db = ONE file holding 2+ entity types
#                  (Record_Type_Parent discriminator, null-padding). MFDB is NOT a format and NOT 104db: it is a layer made of one 104a manifest
#                  (104a.mfdb.bejson) plus dense 104 entity files linked by Parent_Hierarchy. MFDB-132 = an MFDB packed into one Chunked-104a document.
# Version:         1.7.0
# Release_Version: 300
# Date:            2026-10-16
# Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
# Format_Creator:  Elton Boehnen
# RELATIONAL_ID:   21a3adb9-7d03-4fd1-ba06-161643594e88
# Changelog:
#   1.7.0 (2026-10-16) - Added the seven Core codes missing versus the Python registry: E_CORE_PARSE_ERROR (17), SERIALIZATION_ERROR (18), NULL_DOCUMENT (19), E_MFDB_CORE_DUPLICATE_ENTITY_NAME (57), RECORD_COUNT_SYNC_FAILED (58), NULL_MANIFEST (59), ENTITY_NOT_IN_MANIFEST (60).
#           Bash now has every code the Python Core registry has (66), same names and values.
#   1.6.0 (2026-10-16) - Added the Core nesting codes E_NESTING_* (130-139), moved here from the removed lib_bejson_Core_bejson_nesting_errors.sh.
#           Core now resolves every error code through this single file. Codes, names and values unchanged.
# -----------------------------------------------------------------------------

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
[[ -v E_CORE_PARSE_ERROR         ]] || readonly E_CORE_PARSE_ERROR=17
[[ -v E_CORE_SERIALIZATION_ERROR ]] || readonly E_CORE_SERIALIZATION_ERROR=18
[[ -v E_CORE_NULL_DOCUMENT       ]] || readonly E_CORE_NULL_DOCUMENT=19

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
[[ -v E_MFDB_CORE_DUPLICATE_ENTITY_NAME    ]] || readonly E_MFDB_CORE_DUPLICATE_ENTITY_NAME=57
[[ -v E_MFDB_CORE_RECORD_COUNT_SYNC_FAILED ]] || readonly E_MFDB_CORE_RECORD_COUNT_SYNC_FAILED=58
[[ -v E_MFDB_CORE_NULL_MANIFEST            ]] || readonly E_MFDB_CORE_NULL_MANIFEST=59
[[ -v E_MFDB_CORE_ENTITY_NOT_IN_MANIFEST   ]] || readonly E_MFDB_CORE_ENTITY_NOT_IN_MANIFEST=60
[[ -v E_MFDB_CORE_ARCHIVE_ERROR     ]] || readonly E_MFDB_CORE_ARCHIVE_ERROR=70
[[ -v E_MFDB_CORE_MOUNT_CONFLICT    ]] || readonly E_MFDB_CORE_MOUNT_CONFLICT=71
[[ -v E_MFDB_CORE_CREATE_FAILED     ]] || readonly E_MFDB_CORE_CREATE_FAILED=72


# ===========================================================================
# CORE NESTING ERRORS (130-159) - nested BEJSON 104; part of Core, no separate errors file
# ===========================================================================
[[ -v E_NESTING_INVALID_CELL       ]] || readonly E_NESTING_INVALID_CELL=130
[[ -v E_NESTING_NOT_BEJSON         ]] || readonly E_NESTING_NOT_BEJSON=131
[[ -v E_NESTING_DEPTH_EXCEEDED     ]] || readonly E_NESTING_DEPTH_EXCEEDED=132
[[ -v E_NESTING_CACHE_MISS         ]] || readonly E_NESTING_CACHE_MISS=133
[[ -v E_NESTING_SCHEMA_MISMATCH    ]] || readonly E_NESTING_SCHEMA_MISMATCH=134
[[ -v E_NESTING_CIRCULAR_REF       ]] || readonly E_NESTING_CIRCULAR_REF=135
[[ -v E_NESTING_VALIDATION_FAILED  ]] || readonly E_NESTING_VALIDATION_FAILED=136
[[ -v E_NESTING_FIELD_MAP_FAILED   ]] || readonly E_NESTING_FIELD_MAP_FAILED=137
[[ -v E_NESTING_QUERY_INVALID_PATH ]] || readonly E_NESTING_QUERY_INVALID_PATH=138
[[ -v E_NESTING_QUERY_EMPTY_PATH   ]] || readonly E_NESTING_QUERY_EMPTY_PATH=139

# 140-159 reserved for future Core nesting codes.

# --- Format 105 & MFDB v1.40 Referential Integrity ---
[[ -v E_MFDB_FK_TARGET_ENTITY_UNKNOWN    ]] || readonly E_MFDB_FK_TARGET_ENTITY_UNKNOWN=43
[[ -v E_MFDB_FK_RESTRICT_VIOLATION       ]] || readonly E_MFDB_FK_RESTRICT_VIOLATION=44
[[ -v E_MFDB_FK_CASCADE_CYCLE            ]] || readonly E_MFDB_FK_CASCADE_CYCLE=45
[[ -v E_MFDB_FK_ENTITY_STILL_REFERENCED  ]] || readonly E_MFDB_FK_ENTITY_STILL_REFERENCED=46
[[ -v E_MFDB_FK_INVALID_ON_DELETE        ]] || readonly E_MFDB_FK_INVALID_ON_DELETE=47
[[ -v E_FIELD_INTEGRITY_MISMATCH    ]] || readonly E_FIELD_INTEGRITY_MISMATCH=80
[[ -v E_FORMAT_UNSUPPORTED          ]] || readonly E_FORMAT_UNSUPPORTED=81
[[ -v E_RECORD_NOT_FOUND            ]] || readonly E_RECORD_NOT_FOUND=82
[[ -v E_UPGRADE_VALIDATION_FAILED   ]] || readonly E_UPGRADE_VALIDATION_FAILED=83
[[ -v E_DUPLICATE_FIELD_NAME        ]] || readonly E_DUPLICATE_FIELD_NAME=84
[[ -v E_DUPLICATE_FIELD_UUID        ]] || readonly E_DUPLICATE_FIELD_UUID=85
