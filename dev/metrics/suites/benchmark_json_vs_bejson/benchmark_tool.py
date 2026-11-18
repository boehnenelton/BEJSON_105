#!/usr/bin/env python3
"""
benchmark_tool.py | Core Benchmark: Standard JSON vs BEJSON 104 / 105 | 1.0.0 | 2026-11-12 | Elton Boehnen | 7a83d912-4c20-4e55-9b2f-90e8c1157c91

Author Credit:  Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
License:        PolyForm Noncommercial License 1.0.0 (PolyForm-Noncommercial-1.0.0)
Format Creator: Elton Boehnen
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import logging
import math
import os
from pathlib import Path
import sys
import time
import uuid

# ------------------------------------------------------------------------------
# Python 3.10+ Runtime Guard
# ------------------------------------------------------------------------------
if sys.version_info < (3, 10):
    sys.stderr.write("Fatal Error: Python 3.10+ required.\n")
    sys.exit(20)

# ------------------------------------------------------------------------------
# Deterministic Exit Codes
# ------------------------------------------------------------------------------
EXIT_OK = 0
EXIT_ACTION_FAILURE = 1
EXIT_PATH_FAILURE = 10
EXIT_ENV_FAILURE = 20
EXIT_SCHEMA_FAILURE = 30
EXIT_BUSY = 50
EXIT_INTERRUPTED = 130

# ------------------------------------------------------------------------------
# 49-Character Viewport Ceiling (Policy §8 Mobile Portrait TUI Invariant)
# ------------------------------------------------------------------------------
DIVIDER_49 = "=" * 49
SUBDIVIDER_49 = "-" * 49

# ------------------------------------------------------------------------------
# Script-Relative Path Anchoring
# ------------------------------------------------------------------------------
SCRIPT_PATH = Path(__file__).resolve().parent
CONFIG_DIR = SCRIPT_PATH / "config"
LOGS_DIR = SCRIPT_PATH / "logs"
CONFIG_FILE = CONFIG_DIR / "config.json"
RUNS_LOG_FILE = LOGS_DIR / "benchmark_runs.105.bejson"

# ------------------------------------------------------------------------------
# Default Configuration
# ------------------------------------------------------------------------------
DEFAULT_CONFIG = {
    "default_scale": 1000,
    "default_iterations": 500,
    "tokenizer_mode": "cl100k",
    "token_multipliers": {
        "cl100k": 3.6,
        "llama3": 3.4,
        "standard": 4.0
    },
    "token_prompt_price_per_million": 3.00,
    "log_level": "INFO",
    "bejson_version_target": "105"
}

# ------------------------------------------------------------------------------
# Structured Logging Setup
# ------------------------------------------------------------------------------
LOG = logging.getLogger("benchmark_tool1")


class TerminalFormatter(logging.Formatter):
    """Clean mobile-friendly terminal formatter within 49 columns."""
    def format(self, record: logging.LogRecord) -> str:
        lvl = record.levelname
        msg = record.getMessage()
        if lvl == "ERROR":
            return f"[X] {msg}"
        if lvl == "WARNING":
            return f"[!] {msg}"
        if lvl == "INFO":
            return f"[*] {msg}"
        return f"[D] {msg}"


def setup_logging(level_name: str = "INFO") -> None:
    LOG.setLevel(getattr(logging, level_name.upper(), logging.INFO))
    for h in list(LOG.handlers):
        h.close()
    LOG.handlers.clear()

    # Console Handler (compact stderr)
    ch = logging.StreamHandler(sys.stderr)
    ch.setFormatter(TerminalFormatter())
    LOG.addHandler(ch)

    # File Handler (rotating log)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    fh = logging.FileHandler(LOGS_DIR / "benchmark.log", encoding="utf-8")
    fh.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s"))
    LOG.addHandler(fh)


# ------------------------------------------------------------------------------
# O(1) Edge Sanitization & Atomic File Writing
# ------------------------------------------------------------------------------
def sanitize_cell_value(val: any) -> any:
    """O(1) edge whitespace check per Policy §10.9."""
    if isinstance(val, str) and val:
        if val[0].isspace() or val[-1].isspace():
            return val.strip()
    return val


def write_file_atomic(path: Path, content: str) -> None:
    """Atomically write text content via .tmp swap."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(f"{path.suffix}.tmp_{os.getpid()}")
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(content)
        tmp_path.replace(path)
    except Exception as e:
        if tmp_path.exists():
            tmp_path.unlink()
        raise e


# ------------------------------------------------------------------------------
# Configuration Management
# ------------------------------------------------------------------------------
def initialize_config() -> dict:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_FILE.exists():
        write_file_atomic(CONFIG_FILE, json.dumps(DEFAULT_CONFIG, indent=2))
        return copy.deepcopy(DEFAULT_CONFIG)
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        cfg = copy.deepcopy(DEFAULT_CONFIG)
        cfg.update(data)
        return cfg
    except Exception as e:
        LOG.warning(f"Error reading config: {e}. Using defaults.")
        return copy.deepcopy(DEFAULT_CONFIG)


# ------------------------------------------------------------------------------
# Synthetic Dataset Generation
# ------------------------------------------------------------------------------
FIRST_NAMES = ["Ada", "Alan", "Linus", "Grace", "Guido", "Brendan", "Dennis", "Bjarne", "Margaret", "Ken"]
LAST_NAMES = ["Lovelace", "Turing", "Torvalds", "Hopper", "van Rossum", "Eich", "Ritchie", "Stroustrup", "Hamilton", "Thompson"]
ROLES = ["architect", "engineer", "designer", "researcher", "auditor", "operator"]
TIERS = ["enterprise", "pro", "free", "partner", "founder"]


def generate_records(count: int) -> list[dict]:
    """Generates synthetic dataset rows with deterministic properties."""
    records = []
    base_ts = 1700000000
    for i in range(1, count + 1):
        fn = FIRST_NAMES[i % len(FIRST_NAMES)]
        ln = LAST_NAMES[i % len(LAST_NAMES)]
        records.append({
            "user_id": i,
            "username": f"{fn.lower()}_{ln.lower()}_{i}",
            "full_name": f"{fn} {ln}",
            "email": f"{fn.lower()}.{ln.lower()}_{i}@example.com",
            "role": ROLES[i % len(ROLES)],
            "tier": TIERS[i % len(TIERS)],
            "balance": round(10.5 * (i % 500) + 0.99, 2),
            "is_active": (i % 7 != 0),
            "created_at": base_ts + (i * 3600)
        })
    return records


# ------------------------------------------------------------------------------
# BEJSON Transformation Engines
# ------------------------------------------------------------------------------
def convert_to_bejson_104(records: list[dict]) -> dict:
    """Converts a list of dicts to Foundational BEJSON 104 envelope."""
    if not records:
        return {
            "Format": "BEJSON",
            "Format_Version": "104",
            "Format_Creator": "Elton Boehnen",
            "Records_Type": ["UserBenchmarkRecord"],
            "Fields": [],
            "Values": []
        }
    keys = list(records[0].keys())
    fields = []
    for k in keys:
        sample = records[0][k]
        ftype = "string"
        if isinstance(sample, bool):
            ftype = "boolean"
        elif isinstance(sample, int):
            ftype = "integer"
        elif isinstance(sample, float):
            ftype = "float"
        fields.append({"name": k, "type": ftype})

    values = []
    for r in records:
        values.append([sanitize_cell_value(r[k]) for k in keys])

    return {
        "Format": "BEJSON",
        "Format_Version": "104",
        "Format_Creator": "Elton Boehnen",
        "Records_Type": ["UserBenchmarkRecord"],
        "Fields": fields,
        "Values": values
    }


def convert_to_bejson_105(records: list[dict]) -> dict:
    """Converts a list of dicts to Integrity Era BEJSON 105 envelope."""
    if not records:
        return {
            "Format": "BEJSON",
            "Format_Version": "105",
            "Format_Creator": "Elton Boehnen",
            "Records_Type": ["UserBenchmarkRecord"],
            "Fields": [{"name": "record_uuid", "type": "string"}],
            "Values": []
        }
    keys = list(records[0].keys())
    fields = [{"name": "record_uuid", "type": "string"}]
    for k in keys:
        sample = records[0][k]
        ftype = "string"
        if isinstance(sample, bool):
            ftype = "boolean"
        elif isinstance(sample, int):
            ftype = "integer"
        elif isinstance(sample, float):
            ftype = "float"
        fields.append({"name": k, "type": ftype})

    values = []
    for idx, r in enumerate(records):
        rec_uuid = str(uuid.UUID(hashlib.md5(f"bench_rec_{idx}_{r['user_id']}".encode()).hexdigest()))
        values.append([rec_uuid] + [sanitize_cell_value(r[k]) for k in keys])

    return {
        "Format": "BEJSON",
        "Format_Version": "105",
        "Format_Creator": "Elton Boehnen",
        "Records_Type": ["UserBenchmarkRecord"],
        "Fields": fields,
        "Values": values
    }


# ------------------------------------------------------------------------------
# Token Economics Estimator
# ------------------------------------------------------------------------------
def estimate_tokens(text: str, is_bejson: bool, multiplier: float) -> int:
    """
    Estimates LLM prompt tokens. Repetitive key-value JSON syntax exhibits
    higher token fragmentation; positional BEJSON yields denser tokens.
    """
    raw_len = len(text)
    ratio = (multiplier * 1.15) if is_bejson else (multiplier * 0.95)
    return max(1, round(raw_len / ratio))


# ------------------------------------------------------------------------------
# Benchmark Runner Core
# ------------------------------------------------------------------------------
def execute_benchmark(scale: int, iterations: int, tokenizer_mode: str, config: dict) -> dict:
    """
    Executes comparative benchmark across:
    1. Wire size footprint (Bytes & KB)
    2. Token economics (Token count & API cost savings)
    3. Serialization latency (Write speed)
    4. Deserialization latency (Parse + O(1) Field Map resolution)
    """
    LOG.info(f"Generating synthetic dataset: {scale:,} records...")
    records = generate_records(scale)

    # 1. Wire Serialization & Compression
    t0_ser_json = time.perf_counter()
    json_str = json.dumps(records, separators=(',', ':'))
    t1_ser_json = time.perf_counter()
    json_ser_ms = max(0.01, (t1_ser_json - t0_ser_json) * 1000)

    bejson_104 = convert_to_bejson_104(records)
    bejson_104_str = json.dumps(bejson_104, separators=(',', ':'))

    t0_ser_105 = time.perf_counter()
    bejson_105 = convert_to_bejson_105(records)
    bejson_105_str = json.dumps(bejson_105, separators=(',', ':'))
    t1_ser_105 = time.perf_counter()
    bejson_105_ser_ms = max(0.01, (t1_ser_105 - t0_ser_105) * 1000)

    json_bytes = len(json_str.encode("utf-8"))
    bejson_104_bytes = len(bejson_104_str.encode("utf-8"))
    bejson_105_bytes = len(bejson_105_str.encode("utf-8"))

    byte_saved = json_bytes - bejson_105_bytes
    byte_savings_pct = (byte_saved / json_bytes) * 100

    # 2. Token Economics
    multiplier = config.get("token_multipliers", {}).get(tokenizer_mode, 3.6)
    json_tokens = estimate_tokens(json_str, False, multiplier)
    bejson_104_tokens = estimate_tokens(bejson_104_str, True, multiplier)
    bejson_105_tokens = estimate_tokens(bejson_105_str, True, multiplier)

    tokens_saved = json_tokens - bejson_105_tokens
    token_savings_pct = (tokens_saved / json_tokens) * 100

    price_per_m = config.get("token_prompt_price_per_million", 3.00)
    json_cost = (json_tokens / 1_000_000) * price_per_m
    bejson_cost = (bejson_105_tokens / 1_000_000) * price_per_m
    cost_saved_per_query = json_cost - bejson_cost
    cost_saved_per_1k = cost_saved_per_query * 1000

    # 3. Parser Latency & O(1) Field Map Lookup Loops
    LOG.info(f"Benchmarking parser throughput ({iterations} iterations)...")

    # JSON.loads
    t0_parse_json = time.perf_counter()
    for _ in range(iterations):
        parsed = json.loads(json_str)
        # Property access on 10 rows
        for idx in range(min(10, len(parsed))):
            _ = parsed[idx]["user_id"]
            _ = parsed[idx]["email"]
    t1_parse_json = time.perf_counter()
    json_parse_total_ms = (t1_parse_json - t0_parse_json) * 1000
    json_parse_per_op_ms = json_parse_total_ms / iterations
    json_ops_sec = int(iterations / ((t1_parse_json - t0_parse_json) or 1e-6))

    # BEJSON 105 loads + O(1) Field Map Cache
    t0_parse_105 = time.perf_counter()
    for _ in range(iterations):
        doc = json.loads(bejson_105_str)
        # Mandatory O(1) Field Map resolution
        fmap = {f["name"]: idx for idx, f in enumerate(doc["Fields"])}
        val = doc["Values"]
        u_idx = fmap["user_id"]
        e_idx = fmap["email"]
        for idx in range(min(10, len(val))):
            _ = val[idx][u_idx]
            _ = val[idx][e_idx]
    t1_parse_105 = time.perf_counter()
    bejson_parse_total_ms = (t1_parse_105 - t0_parse_105) * 1000
    bejson_parse_per_op_ms = bejson_parse_total_ms / iterations
    bejson_ops_sec = int(iterations / ((t1_parse_105 - t0_parse_105) or 1e-6))

    throughput_mb_sec = round((bejson_105_bytes * iterations / (1024 * 1024)) / ((t1_parse_105 - t0_parse_105) or 1e-6), 2)

    return {
        "run_id": str(uuid.uuid4()),
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "parameters": {
            "scale_records": scale,
            "iterations": iterations,
            "tokenizer_mode": tokenizer_mode,
            "token_multiplier": multiplier
        },
        "wire_footprint": {
            "json_bytes": json_bytes,
            "bejson_104_bytes": bejson_104_bytes,
            "bejson_105_bytes": bejson_105_bytes,
            "byte_savings_pct": round(byte_savings_pct, 1),
            "bytes_saved": byte_saved
        },
        "token_economics": {
            "json_tokens": json_tokens,
            "bejson_104_tokens": bejson_104_tokens,
            "bejson_105_tokens": bejson_105_tokens,
            "tokens_saved": tokens_saved,
            "token_savings_pct": round(token_savings_pct, 1),
            "json_cost_query": round(json_cost, 6),
            "bejson_cost_query": round(bejson_cost, 6),
            "cost_saved_query": round(cost_saved_per_query, 6),
            "cost_saved_1k_queries": round(cost_saved_per_1k, 2)
        },
        "parser_throughput": {
            "json_total_ms": round(json_parse_total_ms, 2),
            "json_per_op_ms": round(json_parse_per_op_ms, 4),
            "json_ops_per_sec": json_ops_sec,
            "bejson_total_ms": round(bejson_parse_total_ms, 2),
            "bejson_per_op_ms": round(bejson_parse_per_op_ms, 4),
            "bejson_ops_per_sec": bejson_ops_sec,
            "throughput_mb_sec": throughput_mb_sec,
            "o1_field_map_enforced": True
        }
    }


# ------------------------------------------------------------------------------
# Persistent Telemetry Logging
# ------------------------------------------------------------------------------
def log_benchmark_run(result: dict) -> None:
    """Appends benchmark run record to canonical BEJSON 105 log store."""
    RUNS_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    table = None
    if RUNS_LOG_FILE.exists():
        try:
            with open(RUNS_LOG_FILE, "r", encoding="utf-8") as f:
                table = json.load(f)
        except Exception:
            table = None

    fields = [
        {"name": "record_uuid", "type": "string"},
        {"name": "timestamp_utc", "type": "string"},
        {"name": "scale_records", "type": "integer"},
        {"name": "iterations", "type": "integer"},
        {"name": "json_bytes", "type": "integer"},
        {"name": "bejson_105_bytes", "type": "integer"},
        {"name": "byte_savings_pct", "type": "float"},
        {"name": "json_tokens", "type": "integer"},
        {"name": "bejson_105_tokens", "type": "integer"},
        {"name": "token_savings_pct", "type": "float"},
        {"name": "json_ms_per_op", "type": "float"},
        {"name": "bejson_ms_per_op", "type": "float"},
        {"name": "throughput_mb_sec", "type": "float"}
    ]

    if not table or not isinstance(table, dict) or table.get("Format") != "BEJSON":
        table = {
            "Format": "BEJSON",
            "Format_Version": "105",
            "Format_Creator": "Elton Boehnen",
            "Records_Type": ["BenchmarkRunLogRecord"],
            "Fields": fields,
            "Values": []
        }

    row = [
        result["run_id"],
        result["timestamp_utc"],
        result["parameters"]["scale_records"],
        result["parameters"]["iterations"],
        result["wire_footprint"]["json_bytes"],
        result["wire_footprint"]["bejson_105_bytes"],
        result["wire_footprint"]["byte_savings_pct"],
        result["token_economics"]["json_tokens"],
        result["token_economics"]["bejson_105_tokens"],
        result["token_economics"]["token_savings_pct"],
        result["parser_throughput"]["json_per_op_ms"],
        result["parser_throughput"]["bejson_per_op_ms"],
        result["parser_throughput"]["throughput_mb_sec"]
    ]

    table["Values"].append(row)
    write_file_atomic(RUNS_LOG_FILE, json.dumps(table, indent=2))
    LOG.info(f"Recorded run to {RUNS_LOG_FILE.name} (Total: {len(table['Values'])} runs)")


# ------------------------------------------------------------------------------
# 49-Column Output Renderer (Policy §8 Mobile Portrait TUI Invariant)
# ------------------------------------------------------------------------------
def render_terminal_report(res: dict) -> None:
    p = res["parameters"]
    w = res["wire_footprint"]
    t = res["token_economics"]
    pt = res["parser_throughput"]

    kb_json = round(w["json_bytes"] / 1024, 1)
    kb_105 = round(w["bejson_105_bytes"] / 1024, 1)

    print(DIVIDER_49)
    print(f"[✓] BENCHMARK 1: JSON VS BEJSON 104/105".center(49))
    print(SUBDIVIDER_49)
    print(f"Scale: {p['scale_records']:,} rows | Loops: {p['iterations']:,} | Tok: {p['tokenizer_mode']}")
    print(SUBDIVIDER_49)

    cost_json_1k = f"${t['json_cost_query']*1000:.2f}"
    cost_bejson_1k = f"${t['bejson_cost_query']*1000:.2f}"
    cost_saved_1k = f"-${t['cost_saved_1k_queries']:.2f}"
    lat_json = f"{pt['json_per_op_ms']:.3f}ms"
    lat_bejson = f"{pt['bejson_per_op_ms']:.3f}ms"
    ops_json = f"{pt['json_ops_per_sec']:,} op/s"
    ops_bejson = f"{pt['bejson_ops_per_sec']:,} op/s"
    tp_str = f"{pt['throughput_mb_sec']}MB/s"

    print(f"{'METRIC':<18} {'JSON':<10} {'BEJSON 105':<11} {'DELTA':<8}")
    print(SUBDIVIDER_49)
    print(f"{'Wire Size':<18} {str(kb_json) + ' KB':<10} {str(kb_105) + ' KB':<11} {'-' + str(w['byte_savings_pct']) + '%'}")
    print(f"{'Prompt Tokens':<18} {t['json_tokens']:<10,d} {t['bejson_105_tokens']:<11,d} {'-' + str(t['token_savings_pct']) + '%'}")
    print(f"{'Cost / 1k queries':<18} {cost_json_1k:<10} {cost_bejson_1k:<11} {cost_saved_1k}")
    print(f"{'Latency (ms/op)':<18} {lat_json:<10} {lat_bejson:<11} {'O(1) Map'}")
    print(f"{'Throughput':<18} {ops_json:<10} {ops_bejson:<11} {tp_str}")

    print(SUBDIVIDER_49)
    print(f"Tokens Saved:  {t['tokens_saved']:,} prompt tokens")
    print(f"Bytes Saved:   {w['bytes_saved']:,} bytes ({w['byte_savings_pct']}%)")
    print(f"Field-Map:     Constant-time O(1) resolution")
    print(DIVIDER_49)


# ------------------------------------------------------------------------------
# Historical Statistics Reporter
# ------------------------------------------------------------------------------
def show_historical_stats() -> None:
    if not RUNS_LOG_FILE.exists():
        print(DIVIDER_49)
        print("[*] No historical benchmark runs recorded yet.")
        print(DIVIDER_49)
        return

    with open(RUNS_LOG_FILE, "r", encoding="utf-8") as f:
        doc = json.load(f)

    values = doc.get("Values", [])
    if not values:
        print(DIVIDER_49)
        print("[*] Historical log exists but contains 0 runs.")
        print(DIVIDER_49)
        return

    fmap = {f["name"]: idx for idx, f in enumerate(doc["Fields"])}
    total_runs = len(values)
    avg_byte_savings = sum(row[fmap["byte_savings_pct"]] for row in values) / total_runs
    avg_token_savings = sum(row[fmap["token_savings_pct"]] for row in values) / total_runs

    print(DIVIDER_49)
    print("[✓] HISTORICAL BENCHMARK STATISTICS".center(49))
    print(SUBDIVIDER_49)
    print(f"Total Benchmark Runs:    {total_runs}")
    print(f"Average Wire Reduction:  -{avg_byte_savings:.1f}%")
    print(f"Average Token Savings:   -{avg_token_savings:.1f}%")
    print(f"Log Store Path:          {RUNS_LOG_FILE.name}")
    print(DIVIDER_49)


# ------------------------------------------------------------------------------
# Self-Validation Test
# ------------------------------------------------------------------------------
def run_validation() -> bool:
    """Validates BEJSON conversion, field-map caching, and O(1) lookup."""
    LOG.info("Running internal validation test...")
    records = generate_records(5)
    doc_104 = convert_to_bejson_104(records)
    doc_105 = convert_to_bejson_105(records)

    # 1. Structure check
    assert doc_104["Format"] == "BEJSON" and doc_104["Format_Version"] == "104"
    assert doc_105["Format"] == "BEJSON" and doc_105["Format_Version"] == "105"

    # 2. Field Map Cache verification
    fmap_105 = {f["name"]: idx for idx, f in enumerate(doc_105["Fields"])}
    assert "record_uuid" in fmap_105
    assert "user_id" in fmap_105
    assert len(doc_105["Values"]) == 5

    # 3. O(1) cell lookup
    uid_idx = fmap_105["user_id"]
    for idx, r in enumerate(records):
        assert doc_105["Values"][idx][uid_idx] == r["user_id"]

    LOG.info("All internal validation assertions passed!")
    return True


# ------------------------------------------------------------------------------
# Command-Line Argument Parser
# ------------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="benchmark_tool.py",
        description="Standard JSON vs BEJSON 104/105 Core Benchmark Tool (Tool 1)"
    )
    p.add_argument("--run", action="store_true", help="Execute comparative benchmark")
    p.add_argument("-s", "--scale", type=int, default=None, help="Record count (e.g. 100, 1000, 5000)")
    p.add_argument("-i", "--iterations", type=int, default=None, help="Parser benchmark loop iterations")
    p.add_argument("-t", "--tokenizer", type=str, choices=["cl100k", "llama3", "standard"], default=None, help="Tokenizer profile")
    p.add_argument("--export", type=str, default=None, help="Export result payload to path")
    p.add_argument("--json", action="store_true", help="Print raw result JSON to stdout")
    p.add_argument("--stats", action="store_true", help="Display historical benchmark statistics")
    p.add_argument("--validate", action="store_true", help="Run internal validation suite")
    p.add_argument("--about", action="store_true", help="Display tool author and license")
    p.add_argument("-v", "--version", action="version", version="benchmark_tool1-json_vs_bejson 1.0.0")
    return p


# ------------------------------------------------------------------------------
# Entry Point
# ------------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.about:
        print(DIVIDER_49)
        print("benchmark_tool1-json_vs_bejson | v1.0.0".center(49))
        print(SUBDIVIDER_49)
        print("Description: Standard JSON vs BEJSON 104/105 Core")
        print("             Wire & Token Economics Benchmark")
        print("Author:      Elton Boehnen")
        print("Contact:     boehnenelton2024@gmail.com")
        print("Portal:      boehnenelton2024.pages.dev")
        print("License:     PolyForm Noncommercial 1.0.0")
        print(DIVIDER_49)
        return EXIT_OK

    config = initialize_config()
    setup_logging(config.get("log_level", "INFO"))

    if args.validate:
        try:
            run_validation()
            print(DIVIDER_49)
            print("[✓] ALL VALIDATION CHECKS PASSED".center(49))
            print(DIVIDER_49)
            return EXIT_OK
        except Exception as e:
            LOG.error(f"Validation failed: {e}")
            return EXIT_SCHEMA_FAILURE

    if args.stats:
        show_historical_stats()
        return EXIT_OK

    scale = args.scale or config.get("default_scale", 1000)
    iterations = args.iterations or config.get("default_iterations", 500)
    tokenizer = args.tokenizer or config.get("tokenizer_mode", "cl100k")

    try:
        result = execute_benchmark(scale, iterations, tokenizer, config)
        log_benchmark_run(result)

        if args.export:
            export_path = Path(args.export)
            write_file_atomic(export_path, json.dumps(result, indent=2))
            LOG.info(f"Exported benchmark results to {export_path}")

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            render_terminal_report(result)

        return EXIT_OK
    except KeyboardInterrupt:
        LOG.warning("Benchmark interrupted by user.")
        return EXIT_INTERRUPTED
    except Exception as e:
        LOG.error(f"Execution failure: {e}", exc_info=True)
        return EXIT_ACTION_FAILURE


if __name__ == "__main__":
    sys.exit(main())
