/**
 * Library:         test_nesting_smoke.js
 * Family:          Core
 * Module Purpose:  Smoke/behavior tests for the nesting modules (scan, mutate, query, error codes 130-139); written to prove the Core_Nesting -> Core move changed no behavior.
 * Architecture:    Standalone script; resolves the nesting modules relative to this file (no absolute paths).
 * Format_Scope:    Nested 104 (NOT 104db, NOT MFDB)
 * Glossary:        BEJSON 104, 104a and 104db are the three file formats (Format_Version). 104db = ONE file holding 2+ entity types
 *                  (Record_Type_Parent discriminator, null-padding). MFDB is NOT a format and NOT 104db: it is a layer made of one 104a manifest
 *                  (104a.mfdb.bejson) plus dense 104 entity files linked by Parent_Hierarchy. MFDB-132 = an MFDB packed into one Chunked-104a document.
 * Version:         1.1.0
 * Release_Version: 300
 * Date:            2026-10-16
 * Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
 * Format_Creator:  Elton Boehnen
 * RELATIONAL_ID:   39f28ae0-dffd-42a9-8e08-b67ec091282a
 * Changelog:
 *   1.1.0 (2026-10-16) - Added tests: Core validator rules apply to nested cells; same-schema documents do not share cache entries.
 *   1.0.2 (2026-10-16) - Query API now read from core_nesting (nesting_query merged).
 *   1.0.1 (2026-10-16) - Reads codes 130-139 from lib_bejson_Core_bejson_errors (nesting errors file removed).
 */
'use strict';
const assert = require('assert');
const path = require('path');
const N = require(path.join(__dirname, '..', 'lib_bejson_Core_bejson_core_nesting.js'));
const Q = N;  // query API lives in core_nesting
const E = require(path.join(__dirname, '..', 'lib_bejson_Core_bejson_errors.js'));

let passed = 0, failed = 0;
function test(name, fn) { try { fn(); passed++; console.log('ok   - ' + name); } catch (e) { failed++; console.log('FAIL - ' + name + '\n       ' + e.message); } }
const INNER = { Format: 'BEJSON', Format_Version: '104', Format_Creator: 'Elton Boehnen', Records_Type: ['Items'],
  Fields: [{ name: 'sku', type: 'string' }, { name: 'qty', type: 'integer' }], Values: [['a', 1], ['b', 2]] };
const outer = () => ({ Format: 'BEJSON', Format_Version: '104', Format_Creator: 'Elton Boehnen', Records_Type: ['Order'],
  Fields: [{ name: 'id', type: 'string' }, { name: 'items', type: 'string' }], Values: [['o1', JSON.stringify(INNER)], ['o2', null]] });

test('scan', () => {
  const r = N.bejsonNestingScan(outer(), false);
  assert.deepStrictEqual([r.nestedFound, r.nestedValid, r.nestedInvalid, r.scannedCells, r.maxDepthSeen], [1, 1, 0, 4, 1]);
  assert.ok(N.bejsonNestingSummary(r).includes('Scan Summary'));
  const cells = N.bejsonNestingFlatten(r);
  assert.strictEqual(cells.length, 1);
  assert.deepStrictEqual(N.bejsonNestingGetFieldMap(cells[0]), { sku: 0, qty: 1 });
});
test('mutate appends field and null-pads', () => {
  const doc = outer(); const r = N.bejsonNestingScan(doc, false);
  N.bejsonNestingMutate(doc, r.cells[0], d => { d.Fields.push({ name: 'note', type: 'string' }); });
  assert.deepStrictEqual(JSON.parse(doc.Values[0][1]).Values[0], ['a', 1, null]);
});
test('mutate rejects field removal', () => {
  const doc = outer(); const r = N.bejsonNestingScan(doc, false);
  assert.throws(() => N.bejsonNestingMutate(doc, r.cells[0], d => { d.Fields.pop(); }));
});
test('query', () => {
  assert.strictEqual(Q.bejsonNestingQuery(outer(), 'items').length, 2);
  assert.strictEqual(Q.bejsonNestingGetPath(outer(), 'nope', 'DEF'), 'DEF');
  assert.throws(() => Q.bejsonNestingQuery(outer(), 'bad..path'));
});
const outerWith = inner => { const d = outer(); d.Values[0][1] = JSON.stringify(inner); return d; };
test('Core validator rules apply to nested cells', () => {
  const badCreator = Object.assign({}, INNER, { Format_Creator: 'Someone' });
  const dupFields = Object.assign({}, INNER, { Fields: [{ name: 'a', type: 'string' }, { name: 'a', type: 'string' }], Values: [['x', 'y']] });
  [badCreator, dupFields].forEach(bad => {
    N.bejsonNestingCacheClear();
    const r = N.bejsonNestingScan(outerWith(bad), false);
    assert.deepStrictEqual([r.nestedValid, r.nestedInvalid], [0, 1]);
  });
});
test('same-schema different content is not served from cache', () => {
  N.bejsonNestingCacheClear();
  N.bejsonNestingScan(outerWith(INNER));
  assert.strictEqual(N.bejsonNestingScan(outerWith(Object.assign({}, INNER, { Format_Creator: 'Someone' }))).nestedInvalid, 1);
});
test('error codes unchanged (130-139)', () => {
  const vals = Object.entries(E).filter(([k, v]) => k.startsWith('E_NESTING_') && typeof v === 'number').map(([, v]) => v).sort((a, b) => a - b);
  assert.deepStrictEqual(vals, [130, 131, 132, 133, 134, 135, 136, 137, 138, 139]);
});
console.log('\n' + passed + ' passed, ' + failed + ' failed');
process.exit(failed ? 1 : 0);
