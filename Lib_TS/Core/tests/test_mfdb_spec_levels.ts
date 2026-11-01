/**
 * Library:         test_mfdb_spec_levels.ts
 * Family:          Core
 * Module Purpose:  Pins the MFDB spec Level 1/2/3 rules for TS: entity Records_Type == manifest entity_name (34, case-sensitive), exactly one entry, bidirectional Parent_Hierarchy <-> manifest as a HARD error (38), missing Parent_Hierarchy (36), record_count drift = warning only, manifest dup/null/missing file errors.
 * Architecture:    Standalone script (pure in-memory validators); imports libraries relative to this file.
 * Format_Scope:    MFDB only (104a manifest + 104/105 entity files; NOT 104db)
 * Version:         1.0.0
 * Release_Version: 300
 * Date:            2026-10-28
 * Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
 * Format_Creator:  Elton Boehnen
 * RELATIONAL_ID:   7e809c11-a092-4d96-962d-e787a29640e3
 * Usage: tsc --target es2020 --module commonjs --skipLibCheck --outDir out *.ts tests/*.ts && node out/tests/test_mfdb_spec_levels.js
 */
import { createManifest, registerEntity } from "../lib_bejson_Core_mfdb_core";
import { validateDatabase, validateEntityFile } from "../lib_bejson_Core_mfdb_validators";
import { createEmpty104 } from "../lib_bejson_Core_bejson_core";

const FIELDS = [{ name: "id", type: "integer" as const }, { name: "name", type: "string" as const }];
function check(cond: boolean, msg: string): void { if (!cond) throw new Error(msg); }
const MANIFEST = "104a.mfdb.bejson";

function build(count = 1): { manifest: any; entities: Map<string, any> } {
  let manifest: any = createManifest({ db_name: "T" } as any);
  manifest = registerEntity(manifest, { entity_name: "Order", file_path: "data/order.bejson", record_count: count });
  const entity = createEmpty104("Order", FIELDS as any, [[1, "a"]], "../" + MANIFEST);
  return { manifest, entities: new Map<string, any>([["data/order.bejson", entity]]) };
}
const run = (m: any, e: Map<string, any>) => validateDatabase(m, e as any, { manifestRelativePath: MANIFEST });
const codes = (r: any): number[] => [...new Set<number>(r.errors.map((x: any) => x.code))].sort();

const tests: Record<string, () => void> = {
  clean_valid_no_warnings() { const b = build(); const r = run(b.manifest, b.entities); check(r.valid && r.warnings.length === 0, "clean DB: " + JSON.stringify(r.errors)); },
  records_type_wrong_is_34() { const b = build(); b.entities.get("data/order.bejson").Records_Type = ["WrongName"]; const r = run(b.manifest, b.entities); check(!r.valid && codes(r).includes(34), "34 expected, got " + codes(r)); },
  records_type_case_sensitive() { const b = build(); b.entities.get("data/order.bejson").Records_Type = ["order"]; const r = run(b.manifest, b.entities); check(!r.valid && codes(r).includes(34), "case must matter"); },
  records_type_two_entries_fails() { const b = build(); b.entities.get("data/order.bejson").Records_Type = ["Order", "X"]; check(!run(b.manifest, b.entities).valid, "two entries must fail"); },
  missing_parent_hierarchy_is_36() { const b = build(); delete b.entities.get("data/order.bejson").Parent_Hierarchy; const r = run(b.manifest, b.entities); check(!r.valid && codes(r).includes(36), "36 expected, got " + codes(r)); },
  bidirectional_other_manifest_is_38() { const b = build(); b.entities.get("data/order.bejson").Parent_Hierarchy = "../other/" + MANIFEST; const r = run(b.manifest, b.entities); check(!r.valid && codes(r).includes(38), "38 expected, got " + codes(r)); },
  bidirectional_wrong_name_is_38() { const b = build(); b.entities.get("data/order.bejson").Parent_Hierarchy = "../nope.mfdb.bejson"; const r = run(b.manifest, b.entities); check(!r.valid && codes(r).includes(38), "38 expected, got " + codes(r)); },
  bidirectional_without_explicit_manifest_requires_root_mfdb_file() {
    const b = build(); const e = b.entities.get("data/order.bejson"); e.Parent_Hierarchy = "../sub/x.mfdb.bejson";
    check(!validateDatabase(b.manifest, b.entities as any).valid, "non-root target must fail"); 
    e.Parent_Hierarchy = "../" + MANIFEST; check(validateDatabase(b.manifest, b.entities as any).valid, "root manifest ok");
  },
  entity_standalone_checks_name() { const b = build(); const r = validateEntityFile(b.entities.get("data/order.bejson"), { expectedEntityName: "Other" }); check(!r.valid && codes(r).includes(34), "standalone 34"); },
  record_count_drift_is_warning_only() { const b = build(99); const r = run(b.manifest, b.entities); check(r.valid && r.warnings.length > 0, "drift must warn, not fail"); },
  entity_105_is_accepted() {
    const b = build(); const e = b.entities.get("data/order.bejson");
    e.Format_Version = "105";
    e.Fields = [{ name: "id", type: "integer", field_uuid: "00000001-0000-4000-8000-000000000001" }, { name: "name", type: "string", field_uuid: "00000002-0000-4000-8000-000000000002" }];
    e.Values = [["00000003-0000-4000-8000-000000000003", 1, "a"]];
    const r = run(b.manifest, b.entities); check(r.valid, "105 entity must pass: " + JSON.stringify(r.errors));
  },
  entity_104db_rejected() { const b = build(); b.entities.get("data/order.bejson").Format_Version = "104db"; check(!run(b.manifest, b.entities).valid, "104db entity must fail"); },
  entity_must_be_104_or_105() { const b = build(); b.entities.get("data/order.bejson").Format_Version = "104a"; check(!run(b.manifest, b.entities).valid, "104a entity must fail"); },
  missing_entity_doc_fails() { const b = build(); check(!run(b.manifest, new Map()).valid, "missing entity must fail"); },
  network_role_valid_values() { for (const role of ["Master", "Slave", "Standalone"]) { const b = build(); b.manifest.Network_Role = role; const r = run(b.manifest, b.entities); check(r.valid, role + ": " + JSON.stringify(r.errors)); } },
  network_role_invalid_is_30() { const b = build(); b.manifest.Network_Role = "RogueNode"; const r = run(b.manifest, b.entities); check(!r.valid && codes(r).includes(30), "30 expected, got " + codes(r)); },
  absolute_file_path_rejected() { const b = build(); b.manifest.Values[0][b.manifest.Fields.findIndex((f: any) => f.name === "file_path")] = "/etc/outside.bejson"; check(!run(b.manifest, b.entities).valid, "absolute file_path must fail"); },
  absolute_parent_hierarchy_is_38() { const b = build(); b.entities.get("data/order.bejson").Parent_Hierarchy = "/tmp/" + MANIFEST; const r = run(b.manifest, b.entities); check(!r.valid && codes(r).includes(38), "38 expected, got " + codes(r)); },
  orphan_is_37_when_resolved_paths_given() {
    const b = build(); b.entities.get("data/order.bejson").Parent_Hierarchy = "../nope.mfdb.bejson";
    const r = validateDatabase(b.manifest, b.entities as any, { manifestRelativePath: MANIFEST, resolvedPaths: new Set(["data/order.bejson"]) });
    check(!r.valid && codes(r).includes(37) && !codes(r).includes(38), "37 expected, got " + codes(r));
  },
  parent_hierarchy_escaping_root_is_38_only() {
    const b = build(); b.entities.get("data/order.bejson").Parent_Hierarchy = "../../x/" + MANIFEST;
    const r = run(b.manifest, b.entities); check(!r.valid && codes(r).join() === "38", "only 38 expected, got " + codes(r));
  },
  fk_suffix_is_advisory_even_strict() {
    const b = build(); const e = b.entities.get("data/order.bejson");
    e.Fields.push({ name: "ghost_id_fk", type: "string" }); e.Values[0].push("nowhere");
    const r = validateDatabase(b.manifest, b.entities as any, { manifestRelativePath: MANIFEST, strict: true });
    check(r.valid && r.warnings.length > 0, "_fk naming must warn only: " + JSON.stringify(r.errors));
  },
};

let failed = 0;
for (const [name, fn] of Object.entries(tests)) {
  try { fn(); console.log("PASS " + name); } catch (e: any) { failed++; console.log("FAIL " + name + ": " + e.message); }
}
console.log(`${Object.keys(tests).length - failed} passed, ${failed} failed`);
if (failed) throw new Error("test failures");
