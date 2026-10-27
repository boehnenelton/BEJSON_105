/**
 * Library:        test_105_104_parity_suite.js
 * Family:         Core (tests)
 * Description:    Proves the 105-series enforces everything its 104 base enforces
 *                 in JavaScript: row length, value types, Records_Type count,
 *                 105a primitives, 105db Record_Type_Parent rules, 105 writer
 *                 type enforcement, 104 writer blocking on 105, and MFDB
 *                 deep_verify / self_heal / discover on 105 entities.
 * Version:        1.0.0
 * Date:           2026-10-27
 * Author:         Elton Boehnen
 * Format_Creator: Elton Boehnen
 * RELATIONAL_ID:  4e1a8b92-7f2c-4a3d-8e6b-5c0d1e2f3a4b
 * Release_Version: 300
 */

'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const os = require('os');
const crypto = require('crypto');

const V = require('../lib_bejson_Core_bejson_validator.js');
const C = require('../lib_bejson_Core_bejson_core.js');
const M = require('../lib_bejson_Core_mfdb_core.js');
const MV = require('../lib_bejson_Core_mfdb_validator.js');

const U4 = () => crypto.randomUUID();
const HDR = { Format: "BEJSON", Format_Creator: "Elton Boehnen" };

function d105(version = "105", types = ["T"], fields = null, values = null) {
  const fList = fields || [["name", "string"], ["age", "integer"]];
  const fl = fList.map(([n, t]) => ({ name: n, type: t, field_uuid: U4() }));
  return {
    ...HDR,
    Format_Version: version,
    Records_Type: [...types],
    Fields: fl,
    Values: values !== null ? values : [[U4(), "a", 1]]
  };
}

function d105db() {
  const fl = [
    { name: "Record_Type_Parent", type: "string", field_uuid: U4() },
    { name: "dept", type: "string", Record_Type_Parent: "D", field_uuid: U4() },
    { name: "emp", type: "string", Record_Type_Parent: "E", field_uuid: U4() }
  ];
  return {
    ...HDR,
    Format_Version: "105db",
    Records_Type: ["D", "E"],
    Fields: fl,
    Values: [["D", U4(), "eng", null], ["E", U4(), null, "al"]]
  };
}

function errs(doc) {
  return V.validate_bejson(doc, false).errors;
}

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

// ---------------------------------------------------------------------------
// 1. Validator Parity
// ---------------------------------------------------------------------------

test("test_baseline_valid", () => {
  assert.strictEqual(errs(d105()).length, 0);
  assert.strictEqual(errs(d105("105a")).length, 0);
  assert.strictEqual(errs(d105db()).length, 0);
});

test("test_row_too_short_long_and_no_uuid_slot", () => {
  for (const bad of [[U4(), "a"], [U4(), "a", 1, 9], ["a", 1]]) {
    const d = d105("105", ["T"], null, [bad]);
    const errors = errs(d);
    assert.ok(errors.some(e => e.includes("E_RECORD_LENGTH_MISMATCH") || e.includes("[9]")), JSON.stringify(bad));
  }
});

test("test_value_type_mismatch", () => {
  let d = d105("105", ["T"], null, [[U4(), "a", "not-int"]]);
  assert.ok(errs(d).some(e => e.includes("E_TYPE_MISMATCH") || e.includes("[8]")));

  d = d105("105", ["T"], null, [[U4(), "a", true]]); // bool is not integer
  assert.ok(errs(d).some(e => e.includes("E_TYPE_MISMATCH") || e.includes("[8]") || e.includes("bool")));

  d = d105("105", ["T"], [["x", "number"]], [[U4(), true]]); // bool is not number
  assert.ok(errs(d).some(e => e.includes("bool") || e.includes("number")));
});

test("test_null_always_allowed", () => {
  const d = d105("105", ["T"], null, [[U4(), null, null]]);
  assert.strictEqual(errs(d).length, 0);
});

test("test_all_six_types_checked", () => {
  const f = [
    ["s", "string"], ["i", "integer"], ["n", "number"],
    ["b", "boolean"], ["a", "array"], ["o", "object"]
  ];
  const good = [U4(), "x", 1, 1.5, true, [1], { k: 1 }];
  assert.strictEqual(errs(d105("105", ["T"], f, [good])).length, 0);

  for (let col = 1; col <= 6; col++) {
    const bad = [...good];
    bad[col] = (col === 5) ? "str" : (col === 6 ? [1] : { z: 1 });
    assert.ok(errs(d105("105", ["T"], f, [bad])).some(e => e.includes("E_TYPE_MISMATCH") || e.includes("[8]")), `col ${col}`);
  }
});

test("test_records_type_counts", () => {
  assert.ok(errs(d105("105", ["A", "B"])).length > 0);
  assert.ok(errs(d105("105a", ["A", "B"])).length > 0);
  assert.ok(errs(d105("105", [])).length > 0);

  const d = d105db();
  d.Records_Type = ["D"];
  assert.ok(errs(d).length > 0);
});

test("test_105a_primitives_only", () => {
  let d = d105("105a", ["T"], [["tags", "array"]], [[U4(), [1]]]);
  assert.ok(errs(d).some(e => e.includes("forbids complex type") || e.includes("E_INVALID_TYPE") || e.includes("[6]")));

  d = d105("105a", ["T"], [["o", "object"]], [[U4(), {}]]);
  assert.ok(errs(d).some(e => e.includes("forbids complex type") || e.includes("E_INVALID_TYPE") || e.includes("[6]")));
});

test("test_105db_discriminator_and_parent_rules", () => {
  let d = d105db();
  d.Fields[0].name = "other";
  assert.ok(errs(d).some(e => e.includes("Record_Type_Parent")));

  d = d105db();
  delete d.Fields[1].Record_Type_Parent;
  assert.ok(errs(d).length > 0);

  d = d105db();
  d.Values[0][0] = "UNKNOWN";
  assert.ok(errs(d).some(e => e.includes("Record_Type_Parent") || e.includes("not in Records_Type")));
});

test("test_uuidv4_format_warning_only", () => {
  const d = d105("105", ["T"], null, [["not-a-uuid-v4", "a", 1]]);
  const res = V.validate_bejson(d, false);
  assert.strictEqual(res.errors.length, 0);
  assert.ok(res.warnings.some(w => w.includes("UUIDv4")));
});

// ---------------------------------------------------------------------------
// 2. Core Writer Parity
// ---------------------------------------------------------------------------

test("test_104_add_record_rejects_105_doc", () => {
  for (const v of ["105", "105a", "105db"]) {
    const d = (v === "105db") ? d105db() : d105(v);
    assert.throws(() => {
      C.bejson_core_add_record(d, ["x", 1]);
    }, /81|E_FORMAT_UNSUPPORTED/);
  }
});

test("test_105_add_record_enforces_row_length_and_types", () => {
  const d = d105("105", ["T"], [["name", "string"], ["age", "integer"]], []);
  assert.throws(() => C.bejson_core_add_record_105(d, ["only_one"]), err => err.code === 9);
  assert.throws(() => C.bejson_core_add_record_105(d, ["bob", "not_int"]), err => err.code === 8);
  assert.throws(() => C.bejson_core_add_record_105(d, ["bob", true]), err => err.code === 8);

  const u = C.bejson_core_add_record_105(d, ["bob", 30]);
  assert.strictEqual(d.Values.length, 1);
  assert.strictEqual(d.Values[0][0], u);
  assert.strictEqual(d.Values[0][1], "bob");
  assert.strictEqual(d.Values[0][2], 30);
});

test("test_105_write_cell_enforces_type", () => {
  const d = d105("105", ["T"], [["name", "string"], ["age", "integer"]], []);
  const u = C.bejson_core_add_record_105(d, ["alice", 25]);
  const ageFieldUuid = d.Fields[1].field_uuid;

  assert.throws(() => C.bejson_core_write_cell(d, u, ageFieldUuid, "not_int"), err => err.code === 8);
  assert.throws(() => C.bejson_core_write_cell(d, u, ageFieldUuid, false), err => err.code === 8);

  C.bejson_core_write_cell(d, u, ageFieldUuid, 26);
  assert.strictEqual(d.Values[0][2], 26);
});

// ---------------------------------------------------------------------------
// 3. MFDB Maintenance Parity
// ---------------------------------------------------------------------------

function setupMfdb() {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "mfdb_parity_js_"));
  const m = M.mfdb_core_create_database(tmp, "Shop", [
    { name: "Customer", fields: [{ name: "cust_name", type: "string" }], format_version: "105" },
    { name: "Order", fields: [{ name: "code", type: "string" }, { name: "qty", type: "integer" }], format_version: "105" },
    { name: "Legacy", fields: [{ name: "tag", type: "string" }, { name: "val", type: "integer" }], format_version: "104" }
  ], { mfdb_version: "1.40" });

  M.mfdb_core_add_entity_record_105(m, "Customer", ["alice"]);
  M.mfdb_core_add_entity_record_105(m, "Order", ["O1", 10]);
  M.mfdb_core_add_entity_record(m, "Legacy", ["a", 1]);
  return { tmp, m };
}

function cleanupMfdb(tmp) {
  try { fs.rmSync(tmp, { recursive: true, force: true }); } catch (_) {}
}

test("test_105_add_rejects_wrong_length_and_type", () => {
  const { tmp, m } = setupMfdb();
  try {
    assert.throws(() => M.mfdb_core_add_entity_record_105(m, "Order", ["only"]));
    assert.throws(() => M.mfdb_core_add_entity_record_105(m, "Order", ["O2", "str"]));
    assert.strictEqual(M.mfdb_core_load_entity(m, "Order").length, 1);
  } finally {
    cleanupMfdb(tmp);
  }
});

test("test_104_writer_blocked_on_105_entity", () => {
  const { tmp, m } = setupMfdb();
  try {
    const custPath = M._get_entity_path(m, "Customer");
    const before = fs.readFileSync(custPath, 'utf8');
    assert.throws(() => M.mfdb_core_add_entity_record(m, "Customer", ["bob"]));
    assert.strictEqual(fs.readFileSync(custPath, 'utf8'), before);

    // 104 entity unaffected
    M.mfdb_core_add_entity_record(m, "Legacy", ["b", 2]);
    assert.strictEqual(M.mfdb_core_load_entity(m, "Legacy").length, 2);
  } finally {
    cleanupMfdb(tmp);
  }
});

test("test_deep_verify_clean_on_healthy_105", () => {
  const { tmp, m } = setupMfdb();
  try {
    const findings = M.mfdb_core_deep_verify(m);
    const bad = findings.filter(f => f.error || f.warning === "TYPE_MISMATCH");
    assert.strictEqual(bad.length, 0);
  } finally {
    cleanupMfdb(tmp);
  }
});

test("test_deep_verify_still_flags_real_105_violation", () => {
  const { tmp, m } = setupMfdb();
  try {
    const p = M._get_entity_path(m, "Order");
    const doc = JSON.parse(fs.readFileSync(p, 'utf8'));
    doc.Values[0].pop();
    fs.writeFileSync(p, JSON.stringify(doc));

    const findings = M.mfdb_core_deep_verify(m);
    const pos = findings.filter(f => f.error === "POSITIONAL_VIOLATION");
    assert.strictEqual(pos.length, 1);
    assert.strictEqual(pos[0].expected, 3);
  } finally {
    cleanupMfdb(tmp);
  }
});

test("test_self_heal_never_changes_healthy_105", () => {
  const { tmp, m } = setupMfdb();
  try {
    const snap = {};
    for (const n of ["Customer", "Order", "Legacy"]) {
      snap[n] = fs.readFileSync(M._get_entity_path(m, n), 'utf8');
    }
    const rep = M.mfdb_core_self_heal(m);
    assert.strictEqual(rep.remaining_errors.length, 0);
    for (const n of ["Customer", "Order", "Legacy"]) {
      assert.strictEqual(fs.readFileSync(M._get_entity_path(m, n), 'utf8'), snap[n], n);
    }
  } finally {
    cleanupMfdb(tmp);
  }
});

test("test_self_heal_does_not_guess_on_broken_105_row", () => {
  const { tmp, m } = setupMfdb();
  try {
    const p = M._get_entity_path(m, "Order");
    const doc = JSON.parse(fs.readFileSync(p, 'utf8'));
    doc.Values[0].pop();
    fs.writeFileSync(p, JSON.stringify(doc));
    const raw = fs.readFileSync(p, 'utf8');

    const rep = M.mfdb_core_self_heal(m);
    assert.ok(rep.remaining_errors.some(e => e.includes("not auto-repaired")));
    assert.strictEqual(fs.readFileSync(p, 'utf8'), raw);
  } finally {
    cleanupMfdb(tmp);
  }
});

test("test_self_heal_still_repairs_104", () => {
  const { tmp, m } = setupMfdb();
  try {
    const p = M._get_entity_path(m, "Legacy");
    const doc = JSON.parse(fs.readFileSync(p, 'utf8'));
    doc.Values[0].pop();
    fs.writeFileSync(p, JSON.stringify(doc));

    const rep = M.mfdb_core_self_heal(m);
    assert.ok(rep.actions.some(a => a.includes("Repaired")));
    const repairedDoc = JSON.parse(fs.readFileSync(p, 'utf8'));
    assert.strictEqual(repairedDoc.Values[0].length, 2);
  } finally {
    cleanupMfdb(tmp);
  }
});

test("test_discover_classifies_105_entities", () => {
  const { tmp, m } = setupMfdb();
  try {
    assert.strictEqual(M.mfdb_core_discover(M._get_entity_path(m, "Order")), "entity");
    assert.strictEqual(M.mfdb_core_discover(M._get_entity_path(m, "Legacy")), "entity");
    assert.strictEqual(M.mfdb_core_discover(m), "manifest");
  } finally {
    cleanupMfdb(tmp);
  }
});

test("test_database_validates_and_catches_bad_105_row", () => {
  const { tmp, m } = setupMfdb();
  try {
    assert.strictEqual(MV.validate_mfdb_database(m).valid, true);
    const p = M._get_entity_path(m, "Order");
    const doc = JSON.parse(fs.readFileSync(p, 'utf8'));
    doc.Values[0][2] = "text"; // col 2 is qty (integer)
    fs.writeFileSync(p, JSON.stringify(doc));

    assert.strictEqual(MV.validate_mfdb_database(m).valid, false);
  } finally {
    cleanupMfdb(tmp);
  }
});

console.log(`\nAll ${passed} JS parity tests passed!`);
