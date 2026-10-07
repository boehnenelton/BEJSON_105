/**
 * Library:        lib_bejson_Core_bejson_core.js
 * Family:         Core
 * Description:    Low-level primitive operations for BEJSON document manipulation.
 * BEJSON:         BEJSON stands for BOEHNEN ELTON JSON. Authoritative definition;
 *                 do not restate or reinterpret this acronym elsewhere.
 * MFDB:           MFDB stands for Multi File Database. Authoritative definition;
 *                 do not restate or reinterpret this acronym elsewhere.
 * Version:        2.2.1
 * Date:           2026-10-06
 * Author:         Elton Boehnen
 * Contact:        eltonboehnen@gmail.com | boehnenelton2024.pages.dev | github.com/boehnenelton
 * Format_Creator: Elton Boehnen
 * RELATIONAL_ID:  1ebf2e4c-0d38-408d-8645-36bd4f320a6e
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

async function _getOrDeriveKey(password, salt, providedKey = null) {
    if (providedKey) return providedKey;
    const saltB64 = CryptoUtils.ab2base64(salt);
    const hitIdx = _keyCache.findIndex((e) => e.password === password && e.salt === saltB64);
    if (hitIdx !== -1) {
        const [hit] = _keyCache.splice(hitIdx, 1);
        _keyCache.push(hit); // move to most-recently-used end
        return hit.key;
    }
    const key = await CryptoUtils.deriveKey(password, salt);
    if (_keyCache.length >= _KEY_CACHE_MAX_SLOTS) {
        _keyCache.shift(); // evict least-recently-used
    }
    _keyCache.push({ password, salt: saltB64, key });
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

function _bejson_row_offset(doc) {
    const v = doc.Format_Version;
    return v === "105db" ? 2 : (_105_SERIES.includes(v) ? 1 : 0);
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
    const offset = _bejson_row_offset(doc);
    (doc.Fields || []).forEach((f, i) => {
        by_name[f.name] = i;
        by_name_row[f.name] = i + offset;
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
function bejson_core_get_field_map(doc) {
    if (!doc || !Array.isArray(doc.Fields)) return {};
    if (_105_SERIES.includes(doc.Format_Version)) {
        return bejson_core_get_field_cache(doc).by_name_row;
    }
    if (!doc.Fields.length) return {};

    const fp = _bejson_fields_fingerprint(doc);
    const cached = doc._bejson_field_map;
    if (cached && !cached.by_name && doc._bejson_field_map_fp === fp) return cached;

    let fieldMap = _FIELD_MAP_CACHE.get(fp);
    if (!fieldMap) {
        fieldMap = {};
        doc.Fields.forEach((f, i) => { fieldMap[f.name] = i; });
        _FIELD_MAP_CACHE.set(fp, fieldMap);
    }
    _bejson_hide(doc, "_bejson_field_map", fieldMap);
    _bejson_hide(doc, "_bejson_field_map_fp", fp);
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
// 105db -> 2), same error codes (80-82), same "never address by row offset"
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
    const offset = doc.Format_Version === "105db" ? 2 : 1;
    const has = (o, k) => k !== undefined && k !== null && Object.prototype.hasOwnProperty.call(o, k);
    if (target && typeof target === 'object') {
        const byName = has(fm.by_name, target.name) ? fm.by_name[target.name] : undefined;
        const byUuid = has(fm.by_uuid, target.field_uuid) ? fm.by_uuid[target.field_uuid] : undefined;
        if (byName === undefined || byUuid === undefined || byName !== byUuid) {
            throw new BEJSONCoreError(
                `E_FIELD_INTEGRITY_MISMATCH: name=${JSON.stringify(target.name)} resolves to ${byName}, field_uuid=${JSON.stringify(target.field_uuid)} resolves to ${byUuid}`,
                _E_FIELD_INTEGRITY_MISMATCH);
        }
        return byName + offset;
    }
    if (has(fm.by_uuid, target)) return fm.by_uuid[target] + offset;
    if (has(fm.by_name, target)) return fm.by_name[target] + offset;
    throw new BEJSONCoreError(`E_FIELD_INTEGRITY_MISMATCH: unresolvable target ${JSON.stringify(target)}`, _E_FIELD_INTEGRITY_MISMATCH);
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
    const absCol = fm.by_uuid[fieldUuid] + (doc.Format_Version === "105db" ? 2 : 1);
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
    const recordUuid = _bejson_new_uuid();
    const row = doc.Format_Version === "105db"
        ? [values[0], recordUuid, ...values.slice(1)]
        : [recordUuid, ...values];
    if (!Array.isArray(doc.Values)) doc.Values = [];
    doc.Values.push(row);
    return recordUuid;
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
    bejson_core_is_valid,
    bejson_core_get_version,
    bejson_core_get_stats,
    bejson_core_get_field_map,
    bejson_core_get_field_cache,
    bejson_core_warm,
    bejson_core_get_field_index,
    bejson_core_clear_field_map_cache,
    bejson_core_serialize,
    // 105-series uuid-addressed CRUD
    bejson_core_find_row_by_uuid,
    bejson_core_resolve_field_index,
    bejson_core_write_cell,
    bejson_core_add_record_105,
    bejson_core_delete_record,
    // Error codes
    E_CORE_INVALID_VERSION, E_CORE_INVALID_OPERATION, E_CORE_INDEX_OUT_OF_BOUNDS,
    E_CORE_FIELD_NOT_FOUND, E_CORE_TYPE_CONVERSION_FAILED, E_CORE_BACKUP_FAILED,
    E_CORE_WRITE_FAILED, E_CORE_QUERY_FAILED, E_CORE_ENCRYPTION_FAILED, E_CORE_DECRYPTION_FAILED,
    E_FIELD_INTEGRITY_MISMATCH: _E_FIELD_INTEGRITY_MISMATCH,
    E_FORMAT_UNSUPPORTED: _E_FORMAT_UNSUPPORTED,
    E_RECORD_NOT_FOUND: _E_RECORD_NOT_FOUND
};

// UMD-like export
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CoreExports;
}
if (typeof window !== 'undefined') {
    window.BEJSON = window.BEJSON || {};
    Object.assign(window.BEJSON, CoreExports);
}
