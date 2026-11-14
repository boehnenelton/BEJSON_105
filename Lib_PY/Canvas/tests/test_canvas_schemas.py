"""
Test Suite:      test_canvas_schemas.py
Family:          Canvas
Purpose:         Unit tests for BEJSON 105a Canvas schema generation and frame sequences
Version:         1.0.0
Release_Version: 300
Date:            2026-11-14
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
RELATIONAL_ID:   c8e1f2a3-4b5c-46d7-8e9f-0a1b2c3d4e5f
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

_CANVAS_FAMILY_DIR = Path(__file__).resolve().parent.parent
if str(_CANVAS_FAMILY_DIR) not in sys.path:
    sys.path.insert(0, str(_CANVAS_FAMILY_DIR))

from lib_bejson_Canvas_canvas_schemas import (  # noqa: E402
    compute_frame_seek_points,
    create_canvas_config_105a,
    create_frame_sequence_105a,
    validate_canvas_config,
)


class TestCanvasSchemas(unittest.TestCase):
    def test_canvas_config_105a_creation_and_validation(self) -> None:
        canvas_config_document = create_canvas_config_105a(
            canvas_id="canvas_hero_01",
            template_name="template_split_stage.html",
            width_px=1920,
            height_px=1080,
            fps=30,
            duration_sec=3.0,
            total_frames=90,
        )
        validation_success_flag, validation_error_messages_list = validate_canvas_config(canvas_config_document)
        self.assertTrue(validation_success_flag)
        self.assertEqual(len(validation_error_messages_list), 0)
        self.assertEqual(canvas_config_document["Format"], "BEJSON")
        self.assertEqual(canvas_config_document["Format_Version"], "105a")

    def test_frame_sequence_generation(self) -> None:
        frame_sequence_document = create_frame_sequence_105a(
            duration_sec=2.0,
            fps=12,
            total_frames=24,
        )
        self.assertEqual(frame_sequence_document["Format"], "BEJSON")
        self.assertEqual(len(frame_sequence_document["Values"]), 24)

    def test_compute_frame_seek_points(self) -> None:
        calculated_seek_points_list = compute_frame_seek_points(duration_sec=1.0, fps=10, frames_count=10)
        self.assertEqual(len(calculated_seek_points_list), 10)
        frame_idx, seek_ratio, timestamp = calculated_seek_points_list[0]
        self.assertEqual(frame_idx, 0)
        self.assertEqual(seek_ratio, 0.0)
        self.assertEqual(timestamp, 0.0)


if __name__ == "__main__":
    unittest.main()
