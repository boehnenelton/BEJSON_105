/**
 * Library:        test_validator_types.js
 * Family:         Core
 * Description:    Field type closed-set tests: "any" and other non-spec types must be rejected; the six spec types accepted.
 * Version:        1.0.0
 * Date:           2026-10-03
 * Author:         Elton Boehnen
 * Contact:        eltonboehnen@gmail.com | boehnenelton2024.pages.dev | github.com/boehnenelton
 * Format_Creator: Elton Boehnen
 * RELATIONAL_ID:  0e6b41c8-7a35-4d92-b1f4-62c9d8a3e570
 * Release_Version: 300
 */
'use strict';
const assert = require('assert');
const V = require('../lib_bejson_Core_bejson_validator.js');
const doc = t => JSON.stringify({ Format: 'BEJSON', Format_Version: '104', Format_Creator: 'Elton Boehnen',
  Records_Type: ['R'], Fields: [{ name: 'a', type: t }], Values: [] });
let n = 0;
for (const bad of ['any', 'ANY', 'String', 'text', '', 'null']) {
  V.bejson_validator_reset_state();
  assert.throws(() => V.bejson_validator_validate_string(doc(bad)), `type ${JSON.stringify(bad)} must be rejected`); n++;
}
for (const good of ['string', 'integer', 'number', 'boolean', 'array', 'object']) {
  V.bejson_validator_reset_state();
  assert.strictEqual(V.bejson_validator_validate_string(doc(good)), true, good); n++;
}
assert.ok(!V.VALID_FIELD_TYPES.has('any')); n++;
console.log(`JS validator type tests passed: ${n}`);
