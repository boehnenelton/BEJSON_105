/**
 * Library:        test_phase6_ref_integrity.ts
 * Family:         Core (tests)
 * Description:    Functional test suite for the Phase 6 TypeScript
 *                 Referential Integrity port -- checkReferentialIntegrity
 *                 (standalone audit, mfdb_validators.ts), checkFKWrite,
 *                 checkEntityDroppable, resolveDeleteDependents, and the
 *                 enable/disable/isRefIntegrityEnabled advisory switch
 *                 (all mfdb_core.ts).
 *
 *                 Entirely in-memory -- createManifest/registerEntity/
 *                 upgradeTo105/defineField/addRecord105 are all pure
 *                 functions, so this suite touches zero filesystem and
 *                 sidesteps the pre-existing fs/path bug elsewhere in
 *                 mfdb_core.ts entirely (that bug is in the Node-only
 *                 debug/federation functions, untouched by Phase 6).
 *
 *                 No test framework dependency, matching this library's
 *                 existing convention. Compile and run:
 *
 *                     cd Lib_TS/Core
 *                     npx tsc --outDir /tmp/ts105test \
 *                       --target ES2021 --module commonjs \
 *                       --lib ES2021,DOM \
 *                       --esModuleInterop --skipLibCheck \
 *                       tests/test_phase6_ref_integrity.ts
 *                     node /tmp/ts105test/tests/test_phase6_ref_integrity.js
 *
 * Version:        1.0.0
 * Date:           2026-08-26
 * Author:         Elton Boehnen
 * Contact:        eltonboehnen@gmail.com | boehnenelton2024.pages.dev | github.com/boehnenelton
 * Format_Creator: Elton Boehnen
 * RELATIONAL_ID:  9e2c7a4f-1d6b-4c83-a5f0-3e8d2b7c9a41
 * Release_Version: 300
 */

import { BEJSONDocument, MFDBCoreError } from "../lib_bejson_Core_bejson_types";
import { createEmpty104 } from "../lib_bejson_Core_bejson_core";
import { upgradeTo105, defineField, addRecord105 } from "../lib_bejson_Core_bejson_core_105";
import {
  createManifest,
  registerEntity,
  enableRefIntegrity,
  disableRefIntegrity,
  isRefIntegrityEnabled,
  checkFKWrite,
  checkEntityDroppable,
  resolveDeleteDependents,
} from "../lib_bejson_Core_mfdb_core";
import { checkReferentialIntegrity, validateDatabase } from "../lib_bejson_Core_mfdb_validators";

let passed = 0;
let failed = 0;

function assert(cond: boolean, label: string) {
  if (cond) { passed++; console.log(`  ok - ${label}`); }
  else { failed++; console.log(`  FAIL - ${label}`); }
}

function assertThrows(fn: () => void, label: string, expectedCode?: number) {
  try {
    fn();
    failed++;
    console.log(`  FAIL - ${label} (did not throw)`);
  } catch (e) {
    if (expectedCode !== undefined && e instanceof MFDBCoreError && e.code !== expectedCode) {
      failed++;
      console.log(`  FAIL - ${label} (wrong code: ${e.code}, expected ${expectedCode})`);
    } else {
      passed++;
      console.log(`  ok - ${label}`);
    }
  }
}

// ---------------------------------------------------------------------------
// Fixture: authors / books / reviews, all 105-series
// ---------------------------------------------------------------------------

/**
 * NOTE: every registerEntity() call below explicitly passes record_count: 0.
 * This is a workaround, not incidental -- registerEntity leaves optional
 * MFDBManifestRecord fields as `null` when omitted, and appendRecord's
 * _coerceValue() calls parseInt(null, 10) for any "integer"-typed field,
 * which is NaN, which throws BEJSONCoreError("Coercion failed."). This is
 * a real, separate, pre-existing bug in lib_bejson_Core_bejson_core.ts's
 * coercion (or arguably in registerEntity for passing null into it) --
 * found while writing this suite, NOT fixed here since it's outside Phase
 * 6's scope and _coerceValue is shared machinery other things may already
 * depend on in ways this suite can't fully audit. Flagged for Elton.
 */
function buildFixture() {
  let manifest = createManifest({ mfdb_version: "1.0", db_name: "test_db" });

  let authors: BEJSONDocument = upgradeTo105(createEmpty104("authors", [{ name: "author_name", type: "string" }], []));
  let books: BEJSONDocument = upgradeTo105(createEmpty104("books", [{ name: "title", type: "string" }], []));
  const bDef = defineField(books, "author_fk", "string", { fk_target_entity: "authors", fk_on_delete: "restrict" });
  books = bDef.doc;

  let reviews: BEJSONDocument = upgradeTo105(createEmpty104("reviews", [{ name: "review_text", type: "string" }], []));
  const rDef = defineField(reviews, "book_fk", "string", { fk_target_entity: "books", fk_on_delete: "cascade" });
  reviews = rDef.doc;

  manifest = registerEntity(manifest, { entity_name: "authors", file_path: "data/authors.bejson", record_count: 0 });
  manifest = registerEntity(manifest, { entity_name: "books", file_path: "data/books.bejson", record_count: 0 });
  manifest = registerEntity(manifest, { entity_name: "reviews", file_path: "data/reviews.bejson", record_count: 0 });

  return { manifest, authors, books, reviews };
}

function byName(authors: BEJSONDocument, books: BEJSONDocument, reviews: BEJSONDocument): Map<string, BEJSONDocument> {
  return new Map([["authors", authors], ["books", books], ["reviews", reviews]]);
}

function byPath(manifest: BEJSONDocument, authors: BEJSONDocument, books: BEJSONDocument, reviews: BEJSONDocument): Map<string, unknown> {
  return new Map([
    ["data/authors.bejson", authors],
    ["data/books.bejson", books],
    ["data/reviews.bejson", reviews],
  ]);
}

function main() {
  console.log("=== Section 1: enable/disable/isRefIntegrityEnabled (advisory switch) ===");
  {
    const { manifest } = buildFixture();
    assert(isRefIntegrityEnabled(manifest) === false, "default off");
    const on = enableRefIntegrity(manifest);
    assert(isRefIntegrityEnabled(on) === true, "enable sets true");
    assert(isRefIntegrityEnabled(manifest) === false, "original manifest untouched (immutability)");
    const off = disableRefIntegrity(on);
    assert(isRefIntegrityEnabled(off) === false, "disable sets false");
  }

  console.log("\n=== Section 2: checkFKWrite ===");
  {
    let { authors, books } = buildFixture();
    const authorResult = addRecord105(authors, ["Elton Boehnen"]);
    authors = authorResult.doc;
    const authorUuid = authorResult.recordUuid;

    const fkField = books.Fields.find((f) => f.name === "author_fk")!;
    checkFKWrite(fkField, authorUuid, authors); // must not throw
    passed++; console.log("  ok - valid FK value accepted");

    assertThrows(() => checkFKWrite(fkField, "nonexistent-uuid", authors), "unresolvable FK value throws", 39 /* FK_UNRESOLVED */);

    checkFKWrite(fkField, null, authors); // null always passes
    passed++; console.log("  ok - null FK value accepted (nullable)");

    assertThrows(() => checkFKWrite(fkField, authorUuid, undefined), "missing target doc throws", 43 /* FK_TARGET_ENTITY_UNKNOWN */);

    const doc104 = createEmpty104("x", [{ name: "y", type: "string" }], []);
    assertThrows(() => checkFKWrite(fkField, authorUuid, doc104), "104-series target doc throws", 43);
  }

  console.log("\n=== Section 3: checkEntityDroppable ===");
  {
    let { authors, books } = buildFixture();
    const a = addRecord105(authors, ["Elton"]);
    authors = a.doc;
    const b = addRecord105(books, ["Some Book", a.recordUuid]);
    books = b.doc;

    const entityDocs = byName(authors, books, upgradeTo105(createEmpty104("reviews", [{ name: "x", type: "string" }], [])));
    const refs = checkEntityDroppable(entityDocs, "authors");
    assert(refs.length === 1, "reports the one referencing row");
    assert(refs[0].entity === "books" && refs[0].recordUuid === b.recordUuid, "correct referencing record");

    const emptyRefs = checkEntityDroppable(entityDocs, "reviews");
    assert(emptyRefs.length === 0, "empty when nothing references it");
  }

  console.log("\n=== Section 4: resolveDeleteDependents -- restrict ===");
  {
    let { authors, books } = buildFixture();
    const a = addRecord105(authors, ["Elton"]);
    authors = a.doc;
    const b = addRecord105(books, ["Book", a.recordUuid]);
    books = b.doc;

    const entityDocs = byName(authors, books, upgradeTo105(createEmpty104("reviews", [{ name: "x", type: "string" }], [])));
    assertThrows(
      () => resolveDeleteDependents(entityDocs, "authors", a.recordUuid),
      "restrict blocks delete of referenced author",
      44 /* FK_RESTRICT_VIOLATION */
    );
    // confirm untouched
    assert(entityDocs.get("books")!.Values.length === 1, "original map untouched after a thrown restrict");
  }

  console.log("\n=== Section 5: resolveDeleteDependents -- cascade ===");
  {
    let { authors, books, reviews } = buildFixture();
    const a = addRecord105(authors, ["Elton"]); authors = a.doc;
    const b = addRecord105(books, ["Book", a.recordUuid]); books = b.doc;
    const r1 = addRecord105(reviews, ["Great!", b.recordUuid]); reviews = r1.doc;
    const r2 = addRecord105(reviews, ["Meh.", b.recordUuid]); reviews = r2.doc;

    const entityDocs = byName(authors, books, reviews);
    const resolved = resolveDeleteDependents(entityDocs, "books", b.recordUuid);
    assert(resolved.get("reviews")!.Values.length === 0, "both reviews cascade-removed");
    assert(entityDocs.get("reviews")!.Values.length === 2, "original map untouched (immutability)");
  }

  console.log("\n=== Section 6: resolveDeleteDependents -- null ===");
  {
    let authorsN: BEJSONDocument = upgradeTo105(createEmpty104("authors", [{ name: "author_name", type: "string" }], []));
    let booksN: BEJSONDocument = upgradeTo105(createEmpty104("books", [{ name: "title", type: "string" }], []));
    const bDef = defineField(booksN, "author_fk", "string", { fk_target_entity: "authors", fk_on_delete: "null" });
    booksN = bDef.doc;

    const a = addRecord105(authorsN, ["Elton"]); authorsN = a.doc;
    const b = addRecord105(booksN, ["Book", a.recordUuid]); booksN = b.doc;

    const entityDocs = new Map([["authors", authorsN], ["books", booksN]]);
    const resolved = resolveDeleteDependents(entityDocs, "authors", a.recordUuid);
    const bookRow = resolved.get("books")!.Values.find((r) => r[0] === b.recordUuid)!;
    const fkIdx = resolved.get("books")!.Fields.findIndex((f) => f.name === "author_fk") + 1;
    assert(bookRow[fkIdx] === null, "author_fk nulled instead of the book being deleted");
    assert(resolved.get("books")!.Values.length === 1, "book row still present");
  }

  console.log("\n=== Section 7: cascade cycle detection ===");
  {
    let a: BEJSONDocument = upgradeTo105(createEmpty104("entity_a", [{ name: "label", type: "string" }], []));
    let b: BEJSONDocument = upgradeTo105(createEmpty104("entity_b", [{ name: "label", type: "string" }], []));
    a = defineField(a, "b_fk", "string", { fk_target_entity: "entity_b", fk_on_delete: "cascade" }).doc;
    b = defineField(b, "a_fk", "string", { fk_target_entity: "entity_a", fk_on_delete: "cascade" }).doc;

    const ra = addRecord105(a, ["A1", null]); a = ra.doc;
    const rb = addRecord105(b, ["B1", ra.recordUuid]); b = rb.doc;
    // link a back to b (mutual cascade cycle)
    const aFkFieldUuid = a.Fields.find((f) => f.name === "b_fk")!.field_uuid as string;
    a = { ...a, Values: a.Values.map((row) => (row[0] === ra.recordUuid ? [row[0], row[1], rb.recordUuid] : row)) };

    const entityDocs = new Map([["entity_a", a], ["entity_b", b]]);
    assertThrows(
      () => resolveDeleteDependents(entityDocs, "entity_a", ra.recordUuid),
      "mutual cascade cycle raises, not infinite loop",
      45 /* FK_CASCADE_CYCLE */
    );
  }

  console.log("\n=== Section 8: checkReferentialIntegrity (standalone audit) ===");
  {
    let { manifest, authors, books, reviews } = buildFixture();
    const a = addRecord105(authors, ["Elton"]); authors = a.doc;
    const b = addRecord105(books, ["Book", a.recordUuid]); books = b.doc;

    const clean = checkReferentialIntegrity(manifest, byPath(manifest, authors, books, reviews));
    assert(clean.length === 0, "clean database reports zero findings");

    // plant an orphan directly
    const orphanBooks = { ...books, Values: books.Values.map((row) => [row[0], row[1], "totally-fake-uuid"]) };
    const withOrphan = checkReferentialIntegrity(manifest, byPath(manifest, authors, orphanBooks, reviews));
    assert(withOrphan.length === 1 && withOrphan[0].code === 39, "orphaned FK detected (FK_UNRESOLVED)");

    // 104-series entity never inspected
    const doc104 = createEmpty104("legacy", [{ name: "x", type: "string" }], [["y"]]);
    let m2 = registerEntity(createManifest({ mfdb_version: "1.0", db_name: "d2" }), { entity_name: "legacy", file_path: "data/legacy.bejson", record_count: 0 });
    const legacyResult = checkReferentialIntegrity(m2, new Map([["data/legacy.bejson", doc104]]));
    assert(legacyResult.length === 0, "104-series entity never inspected");
  }

  console.log("\n=== Section 9: wired into validateDatabase ===");
  {
    let { manifest, authors, books, reviews } = buildFixture();
    const a = addRecord105(authors, ["Elton"]); authors = a.doc;
    const orphanBooks = addRecord105(books, ["Book", "nonexistent-author"]).doc;

    const res = validateDatabase(manifest, byPath(manifest, authors, orphanBooks, reviews));
    assert(res.valid === false, "validateDatabase catches the orphan via the new FK audit");
    assert(res.errors.some((e) => e.message.includes("L3-FK")), "error tagged with L3-FK marker");
  }

  console.log(`\n${"=".repeat(60)}`);
  console.log(`TOTAL: ${passed} passed, ${failed} failed`);
  console.log("=".repeat(60));
  if (failed > 0) throw new Error(`${failed} test(s) failed`);
}

try {
  main();
} catch (e) {
  console.error("UNCAUGHT ERROR:", e);
  throw e;
}
