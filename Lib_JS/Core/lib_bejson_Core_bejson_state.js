/**
 * Library:         lib_bejson_Core_bejson_state.js
 * Family:          Core
 * Module Purpose:  Browser state manager with undo history kept in one BEJSON 104db document; blocks prototype-pollution keys.
 * Architecture:    BEJSON 104db: ONE file holding 2+ entity types, with a Record_Type_Parent discriminator in column 0, per-field Record_Type_Parent ownership, and null-padding for non-applicable fields. A single-file format; it is not MFDB.
 * Format_Scope:    104db only (single file; NOT MFDB)
 * Glossary:        BEJSON 104, 104a and 104db are the three file formats (Format_Version). 104db = ONE file holding 2+ entity types
 *                  (Record_Type_Parent discriminator, null-padding). MFDB is NOT a format and NOT 104db: it is a layer made of one 104a manifest
 *                  (104a.mfdb.bejson) plus dense 104 entity files linked by Parent_Hierarchy. MFDB-132 = an MFDB packed into one Chunked-104a document.
 * Version:         2.1.4
 * Release_Version: 300
 * Date:            2026-10-02
 * Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
 * Format_Creator:  Elton Boehnen
 * RELATIONAL_ID:   ca89e756-ed77-440b-83f9-5422ab22b231
 */

if (typeof window !== 'undefined') {
    window.BEJSON = window.BEJSON || {};
}

// Prototype-pollution guard: these names, if set on a plain object via Object.assign, can
// overwrite Object.prototype in older runtimes.
const _DANGEROUS_KEYS = new Set(["__proto__", "constructor", "prototype"]);

/**
 * Removes dangerous keys (__proto__, constructor, prototype) from a plain object before it is stored or restored.
 */
function _sanitizeObject(obj) {
    if (obj === null || typeof obj !== "object" || Array.isArray(obj)) return obj;
    const safe = Object.create(null);
    for (const [k, v] of Object.entries(obj)) {
        if (_DANGEROUS_KEYS.has(k)) continue;
        safe[k] = _sanitizeObject(v);
    }
    return safe;
}

class BEJSONState {
    /**
     * Creates the state manager: a reactive Proxy state object plus ONE BEJSON 104db document (StateNode + History records) that mirrors it. Options control history size.
     */
    constructor(initialState = {}, options = {}) {
        // Sanitize initial state before proxying
        initialState = _sanitizeObject(initialState) ?? {};
        this.schema_name = options.name || "BEJSONState";
        // Construct BEJSON 104db document directly (no namespace dependency)
        this.bejson = {
            Format: "BEJSON",
            Format_Version: "104db",
            Format_Creator: "Elton Boehnen",
            Records_Type: ["StateNode", "History"],
            Fields: [
            { name: "Record_Type_Parent", type: "string" },
            { name: "key", type: "string", Record_Type_Parent: "StateNode" },
            { name: "value", type: "string", Record_Type_Parent: "StateNode" },
            { name: "timestamp", type: "string", Record_Type_Parent: "History" },
            { name: "snapshot", type: "string", Record_Type_Parent: "History" }
        ],
            Values: []
        };

        this._listeners = new Map();
        this._historyIndex = -1;
        // FM3: Cache field indices at construction time — _syncToBEJSON is called on
        // every mutation; computing these via findIndex on every call is wasteful.
        this._fieldIdx = this._buildFieldIdx();
        this._activeEffect = null;
        this._dependencyGraph = new Map(); // path -> Set of effects
        this._effectDeps = new Map();      // effect -> Set of paths

        // Reactive Proxy
        this.state = this._createProxy(initialState, '');
        
        // Initialize BEJSON values from initial state
        this._syncToBEJSON();
        this._saveHistory();
    }

    /**
     * Wraps a state object in a Proxy that notifies listeners and re-syncs the 104db document when a value changes.
     */
    _createProxy(target, path) {
        const self = this;
        return new Proxy(target, {
            get(obj, prop) {
                const fullPath = path ? `${path}.${prop}` : prop;
                if (self._activeEffect) {
                    // Track dependency: path -> effect
                    if (!self._dependencyGraph.has(fullPath)) self._dependencyGraph.set(fullPath, new Set());
                    self._dependencyGraph.get(fullPath).add(self._activeEffect);
                    
                    // Track inverse dependency: effect -> path
                    if (!self._effectDeps.has(self._activeEffect)) self._effectDeps.set(self._activeEffect, new Set());
                    self._effectDeps.get(self._activeEffect).add(fullPath);
                }
                const value = obj[prop];
                if (value && typeof value === 'object') return self._createProxy(value, fullPath);
                return value;
            },
            set(obj, prop, value) {
                // block prototype pollution via proxy setter
                if (_DANGEROUS_KEYS.has(String(prop))) return true;
                const fullPath = path ? `${path}.${prop}` : prop;
                const oldValue = obj[prop];
                if (oldValue !== value) {
                    obj[prop] = value;
                    self._syncToBEJSON();
                    self._saveHistory();
                    self._notify(fullPath, value, oldValue);
                    self._triggerEffects(fullPath);
                }
                return true;
            }
        });
    }

    /**
     * Removes an effect's dependency registrations.
     */
    _cleanupEffect(effect) {
        const paths = this._effectDeps.get(effect);
        if (paths) {
            paths.forEach(path => {
                const effects = this._dependencyGraph.get(path);
                if (effects) {
                    effects.delete(effect);
                    if (effects.size === 0) this._dependencyGraph.delete(path);
                }
            });
            paths.clear();
        }
    }

    /**
     * Computes the field indices used by sync and history from the document's Fields (no fixed positions).
     */
    _buildFieldIdx() {
        // Pre-compute all field indices used by _syncToBEJSON and _saveHistory (FM3)
        const fields = this.bejson.Fields;
        return {
            rtp:      fields.findIndex(f => f.name === "Record_Type_Parent"),
            key:      fields.findIndex(f => f.name === "key"),
            value:    fields.findIndex(f => f.name === "value"),
            timestamp:fields.findIndex(f => f.name === "timestamp"),
            snapshot: fields.findIndex(f => f.name === "snapshot"),
        };
    }

    /**
     * Rebuilds the StateNode rows of the 104db document from the current state.
     */
    _syncToBEJSON() {
        const fields = this.bejson.Fields;
        const fieldCount = fields.length;
        // cached field indices
        const { rtp: rtpIdx, key: keyIdx, value: valIdx } = this._fieldIdx;

        // Clear StateNodes
        this.bejson.Values = this.bejson.Values.filter(r => r[0] !== "StateNode");
        
        // Flatten and add
        for (const [key, value] of Object.entries(this.state)) {
            const row = new Array(fieldCount).fill(null);
            if (rtpIdx !== -1) row[rtpIdx] = "StateNode";
            if (keyIdx !== -1) row[keyIdx] = key;
            if (valIdx !== -1) row[valIdx] = JSON.stringify(value);
            this.bejson.Values.push(row);
        }
    }

    /**
     * Appends a History row (JSON snapshot + timestamp).
     */
    _saveHistory() {
        const fields = this.bejson.Fields;
        const fieldCount = fields.length;
        // use cached indices
        const { rtp: rtpIdx, timestamp: tsIdx, snapshot: snIdx } = this._fieldIdx;

        const snapshot = JSON.stringify(this.state);
        const row = new Array(fieldCount).fill(null);
        if (rtpIdx !== -1) row[rtpIdx] = "History";
        if (tsIdx !== -1) row[tsIdx] = new Date().toISOString();
        if (snIdx !== -1) row[snIdx] = snapshot;
        
        this.bejson.Values.push(row);
        const historyRows = this.bejson.Values.filter(r => r[0] === "History");
        this._historyIndex = historyRows.length - 1;
    }

    /**
     * Calls the listeners subscribed to a path.
     */
    _notify(path, newValue, oldValue) {
        if (this._listeners.has(path)) this._listeners.get(path).forEach(cb => cb(newValue, oldValue, path));
        if (this._listeners.has('*')) this._listeners.get('*').forEach(cb => cb(newValue, oldValue, path));
    }

    /**
     * Re-runs the effects that depend on a changed path.
     */
    _triggerEffects(path) {
        const effectsToRun = new Set();
        if (this._dependencyGraph.has(path)) {
            this._dependencyGraph.get(path).forEach(e => effectsToRun.add(e));
        }
        
        // Handle nested paths (e.g., user.name triggers user)
        const parts = path.split('.');
        let currentPath = '';
        for (let i = 0; i < parts.length - 1; i++) {
            currentPath += (currentPath ? '.' : '') + parts[i];
            if (this._dependencyGraph.has(currentPath)) {
                this._dependencyGraph.get(currentPath).forEach(e => effectsToRun.add(e));
            }
        }
        
        effectsToRun.forEach(effect => effect());
    }

    /**
     * Registers a callback for changes at a state path; returns an unsubscribe function.
     */
    subscribe(path, callback) {
        if (!this._listeners.has(path)) this._listeners.set(path, new Set());
        this._listeners.get(path).add(callback);
        return () => this._listeners.get(path).delete(callback);
    }

    /**
     * Runs fn immediately and again whenever a state path it read changes.
     */
    effect(fn) {
        const runner = () => {
            this._cleanupEffect(runner);
            this._activeEffect = runner;
            try {
                fn(this.state);
            } finally {
                this._activeEffect = null;
            }
        };
        runner();
    }

    /**
     * Restores the previous History snapshot (sanitized); no-op at the oldest.
     */
    undo() {
        // snapshot column index is resolved through the field map (not a fixed position)
        const historyRows = this.bejson.Values.filter(r => r[0] === "History");
        if (this._historyIndex <= 0) return false;
        const snIdx = this.bejson.Fields.findIndex(f => f.name === "snapshot");
        if (snIdx === -1) return false;
        this._historyIndex--;
        this._restore(JSON.parse(historyRows[this._historyIndex][snIdx]));
        return true;
    }

    /**
     * Replaces the current state with a snapshot after sanitizing it.
     */
    _restore(snapshot) {
        // sanitize before restoring to prevent prototype pollution
        const safe = _sanitizeObject(snapshot) ?? {};
        Object.keys(this.state).forEach(k => delete this.state[k]);
        Object.assign(this.state, safe);
        this._notify('*', this.state, null);
    }
}

// --- Exports ---
const StateExports = {
    BEJSONState,
    State: BEJSONState
};

if (typeof module !== 'undefined' && module.exports) {
    module.exports = StateExports;
}
if (typeof window !== 'undefined') {
    window.BEJSON = window.BEJSON || {};
    Object.assign(window.BEJSON, StateExports);
}