/**
 * Library:        test_mfdb_spec_levels_suite.js
 * Family:         Core (tests)
 * Description:    Pins the MFDB spec Level 1/2/3 validation rules (104 crash course)
 *                 for BOTH 104 and 105 entity files in JavaScript: entity Records_Type
 *                 match (34), bidirectional manifest<->entity (38), orphan (37),
 *                 missing Parent_Hierarchy (36), duplicates (35), missing field (40),
 *                 nulls (41), record_count drift = warning only.
 * Version:        1.0.0
 * Date:           2026-10-27
 * Author:         Elton Boehnen
 * Format_Creator: Elton Boehnen
 * RELATIONAL_ID:  f3c2a10e-94b8-4d5c-8a12-6e7f8b9c0d1e
 * Release_Version: 300
 */

'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const os = require('os');

const M = require('../lib_bejson_Core_mfdb_core.js');
const MV = require('../lib_bejson_Core_mfdb_validator.js');

const S = n => ({ name: n, type: "string" });
const jl = p => JSON.parse(fs.readFileSync(p, 'utf8'));
const jd = (doc, p) => fs.writeFileSync(p, JSON.stringify(doc));

let passed = 0;
function test(name, fn) {
  try {
    fn();
    passed++;
    console.log(`PASS ${name}`);
  } catch (e) {
    console.error(`FAIL ${name}: ${e.message}`);
    throw e;
  }
}

function runSpecSuite(fmt) {
  const suiteName = `Spec_${fmt}`;

  function makeDb(prefix) {
    const tmp = fs.mkdtempSync(path.join(os.tmpdir(), `mfdbspec_${fmt}_${prefix}_`));
    const m = M.mfdb_core_create_database(path.join(tmp, "a"), "Shop", [
      { name: "Customer", fields: [S("cust_name")], format_version: fmt },
      { name: "Order", fields: [S("code")], format_version: fmt }
    ], { mfdb_version: "1.40" });

    const add = fmt === "105" ? M.mfdb_core_add_entity_record_105 : M.mfdb_core_add_entity_record;
    add(m, "Customer", ["ann"]);
    add(m, "Order", ["O1"]);
    const ent = M._get_entity_path(m, "Order");
    return { tmp, m, ent };
  }

  function cleanup(tmp) {
    try { fs.rmSync(tmp, { recursive: true, force: true }); } catch (_) {}
  }

  test(`${suiteName}: clean database valid with no warnings`, () => {
    const { tmp, m } = makeDb("clean");
    try {
      const r = MV.validate_mfdb_database(m);
      assert.strictEqual(r.valid, true, JSON.stringify(r.errors));
      assert.strictEqual(r.warnings.length, 0);
    } finally {
      cleanup(tmp);
    }
  });

  test(`${suiteName}: records_type must match entity_name (34)`, () => {
    const { tmp, m, ent } = makeDb("rt_name");
    try {
      const d = jl(ent);
      d.Records_Type = ["WrongName"];
      jd(d, ent);
      const r = MV.validate_mfdb_database(m);
      assert.strictEqual(r.valid, false);
      assert.ok(r.errors.join(' ').includes("[34]"));
    } finally {
      cleanup(tmp);
    }
  });

  test(`${suiteName}: records_type case sensitive (34)`, () => {
    const { tmp, m, ent } = makeDb("rt_case");
    try {
      const d = jl(ent);
      d.Records_Type = ["order"];
      jd(d, ent);
      const r = MV.validate_mfdb_database(m);
      assert.strictEqual(r.valid, false);
      assert.ok(r.errors.join(' ').includes("[34]"));
    } finally {
      cleanup(tmp);
    }
  });

  test(`${suiteName}: records_type exactly one`, () => {
    const { tmp, m, ent } = makeDb("rt_count");
    try {
      const d = jl(ent);
      d.Records_Type = ["Order", "Extra"];
      jd(d, ent);
      const r = MV.validate_mfdb_database(m);
      assert.strictEqual(r.valid, false);
    } finally {
      cleanup(tmp);
    }
  });

  test(`${suiteName}: parent_hierarchy missing (36)`, () => {
    const { tmp, m, ent } = makeDb("ph_missing");
    try {
      const d = jl(ent);
      delete d.Parent_Hierarchy;
      jd(d, ent);
      const r = MV.validate_mfdb_database(m);
      assert.strictEqual(r.valid, false);
      assert.ok(r.errors.join(' ').includes("Parent_Hierarchy") || r.errors.join(' ').includes("[36]"));
    } finally {
      cleanup(tmp);
    }
  });

  test(`${suiteName}: orphan parent_hierarchy nonexistent manifest (37)`, () => {
    const { tmp, m, ent } = makeDb("ph_orphan");
    try {
      const d = jl(ent);
      d.Parent_Hierarchy = "../nope.mfdb.bejson";
      jd(d, ent);
      const r = MV.validate_mfdb_database(m);
      assert.strictEqual(r.valid, false);
      assert.ok(r.errors.join(' ').includes("[37]"));
    } finally {
      cleanup(tmp);
    }
  });

  test(`${suiteName}: bidirectional entity points to other manifest (38)`, () => {
    const { tmp, m, ent } = makeDb("ph_bidi");
    try {
      const otherTmp = fs.mkdtempSync(path.join(os.tmpdir(), "mfdbspec_other_"));
      const otherM = M.mfdb_core_create_database(path.join(otherTmp, "b"), "Other", [
        { name: "Order", fields: [S("code")], format_version: fmt }
      ]);
      const d = jl(ent);
      d.Parent_Hierarchy = path.relative(path.dirname(ent), otherM).split(path.sep).join('/');
      jd(d, ent);
      const r = MV.validate_mfdb_database(m);
      assert.strictEqual(r.valid, false);
      assert.ok(r.errors.join(' ').includes("[38]"));
      cleanup(otherTmp);
    } finally {
      cleanup(tmp);
    }
  });

  test(`${suiteName}: bidirectional standalone entity not listed (38)`, () => {
    const { tmp, ent } = makeDb("bidi_stray");
    try {
      const stray = path.join(path.dirname(ent), "stray.bejson");
      fs.copyFileSync(ent, stray);
      const rStray = MV.validate_mfdb_entity_file(stray);
      assert.strictEqual(rStray.valid, false);
      assert.ok(rStray.errors.join(' ').includes("[38]"));
      const rEnt = MV.validate_mfdb_entity_file(ent);
      assert.strictEqual(rEnt.valid, true);
    } finally {
      cleanup(tmp);
    }
  });

  test(`${suiteName}: entity standalone name check uses manifest row (34)`, () => {
    const { tmp, ent } = makeDb("standalone_name");
    try {
      const d = jl(ent);
      d.Records_Type = ["Nope"];
      jd(d, ent);
      const r = MV.validate_mfdb_entity_file(ent);
      assert.strictEqual(r.valid, false);
      assert.ok(r.errors.join(' ').includes("[34]"));
    } finally {
      cleanup(tmp);
    }
  });

  test(`${suiteName}: entity format 105db rejected (31)`, () => {
    const { tmp, m, ent } = makeDb("format_105db");
    try {
      const d = jl(ent);
      d.Format_Version = "105db";
      jd(d, ent);
      const r = MV.validate_mfdb_database(m);
      assert.strictEqual(r.valid, false);
    } finally {
      cleanup(tmp);
    }
  });

  test(`${suiteName}: record_count drift is warning only`, () => {
    const { tmp, m } = makeDb("count_drift");
    try {
      const mf = jl(m);
      const names = mf.Fields.map(f => f.name);
      const idx = names.indexOf("record_count");
      mf.Values[1][idx] = 99;
      jd(mf, m);
      const r = MV.validate_mfdb_database(m);
      assert.strictEqual(r.valid, true, JSON.stringify(r.errors));
      assert.ok(r.warnings.some(w => w.includes("record_count")));
    } finally {
      cleanup(tmp);
    }
  });

  test(`${suiteName}: manifest level 1 codes (35, 41, 33, Records_Type)`, () => {
    const { tmp, m } = makeDb("manifest_l1");
    try {
      const mf = jl(m);
      const names = mf.Fields.map(f => f.name);
      const enIdx = names.indexOf("entity_name");
      const fpIdx = names.indexOf("file_path");

      // duplicate entity_name (35)
      let bad = JSON.parse(JSON.stringify(mf));
      bad.Values[1][enIdx] = bad.Values[0][enIdx];
      jd(bad, m);
      let r = MV.validate_mfdb_database(m);
      assert.ok(r.errors.join(' ').includes("[35]"));

      // null entity_name (41)
      bad = JSON.parse(JSON.stringify(mf));
      bad.Values[0][enIdx] = null;
      jd(bad, m);
      r = MV.validate_mfdb_database(m);
      assert.ok(r.errors.join(' ').includes("[41]"));

      // missing entity file (33)
      bad = JSON.parse(JSON.stringify(mf));
      bad.Values[0][fpIdx] = "data/missing.bejson";
      jd(bad, m);
      r = MV.validate_mfdb_database(m);
      assert.ok(r.errors.join(' ').includes("[33]"));

      // Records_Type not ['mfdb']
      bad = JSON.parse(JSON.stringify(mf));
      bad.Records_Type = ["other"];
      jd(bad, m);
      r = MV.validate_mfdb_database(m);
      assert.strictEqual(r.valid, false);
    } finally {
      cleanup(tmp);
    }
  });
}

runSpecSuite("104");
runSpecSuite("105");

test(`Spec_105: absolute file_path to an existing file outside the root is rejected`, () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'mfdbspec_abs_'));
  try {
    const m = M.mfdb_core_create_database(path.join(tmp, 'a'), 'Shop', [{ name: 'Order', fields: [S('code')], format_version: '105' }], { mfdb_version: '1.40' });
    M.mfdb_core_add_entity_record_105(m, 'Order', ['O1']);
    const ent = M._get_entity_path(m, 'Order');
    const ext = path.join(tmp, 'ext'); fs.mkdirSync(ext);
    const outside = path.join(ext, 'outside.bejson');
    const d = jl(ent); d.Parent_Hierarchy = path.relative(ext, m); jd(d, outside);
    const mf = jl(m); const n = mf.Fields.map(f => f.name); mf.Values[0][n.indexOf('file_path')] = outside; jd(mf, m);
    const r = MV.validate_mfdb_database(m);
    assert.strictEqual(r.valid, false);
    assert.ok(r.errors.join(' ').includes('[33]') && r.errors.join(' ').includes('escapes root'));
  } finally { fs.rmSync(tmp, { recursive: true, force: true }); }
});

test(`Spec_105: Network_Role Master/Slave/Standalone valid, invalid role rejected (30)`, () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'mfdbspec_role_'));
  try {
    const m = M.mfdb_core_create_database(path.join(tmp, 'a'), 'Shop', [{ name: 'Order', fields: [S('code')], format_version: '105' }]);
    for (const role of ['Master', 'Slave', 'Standalone']) {
      const mf = jl(m); mf.Network_Role = role; jd(mf, m);
      assert.strictEqual(MV.validate_mfdb_database(m).valid, true, role);
    }
    const mf = jl(m); mf.Network_Role = 'RogueNode'; jd(mf, m);
    const r = MV.validate_mfdb_database(m);
    assert.strictEqual(r.valid, false);
    assert.ok(r.errors.join(' ').includes('[30]'));
  } finally { fs.rmSync(tmp, { recursive: true, force: true }); }
});

test(`Spec_105: check_referential_integrity is 105-only; strict mode fails on orphan FK`, () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'mfdbspec_ri_'));
  try {
    const m = M.mfdb_core_create_database(path.join(tmp, 'a'), 'Shop', [
      { name: 'authors', fields: [S('name')], format_version: '105' },
      { name: 'books', fields: [S('title'), { name: 'author_fk', type: 'string', fk_target_entity: 'authors', fk_on_delete: 'restrict' }], format_version: '105' },
      { name: 'legacy', fields: [S('x'), S('ghost_id_fk')], format_version: '104' },
    ]);
    const a = M.mfdb_core_add_entity_record_105(m, 'authors', ['Ada']).record_uuid;
    M.mfdb_core_add_entity_record_105(m, 'books', ['B1', a]);
    M.mfdb_core_add_entity_record(m, 'legacy', ['x', 'nowhere']);
    assert.deepStrictEqual(MV.mfdb_validator_check_referential_integrity(m), []);
    assert.strictEqual(MV.validate_mfdb_database(m, true).valid, true);
    M.mfdb_core_add_entity_record_105(m, 'books', ['B2', 'dangling-uuid']);
    const f = MV.mfdb_validator_check_referential_integrity(m);
    assert.strictEqual(f.length, 1);
    assert.strictEqual(f[0].numeric_code, 39);
    assert.strictEqual(MV.validate_mfdb_database(m, false).valid, true);
    assert.strictEqual(MV.validate_mfdb_database(m, true).valid, false);
  } finally { fs.rmSync(tmp, { recursive: true, force: true }); }
});

console.log(`\nAll ${passed} MFDB spec level tests passed!`);
