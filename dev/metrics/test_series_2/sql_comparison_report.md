# Test Series 2: BEJSON 105 vs SQL (SQLite) Benchmark Report
**Comparative Systems Architecture Evaluation across 6 Critical Factors**
*Generated: 2026-11-09 22:24:55 UTC*

## 1. Executive Comparison Table

+------------------------------------+-------------------------+-------------------------+
| Benchmark Factor                   | SQL (SQLite3)           | BEJSON 105 / MFDB       |
+------------------------------------+-------------------------+-------------------------+
| Point Lookup Query Latency         |  23.53 µs                |   0.29 µs (80.4x)       |
| Point Query Throughput             |    42,504 ops/s         | 3,417,769 ops/s         |
| 5,000-Row Dataset Size (Minified)  | 1,130,496 bytes         |   873,484 bytes (-22.7%) |
| LLM Context Tokens (5,000 Rows)    |   720,726 tokens        |   226,878 tokens (-68.5%) |
| Batch Write / Ingestion Latency    |  39.75 ms (WAL/Trans)    |  94.33 ms (Atomic)      |
| C-Binary / Driver Dependency       | Compiled C Binary       | Zero-Binary / Pure JSON |
| Git Diffability & Portability      | Binary Opaque           | Deterministic Plaintext |
+------------------------------------+-------------------------+-------------------------+


## 2. In-Depth Factor Analysis

### Factor 1: Query & Lookup Performance
- **Point Queries**: BEJSON 105 in-memory O(1) field-map queries reached **3,417,769 ops/sec** (0.29 µs/op), achieving a **80.41x speedup** over indexed SQLite queries (42,504 ops/sec).
- **Full Scans**: Aggregating 5,000 rows executed in 0.483 ms in BEJSON 105 vs 1.174 ms in SQLite.

### Factor 2: Storage Footprint & Wire Transfer
- **On-Disk Size (5,000 Rows)**:
  - SQLite File: 1,130,496 bytes
  - BEJSON 105 Minified: 873,484 bytes
  - **Net Storage Reduction**: 22.73%
- **Gzipped Wire Size**:
  - SQLite: 365,363 bytes
  - BEJSON 105: 178,322 bytes

### Factor 3: AI & LLM Context Token Efficiency
- **Standard SQL Object Serialization**: 720,726 tokens
- **BEJSON 105 Matrix Schema**: 226,878 tokens
- **LLM Tokens Saved**: **493,847 tokens (68.52% reduction)**.

### Factor 4: Cascading Referential Integrity
- **SQLite 3-Tier Cascade**: Completed in 5.22 ms via in-process B-tree page deletion.
- **MFDB v1.40 3-Tier Cascade**: Completed in 1950.82 ms with full cross-file two-phase snapshot pre-commit guarantees, Parent_Hierarchy verification, and manifest count synchronization.

### Factor 5: Architecture & Environment Portability
- **Zero Binary Dependency**: BEJSON 105 runs universally across any environment with standard Python, Node.js, TypeScript, or Bash without requiring C compilers, dynamic linkers (`libsqlite3.so`), or root permissions.
- **Git Version Control**: BEJSON files are deterministic newline-delimited text files that can be diffed, merged, and reviewed line-by-line in git.

---
*Author Credit: Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton*
