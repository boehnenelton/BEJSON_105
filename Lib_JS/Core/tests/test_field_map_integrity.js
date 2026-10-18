/**
 * Library:         test_field_map_integrity.js
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
 * RELATIONAL_ID:   49f2e612-be5c-4c2e-b502-ff35c3917261
 */
'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const BEJSON = require(path.join(__dirname, '..', 'lib_bejson_Core_bejson_core.js'));

// The JS validator is a browser-style script with no exports; load it with an appended export.
const validateString = require(path.join(__dirname, '..', 'lib_bejson_Core_bejson_validator.js')).bejson_validator_validate_string;
const accepts = input => { try { return validateString(input) === true; } catch (_) { return false; } };
const mk104 = (ver, extra = {}) => Object.assign({ Format: 'BEJSON', Format_Version: ver, Format_Creator: 'Elton Boehnen',
    Records_Type: ['T'], Fields: [{ name: 'a', type: 'string' }, { name: 'b', type: 'string' }], Values: [['x', 'y']] }, extra);

const names = ['f0', 'f1', 'f2', 'f3', 'f4', 'f5'];
const makeDoc = (list = names, extra = {}) => Object.assign({
    Format_Version: '104a',
    Fields: list.map(n => ({ name: n, type: 'string' })),
    Values: [list.map(n => 'v_' + n)],
}, extra);
const valueFor = (doc, n) => doc.Values[0][BEJSON.bejson_core_get_field_index(doc, n)];

const tests = {
    forged_inner_swap_with_size_key() {
        const forged = {}; names.forEach((n, i) => { forged[n] = i; });
        forged.f1 = 2; forged.f2 = 1; forged.__bejson_field_count = 6;
        const doc = JSON.parse(JSON.stringify(makeDoc(names, { _bejson_field_map: forged })));
        assert.strictEqual(valueFor(doc, 'f1'), 'v_f1');
    },
    stale_after_push_and_shift() {
        const doc = makeDoc(['a', 'b', 'c']);
        BEJSON.bejson_core_get_field_map(doc);
        doc.Fields.push({ name: 'd' });
        assert.strictEqual(BEJSON.bejson_core_get_field_index(doc, 'd'), 3);
        doc.Fields.shift();
        assert.strictEqual(BEJSON.bejson_core_get_field_index(doc, 'a'), -1);
        assert.strictEqual(BEJSON.bejson_core_get_field_index(doc, 'b'), 0);
    },
    maps_not_shared_between_documents() {
        const a = makeDoc(), b = makeDoc();
        BEJSON.bejson_core_get_field_map(a).f0 = 99;
        assert.strictEqual(BEJSON.bejson_core_get_field_map(b).f0, 0);
    },
    comma_names_do_not_collide() {
        const one = makeDoc(['a,b', 'c']), two = makeDoc(['a', 'b,c']);
        BEJSON.bejson_core_get_field_map(one);
        assert.strictEqual(BEJSON.bejson_core_get_field_index(two, 'a'), 0);
        assert.strictEqual(BEJSON.bejson_core_get_field_index(two, 'b,c'), 1);
    },
    cached_map_serializes_clean() {
        assert.strictEqual(JSON.stringify(BEJSON.bejson_core_get_field_map(makeDoc(['x', 'y']))), '{"x":0,"y":1}');
    },
    validator_rejects_persisted_map_in_text() {
        for (const ver of ['104', '104a']) {
            assert.ok(accepts(JSON.stringify(mk104(ver))), ver + ' plain text should validate');
            assert.ok(!accepts(JSON.stringify(mk104(ver, { _bejson_field_map: { a: 0, b: 1 } }))), ver + ' persisted map must be rejected');
        }
    },
    validator_accepts_honest_and_rejects_forged_objects() {
        for (const ver of ['104', '104a']) {
            const honest = mk104(ver); BEJSON.bejson_core_get_field_map(honest);
            assert.ok(accepts(honest), ver + ' honest cached object must validate');
            assert.ok(!accepts(mk104(ver, { _bejson_field_map: { a: 1, b: 0 } })), ver + ' forged object must be rejected');
        }
    },
    lookup_cost_is_flat() {
        const cost = count => {
            const doc = makeDoc(Array.from({ length: count }, (_, i) => 'f' + i));
            BEJSON.bejson_core_get_field_map(doc);
            let best = Infinity;
            for (let r = 0; r < 5; r++) {
                const t = process.hrtime.bigint();
                for (let i = 0; i < 20000; i++) BEJSON.bejson_core_get_field_index(doc, 'f7');
                best = Math.min(best, Number(process.hrtime.bigint() - t));
            }
            return best;
        };
        cost(10); // warm-up
        assert.ok(cost(10000) / cost(10) < 6, 'lookup cost grew with field count');
    },
    reserved_underscore_keys() {
        // persisted (string) input: any '_' key is rejected, in every version
        for (const ver of ['104', '104a', '104db']) {
            assert.ok(!accepts(JSON.stringify(mk104(ver, { _anything: 1 }))), ver + ' persisted _anything');
        }
        assert.ok(!accepts(JSON.stringify(mk104('104a', { _nestingFieldMap: {} }))), 'persisted nesting map');
        // in-memory input: only the known caches
        assert.ok(!accepts(mk104('104a', { _anything: 1 })), 'in-memory unknown _ key');
        assert.ok(accepts(mk104('104a', { _nestingFieldMap: {} })), 'in-memory nesting map allowed');
        assert.ok(accepts(mk104('104a', { Custom_Header: 1 })), '104a custom header still fine');
    },
};

let failed = 0;
for (const [name, fn] of Object.entries(tests)) {
    try { fn(); console.log('PASS ' + name); }
    catch (e) { failed++; console.error('FAIL ' + name + ': ' + e.message); }
}
process.exit(failed ? 1 : 0);
