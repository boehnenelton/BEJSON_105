"""
Library:         test_ai_invariants.py
Family:          AI_Core
Module Purpose:  Invariant tests: single default model constant is registry-verified and used everywhere; env_vault fallback roots; no duplicate AI error codes.
Version:         1.0.0
Release_Version: 301
Date:            2026-11-19
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Format_Creator:  Elton Boehnen
RELATIONAL_ID:   41636b07-1629-4d27-b54e-c190f2e6f514
"""
from __future__ import annotations

import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_AI_DIR = Path(__file__).resolve().parent.parent
if str(_AI_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_DIR))

import lib_bejson_AI_Core_models as models  # noqa: E402
import lib_bejson_AI_Core_features_common as features_common  # noqa: E402
import lib_bejson_AI_Core_client_geminirest as geminirest  # noqa: E402
import lib_bejson_AI_Core_tooling_registry as tooling_registry  # noqa: E402
import lib_bejson_AI_Core_env_vault as env_vault  # noqa: E402
import lib_bejson_AI_Core_errors as errors_module  # noqa: E402


class DefaultModelInvariantTests(unittest.TestCase):
    def test_default_is_in_active_registry(self) -> None:
        self.assertIn(features_common.DEFAULT_TEXT_MODEL_ID, models.ACTIVE_TEXT_MODELS_REGISTRY.values())
        self.assertEqual(models.DEFAULT_TEXT_MODEL, features_common.DEFAULT_TEXT_MODEL_ID)

    def test_every_default_site_uses_the_single_constant(self) -> None:
        self.assertEqual(geminirest.DEFAULT_GEMINI_MODEL, features_common.DEFAULT_TEXT_MODEL_ID)
        self.assertEqual(tooling_registry.DEFAULT_SETTINGS_INITIAL_VALUES["default_model"], features_common.DEFAULT_TEXT_MODEL_ID)
        request = features_common.build_bejson_105_ai_request("hi")
        self.assertIn(features_common.DEFAULT_TEXT_MODEL_ID, str(request))

    def test_config_template_default_matches_constant(self) -> None:
        template_text = (_AI_DIR / "config" / "ai_global_config.105a.bejson").read_text(encoding="utf-8")
        self.assertIn(features_common.DEFAULT_TEXT_MODEL_ID, template_text)


class EnvVaultFallbackRootTests(unittest.TestCase):
    def test_canonical_root_first_then_external_storage_then_termux_shared(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(os.environ, {"EXTERNAL_STORAGE": tmp}, clear=False):
                roots = env_vault._fallback_env_roots()
        self.assertEqual(roots[0], env_vault._canonical_env_root())
        self.assertIn(Path(tmp) / ".env", roots)
        self.assertEqual(roots[-1], Path.home() / "storage" / "shared" / ".env")

    def test_no_literal_absolute_storage_paths(self) -> None:
        source = (_AI_DIR / "lib_bejson_AI_Core_env_vault.py").read_text(encoding="utf-8")
        self.assertNotRegex(source, r"[\"']/storage/emulated")


class ErrorCodeRegistryTests(unittest.TestCase):
    def test_ai_codes_inside_owned_range_and_unique(self) -> None:
        pairs = [(n, v) for n, v in vars(errors_module).items() if n.startswith("ERR_AI_") and isinstance(v, int) and v != 0]  # 0 is the success sentinel
        values = [v for _, v in pairs]
        self.assertEqual(len(values), len(set(values)), "duplicate AI error code")
        for name, value in pairs:
            self.assertTrue(200 <= value <= 249, f"{name}={value} outside AI range 200-249")


if __name__ == "__main__":
    unittest.main()
