/**
 * Library:         test_mfdb.ts
 * Family:          Core
 * Module Purpose:  Tests for the MFDB core and validators: manifest/entity creation, validator catches broken databases, debug logging on disk (regression for the missing fs/path imports).
 * Architecture:    Standalone script; imports the libraries relative to this file; needs @types/node to compile; temp dir per debug test.
 * Format_Scope:    MFDB only (104a manifest + 104 entity files; NOT 104db)
 * Glossary:        BEJSON 104, 104a and 104db are the three file formats (Format_Version). 104db = ONE file holding 2+ entity types
 *                  (Record_Type_Parent discriminator, null-padding). MFDB is NOT a format and NOT 104db: it is a layer made of one 104a manifest
 *                  (104a.mfdb.bejson) plus dense 104 entity files linked by Parent_Hierarchy. MFDB-132 = an MFDB packed into one Chunked-104a document.
 * Version:         1.0.0
 * Release_Version: 300
 * Date:            2026-10-16
 * Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
 * Format_Creator:  Elton Boehnen
 * RELATIONAL_ID:   61f3a344-bab5-4840-a085-6b3c72ffd29c
 * Usage: tsc --target es2020 --module commonjs --moduleResolution node10 --skipLibCheck --types node --outDir out test_mfdb.ts && node out/tests/test_mfdb.js  (run from Lib_TS/Core/tests; needs @types/node)
 */
import * as fs from "fs";
import * as os from "os";
import * as path from "path";
import { createManifest, registerEntity, enableDebug, disableDebug, getDebugLog } from "../lib_bejson_Core_mfdb_core";
import { validateDatabase } from "../lib_bejson_Core_mfdb_validators";
import { createEmpty104 } from "../lib_bejson_Core_bejson_core";

const FIELDS = [{ name: "id", type: "integer" as const }, { name: "name", type: "string" as const }];
function check(cond: boolean, msg: string): void { if (!cond) throw new Error(msg); }

function build(): { manifest: any; entities: Map<string, unknown> } {
  let manifest: any = createManifest({ db_name: "T" } as any);
  manifest = registerEntity(manifest, { entity_name: "User", file_path: "data/user.bejson", record_count: 1 });
  const entity = createEmpty104("User", FIELDS as any, [[1, "a"]], "../104a.mfdb.bejson");
  return { manifest, entities: new Map<string, unknown>([["data/user.bejson", entity]]) };
}
const valid = (m: any, e: Map<string, unknown>): boolean => validateDatabase(m, e).valid;

const tests: Record<string, () => void> = {
  fresh_database_is_valid() { const b = build(); check(valid(b.manifest, b.entities), "fresh DB should validate"); },
  missing_entity_doc_is_caught() { const b = build(); check(!valid(b.manifest, new Map()), "missing entity must fail"); },
  missing_parent_hierarchy_is_caught() {
    const b = build(); const e: any = b.entities.get("data/user.bejson"); delete e.Parent_Hierarchy;
    check(!valid(b.manifest, b.entities), "entity without Parent_Hierarchy must fail");
  },
  row_length_mismatch_is_caught() {
    const b = build(); const e: any = b.entities.get("data/user.bejson"); e.Values.push([1]);
    check(!valid(b.manifest, b.entities), "short row must fail");
  },
  parent_hierarchy_escaping_root_is_caught() {
    const b = build(); const e: any = b.entities.get("data/user.bejson"); e.Parent_Hierarchy = "../../outside.bejson";
    check(!valid(b.manifest, b.entities), "Parent_Hierarchy above the DB root must fail");
  },
  duplicate_entity_registration_is_rejected() {
    const b = build(); let threw = false;
    try { registerEntity(b.manifest, { entity_name: "User", file_path: "data/user2.bejson" }); } catch { threw = true; }
    check(threw, "duplicate entity name must throw");
  },
  forged_field_map_in_entity_is_caught() {
    const b = build(); const e: any = b.entities.get("data/user.bejson"); e._bejson_field_map = { id: 1, name: 0 };
    check(!valid(b.manifest, b.entities), "forged map in entity must fail");
  },
  debug_logging_round_trip() {
    // Regression: fs/path were never imported at module scope, so every debug helper threw and the catch hid it.
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), "mfdb-ts-"));
    try {
      const b = build();
      const manifestPath = path.join(dir, "104a.mfdb.bejson");
      fs.writeFileSync(manifestPath, JSON.stringify(b.manifest));
      fs.mkdirSync(path.join(dir, "data"));
      fs.writeFileSync(path.join(dir, "data", "user.bejson"), JSON.stringify(b.entities.get("data/user.bejson")));
      const meta = enableDebug(manifestPath);
      check(typeof meta === "string" && meta.length > 0, "enableDebug returns the meta entity name");
      check(fs.existsSync(path.join(dir, "data", meta + ".bejson")), "meta entity file created");
      check(getDebugLog(manifestPath).length > 0, "debug log has the schema-snapshot row for the registered entity");
      disableDebug(manifestPath);
      check(String(JSON.parse(fs.readFileSync(manifestPath, "utf8")).Debug_Mode) === "false", "Debug_Mode off");
    } finally { fs.rmSync(dir, { recursive: true, force: true }); }
  },
};

let failed = 0;
for (const name of Object.keys(tests)) {
  try { tests[name](); process.stdout.write("PASS " + name + "\n"); }
  catch (e) { failed++; process.stderr.write("FAIL " + name + ": " + (e as Error).message + "\n"); }
}
process.exit(failed ? 1 : 0);
