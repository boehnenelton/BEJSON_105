"""
Unit tests for libraries_105 Gaming_Editors family:
- Error code registry (520-539)
- Schemas and O(1) field map caching
- Two-tier barrier validator (Core + Gaming_Editors)
- Stage template resolution
"""

import os
import sys
import unittest
from pathlib import Path

_HERE = os.path.dirname(os.path.abspath(__file__))
_FAM_DIR = os.path.normpath(os.path.join(_HERE, ".."))
_CORE_DIR = os.path.normpath(os.path.join(_HERE, "../../Core"))
if _FAM_DIR not in sys.path:
    sys.path.insert(0, _FAM_DIR)
if _CORE_DIR not in sys.path:
    sys.path.insert(0, _CORE_DIR)

from lib_bejson_Gaming_Editors_errors import (
    E_GAMING_EDITORS_CORE_VALIDATION_FAILED,
    E_GAMING_EDITORS_INVALID_SPRITE_GRID,
    E_GAMING_EDITORS_INVALID_TILEMAP_PALETTE,
    ERROR_NAMES
)
from lib_bejson_Gaming_Editors_schemas import (
    create_sprite_studio_config_105a,
    create_tilemap_palette_config_105a,
    create_hud_stage_config_105a,
    build_field_map_105
)
from lib_bejson_Gaming_Editors_validator import (
    validate_gaming_editors_barrier,
    bejson_gaming_editors_validator_validate_doc
)
from lib_bejson_Gaming_Editors_templates import (
    list_gaming_editor_templates,
    get_gaming_editor_template_html
)


class TestGamingEditorsFamily105(unittest.TestCase):

    def test_error_code_range(self):
        """Errors must be in range 520-539."""
        for code, name in ERROR_NAMES.items():
            self.assertTrue(520 <= code <= 539, f"Code {code} outside range 520-539")
            self.assertTrue(name.startswith("E_GAMING_EDITORS_"))

    def test_sprite_studio_config_barrier(self):
        """Valid sprite studio config must pass both Core and Gaming_Editors barriers."""
        doc = create_sprite_studio_config_105a(
            editor_id="test_sprite_studio",
            canvas_size_px=512,
            cell_size_px=32
        )
        res = validate_gaming_editors_barrier(doc)
        self.assertTrue(res.valid, f"Expected valid, got errors: {res.errors}")
        self.assertEqual(doc["Format_Version"], "105a")
        fmap = build_field_map_105(doc)
        self.assertEqual(fmap["record_uuid"], 0)
        self.assertEqual(fmap["editor_id"], 1)

    def test_tilemap_palette_config_barrier(self):
        """Valid tilemap palette config must pass both barriers."""
        doc = create_tilemap_palette_config_105a(
            palette_id="test_tilemap_palette",
            canvas_size_px=512,
            tile_size_px=32
        )
        res = validate_gaming_editors_barrier(doc)
        self.assertTrue(res.valid, f"Expected valid, got errors: {res.errors}")

    def test_hud_stage_config_barrier(self):
        """Valid HUD stage config must pass both barriers."""
        doc = create_hud_stage_config_105a(
            hud_id="test_hud_stage",
            width_px=640,
            height_px=480
        )
        res = validate_gaming_editors_barrier(doc)
        self.assertTrue(res.valid, f"Expected valid, got errors: {res.errors}")

    def test_invalid_cell_size_rejection(self):
        """Invalid cell size (e.g. 15px) must trigger E_GAMING_EDITORS_INVALID_SPRITE_GRID."""
        doc = create_sprite_studio_config_105a(
            editor_id="bad_grid",
            canvas_size_px=512,
            cell_size_px=15
        )
        res = validate_gaming_editors_barrier(doc)
        self.assertFalse(res.valid)
        self.assertTrue(any("E_GAMING_EDITORS_INVALID_SPRITE_GRID" in err for err in res.errors))

    def test_template_catalog_resolution(self):
        """All 4 editor templates must be registered and resolve HTML from disk."""
        tpls = list_gaming_editor_templates()
        self.assertEqual(len(tpls), 4)
        for t in tpls:
            html = get_gaming_editor_template_html(t["template_id"])
            self.assertIsNotNone(html, f"Failed to resolve {t['template_id']}")
            self.assertIn("capture-stage", html)

    def test_projectile_impact_registry_barrier(self):
        """Valid projectile impact dynamics registry must pass both barriers."""
        from lib_bejson_Gaming_Editors_schemas import create_projectile_impact_registry_105a
        doc = create_projectile_impact_registry_105a()
        res = validate_gaming_editors_barrier(doc)
        self.assertTrue(res.valid, f"Expected valid, got errors: {res.errors}")
        self.assertEqual(doc["Format_Version"], "105a")
        self.assertEqual(doc["Records_Type"], ["ProjectileImpactDynamics"])
        self.assertEqual(len(doc["Values"]), 4)


if __name__ == "__main__":
    unittest.main()

