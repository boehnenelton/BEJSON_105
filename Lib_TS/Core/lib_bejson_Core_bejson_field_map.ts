/**
 * Library:        lib_bejson_Core_bejson_field_map.ts
 * Family:         Core
 * Description:    TypeScript implementation of the Field Map Cache.
 * Version:        2.4.0
 * Date:           2026-10-03
 * Author:         Elton Boehnen
 * Contact:        eltonboehnen@gmail.com | boehnenelton2024.pages.dev | github.com/boehnenelton
 * Format_Creator: Elton Boehnen
 * RELATIONAL_ID:  09778540-7d4b-448b-9412-fa8988dca743
 * Release_Version: 300
 *
 * Changelog:
 *   2.4.0 - ONE self-maintaining cache for every lookup (mirrors Python core
 *           3.4.0/3.5.0 + JS core 2.1.0). get_field_map / get_field_index /
 *           get_field_map_105 / the new get_field_cache all share a per-document
 *           WeakMap entry validated against the live field layout on every
 *           read -- callers never build or refresh anything. FieldMap105 gains
 *           byNameRow (name -> ROW position, record_uuid/discriminator offset
 *           applied). New bejson_core_warm() is called by parse() so 105-series
 *           docs are born warm. Replaced the string-keyed global map (O(fields)
 *           key build per call, never evicted) for the 104 path too.
 *   2.3.0 - bejson_core_get_field_map_105() is now self-maintaining: every call
 *           validates the doc's live field layout and rebuilds if stale, cached
 *           per document in a WeakMap (was a global string-keyed Map that
 *           never evicted).
 *   2.2.0 - Added bejson_core_get_field_map_105(): UUID-aware Field Map
 *           (byName + byUuid) for 105-series docs, mirroring Python's
 *           by_name/by_uuid cache. bejson_core_clear_field_map_cache() now
 *           clears both caches. Existing name-only API unchanged.
 */

import { BEJSONDocument } from './lib_bejson_Core_bejson_types';

/**
 * Field Map type: mapping of field name to its positional index.
 */
export type FieldMap = { [key: string]: number };

/**
 * UUID-aware Field Map (105-series). byName / byUuid -> index into Fields;
 * byNameRow -> index into a ROW (adds the reserved leading columns: 0 for
 * 104-series, 1 for 105/105a record_uuid, 2 for 105db discriminator+uuid),
 * so row[byNameRow.get(name)] is right on every Format_Version.
 */
export type FieldMap105 = {
    byName: Map<string, number>;
    byUuid: Map<string, number>;
    byNameRow: Map<string, number>;
};

const _105_SERIES = ['105', '105a', '105db'];

type _Entry = { fp: string; map: FieldMap105; plain: FieldMap };

// Per-document cache. WeakMap: freed with the document, never leaks, and
// never needs to be cleared for correctness (every read self-validates).
let _CACHE: WeakMap<object, _Entry> = new WeakMap();

function _rowOffset(doc: BEJSONDocument): number {
    const v = doc.Format_Version;
    return v === '105db' ? 2 : (_105_SERIES.indexOf(v as string) !== -1 ? 1 : 0);
}

function _fingerprint(doc: BEJSONDocument): string {
    let fp = String((doc && doc.Format_Version) || '') + '\u0001';
    const fields = (doc && doc.Fields) || [];
    for (let i = 0; i < fields.length; i++) {
        const u = (fields[i] as any).field_uuid;
        fp += fields[i].name + '\u0000' + (u === undefined ? '' : u) + '\u0001';
    }
    return fp;
}

function _entry(doc: BEJSONDocument): _Entry {
    const fp = _fingerprint(doc);
    const hit = _CACHE.get(doc);
    if (hit && hit.fp === fp) return hit;

    const map: FieldMap105 = { byName: new Map(), byUuid: new Map(), byNameRow: new Map() };
    const plain: FieldMap = Object.create(null);
    const offset = _rowOffset(doc);
    ((doc && doc.Fields) || []).forEach((f, i) => {
        map.byName.set(f.name, i);
        map.byNameRow.set(f.name, i + offset);
        plain[f.name] = i;
        const u = (f as any).field_uuid;
        if (u !== undefined) map.byUuid.set(u, i);
    });
    const built = { fp, map, plain };
    _CACHE.set(doc, built);
    return built;
}

/**
 * Field name -> Fields index for a BEJSON document. Self-maintaining: built
 * on first touch, rebuilt automatically whenever the field layout changes.
 */
export function bejson_core_get_field_map(doc: BEJSONDocument): FieldMap {
    if (!doc || !doc.Fields) return {};
    return _entry(doc).plain;
}

/**
 * Returns the index of a specific field by name, using the cache. -1 on miss.
 */
export function bejson_core_get_field_index(doc: BEJSONDocument, fieldName: string): number {
    if (!doc || !doc.Fields) return -1;
    const idx = _entry(doc).map.byName.get(fieldName);
    return (idx !== undefined) ? idx : -1;
}

/**
 * UUID-aware field map, SELF-MAINTAINING. Every call checks the document's
 * current field layout against the cached one and (re)builds if it is
 * missing or out of date -- callers never build or refresh it.
 * Mirrors Python's _bejson_get_field_map_cache.
 */
export function bejson_core_get_field_map_105(doc: BEJSONDocument): FieldMap105 {
    return _entry(doc).map;
}

/** Alias of get_field_map_105 under the cross-language name (JS/PY: get_field_cache). */
export const bejson_core_get_field_cache = bejson_core_get_field_map_105;

/**
 * Warms a freshly parsed/loaded document so the first lookup is already a
 * hit. 105-series only; 104-series stay lazy (standing contract). Returns the
 * same doc so it chains: bejson_core_warm(JSON.parse(text)).
 */
export function bejson_core_warm<T extends BEJSONDocument>(doc: T): T {
    if (doc && Array.isArray(doc.Fields) && _105_SERIES.indexOf(doc.Format_Version as string) !== -1) {
        _entry(doc);
    }
    return doc;
}

/**
 * Drops every cached map. NOT needed for correctness any more (reads
 * self-validate); kept for API parity and memory control.
 */
export function bejson_core_clear_field_map_cache(): void {
    _CACHE = new WeakMap();
}
