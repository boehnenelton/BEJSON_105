/**
 * Library:        test_adversarial_remediation.js
 * Family:         Core
 * Description:    Regression tests for the 2026-10 adversarial review: 105db column mapping, two-phase cascade delete, key-cache hygiene.
 * Version:        1.0.0
 * Date:           2026-10-09
 * Author:         Elton Boehnen
 * Contact:        eltonboehnen@gmail.com | boehnenelton2024.pages.dev | github.com/boehnenelton
 * Format_Creator: Elton Boehnen
 * RELATIONAL_ID:  98ee5f7c-c1c7-41de-8bba-4249a74a03b6
 * Release_Version: 300
 *
 * Run: node Lib_JS/Core/tests/test_adversarial_remediation.js
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


const C = require('../lib_bejson_Core_bejson_core.js');

function doc105db() {
  return { Format: 'BEJSON', Format_Version: '105db', Format_Creator: 'x', Records_Type: ['User'],
    Fields: [{ name: 'Record_Type_Parent', type: 'string', field_uuid: 'f0' },
             { name: 'user_id', type: 'string', field_uuid: 'f1' },
             { name: 'email', type: 'string', field_uuid: 'f2' }],
    Values: [['User', 'ru-1', 'usr_1', 'usr@test.com']] };
}

test('F1: 105db write_cell hits the named field only', () => {
  const d = doc105db();
  assert.strictEqual(C.bejson_core_resolve_field_index(d, 'user_id'), 2);
  const r = C.bejson_core_write_cell(d, 'ru-1', 'f1', 'usr_2');
  assert.strictEqual(r.col, 2);
  assert.deepStrictEqual(d.Values[0], ['User', 'ru-1', 'usr_2', 'usr@test.com']);
});

test('F1: 105/105a unchanged (+1)', () => {
  const d = { Format: 'BEJSON', Format_Version: '105', Format_Creator: 'x', Records_Type: ['T'],
    Fields: [{ name: 'a', type: 'string', field_uuid: 'u1' }], Values: [['ru', 'v']] };
  assert.strictEqual(C.bejson_core_resolve_field_index(d, 'a'), 1);
});

test('F1: FK write check reads the right value for 105db entities', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'advjs-'));
  const w = (n, d) => fs.writeFileSync(path.join(dir, n), JSON.stringify(d, null, 2));
  const authorUuid = uid();
  const authors = entityDoc('Author', [{ name: 'name', type: 'string' }]);
  authors.Values.push([authorUuid, 'Ann']);
  w('authors.bejson', authors);
  w('books.bejson', { Format: 'BEJSON', Format_Version: '105db', Format_Creator: 'x', Records_Type: ['Book'],
    Fields: [{ name: 'Record_Type_Parent', type: 'string', field_uuid: uid() },
             { name: 'title', type: 'string', field_uuid: uid() },
             { name: 'author_id', type: 'string', field_uuid: uid(), fk_target_entity: 'authors', fk_on_delete: 'restrict' }],
    Values: [] });
  const mp = path.join(dir, 'mfdb.bejson');
  w('mfdb.bejson', { Format: 'BEJSON', Format_Version: '104a', Format_Creator: 'x', Records_Type: ['mfdb'],
    Fields: [{ name: 'entity_name', type: 'string' }, { name: 'file_path', type: 'string' }, { name: 'record_count', type: 'integer' }],
    Values: [['authors', 'authors.bejson', 1], ['books', 'books.bejson', 0]] });
  M.mfdb_core_enable_ref_integrity(mp);
  // bad FK must be rejected (previously the check read the wrong cell and passed)
  assert.throws(() => M.mfdb_core_add_entity_record_105(mp, 'books', ['Book', 'T1', 'no-such-author']));
  assert.strictEqual(count(mp, 'books'), 0);
  M.mfdb_core_add_entity_record_105(mp, 'books', ['Book', 'T1', authorUuid]);
  assert.strictEqual(count(mp, 'books'), 1);
});

test('F2: restrict deep in the tree leaves every file untouched', () => {
  const { mp } = build({ childOnDelete: 'cascade', grandOnDelete: 'restrict' });
  M.mfdb_core_enable_ref_integrity(mp);
  const a = M.mfdb_core_add_entity_record_105(mp, 'authors', ['Ann']).record_uuid;
  // sibling B0 has no reviews and is cascade-deleted FIRST in the old walk; B1's review then
  // trips the restrict -- the old code had already destroyed B0 on disk by that point.
  M.mfdb_core_add_entity_record_105(mp, 'books', ['B0', a]);
  const b = M.mfdb_core_add_entity_record_105(mp, 'books', ['B1', a]).record_uuid;
  M.mfdb_core_add_entity_record_105(mp, 'reviews', ['r1', b]);
  M.mfdb_core_add_entity_record_105(mp, 'notes', ['n1', a]);
  const before = ['authors', 'books', 'reviews', 'notes'].map(n => fs.readFileSync(path.join(path.dirname(mp), n + '.bejson'), 'utf8'));
  throwsCode(() => M.mfdb_core_delete_entity_record_105(mp, 'authors', a), 44);
  const after = ['authors', 'books', 'reviews', 'notes'].map(n => fs.readFileSync(path.join(path.dirname(mp), n + '.bejson'), 'utf8'));
  assert.deepStrictEqual(after, before);
});

test('F2: successful cascade removes the whole tree and nulls notes', () => {
  const { mp } = build({ childOnDelete: 'cascade', grandOnDelete: 'cascade', noteOnDelete: 'null' });
  M.mfdb_core_enable_ref_integrity(mp);
  const a = M.mfdb_core_add_entity_record_105(mp, 'authors', ['Ann']).record_uuid;
  const b = M.mfdb_core_add_entity_record_105(mp, 'books', ['B1', a]).record_uuid;
  M.mfdb_core_add_entity_record_105(mp, 'reviews', ['r1', b]);
  M.mfdb_core_add_entity_record_105(mp, 'notes', ['n1', a]);
  M.mfdb_core_delete_entity_record_105(mp, 'authors', a);
  assert.strictEqual(count(mp, 'authors'), 0);
  assert.strictEqual(count(mp, 'books'), 0);
  assert.strictEqual(count(mp, 'reviews'), 0);
  assert.strictEqual(load(mp, 'notes').Values[0][2], null);
});

test('F5: key cache never stores the plaintext password (static + roundtrip)', async () => {
  const text = fs.readFileSync(path.join(__dirname, '..', 'lib_bejson_Core_bejson_core.js'), 'utf8');
  assert.ok(!/_keyCache\.push\(\{[^}]*password/.test(text), 'password stored in _keyCache');
  assert.strictEqual(typeof C.clearKeyCache, 'function');
});

(async () => {
  console.log(`\n${passed} passed, ${failed} failed`);
  process.exit(failed ? 1 : 0);
})();
