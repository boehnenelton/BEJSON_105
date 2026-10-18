/**
 * Library:         test_field_map_integrity.ts
 * Family:          Core
 * Module Purpose:  Regression tests for the field-map cache: forged or persisted maps, stale caches, shared-map isolation, comma/duplicate field names, validator rules, lookup cost.
 * Architecture:    Standalone script; resolves the library modules relative to this file (no absolute paths).
 * Format_Scope:    104 | 104a | 104db (generic)
 * Glossary:        BEJSON 104, 104a and 104db are the three file formats (Format_Version). 104db = ONE file holding 2+ entity types
 *                  (Record_Type_Parent discriminator, null-padding). MFDB is NOT a format and NOT 104db: it is a layer made of one 104a manifest
 *                  (104a.mfdb.bejson) plus dense 104 entity files linked by Parent_Hierarchy. MFDB-132 = an MFDB packed into one Chunked-104a document.
 * Version:         1.0.0
 * Release_Version: 300
 * Date:            2026-10-15
 * Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
 * Format_Creator:  Elton Boehnen
 * RELATIONAL_ID:   b0d58a7c-0e61-4c7b-bf72-21640f78730b
 * Usage: tsc --target es2020 --module commonjs --moduleResolution node10 --skipLibCheck --outDir out test_field_map_integrity.ts && node out/tests/test_field_map_integrity.js
 */
import { bejson_core_get_field_map, bejson_core_get_field_index } from "../lib_bejson_Core_bejson_field_map";
import { validateDocument } from "../lib_bejson_Core_bejson_validators";

const names = ["f0", "f1", "f2", "f3", "f4", "f5"];
function makeDoc(list: string[] = names, version = "104a", extra: Record<string, unknown> = {}): any {
  return Object.assign({
    Format: "BEJSON", Format_Version: version, Format_Creator: "Elton Boehnen", Records_Type: ["T"],
    Fields: list.map(n => ({ name: n, type: "string" })), Values: [list.map(n => "v_" + n)],
  }, extra);
}
function check(cond: boolean, msg: string): void { if (!cond) throw new Error(msg); }

const tests: Record<string, () => void> = {
  forged_inner_swap_with_size_key() {
    const forged: Record<string, number> = {};
    names.forEach((n, i) => { forged[n] = i; });
    forged.f1 = 2; forged.f2 = 1; forged.__bejson_field_count = 6;
    const doc = JSON.parse(JSON.stringify(makeDoc(names, "104a", { _bejson_field_map: forged })));
    check(doc.Values[0][bejson_core_get_field_index(doc, "f1")] === "v_f1", "forged map was trusted");
  },
  stale_after_push_and_shift() {
    const doc = makeDoc(["a", "b", "c"]);
    bejson_core_get_field_map(doc);
    doc.Fields.push({ name: "d" });
    check(bejson_core_get_field_index(doc, "d") === 3, "stale after push");
    doc.Fields.shift();
    check(bejson_core_get_field_index(doc, "a") === -1 && bejson_core_get_field_index(doc, "b") === 0, "stale after shift");
  },
  maps_not_shared_between_documents() {
    const a = makeDoc(), b = makeDoc();
    bejson_core_get_field_map(a)["f0"] = 99;
    check(bejson_core_get_field_map(b)["f0"] === 0, "shared map leaked");
  },
  comma_names_do_not_collide() {
    const one = makeDoc(["a,b", "c"]), two = makeDoc(["a", "b,c"]);
    bejson_core_get_field_map(one);
    check(bejson_core_get_field_index(two, "a") === 0 && bejson_core_get_field_index(two, "b,c") === 1, "cache key collision");
  },
  validator_rules() {
    for (const v of ["104", "104a"]) {
      check(validateDocument(makeDoc(["a", "b"], v)).valid, v + " plain should validate");
      const honest = makeDoc(["a", "b"], v); bejson_core_get_field_map(honest);
      check(validateDocument(honest).valid, v + " honest cached should validate");
      check(!validateDocument(makeDoc(["a", "b"], v, { _bejson_field_map: { a: 1, b: 0 } })).valid, v + " forged must be rejected");
    }
    check(!validateDocument(makeDoc(["x", "x"])).valid, "duplicate names must be rejected");
  },
  reserved_underscore_keys() {
    for (const v of ["104", "104a"]) {
      check(!validateDocument(makeDoc(["a", "b"], v, { _anything: 1 })).valid, v + " unknown _ key must be rejected");
    }
    check(validateDocument(makeDoc(["a", "b"], "104a", { _nestingFieldMap: {} })).valid, "in-memory nesting map allowed");
    check(validateDocument(makeDoc(["a", "b"], "104a", { Custom_Header: 1 })).valid, "104a custom header still fine");
  },
};

let failed = 0;
const proc = (globalThis as any).process;
for (const name of Object.keys(tests)) {
  try { tests[name](); proc.stdout.write("PASS " + name + "\n"); }
  catch (e) { failed++; proc.stderr.write("FAIL " + name + ": " + (e as Error).message + "\n"); }
}
proc.exit(failed ? 1 : 0);
