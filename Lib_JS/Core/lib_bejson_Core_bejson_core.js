/**
 * Library:        lib_bejson_Core_bejson_core.js
 * Family:         Core
 * Description:    Low-level primitive operations for BEJSON document manipulation.
 * BEJSON:         BEJSON stands for BOEHNEN ELTON JSON. Authoritative definition;
 *                 do not restate or reinterpret this acronym elsewhere.
 * MFDB:           MFDB stands for Multi File Database. Authoritative definition;
 *                 do not restate or reinterpret this acronym elsewhere.
 * Version:        3.6.0
 * Date:           2026-10-27
 * Author:         Elton Boehnen
 * Contact:        eltonboehnen@gmail.com | boehnenelton2024.pages.dev | github.com/boehnenelton
 * Format_Creator: Elton Boehnen
 * RELATIONAL_ID:  78d11421-179b-4ebf-a152-96d74be2b03f
 * Release_Version: 300
 *
 * CHANGE (2026-10-06): Consolidation re-merge -- the V6-PKG101 silent-catch
 * logging fix (_bejson_hide field-map cache attach) had been reverted/lost
 * on the forward V10-PKG102 branch; re-applied here on top of the current
 * Object.defineProperty-based implementation, no behavior change.
 *
 * CHANGE (2026-10-03) 2.1.0: SELF-MAINTAINING FIELD MAP, parity with Python
 * core 3.4.0/3.5.0. get_field_map/get_field_index validate against the live
 * field layout on every read (no more stale map after Fields edits), 105-series
 * maps return ROW positions and are warmed on parse/load, cache keys are
 * non-enumerable so JSON.stringify never leaks them. New: get_field_cache(),
 * warm(). 104 load stays untouched (lazy).
 *
 * CHANGE (2026-08-08): LIB-C5 -- _keyCache was a single slot, thrashing
 * on any multi-entity session touching more than one password/salt
 * pair. Now a small fixed-size (4) LRU. Not a security fix -- worst
 * case before was just a repeated PBKDF2 derivation, never wrong
 * encryption -- purely a performance fix.
 */

'use strict';

const BEJSON_ERRORS = (typeof require !== 'undefined') 
  ? require('./lib_bejson_Core_bejson_errors.js') 
  : (window.BEJSON_ERRORS || {});

 const {
     E_CORE_INVALID_VERSION,
     E_CORE_INVALID_OPERATION,
     E_CORE_INDEX_OUT_OF_BOUNDS,
     E_CORE_FIELD_NOT_FOUND,
     E_CORE_TYPE_CONVERSION_FAILED,
     E_CORE_BACKUP_FAILED,
     E_CORE_WRITE_FAILED,
     E_CORE_QUERY_FAILED,
     E_CORE_ENCRYPTION_FAILED,
     E_CORE_DECRYPTION_FAILED
 } = BEJSON_ERRORS;

// Universal library release line (Policy 2026-08-14). Only this file --
// the Core BEJSON file -- defines RELEASE_VERSION as a real code variable;
// all other library files declare it in the header comment only.
const RELEASE_VERSION = 300;

 // --- Environment Detection ---
let crypto = (typeof window !== 'undefined' && window.crypto) ? window.crypto : null;
if (!crypto && typeof require !== 'undefined') {
    try {
        crypto = require('crypto').webcrypto;
    } catch (e) {
        // Fallback for older Node.js or other environments
    }
}

class BEJSONCoreError extends Error {
    constructor(message, code) {
        super(message);
        this.code = code;
        this.name = "BEJSONCoreError";
    }
}

class BEJSONEngine {
    constructor() {
        this.systems = new Map();
        this.state = 'BOOT';
    }
    registerSystem(name, system) { this.systems.set(name, system); }
    getSystem(name) { return this.systems.get(name); }
    loop(dt) {
        this.systems.forEach(s => {
            if (s.step) s.step(dt);
            if (s.update) s.update(dt);
        });
    }
}

// --- Internal Key Cache for current session/document operation ---
// LIB-C5 fix (2026-08-08): was a single slot, same rationale as the TS
// sibling -- small fixed-size LRU (4 slots) instead.
// MED-4 audit fix (2026-08-15): 4 slots was too small for sessions
// switching between more than 4 password/salt combos (thrashing, re-deriving
// PBKDF2 100k-iteration keys unnecessarily). Bumped to 12.
const _KEY_CACHE_MAX_SLOTS = 12;
const _keyCache = [];

// SECURITY (adversarial review, finding 5): the cache must never retain the
// plaintext password. Entries are looked up by an HMAC-SHA-256 fingerprint of
// (salt, password) computed under a random per-process, NON-extractable key,
// so a heap dump yields neither the password nor an offline-crackable hash.
let _cacheMacKeyPromise = null;
function _getCacheMacKey() {
    if (!_cacheMacKeyPromise) {
        _cacheMacKeyPromise = crypto.subtle.generateKey({ name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
    }
    return _cacheMacKeyPromise;
}
async function _cacheFingerprint(password, saltB64) {
    const macKey = await _getCacheMacKey();
    const data = new TextEncoder().encode(saltB64 + "\u0000" + password);
    const sig = await crypto.subtle.sign("HMAC", macKey, data);
    return CryptoUtils.ab2base64(sig);
}
/** Drop every cached derived key (call when a session/document is closed). */
function clearKeyCache() { _keyCache.length = 0; }

async function _getOrDeriveKey(password, salt, providedKey = null) {
    if (providedKey) return providedKey;
    const saltB64 = CryptoUtils.ab2base64(salt);
    const fp = await _cacheFingerprint(password, saltB64);
    const hitIdx = _keyCache.findIndex((e) => e.fp === fp);
    if (hitIdx !== -1) {
        const [hit] = _keyCache.splice(hitIdx, 1);
        _keyCache.push(hit); // move to most-recently-used end
        return hit.key;
    }
    const key = await CryptoUtils.deriveKey(password, salt);
    if (_keyCache.length >= _KEY_CACHE_MAX_SLOTS) {
        _keyCache.shift(); // evict least-recently-used
    }
    _keyCache.push({ fp, key });
    return key;
}

const CryptoUtils = {
    async deriveKey(password, salt) {
        const enc = new TextEncoder();
        const keyMaterial = await crypto.subtle.importKey("raw", enc.encode(password), { name: "PBKDF2" }, false, ["deriveKey"]);
        return await crypto.subtle.deriveKey(
            { name: "PBKDF2", salt: salt, iterations: 100000, hash: "SHA-256" },
            keyMaterial,
            { name: "AES-GCM", length: 256 },
            false,
            ["encrypt", "decrypt"]
        );
    },

    ab2base64(buf) { const b = new Uint8Array(buf); let s = ''; for (let i = 0; i < b.length; i++) s += String.fromCharCode(b[i]); return btoa(s); },
    base642ab(base64) { const b = atob(base64); return new Uint8Array(b.length).map((_, i) => b.charCodeAt(i)); },

    async encryptRecord(doc, recordIndex, password, providedSalt = null, providedKey = null) {
        if (recordIndex < 0 || recordIndex >= doc.Values.length) throw new BEJSONCoreError("Index out of bounds", E_CORE_INDEX_OUT_OF_BOUNDS);
        
        const record = doc.Values[recordIndex];
        // REUSE salt if provided, otherwise generate. Reusing salt allows key caching.
        const salt = providedSalt || crypto.getRandomValues(new Uint8Array(16));
        const key = await _getOrDeriveKey(password, salt, providedKey);
        const saltB64 = this.ab2base64(salt);
        
        const newRecord = [...record];
        for (let i = 0; i < newRecord.length; i++) {
            const field = doc.Fields[i];
            if (field.name === "Record_Type_Parent" || field.name === "is_encrypted") continue;
            
            const val = newRecord[i];
            if (val === null) continue;
            if (typeof val === "object" && val._enc === "AES-GCM") continue;

            const dataEnc = new TextEncoder().encode(JSON.stringify(val));
            const iv = crypto.getRandomValues(new Uint8Array(12));
            const ciphertext = await crypto.subtle.encrypt({ name: "AES-GCM", iv: iv }, key, dataEnc);
            
            const ivB64 = this.ab2base64(iv);
            const ctB64 = this.ab2base64(ciphertext);
            
            newRecord[i] = {
                _enc: "AES-GCM",
                salt: saltB64,
                iv: ivB64,
                ct: ctB64
            };
        }

        const ieIdx = bejson_core_get_field_index(doc, "is_encrypted");
        if (ieIdx !== -1) newRecord[ieIdx] = true;

        doc.Values[recordIndex] = newRecord;
        return doc;
    },

    async decryptRecord(doc, recordIndex, password) {
        if (recordIndex < 0 || recordIndex >= doc.Values.length) throw new BEJSONCoreError("Index out of bounds", E_CORE_INDEX_OUT_OF_BOUNDS);
        
        const record = doc.Values[recordIndex];
        const newRecord = [...record];
        
        for (let i = 0; i < newRecord.length; i++) {
            const val = newRecord[i];
            
            // Handle both legacy string format and new object format for transition
            let saltB64, ivB64, ctB64;
            
            if (typeof val === "string" && val.startsWith("ENC:AES-GCM:")) {
                const parts = val.split(":");
                if (parts.length === 5) {
                    saltB64 = parts[2];
                    ivB64 = parts[3];
                    ctB64 = parts[4];
                }
            } else if (val && typeof val === "object" && val._enc === "AES-GCM") {
                saltB64 = val.salt;
                ivB64 = val.iv;
                ctB64 = val.ct;
            }
            
            if (!saltB64 || !ivB64 || !ctB64) continue;
            
            try {
                const salt = this.base642ab(saltB64);
                const iv = this.base642ab(ivB64);
                const ct = this.base642ab(ctB64);
                const key = await _getOrDeriveKey(password, salt);
                
                const decrypted = await crypto.subtle.decrypt({ name: "AES-GCM", iv: iv }, key, ct);
                newRecord[i] = JSON.parse(new TextDecoder().decode(decrypted));
            } catch (e) {
                throw new BEJSONCoreError("Decryption failed at field " + i + ": " + e.message, E_CORE_DECRYPTION_FAILED);
            }
        }

        const ieIdx = bejson_core_get_field_index(doc, "is_encrypted");
        if (ieIdx !== -1) {
            newRecord[ieIdx] = newRecord.some((v, idx) => {
                if (doc.Fields[idx].name === "is_encrypted") return false;
                return (typeof v === "string" && v.startsWith("ENC:AES-GCM:")) || (v && v._enc === "AES-GCM");
            });
        }

        doc.Values[recordIndex] = newRecord;
        return doc;
    }
};

// Stubs for parser compatibility (Audit 2 Finding)
function bejson_core_is_valid(doc) { return !!(doc && doc.Format === "BEJSON"); }
function bejson_core_get_version(doc) { return doc ? (doc.Format_Version || doc.Version) : null; }
function bejson_core_get_stats(doc) {
    if (!doc || !doc.Values) return { records: 0, fields: 0 };
    return { records: doc.Values.length, fields: doc.Fields ? doc.Fields.length : 0 };
}

// ---------------------------------------------------------------------------
// FIELD MAP CACHE -- SELF-MAINTAINING (v2.1.0, mirrors Python core 3.4.0/3.5.0)
//
// Callers never build or refresh a field map. Every lookup validates the
// cache against the document's live field layout (cheap version+name+uuid
// fingerprint) and rebuilds it if it is missing, wrong-shaped or stale, so
// add-field, rename, reorder or an out-of-band Fields edit can never leave a
// stale index behind. 105-series documents are also warmed the moment they
// are parsed/loaded. Cache keys live on the doc as NON-ENUMERABLE properties,
// so a bare JSON.stringify(doc) can never leak them into a file.
// ---------------------------------------------------------------------------
const _FIELD_MAP_CACHE = new Map();           // shared 104-series name->index maps
const _105_SERIES = ["105", "105a", "105db"];

function _bejson_hide(doc, key, value) {
    try {
        Object.defineProperty(doc, key, { value, enumerable: false, writable: true, configurable: true });
    } catch (e) {
        /* frozen / sealed doc: lookups still work, just uncached */
        console.debug(`[Core] Could not attach field-map cache to document (frozen/sealed or not extensible): ${e.message}`);
    }
}

/**
 * Absolute Values-row column for Fields[fieldIdx].
 * 105/105a: row = [record_uuid, ...Fields] -> fieldIdx + 1.
 * 105db: row = [Record_Type_Parent, record_uuid, ...Fields[1:]]. Fields[0] IS
 * Record_Type_Parent (column 0); only Fields[1:] shift by the single inserted
 * record_uuid column: Fields[0] -> 0, Fields[i>=1] -> i + 1.
 * (A flat "+2" for 105db mis-addresses every data field by one column.)
 */
function _bejson_abs_col(doc, fieldIdx) {
    const v = doc.Format_Version;
    if (v === "105db") return fieldIdx === 0 ? 0 : fieldIdx + 1;
    return _105_SERIES.includes(v) ? fieldIdx + 1 : fieldIdx;
}

function _bejson_fields_fingerprint(doc) {
    let fp = String(doc.Format_Version || "") + "\u0001";
    const fields = doc.Fields || [];
    for (let i = 0; i < fields.length; i++) {
        fp += fields[i].name + "\u0000" + (fields[i].field_uuid === undefined ? "" : fields[i].field_uuid) + "\u0001";
    }
    return fp;
}

function _bejson_build_field_cache(doc) {
    const by_name = {}, by_uuid = {}, by_name_row = {};
    (doc.Fields || []).forEach((f, i) => {
        by_name[f.name] = i;
        by_name_row[f.name] = _bejson_abs_col(doc, i);
        if (f.field_uuid !== undefined) by_uuid[f.field_uuid] = i;
    });
    return { by_name, by_uuid, by_name_row, fingerprint: _bejson_fields_fingerprint(doc) };
}

/**
 * 105-shaped field map cache {by_name, by_uuid, by_name_row, fingerprint}.
 * Self-maintaining: built on first touch, rebuilt whenever Fields change.
 */
function bejson_core_get_field_cache(doc) {
    if (!doc || !Array.isArray(doc.Fields)) return null;
    const cached = doc._bejson_field_map;
    if (!cached || !cached.by_name || cached.fingerprint !== _bejson_fields_fingerprint(doc)) {
        const built = _bejson_build_field_cache(doc);
        _bejson_hide(doc, "_bejson_field_map", built);
        return built;
    }
    return cached;
}

/**
 * Returns name -> index. 105-series: name -> ROW position (record_uuid /
 * discriminator offset already applied) so row[map[name]] is correct on
 * every Format_Version. 104-series: plain Fields index, validated against
 * the live layout on every read.
 */
const _BEJSON_OWNED_MAPS = new WeakMap();
function _bejson_core_field_map_is_fresh(cached, fields) {
    if (!cached || typeof cached !== "object" || !Array.isArray(fields)) return false;
    const count = fields.length;
    if (_BEJSON_OWNED_MAPS.get(cached) !== count) return false;
    if (count === 0) return true;
    const last = count - 1, mid = count >> 1;
    return cached[fields[0].name] === 0 && cached[fields[last].name] === last && cached[fields[mid].name] === mid;
}

function bejson_core_get_field_map(doc) {
    if (!doc || !Array.isArray(doc.Fields)) return {};
    if (_105_SERIES.includes(doc.Format_Version)) {
        return bejson_core_get_field_cache(doc).by_name_row;
    }
    if (!doc.Fields.length) return {};

    if (_bejson_core_field_map_is_fresh(doc._bejson_field_map, doc.Fields)) {
        return doc._bejson_field_map;
    }

    const fieldMap = {};
    for (let i = 0; i < doc.Fields.length; i++) {
        fieldMap[doc.Fields[i].name] = i;
    }
    _BEJSON_OWNED_MAPS.set(fieldMap, Object.keys(fieldMap).length);
    _bejson_hide(doc, "_bejson_field_map", fieldMap);
    return fieldMap;
}

/**
 * Returns the positional index of a field name using the cache.
 * Returns -1 on miss (consistent with JS/PY; TS core throws -- see audit FM4).
 */
function bejson_core_get_field_index(doc, fieldName) {
    const fieldMap = bejson_core_get_field_map(doc);
    const idx = Object.prototype.hasOwnProperty.call(fieldMap, fieldName) ? fieldMap[fieldName] : undefined;
    return (idx !== undefined) ? idx : -1;
}

/**
 * Warms a freshly parsed/loaded document: 105-series docs get their cache
 * built immediately; 104-series docs are returned untouched (lazy, per the
 * standing contract). Returns the same doc so it chains: warm(JSON.parse(t)).
 */
function bejson_core_warm(doc) {
    if (doc && _105_SERIES.includes(doc.Format_Version) && Array.isArray(doc.Fields)) {
        bejson_core_get_field_cache(doc);
    }
    return doc;
}

/**
 * Clears the shared 104-series map table. NOT required for correctness any
 * more (every lookup self-validates); kept for API parity and memory control.
 */
function bejson_core_clear_field_map_cache() {
    _FIELD_MAP_CACHE.clear();
}

/**
 * Serializes a BEJSON document to a string, stripping internal metadata keys
 * (those starting with '_') to prevent leakage into persisted files.
 * @param {Object} doc - The BEJSON document to serialize.
 * @param {number} indent - Indentation spaces.
 * @returns {string} The JSON string.
 */
function bejson_core_serialize(doc, indent = 2) {
    if (!doc) return "";
    const cleanDoc = {};
    Object.keys(doc).forEach(key => {
        if (!key.startsWith("_")) cleanDoc[key] = doc[key];
    });
    return JSON.stringify(cleanDoc, null, indent);
}


// ---------------------------------------------------------------------------
// 105-SERIES UUID-ADDRESSED CRUD (Phase 6 prerequisite, JS port of PY core)
// Added 2026-10-03. Mirrors PY bejson_core_find_row_by_uuid / resolve_field_index
// / write_cell / add_record_105 / delete_record exactly: same offsets (105 -> 1,
// 105db -> Fields[0] at col 0, Fields[i>=1] at i+1), same error codes (80-82), same "never address by row offset"
// contract. 104-series documents raise E_FORMAT_UNSUPPORTED (81).
// ---------------------------------------------------------------------------
const _E_FIELD_INTEGRITY_MISMATCH = (BEJSON_ERRORS.E_FIELD_INTEGRITY_MISMATCH !== undefined) ? BEJSON_ERRORS.E_FIELD_INTEGRITY_MISMATCH : 80;
const _E_FORMAT_UNSUPPORTED       = (BEJSON_ERRORS.E_FORMAT_UNSUPPORTED !== undefined) ? BEJSON_ERRORS.E_FORMAT_UNSUPPORTED : 81;
const _E_RECORD_NOT_FOUND         = (BEJSON_ERRORS.E_RECORD_NOT_FOUND !== undefined) ? BEJSON_ERRORS.E_RECORD_NOT_FOUND : 82;

function _bejson_new_uuid() {
    if (crypto && typeof crypto.randomUUID === 'function') return crypto.randomUUID();
    const b = new Uint8Array(16);
    if (crypto && typeof crypto.getRandomValues === 'function') crypto.getRandomValues(b);
    else for (let i = 0; i < 16; i++) b[i] = Math.floor(Math.random() * 256);
    b[6] = (b[6] & 0x0f) | 0x40; b[8] = (b[8] & 0x3f) | 0x80;
    const h = Array.from(b, x => x.toString(16).padStart(2, '0')).join('');
    return `${h.slice(0,8)}-${h.slice(8,12)}-${h.slice(12,16)}-${h.slice(16,20)}-${h.slice(20)}`;
}

function _bejson_require_105(doc, fn) {
    if (!doc || !_105_SERIES.includes(doc.Format_Version)) {
        throw new BEJSONCoreError(
            `E_FORMAT_UNSUPPORTED: ${fn} requires a 105-series document, got ${JSON.stringify(doc && doc.Format_Version)}.`,
            _E_FORMAT_UNSUPPORTED);
    }
}

/** Row index of record_uuid, or null. */
function bejson_core_find_row_by_uuid(doc, recordUuid) {
    const uuidCol = doc.Format_Version === "105db" ? 1 : 0;
    const vals = doc.Values || [];
    for (let i = 0; i < vals.length; i++) {
        if (vals[i].length > uuidCol && vals[i][uuidCol] === recordUuid) return i;
    }
    return null;
}

/**
 * Absolute row column for a field. target: name string, field_uuid string, or
 * {name, field_uuid} (both must agree).
 */
function bejson_core_resolve_field_index(doc, target) {
    _bejson_require_105(doc, "resolve_field_index");
    const fm = bejson_core_get_field_cache(doc);
    const has = (o, k) => k !== undefined && k !== null && Object.prototype.hasOwnProperty.call(o, k);
    if (target && typeof target === 'object') {
        const byName = has(fm.by_name, target.name) ? fm.by_name[target.name] : undefined;
        const byUuid = has(fm.by_uuid, target.field_uuid) ? fm.by_uuid[target.field_uuid] : undefined;
        if (byName === undefined || byUuid === undefined || byName !== byUuid) {
            throw new BEJSONCoreError(
                `E_FIELD_INTEGRITY_MISMATCH: name=${JSON.stringify(target.name)} resolves to ${byName}, field_uuid=${JSON.stringify(target.field_uuid)} resolves to ${byUuid}`,
                _E_FIELD_INTEGRITY_MISMATCH);
        }
        return _bejson_abs_col(doc, byName);
    }
    if (has(fm.by_uuid, target)) return _bejson_abs_col(doc, fm.by_uuid[target]);
    if (has(fm.by_name, target)) return _bejson_abs_col(doc, fm.by_name[target]);
    throw new BEJSONCoreError(`E_FIELD_INTEGRITY_MISMATCH: unresolvable target ${JSON.stringify(target)}`, _E_FIELD_INTEGRITY_MISMATCH);
}

function _getTypeProblem(val, type) {
    try {
        const V = (typeof require !== 'undefined') ? require('./lib_bejson_Core_bejson_validator.js') : window.BEJSON_VALIDATOR;
        if (V && V._bejson_validator_type_problem) {
            return V._bejson_validator_type_problem(val, type);
        }
    } catch (_) {}
    if (val === null || val === undefined) return null;
    if (type === 'string') return typeof val === 'string' ? null : 'expected string';
    if (type === 'integer') return (typeof val === 'number' && Number.isInteger(val) && typeof val !== 'boolean') ? null : 'expected integer';
    if (type === 'number') {
        if (typeof val === 'boolean') return 'expected number, got bool';
        return typeof val === 'number' ? null : 'expected number';
    }
    if (type === 'boolean') return typeof val === 'boolean' ? null : 'expected boolean';
    if (type === 'array') return Array.isArray(val) ? null : 'expected array';
    if (type === 'object') return (typeof val === 'object' && !Array.isArray(val)) ? null : 'expected object';
    return null;
}

function _bejson_core_check_value_type(field, value, where) {
    const problem = _getTypeProblem(value, field && field.type);
    if (problem) {
        throw new BEJSONCoreError(
            `E_TYPE_MISMATCH: ${where} (${field && field.name}): ${problem}`,
            BEJSON_ERRORS.E_TYPE_MISMATCH !== undefined ? BEJSON_ERRORS.E_TYPE_MISMATCH : 8
        );
    }
}

/** Write one cell addressed by (record_uuid, field_uuid). Returns {row, col, healed}. */
function bejson_core_write_cell(doc, recordUuid, fieldUuid, newValue, opts = {}) {
    _bejson_require_105(doc, "write_cell");
    const fm = bejson_core_get_field_cache(doc);
    if (!Object.prototype.hasOwnProperty.call(fm.by_uuid, fieldUuid)) {
        throw new BEJSONCoreError(`E_FIELD_INTEGRITY_MISMATCH: unknown field_uuid ${JSON.stringify(fieldUuid)}`, _E_FIELD_INTEGRITY_MISMATCH);
    }
    const row = bejson_core_find_row_by_uuid(doc, recordUuid);
    if (row === null) {
        throw new BEJSONCoreError(`E_RECORD_NOT_FOUND: unknown record_uuid ${JSON.stringify(recordUuid)}`, _E_RECORD_NOT_FOUND);
    }
    const col = fm.by_uuid[fieldUuid];
    const fieldDef = (doc.Fields || [])[col];
    _bejson_core_check_value_type(fieldDef, newValue, `write_cell record ${recordUuid}`);
    const absCol = _bejson_abs_col(doc, col);
    const healed = (opts.expected_row !== undefined && opts.expected_row !== row) ||
                   (opts.expected_col !== undefined && opts.expected_col !== absCol);
    doc.Values[row][absCol] = newValue;
    return { row, col: absCol, healed };
}

/**
 * 105-series add. values excludes the record_uuid; for 105db values[0] is the
 * caller-supplied discriminator. Returns the new record_uuid.
 */
function bejson_core_add_record_105(doc, values) {
    _bejson_require_105(doc, "add_record_105");
    const fields = doc.Fields || [];
    if (!Array.isArray(values) || values.length !== fields.length) {
        throw new BEJSONCoreError(
            `E_RECORD_LENGTH_MISMATCH: add_record_105 expects ${fields.length} values (one per field, WITHOUT record_uuid), got ${Array.isArray(values) ? values.length : typeof values}`,
            BEJSON_ERRORS.E_RECORD_LENGTH_MISMATCH !== undefined ? BEJSON_ERRORS.E_RECORD_LENGTH_MISMATCH : 9
        );
    }
    for (let j = 0; j < fields.length; j++) {
        _bejson_core_check_value_type(fields[j], values[j], "add_record_105 value");
    }
    if (doc.Format_Version === "105db" && values && !((doc.Records_Type || []).includes(values[0]))) {
        throw new BEJSONCoreError(
            `E_FIELD_INTEGRITY_MISMATCH: Record_Type_Parent '${values[0]}' not in Records_Type`,
            _E_FIELD_INTEGRITY_MISMATCH
        );
    }
    const recordUuid = _bejson_new_uuid();
    const row = doc.Format_Version === "105db"
        ? [values[0], recordUuid, ...values.slice(1)]
        : [recordUuid, ...values];
    if (!Array.isArray(doc.Values)) doc.Values = [];
    doc.Values.push(row);
    return recordUuid;
}

/** 104-series add_record: rejects 105-series documents with E_FORMAT_UNSUPPORTED (81). */
function bejson_core_add_record(doc, record) {
    if (doc && _105_SERIES.includes(doc.Format_Version)) {
        throw new BEJSONCoreError(
            `E_FORMAT_UNSUPPORTED: add_record is 104-series only, got '${doc.Format_Version}'. Use bejson_core_add_record_105().`,
            _E_FORMAT_UNSUPPORTED
        );
    }
    if (!Array.isArray(record) || !Array.isArray(doc.Fields) || record.length !== doc.Fields.length) {
        return false;
    }
    if (!Array.isArray(doc.Values)) doc.Values = [];
    doc.Values.push(record);
    return true;
}

/** Field adder for 104 and 105 series. */
function bejson_core_add_field(doc, name, fieldType) {
    if (!doc || !_105_SERIES.includes(doc.Format_Version)) {
        if (!doc.Fields) doc.Fields = [];
        doc.Fields.push({ name, type: fieldType });
        for (const row of (doc.Values || [])) row.push(null);
        return null;
    }
    const validTypes = ['string', 'integer', 'number', 'boolean', 'array', 'object'];
    if (!validTypes.includes(fieldType)) {
        throw new BEJSONCoreError(
            `E_FIELD_INTEGRITY_MISMATCH: field_type must be one of ${JSON.stringify(validTypes)}, got '${fieldType}'`,
            _E_FIELD_INTEGRITY_MISMATCH
        );
    }
    const existingNames = new Set((doc.Fields || []).map(f => f.name));
    if (existingNames.has(name)) {
        throw new BEJSONCoreError(
            `E_DUPLICATE_FIELD_NAME: '${name}' already exists`,
            BEJSON_ERRORS.E_DUPLICATE_FIELD_NAME !== undefined ? BEJSON_ERRORS.E_DUPLICATE_FIELD_NAME : 84
        );
    }
    const newUuid = _bejson_new_uuid();
    if (!doc.Fields) doc.Fields = [];
    doc.Fields.push({ name, type: fieldType, field_uuid: newUuid });
    for (const row of (doc.Values || [])) row.push(null);
    return newUuid;
}

/** 105 integrity verification. */
function bejson_core_verify_105_integrity(doc) {
    if (!doc || !_105_SERIES.includes(doc.Format_Version)) {
        return { ok: false, reason: "E_FORMAT_UNSUPPORTED", errors: [] };
    }
    const V = (typeof require !== 'undefined') ? require('./lib_bejson_Core_bejson_validator.js') : window.BEJSON_VALIDATOR;
    const res = V.validate_bejson ? V.validate_bejson(doc) : V.bejson_validator_validate_object(doc);
    const fm = bejson_core_get_field_cache(doc);
    return {
        ok: res.valid,
        field_count: (doc.Fields || []).length,
        record_count: (doc.Values || []).length,
        field_map_content_hash: fm ? fm.content_hash : "",
        errors: res.errors
    };
}

/** 105-series delete by record_uuid (never by row offset). */
function bejson_core_delete_record(doc, recordUuid) {
    _bejson_require_105(doc, "delete_record");
    const row = bejson_core_find_row_by_uuid(doc, recordUuid);
    if (row === null) {
        throw new BEJSONCoreError(`E_RECORD_NOT_FOUND: unknown record_uuid ${JSON.stringify(recordUuid)}`, _E_RECORD_NOT_FOUND);
    }
    doc.Values.splice(row, 1);
}

const CoreExports = {
    RELEASE_VERSION,
    BEJSONCoreError,
    BEJSONEngine,
    Crypto: CryptoUtils,
    clearKeyCache,
    bejson_core_is_valid,
    bejson_core_get_version,
    bejson_core_get_stats,
    bejson_core_get_field_map,
    bejson_core_get_field_cache,
    bejson_core_warm,
    bejson_core_get_field_index,
    bejson_core_clear_field_map_cache,
    bejson_core_serialize,
    // 104 CRUD
    bejson_core_add_record,
    // 105-series uuid-addressed CRUD
    bejson_core_find_row_by_uuid,
    bejson_core_resolve_field_index,
    bejson_core_write_cell,
    bejson_core_add_record_105,
    bejson_core_add_field,
    bejson_core_delete_record,
    bejson_core_verify_105_integrity,
    // Error codes
    E_CORE_INVALID_VERSION, E_CORE_INVALID_OPERATION, E_CORE_INDEX_OUT_OF_BOUNDS,
    E_CORE_FIELD_NOT_FOUND, E_CORE_TYPE_CONVERSION_FAILED, E_CORE_BACKUP_FAILED,
    E_CORE_WRITE_FAILED, E_CORE_QUERY_FAILED, E_CORE_ENCRYPTION_FAILED, E_CORE_DECRYPTION_FAILED,
    E_FIELD_INTEGRITY_MISMATCH: _E_FIELD_INTEGRITY_MISMATCH,
    E_FORMAT_UNSUPPORTED: _E_FORMAT_UNSUPPORTED,
    E_RECORD_NOT_FOUND: _E_RECORD_NOT_FOUND,
    E_DUPLICATE_FIELD_NAME: (BEJSON_ERRORS.E_DUPLICATE_FIELD_NAME !== undefined ? BEJSON_ERRORS.E_DUPLICATE_FIELD_NAME : 84),
    E_RECORD_LENGTH_MISMATCH: (BEJSON_ERRORS.E_RECORD_LENGTH_MISMATCH !== undefined ? BEJSON_ERRORS.E_RECORD_LENGTH_MISMATCH : 9),
    E_TYPE_MISMATCH: (BEJSON_ERRORS.E_TYPE_MISMATCH !== undefined ? BEJSON_ERRORS.E_TYPE_MISMATCH : 8),
};

// UMD-like export
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CoreExports;
}
if (typeof window !== 'undefined') {
    window.BEJSON = window.BEJSON || {};
    Object.assign(window.BEJSON, CoreExports);
}
