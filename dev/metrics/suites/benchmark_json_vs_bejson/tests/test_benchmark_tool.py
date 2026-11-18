"""
test_benchmark_tool.py | Unit Test Suite for benchmark_tool1-json_vs_bejson
Author Credit:  Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
License:        PolyForm Noncommercial License 1.0.0 (PolyForm-Noncommercial-1.0.0)
"""

import json
from pathlib import Path
import sys
import unittest

# Ensure parent directory is on sys.path
TOOL_DIR = Path(__file__).resolve().parent.parent
if str(TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(TOOL_DIR))

import benchmark_tool


class TestBenchmarkTool1(unittest.TestCase):

    def setUp(self):
        self.config = benchmark_tool.initialize_config()

    def test_01_deterministic_exit_codes(self):
        self.assertEqual(benchmark_tool.EXIT_OK, 0)
        self.assertEqual(benchmark_tool.EXIT_ACTION_FAILURE, 1)
        self.assertEqual(benchmark_tool.EXIT_PATH_FAILURE, 10)
        self.assertEqual(benchmark_tool.EXIT_ENV_FAILURE, 20)
        self.assertEqual(benchmark_tool.EXIT_SCHEMA_FAILURE, 30)

    def test_02_49_column_ceiling(self):
        self.assertEqual(len(benchmark_tool.DIVIDER_49), 49)
        self.assertEqual(len(benchmark_tool.SUBDIVIDER_49), 49)

    def test_03_generate_records(self):
        records = benchmark_tool.generate_records(25)
        self.assertEqual(len(records), 25)
        first = records[0]
        self.assertIn("user_id", first)
        self.assertIn("username", first)
        self.assertIn("email", first)
        self.assertIn("balance", first)
        self.assertIn("is_active", first)
        self.assertEqual(first["user_id"], 1)

    def test_04_bejson_104_conversion(self):
        records = benchmark_tool.generate_records(10)
        doc = benchmark_tool.convert_to_bejson_104(records)
        self.assertEqual(doc["Format"], "BEJSON")
        self.assertEqual(doc["Format_Version"], "104")
        self.assertEqual(len(doc["Values"]), 10)
        fmap = {f["name"]: idx for idx, f in enumerate(doc["Fields"])}
        self.assertIn("user_id", fmap)
        self.assertIn("balance", fmap)
        self.assertEqual(doc["Values"][0][fmap["user_id"]], 1)

    def test_05_bejson_105_uuid_integrity(self):
        records = benchmark_tool.generate_records(10)
        doc = benchmark_tool.convert_to_bejson_105(records)
        self.assertEqual(doc["Format"], "BEJSON")
        self.assertEqual(doc["Format_Version"], "105")
        self.assertEqual(doc["Fields"][0]["name"], "record_uuid")
        self.assertEqual(len(doc["Values"]), 10)
        # Check UUID length in column 0
        rec_uuid = doc["Values"][0][0]
        self.assertEqual(len(rec_uuid), 36)
        self.assertEqual(rec_uuid.count("-"), 4)

    def test_06_token_estimation(self):
        sample_json = '{"user_id":1,"username":"ada_lovelace","role":"architect"}'
        sample_bejson = '["1","ada_lovelace","architect"]'
        tok_json = benchmark_tool.estimate_tokens(sample_json, False, 3.6)
        tok_bejson = benchmark_tool.estimate_tokens(sample_bejson, True, 3.6)
        self.assertGreater(tok_json, tok_bejson)

    def test_07_execute_benchmark_metrics(self):
        result = benchmark_tool.execute_benchmark(scale=50, iterations=20, tokenizer_mode="cl100k", config=self.config)
        self.assertIn("run_id", result)
        self.assertIn("wire_footprint", result)
        self.assertIn("token_economics", result)
        self.assertIn("parser_throughput", result)
        # Wire size savings
        wf = result["wire_footprint"]
        self.assertGreater(wf["json_bytes"], 0)
        self.assertGreater(wf["bejson_105_bytes"], 0)
        self.assertGreater(wf["bytes_saved"], 0)
        # Token economics
        te = result["token_economics"]
        self.assertGreater(te["tokens_saved"], 0)
        self.assertGreater(te["token_savings_pct"], 0)
        # Parser throughput
        pt = result["parser_throughput"]
        self.assertTrue(pt["o1_field_map_enforced"])
        self.assertGreater(pt["json_ops_per_sec"], 0)
        self.assertGreater(pt["bejson_ops_per_sec"], 0)

    def test_08_cli_about_and_validate(self):
        exit_code_about = benchmark_tool.main(["--about"])
        self.assertEqual(exit_code_about, benchmark_tool.EXIT_OK)

        exit_code_val = benchmark_tool.main(["--validate"])
        self.assertEqual(exit_code_val, benchmark_tool.EXIT_OK)

    def test_09_cli_export(self):
        export_file = TOOL_DIR / "logs" / "test_export_output.json"
        exit_code = benchmark_tool.main(["--scale", "20", "--iterations", "10", "--export", str(export_file)])
        self.assertEqual(exit_code, benchmark_tool.EXIT_OK)
        self.assertTrue(export_file.exists())
        with open(export_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("run_id", data)
        export_file.unlink()


if __name__ == "__main__":
    unittest.main()
