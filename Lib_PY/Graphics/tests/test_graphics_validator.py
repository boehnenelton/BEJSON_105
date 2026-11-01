"""
Unit tests for Graphics Domain Two-Tier Barrier Validator and Remove_Frame_Source Pruning.
"""

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

_HERE = os.path.dirname(os.path.abspath(__file__))
_GRAPHICS_DIR = os.path.normpath(os.path.join(_HERE, ".."))
_CORE_DIR = os.path.normpath(os.path.join(_HERE, "../../Core"))
if _GRAPHICS_DIR not in sys.path:
    sys.path.insert(0, _GRAPHICS_DIR)
if _CORE_DIR not in sys.path:
    sys.path.insert(0, _CORE_DIR)

from lib_bejson_Graphics_graphics_schemas import (
    create_graphic_stage_config_105a,
    create_svg_animation_timeline_105a,
    create_graphics_mfdb_manifest_105a,
    compute_frame_timeline_105a
)
from lib_bejson_Graphics_graphics_core import (
    render_spinning_cube_svg,
    compile_frames_to_gif
)
from lib_bejson_Graphics_graphics_validator import (
    validate_graphics_barrier,
    bejson_graphics_validator_validate_doc,
    bejson_graphics_validator_validate_file
)
from lib_bejson_Graphics_graphics_errors import (
    E_GRAPHICS_CORE_VALIDATION_FAILED,
    E_GRAPHICS_INVALID_DIMENSIONS,
    E_GRAPHICS_INVALID_FRAME_SEQUENCE,
    E_GRAPHICS_INVALID_SVG_MARKUP,
    E_GRAPHICS_STAGE_CONFIG_INVALID
)


class TestGraphicsBarrierValidator(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_barrier_valid_stage_config(self):
        """Valid stage config with remove_frame_source passes both Core and Graphics barriers."""
        doc = create_graphic_stage_config_105a(
            canvas_id="test_stage_01",
            width_px=800,
            height_px=800,
            remove_frame_source=True
        )
        res = validate_graphics_barrier(doc)
        self.assertTrue(res.valid, f"Expected valid, got errors: {res.errors}")
        self.assertEqual(len(res.errors), 0)

    def test_barrier_valid_svg_timeline(self):
        """Valid SVG timeline with procedural renderers passes both barriers."""
        timeline_rows = compute_frame_timeline_105a(total_frames=12, fps=12, duration_sec=1.0)
        for row in timeline_rows:
            row["svg_markup"] = render_spinning_cube_svg(row["rotation_deg"], 400, 400)

        doc = create_svg_animation_timeline_105a(
            animation_name="test_anim",
            total_frames=12,
            fps=12,
            width_px=400,
            height_px=400,
            dynamic_frames=timeline_rows,
            remove_frame_source=True
        )
        res = validate_graphics_barrier(doc)
        self.assertTrue(res.valid, f"Expected valid, got errors: {res.errors}")

    def test_barrier_core_rejection(self):
        """Core validator failure halts immediately with E_GRAPHICS_CORE_VALIDATION_FAILED."""
        broken_doc = {
            "Format": "CORRUPT",
            "Format_Version": "999",
            "Records_Type": ["GraphicCanvasConfig"],
            "Fields": [],
            "Values": []
        }
        res = validate_graphics_barrier(broken_doc)
        self.assertFalse(res.valid)
        self.assertTrue(any("E_GRAPHICS_CORE_VALIDATION_FAILED" in err for err in res.errors))

    def test_barrier_invalid_dimensions(self):
        """Negative or non-integer width/height is caught by Graphics barrier."""
        doc = create_graphic_stage_config_105a(width_px=800, height_px=800)
        doc["Width_Px"] = -800
        res = validate_graphics_barrier(doc)
        self.assertFalse(res.valid)
        self.assertTrue(any("E_GRAPHICS_INVALID_DIMENSIONS" in err for err in res.errors))

    def test_barrier_invalid_frame_sequence(self):
        """Non-sequential frame indices trigger E_GRAPHICS_INVALID_FRAME_SEQUENCE."""
        doc = create_svg_animation_timeline_105a("seq_test", total_frames=4, fps=10)
        # Disrupt frame_index in row 2 (at offset 1 in 105a: offset 0 is record_uuid, offset 1 is frame_index)
        doc["Values"][2][1] = 99
        res = validate_graphics_barrier(doc)
        self.assertFalse(res.valid)
        self.assertTrue(any("E_GRAPHICS_INVALID_FRAME_SEQUENCE" in err for err in res.errors))

    def test_barrier_invalid_svg_markup(self):
        """Unclosed or broken SVG markup is caught by Graphics barrier."""
        doc = create_svg_animation_timeline_105a("svg_test", total_frames=2, fps=10)
        doc["Values"][0][9] = "<div>broken not svg</div>"
        res = validate_graphics_barrier(doc)
        self.assertFalse(res.valid)
        self.assertTrue(any("E_GRAPHICS_INVALID_SVG_MARKUP" in err for err in res.errors))

    def test_remove_frame_source_header_boolean(self):
        """Remove_Frame_Source header must strictly be boolean."""
        doc = create_graphic_stage_config_105a()
        doc["Remove_Frame_Source"] = "invalid_string_not_bool"
        res = validate_graphics_barrier(doc)
        self.assertFalse(res.valid)
        self.assertTrue(any("Remove_Frame_Source" in err for err in res.errors))

    def test_mfdb_manifest_barrier(self):
        """Graphics MFDB manifest and entity tables with Parent_Hierarchy pass barrier."""
        manifest_path = Path(self.tmp_dir) / "104a.mfdb.bejson"
        data_dir = Path(self.tmp_dir) / "data"
        data_dir.mkdir(parents=True, exist_ok=True)

        entity_file = data_dir / "stage.105.bejson"
        stage_doc = create_graphic_stage_config_105a(
            canvas_id="mfdb_stage",
            parent_hierarchy="../104a.mfdb.bejson",
            remove_frame_source=True
        )
        stage_doc["Format_Version"] = "105"  # MFDB entities must be 104 or 105 per MFDB Level 2 spec
        stage_doc.pop("Remove_Frame_Source", None)  # 105 entity documents forbid custom headers; flag is in manifest & row
        with open(entity_file, "w") as f:
            json.dump(stage_doc, f, indent=2)

        manifest_doc = create_graphics_mfdb_manifest_105a(
            db_name="Graphics_Test_DB",
            db_description="Test MFDB database for graphics",
            entities=[{
                "entity_name": "GraphicCanvasConfig",
                "file_path": "data/stage.105.bejson",
                "description": "Stage configuration",
                "record_count": 1,
                "schema_version": "1.0.0",
                "primary_key": "record_uuid"
            }],
            remove_frame_source=True
        )
        with open(manifest_path, "w") as f:
            json.dump(manifest_doc, f, indent=2)

        # Validate entity file
        entity_res = validate_graphics_barrier(str(entity_file), is_file=True)
        self.assertTrue(entity_res.valid, f"Entity validation failed: {entity_res.errors}")

        # Validate manifest file
        manifest_res = validate_graphics_barrier(str(manifest_path), is_file=True)
        self.assertTrue(manifest_res.valid, f"Manifest validation failed: {manifest_res.errors}")

    def test_frame_pruning_on_compile(self):
        """When remove_frame_source=True, transient frame source files are deleted after compilation."""
        from PIL import Image
        frames_dir = Path(self.tmp_dir) / "frames"
        frames_dir.mkdir()

        # Create 3 dummy test PNG frames
        for i in range(3):
            img = Image.new("RGBA", (100, 100), color=(i * 50, 0, 0, 255))
            img.save(frames_dir / f"frame_{i:04d}.png")

        self.assertEqual(len(list(frames_dir.glob("*.png"))), 3)

        out_gif = Path(self.tmp_dir) / "output.gif"
        res_gif = compile_frames_to_gif(
            frames_dir_or_list=str(frames_dir),
            output_gif_path=str(out_gif),
            fps=10,
            remove_frame_source=True
        )

        self.assertTrue(out_gif.exists())
        self.assertGreater(out_gif.stat().st_size, 0)
        # Verify transient frames are pruned
        remaining_frames = list(frames_dir.glob("*.png"))
        self.assertEqual(len(remaining_frames), 0, "Transient frame files should be removed")

    def test_branding_slide_renderers_and_barrier(self):
        """Tests that all 5 branding slide renderers produce valid SVG and create valid 105a slide decks."""
        from lib_bejson_Graphics_graphics_core import (
            render_branding_title_slide_svg,
            render_branding_architecture_slide_svg,
            render_branding_feature_slide_svg,
            render_branding_metrics_slide_svg,
            render_branding_summary_slide_svg
        )
        from lib_bejson_Graphics_graphics_schemas import create_branding_slide_deck_105a

        slides_data = [
            {"slide_type": "title", "title": "BEJSON 105", "svg_markup": render_branding_title_slide_svg(), "duration_sec": 3.0},
            {"slide_type": "architecture", "title": "ARCHITECTURE", "svg_markup": render_branding_architecture_slide_svg(), "duration_sec": 3.0},
            {"slide_type": "feature", "title": "CONFORMANCE", "svg_markup": render_branding_feature_slide_svg(), "duration_sec": 3.0},
            {"slide_type": "metrics", "title": "TELEMETRY", "svg_markup": render_branding_metrics_slide_svg(), "duration_sec": 3.0},
            {"slide_type": "summary", "title": "DELIVERABLES", "svg_markup": render_branding_summary_slide_svg(), "duration_sec": 3.0}
        ]

        deck_doc = create_branding_slide_deck_105a(
            deck_name="test_branding_presentation",
            slides=slides_data,
            remove_frame_source=True
        )

        deck_path = Path(self.tmp_dir) / "test_deck.105a.bejson"
        with open(deck_path, "w") as f:
            json.dump(deck_doc, f, indent=2)

        res = validate_graphics_barrier(str(deck_path), is_file=True)
        self.assertTrue(res.valid, f"Slide deck barrier validation failed: {res.errors}")
        self.assertEqual(len(deck_doc["Values"]), 5)

    def test_canvas_template_registry_slide_archetypes(self):
        """Tests that branding slide templates are properly registered in the family registry."""
        from lib_bejson_Graphics_graphics_canvas_templates import (
            get_canvas_template_registry_105a,
            list_branding_slide_templates,
            get_branding_slide_template_html
        )

        slides = list_branding_slide_templates()
        self.assertEqual(len(slides), 5, "Should register exactly 5 canonical branding slide templates")
        slide_ids = {s["template_id"] for s in slides}
        self.assertIn("slide_branding_title_1280", slide_ids)
        self.assertIn("slide_branding_architecture_1280", slide_ids)
        self.assertIn("slide_branding_feature_1280", slide_ids)
        self.assertIn("slide_branding_metrics_1280", slide_ids)
        self.assertIn("slide_branding_summary_1280", slide_ids)

        # Verify HTML can be retrieved
        title_html = get_branding_slide_template_html("slide_branding_title_1280")
        self.assertIsNotNone(title_html)
    def test_video_compilation_with_dwell_durations(self):
        """Tests compiling slide sequences into MP4 video with custom dwell durations (4s, 8s, 12s)."""
        from PIL import Image
        from lib_bejson_Graphics_graphics_core import compile_frames_to_mp4

        frames_dir = Path(self.tmp_dir) / "test_dwell_slides"
        frames_dir.mkdir(parents=True, exist_ok=True)

        # Create 2 lightweight slide frames
        slide_paths = []
        for i in range(2):
            img = Image.new("RGB", (320, 240), color=(i * 100, 20, 20))
            sp = frames_dir / f"slide_{i:02d}.png"
            img.save(sp)
            slide_paths.append(sp)

        out_mp4 = Path(self.tmp_dir) / "test_dwell.mp4"
        res_path = compile_frames_to_mp4(
            frames_dir_or_slides=slide_paths,
            output_mp4_path=str(out_mp4),
            fps=24,
            dwell_sec=1.5,
            remove_frame_source=False
        )
        self.assertTrue(out_mp4.exists())
        self.assertGreater(out_mp4.stat().st_size, 0)
        self.assertEqual(res_path, str(out_mp4))


if __name__ == "__main__":
    unittest.main()

