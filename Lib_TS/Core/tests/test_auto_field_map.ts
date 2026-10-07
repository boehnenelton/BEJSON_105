/**
 * Library:        test_auto_field_map.ts
 * Family:         Core
 * Description:    Tests that the TS field map is SELF-MAINTAINING (callers never build/refresh it):
 *                 parity with Python TestAutoFieldMap and JS bejson_cache.test.js.
 * Version:        1.0.0
 * Date:           2026-10-03
 * Author:         Elton Boehnen
 * Contact:        eltonboehnen@gmail.com | boehnenelton2024.pages.dev | github.com/boehnenelton
 * Format_Creator: Elton Boehnen
 * RELATIONAL_ID:  5b0c3a52-7e1d-4c8a-9a64-2f7d1e6b9c10
 * Release_Version: 300
 */
import * as assert from "assert";
import { parse, getFieldIndex, getFieldValue, setFieldValue } from "../lib_bejson_Core_bejson_core";
import {
  bejson_core_get_field_map, bejson_core_get_field_index, bejson_core_get_field_map_105,
  bejson_core_get_field_cache, bejson_core_warm,
} from "../lib_bejson_Core_bejson_field_map";

let n = 0;
const t = (name: string, fn: () => void) => { fn(); n++; console.log("  ok - " + name); };
const j105 = () => JSON.stringify({ Format: "BEJSON", Format_Version: "105", Format_Creator: "x", Records_Type: ["T"],
  Fields: [{ name: "a", type: "string", field_uuid: "ua" }, { name: "b", type: "string", field_uuid: "ub" }],
  Values: [["r1", "x", "y"]] });
const j104 = () => JSON.stringify({ Format: "BEJSON", Format_Version: "104", Format_Creator: "x", Records_Type: ["T"],
  Fields: [{ name: "a", type: "string" }, { name: "b", type: "string" }], Values: [["x", "y"]] });

t("parse() leaves a 105 doc warm: first lookup is a cache hit (no rebuild)", () => {
  const d = parse(j105());
  const m1 = bejson_core_get_field_map_105(d);
  assert.strictEqual(bejson_core_get_field_map_105(d), m1);
});
t("105 byNameRow carries the record_uuid offset", () => {
  const d = parse(j105());
  assert.strictEqual(bejson_core_get_field_cache(d).byNameRow.get("a"), 1);
  assert.strictEqual((d.Values[0] as any[])[bejson_core_get_field_cache(d).byNameRow.get("b")!], "y");
});
t("105db offset is 2", () => {
  const d = parse(j105()); (d as any).Format_Version = "105db";
  assert.strictEqual(bejson_core_get_field_cache(d).byNameRow.get("a"), 2);
});
t("getFieldIndex (throwing core API) uses the cache, still throws on miss", () => {
  const d = parse(j104());
  assert.strictEqual(getFieldIndex(d, "b"), 1);
  assert.throws(() => getFieldIndex(d, "nope"));
});
t("immutable mutations return docs whose first lookup just works", () => {
  const d = parse(j104());
  const d2 = setFieldValue(d, 0, "b", "z");
  assert.strictEqual(getFieldValue(d2, 0, "b"), "z");
});
t("never stale: in-place Fields edit is noticed (104 and 105)", () => {
  const d = parse(j104());
  assert.strictEqual(bejson_core_get_field_index(d, "c"), -1);
  d.Fields.push({ name: "c", type: "string" } as any);
  assert.strictEqual(bejson_core_get_field_index(d, "c"), 2);
  d.Fields.reverse();
  assert.strictEqual(bejson_core_get_field_map(d)["a"], 2);
  const d5 = parse(j105());
  d5.Fields[0].name = "a2";
  assert.strictEqual(bejson_core_get_field_index(d5, "a"), -1);
  assert.strictEqual(bejson_core_get_field_index(d5, "a2"), 0);
});
t("prototype keys are not fields", () => {
  const m = bejson_core_get_field_map(parse(j104()));
  assert.strictEqual((m as any)["toString"], undefined);
  assert.strictEqual(bejson_core_get_field_index(parse(j104()), "toString"), -1);
});
t("warm() is a no-op for 104 and returns the same doc", () => {
  const d = JSON.parse(j104()); assert.strictEqual(bejson_core_warm(d), d);
});
console.log("TS field-map tests passed: " + n);
