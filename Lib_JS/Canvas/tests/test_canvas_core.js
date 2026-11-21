/**
 * Test Suite:      test_canvas_core.js
 * Family:          Canvas
 * Module Tested:   lib_bejson_canvas_core.js
 * Description:     Unit and round-trip verification for Universal Canvas Core Store,
 *                  MFDB-132 packaging, 104a manifest generation, and collision geometry.
 * Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
 * License:         PolyForm Noncommercial 1.0.0
 */
'use strict';

const assert = require('assert');
const path = require('path');
const core = require('../lib_bejson_canvas_core.js');

console.log('--- Starting Universal Canvas Core Unit Test Suite ---');

// 1. Module Exports & Constants Verification
assert.strictEqual(core.VERSION, '1.0.0');
assert.strictEqual(core.RELEASE_VERSION, 300);
assert.strictEqual(core.BEHTML_LANES, 8);
assert.strictEqual(core.BEHTML_RY, 32);
assert.strictEqual(core.MFDB_MANIFEST_FILENAME, '104a.mfdb.bejson');
assert.strictEqual(core.MFDB_CHUNK_SCHEMA_VERSION, '1.32');
assert(Array.isArray(core.CHUNKED_104_FIELDS));
assert(Array.isArray(core.MFDB_MANIFEST_FIELDS));
assert(Array.isArray(core.CANVAS_META_FIELDS));
assert(Array.isArray(core.OBJECT_ENTITY_FIELDS));
console.log('✓ Module exports and constant assertions passed.');

// 2. Utility Functions Verification
assert.strictEqual(core.sanitizeDbName('  My Test Canvas !@# '), 'My_Test_Canvas');
assert.strictEqual(core.sanitizeDbName(''), 'untitled_canvas');
assert.strictEqual(core.makeEntityName('Square', 1), 'obj_square_001');
assert.strictEqual(core.makeEntityName('flow_node', 42), 'obj_flow_node_042');

const uuid = core.generateUuidV4();
assert.strictEqual(typeof uuid, 'string');
assert.strictEqual(uuid.length, 36);

const hash = core.sha256Hex('test content');
assert.strictEqual(typeof hash, 'string');
assert.strictEqual(hash.length, 64);
console.log('✓ Utility functions passed.');

// 3. Collision & Geometry Verification
const shapes = [{ id: 1, cx: 100, cy: 100, size: 50 }];

assert.strictEqual(core.hasOverlap(shapes, 120, 100, 50, -1), true);
assert.strictEqual(core.hasOverlap(shapes, 200, 200, 50, -1), false);

const mtv = core.resolveMTV(shapes, 120, 100, 50, 800, 600, -1);
assert(mtv !== null);
assert(typeof mtv.cx === 'number');
assert(typeof mtv.cy === 'number');
assert.strictEqual(core.hasOverlap(shapes, mtv.cx, mtv.cy, 50, -1), false);

const clamped = core.clampToStage(20, 20, 100, 800, 600);
assert.strictEqual(clamped.cx, 50); // half size
assert.strictEqual(clamped.cy, 50);
console.log('✓ Collision & geometry assertions passed.');

// 4. Canvas Store Lifecycle
const store = core.createCanvasStore();
assert.strictEqual(store.state.isInitialized, false);
assert.strictEqual(store.state.shapes.length, 0);

store.createNewFile('flow_db', 1280, 720);
assert.strictEqual(store.state.isInitialized, true);
assert.strictEqual(store.state.dbName, 'flow_db');
assert.strictEqual(store.state.stageWidth, 1280);
assert.strictEqual(store.state.stageHeight, 720);

// 5. Object Operations (Add, Move, Select, Delete)
const obj1 = store.addObject('square', 100, 100, 64, 1280, 720);
assert.strictEqual(obj1.id, 1);
assert.strictEqual(obj1.entityName, 'obj_square_001');
assert.strictEqual(store.state.shapes.length, 1);
assert.strictEqual(store.state.selectedShapeId, 1);

const obj2 = store.addObject('square', 110, 100, 64, 1280, 720);
assert.strictEqual(obj2.id, 2);
assert.strictEqual(store.state.shapes.length, 2);
// Check that collision displacement occurred so obj2 is not overlapping obj1
assert.strictEqual(core.hasOverlap([obj1], obj2.cx, obj2.cy, obj2.size, -1), false);

// Move object
const moved = store.moveObject(obj1.id, 300, 300, 1280, 720);
assert.strictEqual(moved.cx, 300);
assert.strictEqual(moved.cy, 300);

// Selection
store.selectObject(null);
assert.strictEqual(store.state.selectedShapeId, null);
store.selectObject(obj2.id);
assert.strictEqual(store.state.selectedShapeId, obj2.id);

// Undo / Redo
store.deleteSelected();
assert.strictEqual(store.state.shapes.length, 1);
assert.strictEqual(store.state.shapes[0].id, 1);

store.undo();
assert.strictEqual(store.state.shapes.length, 2);

store.redo();
assert.strictEqual(store.state.shapes.length, 1);
console.log('✓ Canvas Store CRUD & undo/redo passed.');

// 6. MFDB-132 Packaging and Manifest Generation
const metaDoc = store.buildCanvasMetaEntityDoc();
assert.strictEqual(metaDoc.Format, 'BEJSON');
assert.strictEqual(metaDoc.Format_Version, '104');
assert.strictEqual(metaDoc.Values[0][0], 'flow_db');

const objDoc = store.buildObjectEntityDoc(store.state.shapes[0]);
assert.strictEqual(objDoc.Format, 'BEJSON');
assert.strictEqual(objDoc.Format_Version, '104');
assert.strictEqual(objDoc.Values[0][1], 1); // obj_id
assert.strictEqual(objDoc.Values[0][2], 'obj_square_001');

const manifest = store.buildMfdbManifest();
assert.strictEqual(manifest.Format, 'BEJSON');
assert.strictEqual(manifest.Format_Version, '104a');
assert.strictEqual(manifest.Values.length, 2); // meta_canvas + obj_square_001

const pkg = store.buildMfdb132Package();
assert.strictEqual(pkg.Format, 'BEJSON');
assert.strictEqual(pkg.Format_Version, '104a');
assert.strictEqual(pkg.Values.length, 3); // 104a.mfdb.bejson + meta + obj

const valRes = store.validateMfdb132(pkg);
assert.strictEqual(valRes.valid, true);
assert.strictEqual(valRes.errors.length, 0);
console.log('✓ MFDB-132 schema packaging and validation passed.');

// 7. Full Import Round-Trip
const storeImported = core.createCanvasStore();
const importRes = storeImported.importMfdb132(pkg);
assert.strictEqual(importRes.ok, true);
assert.strictEqual(importRes.dbName, 'flow_db');
assert.strictEqual(importRes.objectCount, 1);
assert.strictEqual(storeImported.state.shapes.length, 1);
assert.strictEqual(storeImported.state.shapes[0].id, 1);
assert.strictEqual(storeImported.state.shapes[0].cx, 300);
assert.strictEqual(storeImported.state.shapes[0].cy, 300);
console.log('✓ MFDB-132 import round-trip passed.');

console.log('--- All Universal Canvas Core Tests Passed Successfully! ---');
