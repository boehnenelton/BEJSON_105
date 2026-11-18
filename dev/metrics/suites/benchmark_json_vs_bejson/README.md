# benchmark_tool1-json_vs_bejson

> Part of the Python Benchmark Tool Series (`benchmark_tool1-(name)`)  
> Author: Elton Boehnen · boehnenelton2024@gmail.com · [boehnenelton2024.pages.dev](https://boehnenelton2024.pages.dev)  
> License: PolyForm Noncommercial License 1.0.0 (`PolyForm-Noncommercial-1.0.0`)

---

## Overview

`benchmark_tool1-json_vs_bejson` is a standardized standalone Python CLI benchmark engine designed to compare **Standard Key-Value JSON** against **BEJSON 104** and **BEJSON 105** across:

1. **Wire Size Footprint**: Raw byte payload comparison and compression ratios.
2. **LLM Prompt Token Economics**: Token fragmentation metrics and API query cost differentials (`cl100k`, `llama3`, and standard tokenizers).
3. **Parser Throughput & Latency**: `json.loads()` baseline vs. BEJSON parsing with constant-time **O(1) Field Map resolution**.
4. **Persistent BEJSON 105 Run Logging**: Automated telemetry logging into `logs/benchmark_runs.105.bejson`.

---

## Mobile Portrait TUI Discipline

All terminal status outputs, ASCII data tables, and metrics reports strictly comply with the **49-character viewport ceiling** (Policy §8), eliminating line-wrap distortion on narrow Android Termux screens.

```
=================================================
     [✓] BENCHMARK 1: JSON VS BEJSON 104/105     
-------------------------------------------------
Scale: 500 rows | Loops: 100 | Tok: cl100k
-------------------------------------------------
METRIC             JSON       BEJSON 105  DELTA   
-------------------------------------------------
Wire Size          102.5 KB   78.1 KB     -23.8%
Prompt Tokens      30,689     19,311      -37.1%
Cost / 1k queries  $92.07     $57.93      -$34.13
Latency (ms/op)    2.456ms    1.153ms     O(1) Map
Throughput         407 op/s   867 op/s    66.15MB/s
-------------------------------------------------
Tokens Saved:  11,378 prompt tokens
Bytes Saved:   25,009 bytes (23.8%)
Field-Map:     Constant-time O(1) resolution
=================================================
```

---

## CLI Usage

### 1. Run Standard Benchmark
```bash
python3 benchmark_tool.py
```

### 2. Custom Scale & Iterations
```bash
# 5,000 records, 1,000 loop iterations
python3 benchmark_tool.py --scale 5000 --iterations 1000
```

### 3. Change Tokenizer Profile
```bash
python3 benchmark_tool.py --tokenizer llama3
```

### 4. Export Results
```bash
python3 benchmark_tool.py --scale 1000 --export report.json
```

### 5. Historical Run Statistics
```bash
python3 benchmark_tool.py --stats
```

### 6. Self-Validation Check
```bash
python3 benchmark_tool.py --validate
```

---

## Directory Structure

```
~/benchmark_tool1-json_vs_bejson/
├── benchmark_tool.py       # Main CLI benchmark executable
├── config/
│   └── config.json         # Tool configuration defaults
├── logs/
│   ├── benchmark.log       # Rotating execution log
│   └── benchmark_runs.105.bejson # Canonical BEJSON 105 run store
├── tests/
│   └── test_benchmark_tool.py    # Unit test suite (9 tests)
└── README.md               # Documentation
```
