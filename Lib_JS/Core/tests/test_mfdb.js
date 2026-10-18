/**
 * Library:         test_mfdb.js
 * Family:          Core
 * Module Purpose:  Tests for the MFDB core and validator: manifest + entity creation, count sync, validator catches broken databases, debug logging.
 * Architecture:    Standalone Node script (plain assert); resolves the library modules relative to this file; each test builds a database in a temp dir.
 * Format_Scope:    MFDB only (104a manifest + 104 entity files; NOT 104db)
 * Glossary:        BEJSON 104, 104a and 104db are the three file formats (Format_Version). 104db = ONE file holding 2+ entity types
 *                  (Record_Type_Parent discriminator, null-padding). MFDB is NOT a format and NOT 104db: it is a layer made of one 104a manifest
 *                  (104a.mfdb.bejson) plus dense 104 entity files linked by Parent_Hierarchy. MFDB-132 = an MFDB packed into one Chunked-104a document.
 * Version:         1.0.0
 * Release_Version: 300
 * Date:            2026-10-16
 * Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
 * Format_Creator:  Elton Boehnen
 * RELATIONAL_ID:   d5fe2d47-98fd-4ade-8ae0-99f4f42f28c3
 */
'use strict';
const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const core = require(path.join(__dirname, '..', 'lib_bejson_Core_mfdb_core.js'));
const val = require(path.join(__dirname, '..', 'lib_bejson_Core_mfdb_validator.js'));

const FIELDS = [{ name: 'id', type: 'integer' }, { name: 'name', type: 'string' }];
const readJson = p => JSON.parse(fs.readFileSync(p, 'utf8'));
const writeJson = (p, d) => fs.writeFileSync(p, JSON.stringify(d));
const isValid = m => { try { val.mfdb_validator_validate_database(m); return !val.mfdb_validator_has_errors(); } catch (_) { return false; } };

function fresh() {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'mfdb-js-'));
    const manifest = path.join(dir, '104a.mfdb.bejson');
    writeJson(manifest, core.mfdb_core_create_manifest('T'));
    core.mfdb_core_init_entity_file(manifest, 'User', FIELDS, 'data/user.bejson');
    return { dir, manifest, entity: path.join(dir, 'data', 'user.bejson') };
}

const tests = {
    fresh_database_is_valid() { assert.ok(isValid(fresh().manifest)); },
    missing_entity_file_is_caught() {
        const t = fresh(); fs.unlinkSync(t.entity);
        assert.ok(!isValid(t.manifest));
    },
    wrong_parent_hierarchy_is_caught() {
        const t = fresh(); const d = readJson(t.entity); d.Parent_Hierarchy = '../nope.bejson'; writeJson(t.entity, d);
        assert.ok(!isValid(t.manifest));
    },
    missing_parent_hierarchy_is_caught() {
        const t = fresh(); const d = readJson(t.entity); delete d.Parent_Hierarchy; writeJson(t.entity, d);
        assert.ok(!isValid(t.manifest));
    },
    entity_row_length_mismatch_is_caught() {
        const t = fresh(); const d = readJson(t.entity); d.Values.push([1]); writeJson(t.entity, d);
        assert.ok(!isValid(t.manifest));
    },
    persisted_field_map_in_entity_is_caught() {
        const t = fresh(); const d = readJson(t.entity); d._bejson_field_map = { id: 0, name: 1 }; writeJson(t.entity, d);
        assert.ok(!isValid(t.manifest));
    },
    sync_repairs_stale_count() {
        const t = fresh(); const d = readJson(t.entity); d.Values.push([1, 'a'], [2, 'b']); writeJson(t.entity, d);
        core.mfdb_core_sync_all_counts(t.manifest);
        assert.strictEqual(readJson(t.manifest).Values[0][3], 2);
    },
    debug_logging_round_trip() {
        const t = fresh();
        core.mfdb_core_enable_debug(t.manifest);
        assert.strictEqual(String(readJson(t.manifest).Debug_Mode).toLowerCase(), 'true');
        assert.ok(core.mfdb_core_get_debug_log(t.manifest).length > 0, 'enable_debug logs an initial row');
        core.mfdb_core_disable_debug(t.manifest);
        assert.strictEqual(String(readJson(t.manifest).Debug_Mode).toLowerCase(), 'false');
    },
    slave_entity_only_on_master() {
        const t = fresh();
        assert.throws(() => core.mfdb_core_create_connected_slave_entity(t.manifest));
        const m = readJson(t.manifest); m.Network_Role = 'Master'; writeJson(t.manifest, m);
        core.mfdb_core_create_connected_slave_entity(t.manifest);
        assert.ok(fs.existsSync(path.join(t.dir, 'data', 'connectedslave.bejson')));
        assert.ok(isValid(t.manifest));
    },
    federation_push_config_writes_atomically() {
        const t = fresh(); const dest = path.join(t.dir, 'drop', 'cfg.bejson');
        assert.strictEqual(core.mfdb_federation_push_config(readJson(t.manifest), dest), true);
        assert.strictEqual(readJson(dest).DB_Name, 'T');
        assert.deepStrictEqual(fs.readdirSync(path.dirname(dest)), ['cfg.bejson']);
    },
};

let failed = 0;
for (const [name, fn] of Object.entries(tests)) {
    try { fn(); console.log('PASS ' + name); }
    catch (e) { failed++; console.error('FAIL ' + name + ': ' + e.message); }
}
process.exit(failed ? 1 : 0);
