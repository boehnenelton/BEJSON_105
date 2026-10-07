/**
 * Library:        test_validator_105.js
 * Family:         Core
 * Description:    JS validator tests for Format_Version 105 / 105a / 105db: accepts sound docs, rejects missing/duplicate field_uuid, missing/duplicate record_uuid, Fail-on-Switch, wrong row length, bad types, bad 105db discriminator, and type "any". Also validates documents produced by the PY upgrade code (cross-language).
 * Version:        1.0.0
 * Date:           2026-10-03
 * Author:         Elton Boehnen
 * Contact:        eltonboehnen@gmail.com | boehnenelton2024.pages.dev | github.com/boehnenelton
 * Format_Creator: Elton Boehnen
 * RELATIONAL_ID:  3b8f6d20-c1a4-47e9-9d75-e04a1b6c2f83
 * Release_Version: 300
 */
'use strict';
const assert = require('assert');
const V = require('../lib_bejson_Core_bejson_validator.js');
let n = 0;
const ok  = (d, msg) => { V.bejson_validator_reset_state(); assert.strictEqual(V.bejson_validator_validate_string(JSON.stringify(d)), true, msg); n++; };
const bad = (d, code, msg) => { V.bejson_validator_reset_state();
  try { V.bejson_validator_validate_string(JSON.stringify(d)); } catch (e) { assert.strictEqual(e.code, code, `${msg}: code ${e.code}`); n++; return; }
  assert.fail('should have been rejected: ' + msg); };
const E = require('../lib_bejson_Core_bejson_errors.js');

// 105db mirrors the real PY upgrader output: Fields[0] is Record_Type_Parent, rows are
// [discriminator, record_uuid, ...rest], so row length = fields + 1 (same as 105/105a).
const mk = (ver, extra = {}) => Object.assign({
  Format: 'BEJSON', Format_Version: ver, Format_Creator: 'Elton Boehnen', Records_Type: ver === '105db' ? ['A', 'B'] : ['R'],
  Fields: ver === '105db'
    ? [{ name: 'Record_Type_Parent', type: 'string', field_uuid: 'f0' }, { name: 'a', type: 'string', field_uuid: 'f1', Record_Type_Parent: 'A' }, { name: 'n', type: 'integer', field_uuid: 'f2', Record_Type_Parent: 'B' }]
    : [{ name: 'a', type: 'string', field_uuid: 'f1' }, { name: 'n', type: 'integer', field_uuid: 'f2' }],
  Values: ver === '105db' ? [['A', 'r1', 'x', null], ['B', 'r2', null, 2]] : [['r1', 'x', 1], ['r2', null, 2]],
}, extra);

for (const v of ['105', '105a', '105db']) {
  ok(mk(v), `${v} sound`);
  ok(mk(v, { Values: [] }), `${v} empty`);
}
// reject: missing / duplicate field_uuid, Fail-on-Switch
let d = mk('105'); delete d.Fields[1].field_uuid; bad(d, E.E_INVALID_FIELDS, 'missing field_uuid (Fail-on-Switch)');
d = mk('105'); d.Fields[1].field_uuid = 'f1'; bad(d, E.E_INVALID_FIELDS, 'duplicate field_uuid');
d = mk('105'); d.Fields.forEach(f => delete f.field_uuid); bad(d, E.E_INVALID_FIELDS, '104 re-headered to 105');
// reject: record_uuid problems
d = mk('105'); d.Values[1][0] = 'r1'; bad(d, E.E_INVALID_VALUES, 'duplicate record_uuid');
d = mk('105'); d.Values[0][0] = null; bad(d, E.E_INVALID_VALUES, 'null record_uuid');
d = mk('105db'); d.Values[1][1] = 'r1'; bad(d, E.E_INVALID_VALUES, '105db duplicate record_uuid (col 1)');
// reject: row length (offset-aware) and type mismatch on the right column
d = mk('105'); d.Values[0] = ['r1', 'x']; bad(d, E.E_RECORD_LENGTH_MISMATCH, '105 short row');
d = mk('105'); d.Values[0] = ['x', 1]; bad(d, E.E_RECORD_LENGTH_MISMATCH, '105 row missing uuid cell');
d = mk('105db'); d.Values[0] = ['r1', 'x', null]; bad(d, E.E_RECORD_LENGTH_MISMATCH, '105db row missing discriminator');
d = mk('105db'); d.Values[0] = ['A', 'r1', 'x', null, 'extra']; bad(d, E.E_RECORD_LENGTH_MISMATCH, '105db row too long (old +2 assumption must not pass)');
d = mk('105'); d.Values[0][2] = 'not-int'; bad(d, E.E_TYPE_MISMATCH, '105 type mismatch in data column');
d = mk('105db'); d.Values[1][3] = 'not-int'; bad(d, E.E_TYPE_MISMATCH, '105db type mismatch in data column');
d = mk('105db'); d.Values[0][0] = 'ZZZ'; bad(d, E.E_INVALID_RECORD_TYPE_PARENT, '105db bad discriminator');
// "any" and unknown types still rejected under 105
for (const v of ['105', '105a', '105db']) { d = mk(v); d.Fields[0].type = 'any'; bad(d, E.E_INVALID_FIELDS, `${v} type any`); }
// unknown version still rejected
d = mk('105'); d.Format_Version = '106'; bad(d, E.E_INVALID_VERSION, 'version 106');
// 104 behaviour unchanged
ok({ Format: 'BEJSON', Format_Version: '104', Format_Creator: 'Elton Boehnen', Records_Type: ['R'], Fields: [{ name: 'a', type: 'string' }], Values: [['x']] }, '104 sound');
bad({ Format: 'BEJSON', Format_Version: '104', Format_Creator: 'Elton Boehnen', Records_Type: ['R'], Fields: [{ name: 'a', type: 'string' }], Values: [['x', 'y']] }, E.E_RECORD_LENGTH_MISMATCH, '104 wrong length');

// Cross-language: documents produced by the real PY upgrade code must validate in JS
const { execFileSync } = require('child_process');
const fs = require('fs'), os = require('os'), path = require('path');
const pyDir = path.join(__dirname, '..', '..', '..', 'Lib_PY', 'Core');
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'v105-'));
const fixtures = {
  '104':   { Format: 'BEJSON', Format_Version: '104', Format_Creator: 'Elton Boehnen', Records_Type: ['R'],
             Fields: [{ name: 'a', type: 'string' }, { name: 'n', type: 'integer' }], Values: [['x', 1], ['y', 2]] },
  '104a':  { Format: 'BEJSON', Format_Version: '104a', Format_Creator: 'Elton Boehnen', Records_Type: ['R'],
             Fields: [{ name: 'a', type: 'string' }, { name: 'n', type: 'integer' }], Values: [['x', 1], ['y', 2]] },
  '104db': { Format: 'BEJSON', Format_Version: '104db', Format_Creator: 'Elton Boehnen', Records_Type: ['A', 'B'],
             Fields: [{ name: 'Record_Type_Parent', type: 'string' }, { name: 'a', type: 'string', Record_Type_Parent: 'A' }, { name: 'n', type: 'integer', Record_Type_Parent: 'B' }],
             Values: [['A', 'x', null], ['B', null, 2]] },
};
for (const [ver, doc] of Object.entries(fixtures)) {
  const f = path.join(tmp, `d${ver}.bejson`);
  fs.writeFileSync(f, JSON.stringify(doc));
  execFileSync('python3', ['-c', `
import json,sys
sys.path.insert(0,${JSON.stringify(pyDir)})
import lib_bejson_Core_bejson_upgrade as U
p=${JSON.stringify(f)}
U.bejson_core_upgrade_to_105(json.load(open(p)), p)
`], { encoding: 'utf8' });
  const up = JSON.parse(fs.readFileSync(f, 'utf8'));
  assert.ok(/^105/.test(up.Format_Version), `PY upgraded ${ver} -> ${up.Format_Version}`);
  ok(up, `PY-upgraded ${ver} (-> ${up.Format_Version}) validates in JS`);
}
console.log(`JS 105 validator tests passed: ${n}`);
