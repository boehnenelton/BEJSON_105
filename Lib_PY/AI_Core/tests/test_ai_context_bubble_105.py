"""
Library:         test_ai_context_bubble_105.py
Family:          AI_Core
Module Purpose:  Unit tests for the BEJSON 105 Context Bubble Engine, Allotments, Context/Attachment Files, and Preprocessor integration.
Version:         1.0.0
Release_Version: 300
Date:            2026-11-20
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Format_Creator:  Elton Boehnen
RELATIONAL_ID:   f4921e70-9c44-4a7d-9b30-2c714bc19e5a
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_AI_DIR = Path(__file__).resolve().parent.parent
if str(_AI_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_DIR))

from lib_bejson_AI_Core_bubble_allotments import register_builtin_allotments  # noqa: E402
from lib_bejson_AI_Core_context_bubble import (  # noqa: E402
    ContextBubblePreParser,
    ai_bubble_clear_allotments,
    ai_bubble_config_load,
    ai_bubble_config_update,
    ai_bubble_init,
    ai_bubble_prepare,
    ai_bubble_preview,
)
from lib_bejson_AI_Core_context_files import (  # noqa: E402
    ai_attachment_files_import,
    ai_attachment_files_list,
    ai_attachment_files_read,
    ai_attachment_files_toggle,
    ai_attachment_files_uncheck_all,
    ai_attachment_files_update_content,
    ai_context_files_import,
    ai_context_files_list,
    ai_context_files_toggle,
)
from lib_bejson_AI_Core_core_bridge import core_load  # noqa: E402
from lib_bejson_AI_Core_models import (  # noqa: E402
    ACTIVE_TEXT_MODELS_REGISTRY,
    Gemini_3_6_Flash,
    Gemini_3_7_Flash,
    List_Active_Gemini_Models,
    Resolve_Model_Identifier,
)
from lib_bejson_AI_Core_preprocessor import AIPreprocessor  # noqa: E402


class ContextBubble105Tests(unittest.TestCase):
    def setUp(self) -> None:
        ai_bubble_clear_allotments()
        register_builtin_allotments()

    def tearDown(self) -> None:
        ai_bubble_clear_allotments()

    def test_flash_3_6_and_3_7_models_registered(self) -> None:
        self.assertEqual(Gemini_3_6_Flash, "gemini-3.6-flash")
        self.assertEqual(Gemini_3_7_Flash, "gemini-3.7-flash")
        self.assertIn("gemini-3.6-flash", List_Active_Gemini_Models())
        self.assertIn("gemini-3.7-flash", List_Active_Gemini_Models())
        self.assertEqual(Resolve_Model_Identifier("Gemini_3_6_Flash"), "gemini-3.6-flash")
        self.assertEqual(Resolve_Model_Identifier("Gemini_3_7_Flash"), "gemini-3.7-flash")
        self.assertIn("Gemini_3_6_Flash", ACTIVE_TEXT_MODELS_REGISTRY)
        self.assertIn("Gemini_3_7_Flash", ACTIVE_TEXT_MODELS_REGISTRY)

    def test_context_bubble_105a_config_and_turn_lifecycle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ctx_dir = root / "context"
            cfg_dir = root / "config"
            paths = ai_bubble_init(ctx_dir, cfg_dir, policy_text="Always be concise.", default_interval=7)
            cfg_doc = core_load(paths["config"])
            self.assertEqual(cfg_doc["Format_Version"], "105a")
            self.assertEqual(cfg_doc["Rebuild_Interval_Turns"], 7)

            # Import a persistent context file and an active attachment file
            ctx_rec = ai_context_files_import(ctx_dir, "architecture.md", "Layered 6-tier architecture specification.")
            att_rec = ai_attachment_files_import(ctx_dir, "script.py", "def run():\n    return 42\n")
            self.assertTrue(ctx_rec["enabled"])
            self.assertTrue(att_rec["checked"])

            # Turn 1: initial build
            res1 = ai_bubble_prepare(
                ctx_dir,
                cfg_dir,
                "Please review script.py",
                extras={
                    "profile_instruction": "You are a senior Python architect.",
                    "url_context": "Example URL summary text.",
                },
            )
            self.assertTrue(res1["rebuilt"])
            self.assertEqual(res1["reason"], "first")
            self.assertEqual(res1["turn"], 1)
            self.assertEqual(res1["rebuild_interval"], 7)
            self.assertIn("[CONTEXT BUBBLE]", res1["text"])
            self.assertIn("Layered 6-tier architecture specification.", res1["text"])
            self.assertIn("NEVER reference, mention, acknowledge, source, cite, quote, or copy", res1["text"])
            self.assertIn("--- ATTACHED FILE: script.py", res1["text"])
            self.assertIn("<file_modification", res1["text"])
            self.assertIn("Example URL summary text.", res1["text"])

            # Auto-uncheck attachments after turn 1 dispatch
            unchecked = ai_attachment_files_uncheck_all(ctx_dir)
            self.assertEqual(unchecked, [att_rec["file_id"]])
            att_list = ai_attachment_files_list(ctx_dir)
            self.assertFalse(att_list[0]["checked"])

            # Re-check attachment for turn 2 so stable allotments match turn 1 and test reuse/interval
            ai_attachment_files_toggle(ctx_dir, att_rec["file_id"], checked=True)
            res2 = ai_bubble_prepare(
                ctx_dir,
                cfg_dir,
                "Turn 2 message",
                extras={
                    "profile_instruction": "You are a senior Python architect.",
                    "url_context": "Example URL summary text.",
                },
            )
            self.assertFalse(res2["rebuilt"])
            self.assertEqual(res2["reason"], "reuse")
            self.assertEqual(res2["turn"], 2)

            # Update attachment content from AI <file_modification>
            updated = ai_attachment_files_update_content(ctx_dir, "script.py", "def run():\n    return 99\n")
            self.assertIsNotNone(updated)
            self.assertEqual(ai_attachment_files_read(ctx_dir, att_rec["file_id"]), "def run():\n    return 99\n")

            # Toggle context file off and verify preview & config update
            new_state = ai_context_files_toggle(ctx_dir, ctx_rec["file_id"])
            self.assertFalse(new_state)
            self.assertFalse(ai_context_files_list(ctx_dir)[0]["enabled"])

            ai_bubble_config_update(cfg_dir, {"context": {"pct": 30.0}}, rebuild_interval=5)
            loaded_cfg = ai_bubble_config_load(cfg_dir)
            self.assertEqual(loaded_cfg["interval"], 5)

            prev = ai_bubble_preview(ctx_dir, cfg_dir, "Preview message")
            self.assertEqual(prev["reason"], "preview")

    def test_preprocessor_and_modular_pre_parser_integration(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ctx_dir = root / "context"
            cfg_dir = root / "config"
            ai_bubble_init(ctx_dir, cfg_dir, policy_text="Core Policy Rule 1.", default_interval=7)
            ai_context_files_import(ctx_dir, "notes.txt", "Secret background domain notes.")

            pre = AIPreprocessor(
                bubble_context_dir=ctx_dir,
                bubble_config_dir=cfg_dir,
                bubble_enabled=True,
                bubble_rebuild_interval=7,
            )
            processed = pre.process({
                "prompt": "Hello world",
                "profile_instruction": "Act as profile X.",
            })
            self.assertIn("[CONTEXT BUBBLE]", processed["system_instruction"])
            self.assertIn("Secret background domain notes.", processed["system_instruction"])
            self.assertIn("_context_bubble", processed)
            self.assertEqual(processed["_context_bubble"]["turn"], 1)

            # Also verify ContextBubblePreParser
            modular = ContextBubblePreParser(context_dir=ctx_dir, config_dir=cfg_dir)
            mod_out = modular.parse_pre({"prompt": "Second turn", "profile_instruction": "Act as profile X."})
            self.assertIn("[CONTEXT BUBBLE]", mod_out["system_instruction"])
            self.assertEqual(mod_out["_context_bubble"]["turn"], 2)


if __name__ == "__main__":
    unittest.main()
