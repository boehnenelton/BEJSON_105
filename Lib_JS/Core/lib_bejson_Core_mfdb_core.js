/**
 * Library:        lib_bejson_Core_mfdb_core.js
 * Family:         Core
 * Description:    Multi-file database orchestrator managing manifests and entity synchronization.
 * Version:        2.4.1
 * Date:           2026-10-06
 * Author:         Elton Boehnen
 * Contact:        eltonboehnen@gmail.com | boehnenelton2024.pages.dev | github.com/boehnenelton
 * Format_Creator: Elton Boehnen
 * RELATIONAL_ID:  70f3fc35-5fca-460f-9b4d-ec36628286bf
 * Release_Version: 300
 *
 * CHANGE (2026-10-06): Consolidation re-merge -- the V6-PKG101 silent-catch
 * logging fix (5 sites: federation temp-cleanup, meta auto-trim, nested
 * schema-snapshot x2, schema-drift check) had been reverted/lost on the
 * forward V10-PKG102 branch; re-applied here on top of the current Phase 6
 * Referential Integrity content, no behavior change.
 *
 * FEATURE (2026-10-03): Phase 6 JS port -- 105-series Referential Integrity.
 * mfdb_core_enable/disable/is_ref_integrity_enabled (Ref_Integrity manifest
 * header), mfdb_core_check_fk_write, mfdb_core_check_entity_droppable,
 * mfdb_core_find_referencing_rows, and uuid-addressed CRUD entry points
 * mfdb_core_add/update/delete_entity_record_105 (restrict / cascade / null,
 * cycle-guarded). Semantics mirror PY 105 Phase 6. NOTE: unlike PY there is no
 * PID lock (JS has no ResilientPIDLock); writes are single-process synchronous.
 * Delete resolves dependents ON DISK as it walks, exactly as PY does; a restrict
 * violation raised mid-walk can follow earlier null/cascade resolutions of
 * sibling dependents (same behaviour as PY -- documented, not changed here).
 *
 * FIX (2026-10-03): Node.js load crash. `window.JSZip` was dereferenced
 * unconditionally at module top level, throwing ReferenceError in Node before
 * the require('jszip') fallback could run. Now guarded with typeof window and
 * a try/catch around require('jszip') (jszip stays optional outside archive use).
 *
 * FEATURE (2026-07-31): Meta-GUID debug entity system — full JS port of the
 * Python debug block. META_DEBUG_FIELDS, _mfdbMetaLog (direct writer, no
 * recursion), _mfdbMetaAutoTrim, _mfdbDebugSchemaSnapshot, enable/disable/
 * get_log/get_failed_ops/clear_log/debug_summary/detect_schema_drift.
 * Node.js only; silently no-ops in browser.
 */

'use strict';

// Field-map cache (self-maintaining) from Core; optional so this file still loads standalone.
let _bejsonCoreFM = null;
try { _bejsonCoreFM = (typeof require !== 'undefined') ? require('./lib_bejson_Core_bejson_core.js') : (window.BEJSON || null); } catch (e) { _bejsonCoreFM = null; }
const JSZip = ((typeof window !== 'undefined' && window.JSZip) ? window.JSZip : null) || (typeof require !== 'undefined' ? (() => { try { return require('jszip'); } catch (e) { return null; } })() : null);

// ---------------------------------------------------------------------------
// Setup environments (merged from engine dump — required by manifest/entity
// manipulation functions below, which depend on the validator's IO helpers
// and the shared MFDB error codes).
// ---------------------------------------------------------------------------

const MFDB_VALIDATOR = (typeof require !== 'undefined')
  ? require('./lib_bejson_Core_mfdb_validator.js')
  : (window.MFDB_VALIDATOR || {});

const BEJSON_ERRORS = (typeof require !== 'undefined')
  ? require('./lib_bejson_Core_bejson_errors.js')
  : (window.BEJSON_ERRORS || {});

const {
  E_MFDB_CORE_MANIFEST_NOT_FOUND,
  E_MFDB_CORE_ENTITY_NOT_FOUND,
  E_MFDB_CORE_WRITE_FAILED,
  E_MFDB_CORE_CREATE_FAILED,
  E_MFDB_CORE_INVALID_OPERATION,
  E_MFDB_CORE_INDEX_OUT_OF_BOUNDS,
  E_MFDB_CORE_JOIN_FAILED,
  E_MFDB_CORE_ARCHIVE_ERROR,
  E_MFDB_CORE_MOUNT_CONFLICT
} = BEJSON_ERRORS;

const {
  _loadJson,
  _rowsAsDicts,
  _resolveEntityPath,
  _fileExists
} = MFDB_VALIDATOR;

class MFDBCoreError extends Error {
  constructor(message, code) {
    super(message);
    this.name = 'MFDBCoreError';
    this.code = code;
  }
}

function _isNode() {
  return typeof process !== 'undefined' && process.versions && !!process.versions.node;
}

function _writeFile(filePath, content) {
  if (!_isNode()) {
    console.warn('Sync write not available in browser');
    return;
  }
  const fs = require('fs');
  const path = require('path');
  const dir = path.dirname(filePath);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(filePath, content, 'utf8');
}

function _writeBejson(filePath, doc) {
  _writeFile(filePath, JSON.stringify(doc, null, 2));
}

// ---------------------------------------------------------------------------
// Manifest API (Spec §15.3 and §15.10) — merged from engine dump.
// Complements MFDBArchive below: this section manipulates the unpacked
// manifest/entity files directly, while MFDBArchive handles zip packaging.
// ---------------------------------------------------------------------------

function mfdb_core_create_manifest(dbName, options = {}) {
  const mfdbVersion  = options.mfdbVersion  || '1.31';
  const description  = options.description  || '';
  const author       = options.author       || (typeof process !== 'undefined' ? process.env.USER : '');
  const createdAt    = options.createdAt    || new Date().toISOString();
  const networkRole  = options.networkRole  || 'Standalone';   // "Master" | "Slave" | "Standalone"

  const doc = {
    Format: 'BEJSON',
    Format_Version: '104a',
    Format_Creator: 'Elton Boehnen',
    MFDB_Version: mfdbVersion,
    Network_Role: networkRole,
    DB_Name: dbName,
    DB_Description: description,
    Author: author,
    Created_At: createdAt,
    Records_Type: ['mfdb'],
    Fields: [
      { name: 'entity_name',    type: 'string' },
      { name: 'file_path',      type: 'string' },
      { name: 'description',    type: 'string' },
      { name: 'record_count',   type: 'integer' },
      { name: 'schema_version', type: 'string' },
      { name: 'primary_key',    type: 'string' },
    ],
    Values: [],
  };

  if (options.extraHeaders) {
    Object.assign(doc, options.extraHeaders);
  }

  return doc;
}

function mfdb_core_register_entity(manifestPath, record) {
  if (!_fileExists(manifestPath)) {
    throw new MFDBCoreError(`Manifest not found: ${manifestPath}`, E_MFDB_CORE_MANIFEST_NOT_FOUND);
  }

  const doc     = _loadJson(manifestPath);
  const entries = _rowsAsDicts(doc);

  if (entries.some(e => e.entity_name === record.entity_name)) {
    throw new MFDBCoreError(`Entity '${record.entity_name}' already registered`, E_MFDB_CORE_JOIN_FAILED);
  }

  const names = doc.Fields.map(f => f.name);
  const row   = names.map(n => {
    if (record[n] !== undefined) return record[n];
    return null;
  });

  doc.Values.push(row);
  _writeBejson(manifestPath, doc);
  return true;
}

function mfdb_core_sync_count(manifestPath, entityName, overrideCount = null) {
  const doc     = _loadJson(manifestPath);
  const entries = _rowsAsDicts(doc);
  const idx     = entries.findIndex(e => e.entity_name === entityName);

  if (idx === -1) {
    throw new MFDBCoreError(`Entity '${entityName}' not found in manifest`, E_MFDB_CORE_ENTITY_NOT_FOUND);
  }

  let count = overrideCount;
  if (count === null) {
    const ePath = _resolveEntityPath(manifestPath, entries[idx].file_path);
    if (_fileExists(ePath)) {
      const edoc = _loadJson(ePath);
      count = (edoc.Values || []).length;
    }
  }

  if (count !== null) {
    const cIdx  = _bejsonCoreFM ? _bejsonCoreFM.bejson_core_get_field_index(doc, 'record_count')
                                : doc.Fields.map(f => f.name).indexOf('record_count');
    if (cIdx !== -1) {
      doc.Values[idx][cIdx] = count;
      _writeBejson(manifestPath, doc);
    }
  }
  return true;
}

function mfdb_core_sync_all_counts(manifestPath) {
  const doc     = _loadJson(manifestPath);
  const entries = _rowsAsDicts(doc);
  for (const entry of entries) {
    mfdb_core_sync_count(manifestPath, entry.entity_name);
  }
  return true;
}

// ---------------------------------------------------------------------------
// Entity Creation (Spec §15.4) — merged from engine dump.
// ---------------------------------------------------------------------------

function mfdb_core_init_entity_file(manifestPath, entityName, fields, filePathRel) {
  if (!_isNode()) return;
  const path = require('path');
  const manifestDir = path.dirname(path.resolve(manifestPath));
  const entityPath  = path.resolve(manifestDir, filePathRel);
  const relBack     = path.relative(path.dirname(entityPath), manifestPath);

  const doc = {
    Format: 'BEJSON',
    Format_Version: '104',
    Format_Creator: 'Elton Boehnen',
    Parent_Hierarchy: relBack,
    Records_Type: [entityName],
    Fields: fields,
    Values: [],
  };

  _writeBejson(entityPath, doc);

  // Auto-register
  mfdb_core_register_entity(manifestPath, {
    entity_name: entityName,
    file_path: filePathRel,
    record_count: 0,
  });

  return doc;
}

/**
 * MFDBArchive Class - Vanilla Implementation
 * Leverages the Browser's File System Access API and JSZip.
 */
class MFDBArchive {
    /**
     * mount (Browser version)
     * @param {File|Blob} zipFile - The .mfdb.zip file.
     * @param {FileSystemDirectoryHandle} dirHandle - The target directory handle.
     */
    static async mount(zipFile, dirHandle) {
        if (!JSZip) throw new Error("JSZip library not found. Required for archive operations.");
        
        const zip = await JSZip.loadAsync(zipFile);
        
        // Secure ZIP validation.
        const utility = (typeof window !== 'undefined' && window.BEJSON_UTILITY) 
            ? window.BEJSON_UTILITY 
            : (typeof require !== 'undefined' ? require('./lib_bejson_Core_bejson_secure_zip.js') : null);
        
        if (utility && utility.secure_zip_validate) {
            // Note: Virtual mount doesn't use real paths, but we validate for consistency.
            // dirHandle.name is used as the 'boundary'.
            utility.secure_zip_validate({ getEntries: () => Object.keys(zip.files).map(k => ({ entryName: k })) }, dirHandle.name || "mount_root");
        }
        
        // Check for manifest
        if (!zip.file("104a.mfdb.bejson")) {
            throw new Error("Invalid MFDB Archive: 104a.mfdb.bejson missing at root.");
        }

        // Virtual "Extraction" to Directory Handle
        for (const [path, file] of Object.entries(zip.files)) {
            if (file.dir) continue; // Skip directories (created as needed by getFileHandle)
            
            const pathParts = path.split('/');
            const fileName = pathParts.pop();
            let currentDir = dirHandle;

            // Navigate/Create subdirectories
            for (const part of pathParts) {
                if (part === "") continue;
                currentDir = await currentDir.getDirectoryHandle(part, { create: true });
            }

            const data = await file.async("uint8array");
            const fileHandle = await currentDir.getFileHandle(fileName, { create: true });
            const writable = await fileHandle.createWritable();
            await writable.write(data);
            await writable.close();
        }

        // Create session lock file
        const lockHandle = await dirHandle.getFileHandle('.mfdb_lock', { create: true });
        const lockWritable = await lockHandle.createWritable();
        const lockData = {
            mounted_at: new Date().toISOString(),
            original_name: zipFile.name || "archive.mfdb.zip"
        };
        await lockWritable.write(JSON.stringify(lockData));
        await lockWritable.close();

        return "Mounted successfully to FileSystemHandle";
    }

    /**
     * commit (Browser version)
     * Repacks the directory handle back into a JSZip Blob.
     */
    static async commit(dirHandle) {
        if (!JSZip) throw new Error("JSZip library not found.");
        
        const zip = new JSZip();
        
        async function readDir(handle, currentPath = "") {
            for await (const entry of handle.values()) {
                if (entry.name === '.mfdb_lock') continue;
                
                if (entry.kind === 'file') {
                    const file = await entry.getFile();
                    const data = await file.arrayBuffer();
                    zip.file(currentPath + entry.name, data);
                } else if (entry.kind === 'directory') {
                    await readDir(entry, currentPath + entry.name + "/");
                }
            }
        }

        await readDir(dirHandle);
        return await zip.generateAsync({ type: "blob", compression: "DEFLATE" });
    }
}

// ── Federated Master / Slave node system ───────────────────────────────────────
// Network_Role is now emitted on mfdb_core_create_manifest. This block wires
// the full runtime federation protocol (Node.js only for push/poll/distill;
// CONNECTED_SLAVE_SCHEMA and the entity creator are environment-agnostic).

const CONNECTED_SLAVE_SCHEMA = [
  { name: "slave_id",           type: "string"  },
  { name: "label",              type: "string"  },
  { name: "url",                type: "string"  },
  { name: "role",               type: "string"  },
  { name: "status",             type: "string"  },
  { name: "supported_entities", type: "array"   },
];

function mfdb_core_create_connected_slave_entity(manifestPath) {
  const doc  = _loadJson(manifestPath);
  const role = doc.Network_Role || "";
  if (role !== "Master") {
    throw new MFDBCoreError(
      `ConnectedSlave may only be created on a Master node (Network_Role='Master'). Got: '${role}'`,
      E_MFDB_CORE_INVALID_OPERATION
    );
  }
  return mfdb_core_init_entity_file(
    manifestPath, "ConnectedSlave", CONNECTED_SLAVE_SCHEMA,
    { description: "Registry of Slave nodes connected to this Master.", primary_key: "slave_id" }
  );
}

// Node.js only — federation I/O requires fs
function mfdb_federation_push_config(configDoc, slaveTargetPath) {
  if (typeof require === 'undefined') {
    throw new Error("mfdb_federation_push_config requires Node.js (fs not available in browser).");
  }
  const _fs   = require("fs");
  const _path = require("path");
  const dest    = _path.resolve(slaveTargetPath);
  const destDir = _path.dirname(dest);
  _fs.mkdirSync(destDir, { recursive: true });
  const tempPath = dest + ".tmp." + Date.now();
  try {
    _fs.writeFileSync(tempPath, JSON.stringify(configDoc, null, 2), "utf8");
    _fs.renameSync(tempPath, dest);
    return true;
  } catch (e) {
    if (_fs.existsSync(tempPath)) try { _fs.unlinkSync(tempPath); } catch (_e) { console.debug(`[MFDB_FEDERATION] Could not remove leftover temp file ${tempPath}: ${_e.message}`); }
    console.error(`[MFDB_FEDERATION] push_config failed: ${e.message}`);
    return false;
  }
}

function mfdb_federation_poll_dropzone(
  dropzoneDir, callback,
  { pollInterval = 2000, timeout = 60000 } = {}
) {
  if (typeof require === 'undefined') {
    throw new Error("mfdb_federation_poll_dropzone requires Node.js.");
  }
  const _fs   = require("fs");
  const _path = require("path");
  _fs.mkdirSync(dropzoneDir, { recursive: true });

  let processed = 0;
  const deadline = Date.now() + timeout;

  const tick = () => {
    if (Date.now() >= deadline) return;
    const files = _fs.readdirSync(dropzoneDir)
      .filter(f => f.endsWith(".bejson"))
      .sort()
      .map(f => _path.join(dropzoneDir, f));

    for (const fpath of files) {
      try {
        const doc = JSON.parse(_fs.readFileSync(fpath, "utf8"));
        callback(fpath, doc);
        _fs.unlinkSync(fpath);
        processed++;
      } catch (e) {
        console.warn(`[MFDB_FEDERATION] poll_dropzone skipped ${fpath}: ${e.message}`);
      }
    }
    setTimeout(tick, pollInterval);
  };

  tick();
  return () => processed;  // Returns a getter for processed count
}

function mfdb_federation_distill_logs(
  slaveManifestPath, entityName, masterPollDir,
  { maxRows = 100 } = {}
) {
  if (typeof require === 'undefined') {
    throw new Error("mfdb_federation_distill_logs requires Node.js.");
  }
  const _fs   = require("fs");
  const _path = require("path");

  const manifestDoc  = _loadJson(slaveManifestPath);
  const entries      = _rowsAsDicts(manifestDoc);
  const entityEntry  = entries.find(e => e.entity_name === entityName);
  if (!entityEntry) throw new MFDBCoreError(`Entity '${entityName}' not in manifest`, E_MFDB_CORE_ENTITY_NOT_FOUND);

  const entityPath  = _path.resolve(_path.dirname(slaveManifestPath), entityEntry.file_path);
  const entityDoc   = _loadJson(entityPath);
  const rows        = entityDoc.Values || [];

  if (rows.length <= maxRows) return true;

  const overflow = rows.slice(0, rows.length - maxRows);
  const kept     = rows.slice(rows.length - maxRows);

  _fs.mkdirSync(masterPollDir, { recursive: true });
  const ts   = new Date().toISOString().replace(/[:.]/g, "").replace("T", "T").slice(0, 16) + "Z";
  const dest = _path.join(masterPollDir, `distilled_${entityName}_${ts}.bejson`);

  const summaryDoc = {
    Format: "BEJSON", Format_Version: "104a", Format_Creator: "Elton Boehnen",
    Distill_Source: entityName,
    Distill_Timestamp: new Date().toISOString(),
    Records_Type: ["DistilledLog"],
    Fields: entityDoc.Fields || [],
    Values: overflow,
  };

  if (!mfdb_federation_push_config(summaryDoc, dest)) return false;

  entityDoc.Values = kept;
  _atomicWrite(entityPath, entityDoc);

  // Update record count in manifest
  const fields = manifestDoc.Fields || [];
  const fm     = {};
  fields.forEach((f, i) => { fm[f.name] = i; });
  for (const row of (manifestDoc.Values || [])) {
    if (row[fm["entity_name"]] === entityName && fm["record_count"] !== undefined) {
      row[fm["record_count"]] = kept.length;
      break;
    }
  }
  _atomicWrite(slaveManifestPath, manifestDoc);
  return true;
}

// ── Meta-GUID Debug Entity System ─────────────────────────────────────────────
// Node.js only — direct file I/O required. All functions silently no-op in
// browser environments. _mfdbMetaLog bypasses normal write functions to prevent
// recursion; it acquires its own lock directly on the meta entity file.

const META_DEBUG_FIELDS = [
  { name: "timestamp",     type: "string"  },
  { name: "operation",     type: "string"  },
  { name: "target_entity", type: "string"  },
  { name: "field_name",    type: "string"  },
  { name: "field_exists",  type: "boolean" },
  { name: "row_index",     type: "integer" },
  { name: "success",       type: "boolean" },
  { name: "duration_ms",   type: "integer" },
  { name: "pid",           type: "integer" },
  { name: "notes",         type: "string"  },
];

function _mfdbDebugIsEnabled(manifestPath) {
  try {
    const doc = _loadJson(manifestPath);
    return String(doc.Debug_Mode || "false").toLowerCase() === "true";
  } catch (_) { return false; }
}

function _mfdbDebugReadsEnabled(manifestPath) {
  try {
    const doc = _loadJson(manifestPath);
    return String(doc.Debug_Reads || "false").toLowerCase() === "true";
  } catch (_) { return false; }
}

function _mfdbDebugGetMetaEntityName(manifestPath) {
  try {
    const doc = _loadJson(manifestPath);
    return doc.Debug_Meta_Entity || null;
  } catch (_) { return null; }
}

function _mfdbGetEntityPath(manifestPath, entityName) {
  const manifest  = _loadJson(manifestPath);
  const entries   = _rowsAsDicts(manifest);
  const entry     = entries.find(e => e.entity_name === entityName);
  if (!entry) throw new MFDBCoreError(`Entity '${entityName}' not found`, E_MFDB_CORE_ENTITY_NOT_FOUND);
  return require("path").resolve(require("path").dirname(manifestPath), entry.file_path);
}

function _mfdbMetaLog(manifestPath, operation, targetEntity, {
  fieldName = null, fieldExists = null, rowIndex = null,
  success = true, durationMs = 0, notes = "", readsOnly = false,
} = {}) {
  try {
    if (!_isNode()) return;
    if (!_mfdbDebugIsEnabled(manifestPath)) return;
    if (readsOnly && !_mfdbDebugReadsEnabled(manifestPath)) return;

    const metaName = _mfdbDebugGetMetaEntityName(manifestPath);
    if (!metaName) return;

    const metaPath = _mfdbGetEntityPath(manifestPath, metaName);
    const fs = require("fs");

    const row = [
      new Date().toISOString(), operation, targetEntity,
      fieldName, fieldExists, rowIndex, success, durationMs,
      process.pid, notes || "",
    ];

    const doc = _loadJson(metaPath);
    doc.Values = doc.Values || [];
    doc.Values.push(row);
    _atomicWrite(metaPath, doc);

    _mfdbMetaAutoTrim(manifestPath, metaName, metaPath);
  } catch (e) {
    // Non-fatal — debug logging must never break the calling operation
  }
}

function _mfdbMetaAutoTrim(manifestPath, metaName, metaPath) {
  try {
    const cap = parseInt(_loadJson(manifestPath).Debug_Row_Cap || "500", 10);
    const doc = _loadJson(metaPath);
    if ((doc.Values || []).length > cap) {
      doc.Values = doc.Values.slice(-cap);
      _atomicWrite(metaPath, doc);
    }
  } catch (_e) {
    console.debug(`[MFDB_DEBUG] Meta auto-trim failed for ${metaPath}: ${_e.message}`);
  }
}

function _mfdbDebugSchemaSnapshot(manifestPath, metaName) {
  try {
    const entries = _rowsAsDicts(_loadJson(manifestPath));
    for (const entry of entries) {
      const ename = entry.entity_name;
      if (!ename || ename === metaName) continue;
      try {
        const edoc   = _loadJson(_mfdbGetEntityPath(manifestPath, ename));
        const fields = (edoc.Fields || []).map(f => f.name).join(",");
        _mfdbMetaLog(manifestPath, "SCHEMA_SNAPSHOT", ename, {
          fieldName: fields, fieldExists: true, durationMs: 0,
          notes: `field_count=${(edoc.Fields || []).length}`,
        });
      } catch (_innerE) {
        console.debug(`[MFDB_DEBUG] schema snapshot failed for entity ${ename}: ${_innerE.message}`);
      }
    }
  } catch (_e) {
    console.debug(`[MFDB_DEBUG] schema snapshot failed: ${_e.message}`);
  }
}

// ── Public Debug API (JS) ──────────────────────────────────────────────────────

function mfdb_core_enable_debug(manifestPath, { rowCap = 500, debugReads = false } = {}) {
  const fs   = require("fs");
  const path = require("path");
  const crypto = require("crypto");

  const doc      = _loadJson(manifestPath);
  const metaName = doc.Debug_Meta_Entity || `meta-${crypto.randomUUID()}`;

  doc.Debug_Mode        = "true";
  doc.Debug_Meta_Entity = metaName;
  doc.Debug_Row_Cap     = String(rowCap);
  doc.Debug_Reads       = debugReads ? "true" : "false";
  _atomicWrite(manifestPath, doc);

  const metaFpRel = `data/${metaName}.bejson`;
  const metaAbs   = path.resolve(path.dirname(manifestPath), metaFpRel);

  if (!fs.existsSync(metaAbs)) {
    fs.mkdirSync(path.dirname(metaAbs), { recursive: true });
    const relToManifest = path.relative(path.dirname(metaAbs), manifestPath);
    const metaDoc = {
      Format: "BEJSON", Format_Version: "104", Format_Creator: "Elton Boehnen",
      Parent_Hierarchy: relToManifest,
      Records_Type: [metaName],
      Fields: META_DEBUG_FIELDS, Values: [],
    };
    _atomicWrite(metaAbs, metaDoc);

    const doc2    = _loadJson(manifestPath);
    const entries = _rowsAsDicts(doc2);
    if (!entries.find(e => e.entity_name === metaName)) {
      doc2.Values = doc2.Values || [];
      doc2.Values.push([metaName, metaFpRel, "Debug audit log (auto-generated)", 0, "1.0", null]);
      _atomicWrite(manifestPath, doc2);
    }
  }

  _mfdbDebugSchemaSnapshot(manifestPath, metaName);
  return metaName;
}

function mfdb_core_disable_debug(manifestPath) {
  const doc = _loadJson(manifestPath);
  doc.Debug_Mode = "false";
  _atomicWrite(manifestPath, doc);
}

function mfdb_core_get_debug_log(manifestPath) {
  const metaName = _mfdbDebugGetMetaEntityName(manifestPath);
  if (!metaName) return [];
  try {
    const doc = _loadJson(_mfdbGetEntityPath(manifestPath, metaName));
    const fm  = {};
    (doc.Fields || META_DEBUG_FIELDS).forEach((f, i) => { fm[f.name] = i; });
    return (doc.Values || []).map(row => {
      const out = {};
      for (const [k, i] of Object.entries(fm)) out[k] = row[i];
      return out;
    });
  } catch (_) { return []; }
}

function mfdb_core_get_failed_ops(manifestPath) {
  return mfdb_core_get_debug_log(manifestPath)
    .filter(r => r.success === false)
    .sort((a, b) => (a.timestamp > b.timestamp ? 1 : -1));
}

function mfdb_core_clear_debug_log(manifestPath) {
  const metaName = _mfdbDebugGetMetaEntityName(manifestPath);
  if (!metaName) return 0;
  try {
    const metaPath = _mfdbGetEntityPath(manifestPath, metaName);
    const doc      = _loadJson(metaPath);
    const deleted  = (doc.Values || []).length;
    doc.Values     = [];
    _atomicWrite(metaPath, doc);
    return deleted;
  } catch (_) { return 0; }
}

function mfdb_core_debug_summary(manifestPath) {
  if (!_mfdbDebugIsEnabled(manifestPath)) return {};
  const rows = mfdb_core_get_debug_log(manifestPath);
  if (!rows.length) return { total_ops: 0 };

  const writeOps  = new Set(["ADD", "REMOVE", "UPDATE", "UPDATE_BULK"]);
  const opsByType = {};
  for (const r of rows) opsByType[r.operation] = (opsByType[r.operation] || 0) + 1;

  return {
    total_ops:         rows.length,
    unique_entities:   [...new Set(rows.map(r => r.target_entity))].sort(),
    failed_ops:        rows.filter(r => r.success === false).length,
    schema_drift_hits: rows.filter(r => r.field_exists === false).length,
    top_3_slowest:     [...rows]
      .sort((a, b) => b.duration_ms - a.duration_ms)
      .slice(0, 3)
      .map(r => ({ op: r.operation, entity: r.target_entity, duration_ms: r.duration_ms })),
    reads_logged:  rows.filter(r => r.operation === "READ").length,
    writes_logged: rows.filter(r => writeOps.has(r.operation)).length,
    ops_by_type:   opsByType,
  };
}

function mfdb_core_detect_schema_drift(manifestPath) {
  if (!_mfdbDebugIsEnabled(manifestPath)) return {};
  const rows = mfdb_core_get_debug_log(manifestPath);
  const snapshots = {};
  for (const r of rows) {
    if (r.operation === "SCHEMA_SNAPSHOT" && r.field_name) {
      snapshots[r.target_entity] = new Set(r.field_name.split(",").filter(Boolean));
    }
  }
  if (!Object.keys(snapshots).length) return {};

  const report = {};
  for (const [ename, snapFields] of Object.entries(snapshots)) {
    try {
      const edoc       = _loadJson(_mfdbGetEntityPath(manifestPath, ename));
      const liveFields = new Set((edoc.Fields || []).map(f => f.name));
      const added      = [...liveFields].filter(f => !snapFields.has(f)).sort();
      const removed    = [...snapFields].filter(f => !liveFields.has(f)).sort();
      report[ename]    = { added_fields: added, removed_fields: removed, drifted: !!(added.length || removed.length) };
    } catch (_e) {
      console.debug(`[MFDB_DEBUG] Could not compute schema drift for entity ${ename}: ${_e.message}`);
    }
  }
  return report;
}


// ---------------------------------------------------------------------------
// Phase 6 (2026-10-03) -- 105-series MFDB Referential Integrity, JS port.
// Additive only: gated on Format_Version 105/105a/105db; 104-series CRUD above
// is untouched. Node.js only (reads/writes entity files).
// ---------------------------------------------------------------------------
const _MFDB_105_SERIES = ['105', '105a', '105db'];
const _E_FK = {
  UNRESOLVED:           (BEJSON_ERRORS.E_MFDB_FK_UNRESOLVED !== undefined) ? BEJSON_ERRORS.E_MFDB_FK_UNRESOLVED : 39,
  TARGET_UNKNOWN:       (BEJSON_ERRORS.E_MFDB_FK_TARGET_ENTITY_UNKNOWN !== undefined) ? BEJSON_ERRORS.E_MFDB_FK_TARGET_ENTITY_UNKNOWN : 43,
  RESTRICT_VIOLATION:   (BEJSON_ERRORS.E_MFDB_FK_RESTRICT_VIOLATION !== undefined) ? BEJSON_ERRORS.E_MFDB_FK_RESTRICT_VIOLATION : 44,
  CASCADE_CYCLE:        (BEJSON_ERRORS.E_MFDB_FK_CASCADE_CYCLE !== undefined) ? BEJSON_ERRORS.E_MFDB_FK_CASCADE_CYCLE : 45,
  ENTITY_STILL_REF:     (BEJSON_ERRORS.E_MFDB_FK_ENTITY_STILL_REFERENCED !== undefined) ? BEJSON_ERRORS.E_MFDB_FK_ENTITY_STILL_REFERENCED : 46,
  INVALID_ON_DELETE:    (BEJSON_ERRORS.E_MFDB_FK_INVALID_ON_DELETE !== undefined) ? BEJSON_ERRORS.E_MFDB_FK_INVALID_ON_DELETE : 47,
};

function _riCore() {
  const c = _bejsonCoreFM || ((typeof window !== 'undefined' && window.BEJSON) ? window.BEJSON : null);
  if (!c || !c.bejson_core_add_record_105) {
    throw new MFDBCoreError('Core 105 CRUD (bejson_core_add_record_105 etc.) is unavailable', E_MFDB_CORE_INVALID_OPERATION);
  }
  return c;
}

function mfdb_core_enable_ref_integrity(manifestPath) {
  const doc = _loadJson(manifestPath);
  doc.Ref_Integrity = 'true';
  _writeBejson(manifestPath, doc);
}

function mfdb_core_disable_ref_integrity(manifestPath) {
  const doc = _loadJson(manifestPath);
  doc.Ref_Integrity = 'false';
  _writeBejson(manifestPath, doc);
}

function mfdb_core_is_ref_integrity_enabled(manifestPath) {
  return _loadJson(manifestPath).Ref_Integrity === 'true';
}

function _riLoadEntityDoc(manifestPath, entityName) {
  const p = _mfdbGetEntityPath(manifestPath, entityName);
  if (!_fileExists(p)) {
    throw new MFDBCoreError(`Entity file not found for '${entityName}': ${p}`, E_MFDB_CORE_ENTITY_NOT_FOUND);
  }
  return _loadJson(p);
}

function _riFkFields(entityDoc) {
  return (entityDoc.Fields || []).filter(f => f.fk_target_entity);
}

function _riManifestEntries(manifestPath) {
  return _rowsAsDicts(_loadJson(manifestPath));
}

function _riValidateFkFieldDef(fkField, manifestPath, fromEntity) {
  const onDelete = fkField.fk_on_delete === undefined ? 'restrict' : fkField.fk_on_delete;
  if (!['restrict', 'cascade', 'null'].includes(onDelete)) {
    throw new MFDBCoreError(
      `${fromEntity}.${fkField.name}: fk_on_delete must be restrict/cascade/null, got ${JSON.stringify(onDelete)}`,
      _E_FK.INVALID_ON_DELETE);
  }
  if (!_riManifestEntries(manifestPath).some(e => e.entity_name === fkField.fk_target_entity)) {
    throw new MFDBCoreError(
      `${fromEntity}.${fkField.name}: fk_target_entity ${JSON.stringify(fkField.fk_target_entity)} is not registered in this manifest`,
      _E_FK.TARGET_UNKNOWN);
  }
}

/** Write-time exists-check for one FK value. null/undefined always passes. */
function mfdb_core_check_fk_write(manifestPath, fromEntity, fkField, value) {
  if (value === null || value === undefined) return;
  _riValidateFkFieldDef(fkField, manifestPath, fromEntity);
  const target = fkField.fk_target_entity;
  const targetDoc = _riLoadEntityDoc(manifestPath, target);
  if (!_MFDB_105_SERIES.includes(targetDoc.Format_Version)) {
    throw new MFDBCoreError(
      `${fromEntity}.${fkField.name}: fk_target_entity ${JSON.stringify(target)} is not a 105-series entity -- cannot resolve a record_uuid against it`,
      _E_FK.TARGET_UNKNOWN);
  }
  if (_riCore().bejson_core_find_row_by_uuid(targetDoc, value) === null) {
    throw new MFDBCoreError(`${fromEntity}.${fkField.name}: ${JSON.stringify(value)} does not exist in ${target}`, _E_FK.UNRESOLVED);
  }
}

function _riCheckFkWritesForRow(manifestPath, entityName, entityDoc, values) {
  const fkFields = _riFkFields(entityDoc);
  if (!fkFields.length) return;
  const fields = entityDoc.Fields || [];
  const fieldValues = entityDoc.Format_Version === '105db' ? values.slice(1) : values;
  for (const fk of fkFields) {
    const idx = fields.findIndex(f => f.name === fk.name);
    if (idx === -1 || idx >= fieldValues.length) continue;
    mfdb_core_check_fk_write(manifestPath, entityName, fk, fieldValues[idx]);
  }
}

/** [{entity, field, record_uuid}] of rows in OTHER 105-series entities pointing at (targetEntity, targetUuid). */
function mfdb_core_find_referencing_rows(manifestPath, targetEntity, targetUuid) {
  const core = _riCore();
  const out = [];
  for (const entry of _riManifestEntries(manifestPath)) {
    const name = entry.entity_name;
    if (name === targetEntity) continue;
    let doc;
    try { doc = _riLoadEntityDoc(manifestPath, name); } catch (e) { continue; }
    if (!_MFDB_105_SERIES.includes(doc.Format_Version)) continue;
    const fks = _riFkFields(doc).filter(f => f.fk_target_entity === targetEntity);
    if (!fks.length) continue;
    const uuidCol = doc.Format_Version === '105db' ? 1 : 0;
    for (const fk of fks) {
      let col;
      try { col = core.bejson_core_resolve_field_index(doc, fk.name); } catch (e) { continue; }
      for (const row of (doc.Values || [])) {
        if (row.length > col && row[col] === targetUuid) out.push({ entity: name, field: fk.name, record_uuid: row[uuidCol] });
      }
    }
  }
  return out;
}

/** Read-only: every [{entity, field, record_uuid}] reason entityName is NOT safely droppable. */
function mfdb_core_check_entity_droppable(manifestPath, entityName) {
  const out = [];
  for (const entry of _riManifestEntries(manifestPath)) {
    const other = entry.entity_name;
    if (other === entityName) continue;
    let doc;
    try { doc = _riLoadEntityDoc(manifestPath, other); } catch (e) { continue; }
    const fks = _riFkFields(doc).filter(f => f.fk_target_entity === entityName);
    if (!fks.length) continue;
    const uuidCol = doc.Format_Version === '105db' ? 1 : 0;
    for (const fk of fks) {
      for (const row of (doc.Values || [])) {
        if (row.length > uuidCol) out.push({ entity: other, field: fk.name, record_uuid: row[uuidCol] });
      }
    }
  }
  return out;
}

function _riDeleteRaw(manifestPath, entityName, recordUuid) {
  const p = _mfdbGetEntityPath(manifestPath, entityName);
  const doc = _loadJson(p);
  _riCore().bejson_core_delete_record(doc, recordUuid);
  _writeBejson(p, doc);
  mfdb_core_sync_count(manifestPath, entityName, doc.Values.length);
}

function _riWriteCell(manifestPath, entityName, recordUuid, fieldName, value) {
  const p = _mfdbGetEntityPath(manifestPath, entityName);
  const doc = _loadJson(p);
  const f = doc.Fields.find(x => x.name === fieldName);
  _riCore().bejson_core_write_cell(doc, recordUuid, f.field_uuid, value);
  _writeBejson(p, doc);
}

function _riCascadeDeleteDependents(manifestPath, entityName, recordUuid, visited) {
  const key = `${entityName}#${recordUuid}`;
  if (visited.has(key)) {
    throw new MFDBCoreError(`Cascade cycle detected: ${key} revisited during cascade delete`, _E_FK.CASCADE_CYCLE);
  }
  visited.add(key);
  for (const ref of mfdb_core_find_referencing_rows(manifestPath, entityName, recordUuid)) {
    const refDoc = _riLoadEntityDoc(manifestPath, ref.entity);
    const fk = refDoc.Fields.find(f => f.name === ref.field);
    const onDelete = fk.fk_on_delete === undefined ? 'restrict' : fk.fk_on_delete;
    if (onDelete === 'restrict') {
      throw new MFDBCoreError(
        `Cannot delete ${entityName}#${recordUuid}: restricted by ${ref.entity}.${ref.field} -> record ${ref.record_uuid}`,
        _E_FK.RESTRICT_VIOLATION);
    } else if (onDelete === 'null') {
      _riWriteCell(manifestPath, ref.entity, ref.record_uuid, ref.field, null);
    } else if (onDelete === 'cascade') {
      _riCascadeDeleteDependents(manifestPath, ref.entity, ref.record_uuid, visited);
      _riDeleteRaw(manifestPath, ref.entity, ref.record_uuid);
    } else {
      throw new MFDBCoreError(`${ref.entity}.${ref.field}: fk_on_delete must be restrict/cascade/null, got ${JSON.stringify(onDelete)}`, _E_FK.INVALID_ON_DELETE);
    }
  }
}

function _riRequire105(doc, entityName, hint) {
  if (!_MFDB_105_SERIES.includes(doc.Format_Version)) {
    throw new MFDBCoreError(
      `${entityName} is ${JSON.stringify(doc.Format_Version)}, not 105-series -- use ${hint} for 104-series entities`,
      E_MFDB_CORE_INVALID_OPERATION);
  }
}

/** 105 uuid-addressed add. Returns {record_uuid, doc}. FK values checked first when Ref_Integrity is on. */
function mfdb_core_add_entity_record_105(manifestPath, entityName, values, syncCount = true) {
  const p = _mfdbGetEntityPath(manifestPath, entityName);
  const doc = _loadJson(p);
  _riRequire105(doc, entityName, 'mfdb_core_add_entity_record()');
  if (mfdb_core_is_ref_integrity_enabled(manifestPath)) _riCheckFkWritesForRow(manifestPath, entityName, doc, values);
  const recordUuid = _riCore().bejson_core_add_record_105(doc, values);
  _writeBejson(p, doc);
  if (syncCount) mfdb_core_sync_count(manifestPath, entityName, doc.Values.length);
  return { record_uuid: recordUuid, doc };
}

/** 105 uuid-addressed single-field update. FK target checked first when Ref_Integrity is on. */
function mfdb_core_update_entity_record_105(manifestPath, entityName, recordUuid, fieldName, newValue) {
  const p = _mfdbGetEntityPath(manifestPath, entityName);
  const doc = _loadJson(p);
  _riRequire105(doc, entityName, 'mfdb_core_update_entity_record()');
  const fieldDef = (doc.Fields || []).find(f => f.name === fieldName);
  if (!fieldDef) throw new MFDBCoreError(`Field '${fieldName}' not in ${entityName}`, E_MFDB_CORE_INVALID_OPERATION);
  if (mfdb_core_is_ref_integrity_enabled(manifestPath) && fieldDef.fk_target_entity) {
    mfdb_core_check_fk_write(manifestPath, entityName, fieldDef, newValue);
  }
  _riCore().bejson_core_write_cell(doc, recordUuid, fieldDef.field_uuid, newValue);
  _writeBejson(p, doc);
  return doc;
}

/** 105 uuid-addressed delete. With Ref_Integrity on, dependents are resolved per fk_on_delete first. */
function mfdb_core_delete_entity_record_105(manifestPath, entityName, recordUuid, syncCount = true) {
  const p = _mfdbGetEntityPath(manifestPath, entityName);
  const check = _loadJson(p);
  _riRequire105(check, entityName, 'mfdb_core_remove_entity_record()');
  if (mfdb_core_is_ref_integrity_enabled(manifestPath)) {
    _riCascadeDeleteDependents(manifestPath, entityName, recordUuid, new Set());
  }
  const doc = _loadJson(p);
  _riCore().bejson_core_delete_record(doc, recordUuid);
  _writeBejson(p, doc);
  if (syncCount) mfdb_core_sync_count(manifestPath, entityName, doc.Values.length);
  return doc;
}

// ---------------------------------------------------------------------------
// Exports — combined: MFDBArchive (zip mount/commit) + manifest/entity
// manipulation functions (merged from engine dump). Non-overlapping
// responsibilities, both retained.
// ---------------------------------------------------------------------------

const exports_ = {
  // Error codes
  E_MFDB_CORE_MANIFEST_NOT_FOUND,
  E_MFDB_CORE_ENTITY_NOT_FOUND,
  E_MFDB_CORE_WRITE_FAILED,
  E_MFDB_CORE_CREATE_FAILED,
  E_MFDB_CORE_INVALID_OPERATION,
  E_MFDB_CORE_INDEX_OUT_OF_BOUNDS,
  E_MFDB_CORE_JOIN_FAILED,
  E_MFDB_CORE_ARCHIVE_ERROR,
  E_MFDB_CORE_MOUNT_CONFLICT,
  // Classes
  MFDBCoreError,
  MFDBArchive,
  // Manifest / entity functions
  mfdb_core_create_manifest,
  mfdb_core_register_entity,
  mfdb_core_sync_count,
  mfdb_core_sync_all_counts,
  mfdb_core_init_entity_file,
  // Federation
  CONNECTED_SLAVE_SCHEMA,
  mfdb_core_create_connected_slave_entity,
  mfdb_federation_push_config,
  mfdb_federation_poll_dropzone,
  mfdb_federation_distill_logs,
  // Debug system
  META_DEBUG_FIELDS,
  mfdb_core_enable_debug,
  mfdb_core_disable_debug,
  mfdb_core_get_debug_log,
  mfdb_core_get_failed_ops,
  mfdb_core_clear_debug_log,
  mfdb_core_debug_summary,
  mfdb_core_detect_schema_drift,
  // Phase 6 -- 105-series referential integrity
  mfdb_core_enable_ref_integrity,
  mfdb_core_disable_ref_integrity,
  mfdb_core_is_ref_integrity_enabled,
  mfdb_core_check_fk_write,
  mfdb_core_find_referencing_rows,
  mfdb_core_check_entity_droppable,
  mfdb_core_add_entity_record_105,
  mfdb_core_update_entity_record_105,
  mfdb_core_delete_entity_record_105,
  // Version
  version: "1.31"
};

if (typeof module !== 'undefined' && module.exports) {
  module.exports = exports_;
}
if (typeof window !== 'undefined') {
  window.MFDB_CORE = { ...window.MFDB_CORE, ...exports_ };
}
