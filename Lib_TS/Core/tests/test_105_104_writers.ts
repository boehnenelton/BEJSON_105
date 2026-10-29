/**
 * Library:         test_105_104_writers.ts
 * Family:          Core
 * Module Purpose:  Pins that 105-series writers are as strict as the 104 ones: addRecord105 checks row length, value types and the 105db discriminator; writeCell checks value types; the 104 writers (appendRecord/updateRecord/deleteRecord/setFieldValue) refuse 105-series docs; the 105 validator catches bad rows, types, Records_Type counts and 105a complex types.
 * Architecture:    Standalone script; imports libraries relative to this file.
 * Format_Scope:    105 | 105a | 105db
 * Version:         1.0.0
 * Release_Version: 300
 * Date:            2026-10-28
 * Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
 * Format_Creator:  Elton Boehnen
 * RELATIONAL_ID:   6631e826-7e4d-4985-96d8-67c703dfad4c
 */
import { addRecord105, writeCell } from "../lib_bejson_Core_bejson_core_105";
import { appendRecord, updateRecord, deleteRecord, setFieldValue } from "../lib_bejson_Core_bejson_core";
import { validateDocument } from "../lib_bejson_Core_bejson_validators";

function check(cond: boolean, msg: string): void { if (!cond) throw new Error(msg); }
const U = (a: number, b: number) => a.toString(16).padStart(8, "0") + "-0000-4000-8000-" + b.toString(16).padStart(12, "0");
const throws = (fn: () => unknown): boolean => { try { fn(); return false; } catch { return true; } };
function doc105(): any {
  return { Format: "BEJSON", Format_Version: "105", Format_Creator: "Elton Boehnen", Records_Type: ["T"],
    Fields: [{ name: "name", type: "string", field_uuid: U(1, 1) }, { name: "age", type: "integer", field_uuid: U(2, 2) }],
    Values: [[U(3, 3), "a", 1]] };
}
function doc105db(): any {
  return { Format: "BEJSON", Format_Version: "105db", Format_Creator: "Elton Boehnen", Records_Type: ["D", "E"],
    Fields: [{ name: "Record_Type_Parent", type: "string", field_uuid: U(1, 1) }, { name: "dept", type: "string", Record_Type_Parent: "D", field_uuid: U(2, 2) }, { name: "emp", type: "string", Record_Type_Parent: "E", field_uuid: U(3, 3) }],
    Values: [["D", U(4, 4), "eng", null]] };
}
const valid = (d: any) => validateDocument(d).valid;

const tests: Record<string, () => void> = {
  baselines_valid() { check(valid(doc105()) && valid(doc105db()), "baselines must validate"); },
  addRecord105_ok() { const r = addRecord105(doc105(), ["b", 2]); check(valid(r.doc), "result valid"); },
  addRecord105_short_row() { check(throws(() => addRecord105(doc105(), ["b"])), "short row must throw"); },
  addRecord105_long_row() { check(throws(() => addRecord105(doc105(), ["b", 2, 3])), "long row must throw"); },
  addRecord105_wrong_type() { check(throws(() => addRecord105(doc105(), ["b", "x"])), "string in integer must throw"); },
  addRecord105_bool_in_integer() { check(throws(() => addRecord105(doc105(), ["b", true])), "bool in integer must throw"); },
  addRecord105db_bad_discriminator() { check(throws(() => addRecord105(doc105db(), ["Z", "x", null])), "bad discriminator must throw"); },
  addRecord105db_ok() { check(valid(addRecord105(doc105db(), ["E", null, "al"]).doc), "valid 105db add"); },
  writeCell_wrong_type() { const d = doc105(); check(throws(() => writeCell(d, U(3, 3), U(2, 2), "x")), "writeCell type must throw"); },
  writeCell_ok() { const d = doc105(); const r = writeCell(d, U(3, 3), U(2, 2), 7); check(r.doc.Values[0][2] === 7, "written"); },
  writers_104_refuse_105() {
    const d = doc105();
    check(throws(() => appendRecord(d, ["b", 2])), "appendRecord");
    check(throws(() => updateRecord(d, 0, ["b", 2])), "updateRecord");
    check(throws(() => deleteRecord(d, 0)), "deleteRecord");
    check(throws(() => setFieldValue(d, 0, "name", "z")), "setFieldValue");
  },
  validator_short_row() { const d = doc105(); d.Values = [[U(3, 3), "a"]]; check(!valid(d), "short row"); },
  validator_wrong_cell_type() { const d = doc105(); d.Values[0][2] = "x"; check(!valid(d), "type"); },
  validator_105_two_record_types() { const d = doc105(); d.Records_Type = ["T", "U"]; check(!valid(d), "105 needs exactly 1"); },
  validator_105a_complex_type() { const d = doc105(); d.Format_Version = "105a"; d.Fields[1].type = "array"; d.Values[0][2] = [1]; check(!valid(d), "105a forbids array"); },
  validator_105_custom_header_forbidden() { const d = doc105(); d.Extra = 1; check(!valid(d), "105 custom header"); },
  validator_105a_custom_header_allowed() { const d = doc105(); d.Format_Version = "105a"; d.Extra = 1; check(valid(d), "105a custom header ok"); },
  validator_105db_discriminator() { const d = doc105db(); d.Values[0][0] = "Z"; check(!valid(d), "105db discriminator"); },
};

let failed = 0;
for (const [name, fn] of Object.entries(tests)) {
  try { fn(); console.log("PASS " + name); } catch (e: any) { failed++; console.log("FAIL " + name + ": " + e.message); }
}
console.log(`${Object.keys(tests).length - failed} passed, ${failed} failed`);
if (failed) throw new Error("test failures");
