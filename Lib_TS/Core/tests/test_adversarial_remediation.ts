/**
 * Library:        test_adversarial_remediation.ts
 * Family:         Core
 * Description:    Regression tests for the 2026-10 adversarial review: 105db column mapping
 *                 (resolveFieldIndex / writeCell / removeField / field map / FK cascade) and
 *                 key-cache hygiene.
 * Version:        1.0.0
 * Date:           2026-10-09
 * Author:         Elton Boehnen
 * Contact:        eltonboehnen@gmail.com | boehnenelton2024.pages.dev | github.com/boehnenelton
 * Format_Creator: Elton Boehnen
 * RELATIONAL_ID:  ef93cba6-bf18-4dee-a9c0-57af1dbabb39
 * Release_Version: 300
 */
import * as assert from "assert";
import { resolveFieldIndex, writeCell, removeField } from "../lib_bejson_Core_bejson_core_105";
import { bejson_core_get_field_cache } from "../lib_bejson_Core_bejson_field_map";
import { clearKeyCache } from "../lib_bejson_Core_bejson_core";

let n = 0;
const t = (name: string, fn: () => void) => { fn(); n++; console.log("  ok - " + name); };
const doc105db = (): any => ({
  Format: "BEJSON", Format_Version: "105db", Format_Creator: "x", Records_Type: ["User"],
  Fields: [{ name: "Record_Type_Parent", type: "string", field_uuid: "f0" },
           { name: "user_id", type: "string", field_uuid: "f1" },
           { name: "email", type: "string", field_uuid: "f2" }],
  Values: [["User", "ru-1", "usr_1", "usr@test.com"]],
});

t("105db resolveFieldIndex: RTP=0, user_id=2, email=3", () => {
  const d = doc105db();
  assert.strictEqual(resolveFieldIndex(d, "Record_Type_Parent"), 0);
  assert.strictEqual(resolveFieldIndex(d, "user_id"), 2);
  assert.strictEqual(resolveFieldIndex(d, "email"), 3);
});
t("105db writeCell hits the named field only", () => {
  const r = writeCell(doc105db(), "ru-1", "f1", "usr_2");
  assert.strictEqual(r.col, 2);
  assert.deepStrictEqual(r.doc.Values[0], ["User", "ru-1", "usr_2", "usr@test.com"]);
});
t("105db field-map byNameRow lines up with the row", () => {
  const d = doc105db();
  const m = bejson_core_get_field_cache(d).byNameRow;
  assert.strictEqual(d.Values[0][m.get("user_id")!], "usr_1");
  assert.strictEqual(d.Values[0][m.get("email")!], "usr@test.com");
});
t("105db removeField removes the right column; discriminator is protected", () => {
  const d2 = removeField(doc105db(), "user_id");
  assert.deepStrictEqual(d2.Values[0], ["User", "ru-1", "usr@test.com"]);
  assert.throws(() => removeField(doc105db(), "Record_Type_Parent"));
});
t("clearKeyCache is exported", () => { assert.strictEqual(typeof clearKeyCache, "function"); clearKeyCache(); });

console.log("TS adversarial-remediation tests passed: " + n);
