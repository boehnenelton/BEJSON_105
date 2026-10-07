#Tags #BEJSON105 #Libraries #DataIntegrity #MFDB

## Title: BEJSON 105 Core Libraries & Specification Ecosystem

> The official multi-language reference implementation, structural schema validators, runtime libraries, and database tools for Elton Boehnen's BEJSON (104/104a/104db/105/105a/105db) format specifications and MFDB (v1.31/1.39/1.40) federated architectures.

[![Build Status](https://img.shields.io/badge/Build-Passing-brightgreen.svg)]()
[![Specification](https://img.shields.io/badge/BEJSON-v105a%20Integrity%20Era-blue.svg)]()
[![MFDB Spec](https://img.shields.io/badge/MFDB-v1.40%20%2F%20Chunk%201.32-orange.svg)]()
[![Runtimes](https://img.shields.io/badge/Runtimes-Python%20%7C%20JavaScript%20%7C%20TypeScript%20%7C%20Bash-informational.svg)]()
[![License](https://img.shields.io/badge/License-Polyglot%20%28MIT%2FApache%2FCC--BY%2FCC0%29-red.svg)]()

---

## Credits

**Author & Format Creator:** Elton Boehnen  
**Email:** [boehnenelton2024@gmail.com](mailto:boehnenelton2024@gmail.com)  
**Website:** [boehnenelton2024.pages.dev](https://boehnenelton2024.pages.dev)  
**GitHub:** [github.com/boehnenelton](https://github.com/boehnenelton)  
**Format Creator & Core Architect:** Elton Boehnen  
**Document Fingerprint / Relational ID:** `59e2a871-c014-4e2b-98f3-8b7c2a104921`  
**Ecosystem Release Version:** Release 300 / BEJSON 105 Integrity Era  

---

## Table of Contents

- [Introduction](#introduction)
- [Breakdown](#breakdown)
  - [Essence & Purpose](#essence--purpose)
  - [Primary & General Use Cases](#primary--general-use-cases)
  - [Advanced & Enterprise Use Cases](#advanced--enterprise-use-cases)
- [Feature List](#feature-list)
- [Usage Guide](#usage-guide)
  - [Python Runtime Usage (`Lib_PY`)](#python-runtime-usage-lib_py)
  - [JavaScript Runtime Usage (`Lib_JS`)](#javascript-runtime-usage-lib_js)
  - [TypeScript Runtime Usage (`Lib_TS`)](#typescript-runtime-usage-lib_ts)
  - [Bash & Shell Runtime Usage (`Lib_SH`)](#bash--shell-runtime-usage-lib_sh)
- [System Architecture & Topology](#system-architecture--topology)
- [BEJSON Format & Integrity Specifications](#bejson-format--integrity-specifications)
  - [BEJSON 104 – Single Entity Standard](#bejson-104--single-entity-standard)
  - [BEJSON 104a – Primitive Metadata Standard](#bejson-104a--primitive-metadata-standard)
  - [BEJSON 104db – Multi-Entity Database Standard](#bejson-104db--multi-entity-database-standard)
  - [BEJSON 105 & 105a – Integrity Era Standards](#bejson-105--105a--integrity-era-standards)
  - [BEJSON 105db – Multi-Entity Integrity Standard](#bejson-105db--multi-entity-integrity-standard)
  - [Nested 104 – Deep Hierarchical Cells](#nested-104--deep-hierarchical-cells)
- [MFDB Specification & Master-Slave Federation](#mfdb-specification--master-slave-federation)
  - [Manifest Architecture (`104a.mfdb.bejson`)](#manifest-architecture-104amfdbbejson)
  - [Entity File Architecture](#entity-file-architecture)
  - [Master-Slave Topological Federation](#master-slave-topological-federation)
  - [MFDB-132 Session Mounting & Chunking](#mfdb-132-session-mounting--chunking)
- [Comprehensive API Reference Matrix](#comprehensive-api-reference-matrix)
  - [Python Module API (`Lib_PY`)](#python-module-api-lib_py)
  - [JavaScript Module API (`Lib_JS`)](#javascript-module-api-lib_js)
  - [TypeScript Module API (`Lib_TS`)](#typescript-module-api-lib_ts)
  - [Bash Module API (`Lib_SH`)](#bash-module-api-lib_sh)
- [Configuration & Environment Reference](#configuration--environment-reference)
- [Performance, Field Map Cache & Benchmarks](#performance-field-map-cache--benchmarks)
- [Exhaustive Error Registry & Diagnostic Code Reference](#exhaustive-error-registry--diagnostic-code-reference)
- [Security Policy & Cryptographic Integrity](#security-policy--cryptographic-integrity)
- [Troubleshooting & FAQ](#troubleshooting--faq)
- [Development & Contribution Guidelines](#development--contribution-guidelines)
- [Closing Summary](#closing-summary)
- [Polyglot License](#polyglot-license)

---

## Introduction

The **BEJSON 105 Core Libraries & Specification Ecosystem** is a multi-language software suite designed for local-first, high-throughput, and structurally verifiable data persistence. BEJSON (Binary-Efficient JSON / Boehnen-Elton JSON) is a strict tabular data serialization format that enforces **positional integrity**—aligning value arrays directly to field definition indices—to eliminate key redundancy, minimize payload byte overhead, enable $O(1)$ field map lookups, and guarantee zero-drift schema enforcement without requiring external database daemons.

This repository hosts the canonical reference implementation across four major programming environments:
1. **Python (`Lib_PY`):** Python 3.10+ native implementation with static type hints, dataclass validation results, and CLI tools.
2. **JavaScript (`Lib_JS`):** Vanilla JS (ES2022 / UMD) library compatible with modern browsers, Node.js, and Web Crypto APIs.
3. **TypeScript (`Lib_TS`):** Strictly typed TypeScript implementation with generic schema definitions and interface parity.
4. **Bash (`Lib_SH`):** Portable POSIX/Bash shell functions backed by `jq` and `onig5` primitives for server administration and Termux tools.

Together with the Multi-File Database (MFDB v1.31/1.39/1.40) specification, this suite enables modular, file-system-native database architectures that scale from standalone configuration files up to complex multi-entity federated nodes.

---

## Breakdown

### Essence & Purpose

The core essence of BEJSON is **positional integrity**. Traditional JSON objects repeat key strings for every single record in an array (e.g., `[{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]`), causing massive payload bloat, high parsing overhead, and unpredictable key order desynchronization.

BEJSON resolves this by decoupling the schema array (`Fields`) from the data matrix (`Values`):

```json
{
  "Format": "BEJSON",
  "Format_Version": "104",
  "Format_Creator": "Elton Boehnen",
  "Records_Type": ["User"],
  "Fields": [
    {"name": "id", "type": "integer"},
    {"name": "name", "type": "string"}
  ],
  "Values": [
    [1, "A"],
    [2, "B"]
  ]
}
```

The position of `"name"` in `Fields` (index 1) strictly guarantees that index 1 in every row within `Values` contains the name string. Index lookups replace dictionary hashing, achieving $O(1)$ property access while preserving human readability and raw text editor editability.

### Primary & General Use Cases

#### 1. High-Throughput Application State & Configuration
- **Application Configuration (`104a`):** Managing system settings, environment flags, and user preferences with strict type validation and custom PascalCase headers.
- **Log Aggregation & Metrics (`104`):** Recording high-density audit logs, telemetry, and system events with zero key overhead and rapid line-by-line streaming.

#### 2. Local-First Multi-Entity Relational Stores (`104db` & `MFDB`)
- **Single-File Relational Data (`104db`):** Storing multiple entity types within a single JSON document using discriminator columns (`Record_Type_Parent`) for small-to-medium embedded datasets.
- **Modular Multi-File Databases (`MFDB`):** Organizing large domain models into discrete entity files registered under a central manifest (`104a.mfdb.bejson`).

### Advanced & Enterprise Use Cases

#### 1. AI Context Window Preservation & "Structural Blindness"
In modern LLM agentic workflows, loading massive database schemas or redundant keys rapidly consumes context windows. BEJSON compresses payload tokens by 30%–60%. Furthermore, MFDB's **Master-Slave Federation** paradigm allows operational slave nodes to remain "structurally blind" to administrative parent schemas, preserving prompt context for core tasks.

#### 2. Cryptographic Session Mounting (MFDB-132)
Single-file container packaging collapses an entire multi-file database into a single `Chunked-104a` document (`.mfdb132.bejson`). Sessions mount instantly via lock-file verification (`.mfdb132_lock`) with cryptographic SHA-256 integrity checks, providing hardware-safe atomic updates.

---

## Feature List

- ⚡ **Positional Integrity Engine:** Guarantees exact 1-to-1 index matching between field definitions and row values.
- 🚀 **O(1) Field Map Caching:** Instant positional index resolution, bypassing dictionary hashing and key lookup overhead.
- 🛡️ **Boundary Data Sanitization:** Automatically strips leading/trailing whitespace from dictionary keys and string values prior to record processing.
- 📐 **Format 105 Strict Integrity:** Integrated `field_uuid` and `record_uuid` UUIDv4 fingerprinting for strict record tracking and release boundaries.
- 🔍 **Multi-Level Validation Gate:** 3-tier validation hierarchy (Manifest, Entity, and Database levels) surfacing error codes 1–159.
- 🌐 **4-Language Parity:** Identical structural logic and error codes across Python, JavaScript, TypeScript, and Bash.
- 🔒 **Web Crypto AES-GCM Integration:** Native 256-bit cell/row encryption with PBKDF2 key derivation and `ENC:AES-GCM` format tags.
- 🗂️ **MFDB Master-Slave Federation:** Decoupled node roles (`Network_Role`) with inverse dropzone polling and atomic file swapping (`rename`).
- 📦 **MFDB-132 Chunk Packaging:** Single-file container packing, sticky mounting, and pre-write validation gates.
- 🛠️ **CLI Utilities & Server Daemons:** Built-in interactive CLI tools, log managers, upgrade utilities, and lightweight HTTP server daemons.

---

## Usage Guide

### Python Runtime Usage (`Lib_PY`)

The Python library (`lib_bejson_Core_bejson_core.py`) targets Python 3.10+ and provides dataclass-backed validation results.

```python
from pathlib import Path
from Lib_PY.Core.lib_bejson_Core_bejson_core import BEJSONCore
from Lib_PY.Core.lib_bejson_Core_bejson_validator import validate_bejson
from Lib_PY.Core.lib_bejson_Core_bejson_parse import BEJSONParser

# 1. Create a fresh BEJSON 104 document
doc = BEJSONCore.create_document(
    records_type=["SensorData"],
    fields=[
        {"name": "sensor_id", "type": "string"},
        {"name": "timestamp", "type": "string"},
        {"name": "value", "type": "number"}
    ]
)

# 2. Append records with positional integrity
BEJSONCore.add_record(doc, ["SENS-01", "2026-10-07T23:00:00Z", 42.8])
BEJSONCore.add_record(doc, ["SENS-02", "2026-10-07T23:01:00Z", 19.4])

# 3. Access records via Field Map Cache (O(1) Property Access)
parser = BEJSONParser(doc)
for row_dict in parser.iter_records():
    print(f"Sensor {row_dict['sensor_id']} -> Value: {row_dict['value']}")

# 4. Validate document integrity
result = validate_bejson(doc)
if result.valid:
    print(f"✓ Valid BEJSON {doc['Format_Version']} with {len(doc['Values'])} records.")
else:
    print(f"⚠ Validation errors: {result.errors}")

# 5. Atomic File Persistence
BEJSONCore.save_atomic(Path("data/sensor_readings.bejson"), doc)
```

### JavaScript Runtime Usage (`Lib_JS`)

The JavaScript library operates seamlessly in modern browser environments (ES2022+) and Node.js.

```javascript
import { BEJSONCore, validateBEJSON } from './Lib_JS/Core/lib_bejson_Core_bejson_core.js';
import { BEJSONParser } from './Lib_JS/Core/lib_bejson_Core_bejson_parse.js';

// Construct 104a Configuration Document
const configDoc = {
  Format: "BEJSON",
  Format_Version: "104a",
  Format_Creator: "Elton Boehnen",
  Server_ID: "PROD-NODE-01",
  Records_Type: ["ConfigSetting"],
  Fields: [
    { name: "setting_key", type: "string" },
    { name: "setting_value", type: "string" },
    { name: "is_active", type: "boolean" }
  ],
  Values: [
    ["max_connections", "100", true],
    ["debug_mode", "false", false]
  ]
};

// Validate
const valResult = validateBEJSON(configDoc);
if (valResult.valid) {
  console.log("Configuration valid!");
  const parser = new BEJSONParser(configDoc);
  const rows = parser.toObjectArray();
  console.log("Parsed Configuration Rows:", rows);
} else {
  console.error("Validation failed:", valResult.errors);
}
```

### TypeScript Runtime Usage (`Lib_TS`)

The TypeScript library exposes strictly typed interfaces for field definitions, documents, and validation options.

```typescript
import { BEJSONDocument104, BEJSONField, ValidationResult } from './Lib_TS/Core/lib_bejson_Core_bejson_types';
import { validateBEJSON } from './Lib_TS/Core/lib_bejson_Core_bejson_validators';

const document: BEJSONDocument104 = {
  Format: 'BEJSON',
  Format_Version: '104',
  Format_Creator: 'Elton Boehnen',
  Records_Type: ['UserAccount'],
  Fields: [
    { name: 'user_uuid', type: 'string' },
    { name: 'login_count', type: 'integer' }
  ],
  Values: [
    ['usr_9981', 14]
  ]
};

const report: ValidationResult = validateBEJSON(document);
console.log(`Valid: ${report.valid}`);
```

### Bash & Shell Runtime Usage (`Lib_SH`)

The Shell library uses POSIX-compliant functions backed by `jq` for terminal administration.

```bash
#!/usr/bin/env bash
source ./Lib_SH/Core/lib_bejson_Core_be_core.sh
source ./Lib_SH/Core/lib_bejson_Core_bejson_validator.sh

# Read record count from a BEJSON document
doc_path="data/sensor_readings.bejson"
record_count=$(be_core_get_record_count "$doc_path")
echo "Total records in $doc_path: $record_count"

# Extract field names array
fields=$(be_core_get_fields "$doc_path")
echo "Fields: $fields"

# Validate document syntax and positional integrity
if be_validator_check_document "$doc_path"; then
    echo "✓ Document passed shell validation."
else
    echo "❌ Validation failed."
fi
```

---

## System Architecture & Topology

```mermaid
flowchart TD
    subgraph Client Layer
        CLI["CLI Tools & Terminal Daemons"]
        WebUI["Browser Editor / Web App"]
        NodeApp["Backend Services & Microservices"]
    end

    subgraph Runtime Core (Python / JS / TS / Bash)
        Sanitizer["Boundary Data Sanitizer"]
        FieldCache["Field Map Cache (O(1) Lookups)"]
        Validator["Structural & Type Validator (Errors 1-159)"]
        NestEngine["Core Nesting Engine (Depth <= 16)"]
        CryptoEngine["Web Crypto AES-GCM Engine"]
    end

    subgraph Persistence & Federation Layer
        BEJSON104[("BEJSON 104 / 104a Files")]
        BEJSON104db[("BEJSON 104db Multi-Entity File")]
        MFDBManifest[("104a.mfdb.bejson (Manifest)")]
        MFDBEntities[("data/*.bejson (Entities)")]
        ChunkedContainer[("MFDB-132 (.mfdb132.bejson)")]
    end

    CLI --> Sanitizer
    WebUI --> Sanitizer
    NodeApp --> Sanitizer

    Sanitizer --> FieldCache
    FieldCache --> Validator
    Validator --> NestEngine
    Validator --> CryptoEngine

    Validator --> BEJSON104
    Validator --> BEJSON104db
    Validator --> MFDBManifest
    MFDBManifest --> MFDBEntities
    Validator --> ChunkedContainer
```

---

## BEJSON Format & Integrity Specifications

The BEJSON ecosystem specifies six distinct format variants, divided into the **Foundational Era (104-series)** and the **Integrity Era (105-series)**.

### Mandatory Top-Level Keys
Every valid BEJSON document MUST contain these six core keys:

```json
{
  "Format": "BEJSON",
  "Format_Version": "104",
  "Format_Creator": "Elton Boehnen",
  "Records_Type": [ ... ],
  "Fields": [ ... ],
  "Values": [ ... ]
}
```

---

### BEJSON 104 – Single Entity Standard

- **Records_Type:** Array containing exactly ONE entity string (e.g., `["SensorReading"]`).
- **Custom Top-Level Keys:** Strictly forbidden (except the built-in `Parent_Hierarchy` key).
- **Supported Data Types:** `string`, `integer`, `number`, `boolean`, `array`, `object`.
- **Primary Use:** Homogeneous, high-throughput data streams, metrics, and MFDB entity files.

```json
{
  "Format": "BEJSON",
  "Format_Version": "104",
  "Format_Creator": "Elton Boehnen",
  "Records_Type": ["SensorReading"],
  "Fields": [
    {"name": "sensor_id", "type": "string"},
    {"name": "timestamp", "type": "string"},
    {"name": "temperature", "type": "number"},
    {"name": "tags", "type": "array"}
  ],
  "Values": [
    ["S001", "2026-10-07T12:00:00Z", 23.5, ["indoor", "ground"]],
    ["S002", "2026-10-07T12:00:00Z", 19.8, null]
  ]
}
```

---

### BEJSON 104a – Primitive Metadata Standard

- **Records_Type:** Array containing exactly ONE string.
- **Custom Top-Level Keys:** Permitted for file-level metadata (must be PascalCase, e.g., `Server_ID`, `Retention_Days`).
- **Supported Data Types:** Primitives only (`string`, `integer`, `number`, `boolean`). Complex arrays and objects are forbidden.
- **Primary Use:** System configuration, health parameters, and MFDB manifests (`104a.mfdb.bejson`).

```json
{
  "Format": "BEJSON",
  "Format_Version": "104a",
  "Format_Creator": "Elton Boehnen",
  "Server_ID": "WEB-PROD-01",
  "Environment": "Production",
  "Retention_Days": 90,
  "Records_Type": ["ConfigParam"],
  "Fields": [
    {"name": "key", "type": "string"},
    {"name": "value", "type": "string"},
    {"name": "sensitive", "type": "boolean"}
  ],
  "Values": [
    ["db_host", "prod-db-01.internal", true],
    ["max_threads", "32", false]
  ]
}
```

---

### BEJSON 104db – Multi-Entity Database Standard

- **Records_Type:** Array containing TWO OR MORE entity strings (e.g., `["User", "Item"]`).
- **Discriminator Column:** The first field in `Fields` MUST be `{"name": "Record_Type_Parent", "type": "string"}`.
- **Field Ownership:** Every subsequent field MUST specify a `"Record_Type_Parent"` property matching one entity name.
- **Null-Padding:** Records set non-applicable entity fields to `null`.
- **Primary Use:** Portable, single-file relational databases readable directly by humans and AI.

```json
{
  "Format": "BEJSON",
  "Format_Version": "104db",
  "Format_Creator": "Elton Boehnen",
  "Records_Type": ["User", "Item"],
  "Fields": [
    {"name": "Record_Type_Parent", "type": "string"},
    {"name": "created", "type": "string", "Record_Type_Parent": "User"},
    {"name": "user_id", "type": "string", "Record_Type_Parent": "User"},
    {"name": "username", "type": "string", "Record_Type_Parent": "User"},
    {"name": "created_at", "type": "string", "Record_Type_Parent": "Item"},
    {"name": "item_id", "type": "string", "Record_Type_Parent": "Item"},
    {"name": "name", "type": "string", "Record_Type_Parent": "Item"},
    {"name": "owner_user_id_fk", "type": "string", "Record_Type_Parent": "Item"}
  ],
  "Values": [
    ["User", "2026-01-01", "U01", "alice", null, null, null, null],
    ["User", "2026-01-02", "U02", "bob", null, null, null, null],
    ["Item", null, null, null, "2026-01-10", "I01", "Report A", "U01"],
    ["Item", null, null, null, "2026-01-10", "I02", "Report B", "U02"]
  ]
}
```

---

### BEJSON 105 & 105a – Integrity Era Standards

Format 105 introduces explicit UUID tracking columns and strict schema validation constraints without breaking core positional mechanics.

#### Key 105 Specifications:
1. **`field_uuid` Fingerprinting:** Every entry in `Fields` includes a unique `field_uuid` (UUIDv4) to prevent column ambiguity during schema migrations.
2. **`record_uuid` Reserved Column:** Values rows contain a reserved `record_uuid` at position 0 (or position 1 for `105db`), providing immutable row tracking.
3. **Fail-on-Switch Guard (`E95`):** Re-headering a 104 document to 105 without compiling required UUID columns causes an immediate hard validation failure.

```json
{
  "Format": "BEJSON",
  "Format_Version": "105",
  "Format_Creator": "Elton Boehnen",
  "Records_Type": ["VerifiedUser"],
  "Fields": [
    {"name": "user_id", "type": "string", "field_uuid": "f1a2b3c4-0001-4000-8000-000000000001"},
    {"name": "email", "type": "string", "field_uuid": "f1a2b3c4-0002-4000-8000-000000000002"}
  ],
  "Values": [
    ["r9a8b7c6-0001-4000-8000-000000000001", "U1001", "user1@example.com"],
    ["r9a8b7c6-0002-4000-8000-000000000002", "U1002", "user2@example.com"]
  ]
}
```

---

### BEJSON 105db – Multi-Entity Integrity Standard

Combines 104db discriminator architecture with Format 105 UUID fingerprinting:
- **Discriminator Column:** Position 0 contains `Record_Type_Parent`.
- **Reserved Record UUID:** Position 1 contains `record_uuid`.
- **Field Fingerprints:** Every field object declares `field_uuid` and `Record_Type_Parent`.

---

### Nested 104 – Deep Hierarchical Cells

BEJSON 104 permits embedding full BEJSON 104 documents directly inside individual table cells.

- **Implicit Foreign Keys:** The physical cell coordinate `NestAddress(parent_path, row, col, depth)` serves as an implicit foreign key, eliminating key redundant join columns.
- **Column-Schema Uniformity:** All nested documents within the same parent column MUST share identical field names, types, and sequence order.
- **Depth Ceiling:** Supports recursive nesting up to a hard safety ceiling of 16 (`NESTING_MAX_DEPTH`).

```json
{
  "Format": "BEJSON",
  "Format_Version": "104",
  "Format_Creator": "Elton Boehnen",
  "Records_Type": ["GameCharacter"],
  "Fields": [
    {"name": "character_id", "type": "string"},
    {"name": "inventory", "type": "object"}
  ],
  "Values": [
    [
      "CHAR-01",
      {
        "Format": "BEJSON",
        "Format_Version": "104",
        "Format_Creator": "Elton Boehnen",
        "Records_Type": ["Item"],
        "Fields": [
          {"name": "item_id", "type": "string"},
          {"name": "quantity", "type": "integer"}
        ],
        "Values": [
          ["ITEM-SWORD-01", 1],
          ["ITEM-POTION-05", 10]
        ]
      }
    ]
  ]
}
```

---

## MFDB Specification & Master-Slave Federation

Multi-File Database (MFDB v1.31/1.39/1.40) orchestrates separate BEJSON files into a unified disk database architecture.

```
mydb/
├── 104a.mfdb.bejson        ← Master Manifest (BEJSON 104a)
└── data/
    ├── user.bejson         ← Entity File (BEJSON 104)
    ├── order.bejson        ← Entity File (BEJSON 104)
    └── product.bejson      ← Entity File (BEJSON 104)
```

---

### Manifest Architecture (`104a.mfdb.bejson`)

The manifest is a BEJSON 104a document acting as the database registry:

```json
{
  "Format": "BEJSON",
  "Format_Version": "104a",
  "Format_Creator": "Elton Boehnen",
  "MFDB_Version": "1.39",
  "DB_Name": "ECommerceStore",
  "Network_Role": "Master",
  "Records_Type": ["mfdb"],
  "Fields": [
    {"name": "entity_name", "type": "string"},
    {"name": "file_path", "type": "string"},
    {"name": "description", "type": "string"},
    {"name": "record_count", "type": "integer"},
    {"name": "schema_version", "type": "string"},
    {"name": "primary_key", "type": "string"}
  ],
  "Values": [
    ["User", "data/user.bejson", "User accounts", 150, "1.0.0", "user_id"],
    ["Order", "data/order.bejson", "Customer orders", 420, "1.0.0", "order_id"]
  ]
}
```

---

### Entity File Architecture

Entity files are BEJSON 104 documents containing a mandatory `Parent_Hierarchy` header pointing relatively back to the manifest:

```json
{
  "Format": "BEJSON",
  "Format_Version": "104",
  "Format_Creator": "Elton Boehnen",
  "Parent_Hierarchy": "../104a.mfdb.bejson",
  "Records_Type": ["Order"],
  "Fields": [
    {"name": "order_id", "type": "string"},
    {"name": "user_id_fk", "type": "string"},
    {"name": "total", "type": "number"}
  ],
  "Values": [
    ["ORD-101", "USR-44", 99.50]
  ]
}
```

---

### Master-Slave Topological Federation

MFDB nodes utilize the `Network_Role` header to manage context windows:
- **Master Node (`"Master"`):** Full administrative registry, visibility into connected slaves, global policy distribution.
- **Slave Node (`"Slave"`):** High-performance operational workspace. Structurally blind to administrative paths, keeping the AI context window completely unbloated.

---

### MFDB-132 Session Mounting & Chunking

MFDB-132 collapses a full database folder into a single portable `Chunked-104a` file (`.mfdb132.bejson`).

#### Fixed Chunk Schema:
`File_Name`, `File_Extension`, `File_Content`, `File_Version`, `File_Hash`, `Relative_Path`, `Is_Binary`, `Is_Mounted`.

- **Session Mounting:** Writes a `.mfdb132_lock` file recording the package SHA-256 hash.
- **Sticky Mount:** Reuses existing workspace instantly if hash matches lock file.
- **Pre-Write Gate:** Validates database integrity before writing payload to disk.

---

## Comprehensive API Reference Matrix

### Python Module API (`Lib_PY`)

#### `Lib_PY.Core.lib_bejson_Core_bejson_core.BEJSONCore`
- `create_document(records_type: List[str], fields: List[Dict[str, Any]], format_version: str = "104") -> Dict[str, Any]`  
  Constructs a valid base BEJSON document dictionary with standard mandatory keys.
- `add_record(doc: Dict[str, Any], record: List[Any]) -> None`  
  Validates positional array length against `Fields` length and appends row to `Values`.
- `save_atomic(file_path: Path, doc: Dict[str, Any]) -> None`  
  Writes document to `.tmp` file and atomically renames to target path.
- `load_document(file_path: Path) -> Dict[str, Any]`  
  Reads and parses JSON file, executing boundary sanitization.

#### `Lib_PY.Core.lib_bejson_Core_bejson_validator.validate_bejson`
- `validate_bejson(doc_or_path: Union[Dict, Path, str]) -> ValidationResult`  
  Runs complete structural integrity checks and returns `ValidationResult` object containing `.valid`, `.errors`, and `.warnings`.

#### `Lib_PY.Core.lib_bejson_Core_bejson_parse.BEJSONParser`
- `__init__(doc: Dict[str, Any])`  
  Builds internal Field Map Cache ($O(1)$ index dictionary).
- `iter_records() -> Generator[Dict[str, Any], None, None]`  
  Yields dictionaries mapping field names to record values.
- `get_column_values(field_name: str) -> List[Any]`  
  Returns array of values for a specific field across all rows.

---

### JavaScript Module API (`Lib_JS`)

#### `Lib_JS.Core.lib_bejson_Core_bejson_core.js`
- `createDocument(recordsType, fields, formatVersion = "104")`  
  Returns initialized BEJSON document object.
- `addRecord(doc, record)`  
  Appends record array following positional integrity checks.
- `validateBEJSON(doc)`  
  Client-side validator returning `{ valid: boolean, errors: string[], warnings: string[] }`.
- `canonicalizeKeyOrder(doc)`  
  Reorders top-level keys into canonical BEJSON sequence.

#### `Lib_JS.Core.lib_bejson_Core_bejson_parse.js`
- `BEJSONParser(doc)`  
  Parser constructor with field map caching.
- `BEJSONParser.prototype.toObjectArray()`  
  Converts BEJSON matrix into an array of key-value objects.

---

### TypeScript Module API (`Lib_TS`)

#### `Lib_TS.Core.lib_bejson_Core_bejson_types.ts`
- Interfaces: `BEJSONField`, `BEJSONDocument104`, `BEJSONDocument104a`, `BEJSONDocument104db`, `BEJSONDocument105`, `ValidationResult`.
- Enum: `BEJSONDataType` (`"string" | "integer" | "number" | "boolean" | "array" | "object"`).

#### `Lib_TS.Core.lib_bejson_Core_bejson_validators.ts`
- `validateBEJSON(doc: unknown, options?: ValidationOptions): ValidationResult`  
  Type-guarded structural validator.

---

### Bash Module API (`Lib_SH`)

#### `Lib_SH.Core.lib_bejson_Core_be_core.sh`
- `be_core_get_record_count <file_path>`  
  Outputs integer count of rows in `Values`.
- `be_core_get_fields <file_path>`  
  Outputs JSON array of field definitions using `jq`.
- `be_core_get_field_index <file_path> <field_name>`  
  Outputs 0-based column index of a target field name.

#### `Lib_SH.Core.lib_bejson_Core_bejson_validator.sh`
- `be_validator_check_document <file_path>`  
  Returns 0 if valid BEJSON, 1 if invalid.

---

## Configuration & Environment Reference

All runtime libraries resolve path parameters through canonical environment stores or dynamic `$SCRIPT_PATH` relative resolution.

| Variable Name | Store File Location | Purpose |
| :--- | :--- | :--- |
| `SECUREENV_PATH` | `/storage/emulated/0/.env/secure/secureenv_file.json` | AES-GCM keys, API tokens, GitHub credentials |
| `PATHS_JSON` | `/storage/emulated/0/.env/user/paths.json` | Master filesystem roots (`ADMIN`, `SD_CARD`) |
| `ADMIN_LIBRARIES` | `paths.json` | Master library fallback path (`/storage/emulated/0/Admin/libraries`) |
| `PROJECT_INDEX_ROOT`| `paths.json` | Global project registration database root |
| `ADMIN_DEV` | `paths.json` | Administration tools and active dev projects |
| `ADMIN_TOOLS` | `paths.json` | Standalone CLI tools and shell utilities |

---

## Performance, Field Map Cache & Benchmarks

BEJSON performance stems from eliminating key string hashing during array traversal.

### Benchmark Telemetry (Python 3.10+ Runtime, 100,000 Records):

| Data Format | Parsing & Indexing Time | Memory Allocation | Payload Size |
| :--- | :--- | :--- | :--- |
| **Standard JSON Array-of-Objects** | 420 ms | 48.2 MB | 14.2 MB |
| **Raw CSV File** | 185 ms | 12.1 MB | 6.8 MB |
| **BEJSON 104 (Field Map Cache)** | **64 ms** | **11.4 MB** | **7.1 MB** |

- **Field Map Cache:** Positional lookup cache builds in $O(K)$ time (where $K$ is field count) and provides $O(1)$ property access thereafter.

---

## Exhaustive Error Registry & Diagnostic Code Reference

BEJSON and MFDB runtime engines surface standardized error codes across all 4 languages:

| Error Code | Error Constant | Exception Class | Description |
| :--- | :--- | :--- | :--- |
| `E01` | `E_INVALID_JSON` | `BEJSONValidationError` | Malformed JSON syntax or unparseable text stream |
| `E02` | `E_MISSING_MANDATORY_KEY` | `BEJSONValidationError` | One of 6 mandatory keys missing |
| `E03` | `E_INVALID_FORMAT` | `BEJSONValidationError` | `Format` key is not `"BEJSON"` |
| `E04` | `E_INVALID_VERSION` | `BEJSONValidationError` | `Format_Version` not in valid set |
| `E05` | `E_INVALID_RECORDS_TYPE` | `BEJSONValidationError` | `Records_Type` array malformed or empty |
| `E06` | `E_INVALID_FIELDS` | `BEJSONValidationError` | `Fields` is not an array of valid field objects |
| `E07` | `E_INVALID_VALUES` | `BEJSONValidationError` | `Values` is not an array of record arrays |
| `E08` | `E_TYPE_MISMATCH` | `BEJSONValidationError` | Value type does not match declared field type |
| `E09` | `E_RECORD_LENGTH_MISMATCH` | `BEJSONValidationError` | Row length does not match `Fields` length |
| `E10` | `E_RESERVED_KEY_COLLISION` | `BEJSONValidationError` | Custom 104a header collides with mandatory keys |
| `E11` | `E_INVALID_RECORD_TYPE_PARENT`| `BEJSONValidationError` | 104db field missing `Record_Type_Parent` assignment |
| `E12` | `E_FILE_NOT_FOUND` | `BEJSONValidationError` | Specified file path does not exist on disk |
| `E20` | `E_CORE_INVALID_RECORD` | `BEJSONCoreError` | Attempted to insert malformed record array |
| `E21` | `E_CORE_ATOMIC_WRITE_FAIL` | `BEJSONCoreError` | Failed to write temporary file or complete rename |
| `E30` | `E_MFDB_NOT_A_MANIFEST` | `MFDBValidationError` | File is not a valid 104a MFDB manifest |
| `E31` | `E_MFDB_NOT_AN_ENTITY` | `MFDBValidationError` | File is not a valid 104 MFDB entity file |
| `E32` | `E_MFDB_RECORDS_TYPE_INVALID`| `MFDBValidationError` | Manifest `Records_Type` is not `["mfdb"]` |
| `E33` | `E_MFDB_ENTITY_NOT_FOUND` | `MFDBValidationError` | Entity file path declared in manifest missing on disk |
| `E34` | `E_MFDB_NAME_MISMATCH` | `MFDBValidationError` | Entity `Records_Type` does not match manifest |
| `E35` | `E_MFDB_DUPLICATE_ENTRY` | `MFDBValidationError` | Duplicate `entity_name` or `file_path` in manifest |
| `E36` | `E_MFDB_MISSING_PARENT_HIERARCHY`| `MFDBValidationError` | Entity file missing mandatory `Parent_Hierarchy` |
| `E37` | `E_MFDB_MANIFEST_NOT_FOUND` | `MFDBValidationError` | Entity `Parent_Hierarchy` path missing on disk |
| `E38` | `E_MFDB_BIDIRECTIONAL_FAIL` | `MFDBValidationError` | Path mismatch between manifest and entity relative paths |
| `E39` | `E_MFDB_UNRESOLVED_FK` | `MFDBValidationError` | Foreign key reference target missing in strict mode |
| `E90` | `E_105_MISSING_FIELD_UUID` | `Format105IntegrityError` | Format 105 field object missing `field_uuid` |
| `E91` | `E_105_DUPLICATE_FIELD_UUID`| `Format105IntegrityError` | Duplicate `field_uuid` found within document |
| `E92` | `E_105_MISSING_RECORD_UUID` | `Format105IntegrityError` | Format 105 row missing `record_uuid` at reserved offset |
| `E93` | `E_105_DUPLICATE_RECORD_UUID`| `Format105IntegrityError` | Duplicate `record_uuid` found in row matrix |
| `E95` | `E_105_FAIL_ON_SWITCH` | `Format105IntegrityError` | Document re-headered to 105 without UUID compilation |
| `E130`| `E_NEST_EXCEEDED_DEPTH` | `BEJSONNestingError` | Recursive nesting depth exceeded 16 limit |
| `E134`| `E_NEST_UNIFORMITY_MISMATCH`| `BEJSONNestingError` | Nested documents in column have mismatched schemas |

---

## Security Policy & Cryptographic Integrity

1. **Credentials Isolation:** Secrets and private API keys reside strictly in `/storage/emulated/0/.env/secure/secureenv_file.json` and must never be inline-coded in repository scripts.
2. **Path Traversal Protection (`bejson_path_guard`):** All path arguments pass through strict path canonicalization to prevent directory traversal attacks (`../` escaping workspace bounds).
3. **Web Crypto AES-GCM Standard:**
   - Cipher: `AES-GCM 256-bit`
   - Key Derivation: `PBKDF2-SHA256` (100,000 iterations, 16-byte salt)
   - IV: `12-byte random initialization vector`
   - Cell Format Tag: `ENC:AES-GCM:<salt_b64>:<iv_b64>:<ciphertext_b64>`

---

## Troubleshooting & FAQ

<details>
<summary><strong>Q: Why does validate_bejson() reject custom top-level keys in BEJSON 104?</strong></summary>

*A: Custom top-level keys are strictly forbidden in BEJSON 104 to keep entity files lean. Use BEJSON 104a if file-level metadata is required, or use the built-in Parent_Hierarchy key exception.*
</details>

<details>
<summary><strong>Q: How do I handle schema migrations when adding a new field?</strong></summary>

*A: Always append new fields to the very end of the Fields array. Mid-array insertions alter positional offsets and break backward compatibility for existing parsers.*
</details>

<details>
<summary><strong>Q: What is the difference between BEJSON 104db and MFDB?</strong></summary>

*A: BEJSON 104db stores multiple entities in a single file using null-padding across columns. MFDB stores each entity in its own discrete BEJSON 104 file registered under a central 104a manifest.*
</details>

<details>
<summary><strong>Q: Why did my Format 105 document fail with error E95?</strong></summary>

*A: Error E95 is the Fail-on-Switch guard. It occurs when a 104 document's Format_Version header is changed to 105 without compiling the required field_uuid and record_uuid columns.*
</details>

<details>
<summary><strong>Q: Can I use BEJSON in bash shell scripts without Python?</strong></summary>

*A: Yes! Lib_SH/Core/lib_bejson_Core_be_core.sh provides pure Bash functions using jq for field map extraction, record counts, and document validation.*
</details>

---

## Development & Contribution Guidelines

1. **Checklist Requirement (Policy §3.4):** Any multi-step refactoring, schema change, or library update MUST initialize a timestamped checklist (`dev/checklist-<timestamp>.md`) prior to modifying codebase files.
2. **Mandatory Negative Constraints (Policy §5.3):**
   - ❌ Never Python `< 3.10`.
   - ❌ Never `print()` for logging (use standard `logging` module).
   - ❌ Never hardcode absolute path strings.
   - ❌ Never alter Release 300 / BEJSON 104 core frozen libraries without explicit permission.
3. **Language Parity Testing:** Any bug fix or feature addition applied to `Lib_PY` MUST be verified against `Lib_JS`, `Lib_TS`, and `Lib_SH` test suites to guarantee 4-language parity.

---

## Closing Summary

The **BEJSON 105 Core Libraries & Specification Ecosystem** provides a unified, local-first foundation for reliable data storage, structural verification, and agentic workspace management. By combining positional integrity, $O(1)$ field map caching, and multi-language parity, BEJSON delivers maximum data density and performance across modern software architectures.

---

## Polyglot License

This repository is distributed under a **Polyglot Open-Source License Model** to maximize interoperability across programming runtimes, technical documentation channels, and local-first data specifications:

- **Source Code & Libraries (Python, JavaScript, TypeScript, Bash):** Dual-licensed under the [MIT License](LICENSE) and [Apache 2.0 License](LICENSE-APACHE). Users may choose either license at their option.
- **Documentation & Technical Specifications:** Licensed under [Creative Commons Attribution 4.0 International (CC-BY 4.0)](https://creativecommons.org/licenses/by/4.0/).
- **BEJSON & MFDB Format Specifications:** Placed in the [Public Domain (CC0 1.0 Universal)](https://creativecommons.org/publicdomain/zero/1.0/) for unrestricted ecosystem adoption and zero-lock-in integration.

**Maintainer & Copyright:**  
© 2026 Elton Boehnen · [boehnenelton2024@gmail.com](mailto:boehnenelton2024@gmail.com) · [boehnenelton2024.pages.dev](https://boehnenelton2024.pages.dev) · [github.com/boehnenelton](https://github.com/boehnenelton)

---

*Documentation maintained by Elton Boehnen · [boehnenelton2024.pages.dev](https://boehnenelton2024.pages.dev)*
