# Lib_JS/Canvas — Universal Canvas Foundation & Schema Family

**Family:** `Canvas` (`libraries_105`)  
**Format:** BEJSON 104a / 105a  
**Author:** Elton Boehnen · boehnenelton2024@gmail.com · [boehnenelton2024.pages.dev](https://boehnenelton2024.pages.dev) · [github.com/boehnenelton](https://github.com/boehnenelton)  
**License:** PolyForm Noncommercial License 1.0.0 (`PolyForm-Noncommercial-1.0.0`)

---

## 1. Architectural Mission

The `Lib_JS/Canvas` family establishes the **Universal Canvas Core Framework Baseline** for the BEJSON ecosystem. It provides a domain-agnostic spatial substrate designed to power:
- Freehand and vector drawing applications
- Architectural and technical diagramming suites
- Flowcharts and execution graph editors
- Graphical MFDB spatial database pipelines and visual query planes

Rather than embedding specialized tool assumptions (such as flowchart decision diamonds or freehand brush physics) directly into the core, `Lib_JS/Canvas` provides the universal spatial coordinate engine, reactive state store, collision geometry, and bidirectional BEJSON MFDB database persistence. Specialized domains are implemented as layered extension families (`Canvas_Drawing`, `Canvas_Diagram`, `Canvas_Flow`) that consume this foundation.

---

## 2. Core Modules

| Module | Purpose | Formats |
|---|---|---|
| `lib_bejson_canvas_core.js` | Universal domain-agnostic reactive canvas store, spatial math, MTV collision engine, and live MFDB-132 import/export engine. | BEJSON 104 / 104a (`MFDB-132`) |
| `lib_bejson_Canvas_canvas_schemas.js` | BEJSON 105a schema definitions and validation for SVG canvas templates, animation framerates, dimensions, device scales, and Playwright capture pipelines. | BEJSON 105a |
| `lib_bejson_Canvas_canvas_templates.js` | Fixed-size canvas presets (1:1 square, 2:1 banner, 16:9 widescreen, 9:16 portrait) and seamless texture tile template catalog. | BEJSON 105a |
| `index.js` | Consolidated entry point re-exporting core store, schemas, and template utilities. | CommonJS / Global |

---

## 3. Universal Canvas Core Invariants

Per `AGENTS.md`, all applications and extensions utilizing `lib_bejson_canvas_core.js` adhere to the following architectural laws:

1. **Domain-Agnostic Core:** `lib_bejson_canvas_core.js` contains zero domain-specific node types, connectors, brushes, or traversal heuristics.
2. **Object-to-MFDB Entity Mapping:** Every canvas object maps directly to its own dense BEJSON 104 MFDB entity (`obj_<type>_<id>.bejson`) linked inside a canonical `104a.mfdb.bejson` manifest.
3. **Single-File MFDB-132 Packaging:** Sessions export to and import from self-contained `.mfdb132.bejson` chunk packages verified against `MFDB_VALIDATOR` and `BEJSON_VALIDATOR`.
4. **Spatial Quantization:** Positions are quantized against the canonical 8-lane grid (`stageWidth / 8`) and Ry=32px vertical rhythm rows (`y / 32`), with sub-pixel bounding box tracking.
5. **Collision Awareness:** Placement and drag interactions enforce Minimum Translation Vector (MTV) collision resolution and stage boundary clamping to guarantee zero unresolvable overlapping.
6. **Reactive Store & History:** The canvas store exposes an observer notification interface with a 50-step linear undo/redo history stack.

---

## 4. Extension Architecture

Future specialized libraries build directly on top of `Lib_JS/Canvas`:

```
┌────────────────────────────────────────────────────────┐
│                   Domain Extensions                    │
├───────────────────┬───────────────────┬────────────────┤
│  Canvas_Drawing   │  Canvas_Diagram   │  Canvas_Flow   │
│  (Brushes/Strokes)│  (Nodes/Ports)    │  (Graph/Edges) │
└─────────┬─────────┴─────────┬─────────┴────────┬───────┘
          │                   │                  │
          └───────────────────┼──────────────────┘
                              ▼
        ┌───────────────────────────────────────────┐
        │      Lib_JS/Canvas (Universal Core)       │
        │  - Coordinates (cx, cy, x, y, size)       │
        │  - 8-Lane / Ry=32px Quantization          │
        │  - MTV Collision Resolution               │
        │  - Dense BEJSON 104 Entity Serialization  │
        │  - MFDB-132 Container Import / Export     │
        └───────────────────────────────────────────┘
```

---

## 5. Usage Example

```javascript
const { createCanvasStore, validateMfdb132 } = require('lib_bejson_canvas_core');

// 1. Initialize store
const store = createCanvasStore();
store.createNewFile('system_architecture', 1280, 720);

// 2. Add canvas objects (coordinates, size, stage boundary)
const node1 = store.addObject('node', 200, 150, 96, 1280, 720);
const node2 = store.addObject('node', 220, 150, 96, 1280, 720); // Automatically MTV-displaced

// 3. Export to single-file MFDB-132 container
const mfdbPackage = store.buildMfdb132Package();
const validation = store.validateMfdb132(mfdbPackage);
console.log('Valid MFDB-132:', validation.valid); // true

// 4. Round-trip restore in a fresh store
const restoredStore = createCanvasStore();
restoredStore.importMfdb132(mfdbPackage);
console.log('Restored objects:', restoredStore.state.shapes.length); // 2
```

---

## 6. Test Suite

Unit tests for `lib_bejson_canvas_core.js` are located in `tests/test_canvas_core.js` and executed via Node.js:

```bash
node Lib_JS/Canvas/tests/test_canvas_core.js
```
