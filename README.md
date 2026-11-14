# BEJSON 105 Core & Integrity Era Library Ecosystem (`libraries_105`)

![BEJSON 105 Ecosystem Banner](images/banners/banner_420.png)
*_Figure 1: BEJSON 105 Integrity Era Architecture & Multi-Language Core_*

> **The Official Reference Implementation for BEJSON Integrity Era Formats (`105`, `105a`, `105db`), 104 Baseline Parity, Atomic Migration Tooling, and MFDB v1.40 Multi-File Database Referential Integrity across Python, JavaScript, TypeScript, and Bash.**

---

## Table of Contents
- [Prerequisites & Environment Setup](#prerequisites--environment-setup)
- [Installation & Quick Start](#installation--quick-start)
- [Core Features & Integrity Era Innovations](#core-features--integrity-era-innovations)
- [Multi-Language Quickstart Examples](#multi-language-quickstart-examples)
- [Multi-AI Provider Gateway (`Lib_PY/AI` v1.5.0)](#multi-ai-provider-gateway-lib_pyai-v150)
- [Visual Interface & Architecture Tour](#visual-interface--architecture-tour)
- [System Architecture & Repository Topology](#system-architecture--repository-topology)
- [BEJSON 105 Format Specifications & UUID Fingerprinting](#bejson-105-format-specifications--uuid-fingerprinting)
- [MFDB v1.40 Referential Integrity Engine](#mfdb-v140-referential-integrity-engine)
- [Atomic Format 104-to-105 Migration Pipeline](#atomic-format-104-to-105-migration-pipeline)
- [O(1) Field-Map Cache & Sanitization Mechanics](#o1-field-map-cache--sanitization-mechanics)
- [CLI Reference & Utilities Matrix](#cli-reference--utilities-matrix)
- [Testing & Quality Verification](#testing--quality-verification)
- [Frequently Asked Questions & Troubleshooting](#frequently-asked-questions--troubleshooting)

---

## Prerequisites & Environment Setup

`libraries_105` is engineered as a lightweight, zero-dependency multi-language runtime core compatible with modern Linux distributions, macOS, and Termux environments.

### System Requirements
- **Python**: Version 3.10 or higher (`json`, `pathlib`, `uuid`, `typing`, `hashlib`, `os`, `sys`).
- **Node.js**: Version 18.0.0 or higher with full ES2022 module and CommonJS support.
- **TypeScript**: Version 5.0 or higher for type-checked codebases.
- **Bash**: Version 4.4 or 5.x with standard core utilities (`jq`, `grep`, `sed`).

### Environment Variables Setup
To consume `libraries_105` without hardcoded filesystem paths in application logic, set the following environment variables in your active shell or configuration manager:

```bash
# Path to your local libraries_105 root checkout (the only variable the examples below need)
export ADMIN_LIBRARIES_105="/path/to/your/libraries_105"
```

Python modules are flat files inside family folders, so add each family folder you use to `sys.path` (`PYTHONPATH=Lib_PY` alone is **not** enough); JavaScript uses `require(`${ADMIN_LIBRARIES_105}/Lib_JS/Core/...`)`; Bash uses `source "$ADMIN_LIBRARIES_105/Lib_SH/Core/...sh"` and needs `jq`. See the runnable examples below.

---

## Installation & Quick Start

Clone or extract the repository directly into your workspace:

```bash
git clone https://github.com/boehnenelton/BEJSON_105.git libraries_105
cd libraries_105
```

Execute the test suites to verify four-language engine readiness:

```bash
# Verify Python Core & MFDB v1.40
python3 Lib_PY/Core/tests/test_mfdb_spec_levels_suite.py

# Verify Python Multi-AI Gateway (v1.5.0) & Canvas Suites
python3 -m unittest discover -s Lib_PY/AI/tests -v
python3 -m unittest discover -s Lib_PY/Canvas/tests -v

# Verify JavaScript Core & Referential Integrity
node Lib_JS/Core/tests/test_mfdb_spec_levels_suite.js
node Lib_JS/Core/tests/test_phase6_ref_integrity.js

# Verify TypeScript Core (needs `npm i -D typescript @types/node`; the tests live in Lib_TS/Core/tests/ and are compiled, not just type-checked)
npx tsc -p Lib_TS/tsconfig.json --noEmit

# Verify Bash Core (needs jq)
bash Lib_SH/Core/tests/test_mfdb_spec_levels.sh
```

---

## Core Features & Integrity Era Innovations

The 105 specification advances tabular data architectures by introducing deterministic UUID fingerprinting and active referential integrity enforcement.

1. **Deterministic UUID Fingerprinting**: Every schema field (`field_uuid`) and data row (`record_uuid`) is assigned an immutable UUIDv4, enabling collision-free distributed syncing.
2. **MFDB v1.40 Referential Integrity**: Real-time foreign key (`_fk`) validation with configurable `on_delete` policies (`restrict`, `cascade`, `null`) preventing orphaned records.
3. **Foundational Era Parity**: Full backward compatibility with 104, 104a, 104db, and Nested 104 documents inside the 105 engine.
4. **Atomic In-Place Upgrades**: Upgrade 104 documents to 105 with an automated pre-upgrade backup, atomic file replacement, and post-upgrade verification. The upgrade tool exists in **Python only** (`bejson_core_upgrade_to_105`, `Lib_PY/Core/cli/bejson_upgrade_cli.py`); TypeScript has an in-memory `upgradeTo105`.
5. **Four-Language Core**: Python is the reference implementation. JavaScript, TypeScript and Bash cover the validators, field map and most MFDB operations, with documented gaps: JS/TS have no PID file lock, JS lacks `define_field`, TS has no MFDB entity-record CRUD, and the 104→105 upgrade tool is Python-only. See `Libraries_105_Agent_Directive-V10100-PKG100.md` §3 for the capability matrix.
6. **Hardened Multi-AI Provider Gateway (`Lib_PY/AI` v1.5.0)**: Zero-SDK 3-tier AI gateway supporting Gemini REST (`geminirest`) and Gemini Interactions (`geminiinteractions`), `Name_Case` model constants (`Gemini_3_1_Flash_Lite`, `Gemini_3_5_Flash_Lite`, `Gemini_3_8_Flash`, `Gemini_4_Argon`, `Gemini_4_Hydrogen`), persistent Format 105a configuration (`ai_global_config.105a.bejson`), config-gated `Tooling_Registry`, `Parser_Registry`, `Extension_Parser_Registry`, and silent `x-goog-api-key` rotation with 429 cooldown and 401 quarantine.

---

## Multi-Language Quickstart Examples

Each example below was executed against this tree. It builds a two-entity MFDB (`Customer` ← `Order` with a cascading foreign key) and audits it.

### 1. Python (`Lib_PY/Core`)
```python
import os, sys
from pathlib import Path

LIBRARIES_105_ROOT = Path(os.environ["ADMIN_LIBRARIES_105"])
sys.path.insert(0, str(LIBRARIES_105_ROOT / "Lib_PY" / "Core"))

from lib_bejson_Core_mfdb_core import (
    mfdb_core_create_database, mfdb_core_add_entity_record_105,
    mfdb_core_enable_ref_integrity, mfdb_core_load_entity,
)
from lib_bejson_Core_mfdb_validator import mfdb_validator_check_referential_integrity

manifest_path = mfdb_core_create_database(
    "db", "OrdersDB",
    [{"name": "Customer", "file_path": "data/customer.bejson", "primary_key": "record_uuid",
      "format_version": "105", "fields": [{"name": "cust_name", "type": "string"}]},
     {"name": "Order", "file_path": "data/order.bejson", "primary_key": "record_uuid",
      "format_version": "105",
      "fields": [{"name": "order_customer_fk", "type": "string",
                  "fk_target_entity": "Customer", "fk_on_delete": "cascade"},
                 {"name": "order_total", "type": "integer"}]}],
    mfdb_version="1.40")                                   # writes db/104a.mfdb.bejson

customer_doc = mfdb_core_add_entity_record_105(manifest_path, "Customer", ["Ann"])
customer_uuid = customer_doc["Values"][-1][0]              # returns the ENTITY DOC; the new uuid is the last row's cell 0
mfdb_core_enable_ref_integrity(manifest_path)
mfdb_core_add_entity_record_105(manifest_path, "Order", [customer_uuid, 5])

for order in mfdb_core_load_entity(manifest_path, "Order"):   # list of dicts, includes "record_uuid"
    print(order["record_uuid"], order["order_customer_fk"], order["order_total"])

findings = mfdb_validator_check_referential_integrity(manifest_path)   # a LIST; [] means clean
assert findings == [], findings
```

### 2. JavaScript (`Lib_JS/Core`)
```javascript
"use strict";
const root = process.env.ADMIN_LIBRARIES_105;
const mfdb = require(`${root}/Lib_JS/Core/lib_bejson_Core_mfdb_core.js`);
const validator = require(`${root}/Lib_JS/Core/lib_bejson_Core_mfdb_validator.js`);

const manifestPath = mfdb.mfdb_core_create_database("jsdb", "OrdersDB", [
  { name: "Customer", file_path: "data/customer.bejson", primary_key: "record_uuid", format_version: "105",
    fields: [{ name: "cust_name", type: "string" }] },
  { name: "Order", file_path: "data/order.bejson", primary_key: "record_uuid", format_version: "105",
    fields: [{ name: "order_customer_fk", type: "string", fk_target_entity: "Customer", fk_on_delete: "cascade" },
             { name: "order_total", type: "integer" }] },
], { mfdb_version: "1.40" });                               // writes jsdb/104a.mfdb.bejson

const { record_uuid: customerUuid } = mfdb.mfdb_core_add_entity_record_105(manifestPath, "Customer", ["Ann"]);   // JS returns { record_uuid, doc } (Python returns the doc)
mfdb.mfdb_core_enable_ref_integrity(manifestPath);
mfdb.mfdb_core_add_entity_record_105(manifestPath, "Order", [customerUuid, 5]);

for (const order of mfdb.mfdb_core_load_entity(manifestPath, "Order")) {
  console.log(order.record_uuid, order.order_customer_fk, order.order_total);
}
const findings = validator.mfdb_validator_check_referential_integrity(manifestPath);   // an array; [] means clean
if (findings.length) { console.error(findings); process.exit(1); }
```

### 3. TypeScript (`Lib_TS/Core`)
Run from `Lib_TS/Core`, pointing at a database directory such as the one the Python example creates. Compile with `tsc --target es2020 --module commonjs --moduleResolution node10 --strict --types node`.
```typescript
import * as fs from "fs";
import * as path from "path";
import { parse, bejson_core_get_field_map, verify105Integrity } from "./index";

const manifestDir = process.argv[2];                       // e.g. a database created by the Python example
const orderDoc = parse(fs.readFileSync(path.join(manifestDir, "data", "order.bejson"), "utf8"));
const fieldMap = bejson_core_get_field_map(orderDoc);      // record_uuid is implicit: row[0]; declared fields are offset by one

for (const row of orderDoc.Values) {
  console.log(`Order ${String(row[0])} -> customer ${String(row[fieldMap["order_customer_fk"]])}`);
}
const report = verify105Integrity(orderDoc);
console.log(report.ok ? "105 integrity: ok" : `105 integrity: ${report.errors.join("; ")}`);
```

### 4. Bash (`Lib_SH/Core`)
```bash
source "$ADMIN_LIBRARIES_105/Lib_SH/Core/lib_bejson_Core_bejson_core.sh"
source "$ADMIN_LIBRARIES_105/Lib_SH/Core/lib_bejson_Core_mfdb_validator.sh"

# Levels 1-3 MFDB audit; exit status 0 means valid
if mfdb_validator_validate_database "db/104a.mfdb.bejson"; then
  echo "MFDB database is valid."
fi
```

---

## Multi-AI Provider Gateway (`Lib_PY/AI` v1.5.0)

`Lib_PY/AI` provides a hardened 3-tier AI gateway with zero external SDK dependencies, supporting both **Gemini REST (`generateContent`)** and **Gemini Interactions (`v1beta/interactions`)** with stateful `previous_interaction_id` chaining, `Name_Case` class/method exports, and persistent Format 105a configuration (`Lib_PY/AI/config/ai_global_config.105a.bejson`).

![BEJSON 105 AI Gateway — Part 1: Abstraction, Tooling & Parser Layers (Tiers 1 & 2)](images/ai_gateway/ai_gateway_part1_tiers_1_2.jpg)
*_Figure 2: BEJSON 105 AI Gateway — Part 1: Abstraction, Tooling & Parser Layers (Tiers 1 & 2)_*

![BEJSON 105 AI Gateway — Part 2: Service Callers, Vault & Key Rotation (Tier 3)](images/ai_gateway/ai_gateway_part2_tier_3.jpg)
*_Figure 3: BEJSON 105 AI Gateway — Part 2: Service Callers, Vault & Key Rotation (Tier 3)_*

### Python AI Gateway Quickstart (`Lib_PY/AI`)
```python
import os, sys
from pathlib import Path

LIBRARIES_105_ROOT = Path(os.environ["ADMIN_LIBRARIES_105"])
sys.path.insert(0, str(LIBRARIES_105_ROOT / "Lib_PY" / "AI"))

from lib_bejson_ai_dispatcher import (
    AI_Dispatcher, AI_Dispatch, AI_Dispatch_Async,
    Get_Response_Text, Get_Interaction_ID, Get_Turn_Continuation_Command,
)
from lib_bejson_ai_models import Gemini_3_1_Flash_Lite, Resolve_Model_Identifier
from lib_bejson_ai_tooling_registry import Tooling_Registry
from lib_bejson_ai_parser_registry import Parser_Registry
from lib_bejson_ai_extension_parser import Extension_Parser_Registry

# Resolve active modern model identifier
resolved_model_id = Resolve_Model_Identifier(Gemini_3_1_Flash_Lite)

# Configure persistent 105a gates (tooling, modular pre/post parsers, Python module extensions)
tooling_registry = Tooling_Registry()
parser_registry = Parser_Registry(config_manager=tooling_registry.config_manager)
extension_registry = Extension_Parser_Registry(config_manager=tooling_registry.config_manager)

dispatcher = AI_Dispatcher(
    tooling_registry=tooling_registry,
    parser_registry=parser_registry,
    extension_parser_registry=extension_registry,
)
```

---

## Visual Interface & Architecture Tour

`libraries_105` acts as the authoritative multi-entity relational backbone:

```
[MFDB v1.40 Database Manifest: 104a.mfdb.bejson]
  ├── Network_Role: "Master"
  ├── Ref_Integrity: true
  ├── Entities:
  │     ├── Authors (data/authors.105.bejson) ── [PK: author_uuid]
  │     └── Books (data/books.105.bejson) ────── [FK: author_fk -> Authors.author_uuid]
  │                                               [on_delete: "cascade" | "restrict" | "null"]
  └── Subordinate Slaves:
        └── Worker Node (node_worker/104a.mfdb.bejson)
```

The core libraries interface seamlessly with the 3-tier AI Gateway (`Lib_PY/AI`), canvas rendering modules (`Lib_PY/Canvas`, `Lib_JS/Canvas`), and graphics subsystems (`Lib_PY/Graphics`, `Lib_JS/Graphics`).

---

## System Architecture & Repository Topology

The `libraries_105` repository isolates the core runtime engines and taxonomy definitions:

```
libraries_105/
├── Lib_PY/                    # Python 3.10+ Implementation
│   ├── Core/                  # 105/105a/105db core engine, validators, and upgrade tooling
│   ├── AI/                    # 3-Tier Multi-AI Gateway (Gemini REST/Interactions, Tooling/Parser/Extension Registries, Vault/JIT Key Rotator)
│   ├── CMS/                   # MTV scaffolding engine + Flask admin server (loopback by default)
│   ├── Canvas/                # SVG canvas generators, stage templates, and visual renderers
│   ├── Graphics/              # Geometric layouts, branding slides, and video compilation pipelines
│   ├── Standards/             # Structured logging sink (BEJSONLogHandler), export, archiving
│   ├── Taxonomies/            # "lattice" taxonomy and field-set registry
│   └── Tax_Scaffolds/         # Scaffold/graft field sets onto entities
├── Lib_JS/                    # JavaScript CommonJS / ES2022 Implementation
│   ├── Core/                  # 105 engine, validators, and referential integrity suite
│   ├── Canvas/                # Dynamic in-browser canvas renderer and test suite
│   ├── Graphics/              # Vector calculation, schema validation, and styling engine
│   └── External/              # External format bridges and test suite
├── Lib_TS/                    # TypeScript 5.x Typed Implementation
│   └── Core/                  # Strongly typed 105 engine, MFDB validators, and schemas
├── Lib_SH/                    # Bash 5.x POSIX Implementation
│   └── Core/                  # jq-backed 105 core engine and MFDB validator
└── images/                    # Project banners and architecture diagrams
    ├── banners/               # Ecosystem release banners
    └── ai_gateway/            # Tier 1, 2 & 3 AI Gateway architecture diagrams
```

---

## BEJSON 105 Format Specifications & UUID Fingerprinting

Format 105 enforces structural identity across schemas and row vectors:

### Mandatory Top-Level Keys
1. `"Format"`: Must be `"BEJSON"`.
2. `"Format_Version"`: `"105"` (Table), `"105a"` (Metadata/Config), or `"105db"` (Multi-Table Store).
3. `"Format_Creator"`: Maintainer signature (`"Elton Boehnen"`).
4. `"Records_Type"`: Non-empty array of record names.
5. `"Fields"`: Array of schema objects including `"name"`, `"type"`, and `"field_uuid"`. `record_uuid` is **implicit** and must not be declared here.
6. `"Values"`: Two-dimensional array of row vectors where index 0 is the implicit `record_uuid`.

### Example: Format 105 Document
```json
{
  "Format": "BEJSON",
  "Format_Version": "105",
  "Format_Creator": "Elton Boehnen",
  "Records_Type": ["Author"],
  "Fields": [
    {"name": "author_id", "type": "string", "field_uuid": "e3b0c442-98fc-1c14-9afb-4c72e04f0001"},
    {"name": "author_name", "type": "string", "field_uuid": "e3b0c442-98fc-1c14-9afb-4c72e04f0002"}
  ],
  "Values": [
    ["6f1d2c4a-3b5e-4f70-9a81-2c3d4e5f6071", "auth_01", "Ada Lovelace"]
  ]
}
```

---

## MFDB v1.40 Referential Integrity Engine

MFDB v1.40 introduces true relational constraint handling:

1. **Foreign Key Mapping (`fk_target_entity`)**: Columns ending in `_fk` map directly to target entities registered in the manifest.
2. **Deletion Behaviors (`fk_on_delete`)**:
   - `"restrict"`: Halts deletion if foreign child rows reference the targeted primary key.
   - `"cascade"`: Recursively deletes referencing rows across linked entity tables.
   - `"null"`: Sets referencing foreign key values to `null`.
3. **Cycle Prevention**: Cascade execution detects circular relationship loops and halts cleanly with error code `[44]`.
4. **Standalone Audit (`mfdb_validator_check_referential_integrity`)**: Audits the entire multi-file database without mutating files on disk.

---

## Atomic Format 104-to-105 Migration Pipeline

Existing Foundational Era 104 files can be upgraded seamlessly:

```bash
# Preview (writes nothing), then upgrade a single 104-series file to 105-series
python3 Lib_PY/Core/cli/bejson_upgrade_cli.py --dry-run data/legacy.bejson
python3 Lib_PY/Core/cli/bejson_upgrade_cli.py data/legacy.bejson
```

Whole-database upgrades are done per entity with the same tool (there is no `upgrade_mfdb_to_105.py` in this repository).

- **Verbatim Backup**: Copies the original file to `Backups/<filename>.104.bak` prior to modification.
- **UUID Generation**: Generates deterministic UUIDv4 identifiers for all fields and records.
- **Atomic Swap**: Writes to a temporary staging file before performing an atomic POSIX replace.

---

## O(1) Field-Map Cache & Sanitization Mechanics

### Field-Map Cache Lookup
Positional hardcoding is strictly avoided. Column positions resolve through the constant-time Field-Map Cache:

```python
from lib_bejson_Core_bejson_core import bejson_core_get_field_map

field_map = bejson_core_get_field_map(doc)     # 105 maps already include the record_uuid offset
author_id = row[field_map["author_id"]]
```

### Boundary-Layer Sanitization
Input dictionaries and raw rows undergo sanitization at serialization boundaries:
- Leading and trailing whitespace is stripped from keys and cell values.
- Unknown types are rejected against the closed type taxonomy (`string`, `integer`, `float`, `boolean`, `null`, `any`).
- Format 105 UUIDs are validated against RFC 4122 v4 regex specifications.

---

## CLI Reference & Utilities Matrix

| Language | Script / Tool | Primary Capabilities |
| :--- | :--- | :--- |
| **Python** | `Lib_PY/Core/cli/bejson_upgrade_cli.py` | 104→105 file upgrade with `--dry-run`, backup and atomic swap |
| **Python** | `Lib_PY/Core/cli/bejson_server.py` | Local BEJSON data server |
| **Python** | `Lib_PY/CMS/web/Scaffold_Admin_Entry.py` | MTV scaffold admin server (binds 127.0.0.1; set `MTV_SCAFFOLD_OUTPUT_ROOT`) |
| **Python** | `Lib_PY/Core/lib_bejson_Core_mfdb_validator.py` | `validate_mfdb_database`, `mfdb_validator_check_referential_integrity` |
| **Bash** | `Lib_SH/Core/lib_bejson_Core_mfdb_validator.sh` | Shell-based automated Level 1, 2, and 3 MFDB integrity checks |

---

## Testing & Quality Verification

Run the comprehensive test suites across runtimes:

```bash
# Python Core & MFDB v1.40 Suite
python3 Lib_PY/Core/tests/test_format105_suite.py
python3 Lib_PY/Core/tests/test_mfdb_spec_levels_suite.py

# Python AI Gateway (v1.5.0) & Canvas Suites
python3 -m unittest discover -s Lib_PY/AI/tests -v
python3 -m unittest discover -s Lib_PY/Canvas/tests -v

# JavaScript Core, Referential Integrity, Canvas, Graphics & External Suites
node Lib_JS/Core/tests/test_mfdb_spec_levels_suite.js
node Lib_JS/Core/tests/test_phase6_ref_integrity.js
node Lib_JS/Canvas/tests/test_canvas_schemas.js
node Lib_JS/Graphics/tests/test_graphics_validator.js
node Lib_JS/External/tests/test_external_core.js

# TypeScript Core & Referential Integrity Suite
npx tsc -p Lib_TS/tsconfig.json --noEmit

# Bash Core Suite
bash Lib_SH/Core/tests/test_mfdb_spec_levels.sh
```

### Error Code Summary
- `[30]`: Invalid Network Role string.
- `[34]`: Malformed manifest `Records_Type`.
- `[36]`: Missing or unresolvable `Parent_Hierarchy`.
- `[38]`: Broken bidirectional parent-manifest linkage.
- `[39]`: Unresolved foreign key reference.
- `[43-47]`: Referential integrity constraint violations.
- `[90-95]`: Format 105 migration and UUID integrity errors.
- `[200-235]`: Multi-AI Provider Gateway (`Lib_PY/AI`) transport, key rotation, quarantine, and translation errors.

---

## Frequently Asked Questions & Troubleshooting

**Q: Does `libraries_105` replace `libraries_104`?**  
A: No. `libraries_105` is the Integrity Era engine for UUID-tracked schemas and relational constraints. `libraries_104` remains the stable repository for mature vertical domains (CMS, Gaming, Diagrams).

**Q: Can a 105 MFDB database contain 104 entity tables?**  
A: Yes. An MFDB v1.40 database manifest can register both 104 and 105 entity tables. However, active referential integrity enforcement only audits Format 105 entities declaring primary and foreign keys.

**Q: How does `restrict` handle deletes?**  
A: If any referencing child entity holds a foreign key pointing to the target record, the operation raises error code `[43]` without modifying either table.
