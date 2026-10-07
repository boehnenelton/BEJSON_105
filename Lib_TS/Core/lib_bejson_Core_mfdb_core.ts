/**
 * Library:        lib_bejson_Core_mfdb_core.ts
 * Family:         Core
 * Description:    Multi-file database orchestrator managing manifests and entity synchronization.
 * Version:        2.3.3
 * Date:           2026-10-03
 * Author:         Elton Boehnen
 * Contact:        eltonboehnen@gmail.com | boehnenelton2024.pages.dev | github.com/boehnenelton
 * Format_Creator: Elton Boehnen
 * RELATIONAL_ID:  5ae09152-303b-44a1-a6f1-f2d0d6322d6a
 * Release_Version: 300
 *
 * FIX (2026-10-03): registerEntity() now defaults record_count to 0 instead
 * of null, closing the previously documented parseInt(null) -> NaN ->
 * BEJSONCoreError("Coercion failed.") crash in appendRecord/_coerceValue.
 *
 * FIX (2026-10-03, 2.3.3): the Meta-GUID debug section referenced bare `fs` and
 * `path` that were never imported at module scope (they only exist as local
 * consts inside three unrelated functions). In Node, _debugIsEnabled() swallowed
 * the ReferenceError and always returned false -- the debug system could never
 * turn on -- and enableDebug()/getDebugLog()/etc. threw ReferenceError. Added
 * lazy module-scope handles (resolved on first use, so browser bundles that
 * never touch the debug API still load). No call sites changed.
 *
 * FEATURE (2026-08-26): Phase 6 TS port -- 105-series Referential
 * Integrity enforcement helpers: enableRefIntegrity/disableRefIntegrity/
 * isRefIntegrityEnabled (advisory manifest header -- this file has no
 * entity-CRUD wrapper to auto-gate the way Python's does, so these are
 * opt-in helpers, not an automatic switch; see the in-file architecture
 * note), checkFKWrite (write-time exists-check), checkEntityDroppable
 * (read-only), resolveDeleteDependents (delete-time restrict/cascade/null
 * resolution, cycle-guarded, immutable). The standalone audit
 * (checkReferentialIntegrity) lives in mfdb_validators.ts instead,
 * matching Python's file split.
 * (Former KNOWN BUG re: omitted record_count in registerEntity -- resolved, see FIX 2026-10-03 above.)
 *
 * FEATURE (2026-07-31): Meta-GUID debug entity system — full TS port with
 * typed interfaces: MetaDebugRow, MetaLogOptions, DebugSummary,
 * SchemaDriftEntry. enable/disable/get_log/get_failed_ops/clear_log/
 * debug_summary/detect_schema_drift exported. Node.js only.
 *
 * FEATURE (2026-07-29): Network_Role added to CreateManifestOptions and
 * createManifest. Federation block added: ConnectedSlaveSchema type,
 * CONNECTED_SLAVE_SCHEMA constant, createConnectedSlaveEntity, and Node.js
 * federation functions (federationPushConfig, federationPollDropzone,
 * federationDistillLogs) with typed interfaces.
 */

import { bejson_core_get_field_index as _fmIndex } from "./lib_bejson_Core_bejson_field_map";
import {
  BEJSONDocument,
  BEJSONField,
  BEJSONValue,
  MFDBManifestRecord,
  MFDBDatabaseMeta,
  MFDBCoreError,
  MFDB_CORE_CODES as E,
  MFDB_VALIDATION_CODES as EV,
} from "./lib_bejson_Core_bejson_types";
import { decodeManifestRecords } from "./lib_bejson_Core_mfdb_validators";
import {
  appendRecord,
  deleteRecord,
  getFieldIndex,
  setFieldValue,
  createEmpty104a,
  createEmpty104,
} from "./lib_bejson_Core_bejson_core";
import { deleteRecord105 as _deleteRecord105, writeCell as _writeCell } from "./lib_bejson_Core_bejson_core_105";

// ---------------------------------------------------------------------------
// MFDBArchive Interface (v1.3
// ---------------------------------------------------------------------------

/**
 * Handles .mfdb.zip packaging and virtual mounting using File System Access API.
 */
export interface MFDBArchiveInterface {
  /**
   * Mounts a .mfdb.zip file into a FileSystemDirectoryHandle.
   */
  mount(zipFile: File | Blob, dirHandle: any): Promise<string>;

  /**
   * Repacks a FileSystemDirectoryHandle back into a .mfdb.zip Blob.
   */
  commit(dirHandle: any): Promise<Blob>;
}

// ---------------------------------------------------------------------------
// Manifest factory
// ---------------------------------------------------------------------------

export type NetworkRole = "Master" | "Slave" | "Standalone";

export interface CreateManifestOptions extends MFDBDatabaseMeta {
  includeOptionalFields?: boolean;
  network_role?: NetworkRole;   // "Master" | "Slave" | "Standalone" (default)
}

export function createManifest(opts: CreateManifestOptions): BEJSONDocument {
  if (!opts.db_name || opts.db_name.trim() === "") {
    throw new MFDBCoreError(E.MISSING_DB_NAME, "DB_Name is required when creating a manifest.");
  }

  const includeOptional = opts.includeOptionalFields !== false;
  const networkRole: NetworkRole = opts.network_role ?? "Standalone";

  const fields: BEJSONField[] = [
    { name: "entity_name", type: "string" },
    { name: "file_path", type: "string" },
  ];
  if (includeOptional) {
    fields.push(
      { name: "description", type: "string" },
      { name: "record_count", type: "integer" },
      { name: "schema_version", type: "string" },
      { name: "primary_key", type: "string" }
    );
  }

  const customHeaders: Record<string, string> = {
    MFDB_Version:  opts.mfdb_version ?? "1.31",
    Network_Role:  networkRole,
    DB_Name:       opts.db_name,
  };
  if (opts.db_description) customHeaders["DB_Description"] = opts.db_description;
  if (opts.schema_version) customHeaders["Schema_Version"] = opts.schema_version;
  if (opts.author)         customHeaders["Author"]         = opts.author;
  if (opts.created_at)     customHeaders["Created_At"]     = opts.created_at;

  return createEmpty104a("mfdb", fields, customHeaders);
}

// ---------------------------------------------------------------------------
// Entity registration
// ---------------------------------------------------------------------------

export function registerEntity(
  manifest: BEJSONDocument,
  record: MFDBManifestRecord
): BEJSONDocument {
  _assertManifest(manifest);

  const existing = decodeManifestRecords(manifest);
  if (existing.some((r) => r.entity_name === record.entity_name)) {
    throw new MFDBCoreError(
      E.DUPLICATE_ENTITY_NAME,
      "Entity \"" + record.entity_name + "\" is already registered."
    );
  }

  const fieldNames = manifest.Fields.map((f) => f.name);
  const row: BEJSONValue[] = fieldNames.map((name) => {
    switch (name) {
      case "entity_name": return record.entity_name;
      case "file_path": return record.file_path;
      case "description": return record.description ?? null;
      case "record_count": return record.record_count ?? 0;
      case "schema_version": return record.schema_version ?? null;
      case "primary_key": return record.primary_key ?? null;
      default: return null;
    }
  });

  return appendRecord(manifest, row);
}

export function unregisterEntity(
  manifest: BEJSONDocument,
  entityName: string
): BEJSONDocument {
  _assertManifest(manifest);
  const idx = _findEntityIndex(manifest, entityName);
  return deleteRecord(manifest, idx);
}

export function syncRecordCount(
  manifest: BEJSONDocument,
  entityName: string,
  count: number
): BEJSONDocument {
  _assertManifest(manifest);
  const idx = _findEntityIndex(manifest, entityName);

  try {
    getFieldIndex(manifest, "record_count");
  } catch {
    throw new MFDBCoreError(
      E.RECORD_COUNT_SYNC_FAILED,
      "Manifest lacks \"record_count\" field."
    );
  }

  return setFieldValue(manifest, idx, "record_count", count);
}

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

function _assertManifest(doc: BEJSONDocument): void {
  if (!doc) {
    throw new MFDBCoreError(E.NULL_MANIFEST, "Manifest is null or undefined.");
  }
}

function _findEntityIndex(manifest: BEJSONDocument, entityName: string): number {
  const enIdx = getFieldIndex(manifest, "entity_name");
  for (let i = 0; i < manifest.Values.length; i++) {
    if (manifest.Values[i][enIdx] === entityName) return i;
  }
  throw new MFDBCoreError(
    E.ENTITY_NOT_IN_MANIFEST,
    "Entity \"" + entityName + "\" not found."
  );
}

// ---------------------------------------------------------------------------
// Federated Master / Slave node system
// ---------------------------------------------------------------------------
// Network_Role is now emitted on createManifest. This block wires the full
// runtime federation protocol. Node.js I/O functions (push/poll/distill)
// require the fs module — they throw at call-time if run in a browser.

export interface ConnectedSlaveSchema {
  slave_id:           string;
  label:              string;
  url:                string;
  role:               string;
  status:             string;
  supported_entities: string[];
}

export const CONNECTED_SLAVE_SCHEMA: BEJSONField[] = [
  { name: "slave_id",           type: "string" },
  { name: "label",              type: "string" },
  { name: "url",                type: "string" },
  { name: "role",               type: "string" },
  { name: "status",             type: "string" },
  { name: "supported_entities", type: "array"  },
];

/**
 * Register a ConnectedSlave entity in a Master manifest.
 * Throws if the manifest's Network_Role !== "Master".
 */
export function createConnectedSlaveEntity(manifest: BEJSONDocument): BEJSONDocument {
  const role = (manifest as any)["Network_Role"] ?? "";
  if (role !== "Master") {
    throw new MFDBCoreError(
      E.INVALID_OPERATION ?? "INVALID_OPERATION",
      `ConnectedSlave may only be created on a Master node. Got: '${role}'`
    );
  }
  return registerEntity(manifest, {
    entity_name:    "ConnectedSlave",
    file_path:      "data/connectedslave.bejson",
    description:    "Registry of Slave nodes connected to this Master.",
    primary_key:    "slave_id",
    record_count:   0,
    schema_version: "1.0",
  });
}

export interface FederationPushResult { success: boolean; error?: string; }
export interface FederationPollOptions { pollInterval?: number; timeout?: number; }
export interface FederationDistillOptions { maxRows?: number; }

/**
 * Master → Slave atomic drop-zone push (Node.js only).
 * Writes configDoc to slaveTargetPath via same-dir temp + rename.
 */
export function federationPushConfig(
  configDoc: Record<string, unknown>,
  slaveTargetPath: string
): FederationPushResult {
  const fs   = require("fs");
  const path = require("path");
  const dest    = path.resolve(slaveTargetPath);
  const destDir = path.dirname(dest);
  fs.mkdirSync(destDir, { recursive: true });
  const tempPath = `${dest}.tmp.${Date.now()}`;
  try {
    fs.writeFileSync(tempPath, JSON.stringify(configDoc, null, 2), "utf8");
    fs.renameSync(tempPath, dest);
    return { success: true };
  } catch (err: any) {
    if (fs.existsSync(tempPath)) try { fs.unlinkSync(tempPath); } catch (_) {}
    return { success: false, error: err.message };
  }
}

/**
 * Slave: poll a local dropzone for incoming Master config docs (Node.js only).
 * Each .bejson file found is parsed, passed to callback, then removed.
 * Returns a getter that returns the count of configs processed so far.
 */
export function federationPollDropzone(
  dropzoneDir: string,
  callback: (filePath: string, doc: Record<string, unknown>) => void,
  { pollInterval = 2000, timeout = 60000 }: FederationPollOptions = {}
): () => number {
  const fs   = require("fs");
  const path = require("path");
  fs.mkdirSync(dropzoneDir, { recursive: true });

  let processed = 0;
  const deadline = Date.now() + timeout;

  const tick = () => {
    if (Date.now() >= deadline) return;
    const files: string[] = fs.readdirSync(dropzoneDir)
      .filter((f: string) => f.endsWith(".bejson"))
      .sort()
      .map((f: string) => path.join(dropzoneDir, f));

    for (const fpath of files) {
      try {
        const doc = JSON.parse(fs.readFileSync(fpath, "utf8"));
        callback(fpath, doc);
        fs.unlinkSync(fpath);
        processed++;
      } catch (e: any) {
        console.warn(`[MFDB_FEDERATION] poll_dropzone skipped ${fpath}: ${e.message}`);
      }
    }
    setTimeout(tick, pollInterval);
  };

  tick();
  return () => processed;
}

/**
 * Slave → Master one-way push (log distillation, Node.js only).
 * Overflow rows are pushed as a distilled summary to masterPollDir;
 * the local entity is truncated to maxRows.
 */
export function federationDistillLogs(
  slaveManifestPath: string,
  entityName: string,
  masterPollDir: string,
  { maxRows = 100 }: FederationDistillOptions = {}
): boolean {
  const fs   = require("fs");
  const path = require("path");

  const manifestDoc = JSON.parse(fs.readFileSync(slaveManifestPath, "utf8")) as BEJSONDocument;
  const records     = decodeManifestRecords(manifestDoc);
  const entry       = records.find(r => r.entity_name === entityName);
  if (!entry) {
    throw new MFDBCoreError(E.ENTITY_NOT_IN_MANIFEST, `Entity '${entityName}' not found.`);
  }

  const entityPath = path.resolve(path.dirname(slaveManifestPath), entry.file_path);
  const entityDoc  = JSON.parse(fs.readFileSync(entityPath, "utf8")) as BEJSONDocument;
  const rows       = entityDoc.Values ?? [];

  if (rows.length <= maxRows) return true;

  const overflow = rows.slice(0, rows.length - maxRows);
  const kept     = rows.slice(rows.length - maxRows);

  fs.mkdirSync(masterPollDir, { recursive: true });
  const ts   = new Date().toISOString().replace(/[:.]/g, "").slice(0, 15) + "Z";
  const dest = path.join(masterPollDir, `distilled_${entityName}_${ts}.bejson`);

  const summaryDoc = {
    Format: "BEJSON", Format_Version: "104a", Format_Creator: "Elton Boehnen",
    Distill_Source: entityName,
    Distill_Timestamp: new Date().toISOString(),
    Records_Type: ["DistilledLog"],
    Fields: entityDoc.Fields,
    Values: overflow,
  };

  const pushResult = federationPushConfig(summaryDoc, dest);
  if (!pushResult.success) return false;

  entityDoc.Values = kept;
  const tempEntity = entityPath + ".tmp." + Date.now();
  fs.writeFileSync(tempEntity, JSON.stringify(entityDoc, null, 2), "utf8");
  fs.renameSync(tempEntity, entityPath);

  const updatedManifest = syncRecordCount(manifestDoc, entityName, kept.length);
  const tempManifest    = slaveManifestPath + ".tmp." + Date.now();
  fs.writeFileSync(tempManifest, JSON.stringify(updatedManifest, null, 2), "utf8");
  fs.renameSync(tempManifest, slaveManifestPath);

  return true;
}

// ── Meta-GUID Debug Entity System (TypeScript) ─────────────────────────────────
// Full typed port of the Python/JS debug block. Node.js only — all functions
// that touch the filesystem silently no-op outside Node.

export const META_DEBUG_FIELDS: BEJSONField[] = [
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

export interface MetaDebugRow {
  timestamp:     string;
  operation:     string;
  target_entity: string;
  field_name:    string | null;
  field_exists:  boolean | null;
  row_index:     number | null;
  success:       boolean;
  duration_ms:   number;
  pid:           number;
  notes:         string;
}

export interface MetaLogOptions {
  fieldName?:  string | null;
  fieldExists?: boolean | null;
  rowIndex?:   number | null;
  success?:    boolean;
  durationMs?: number;
  notes?:      string;
  readsOnly?:  boolean;
}

export interface DebugSummary {
  total_ops:         number;
  unique_entities:   string[];
  failed_ops:        number;
  schema_drift_hits: number;
  top_3_slowest:     { op: string; entity: string; duration_ms: number }[];
  reads_logged:      number;
  writes_logged:     number;
  ops_by_type:       Record<string, number>;
}

export interface SchemaDriftEntry {
  added_fields:   string[];
  removed_fields: string[];
  drifted:        boolean;
}

export interface EnableDebugOptions {
  rowCap?:     number;
  debugReads?: boolean;
}

// Lazy Node-only module handles for the debug section (see FIX 2.3.3 above).
declare const require: any;
const fs: any   = new Proxy({}, { get: (_t, k: string) => require("fs")[k] });
const path: any = new Proxy({}, { get: (_t, k: string) => require("path")[k] });

function _debugIsEnabled(manifestPath: string): boolean {
  try {
    const doc = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
    return String(doc.Debug_Mode ?? "false").toLowerCase() === "true";
  } catch { return false; }
}

function _debugReadsEnabled(manifestPath: string): boolean {
  try {
    const doc = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
    return String(doc.Debug_Reads ?? "false").toLowerCase() === "true";
  } catch { return false; }
}

function _debugGetMetaName(manifestPath: string): string | null {
  try {
    const doc = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
    return doc.Debug_Meta_Entity || null;
  } catch { return null; }
}

function _debugGetEntityPath(manifestPath: string, entityName: string): string {
  const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8")) as BEJSONDocument;
  const records  = decodeManifestRecords(manifest);
  const entry    = records.find(r => r.entity_name === entityName);
  if (!entry) throw new MFDBCoreError(E.ENTITY_NOT_IN_MANIFEST, `Entity '${entityName}' not found`);
  return path.resolve(path.dirname(manifestPath), entry.file_path);
}

function _debugAtomicWrite(filePath: string, doc: unknown): void {
  const temp = `${filePath}.tmp.${Date.now()}`;
  fs.writeFileSync(temp, JSON.stringify(doc, null, 2), "utf8");
  fs.renameSync(temp, filePath);
}

function _metaAutoTrim(manifestPath: string, metaName: string, metaPath: string): void {
  try {
    const cap  = parseInt(JSON.parse(fs.readFileSync(manifestPath, "utf8")).Debug_Row_Cap ?? "500", 10);
    const doc  = JSON.parse(fs.readFileSync(metaPath, "utf8")) as BEJSONDocument;
    if ((doc.Values ?? []).length > cap) {
      doc.Values = doc.Values!.slice(-cap);
      _debugAtomicWrite(metaPath, doc);
    }
  } catch { /* non-fatal */ }
}

function _metaSchemaSnapshot(manifestPath: string, metaName: string): void {
  try {
    const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8")) as BEJSONDocument;
    const records  = decodeManifestRecords(manifest);
    for (const rec of records) {
      const ename = rec.entity_name;
      if (!ename || ename === metaName) continue;
      try {
        const edoc   = JSON.parse(fs.readFileSync(_debugGetEntityPath(manifestPath, ename), "utf8")) as BEJSONDocument;
        const fields = (edoc.Fields ?? []).map((f: BEJSONField) => f.name).join(",");
        _metaLog(manifestPath, "SCHEMA_SNAPSHOT", ename, {
          fieldName: fields, fieldExists: true, durationMs: 0,
          notes: `field_count=${(edoc.Fields ?? []).length}`,
        });
      } catch { /* skip unreadable entities */ }
    }
  } catch { /* non-fatal */ }
}

export function _metaLog(
  manifestPath: string,
  operation:    string,
  targetEntity: string,
  opts: MetaLogOptions = {}
): void {
  const {
    fieldName = null, fieldExists = null, rowIndex = null,
    success = true, durationMs = 0, notes = "", readsOnly = false,
  } = opts;

  try {
    if (!_debugIsEnabled(manifestPath)) return;
    if (readsOnly && !_debugReadsEnabled(manifestPath)) return;

    const metaName = _debugGetMetaName(manifestPath);
    if (!metaName) return;

    const metaPath = _debugGetEntityPath(manifestPath, metaName);
    const doc      = JSON.parse(fs.readFileSync(metaPath, "utf8")) as BEJSONDocument;
    doc.Values     = doc.Values ?? [];
    doc.Values.push([
      new Date().toISOString(), operation, targetEntity,
      fieldName, fieldExists, rowIndex, success, durationMs,
      process.pid, notes ?? "",
    ]);
    _debugAtomicWrite(metaPath, doc);
    _metaAutoTrim(manifestPath, metaName, metaPath);
  } catch { /* debug must never break the caller */ }
}

// ── Public Debug API (TS) ──────────────────────────────────────────────────────

export function enableDebug(
  manifestPath: string,
  { rowCap = 500, debugReads = false }: EnableDebugOptions = {}
): string {
  const crypto = require("crypto");
  const doc    = JSON.parse(fs.readFileSync(manifestPath, "utf8")) as BEJSONDocument;

  const metaName: string = (doc as any).Debug_Meta_Entity || `meta-${crypto.randomUUID()}`;
  (doc as any).Debug_Mode        = "true";
  (doc as any).Debug_Meta_Entity = metaName;
  (doc as any).Debug_Row_Cap     = String(rowCap);
  (doc as any).Debug_Reads       = debugReads ? "true" : "false";
  _debugAtomicWrite(manifestPath, doc);

  const metaFpRel = `data/${metaName}.bejson`;
  const metaAbs   = path.resolve(path.dirname(manifestPath), metaFpRel);

  if (!fs.existsSync(metaAbs)) {
    fs.mkdirSync(path.dirname(metaAbs), { recursive: true });
    const metaDoc = {
      Format: "BEJSON", Format_Version: "104", Format_Creator: "Elton Boehnen",
      Parent_Hierarchy: path.relative(path.dirname(metaAbs), manifestPath),
      Records_Type: [metaName],
      Fields: META_DEBUG_FIELDS, Values: [],
    };
    _debugAtomicWrite(metaAbs, metaDoc);

    const doc2    = JSON.parse(fs.readFileSync(manifestPath, "utf8")) as BEJSONDocument;
    const records = decodeManifestRecords(doc2);
    if (!records.find(r => r.entity_name === metaName)) {
      doc2.Values = doc2.Values ?? [];
      doc2.Values.push([metaName, metaFpRel, "Debug audit log (auto-generated)", 0, "1.0", null]);
      _debugAtomicWrite(manifestPath, doc2);
    }
  }

  _metaSchemaSnapshot(manifestPath, metaName);
  return metaName;
}

export function disableDebug(manifestPath: string): void {
  const doc = JSON.parse(fs.readFileSync(manifestPath, "utf8")) as BEJSONDocument;
  (doc as any).Debug_Mode = "false";
  _debugAtomicWrite(manifestPath, doc);
}

export function getDebugLog(manifestPath: string): MetaDebugRow[] {
  const metaName = _debugGetMetaName(manifestPath);
  if (!metaName) return [];
  try {
    const doc = JSON.parse(fs.readFileSync(_debugGetEntityPath(manifestPath, metaName), "utf8")) as BEJSONDocument;
    const fm: Record<string, number> = {};
    (doc.Fields ?? META_DEBUG_FIELDS).forEach((f: BEJSONField, i: number) => { fm[f.name] = i; });
    return (doc.Values ?? []).map((row: unknown[]) => {
      const out: Record<string, unknown> = {};
      for (const [k, i] of Object.entries(fm)) out[k] = row[i];
      return out as unknown as MetaDebugRow;
    });
  } catch { return []; }
}

export function getFailedOps(manifestPath: string): MetaDebugRow[] {
  return getDebugLog(manifestPath)
    .filter(r => r.success === false)
    .sort((a, b) => (a.timestamp > b.timestamp ? 1 : -1));
}

export function clearDebugLog(manifestPath: string): number {
  const metaName = _debugGetMetaName(manifestPath);
  if (!metaName) return 0;
  try {
    const metaPath = _debugGetEntityPath(manifestPath, metaName);
    const doc      = JSON.parse(fs.readFileSync(metaPath, "utf8")) as BEJSONDocument;
    const deleted  = (doc.Values ?? []).length;
    doc.Values     = [];
    _debugAtomicWrite(metaPath, doc);
    return deleted;
  } catch { return 0; }
}

export function debugSummary(manifestPath: string): DebugSummary | Record<string, never> {
  if (!_debugIsEnabled(manifestPath)) return {};
  const rows = getDebugLog(manifestPath);
  if (!rows.length) return { total_ops: 0 } as unknown as DebugSummary;

  const writeOps  = new Set(["ADD", "REMOVE", "UPDATE", "UPDATE_BULK"]);
  const opsByType: Record<string, number> = {};
  for (const r of rows) opsByType[r.operation] = (opsByType[r.operation] ?? 0) + 1;

  return {
    total_ops:         rows.length,
    unique_entities:   [...new Set(rows.map(r => r.target_entity))].sort(),
    failed_ops:        rows.filter(r => r.success === false).length,
    schema_drift_hits: rows.filter(r => r.field_exists === false).length,
    top_3_slowest:     [...rows]
      .sort((a, b) => b.duration_ms - a.duration_ms).slice(0, 3)
      .map(r => ({ op: r.operation, entity: r.target_entity, duration_ms: r.duration_ms })),
    reads_logged:  rows.filter(r => r.operation === "READ").length,
    writes_logged: rows.filter(r => writeOps.has(r.operation)).length,
    ops_by_type:   opsByType,
  };
}

export function detectSchemaDrift(manifestPath: string): Record<string, SchemaDriftEntry> {
  if (!_debugIsEnabled(manifestPath)) return {};
  const rows = getDebugLog(manifestPath);
  const snapshots: Record<string, Set<string>> = {};
  for (const r of rows) {
    if (r.operation === "SCHEMA_SNAPSHOT" && r.field_name) {
      snapshots[r.target_entity] = new Set(r.field_name.split(",").filter(Boolean));
    }
  }
  if (!Object.keys(snapshots).length) return {};

  const report: Record<string, SchemaDriftEntry> = {};
  for (const [ename, snapFields] of Object.entries(snapshots)) {
    try {
      const edoc       = JSON.parse(fs.readFileSync(_debugGetEntityPath(manifestPath, ename), "utf8")) as BEJSONDocument;
      const liveFields = new Set((edoc.Fields ?? []).map((f: BEJSONField) => f.name));
      const added      = [...liveFields].filter(f => !snapFields.has(f)).sort();
      const removed    = [...snapFields].filter(f => !liveFields.has(f)).sort();
      report[ename]    = { added_fields: added, removed_fields: removed, drifted: !!(added.length || removed.length) };
    } catch { /* skip */ }
  }
  return report;
}

// ---------------------------------------------------------------------------
// Phase 6 (2026-08-26) -- 105-series MFDB Referential Integrity, TS port.
//
// ARCHITECTURE NOTE: this file has no add/update/delete-entity-record
// wrapper functions the way lib_bejson_Core_mfdb_core.py does -- entity row
// CRUD in this library already happens directly against a BEJSONDocument
// via lib_bejson_Core_bejson_core_105.ts's pure functions (addRecord105,
// writeCell, deleteRecord105), with no MFDB-level wrapper to hook live
// enforcement into automatically. The honest port is therefore: pure,
// OPT-IN helper functions the caller invokes themselves immediately before
// their own addRecord105/deleteRecord105 calls, rather than an automatic
// gate the way Python's Ref_Integrity switch is. The Ref_Integrity manifest
// header below is advisory for this reason -- nothing in this library reads
// it automatically; it exists so a caller CAN check it and decide whether
// to invoke the helpers, same convention, honestly scoped.
//
// KEYING CONVENTION: checkReferentialIntegrity() (mfdb_validators.ts) takes
// a Map<file_path, doc>, matching validateDatabase's existing manifest-
// driven contract. The three functions below take a Map<entity_name, doc>
// instead -- deliberately different, because a live caller about to mutate
// an entity naturally has it in hand by name, not file_path. Converting
// between the two is one decodeManifestRecords() call away if needed.
// ---------------------------------------------------------------------------

const REF_INTEGRITY_HEADER = "Ref_Integrity";

/** Advisory only -- see architecture note above. Returns a NEW manifest doc. */
export function enableRefIntegrity(manifest: BEJSONDocument): BEJSONDocument {
  return { ...manifest, [REF_INTEGRITY_HEADER]: "true" };
}

/** Advisory only -- see architecture note above. Returns a NEW manifest doc. */
export function disableRefIntegrity(manifest: BEJSONDocument): BEJSONDocument {
  return { ...manifest, [REF_INTEGRITY_HEADER]: "false" };
}

export function isRefIntegrityEnabled(manifest: BEJSONDocument): boolean {
  return manifest[REF_INTEGRITY_HEADER] === "true";
}

function _is105SeriesEntity(doc: BEJSONDocument): boolean {
  return doc.Format_Version === "105" || doc.Format_Version === "105a" || doc.Format_Version === "105db";
}
function _entityUuidCol(doc: BEJSONDocument): number {
  return doc.Format_Version === "105db" ? 1 : 0;
}

/**
 * Write-time exists-check for a single FK field's value. None/undefined
 * always passes (nullable FK). Throws MFDBCoreError on an unresolvable
 * value or an unusable target -- call this yourself immediately before
 * your own addRecord105/writeCell call on the FK field.
 */
export function checkFKWrite(
  fieldDef: BEJSONField,
  value: BEJSONValue,
  targetEntityDoc: BEJSONDocument | undefined
): void {
  if (value === null || value === undefined) return;

  const onDelete = fieldDef.fk_on_delete ?? "restrict";
  if (!["restrict", "cascade", "null"].includes(onDelete)) {
    throw new MFDBCoreError(
      EV.FK_INVALID_ON_DELETE,
      `${fieldDef.name}: fk_on_delete must be restrict/cascade/null, got ${JSON.stringify(onDelete)}`
    );
  }
  if (!targetEntityDoc || !_is105SeriesEntity(targetEntityDoc)) {
    throw new MFDBCoreError(
      EV.FK_TARGET_ENTITY_UNKNOWN,
      `${fieldDef.name}: fk_target_entity ${JSON.stringify(fieldDef.fk_target_entity)} is not a resolvable 105-series entity`
    );
  }
  const uuidCol = _entityUuidCol(targetEntityDoc);
  const exists = targetEntityDoc.Values.some((row) => row[uuidCol] === value);
  if (!exists) {
    throw new MFDBCoreError(EV.FK_UNRESOLVED, `${fieldDef.name}: ${JSON.stringify(value)} does not exist in ${fieldDef.fk_target_entity}`);
  }
}

/**
 * Read-only: every (referencing_entity, fk_field_name, referencing_record_uuid)
 * tuple where some OTHER entity's FK schema targets entityName. Empty
 * result means it's safe to drop. entityDocs is keyed by entity name (see
 * architecture note above).
 */
export function checkEntityDroppable(
  entityDocs: Map<string, BEJSONDocument>,
  entityName: string
): { entity: string; fieldName: string; recordUuid: string }[] {
  const results: { entity: string; fieldName: string; recordUuid: string }[] = [];
  for (const [otherName, doc] of entityDocs) {
    if (otherName === entityName) continue;
    const fkFields = doc.Fields.filter((f) => f.fk_target_entity === entityName);
    if (fkFields.length === 0) continue;
    const uuidCol = _entityUuidCol(doc);
    for (const fkField of fkFields) {
      const col = _fmIndex(doc, fkField.name);
      const offset = doc.Format_Version === "105db" ? 2 : 1;
      for (const row of doc.Values) {
        if (row.length > uuidCol) {
          results.push({ entity: otherName, fieldName: fkField.name, recordUuid: row[uuidCol] as string });
        }
      }
    }
  }
  return results;
}

/**
 * Walks and resolves every OTHER row across entityDocs that references
 * (entityName, recordUuid), per each referencing FK's declared
 * fk_on_delete. Does NOT delete (entityName, recordUuid) itself -- call
 * deleteRecord105() on that yourself after this returns cleanly. Returns a
 * NEW Map (immutable, matching this file's convention) with cascade-deleted
 * rows removed and null'd FKs applied; entities untouched by the walk keep
 * their original object reference. Throws on a restrict violation or a
 * cascade cycle (mutual/circular cascade references) -- in both cases the
 * returned value is never used; nothing partial is left for the caller to
 * accidentally persist.
 */
export function resolveDeleteDependents(
  entityDocs: Map<string, BEJSONDocument>,
  entityName: string,
  recordUuid: string,
  _visited: Set<string> = new Set()
): Map<string, BEJSONDocument> {
  const visitKey = `${entityName}#${recordUuid}`;
  if (_visited.has(visitKey)) {
    throw new MFDBCoreError(EV.FK_CASCADE_CYCLE, `Cascade cycle detected: ${visitKey} revisited during cascade delete`);
  }
  _visited.add(visitKey);

  let working = new Map(entityDocs);

  for (const [refEntityName, refDoc] of entityDocs) {
    const fkFields = refDoc.Fields.filter((f) => f.fk_target_entity === entityName);
    if (fkFields.length === 0) continue;

    const uuidCol = _entityUuidCol(refDoc);
    const offset = refDoc.Format_Version === "105db" ? 2 : 1;

    for (const fkField of fkFields) {
      const onDelete = fkField.fk_on_delete ?? "restrict";
      const col = _fmIndex(refDoc, fkField.name);
      const absCol = col + offset;

      const matchingRows = refDoc.Values.filter((row) => row[absCol] === recordUuid);
      if (matchingRows.length === 0) continue;

      if (onDelete === "restrict") {
        throw new MFDBCoreError(
          EV.FK_RESTRICT_VIOLATION,
          `Cannot delete ${entityName}#${recordUuid}: restricted by ${refEntityName}.${fkField.name} -> ${matchingRows.length} record(s)`
        );
      }

      if (onDelete === "null") {
        let currentDoc = working.get(refEntityName)!;
        const fieldUuid = fkField.field_uuid as string;
        for (const row of matchingRows) {
          const rowUuid = row[uuidCol] as string;
          currentDoc = _writeCell(currentDoc, rowUuid, fieldUuid, null).doc;
        }
        working = new Map(working).set(refEntityName, currentDoc);
      } else if (onDelete === "cascade") {
        for (const row of matchingRows) {
          const depUuid = row[uuidCol] as string;
          working = resolveDeleteDependents(working, refEntityName, depUuid, _visited);
          const currentDoc = working.get(refEntityName)!;
          working = new Map(working).set(refEntityName, _deleteRecord105(currentDoc, depUuid));
        }
      }
    }
  }

  return working;
}
