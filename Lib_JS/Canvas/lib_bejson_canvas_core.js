/**
 * Library:         lib_bejson_canvas_core.js
 * Family:          Canvas / Core
 * Module Purpose:  Backend engine for BEHTML Experimental Flow.
 *                  - Separates canvas state, collision geometry, and persistence from DOM UI.
 *                  - Maps every canvas object to its own dense BEJSON 104 MFDB entity.
 *                  - Maintains a live BEJSON schema (MFDB-132 package, 104a manifest, and live position map).
 *                  - Supports single-file MFDB-132 import/export validated via Core JS libraries.
 * Version:         1.0.0
 * Release_Version: 300
 * Format_Creator:  Elton Boehnen
 */

(function () {
  'use strict';

  const BEHTML_LANES = 8;
  const BEHTML_RY = 32;
  const EPS = 0.001;
  const MFDB_MANIFEST_FILENAME = '104a.mfdb.bejson';
  const MFDB_CHUNK_SCHEMA_VERSION = '1.32';
  const FORMAT_CREATOR = 'Elton Boehnen';

  /* ---------------------------------------------------------------------------
     Canonical BEJSON Field Definitions (POL-002 Primitive-Only, snake_case)
     --------------------------------------------------------------------------- */
  const CHUNKED_104_FIELDS = [
    { name: 'File_Name', type: 'string' },
    { name: 'File_Extension', type: 'string' },
    { name: 'File_Content', type: 'string' },
    { name: 'File_Version', type: 'string' },
    { name: 'File_Hash', type: 'string' },
    { name: 'Relative_Path', type: 'string' },
    { name: 'Is_Binary', type: 'boolean' },
    { name: 'Is_Mounted', type: 'boolean' }
  ];

  const MFDB_MANIFEST_FIELDS = [
    { name: 'entity_name', type: 'string' },
    { name: 'file_path', type: 'string' },
    { name: 'record_count', type: 'integer' },
    { name: 'schema_version', type: 'string' }
  ];

  const CANVAS_META_FIELDS = [
    { name: 'db_name', type: 'string' },
    { name: 'behtml_lanes', type: 'integer' },
    { name: 'behtml_ry', type: 'integer' },
    { name: 'stage_width', type: 'integer' },
    { name: 'stage_height', type: 'integer' },
    { name: 'show_grid', type: 'boolean' },
    { name: 'next_id', type: 'integer' },
    { name: 'updated_at', type: 'string' }
  ];

  const OBJECT_ENTITY_FIELDS = [
    { name: 'obj_uuid', type: 'string' },
    { name: 'obj_id', type: 'integer' },
    { name: 'obj_entity_name', type: 'string' },
    { name: 'obj_type', type: 'string' },
    { name: 'obj_label', type: 'string' },
    { name: 'pos_cx', type: 'number' },
    { name: 'pos_cy', type: 'number' },
    { name: 'pos_x', type: 'number' },
    { name: 'pos_y', type: 'number' },
    { name: 'dim_size', type: 'number' },
    { name: 'dim_width', type: 'number' },
    { name: 'dim_height', type: 'number' },
    { name: 'grid_lane', type: 'integer' },
    { name: 'grid_row', type: 'integer' },
    { name: 'z_index', type: 'integer' },
    { name: 'obj_updated_at', type: 'string' }
  ];

  /* ---------------------------------------------------------------------------
     Utility Helpers: Timestamp, UUIDv4, Field Map, Sync Pure-JS SHA-256
     --------------------------------------------------------------------------- */
  function getIsoTimestamp() {
    return new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');
  }

  function generateUuidV4() {
    if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
      return crypto.randomUUID();
    }
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
      const r = (Math.random() * 16) | 0;
      const v = c === 'x' ? r : (r & 0x3) | 0x8;
      return v.toString(16);
    });
  }

  function sanitizeDbName(rawName) {
    const cleaned = String(rawName || '')
      .trim()
      .replace(/[^a-zA-Z0-9_-]+/g, '_')
      .replace(/^_+|_+$/g, '');
    return cleaned || 'untitled_canvas';
  }

  function makeEntityName(type, id) {
    const safeType = String(type || 'obj').toLowerCase().replace(/[^a-z0-9]+/g, '_');
    const padded = String(id).padStart(3, '0');
    return `obj_${safeType}_${padded}`;
  }

  function roundCoord(n) {
    return Math.round(Number(n || 0) * 100) / 100;
  }

  function getFieldMap(doc) {
    const core = (typeof window !== 'undefined' && window.BEJSON) ? window.BEJSON : null;
    if (core && typeof core.bejson_core_get_field_map === 'function') {
      try {
        return core.bejson_core_get_field_map(doc);
      } catch (_) {
        // fallback below
      }
    }
    const fm = {};
    const fields = (doc && Array.isArray(doc.Fields)) ? doc.Fields : [];
    fields.forEach(function (f, i) {
      if (f && f.name) fm[f.name] = i;
    });
    return fm;
  }

  /**
   * Synchronous pure-JS SHA-256 over UTF-8 string.
   * Works identically on file://, http://, https://, and Node.js without async SubtleCrypto restrictions.
   */
  const SHA256_K = [
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2
  ];

  function sha256Hex(str) {
    const bytes = new TextEncoder().encode(String(str));
    const bitLen = bytes.length * 8;
    const paddedLen = Math.ceil((bytes.length + 9) / 64) * 64;
    const buf = new Uint8Array(paddedLen);
    buf.set(bytes);
    buf[bytes.length] = 0x80;
    const view = new DataView(buf.buffer);
    view.setUint32(paddedLen - 8, Math.floor(bitLen / 0x100000000), false);
    view.setUint32(paddedLen - 4, bitLen >>> 0, false);

    let h0 = 0x6a09e667, h1 = 0xbb67ae85, h2 = 0x3c6ef372, h3 = 0xa54ff53a;
    let h4 = 0x510e527f, h5 = 0x9b05688c, h6 = 0x1f83d9ab, h7 = 0x5be0cd19;
    const w = new Uint32Array(64);

    for (let offset = 0; offset < paddedLen; offset += 64) {
      for (let i = 0; i < 16; i++) {
        w[i] = view.getUint32(offset + i * 4, false);
      }
      for (let i = 16; i < 64; i++) {
        const s0 = ((w[i - 15] >>> 7) | (w[i - 15] << 25)) ^ ((w[i - 15] >>> 18) | (w[i - 15] << 14)) ^ (w[i - 15] >>> 3);
        const s1 = ((w[i - 2] >>> 17) | (w[i - 2] << 15)) ^ ((w[i - 2] >>> 19) | (w[i - 2] << 13)) ^ (w[i - 2] >>> 10);
        w[i] = (w[i - 16] + s0 + w[i - 7] + s1) >>> 0;
      }
      let a = h0, b = h1, c = h2, d = h3, e = h4, f = h5, g = h6, h = h7;
      for (let i = 0; i < 64; i++) {
        const S1 = ((e >>> 6) | (e << 26)) ^ ((e >>> 11) | (e << 21)) ^ ((e >>> 25) | (e << 7));
        const ch = (e & f) ^ (~e & g);
        const temp1 = (h + S1 + ch + SHA256_K[i] + w[i]) >>> 0;
        const S0 = ((a >>> 2) | (a << 30)) ^ ((a >>> 13) | (a << 19)) ^ ((a >>> 22) | (a << 10));
        const maj = (a & b) ^ (a & c) ^ (b & c);
        const temp2 = (S0 + maj) >>> 0;
        h = g; g = f; f = e; e = (d + temp1) >>> 0;
        d = c; c = b; b = a; a = (temp1 + temp2) >>> 0;
      }
      h0 = (h0 + a) >>> 0; h1 = (h1 + b) >>> 0; h2 = (h2 + c) >>> 0; h3 = (h3 + d) >>> 0;
      h4 = (h4 + e) >>> 0; h5 = (h5 + f) >>> 0; h6 = (h6 + g) >>> 0; h7 = (h7 + h) >>> 0;
    }

    return [h0, h1, h2, h3, h4, h5, h6, h7]
      .map(function (v) { return v.toString(16).padStart(8, '0'); })
      .join('');
  }

  /* ---------------------------------------------------------------------------
     Collision Prevention Engine (Flush Edge-to-Edge Allowed)
     --------------------------------------------------------------------------- */
  function clampToStage(cx, cy, size, stageW, stageH) {
    const half = size / 2;
    const maxW = Math.max(size, stageW || size);
    const maxH = Math.max(size, stageH || size);
    return {
      cx: Math.max(half, Math.min(maxW - half, cx)),
      cy: Math.max(half, Math.min(maxH - half, cy))
    };
  }

  function hasOverlap(shapes, cx, cy, size, ignoreId) {
    for (let i = 0; i < shapes.length; i++) {
      const other = shapes[i];
      if (other.id === ignoreId) continue;
      const minDist = (size + other.size) / 2;
      const overlapX = minDist - Math.abs(cx - other.cx);
      const overlapY = minDist - Math.abs(cy - other.cy);
      if (overlapX > EPS && overlapY > EPS) {
        return true;
      }
    }
    return false;
  }

  function resolveMTV(shapes, targetCx, targetCy, size, stageW, stageH, ignoreId, prevCx, prevCy) {
    const pCx = (prevCx !== undefined) ? prevCx : targetCx;
    const pCy = (prevCy !== undefined) ? prevCy : targetCy;
    let pos = clampToStage(targetCx, targetCy, size, stageW, stageH);

    for (let iter = 0; iter < 16; iter++) {
      let moved = false;

      for (let i = 0; i < shapes.length; i++) {
        const other = shapes[i];
        if (other.id === ignoreId) continue;

        const minDist = (size + other.size) / 2;
        const dx = pos.cx - other.cx;
        const dy = pos.cy - other.cy;
        const overlapX = minDist - Math.abs(dx);
        const overlapY = minDist - Math.abs(dy);

        if (overlapX > EPS && overlapY > EPS) {
          if (overlapX < overlapY) {
            const dirX = dx !== 0 ? Math.sign(dx) : (pCx >= other.cx ? 1 : -1);
            pos.cx = other.cx + dirX * minDist;
          } else {
            const dirY = dy !== 0 ? Math.sign(dy) : (pCy >= other.cy ? 1 : -1);
            pos.cy = other.cy + dirY * minDist;
          }
          pos = clampToStage(pos.cx, pos.cy, size, stageW, stageH);
          moved = true;
        }
      }

      if (!moved) break;
    }

    return pos;
  }

  function resolveDragPosition(shapes, targetCx, targetCy, size, stageW, stageH, shapeId, prevCx, prevCy) {
    const direct = resolveMTV(shapes, targetCx, targetCy, size, stageW, stageH, shapeId, prevCx, prevCy);
    if (!hasOverlap(shapes, direct.cx, direct.cy, size, shapeId)) {
      return direct;
    }

    const slideX = resolveMTV(shapes, targetCx, prevCy, size, stageW, stageH, shapeId, prevCx, prevCy);
    if (!hasOverlap(shapes, slideX.cx, slideX.cy, size, shapeId)) {
      return slideX;
    }

    const slideY = resolveMTV(shapes, prevCx, targetCy, size, stageW, stageH, shapeId, prevCx, prevCy);
    if (!hasOverlap(shapes, slideY.cx, slideY.cy, size, shapeId)) {
      return slideY;
    }

    return { cx: prevCx, cy: prevCy };
  }

  function resolveDropPosition(shapes, targetCx, targetCy, size, stageW, stageH) {
    const direct = resolveMTV(shapes, targetCx, targetCy, size, stageW, stageH, null);
    if (!hasOverlap(shapes, direct.cx, direct.cy, size, null)) {
      return direct;
    }

    const step = Math.max(8, size / 4);
    const maxRadius = Math.hypot(stageW || 800, stageH || 600);
    for (let r = step; r <= maxRadius; r += step) {
      for (let a = 0; a < 16; a++) {
        const angle = (a * Math.PI * 2) / 16;
        const cand = resolveMTV(
          shapes,
          targetCx + Math.cos(angle) * r,
          targetCy + Math.sin(angle) * r,
          size,
          stageW,
          stageH,
          null
        );
        if (!hasOverlap(shapes, cand.cx, cand.cy, size, null)) {
          return cand;
        }
      }
    }

    return null;
  }

  /* ---------------------------------------------------------------------------
     CanvasCoreStore — Reactive Backend & Live MFDB-132 Engine
     --------------------------------------------------------------------------- */
  function createCanvasStore() {
    const state = {
      isInitialized: false,
      dbName: 'untitled_canvas',
      packageVersion: 1,
      activeToolId: 'selector',
      activeOptionByTool: {
        selector: 'selector-primary',
        shape: 'square'
      },
      shapes: [],
      selectedShapeId: null,
      nextId: 1,
      showGrid: false,
      stageWidth: 0,
      stageHeight: 0,
      updatedAt: getIsoTimestamp(),
      history: [],
      future: []
    };

    const listeners = new Set();

    function notify(reason) {
      state.updatedAt = getIsoTimestamp();
      listeners.forEach(function (fn) {
        try {
          fn(state, reason || 'update');
        } catch (err) {
          console.error('[lib_bejson_canvas_core] subscriber error:', err);
        }
      });
    }

    function subscribe(fn) {
      listeners.add(fn);
      return function () { listeners.delete(fn); };
    }

    function computeObjectRow(obj) {
      const x = roundCoord(obj.cx - obj.size / 2);
      const y = roundCoord(obj.cy - obj.size / 2);
      const laneW = state.stageWidth > 0 ? state.stageWidth / BEHTML_LANES : Math.max(1, obj.size);
      const lane = Math.max(0, Math.min(BEHTML_LANES - 1, Math.floor(obj.cx / laneW)));
      const row = Math.max(0, Math.floor(y / BEHTML_RY));
      return [
        obj.uuid,
        obj.id,
        obj.entityName,
        obj.type,
        obj.label,
        roundCoord(obj.cx),
        roundCoord(obj.cy),
        x,
        y,
        roundCoord(obj.size),
        roundCoord(obj.size),
        roundCoord(obj.size),
        lane,
        row,
        obj.zIndex || 2,
        obj.updatedAt || state.updatedAt
      ];
    }

    function buildCanvasMetaEntityDoc() {
      return {
        Format: 'BEJSON',
        Format_Version: '104',
        Format_Creator: FORMAT_CREATOR,
        Parent_Hierarchy: '../' + MFDB_MANIFEST_FILENAME,
        Records_Type: ['canvas_meta'],
        Fields: CANVAS_META_FIELDS,
        Values: [[
          state.dbName,
          BEHTML_LANES,
          BEHTML_RY,
          Math.round(state.stageWidth || 0),
          Math.round(state.stageHeight || 0),
          Boolean(state.showGrid),
          state.nextId,
          state.updatedAt
        ]]
      };
    }

    function buildObjectEntityDoc(obj) {
      return {
        Format: 'BEJSON',
        Format_Version: '104',
        Format_Creator: FORMAT_CREATOR,
        Parent_Hierarchy: '../' + MFDB_MANIFEST_FILENAME,
        Records_Type: [obj.entityName],
        Fields: OBJECT_ENTITY_FIELDS,
        Values: [computeObjectRow(obj)]
      };
    }

    function buildMfdbManifest() {
      const values = [
        ['canvas_meta', 'data/canvas_meta.bejson', 1, '1.0.0']
      ];
      state.shapes.forEach(function (obj) {
        values.push([
          obj.entityName,
          'data/' + obj.entityName + '.bejson',
          1,
          '1.0.0'
        ]);
      });

      return {
        Format: 'BEJSON',
        Format_Version: '104a',
        Format_Creator: FORMAT_CREATOR,
        MFDB_Version: '1.31',
        DB_Name: state.dbName,
        Network_Role: 'Master',
        Records_Type: ['mfdb'],
        Fields: MFDB_MANIFEST_FIELDS,
        Values: values
      };
    }

    function buildLivePositionSchema() {
      return {
        Format: 'BEJSON',
        Format_Version: '104a',
        Format_Creator: FORMAT_CREATOR,
        Schema_Name: 'CanvasObjectPositionMap',
        Schema_Version: '1.0.0',
        DB_Name: state.dbName,
        Updated_At: state.updatedAt,
        Records_Type: ['canvas_object'],
        Fields: OBJECT_ENTITY_FIELDS,
        Values: state.shapes.map(computeObjectRow)
      };
    }

    function makeChunkRow(relPath, contentStr) {
      const parts = relPath.split('/');
      const fileName = parts[parts.length - 1];
      const dotIdx = fileName.lastIndexOf('.');
      const ext = dotIdx >= 0 ? fileName.slice(dotIdx) : '';
      return [
        fileName,
        ext,
        contentStr,
        MFDB_CHUNK_SCHEMA_VERSION,
        sha256Hex(contentStr),
        relPath,
        false,
        false
      ];
    }

    function buildMfdb132Package(options) {
      const opts = options || {};
      if (opts.bumpVersion) {
        state.packageVersion += 1;
      }

      const manifestDoc = buildMfdbManifest();
      const metaDoc = buildCanvasMetaEntityDoc();
      const chunkRows = [
        makeChunkRow(MFDB_MANIFEST_FILENAME, JSON.stringify(manifestDoc, null, 2)),
        makeChunkRow('data/canvas_meta.bejson', JSON.stringify(metaDoc, null, 2))
      ];

      state.shapes.forEach(function (obj) {
        const entityDoc = buildObjectEntityDoc(obj);
        chunkRows.push(
          makeChunkRow('data/' + obj.entityName + '.bejson', JSON.stringify(entityDoc, null, 2))
        );
      });

      return {
        Format: 'BEJSON',
        Format_Version: '104a',
        Format_Creator: FORMAT_CREATOR,
        Schema_Name: 'MFDB-132',
        Schema_Version: '1.0.1',
        Schema_Description: 'MFDB-132 single-file package mapping each BEHTML canvas object to an MFDB entity.',
        Chunk_Date: state.updatedAt.slice(0, 10),
        Session_Is_Mounted: false,
        Mount_Path: '',
        Package_Version: String(state.packageVersion),
        MFDB_Version: MFDB_CHUNK_SCHEMA_VERSION,
        DB_Name: state.dbName,
        Package_Format: 'MFDB-Chunked-104a',
        Records_Type: ['MFDB-132'],
        Fields: CHUNKED_104_FIELDS,
        Values: chunkRows
      };
    }

    function validateMfdb132(doc) {
      const errors = [];
      const warnings = [];

      const mfdbVal = (typeof window !== 'undefined' && window.MFDB_VALIDATOR) ? window.MFDB_VALIDATOR : null;
      const bejsonVal = (typeof window !== 'undefined' && window.BEJSON_VALIDATOR) ? window.BEJSON_VALIDATOR : null;

      if (mfdbVal && typeof mfdbVal.mfdb_validator_validate_mfdb132_package === 'function') {
        const res = mfdbVal.mfdb_validator_validate_mfdb132_package(doc);
        if (res && Array.isArray(res.errors)) errors.push.apply(errors, res.errors);
        if (res && Array.isArray(res.warnings)) warnings.push.apply(warnings, res.warnings);
      } else {
        if (!doc || doc.Format_Version !== '104a' || doc.Schema_Name !== 'MFDB-132' || doc.Package_Format !== 'MFDB-Chunked-104a') {
          errors.push('Document is not a valid MFDB-132 package.');
        }
      }

      if (bejsonVal && typeof bejsonVal.bejson_validator_validate_object === 'function') {
        try {
          const bRes = bejsonVal.bejson_validator_validate_object(doc);
          if (bRes && bRes.valid === false && Array.isArray(bRes.errors)) {
            errors.push.apply(errors, bRes.errors);
          }
          if (bRes && Array.isArray(bRes.warnings)) {
            warnings.push.apply(warnings, bRes.warnings);
          }
        } catch (err) {
          errors.push('BEJSON Validator: ' + (err && err.message ? err.message : String(err)));
        }
      }

      return { valid: errors.length === 0, errors: errors, warnings: warnings };
    }

    function createNewFile(rawDbName, stageWidth, stageHeight) {
      state.dbName = sanitizeDbName(rawDbName);
      state.packageVersion = 1;
      state.shapes = [];
      state.selectedShapeId = null;
      state.nextId = 1;
      state.history = [];
      state.future = [];
      state.isInitialized = true;
      if (stageWidth) state.stageWidth = stageWidth;
      if (stageHeight) state.stageHeight = stageHeight;
      notify('file:new');
      return { dbName: state.dbName };
    }

    function importMfdb132(rawInput) {
      let pkg;
      try {
        pkg = (typeof rawInput === 'string') ? JSON.parse(rawInput) : rawInput;
      } catch (err) {
        return { ok: false, errors: ['Invalid JSON syntax: ' + err.message] };
      }

      const check = validateMfdb132(pkg);
      if (!check.valid) {
        return { ok: false, errors: check.errors, warnings: check.warnings };
      }

      const pkgFm = getFieldMap(pkg);
      const relIdx = pkgFm['Relative_Path'];
      const contentIdx = pkgFm['File_Content'];
      if (relIdx === undefined || contentIdx === undefined) {
        return { ok: false, errors: ['MFDB-132 package missing Relative_Path or File_Content fields.'] };
      }

      const fileMap = {};
      (pkg.Values || []).forEach(function (row) {
        const rel = String(row[relIdx] || '').replace(/\\/g, '/');
        fileMap[rel] = row[contentIdx];
      });

      const manifestRaw = fileMap[MFDB_MANIFEST_FILENAME];
      if (!manifestRaw) {
        return { ok: false, errors: ['Missing ' + MFDB_MANIFEST_FILENAME + ' inside MFDB-132 package.'] };
      }

      let manifest;
      try {
        manifest = JSON.parse(manifestRaw);
      } catch (err) {
        return { ok: false, errors: ['Corrupt manifest JSON: ' + err.message] };
      }

      const manFm = getFieldMap(manifest);
      const entNameIdx = manFm['entity_name'];
      const filePathIdx = manFm['file_path'];
      if (entNameIdx === undefined || filePathIdx === undefined) {
        return { ok: false, errors: ['Manifest missing entity_name or file_path columns.'] };
      }

      const loadedShapes = [];
      let loadedShowGrid = state.showGrid;
      let maxId = 0;

      (manifest.Values || []).forEach(function (mRow) {
        const entityName = mRow[entNameIdx];
        const filePath = String(mRow[filePathIdx] || '').replace(/\\/g, '/');
        const entityRaw = fileMap[filePath];
        if (!entityRaw) return;

        let entityDoc;
        try {
          entityDoc = JSON.parse(entityRaw);
        } catch (_) {
          return;
        }

        const eFm = getFieldMap(entityDoc);
        const rows = entityDoc.Values || [];
        if (!rows.length) return;

        if (entityName === 'canvas_meta') {
          const metaRow = rows[0];
          if (eFm['show_grid'] !== undefined) loadedShowGrid = Boolean(metaRow[eFm['show_grid']]);
          if (eFm['next_id'] !== undefined) {
            const parsedNext = Number(metaRow[eFm['next_id']]);
            if (Number.isFinite(parsedNext) && parsedNext > maxId) maxId = parsedNext - 1;
          }
          return;
        }

        rows.forEach(function (r) {
          const id = Number(r[eFm['obj_id']]);
          const safeId = Number.isFinite(id) && id > 0 ? id : (maxId + 1);
          if (safeId > maxId) maxId = safeId;

          const size = Number(r[eFm['dim_size']]);
          const safeSize = Number.isFinite(size) && size > 0 ? size : 96;
          const cx = Number(r[eFm['pos_cx']]);
          const cy = Number(r[eFm['pos_cy']]);

          loadedShapes.push({
            id: safeId,
            uuid: String(r[eFm['obj_uuid']] || generateUuidV4()),
            entityName: String(r[eFm['obj_entity_name']] || entityName || makeEntityName('square', safeId)),
            type: String(r[eFm['obj_type']] || 'square'),
            label: String(r[eFm['obj_label']] || ('Square ' + safeId)),
            cx: Number.isFinite(cx) ? cx : safeSize / 2,
            cy: Number.isFinite(cy) ? cy : safeSize / 2,
            size: safeSize,
            zIndex: Number(r[eFm['z_index']]) || 2,
            updatedAt: String(r[eFm['obj_updated_at']] || getIsoTimestamp())
          });
        });
      });

      state.dbName = sanitizeDbName(pkg.DB_Name || manifest.DB_Name || 'imported_canvas');
      const parsedPkgVer = parseInt(pkg.Package_Version, 10);
      state.packageVersion = Number.isNaN(parsedPkgVer) ? 1 : parsedPkgVer;
      state.shapes = loadedShapes;
      state.selectedShapeId = null;
      state.nextId = maxId + 1;
      state.showGrid = loadedShowGrid;
      state.history = [];
      state.future = [];
      state.isInitialized = true;

      notify('file:import');
      return {
        ok: true,
        dbName: state.dbName,
        objectCount: loadedShapes.length,
        warnings: check.warnings
      };
    }

    /* -------------------------------------------------------------------------
       History & Object CRUD
       ------------------------------------------------------------------------- */
    function snapshot() {
      state.history.push(JSON.stringify(state.shapes));
      if (state.history.length > 50) state.history.shift();
      state.future.length = 0;
    }

    function undo() {
      if (!state.history.length) return false;
      state.future.push(JSON.stringify(state.shapes));
      state.shapes = JSON.parse(state.history.pop());
      if (!state.shapes.some(function (s) { return s.id === state.selectedShapeId; })) {
        state.selectedShapeId = null;
      }
      notify('edit:undo');
      return true;
    }

    function redo() {
      if (!state.future.length) return false;
      state.history.push(JSON.stringify(state.shapes));
      state.shapes = JSON.parse(state.future.pop());
      if (!state.shapes.some(function (s) { return s.id === state.selectedShapeId; })) {
        state.selectedShapeId = null;
      }
      notify('edit:redo');
      return true;
    }

    function addObject(type, targetCx, targetCy, size, stageW, stageH) {
      if (stageW) state.stageWidth = stageW;
      if (stageHeightOrFallback(stageH)) state.stageHeight = stageH;

      const placed = resolveDropPosition(state.shapes, targetCx, targetCy, size, state.stageWidth, state.stageHeight);
      if (!placed) return null;

      snapshot();
      const id = state.nextId++;
      const objType = type || 'square';
      const now = getIsoTimestamp();
      const newObj = {
        id: id,
        uuid: generateUuidV4(),
        entityName: makeEntityName(objType, id),
        type: objType,
        label: objType.charAt(0).toUpperCase() + objType.slice(1) + ' ' + id,
        cx: placed.cx,
        cy: placed.cy,
        size: size,
        zIndex: 2,
        updatedAt: now
      };
      state.shapes.push(newObj);
      state.selectedShapeId = newObj.id;
      notify('object:add');
      return newObj;
    }

    function stageHeightOrFallback(h) {
      return Number.isFinite(h) && h > 0;
    }

    function moveObject(id, targetCx, targetCy, stageW, stageH) {
      const shape = state.shapes.find(function (s) { return s.id === id; });
      if (!shape) return null;
      if (stageW) state.stageWidth = stageW;
      if (stageH) state.stageHeight = stageH;

      const resolved = resolveDragPosition(
        state.shapes,
        targetCx,
        targetCy,
        shape.size,
        state.stageWidth,
        state.stageHeight,
        shape.id,
        shape.cx,
        shape.cy
      );

      shape.cx = resolved.cx;
      shape.cy = resolved.cy;
      shape.updatedAt = getIsoTimestamp();
      notify('object:move');
      return shape;
    }

    function selectObject(id) {
      if (state.selectedShapeId === id) return;
      state.selectedShapeId = id;
      notify('object:select');
    }

    function deleteObject(id) {
      const exists = state.shapes.some(function (s) { return s.id === id; });
      if (!exists) return false;
      snapshot();
      state.shapes = state.shapes.filter(function (s) { return s.id !== id; });
      if (state.selectedShapeId === id) state.selectedShapeId = null;
      notify('object:delete');
      return true;
    }

    function deleteSelected() {
      if (state.selectedShapeId == null) return false;
      return deleteObject(state.selectedShapeId);
    }

    function clearCanvas() {
      if (!state.shapes.length) return false;
      snapshot();
      state.shapes = [];
      state.selectedShapeId = null;
      notify('canvas:clear');
      return true;
    }

    function setStageMetrics(w, h) {
      state.stageWidth = w;
      state.stageHeight = h;
    }

    function setShowGrid(flag) {
      state.showGrid = Boolean(flag);
      notify('view:grid');
    }

    return {
      state: state,
      subscribe: subscribe,
      notify: notify,
      snapshot: snapshot,
      createNewFile: createNewFile,
      importMfdb132: importMfdb132,
      addObject: addObject,
      moveObject: moveObject,
      selectObject: selectObject,
      deleteObject: deleteObject,
      deleteSelected: deleteSelected,
      clearCanvas: clearCanvas,
      undo: undo,
      redo: redo,
      setStageMetrics: setStageMetrics,
      setShowGrid: setShowGrid,
      buildCanvasMetaEntityDoc: buildCanvasMetaEntityDoc,
      buildObjectEntityDoc: buildObjectEntityDoc,
      buildMfdbManifest: buildMfdbManifest,
      buildLivePositionSchema: buildLivePositionSchema,
      buildMfdb132Package: buildMfdb132Package,
      validateMfdb132: validateMfdb132
    };
  }

  const CanvasCoreExports = {
    VERSION: '1.0.0',
    RELEASE_VERSION: 300,
    BEHTML_LANES: BEHTML_LANES,
    BEHTML_RY: BEHTML_RY,
    MFDB_MANIFEST_FILENAME: MFDB_MANIFEST_FILENAME,
    MFDB_CHUNK_SCHEMA_VERSION: MFDB_CHUNK_SCHEMA_VERSION,
    CHUNKED_104_FIELDS: CHUNKED_104_FIELDS,
    MFDB_MANIFEST_FIELDS: MFDB_MANIFEST_FIELDS,
    CANVAS_META_FIELDS: CANVAS_META_FIELDS,
    OBJECT_ENTITY_FIELDS: OBJECT_ENTITY_FIELDS,
    createCanvasStore: createCanvasStore,
    sanitizeDbName: sanitizeDbName,
    makeEntityName: makeEntityName,
    generateUuidV4: generateUuidV4,
    sha256Hex: sha256Hex,
    clampToStage: clampToStage,
    hasOverlap: hasOverlap,
    resolveMTV: resolveMTV,
    resolveDragPosition: resolveDragPosition,
    resolveDropPosition: resolveDropPosition
  };

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = CanvasCoreExports;
  }
  if (typeof window !== 'undefined') {
    window.BEJSON_CANVAS_CORE = CanvasCoreExports;
  }
})();
