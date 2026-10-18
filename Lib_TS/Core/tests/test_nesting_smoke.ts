/**
 * Library:         test_nesting_smoke.ts
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
 * RELATIONAL_ID:   e8210873-eb0c-49b2-9fb7-d8269205d0f0
 * Changelog:
 *   1.1.0 (2026-10-16) - Added tests: Core validator rules apply to nested cells; same-schema documents do not share cache entries.
 *   1.0.2 (2026-10-16) - Query API now imported from core_nesting (nesting_query merged).
 *   1.0.1 (2026-10-16) - Reads codes 130-139 from lib_bejson_Core_bejson_types (nesting errors file removed).
 */
import * as assert from "assert";
import { bejsonNestingScan, bejsonNestingMutate, bejsonNestingFlatten, bejsonNestingGetFieldMap, bejsonNestingSummary, bejsonNestingQuery, bejsonNestingGetPath, bejsonNestingCacheClear } from "../lib_bejson_Core_bejson_core_nesting";
import { CORE_NESTING_ERRORS } from "../lib_bejson_Core_bejson_types";

let n = 0;
const t = (name: string, fn: () => void): void => { fn(); n++; console.log("  ok - " + name); };
const INNER = { Format: "BEJSON", Format_Version: "104", Format_Creator: "Elton Boehnen", Records_Type: ["Items"],
  Fields: [{ name: "sku", type: "string" }, { name: "qty", type: "integer" }], Values: [["a", 1], ["b", 2]] };
const outer = (): any => ({ Format: "BEJSON", Format_Version: "104", Format_Creator: "Elton Boehnen", Records_Type: ["Order"],
  Fields: [{ name: "id", type: "string" }, { name: "items", type: "string" }], Values: [["o1", JSON.stringify(INNER)], ["o2", null]] });

t("scan", () => {
  const r: any = bejsonNestingScan(outer(), false);
  assert.deepStrictEqual([r.nestedFound, r.nestedValid, r.nestedInvalid, r.scannedCells, r.maxDepthSeen], [1, 1, 0, 4, 1]);
  assert.ok(bejsonNestingSummary(r).includes("Scan Summary"));
  const cells = bejsonNestingFlatten(r);
  assert.strictEqual(cells.length, 1);
  assert.deepStrictEqual(bejsonNestingGetFieldMap(cells[0]), { sku: 0, qty: 1 });
});
t("mutate appends field and null-pads", () => {
  const doc = outer(); const r: any = bejsonNestingScan(doc, false);
  bejsonNestingMutate(doc, r.cells[0], (d: any) => { d.Fields.push({ name: "note", type: "string" }); });
  assert.deepStrictEqual(JSON.parse(doc.Values[0][1]).Values[0], ["a", 1, null]);
});
t("mutate rejects field removal", () => {
  const doc = outer(); const r: any = bejsonNestingScan(doc, false);
  assert.throws(() => bejsonNestingMutate(doc, r.cells[0], (d: any) => { d.Fields.pop(); }));
});
t("query", () => {
  assert.strictEqual(bejsonNestingQuery(outer(), "items").length, 2);
  assert.strictEqual(bejsonNestingGetPath(outer(), "nope", "DEF"), "DEF");
  assert.throws(() => bejsonNestingQuery(outer(), "bad..path"));
});
const outerWith = (inner: unknown): any => { const d = outer(); d.Values[0][1] = JSON.stringify(inner); return d; };
t("Core validator rules apply to nested cells", () => {
  const badCreator = { ...INNER, Format_Creator: "Someone" };
  const dupFields = { ...INNER, Fields: [{ name: "a", type: "string" }, { name: "a", type: "string" }], Values: [["x", "y"]] };
  for (const bad of [badCreator, dupFields]) {
    bejsonNestingCacheClear();
    const r: any = bejsonNestingScan(outerWith(bad), false);
    assert.deepStrictEqual([r.nestedValid, r.nestedInvalid], [0, 1]);
  }
});
t("same-schema different content is not served from cache", () => {
  bejsonNestingCacheClear();
  bejsonNestingScan(outerWith(INNER));
  const r: any = bejsonNestingScan(outerWith({ ...INNER, Format_Creator: "Someone" }));
  assert.strictEqual(r.nestedInvalid, 1);
});
t("error codes unchanged (130-139)", () => {
  const vals = Object.values(CORE_NESTING_ERRORS).sort((a, b) => a - b);
  assert.deepStrictEqual(vals, [130, 131, 132, 133, 134, 135, 136, 137, 138, 139]);
});
console.log(`\n${n} passed`);
