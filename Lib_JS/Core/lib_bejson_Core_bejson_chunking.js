/**
 * Library:         lib_bejson_Core_bejson_chunking.js
 * Family:          Core
 * Description:     Standardized BEJSON project chunking engine. Ported 1:1 from
 *                   CLI_Chunker.py's Chunked-104 (104a) schema logic so all four
 *                   language families (PY/JS/TS/SH) produce byte-identical
 *                   documents from the same directory. Also implements the
 *                   MFDB 1.32 packaging extension: chunking an entire MFDB
 *                   database (manifest + entity files) into a single Chunked-104a
 *                   document as an alternative to the 1.31 zip container.
 *                   1.31 zip-based MFDB databases remain fully valid and
 *                   unaffected — 1.32 only adds an optional packaging format.
 *                   MFDB validation logic (mfdb_validator_is_mfdb132_package,
 *                   mfdb_validator_validate_mfdb132_package,
 *                   mfdb_validator_detect_mfdb_in_chunk) has been relocated to
 *                   lib_bejson_Core_mfdb_validator.js — this file now only
 *                   packages/unpacks and calls back into the validator.
 * Version:         1.8.1
 * Library_Version: 227
 * Date:            2026-10-06
 * RELATIONAL_ID:   fe7e7c93-4dbc-43d0-b1f6-df157f67b06f
 * Release_Version: 300
 *
 * CHANGE (2026-10-06): Consolidation re-merge -- the V6-PKG101 silent-catch
 * logging fix (unmount's lock-release header-clear cleanup) had been
 * reverted/lost on the forward V10-PKG102 branch; re-applied here, no
 * behavior change.
 *
 * CHANGE (2026-08-08): LIB-D3 -- renamed top-level session header
 * "Is_Mounted" to "Session_Is_Mounted" (collided with the per-row
 * Fields[] entry of the same name; also fixed from string "True"/"False"
 * to a real boolean). LIB-C2 -- File_Hash now SHA-256 instead of SHA-1.
 *
 * CHANGE (2026-08-07): Renamed top-level header "Chunk_Date-YYYY-MM-DD" to
 * "Chunk_Date" (LIB-D2/LIB-C3) -- fails PASCAL_CASE_RE in the TS sibling's
 * validator (hyphens not allowed). No readers of the old key existed.
 *
 * FEATURE (2026-08-02, later same day): Added bejsonCoreChunkingMfdb* --
 * see PY sibling file's docstring for full rationale (unifies chunking
 * globally across the flat Chunked-104a/MFDB-132 schema and mfdb_chunker.py's
 * rolling multi-version MFDB layout, same file/family, distinct function
 * prefix). Ported 1:1 from the PY implementation.
 *
 * FEATURE (2026-08-02): Package_Version tracking added -- see PY sibling
 * file's docstring for full rationale (ties back to the project schema
 * tracker's Project_Version / Package_Version split). Adds
 * bejsonCoreChunkingBumpPackageVersion() and a packageVersion param on both
 * create functions. Fully backward compatible.
 *
 * FEATURE (2026-07-29): MFDB132Archive class — full session-based mount
 * mirroring MFDBArchive (1.31). mount() unchunks to workspace + writes
 * .mfdb132_lock; commit() pre-validates then rechunks atomically;
 * resurrect_file() re-unchunks a single entity; unmount() releases lock
 * and clears Is_Mounted/Mount_Path headers on the chunk doc.
 *
 * FEATURE (2026-07-14): Binary file content is now preserved. Previously
 * Is_Binary=true rows stored File_Content="" and were skipped on unchunk,
 * silently losing any binary file. Binary bytes are now base64-encoded into
 * File_Content on chunk and base64-decoded back to real bytes on unchunk.
 * Is_Binary is unchanged as a schema field — it now doubles as the per-row
 * decode-path label. See /docs/FEATURE_base64_binary_preservation.md.
 *
 * BUGFIX (2026-07-14): v1.2.0 used ES-module `import`/`export` syntax while
 * every other Lib_JS/Core file (bejson_core.js, bejson_validator.js,
 * mfdb_core.js, mfdb_validator.js, bejson_errors.js) uses the CommonJS/UMD
 * `require()` + `module.exports` pattern. Under Node, `import { name } from
 * './lib_bejson_Core_mfdb_validator.js'` fails at load time because that file
 * is CommonJS and Node's static ESM/CJS interop cannot see its named exports
 * (only `default` is visible) — confirmed via direct reproduction. This file
 * has been converted to the same CommonJS/UMD pattern as its siblings. See
 * /docs/BUGFIX_chunking_js_module_system.md for the full report.
 *
 * Node.js only (uses fs/crypto). JS mirror of lib_bejson_Core_bejson_chunking.ts —
 * keep both in parity; this file has no TS-only constructs (no types/interfaces).
 */

const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const {
  mfdb_validator_is_mfdb132_package,
  mfdb_validator_validate_mfdb132_package,
  mfdb_validator_detect_mfdb_in_chunk,
} = require("./lib_bejson_Core_mfdb_validator.js");

const DEFAULT_EXTENSIONS = [
  ".py", ".js", ".ts", ".html", ".css", ".md", ".json",
  ".sh", ".txt", ".bejson", ".tsx", ".jsx",
];

const DEFAULT_EXCLUDES = [
  ".git", "__pycache__", "node_modules", "lib", "output",
  ".mfdb_lock", "dist", "build",
];

const CHUNKED_104_FIELDS = [
  { name: "File_Name", type: "string" },
  { name: "File_Extension", type: "string" },
  { name: "File_Content", type: "string" },
  { name: "File_Version", type: "string" },
  { name: "File_Hash", type: "string" },
  { name: "Relative_Path", type: "string" },
  { name: "Is_Binary", type: "boolean" },
  { name: "Is_Mounted", type: "boolean" },
];

const MFDB_MANIFEST_FILENAME = "104a.mfdb.bejson";
// Fixed packaging-format identifier for the MFDB-132 spec itself — NOT the
// database's own MFDB_Version (which lives inside the wrapped manifest and
// increments normally). This constant intentionally never changes; "1.32" is
// what makes it "MFDB-132." Do not bump this to track DB schema changes.
const MFDB_CHUNK_SCHEMA_VERSION = "1.32";

function bejsonCoreChunkingGetTimestamp() {
  return new Date().toISOString().replace(/\.\d{3}Z$/, "Z");
}

function bejsonCoreChunkingIsBinary(filePath) {
  // Matches CLI_Chunker.py: attempt strict UTF-8 decode of first 1024 bytes.
  try {
    const fd = fs.openSync(filePath, "r");
    const buf = Buffer.alloc(1024);
    const bytesRead = fs.readSync(fd, buf, 0, 1024, 0);
    fs.closeSync(fd);
    const slice = buf.subarray(0, bytesRead);
    new TextDecoder("utf-8", { fatal: true }).decode(slice);
    return false;
  } catch {
    return true;
  }
}

// LIB-C2 fix (2026-08-08): SHA-1 -> SHA-256. Corruption-detection
// checksum, not a security signature -- low severity, but SHA-1 is
// deprecated and SHA-256 costs nothing here. Straight swap, no
// migration path (matches this ecosystem's established convention).
function bejsonCoreChunkingHashFileBytes(rawBytes) {
  return crypto.createHash("sha256").update(rawBytes).digest("hex");
}

function walkDir(root, excludeDirs) {
  const results = [];
  const stack = [root];
  while (stack.length) {
    const current = stack.pop();
    const entries = fs.readdirSync(current, { withFileTypes: true });
    for (const entry of entries) {
      if (entry.isDirectory()) {
        if (!excludeDirs.includes(entry.name)) {
          stack.push(path.join(current, entry.name));
        }
      } else if (entry.isFile()) {
        results.push(path.join(current, entry.name));
      }
    }
  }
  return results;
}

function bejsonCoreChunkingBumpPackageVersion(priorDoc) {
  // Package_Version tracking, mirroring the project schema tracker's
  // Project_Version / Package_Version split -- see PY counterpart docstring
  // for full rationale. Numeric-string bump; non-numeric/missing resets to "1".
  if (!priorDoc) return "1";
  const n = parseInt(priorDoc.Package_Version, 10);
  return Number.isNaN(n) ? "1" : String(n + 1);
}

function bejsonCoreChunkingCreateChunked104(
  targetDir,
  version = "latest",
  extensions = null,
  excludeDirs = null,
  packageVersion = null
) {
  const targetPath = path.resolve(targetDir);
  const exts = extensions !== null ? extensions : DEFAULT_EXTENSIONS;
  const excl = excludeDirs !== null ? excludeDirs : DEFAULT_EXCLUDES;

  const values = [];
  const allFiles = walkDir(targetPath, excl);

  for (const filePath of allFiles) {
    const ext = path.extname(filePath).toLowerCase();
    if (!exts.includes(ext)) continue;
    try {
      const relPath = path.relative(targetPath, filePath);
      const isBin = bejsonCoreChunkingIsBinary(filePath);
      const rawBytes = fs.readFileSync(filePath);
      const content = isBin ? rawBytes.toString("base64") : rawBytes.toString("utf-8");
      const fileHash = bejsonCoreChunkingHashFileBytes(rawBytes);

      values.push([
        path.basename(filePath),
        path.extname(filePath),
        content,
        version,
        fileHash,
        relPath,
        isBin,
        false,
      ]);
    } catch {
      continue;
    }
  }

  return {
    Format: "BEJSON",
    Format_Version: "104a",
    Format_Creator: "Elton Boehnen",
    Schema_Name: "Chunked-104a",
    Schema_Version: "1.0.1",
    Schema_Description: "Standard schema for chunking single projects.",
    "Chunk_Date": bejsonCoreChunkingGetTimestamp().slice(0, 10),
    // LIB-D3 fix (2026-08-08): renamed from "Is_Mounted" (collided with
    // the per-row Fields[] entry of the same name, and was a string
    // "True"/"False" instead of a real boolean) to Session_Is_Mounted.
    Session_Is_Mounted: false,
    Mount_Path: "",
    Package_Version: packageVersion || "1",
    Records_Type: ["Chunked"],
    Fields: CHUNKED_104_FIELDS,
    Values: values,
  };
}

function bejsonCoreChunkingUnchunkChunked104(doc, outputDir) {
  const fields = doc.Fields || CHUNKED_104_FIELDS;
  const fm = {};
  fields.forEach((f, i) => (fm[f.name] = i));

  const outRoot = path.resolve(outputDir);
  let count = 0;

  for (const row of doc.Values || []) {
    const relPath = row[fm["Relative_Path"]];
    const isBinary = row[fm["Is_Binary"]];
    const content = row[fm["File_Content"]];
    if (!relPath || content === null || content === undefined) continue;

    const targetFile = path.join(outRoot, relPath);
    fs.mkdirSync(path.dirname(targetFile), { recursive: true });
    if (isBinary) {
      fs.writeFileSync(targetFile, Buffer.from(content, "base64"));
    } else {
      fs.writeFileSync(targetFile, content, { encoding: "utf-8" });
    }
    count += 1;
  }

  return count;
}

// ── MFDB 1.32 packaging extension ──────────────────────────────────────────
// 1.31 stays fully valid and unchanged (manifest + entity files, optionally
// zipped). 1.32 adds a second, optional container: the entire MFDB directory
// (manifest + every entity file) chunked into ONE Chunked-104a document. This
// is purely additive — nothing about the 1.31 disk layout or validation rules
// changes.

function bejsonCoreChunkingCreateMfdb132Package(
  mfdbRootDir,
  dbName,
  extensions = null,
  excludeDirs = null,
  packageVersion = null,
  priorPackageDoc = null
) {
  const rootPath = path.resolve(mfdbRootDir);
  const manifestPath = path.join(rootPath, MFDB_MANIFEST_FILENAME);
  if (!fs.existsSync(manifestPath) || !fs.statSync(manifestPath).isFile()) {
    throw new Error(
      `No ${MFDB_MANIFEST_FILENAME} found at root of ${rootPath} — cannot ` +
        `package a directory that isn't a valid MFDB layout.`
    );
  }

  const resolvedPackageVersion =
    packageVersion || bejsonCoreChunkingBumpPackageVersion(priorPackageDoc);

  const doc = bejsonCoreChunkingCreateChunked104(
    rootPath,
    MFDB_CHUNK_SCHEMA_VERSION,
    extensions !== null ? extensions : DEFAULT_EXTENSIONS,
    excludeDirs,
    resolvedPackageVersion
  );

  // Overwrite the inherited Chunked-104a schema identity — see the PY
  // counterpart for rationale (Package_Format alone isn't authoritative for
  // discovery; Schema_Name/Records_Type must say MFDB-132 too).
  doc.Schema_Name = "MFDB-132";
  doc.Records_Type = ["MFDB-132"];
  doc.MFDB_Version = MFDB_CHUNK_SCHEMA_VERSION;
  doc.DB_Name = dbName;
  doc.Package_Format = "MFDB-Chunked-104a";
  return doc;
}

function bejsonCoreChunkingIsMfdb132Package(doc) {
  // Thin wrapper — validation logic lives in
  // lib_bejson_Core_mfdb_validator.mfdb_validator_is_mfdb132_package().
  return mfdb_validator_is_mfdb132_package(doc);
}

function bejsonCoreChunkingValidateMfdb132Package(doc) {
  // Thin wrapper — validation logic lives in
  // lib_bejson_Core_mfdb_validator.mfdb_validator_validate_mfdb132_package().
  return mfdb_validator_validate_mfdb132_package(doc);
}

function bejsonCoreChunkingUnchunkMfdb132Package(doc, outputDir) {
  const validation = bejsonCoreChunkingValidateMfdb132Package(doc);
  const count = bejsonCoreChunkingUnchunkChunked104(doc, outputDir);

  const outRoot = path.resolve(outputDir);
  const manifestRestored = fs.existsSync(path.join(outRoot, MFDB_MANIFEST_FILENAME));
  if (!manifestRestored) {
    validation.valid = false;
    validation.errors.push(
      `Manifest ${MFDB_MANIFEST_FILENAME} was not found on disk after unchunking.`
    );
  }

  return [count, validation];
}

// ── MFDB-in-chunk deep detection (validator extension) ──────────────────────
// Relocated to lib_bejson_Core_mfdb_validator.js (2026-07-13). Kept here as a
// thin wrapper for callers already importing it from the chunking library.

function bejsonCoreChunkingDetectMfdbInChunk(doc) {
  // Thin wrapper — validation logic lives in
  // lib_bejson_Core_mfdb_validator.mfdb_validator_detect_mfdb_in_chunk().
  return mfdb_validator_detect_mfdb_in_chunk(doc);
}

// ── MFDB 1.32 session-based mount ─────────────────────────────────────────────
// Mirrors MFDBArchive (131) exactly, substituting unchunk/rechunk for
// unzip/rezip. Node.js only — uses fs and crypto. Lock file is .mfdb132_lock.
// Is_Mounted and Mount_Path top-level headers on the chunk doc are live
// mount-state markers.

const LOCK_FILE_132 = ".mfdb132_lock";

function _calculateChunkHash(filePath) {
  const data = fs.readFileSync(filePath);
  return crypto.createHash("sha256").update(data).digest("hex");
}

function _setChunkDocHeaders(chunkDocPath, isMounted, mountPath) {
  try {
    const doc = JSON.parse(fs.readFileSync(chunkDocPath, "utf8"));
    doc["Session_Is_Mounted"] = !!isMounted;
    delete doc["Is_Mounted"]; // migrate any doc still on the old key
    doc["Mount_Path"] = mountPath;
    fs.writeFileSync(chunkDocPath, JSON.stringify(doc, null, 2), "utf8");
  } catch (e) {
    console.warn(`[MFDB132] Could not update chunk doc headers: ${e.message}`);
  }
}

class MFDB132Archive {
  /**
   * mount — unchunk an MFDB132 package to a workspace and write a session lock.
   * sticky=true reuses an existing valid workspace when the chunk doc hash matches.
   * Returns the absolute path to the restored manifest.
   */
  static mount(chunkDocPath, targetDir, { force = false, sticky = true } = {}) {
    const chunkAbs = path.resolve(chunkDocPath);
    if (!fs.existsSync(chunkAbs)) {
      throw new Error(`Chunk doc not found: ${chunkDocPath}`);
    }

    const lockFile    = path.join(targetDir, LOCK_FILE_132);
    const manifestOut = path.join(targetDir, MFDB_MANIFEST_FILENAME);
    const currentHash = _calculateChunkHash(chunkAbs);

    // Sticky reuse
    if (sticky && fs.existsSync(lockFile) && fs.existsSync(manifestOut)) {
      try {
        const lock = JSON.parse(fs.readFileSync(lockFile, "utf8"));
        if (lock.original_hash === currentHash) {
          const { mfdb_validator_validate_database } = require("./lib_bejson_Core_mfdb_validator.js");
          if (mfdb_validator_validate_database(manifestOut)) {
            return path.resolve(manifestOut);
          }
        }
      } catch (_) { /* fall through to full re-unchunk */ }
    }

    // Ownership check
    if (fs.existsSync(lockFile) && !force) {
      const lock = JSON.parse(fs.readFileSync(lockFile, "utf8"));
      if (lock.pid !== process.pid) {
        throw new Error(
          `Workspace ${targetDir} is locked by PID ${lock.pid}. Pass force=true to override.`
        );
      }
    }

    // Clear workspace, unchunk
    if (fs.existsSync(targetDir)) {
      fs.rmSync(targetDir, { recursive: true, force: true });
    }
    fs.mkdirSync(targetDir, { recursive: true });

    const doc   = JSON.parse(fs.readFileSync(chunkAbs, "utf8"));
    const count = bejsonCoreChunkingUnchunkChunked104(doc, targetDir);
    if (count === 0) {
      fs.rmSync(targetDir, { recursive: true, force: true });
      throw new Error("Unchunk produced zero files — chunk doc may be empty.");
    }
    if (!fs.existsSync(manifestOut)) {
      fs.rmSync(targetDir, { recursive: true, force: true });
      throw new Error("Invalid MFDB132 package: 104a.mfdb.bejson missing after unchunk.");
    }

    // Write session lock
    const lockData = {
      pid:             process.pid,
      mounted_at:      new Date().toISOString(),
      original_hash:   currentHash,
      chunk_doc_path:  chunkAbs,
      workspace_dir:   path.resolve(targetDir),
    };
    fs.writeFileSync(lockFile, JSON.stringify(lockData, null, 2), "utf8");

    // Activate Is_Mounted / Mount_Path headers
    _setChunkDocHeaders(chunkAbs, true, path.resolve(targetDir));

    return path.resolve(manifestOut);
  }

  /**
   * commit — re-chunk the workspace back into an MFDB132 package atomically.
   * Runs full MFDB validation as a pre-write gate before touching disk.
   */
  static commit(mountDir, outputPath = null, validate = true) {
    const lockFile    = path.join(mountDir, LOCK_FILE_132);
    const manifestOut = path.join(mountDir, MFDB_MANIFEST_FILENAME);

    if (!fs.existsSync(lockFile)) {
      throw new Error(`No active 132 mount session in ${mountDir}`);
    }
    const lockData = JSON.parse(fs.readFileSync(lockFile, "utf8"));

    // Pre-write validation gate
    if (validate) {
      if (!fs.existsSync(manifestOut)) {
        throw new Error("Commit rejected: manifest missing in workspace.");
      }
      const { mfdb_validator_validate_database } = require("./lib_bejson_Core_mfdb_validator.js");
      try { mfdb_validator_validate_database(manifestOut); }
      catch (e) { throw new Error(`Commit rejected: validation failed — ${e.message}`); }
    }

    const destPath = outputPath || lockData.chunk_doc_path;
    if (!destPath) throw new Error("Destination chunk doc path unknown.");

    const manifestDoc = JSON.parse(fs.readFileSync(manifestOut, "utf8"));
    const dbName      = manifestDoc.DB_Name || "";

    // Rechunk to temp, atomic swap
    const tempChunk = destPath + ".tmp." + Date.now();
    try {
      const newDoc = bejsonCoreChunkingCreateMfdb132Package(mountDir, dbName);
      fs.writeFileSync(tempChunk, JSON.stringify(newDoc, null, 2), "utf8");
      fs.renameSync(tempChunk, destPath);
    } catch (e) {
      if (fs.existsSync(tempChunk)) fs.unlinkSync(tempChunk);
      throw new Error(`Commit failed during rechunk: ${e.message}`);
    }

    // Update lock hash; keep Is_Mounted=True until explicit unmount
    const newHash = _calculateChunkHash(destPath);
    lockData.original_hash = newHash;
    fs.writeFileSync(lockFile, JSON.stringify(lockData, null, 2), "utf8");
    _setChunkDocHeaders(destPath, true, path.resolve(mountDir));

    return destPath;
  }

  /**
   * resurrect_file — re-unchunk a single file from the chunk doc into the workspace.
   * Used for recovery when an entity file is missing or corrupted.
   */
  static resurrect_file(mountDir, relativePath) {
    const lockFile = path.join(mountDir, LOCK_FILE_132);
    if (!fs.existsSync(lockFile)) return false;

    const lockData     = JSON.parse(fs.readFileSync(lockFile, "utf8"));
    const chunkDocPath = lockData.chunk_doc_path;
    if (!chunkDocPath || !fs.existsSync(chunkDocPath)) return false;

    try {
      const doc = JSON.parse(fs.readFileSync(chunkDocPath, "utf8"));
      const fields = doc.Fields || CHUNKED_104_FIELDS;
      const fm = {};
      fields.forEach((f, i) => { fm[f.name] = i; });
      const targetRel = path.normalize(relativePath);

      for (const row of (doc.Values || [])) {
        if (path.normalize(row[fm["Relative_Path"]]) === targetRel) {
          const targetFile = path.join(mountDir, row[fm["Relative_Path"]]);
          fs.mkdirSync(path.dirname(targetFile), { recursive: true });
          const isBinary = row[fm["Is_Binary"]];
          const content  = row[fm["File_Content"]];
          if (isBinary) {
            fs.writeFileSync(targetFile, Buffer.from(content, "base64"));
          } else {
            fs.writeFileSync(targetFile, content, "utf8");
          }
          return true;
        }
      }
    } catch (e) {
      console.warn(`[MFDB132] resurrect_file failed for ${relativePath}: ${e.message}`);
    }
    return false;
  }

  /**
   * unmount — release the 132 session lock and clear Is_Mounted / Mount_Path
   * headers on the chunk doc. Optionally deletes the workspace directory.
   */
  static unmount(mountDir, cleanup = true) {
    const lockFile = path.join(mountDir, LOCK_FILE_132);
    if (fs.existsSync(lockFile)) {
      try {
        const lockData = JSON.parse(fs.readFileSync(lockFile, "utf8"));
        const cdp = lockData.chunk_doc_path;
        if (cdp && fs.existsSync(cdp)) _setChunkDocHeaders(cdp, false, "");
      } catch (_e) {
        console.debug(`[Chunking] Could not clear chunk-doc headers during lock release: ${_e.message}`);
      }
      fs.unlinkSync(lockFile);
    }
    if (cleanup && fs.existsSync(mountDir)) {
      fs.rmSync(mountDir, { recursive: true, force: true });
    }
  }
}

// ── MFDB rolling multi-version schema (unify layer) ─────────────────────────
// Everything above (bejsonCoreChunking*) is the Chunked-104a / MFDB-132 flat
// one-shot schema. Everything below (bejsonCoreChunkingMfdb*) is a distinct
// function set, same file/family, for mfdb_chunker.py's rolling
// multi-version layout (manifest + entity split, one entity file holds ALL
// versions as rows). See the PY sibling file's comment block for full
// rationale -- ported 1:1.

const BEJSON_CORE_CHUNKING_MFDB_SCHEMA_MANIFEST = "mfdb_manifest";
const BEJSON_CORE_CHUNKING_MFDB_SCHEMA_ENTITY = "mfdb_entity";
const BEJSON_CORE_CHUNKING_MFDB_SCHEMA_ENTITY_LEGACY = "mfdb_entity_legacy";
const BEJSON_CORE_CHUNKING_MFDB_SCHEMA_CHUNKED_104A = "chunked_104a";
const BEJSON_CORE_CHUNKING_MFDB_SCHEMA_UNKNOWN = "unknown";

const _MFDB_ENTITY_FIELD_NAMES = new Set([
  "version", "File_Name", "File_Extension", "Relative_Path",
  "File_Content", "File_Hash", "Is_Binary", "Is_Mounted",
]);
const _MFDB_ENTITY_LEGACY_FIELD_NAMES = new Set([
  "version", "file_path", "file_name", "content", "is_binary", "is_base64",
]);
const _CHUNKED_104A_FIELD_NAMES = new Set(CHUNKED_104_FIELDS.map((f) => f.name));

function _setsEqual(a, b) {
  if (a.size !== b.size) return false;
  for (const x of a) if (!b.has(x)) return false;
  return true;
}

function bejsonCoreChunkingMfdbGetFieldMap(doc) {
  const fields = doc.Fields || [];
  const map = {};
  fields.forEach((f, i) => { map[f.name] = i; });
  return map;
}

function bejsonCoreChunkingMfdbDetectSchema(doc) {
  const recordsType = doc.Records_Type;
  const fieldNames = new Set((doc.Fields || []).map((f) => f.name));

  if ((Array.isArray(recordsType) && recordsType.length === 1 && recordsType[0] === "MFDB-132") ||
      doc.Schema_Name === "MFDB-132") {
    return BEJSON_CORE_CHUNKING_MFDB_SCHEMA_CHUNKED_104A;
  }
  if (Array.isArray(recordsType) && recordsType.length === 1 && recordsType[0] === "Chunked" &&
      _setsEqual(fieldNames, _CHUNKED_104A_FIELD_NAMES)) {
    return BEJSON_CORE_CHUNKING_MFDB_SCHEMA_CHUNKED_104A;
  }
  if (_setsEqual(fieldNames, _MFDB_ENTITY_FIELD_NAMES)) {
    return BEJSON_CORE_CHUNKING_MFDB_SCHEMA_ENTITY;
  }
  if (_setsEqual(fieldNames, _MFDB_ENTITY_LEGACY_FIELD_NAMES)) {
    return BEJSON_CORE_CHUNKING_MFDB_SCHEMA_ENTITY_LEGACY;
  }
  if (Array.isArray(recordsType) && recordsType.length === 1 && recordsType[0] === "mfdb" &&
      fieldNames.has("entity_name") && fieldNames.has("file_path")) {
    return BEJSON_CORE_CHUNKING_MFDB_SCHEMA_MANIFEST;
  }
  return BEJSON_CORE_CHUNKING_MFDB_SCHEMA_UNKNOWN;
}

function bejsonCoreChunkingMfdbCheckVersion(doc, knownVersions = ["1.31", "1.32", "1.38"]) {
  const mfdbVersion = doc.MFDB_Version;
  if (mfdbVersion === undefined || mfdbVersion === null) return null;
  if (!knownVersions.includes(String(mfdbVersion))) {
    return `MFDB_Version '${mfdbVersion}' not in known set [${knownVersions.join(", ")}] -- ` +
      `proceeding on structural detection anyway, but this is worth a look.`;
  }
  return null;
}

function bejsonCoreChunkingMfdbUnchunk(doc, outputDir, version = null, manifestDir = null) {
  const schema = bejsonCoreChunkingMfdbDetectSchema(doc);
  const warning = bejsonCoreChunkingMfdbCheckVersion(doc);
  const outRoot = path.resolve(outputDir);

  if (schema === BEJSON_CORE_CHUNKING_MFDB_SCHEMA_CHUNKED_104A) {
    const count = bejsonCoreChunkingUnchunkChunked104(doc, outputDir);
    return { ok: true, message: `Restored ${count} file(s) from Chunked-104a/MFDB-132 bundle.`,
      schema, warning, out_dir: outRoot, file_count: count };
  }

  if (schema === BEJSON_CORE_CHUNKING_MFDB_SCHEMA_MANIFEST) {
    if (manifestDir === null || !version) {
      return { ok: false, message: "MFDB manifest requires manifestDir and version.", schema, warning };
    }
    const fm = bejsonCoreChunkingMfdbGetFieldMap(doc);
    const row = (doc.Values || []).find((r) => r[fm.entity_name] === version);
    if (!row) {
      return { ok: false, message: `Version '${version}' not found in manifest.`, schema, warning };
    }
    const entityPath = path.join(manifestDir, row[fm.file_path]);
    if (!fs.existsSync(entityPath)) {
      return { ok: false, message: `Entity file missing: ${entityPath}`, schema, warning };
    }
    const entityDoc = JSON.parse(fs.readFileSync(entityPath, "utf-8"));
    return bejsonCoreChunkingMfdbUnchunk(entityDoc, outputDir, version, null);
  }

  if (schema === BEJSON_CORE_CHUNKING_MFDB_SCHEMA_ENTITY) {
    if (!version) {
      return { ok: false, message: "MFDB entity requires version.", schema, warning };
    }
    const fm = bejsonCoreChunkingMfdbGetFieldMap(doc);
    const rows = (doc.Values || []).filter((r) => r[fm.version] === version);
    if (rows.length === 0) {
      return { ok: false, message: `No rows for version '${version}'.`, schema, warning };
    }
    fs.mkdirSync(outRoot, { recursive: true });
    let count = 0;
    for (const row of rows) {
      const relPath = row[fm.Relative_Path];
      if (!relPath) continue;
      const target = path.join(outRoot, relPath);
      fs.mkdirSync(path.dirname(target), { recursive: true });
      if (row[fm.Is_Binary]) {
        fs.writeFileSync(target, Buffer.from(row[fm.File_Content] || "", "base64"));
      } else {
        fs.writeFileSync(target, row[fm.File_Content] || "", "utf-8");
      }
      count += 1;
    }
    return { ok: true, message: `Restored ${count} file(s) for version '${version}'.`,
      schema, warning, out_dir: outRoot, file_count: count };
  }

  if (schema === BEJSON_CORE_CHUNKING_MFDB_SCHEMA_ENTITY_LEGACY) {
    return { ok: false, message: "Legacy MFDB entity schema -- no migration path by design. " +
      "Re-chunk the source project with current tooling first.", schema, warning };
  }

  return { ok: false, message: "Could not identify chunk schema (structural detection failed).",
    schema: BEJSON_CORE_CHUNKING_MFDB_SCHEMA_UNKNOWN, warning };
}

// ---------------------------------------------------------------------------
// Exports (CommonJS + browser global) — matches sibling Core file convention.
// ---------------------------------------------------------------------------

const exports_ = {
  DEFAULT_EXTENSIONS,
  DEFAULT_EXCLUDES,
  CHUNKED_104_FIELDS,
  MFDB_MANIFEST_FILENAME,
  MFDB_CHUNK_SCHEMA_VERSION,
  LOCK_FILE_132,
  bejsonCoreChunkingGetTimestamp,
  bejsonCoreChunkingIsBinary,
  bejsonCoreChunkingHashFileBytes,
  bejsonCoreChunkingBumpPackageVersion,
  bejsonCoreChunkingCreateChunked104,
  bejsonCoreChunkingUnchunkChunked104,
  bejsonCoreChunkingCreateMfdb132Package,
  bejsonCoreChunkingIsMfdb132Package,
  bejsonCoreChunkingValidateMfdb132Package,
  bejsonCoreChunkingUnchunkMfdb132Package,
  bejsonCoreChunkingDetectMfdbInChunk,
  bejsonCoreChunkingMfdbGetFieldMap,
  bejsonCoreChunkingMfdbDetectSchema,
  bejsonCoreChunkingMfdbCheckVersion,
  bejsonCoreChunkingMfdbUnchunk,
  MFDB132Archive,
};

if (typeof module !== 'undefined' && module.exports) {
  module.exports = exports_;
} else {
  window.BEJSON_CORE_CHUNKING = exports_;
}
