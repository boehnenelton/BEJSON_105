# Performance & Architecture Benchmark Report
**BEJSON 105 & MFDB v1.40 Multi-Entity Federation**
*Generated: 2026-11-09 UTC*

## 1. Executive Summary Table

```
+------------------------------------+----------------------------------------------------+
| Metric                             | Result                                             |
+------------------------------------+----------------------------------------------------+
| Federated Entity Count             | 254 Registered Entity Tables                       |
| Cascade Check                      | PASSED (Error [43/44] Block & Clean Cascade)       |
| Byte / Token Reduction %           | 70.1% (Range 65%-95%)                              |
| Peak RSS Memory                    | 16.4 MB (< 50 MB Target Ceiling)                  |
+------------------------------------+----------------------------------------------------+
```

## 2. Referential Integrity & Cascade Verification
- **Error [43] `E_MFDB_FK_TARGET_ENTITY_UNKNOWN`**: Caught successfully when an FK field declares a nonexistent target entity.
- **Error [44] `E_MFDB_FK_RESTRICT_VIOLATION`**: Restriction block verified when attempting to delete a service referenced by an active deployment (`fk_on_delete: "restrict"`).
- **Cascade Deletion**: Automatic clean cascade across `organizations` -> `clusters` -> `services` upon deleting root organization (`fk_on_delete: "cascade"`).
- **Restricted Unblocking**: Deleting the leaf deployment record unblocked parent deletion.

## 3. Scale & Efficiency Metrics (250 Entities & 4,000 Rows)
- **Federated Entity Count**: 254 discrete entities registered in master manifest (`105a.mfdb.bejson`).
- **On-Demand Entity Query Latency**: 1.93 ms across federated entity files.
- **Dataset Comparison (4,000 Rows)**:
  - Standard Repetitive-Key JSON: 2,172,001 bytes (~564,156 tokens)
  - BEJSON 105: 649,417 bytes (~168,679 tokens)
  - **Net Byte Reduction**: 70.1%
  - **Net Token Reduction**: 70.1% (~395,476 LLM tokens saved per 4k rows)
- **Peak RSS Memory**: 16,824 kB (~16.4 MB, well below the 50 MB target ceiling).

## 4. Speed & Throughput Benchmarks
- **O(1) Field-Map Lookups**: 15,736,023 lookups/sec (7.72x speedup over linear scan).
- **Two-Phase Atomic Write Latency by Tier**:
  - `1KB_Tiny` (1.5 KB): 1.01 ms (1.42 MB/s)
  - `10KB_Small` (12.1 KB): 1.36 ms (8.50 MB/s)
  - `100KB_Medium` (118.7 KB): 5.30 ms (21.37 MB/s)
  - `500KB_Large` (594.2 KB): 20.67 ms (27.42 MB/s)
- **105db Single-File Bundle Query**: 2,581,670 ops/sec (0.39 µs/op).
- **Cascade Tree Delete (3 Hops)**: 1,442.31 ms (full multi-file pre-commit snapshotting, atomic writes, and manifest count synchronization).

---
*Author Credit: Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton*
