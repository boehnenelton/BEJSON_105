"""
Library:        lib_bejson_Core_bejson_errors.py
Family:         Core
Description:    Unified error registry for BEJSON ecosystem.
Version:        2.9.0
Date:           2026-09-25
Author:         Elton Boehnen
Contact:        eltonboehnen@gmail.com | boehnenelton2024.pages.dev | github.com/boehnenelton
Format_Creator: Elton Boehnen
RELATIONAL_ID:  2ca5f1db-d2e9-448c-a2f2-0659ba7ef0d9
Release_Version: 300

Changelog:
  2.9.0 - REMOVED 90-114 (105-series Schema Constraints: required/unique/
          enum/min/max/minLength/maxLength) per Be25 -- value-level schema
          constraints were never wanted as a permanent feature. Field UUIDs
          (84-85) and MFDB FK referential integrity / cascading validation
          (43-47) are kept; that's the entire 105-series feature set now.
          The 2.8.0 renumbering (90-94 -> 110-114) is superseded, not
          undone -- the whole block is gone rather than restored to 90-94.
  2.8.0 - AUDIT FIX (C1, 5th occurrence of the claim-then-collide pattern):
          renumbered 105-series Schema Constraints 90-94 -> 110-114. Codes
          90-94 collided with MD's E_MD_CHUNK_NOT_FOUND..E_MD_INDEX_STALE
          (90-99), assigned to MD by the 2026-08-15 cleanup after this
          range was already claimed. Registry-check-before-claim is now
          mandatory before allocating any new Core error range -- see
          errors.bejson for the authoritative live map, check it first.
  2.7.0 - Added 90-94 for 105-series Schema Constraints (required/unique/
          enum/min/max/minLength/maxLength) -- Tier 1 + top of Tier 2 from
          the Format 105 Validation Extensions proposal. Audit-only,
          105-series only. 95-97 held for pattern/immutable/default.
  2.6.0 - Added 43-47 for 105-series MFDB Referential Integrity (Phase 6).
          Reused the pre-existing E_MFDB_FK_UNRESOLVED (39) rather than
          minting a duplicate -- it was reserved but never actually wired
          to any check until now. 48-49 held unassigned.
  2.5.0 - Reserved 80-89 for Format_Version 105 ("Integrity Era", Format105_
          Master_Plan_Rev2 Appendix B). 80-85 assigned now (Phase 2/3/4
          Core, Validator, Upgrade utility); 86-89 held unassigned for the
          next 105-era validation failure discovered during implementation.
  2.4.0 - Removed Core_Nesting range (130-159) and Cognition range
          (270-289) — those families now own their codes in
          lib_bejson_CoreNesting_bejson_errors.py and
          lib_bejson_Cognition_bejson_errors.py respectively. MFDB codes
          (30-42, 50-72) remain here: MFDB is implemented as part of the
          Core family, not a separate family directory.
"""

# ---------------------------------------------------------------------------
# BEJSON Validation (1-16)
# ---------------------------------------------------------------------------
E_INVALID_JSON                       = 1
E_MISSING_MANDATORY_KEY              = 2
E_INVALID_FORMAT                     = 3
E_INVALID_VERSION                    = 4
E_INVALID_RECORDS_TYPE               = 5
E_INVALID_FIELDS                     = 6
E_INVALID_VALUES                     = 7
E_TYPE_MISMATCH                      = 8
E_RECORD_LENGTH_MISMATCH             = 9
E_RESERVED_KEY_COLLISION             = 10
E_INVALID_RECORD_TYPE_PARENT         = 11
E_NULL_VIOLATION                     = 12
E_FILE_NOT_FOUND                     = 13
E_PERMISSION_DENIED                  = 14
E_ATOMIC_WRITE_FAILED                = 15
E_INVALID_FORMAT_CREATOR             = 16

# BEJSON Core ops (17-29)
# Codes 17-19: parse/serialization layer — added v2.3.0 (parity with TS v2.3.0)
E_CORE_PARSE_ERROR                   = 17
E_CORE_SERIALIZATION_ERROR           = 18
E_CORE_NULL_DOCUMENT                 = 19
E_CORE_INVALID_VERSION               = 20
E_CORE_INVALID_OPERATION             = 21
E_CORE_INDEX_OUT_OF_BOUNDS           = 22
E_CORE_FIELD_NOT_FOUND               = 23
E_CORE_TYPE_CONVERSION_FAILED        = 24
E_CORE_BACKUP_FAILED                 = 25
E_CORE_WRITE_FAILED                  = 26
E_CORE_QUERY_FAILED                  = 27
E_CORE_ENCRYPTION_FAILED             = 28
E_CORE_DECRYPTION_FAILED             = 29

# Aliases — map TS BEJSON_CORE_CODES aliases to canonical codes above
E_CORE_UNSUPPORTED_OPERATION         = E_CORE_INVALID_OPERATION    # 21
E_CORE_WRITE_TYPE_MISMATCH           = E_TYPE_MISMATCH             # 8
E_CORE_WRITE_LENGTH_MISMATCH         = E_RECORD_LENGTH_MISMATCH    # 9

# ---------------------------------------------------------------------------
# MFDB Validation (30-42)
# ---------------------------------------------------------------------------
E_MFDB_NOT_MANIFEST                  = 30
E_MFDB_NOT_ENTITY_FILE               = 31
E_MFDB_MANIFEST_RECORDS_TYPE         = 32
E_MFDB_ENTITY_NOT_FOUND              = 33
E_MFDB_ENTITY_NAME_MISMATCH          = 34
E_MFDB_DUPLICATE_ENTRY               = 35
E_MFDB_NO_PARENT_HIERARCHY           = 36
E_MFDB_MANIFEST_NOT_FOUND            = 37
E_MFDB_BIDIRECTIONAL_FAIL            = 38
E_MFDB_FK_UNRESOLVED                 = 39  # pre-existing code, now actually wired (105 Ref_Integrity, 2026-08-19)
E_MFDB_MISSING_REQUIRED_FIELD        = 40
E_MFDB_NULL_REQUIRED                 = 41
E_MFDB_INVALID_ARCHIVE               = 42

# 43-47: 105-series MFDB Referential Integrity (2026-08-19). 105-series only --
# a 104/104a/104db entity never triggers any of these; the check functions
# gate on Format_Version and no-op immediately for legacy documents.
E_MFDB_FK_TARGET_ENTITY_UNKNOWN      = 43  # fk_target_entity names an entity not in the manifest
E_MFDB_FK_RESTRICT_VIOLATION         = 44  # delete blocked: a "restrict" FK still references this record
E_MFDB_FK_CASCADE_CYCLE              = 45  # a cascade delete walk revisited a record_uuid already visited
E_MFDB_FK_ENTITY_STILL_REFERENCED    = 46  # entity drop blocked: another entity's FK still targets it
E_MFDB_FK_INVALID_ON_DELETE          = 47  # fk_on_delete is not one of restrict/cascade/null
# 48-49 reserved, unassigned.

# 90-114 (was: 105-series Schema Constraints -- required/unique/enum/min/max/
# minLength/maxLength) REMOVED 2026-09-25 per Be25: schema-value-constraint
# enforcement was never wanted long-term. Field UUIDs and FK/cascade
# referential integrity (43-47 above) are the only 105-series additions kept.
# See dev/change-log.md for the full removal record.

# ---------------------------------------------------------------------------
# MFDB Core ops (50-72)
# Codes 57-60: added v2.3.0 (parity with TS MFDB_CORE_CODES v2.3.0)
# ---------------------------------------------------------------------------
E_MFDB_CORE_MANIFEST_NOT_FOUND       = 50
E_MFDB_CORE_ENTITY_NOT_FOUND         = 51
E_MFDB_CORE_WRITE_FAILED             = 52
E_MFDB_CORE_LOCK_FAILED              = 53
E_MFDB_CORE_INVALID_OPERATION        = 54
E_MFDB_CORE_INDEX_OUT_OF_BOUNDS      = 55
E_MFDB_CORE_JOIN_FAILED              = 56
E_MFDB_CORE_DUPLICATE_ENTITY_NAME    = 57
E_MFDB_CORE_RECORD_COUNT_SYNC_FAILED = 58
E_MFDB_CORE_NULL_MANIFEST            = 59
E_MFDB_CORE_ENTITY_NOT_IN_MANIFEST   = 60
E_MFDB_CORE_ARCHIVE_ERROR            = 70
E_MFDB_CORE_MOUNT_CONFLICT           = 71
E_MFDB_CORE_CREATE_FAILED            = 72

# Core_Nesting codes moved to lib_bejson_CoreNesting_bejson_errors.py (v2.4.0)
# Cognition codes moved to lib_bejson_Cognition_bejson_errors.py (v2.4.0)

# ---------------------------------------------------------------------------
# Format_Version 105 / 105a / 105db "Integrity Era" (80-89)
# Reserved per Format105_Master_Plan_Rev2 Appendix B, Finding 2.3 (fixed now,
# not deferred, to avoid a future collision with another library's codes).
# ---------------------------------------------------------------------------
E_FIELD_INTEGRITY_MISMATCH           = 80  # name/field_uuid pair disagree, or target unresolvable
E_FORMAT_UNSUPPORTED                 = 81  # a 105-only function was called on a non-105-series doc
E_RECORD_NOT_FOUND                   = 82  # record_uuid does not resolve to any row
E_UPGRADE_VALIDATION_FAILED          = 83  # bejson_core_upgrade_to_105 built a doc that failed strict-integrity validation
E_DUPLICATE_FIELD_NAME               = 84  # add_field called with a name already present in Fields
E_DUPLICATE_FIELD_UUID               = 85  # a generated/supplied field_uuid collides with an existing one
# 86-89 reserved, unassigned — held for the next 105-era validation failure.
