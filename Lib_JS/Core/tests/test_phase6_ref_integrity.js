/**
 * Library:        test_phase6_ref_integrity.js
 * Family:         Core
 * Description:    Phase 6 (105-series referential integrity) test suite for the JS port. Real imports, real temp-dir MFDB, no exec() strings.
 * Version:        1.0.0
 * Date:           2026-10-03
 * Author:         Elton Boehnen
 * Contact:        eltonboehnen@gmail.com | boehnenelton2024.pages.dev | github.com/boehnenelton
 * Format_Creator: Elton Boehnen
 * RELATIONAL_ID:  7c1e4b9a-2d58-4f36-9a0e-5b83d1c6f204
 * Release_Version: 300
 *
 * Run: node Lib_JS/Core/tests/test_phase6_ref_integrity.js
 */
'use strict';
const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const crypto = require('crypto');

const M = require('../lib_bejson_Core_mfdb_core.js');
const E = require('../lib_bejson_Core_bejson_errors.js');

let passed = 0, failed = 0;
function test(name, fn) {
  try { fn(); passed++; console.log('PASS  ' + name); }
  catch (e) { failed++; console.log('FAIL  ' + name + '\n      ' + (e && e.stack ? e.stack.split('\n').slice(0, 3).join('\n      ') : e)); }
}
function throwsCode(fn, code) {
  try { fn(); } catch (e) { assert.strictEqual(e.code, code, `expected code ${code}, got ${e.code}: ${e.message}`); return; }
  assert.fail(`expected throw with code ${code}`);
}

const uid = () => crypto.randomUUID();
function entityDoc(recordsType, fields) {
  return {
    Format: 'BEJSON', Format_Version: '105', Format_Creator: 'Elton Boehnen',
    Records_Type: [recordsType],
    Fields: fields.map(f => ({ field_uuid: uid(), ...f })),
    Values: []
  };
}
function build({ childOnDelete = 'restrict', grandOnDelete = 'restrict', noteOnDelete = 'null' } = {}) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'p6js-'));
  const write = (n, d) => fs.writeFileSync(path.join(dir, n), JSON.stringify(d, null, 2));
  write('authors.bejson', entityDoc('Author', [{ name: 'name', type: 'string' }]));
  write('books.bejson', entityDoc('Book', [
    { name: 'title', type: 'string' },
    { name: 'author_id', type: 'string', fk_target_entity: 'authors', fk_on_delete: childOnDelete }]));
  write('reviews.bejson', entityDoc('Review', [
    { name: 'text', type: 'string' },
    { name: 'book_id', type: 'string', fk_target_entity: 'books', fk_on_delete: grandOnDelete }]));
  write('notes.bejson', entityDoc('Note', [
    { name: 'text', type: 'string' },
    { name: 'author_id', type: 'string', fk_target_entity: 'authors', fk_on_delete: noteOnDelete }]));
  const legacy = { Format: 'BEJSON', Format_Version: '104', Format_Creator: 'Elton Boehnen', Records_Type: ['Legacy'],
    Fields: [{ name: 'x', type: 'string' }], Values: [] };
  write('legacy.bejson', legacy);
  const manifest = { Format: 'BEJSON', Format_Version: '104a', Format_Creator: 'Elton Boehnen', Records_Type: ['mfdb'],
    Fields: [{ name: 'entity_name', type: 'string' }, { name: 'file_path', type: 'string' }, { name: 'record_count', type: 'integer' }],
    Values: ['authors', 'books', 'reviews', 'notes', 'legacy'].map(n => [n, n + '.bejson', 0]) };
  const mp = path.join(dir, 'mfdb.bejson');
  fs.writeFileSync(mp, JSON.stringify(manifest, null, 2));
  return { dir, mp };
}
const load = (mp, n) => JSON.parse(fs.readFileSync(path.join(path.dirname(mp), n + '.bejson'), 'utf8'));
const count = (mp, n) => load(mp, n).Values.length;
const manifestCount = (mp, n) => { const m = JSON.parse(fs.readFileSync(mp, 'utf8')); return m.Values.find(r => r[0] === n)[2]; };

test('error codes 43-47 and 80-85 registered in JS errors', () => {
  assert.deepStrictEqual([E.E_MFDB_FK_TARGET_ENTITY_UNKNOWN, E.E_MFDB_FK_RESTRICT_VIOLATION, E.E_MFDB_FK_CASCADE_CYCLE, E.E_MFDB_FK_ENTITY_STILL_REFERENCED, E.E_MFDB_FK_INVALID_ON_DELETE], [43, 44, 45, 46, 47]);
  assert.deepStrictEqual([E.E_FIELD_INTEGRITY_MISMATCH, E.E_FORMAT_UNSUPPORTED, E.E_RECORD_NOT_FOUND, E.E_UPGRADE_VALIDATION_FAILED, E.E_DUPLICATE_FIELD_NAME, E.E_DUPLICATE_FIELD_UUID], [80, 81, 82, 83, 84, 85]);
});

test('enable/disable round-trips Ref_Integrity header', () => {
  const { mp } = build();
  assert.strictEqual(M.mfdb_core_is_ref_integrity_enabled(mp), false);
  M.mfdb_core_enable_ref_integrity(mp); assert.strictEqual(M.mfdb_core_is_ref_integrity_enabled(mp), true);
  M.mfdb_core_disable_ref_integrity(mp); assert.strictEqual(M.mfdb_core_is_ref_integrity_enabled(mp), false);
});

test('add: valid FK passes, null FK passes, dangling FK raises 39 and writes nothing', () => {
  const { mp } = build(); M.mfdb_core_enable_ref_integrity(mp);
  const a = M.mfdb_core_add_entity_record_105(mp, 'authors', ['Ada']).record_uuid;
  M.mfdb_core_add_entity_record_105(mp, 'books', ['B1', a]);
  M.mfdb_core_add_entity_record_105(mp, 'books', ['B2', null]);
  throwsCode(() => M.mfdb_core_add_entity_record_105(mp, 'books', ['B3', uid()]), 39);
  assert.strictEqual(count(mp, 'books'), 2);
  assert.strictEqual(manifestCount(mp, 'books'), 2);
});

test('add: dangling FK accepted when Ref_Integrity is off', () => {
  const { mp } = build();
  M.mfdb_core_add_entity_record_105(mp, 'books', ['B', uid()]);
  assert.strictEqual(count(mp, 'books'), 1);
});

test('update: FK field checked against target; non-FK field unchecked', () => {
  const { mp } = build(); M.mfdb_core_enable_ref_integrity(mp);
  const a = M.mfdb_core_add_entity_record_105(mp, 'authors', ['Ada']).record_uuid;
  const b = M.mfdb_core_add_entity_record_105(mp, 'books', ['B1', a]).record_uuid;
  throwsCode(() => M.mfdb_core_update_entity_record_105(mp, 'books', b, 'author_id', uid()), 39);
  M.mfdb_core_update_entity_record_105(mp, 'books', b, 'title', 'Renamed');
  assert.strictEqual(load(mp, 'books').Values[0][1], 'Renamed');
});

test('delete restrict: blocked with 44, nothing removed', () => {
  const { mp } = build({ childOnDelete: 'restrict' }); M.mfdb_core_enable_ref_integrity(mp);
  const a = M.mfdb_core_add_entity_record_105(mp, 'authors', ['Ada']).record_uuid;
  M.mfdb_core_add_entity_record_105(mp, 'books', ['B1', a]);
  throwsCode(() => M.mfdb_core_delete_entity_record_105(mp, 'authors', a), 44);
  assert.strictEqual(count(mp, 'authors'), 1); assert.strictEqual(count(mp, 'books'), 1);
});

test('delete null: dependent FK cleared, dependent row kept', () => {
  const { mp } = build({ noteOnDelete: 'null' }); M.mfdb_core_enable_ref_integrity(mp);
  const a = M.mfdb_core_add_entity_record_105(mp, 'authors', ['Ada']).record_uuid;
  M.mfdb_core_add_entity_record_105(mp, 'notes', ['n1', a]);
  M.mfdb_core_delete_entity_record_105(mp, 'authors', a);
  assert.strictEqual(count(mp, 'authors'), 0);
  assert.strictEqual(load(mp, 'notes').Values[0][2], null);
  assert.strictEqual(manifestCount(mp, 'authors'), 0);
});

test('delete cascade: two-level cascade removes grandchildren, counts synced', () => {
  const { mp } = build({ childOnDelete: 'cascade', grandOnDelete: 'cascade', noteOnDelete: 'null' }); M.mfdb_core_enable_ref_integrity(mp);
  const a = M.mfdb_core_add_entity_record_105(mp, 'authors', ['Ada']).record_uuid;
  const b1 = M.mfdb_core_add_entity_record_105(mp, 'books', ['B1', a]).record_uuid;
  const b2 = M.mfdb_core_add_entity_record_105(mp, 'books', ['B2', a]).record_uuid;
  M.mfdb_core_add_entity_record_105(mp, 'reviews', ['r1', b1]);
  M.mfdb_core_add_entity_record_105(mp, 'reviews', ['r2', b2]);
  M.mfdb_core_delete_entity_record_105(mp, 'authors', a);
  assert.deepStrictEqual(['authors', 'books', 'reviews'].map(n => count(mp, n)), [0, 0, 0]);
  assert.deepStrictEqual(['authors', 'books', 'reviews'].map(n => manifestCount(mp, n)), [0, 0, 0]);
});

test('delete cascade into restricted grandchild: whole delete blocked with 44, root survives', () => {
  const { mp } = build({ childOnDelete: 'cascade', grandOnDelete: 'restrict' }); M.mfdb_core_enable_ref_integrity(mp);
  const a = M.mfdb_core_add_entity_record_105(mp, 'authors', ['Ada']).record_uuid;
  const b = M.mfdb_core_add_entity_record_105(mp, 'books', ['B1', a]).record_uuid;
  M.mfdb_core_add_entity_record_105(mp, 'reviews', ['r1', b]);
  throwsCode(() => M.mfdb_core_delete_entity_record_105(mp, 'authors', a), 44);
  assert.strictEqual(count(mp, 'authors'), 1);
  assert.strictEqual(count(mp, 'books'), 1);
  assert.strictEqual(count(mp, 'reviews'), 1);
});

test('delete cascade cycle: mutual cascade references raise 45', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'p6js-cyc-'));
  const A = entityDoc('A', [{ name: 'label', type: 'string' }, { name: 'b_id', type: 'string', fk_target_entity: 'b', fk_on_delete: 'cascade' }]);
  const B = entityDoc('B', [{ name: 'label', type: 'string' }, { name: 'a_id', type: 'string', fk_target_entity: 'a', fk_on_delete: 'cascade' }]);
  fs.writeFileSync(path.join(dir, 'a.bejson'), JSON.stringify(A)); fs.writeFileSync(path.join(dir, 'b.bejson'), JSON.stringify(B));
  const mp = path.join(dir, 'mfdb.bejson');
  fs.writeFileSync(mp, JSON.stringify({ Format: 'BEJSON', Format_Version: '104a', Format_Creator: 'Elton Boehnen', Records_Type: ['mfdb'],
    Fields: [{ name: 'entity_name', type: 'string' }, { name: 'file_path', type: 'string' }, { name: 'record_count', type: 'integer' }],
    Values: [['a', 'a.bejson', 0], ['b', 'b.bejson', 0]] }));
  const a1 = M.mfdb_core_add_entity_record_105(mp, 'a', ['a1', null]).record_uuid;
  const b1 = M.mfdb_core_add_entity_record_105(mp, 'b', ['b1', a1]).record_uuid;
  M.mfdb_core_update_entity_record_105(mp, 'a', a1, 'b_id', b1);
  M.mfdb_core_enable_ref_integrity(mp);
  throwsCode(() => M.mfdb_core_delete_entity_record_105(mp, 'a', a1), 45);
});

test('check_entity_droppable lists every referencing row; empty for unreferenced entity', () => {
  const { mp } = build({ childOnDelete: 'cascade' });
  const a = M.mfdb_core_add_entity_record_105(mp, 'authors', ['Ada']).record_uuid;
  M.mfdb_core_add_entity_record_105(mp, 'books', ['B1', a]);
  M.mfdb_core_add_entity_record_105(mp, 'notes', ['n1', a]);
  const reasons = M.mfdb_core_check_entity_droppable(mp, 'authors');
  assert.strictEqual(reasons.length, 2);
  assert.deepStrictEqual(reasons.map(r => r.entity).sort(), ['books', 'notes']);
  assert.deepStrictEqual(M.mfdb_core_check_entity_droppable(mp, 'reviews'), []);
});

test('find_referencing_rows returns only rows pointing at the target uuid', () => {
  const { mp } = build();
  const a1 = M.mfdb_core_add_entity_record_105(mp, 'authors', ['A1']).record_uuid;
  const a2 = M.mfdb_core_add_entity_record_105(mp, 'authors', ['A2']).record_uuid;
  M.mfdb_core_add_entity_record_105(mp, 'books', ['B1', a1]);
  M.mfdb_core_add_entity_record_105(mp, 'books', ['B2', a2]);
  const refs = M.mfdb_core_find_referencing_rows(mp, 'authors', a1);
  assert.strictEqual(refs.length, 1); assert.strictEqual(refs[0].entity, 'books');
});

test('104-series entity: *_105 entry points raise E_MFDB_CORE_INVALID_OPERATION (54)', () => {
  const { mp } = build();
  throwsCode(() => M.mfdb_core_add_entity_record_105(mp, 'legacy', ['x']), 54);
});

test('invalid fk_on_delete on a dependent is rejected with 47 at write-time', () => {
  const { mp, dir } = build({ childOnDelete: 'explode' }); M.mfdb_core_enable_ref_integrity(mp);
  const a = M.mfdb_core_add_entity_record_105(mp, 'authors', ['Ada']).record_uuid;
  throwsCode(() => M.mfdb_core_add_entity_record_105(mp, 'books', ['B1', a]), 47);
});

test('unregistered fk_target_entity rejected with 43', () => {
  const { mp, dir } = build(); M.mfdb_core_enable_ref_integrity(mp);
  const p = path.join(dir, 'books.bejson'); const d = JSON.parse(fs.readFileSync(p, 'utf8'));
  d.Fields[1].fk_target_entity = 'ghost'; fs.writeFileSync(p, JSON.stringify(d));
  throwsCode(() => M.mfdb_core_add_entity_record_105(mp, 'books', ['B1', uid()]), 43);
});

console.log(`\n${passed} passed, ${failed} failed`);
process.exit(failed ? 1 : 0);
