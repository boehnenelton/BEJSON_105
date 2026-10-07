/**
 * Library:        bejson_cache.test.js
 * Family:         Core
 * Description:    Tests for the SELF-MAINTAINING Field Map Cache in lib_bejson_Core_bejson_core.js
 *                 (callers never build/refresh it; parity with Python TestAutoFieldMap).
 * Version:        2.1.1
 * Date:           2026-10-03
 * Author:         Elton Boehnen
 * Contact:        eltonboehnen@gmail.com | boehnenelton2024.pages.dev | github.com/boehnenelton
 * Format_Creator: Elton Boehnen
 * RELATIONAL_ID:  ffa0a170-6e87-4f77-9076-4ec53750dbff
 * Release_Version: 300
 */
const assert = require('assert');
const BEJSON = require('./lib_bejson_Core_bejson_core.js');
const PARSE  = require('./lib_bejson_Core_bejson_parse.js');
let n = 0;
const t = (name, fn) => { fn(); n++; console.log('  ok -', name); };

const doc105 = () => ({ Format: 'BEJSON', Format_Version: '105', Format_Creator: 'x', Records_Type: ['T'],
  Fields: [{ name: 'a', type: 'string', field_uuid: 'ua' }, { name: 'b', type: 'string', field_uuid: 'ub' }],
  Values: [['r1', 'x', 'y']] });

t('104 lookup + miss', () => {
  const d = { Format_Version: '104', Fields: [{ name: 'id' }, { name: 'name' }, { name: 'value' }], Values: [] };
  assert.strictEqual(BEJSON.bejson_core_get_field_index(d, 'name'), 1);
  assert.strictEqual(BEJSON.bejson_core_get_field_index(d, 'missing'), -1);
  assert.strictEqual(BEJSON.bejson_core_get_field_index(d, 'toString'), -1);   // prototype keys are not fields
});
t('104 identical-name docs do not collide', () => {
  const d1 = { Format_Version: '104', Fields: [{ name: 'a' }, { name: 'b' }] };
  const d2 = { Format_Version: '104', Fields: [{ name: 'b' }, { name: 'a' }] };
  assert.strictEqual(BEJSON.bejson_core_get_field_index(d1, 'a'), 0);
  assert.strictEqual(BEJSON.bejson_core_get_field_index(d2, 'a'), 1);
});
t('104 map is never stale after Fields edit (add / reorder)', () => {
  const d = { Format_Version: '104', Fields: [{ name: 'a' }], Values: [] };
  assert.strictEqual(BEJSON.bejson_core_get_field_index(d, 'b'), -1);
  d.Fields.push({ name: 'b' });
  assert.strictEqual(BEJSON.bejson_core_get_field_index(d, 'b'), 1);
  d.Fields.reverse();
  assert.strictEqual(BEJSON.bejson_core_get_field_index(d, 'a'), 1);
});
t('105 returns ROW positions (record_uuid offset) with no setup', () => {
  const d = doc105();
  assert.strictEqual(BEJSON.bejson_core_get_field_index(d, 'a'), 1);
  assert.strictEqual(d.Values[0][BEJSON.bejson_core_get_field_index(d, 'b')], 'y');
});
t('105db offset is 2', () => {
  const d = doc105(); d.Format_Version = '105db';
  assert.strictEqual(BEJSON.bejson_core_get_field_index(d, 'a'), 2);
});
t('105 self-heals after a rename and after add', () => {
  const d = doc105();
  BEJSON.bejson_core_get_field_index(d, 'a');
  d.Fields[0].name = 'a2';
  assert.strictEqual(BEJSON.bejson_core_get_field_index(d, 'a'), -1);
  assert.strictEqual(BEJSON.bejson_core_get_field_index(d, 'a2'), 1);
  d.Fields.push({ name: 'c', type: 'string', field_uuid: 'uc' });
  assert.strictEqual(BEJSON.bejson_core_get_field_index(d, 'c'), 3);
  assert.strictEqual(BEJSON.bejson_core_get_field_cache(d).by_uuid.uc, 2);
});
t('105 cache hit does not rebuild (same object)', () => {
  const d = doc105();
  const c1 = BEJSON.bejson_core_get_field_cache(d);
  BEJSON.bejson_core_get_field_index(d, 'a');
  assert.strictEqual(BEJSON.bejson_core_get_field_cache(d), c1);
});
t('parse() warms 105 docs, leaves 104 untouched', () => {
  const d5 = PARSE.parse_json(JSON.stringify(doc105()));
  assert.ok(d5._bejson_field_map && d5._bejson_field_map.by_name, '105 should be born warm');
  const d4 = PARSE.parse_json(JSON.stringify({ Format: 'BEJSON', Format_Version: '104', Records_Type: ['T'], Fields: [{ name: 'a', type: 'string' }], Values: [['x']] }));
  assert.strictEqual(d4._bejson_field_map, undefined);
});
t('cache keys never leak: JSON.stringify and serialize', () => {
  const d = doc105(); BEJSON.bejson_core_get_field_index(d, 'a');
  assert.ok(!JSON.stringify(d).includes('_bejson_field_map'));
  assert.ok(!BEJSON.bejson_core_serialize(d).includes('_bejson_field_map'));
  const d4 = { Format_Version: '104', Fields: [{ name: 'a' }], Values: [] }; BEJSON.bejson_core_get_field_index(d4, 'a');
  assert.ok(!JSON.stringify(d4).includes('_bejson_field_map'));
});
t('frozen doc still answers correctly (uncached)', () => {
  const d = Object.freeze({ Format_Version: '104', Fields: Object.freeze([{ name: 'a' }, { name: 'b' }]), Values: [] });
  assert.strictEqual(BEJSON.bejson_core_get_field_index(d, 'b'), 1);
});
console.log('JS field-map tests passed: ' + n);
