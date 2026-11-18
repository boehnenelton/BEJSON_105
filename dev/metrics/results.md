# BEJSON 105 & MFDB v1.40 — Consolidated Test & Benchmark Results

- **Generated:** `2026-11-18T09:23:13.606129+00:00`
- **Test Suite Status:** `10/10 PASS` (`1582.92 ms` total execution time)
- **Standardized Metrics Recorded:** `13` records (`data/metrics_runs.105a.bejson`)

---

## 1. Executive Comparative Summary

- **BEJSON 105 Wide-Matrix Access — BEJSON 105: 24.40 M ops/s:** BEJSON 105 read 96,000 cells (64 cols × 1,500 rows) at 24.40M ops/s
- **BEJSON 105 vs SQLite Queries — BEJSON 105 was 80.41x faster than SQLite:** BEJSON 105: 3.42M ops/s vs SQLite (disk): 42.5k ops/s (8.24x faster vs :memory:)
- **BEJSON 105 vs Standard JSON Tokens — BEJSON 105 used 68.52% fewer tokens than JSON:** BEJSON 105: 226.9k tokens vs Standard JSON: 720.7k tokens (5,000 rows)
- **BEJSON 105 Bulk Write Speed — BEJSON 105 wrote 68.25k rows/sec:** BEJSON 105 wrote 15,000 UUID records in 220 ms + verified in 130 ms
- **BEJSON 105 & MFDB Test Suite — BEJSON 105 passed 10/10 tests:** All 10 BEJSON 105 and MFDB v1.40 test cases passed validation

---

## 2. Benchmark & Stress Test Summary by Category

### Point Lookup & Cell Throughput (`O(1) Field-Map Lookups vs SQLite (M ops/s)`)
- **BEJSON 105 (test_series_1 · federation_core):** `17.33 M ops/s`
- **BEJSON 105 (test_series_2 · bejson_vs_sqlite):** `3.42 M ops/s`
- **SQLite Baseline (test_series_2):** `0.04 M ops/s`
- **BEJSON 105 (test_series_3 · 25k_in_5_entities):** `8.30 M ops/s`
- **BEJSON 105 (test_series_3 · 60k_in_3_entities):** `7.67 M ops/s`
- **BEJSON 105 (sql_compare · bejson_vs_sqlite_500k):** `1.76 M ops/s`
- **SQLite Baseline (sql_compare):** `0.22 M ops/s`
- **BEJSON 105 (wide_64col · wide_matrix_96k_cells):** `24.65 M ops/s`

**Summary Findings:**
  - BEJSON 105 O(1) Field-Map point queries executed 3,417,769 ops/sec (0.29 µs/query) while SQLite disk B-tree queries executed 42,504 ops/sec (23.53 µs/query) — BEJSON 105 was 80.41x faster than SQLite on disk.
  - In the 500,000-query stress benchmark against in-memory SQLite (:memory:), BEJSON 105 completed 500,000 lookups at 1.75 M ops/sec (~285 ms) vs SQLite at 0.21 M ops/sec (~2,380 ms) — 8.24x faster than in-memory SQLite.
  - Across the 64-column × 1,500-row wide matrix (96,000 cells), O(1) Field-Map access sustained 24.70 M cell lookups/sec with 0% positional degradation between column 0 and column 63.

### LLM Token & Storage Compression (`BEJSON 105 vs JSON Footprint (k tokens)`)
- **BEJSON 105 (test_series_1):** `186.29 k tokens`
- **Standard JSON (test_series_1):** `581.77 k tokens`
- **BEJSON 105 (test_series_2):** `226.88 k tokens`
- **Standard JSON (test_series_2):** `720.73 k tokens`
- **BEJSON 105 (json_compare_10k):** `287.89 k tokens`
- **Standard JSON (json_compare_10k):** `854.72 k tokens`

**Summary Findings:**
  - On 10,000 8-field records (json_compare_10k), BEJSON 105a used 287,886 tokens (1.15 MB) while Standard JSON used 854,722 tokens (3.42 MB) — 566,836 fewer tokens (-66.32% reduction) for identical records.
  - On the 5,000-row SQL comparison dataset (test_series_2), BEJSON 105 used 226,878 tokens (873 KB) vs 720,726 tokens (2.77 MB) for SQL-JSON — 493,847 fewer tokens (-68.52% reduction).
  - Across 254 federated entities (test_series_1), BEJSON 105 used 186,292 tokens (717 KB) vs 581,766 tokens (2.24 MB) for Standard JSON — 395,474 fewer tokens (-67.98% reduction).

### High-Scale Bulk Ingestion (`Bulk Transaction Ingestion (k rec/s)`)
- **BEJSON 105 (test_series_3 · 25k_in_5_entities):** `53.27 k rec/s`
- **BEJSON 105 (test_series_3 · 60k_in_3_entities):** `47.65 k rec/s`
- **BEJSON 105 (stress_15k · bulk_tx_15k):** `68.68 k rec/s`

**Summary Findings:**
  - In stress_15k, BEJSON 105 wrote 15,000 UUID-stamped records in 220 ms (68.25k records/sec) using a single atomic transaction.
  - In test_series_3, BEJSON 105 wrote 25,000 records across 5 entities (4.0 MB) in 469 ms (53.27k records/sec), and 60,000 records across 3 entities (13.1 MB) in 1,259 ms (47.65k records/sec) — retaining 89% write speed when scaling volume by 2.4x.

### Memory & Integrity Gate (`Peak RSS (MB) & 15k Verify Gate (ms)`)
- **BEJSON 105 Peak RSS (test_series_1):** `26.01 MB`
- **BEJSON 105 Peak RSS (test_series_2):** `28.12 MB`
- **BEJSON 105 Peak RSS (test_series_3):** `26.07 MB`
- **BEJSON 105 Peak RSS (stress_15k):** `28.50 MB`
- **BEJSON 105 15k Verify Gate (stress_15k):** `129.46 ms`
- **BEJSON 105 Peak RSS (json_compare_10k):** `28.50 MB`
- **BEJSON 105 Peak RSS (sql_compare):** `28.50 MB`
- **BEJSON 105 Peak RSS (wide_64col):** `28.50 MB`

**Summary Findings:**
  - Full schema validation (validate_bejson) plus 105 UUID integrity verification (bejson_core_verify_105_integrity) across all 15,000 records completed in ~130 ms (115,000+ rows/sec verified).
  - Peak process memory stayed within 26.01 MB–28.50 MB for 5k–25k record workloads and reached 35.85 MB at 60,000 records (only 9.78 MB / +37.5% extra RAM for 35,000 additional records).

### Test Execution Latency (`Per-Test Execution Duration Across Suites (ms)`)
- **test_live_metrics_ledger_persisted_and_valid:** `286.83 ms [pass]`
- **test_negative_metric_rejected:** `45.08 ms [pass]`
- **test_round_trip_collect_and_render:** `44.84 ms [pass]`
- **test_schema_creation_and_validation:** `0.89 ms [pass]`
- **test_bejson_105_atomic_write_and_o1_lookup:** `12.75 ms [pass]`
- **test_mfdb_v140_manifest_and_fk_integrity:** `31.13 ms [pass]`
- **test_01_high_volume_bulk_transaction_stress_15k_rows:** `351.45 ms [pass]`
- **test_02_bejson_vs_json_token_and_storage_compression_10k_rows:** `243.56 ms [pass]`
- **test_03_bejson_o1_field_map_vs_sqlite_point_queries_500k:** `397.25 ms [pass]`
- **test_04_wide_table_64_columns_invariance_stress:** `169.15 ms [pass]`

**Summary Findings:**
  - Executed 10 standardized test cases in 1582.9 ms total with 10/10 passing (0 failures, 0 errors).
  - Fastest test: 'test_schema_creation_and_validation' completed in 0.89 ms; heaviest stress test: 'test_03_bejson_o1_field_map_vs_sqlite_point_queries_500k' (500,000 BEJSON vs SQLite lookups) completed in 397.25 ms.

---

## 3. Individual Automated Test Case Results (`data/test_results.105a.bejson`)

| # | Suite | Test Case | Domain | Status | Duration (ms) |
|---:|---|---|---|---|---:|
| 1 | `TestMetricsFamily` | `test_live_metrics_ledger_persisted_and_valid` | `bejson` | **PASS** | `286.83 ms` |
| 2 | `TestMetricsFamily` | `test_negative_metric_rejected` | `bejson` | **PASS** | `45.08 ms` |
| 3 | `TestMetricsFamily` | `test_round_trip_collect_and_render` | `bejson` | **PASS** | `44.84 ms` |
| 4 | `TestMetricsFamily` | `test_schema_creation_and_validation` | `bejson` | **PASS** | `0.89 ms` |
| 5 | `TestStandardizedBEJSONAndMFDB` | `test_bejson_105_atomic_write_and_o1_lookup` | `mfdb` | **PASS** | `12.75 ms` |
| 6 | `TestStandardizedBEJSONAndMFDB` | `test_mfdb_v140_manifest_and_fk_integrity` | `mfdb` | **PASS** | `31.13 ms` |
| 7 | `TestBEJSONStressAndComparisons` | `test_01_high_volume_bulk_transaction_stress_15k_rows` | `bejson` | **PASS** | `351.45 ms` |
| 8 | `TestBEJSONStressAndComparisons` | `test_02_bejson_vs_json_token_and_storage_compression_10k_rows` | `bejson` | **PASS** | `243.56 ms` |
| 9 | `TestBEJSONStressAndComparisons` | `test_03_bejson_o1_field_map_vs_sqlite_point_queries_500k` | `bejson` | **PASS** | `397.25 ms` |
| 10 | `TestBEJSONStressAndComparisons` | `test_04_wide_table_64_columns_invariance_stress` | `bejson` | **PASS** | `169.15 ms` |

---
Author Credit: Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
License: PolyForm-Noncommercial-1.0.0
