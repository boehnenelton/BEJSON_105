/**
 * Library:        test_phase_105_parity.ts
 * Family:         Core (tests)
 * Description:    Functional test suite for the Phase 2.7 TypeScript
 *                 parity port of Format 105 ("Integrity Era") -- covers
 *                 upgradeTo105, resolveFieldIndex, writeCell, defineField,
 *                 addRecord105, removeField, deleteRecord105,
 *                 verify105Integrity, the UUID field map, and the validator's
 *                 check105StrictIntegrity, plus
 *                 a 104-series regression section proving every new
 *                 function correctly rejects a legacy document.
 *
 *                 No test framework dependency assumed (Jest/Mocha/etc.
 *                 not assumed installed) -- plain assert()/assertThrows()
 *                 helpers, matching this TS library's existing lack of a
 *                 test framework. Compile and run with plain tsc + node:
 *
 *                     cd Lib_TS/Core
 *                     npx tsc --outDir /tmp/ts105test \
 *                       --target ES2021 --module commonjs \
 *                       --lib ES2021,DOM \
 *                       --esModuleInterop --skipLibCheck \
 *                       tests/test_phase_105_parity.ts
 *                     node /tmp/ts105test/tests/test_phase_105_parity.js *
 * Version:        1.3.0
 * Date:           2026-09-25
 * Author:         Elton Boehnen
 * Contact:        eltonboehnen@gmail.com | boehnenelton2024.pages.dev | github.com/boehnenelton
 * Format_Creator: Elton Boehnen
 * RELATIONAL_ID:  3af4a56d-a477-4102-8195-964ff4e9c6fd
 * Release_Version: 300
 *
 * Changelog:
 *   1.2.0 - Removed upsert105/rowChecksum/verifyRowChecksums/paginate105 tests;
 *           added UUID field map tests (coverage, caching, rename stability).
 *   1.3.0 - Added automatic-maintenance tests: in-place edits are noticed on the
 *           next lookup with no manual rebuild.
 *   1.1.0 - Removed schema-constraint tests/imports (required/unique/enum/
 *           min/max/length, check105SchemaConstraints). 53 pass / 0 fail.
 */

import {
  BEJSONDocument,
  BEJSONCoreError,
} from "../lib_bejson_Core_bejson_types";
import {
  createEmpty104,
  createEmpty104db,
} from "../lib_bejson_Core_bejson_core";
import {
  resolveFieldIndex,
  writeCell,
  defineField,
  addRecord105,
  removeField,
  deleteRecord105,
  verify105Integrity,
  upgradeTo105,
} from "../lib_bejson_Core_bejson_core_105";
import { bejson_core_get_field_map_105 } from "../lib_bejson_Core_bejson_field_map";
import {
  validateDocument,
  check105StrictIntegrity,
} from "../lib_bejson_Core_bejson_validators";

let passed = 0;
let failed = 0;

function assert(cond: boolean, label: string) {
  if (cond) {
    passed++;
    console.log(`  ok - ${label}`);
  } else {
    failed++;
    console.log(`  FAIL - ${label}`);
  }
}

function assertThrows(fn: () => void, label: string, expectedCode?: number) {
  try {
    fn();
    failed++;
    console.log(`  FAIL - ${label} (did not throw)`);
  } catch (e) {
    if (expectedCode !== undefined && e instanceof BEJSONCoreError && e.code !== expectedCode) {
      failed++;
      console.log(`  FAIL - ${label} (wrong code: ${e.code}, expected ${expectedCode})`);
    } else {
      passed++;
      console.log(`  ok - ${label}`);
    }
  }
}

function make104(): BEJSONDocument {
  return createEmpty104("Test", [
    { name: "full_name", type: "string" },
    { name: "age", type: "integer" },
  ], [["Elton", 40], ["Bob", 30], ["Carol", 55]]);
}

async function main() {
  console.log("=== Section 1: upgradeTo105 ===");
  {
    const doc104 = make104();
    const doc105 = upgradeTo105(doc104);
    assert(doc105.Format_Version === "105", "104 -> 105");
    assert(doc105.Values.length === 3, "record count preserved");
    assert((doc105.Values[0][0] as string).length === 36, "record_uuid generated");
    assert(doc105.Values[0].slice(1).join(",") === doc104.Values[0].join(","), "original values preserved");
    assert(doc104.Format_Version === "104", "original doc104 untouched (immutability)");

    const fieldUuids = doc105.Fields.map((f) => f.field_uuid);
    assert(new Set(fieldUuids).size === fieldUuids.length, "every field_uuid unique");

    // 104a -> 105a (the exact bug Python shipped with initially)
    const doc104a = { ...doc104, Format_Version: "104a" as const };
    const doc105a = upgradeTo105(doc104a);
    assert(doc105a.Format_Version === "105a", "104a -> 105a (not silently 105)");

    // 104db -> 105db, discriminator survives at index 0
    const doc104db = createEmpty104db(["TypeA", "TypeB"], [
      { name: "Record_Type_Parent", type: "string" },
      { name: "val", type: "string" },
    ]);
    doc104db.Values = [["TypeA", "x"], ["TypeB", "y"]];
    const doc105db = upgradeTo105(doc104db);
    assert(doc105db.Format_Version === "105db", "104db -> 105db");
    assert(doc105db.Values[0][0] === "TypeA", "discriminator survives at index 0");
    assert((doc105db.Values[0][1] as string).length === 36, "record_uuid at index 1 for 105db");
  }

  console.log("\n=== Section 2: resolveFieldIndex / writeCell ===");
  let doc = upgradeTo105(make104());
  {
    const idx = resolveFieldIndex(doc, "full_name");
    assert(idx === 1, "resolveFieldIndex by name (offset 1)");

    const recordUuid = doc.Values[0][0] as string;
    const fieldUuid = doc.Fields[0].field_uuid as string;
    const result = writeCell(doc, recordUuid, fieldUuid, "Elton Boehnen", { expectedRow: 99, expectedCol: 99 });
    assert(result.healed === true, "writeCell heals drifted coordinates");
    assert(result.doc.Values[0][1] === "Elton Boehnen", "writeCell wrote correct cell");
    assert(doc.Values[0][1] === "Elton", "original doc untouched (immutability)");
    doc = result.doc;

    assertThrows(() => writeCell(doc, "nonexistent", fieldUuid, "x"), "writeCell unknown record_uuid throws");
  }

  console.log("\n=== Section 3: defineField ===");
  {
    const r1 = defineField(doc, "email", "string");
    assert(typeof r1.fieldUuid === "string", "defineField returns field_uuid");
    assert(r1.doc.Values.every((row) => row.length === 4), "defineField pads existing rows");
    doc = r1.doc;

    assertThrows(() => defineField(doc, "full_name", "string"), "defineField duplicate name throws");
    assertThrows(() => defineField(doc, "x", "not_a_type"), "defineField invalid type throws");
    assertThrows(() => defineField(doc, "x", "string", { fk_on_delete: "restrict" }), "defineField fk_on_delete without target throws");

    const r2 = defineField(doc, "status", "string");
    doc = r2.doc;
  }

  console.log("\n=== Section 4: addRecord105 / removeField / deleteRecord105 ===");
  {
    const r = addRecord105(doc, ["Dana", 22, "dana@x.com", "active"]);
    assert(typeof r.recordUuid === "string", "addRecord105 returns record_uuid");
    assert(r.doc.Values.length === doc.Values.length + 1, "addRecord105 appended a row");
    doc = r.doc;

    const targetUuid = doc.Values[0][0] as string;
    const emailFieldUuid = doc.Fields.find((f) => f.name === "email")!.field_uuid as string;
    doc = removeField(doc, emailFieldUuid);
    assert(!doc.Fields.some((f) => f.name === "email"), "removeField removed the field");
    assert(doc.Values.every((row) => row.length === 4), "removeField removed the column from every row");

    const beforeCount = doc.Values.length;
    doc = deleteRecord105(doc, targetUuid);
    assert(doc.Values.length === beforeCount - 1, "deleteRecord105 removed exactly one row");
    assert(!doc.Values.some((row) => row[0] === targetUuid), "deleted record_uuid gone");

    assertThrows(() => deleteRecord105(doc, "nonexistent"), "deleteRecord105 unknown uuid throws");
  }

  console.log("\n=== Section 5: verify105Integrity ===");
  {
    const report = verify105Integrity(doc);
    assert(report.ok === true, "verify105Integrity ok on healthy doc");

    const corrupted = { ...doc, Fields: doc.Fields.map((f, i) => (i === 0 ? { ...f, field_uuid: undefined } : f)) };
    const badReport = verify105Integrity(corrupted as BEJSONDocument);
    assert(badReport.ok === false, "verify105Integrity catches missing field_uuid");
  }

  console.log("\n=== Section 6: UUID-aware field map ===");
  {
    const fm = bejson_core_get_field_map_105(doc);
    assert(fm.byName.size === doc.Fields.length, "field map byName covers every field");
    assert(fm.byUuid.size === doc.Fields.length, "field map byUuid covers every field");
    doc.Fields.forEach((f, i) => {
      assert(fm.byUuid.get(f.field_uuid as string) === i && fm.byName.get(f.name) === i, `field map resolves '${f.name}' by name and uuid to ${i}`);
    });
    assert(bejson_core_get_field_map_105(doc) === fm, "field map is cached for an unchanged doc");

    // automatic maintenance: edit the SAME document object in place, never rebuild by hand
    const live = { ...doc, Fields: [...doc.Fields] };
    const liveBefore = bejson_core_get_field_map_105(live);
    live.Fields.push({ name: "added_by_hand", type: "string", field_uuid: "u-hand" });
    const liveAfter = bejson_core_get_field_map_105(live);
    assert(liveAfter !== liveBefore && liveAfter.byName.get("added_by_hand") === live.Fields.length - 1, "in-place append is noticed on the next lookup");
    assert(liveAfter.byUuid.get("u-hand") === live.Fields.length - 1, "new field resolves by uuid with no manual rebuild");
    live.Fields[0] = { ...live.Fields[0], name: "renamed_in_place" };
    assert(bejson_core_get_field_map_105(live).byName.get("renamed_in_place") === 0, "in-place rename is noticed on the next lookup");
    assert(bejson_core_get_field_map_105(live) === bejson_core_get_field_map_105(live), "unchanged doc reuses the same map");

    // the 105 functions themselves ride the same automatic map
    const viaApi = defineField(live as any, "late_field", "string");
    assert(resolveFieldIndex(viaApi.doc, "late_field") === viaApi.doc.Fields.length, "defineField then lookup works with no manual step");

    // rename-stability: same field_uuid, new name -> uuid still resolves, old name gone
    const target = doc.Fields[0];
    const renamed = { ...doc, Fields: doc.Fields.map((f, i) => (i === 0 ? { ...f, name: "renamed_field" } : f)) };
    const fm2 = bejson_core_get_field_map_105(renamed);
    assert(fm2 !== fm, "rename produces a fresh field map");
    assert(fm2.byUuid.get(target.field_uuid as string) === 0, "uuid still resolves after rename");
    assert(fm2.byName.get("renamed_field") === 0 && !fm2.byName.has(target.name), "name index follows the rename");
  }

  console.log("\n=== Section 9: validateDocument for 105-series ===");
  {
    const vdoc = upgradeTo105(make104());
    const res = validateDocument(vdoc);
    assert(res.valid === true, "validateDocument passes clean 105 doc");

    // Fail-on-Switch
    const fakeDoc = { ...make104(), Format_Version: "105" as const };
    const failRes = validateDocument(fakeDoc);
    assert(failRes.valid === false, "validateDocument Fail-on-Switch catches header-only bump");

    // direct check function
    const strictErrors = check105StrictIntegrity(vdoc);
    assert(strictErrors.length === 0, "check105StrictIntegrity clean on healthy doc");
  }

  console.log("\n=== Section 10: 104-series regression (must be untouched) ===");
  {
    const doc104 = make104();
    const res = validateDocument(doc104);
    assert(res.valid === true, "104-series validateDocument still passes");

    assertThrows(() => resolveFieldIndex(doc104, "full_name"), "resolveFieldIndex rejects 104-series", 81);
    assertThrows(() => writeCell(doc104, "x", "y", "z"), "writeCell rejects 104-series", 81);
    assertThrows(() => addRecord105(doc104, ["x"]), "addRecord105 rejects 104-series", 81);
    assertThrows(() => deleteRecord105(doc104, "x"), "deleteRecord105 rejects 104-series", 81);
    assertThrows(() => defineField(doc104, "x", "string"), "defineField rejects 104-series", 81);
  }

  console.log(`\n${"=".repeat(60)}`);
  console.log(`TOTAL: ${passed} passed, ${failed} failed`);
  console.log("=".repeat(60));
  if (failed > 0) throw new Error(`${failed} test(s) failed`);
}

main().catch((e) => {
  console.error("UNCAUGHT ERROR:", e);
  throw e; // non-zero Node exit code without needing @types/node's `process`
});
