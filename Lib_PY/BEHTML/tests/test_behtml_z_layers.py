"""
Library:         test_behtml_z_layers.py
Family:          BEHTML
Module Purpose:  Unit tests for BEHTML 105 Z math, layer rules, policy overrides and Core 105 compatibility.
Architecture:    BEHTML on BEJSON 105: one 105 table, one row per placed element, X0-X7 lanes, Ry=32px rows, Rz=32px layers; all field access via the Core field map.
Version:         1.0.0
Release_Version: 301
Date:            2026-11-13
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Format_Creator:  Elton Boehnen
RELATIONAL_ID:   c37e3e58-e889-4d7a-9ec1-0603d2f1aad6
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import lib_bejson_BEHTML_bootstrap  # noqa: F401,E402
from lib_bejson_BEHTML_bejson_errors import (  # noqa: E402
    E_BEHTML_Z_INVALID_DEPTH, E_BEHTML_Z_LAYER_COLLISION, E_BEHTML_PARENT_NOT_FOUND,
    W_BEHTML_Z_CHROME_SCROLLS, W_BEHTML_Z_HALF_CONTENT_MISMATCH, W_BEHTML_Z_MISSING_SCRIM,
    W_BEHTML_Z_NESTING_NOT_ABOVE, W_BEHTML_Z_SEMANTIC_MISMATCH, W_BEHTML_Z_SKIPPED_LAYER,
    W_BEHTML_Z_LAYER_CROWDED, E_BEHTML_SCHEMA_MISMATCH,
)
from lib_bejson_BEHTML_bejson_schema import behtml_schema_new_document  # noqa: E402
import lib_bejson_BEHTML_core as core  # noqa: E402
import lib_bejson_BEHTML_validator as val  # noqa: E402


def make_doc():
    return behtml_schema_new_document()


def add(doc, eid, etype, y, x, xs=1, ys=1, **kw):
    return core.behtml_core_add_element(doc, eid, etype, y_start=y, x_start=x, x_span=xs, y_span=ys, **kw)


def codes(findings):
    return {f.code for f in findings}


class ZMath(unittest.TestCase):
    def test_depths(self):
        self.assertEqual(core.behtml_core_z_depth_px(0), 0)
        self.assertEqual(core.behtml_core_z_depth_px(4), 128)
        self.assertEqual(core.behtml_core_z_depth_px(3, True), 112)
        self.assertEqual(core.behtml_core_z_index(1, True), 48)

    def test_round_trip(self):
        for depth in (0, 16, 32, 48, 64, 112, 128):
            layer, half = core.behtml_core_z_from_depth_px(depth)
            self.assertEqual(core.behtml_core_z_depth_px(layer, half), depth)

    def test_off_grid_and_bad_values(self):
        for bad in (-1, 8, 17, True, 1.5):
            with self.assertRaises(core.BEHTMLError) as ctx:
                core.behtml_core_z_from_depth_px(bad)
            self.assertEqual(ctx.exception.code, E_BEHTML_Z_INVALID_DEPTH)
        for layer, half in ((-1, False), (True, False), (1.0, False), (2, 1), (32, False)):
            with self.assertRaises(core.BEHTMLError):
                core.behtml_core_z_validate(layer, half)

    def test_css_and_scrim(self):
        self.assertEqual(core.behtml_core_z_css(2), "z-index:64;")
        self.assertIn("translateZ(64px)", core.behtml_core_z_css(2, three_d=True))
        self.assertEqual(core.behtml_core_z_scrim_slot(4), (3, True))
        with self.assertRaises(core.BEHTMLError):
            core.behtml_core_z_scrim_slot(0)

    def test_default_layers(self):
        self.assertEqual(core.behtml_core_default_layer("button"), 2)
        self.assertEqual(core.behtml_core_default_layer("dialog"), 4)
        self.assertEqual(core.behtml_core_default_layer("mystery"), 1)


class Documents(unittest.TestCase):
    def test_default_layer_applied_and_core_accepts(self):
        doc = make_doc()
        add(doc, "bg", "page", 0, 0, 8, 20)
        add(doc, "card1", "card", 2, 1, 6, 6, parent_id_fk=None)
        add(doc, "btn", "button", 3, 2, 2, 1, parent_id_fk="card1", z_layer=2)
        findings = val.behtml_validator_validate_document(doc)
        self.assertEqual(findings, [])

    def test_layers_overlap_freely_same_layer_collides(self):
        doc = make_doc()
        add(doc, "card", "card", 0, 0, 4, 4)
        add(doc, "btn", "button", 1, 1, 2, 1, z_layer=2)  # overlaps card in X/Y, different layer
        with self.assertRaises(core.BEHTMLError) as ctx:
            add(doc, "card2", "card", 1, 1, 2, 1)  # same layer, same scope, overlaps
        self.assertEqual(ctx.exception.code, E_BEHTML_Z_LAYER_COLLISION)

    def test_validator_catches_collision_when_written_bypassing_helper(self):
        doc = make_doc()
        add(doc, "a", "card", 0, 0, 4, 4)
        add(doc, "b", "card", 2, 2, 4, 4, check_collision=False)
        with self.assertRaises(core.BEHTMLError) as ctx:
            val.behtml_validator_validate_document(doc)
        self.assertEqual(ctx.exception.code, E_BEHTML_Z_LAYER_COLLISION)

    def test_different_scope_does_not_collide(self):
        doc = make_doc()
        add(doc, "p1", "card", 0, 0, 4, 4)
        add(doc, "p2", "card", 0, 4, 4, 4)
        add(doc, "c1", "button", 0, 0, 1, 1, parent_id_fk="p1", z_layer=2)
        add(doc, "c2", "button", 0, 0, 1, 1, parent_id_fk="p2", z_layer=2)
        self.assertEqual(val.behtml_validator_validate_document(doc), [])

    def test_soft_rules(self):
        doc = make_doc()
        add(doc, "card", "card", 0, 0, 8, 6)
        add(doc, "btn", "button", 0, 0, 1, 1, z_layer=0)                      # semantic: control on ground
        add(doc, "tip", "tooltip", 1, 0, 1, 1, z_layer=5, parent_id_fk="card")  # skipped layers
        add(doc, "hdr", "header", 8, 0, 8, 1, bem_modifiers="fixed,scroll")      # chrome scrolls
        add(doc, "dlg", "dialog", 9, 1, 6, 6)                                    # no scrim
        add(doc, "ghost", "card", 20, 0, 1, 1, z_half=True, z_layer=1)           # half holds a card
        add(doc, "inner", "button", 30, 0, 1, 1, z_layer=1, parent_id_fk="card")  # not above parent
        found = codes(val.behtml_validator_validate_document(doc))
        for expected in (W_BEHTML_Z_SEMANTIC_MISMATCH, W_BEHTML_Z_SKIPPED_LAYER, W_BEHTML_Z_CHROME_SCROLLS,
                         W_BEHTML_Z_MISSING_SCRIM, W_BEHTML_Z_HALF_CONTENT_MISMATCH, W_BEHTML_Z_NESTING_NOT_ABOVE):
            self.assertIn(expected, found)

    def test_scrim_satisfies_modal(self):
        doc = make_doc()
        add(doc, "scrim", "scrim", 0, 0, 8, 20, z_layer=3, z_half=True)   # 112px
        add(doc, "dlg", "dialog", 4, 2, 4, 6)                              # 128px
        self.assertEqual(val.behtml_validator_validate_document(doc), [])

    def test_crowd_limit(self):
        doc = make_doc()
        policy = core.behtml_core_build_z_policy({"crowd_limit": 2})
        for i in range(3):
            add(doc, f"c{i}", "card", i, 0, 1, 1, policy=policy)
        findings = val.behtml_validator_validate_document(doc, policy=policy)
        self.assertIn(W_BEHTML_Z_LAYER_CROWDED, codes(findings))

    def test_structure_hard_faults(self):
        doc = make_doc()
        add(doc, "a", "card", 0, 0, 1, 1)
        add(doc, "b", "button", 0, 3, 1, 1, parent_id_fk="nope")
        with self.assertRaises(core.BEHTMLError) as ctx:
            val.behtml_validator_validate_document(doc)
        self.assertEqual(ctx.exception.code, E_BEHTML_PARENT_NOT_FOUND)
        with self.assertRaises(core.BEHTMLError) as ctx:
            val.behtml_validator_validate_document({"Format_Version": "104"})
        self.assertEqual(ctx.exception.code, E_BEHTML_SCHEMA_MISMATCH)

    def test_invalid_depth_in_file_is_hard_and_skips_other_z_rules(self):
        doc = make_doc()
        add(doc, "a", "card", 0, 0, 1, 1)
        from lib_bejson_Core_bejson_core import bejson_core_get_field_map
        fm = bejson_core_get_field_map(doc)
        doc["Values"][0][fm["z_layer"]] = -3
        findings = val.behtml_validator_audit_document(doc, core_check=False)
        self.assertEqual([f.code for f in findings], [E_BEHTML_Z_INVALID_DEPTH])


class Policy(unittest.TestCase):
    def _bad_doc(self):
        doc = make_doc()
        add(doc, "btn", "button", 0, 0, 1, 1, z_layer=0)
        return doc

    def test_soft_can_become_hard_or_off(self):
        doc = self._bad_doc()
        hard = core.behtml_core_build_z_policy({"severity": {"semantic_mismatch": "hard"}})
        with self.assertRaises(core.BEHTMLError) as ctx:
            val.behtml_validator_validate_document(doc, policy=hard)
        self.assertEqual(ctx.exception.code, W_BEHTML_Z_SEMANTIC_MISMATCH)
        off = core.behtml_core_build_z_policy({"severity": {"semantic_mismatch": "off"}})
        self.assertEqual(val.behtml_validator_validate_document(doc, policy=off), [])

    def test_hard_can_become_soft(self):
        doc = make_doc()
        add(doc, "a", "card", 0, 0, 4, 4)
        add(doc, "b", "card", 2, 2, 4, 4, check_collision=False)
        soft = core.behtml_core_build_z_policy({"severity": {"layer_collision": "soft"}})
        findings = val.behtml_validator_validate_document(doc, policy=soft)
        self.assertIn(E_BEHTML_Z_LAYER_COLLISION, codes(findings))

    def test_type_rule_override_and_typos_rejected(self):
        doc = self._bad_doc()
        relaxed = core.behtml_core_build_z_policy({"type_rules": {"button": [2, 0, 5]}})
        self.assertEqual(val.behtml_validator_validate_document(doc, policy=relaxed), [])
        for bad in ({"severity": {"nonsense": "soft"}}, {"severity": {"skipped_layer": "maybe"}}, {"bogus": 1}):
            with self.assertRaises(ValueError):
                core.behtml_core_build_z_policy(bad)

    def test_report_format(self):
        text = val.behtml_validator_format_report(val.behtml_validator_validate_document(self._bad_doc()))
        self.assertIn("SOFT W_BEHTML_Z_SEMANTIC_MISMATCH", text)
        self.assertTrue(text.endswith("0 hard, 1 soft"))


class CrudAndRender(unittest.TestCase):
    def test_get_list_update_delete(self):
        doc = make_doc()
        add(doc, "card1", "card", 0, 0, 4, 4, content_ref="Card")
        add(doc, "btn1", "button", 1, 1, 2, 1, parent_id_fk="card1", z_layer=2, content_ref="Save")
        self.assertEqual(core.behtml_core_get_element(doc, "btn1")["content_ref"], "Save")
        self.assertEqual(len(core.behtml_core_list_elements(doc, parent_id_fk="card1", filter_parent=True)), 1)
        core.behtml_core_update_element(doc, "btn1", content_ref="Submit", x_span=3)
        self.assertEqual(core.behtml_core_get_element(doc, "btn1")["x_span"], 3)
        deleted = core.behtml_core_delete_element(doc, "card1", cascade=True)
        self.assertEqual(deleted, 2)
        self.assertEqual(len(doc["Values"]), 0)

    def test_content_kind_and_url_validation(self):
        from lib_bejson_BEHTML_bejson_errors import (
            E_BEHTML_INVALID_CONTENT_KIND,
            E_BEHTML_INVALID_URL,
            E_BEHTML_MISSING_FIELD_BINDING,
        )
        doc = make_doc()
        add(doc, "bad_kind", "card", 0, 0, 2, 1, content_kind="bogus")
        add(doc, "bad_url", "link", 1, 0, 2, 1, content_kind="url", content_ref="javascript:alert(1)")
        add(doc, "bad_bind", "label", 2, 0, 2, 1, content_kind="field_binding", content_ref="")
        found = codes(val.behtml_validator_audit_document(doc))
        self.assertIn(E_BEHTML_INVALID_CONTENT_KIND, found)
        self.assertIn(E_BEHTML_INVALID_URL, found)
        self.assertIn(E_BEHTML_MISSING_FIELD_BINDING, found)

    def test_render_document_html(self):
        import lib_bejson_BEHTML_render as render
        doc = make_doc()
        add(doc, "card1", "card", 0, 0, 4, 4, content_ref="Panel")
        add(doc, "btn1", "button", 1, 1, 2, 1, parent_id_fk="card1", z_layer=2, content_ref="Action")
        out = render.behtml_render_document_html(doc, title="Test Page")
        self.assertIn("<!DOCTYPE html>", out)
        self.assertIn('id="btn1"', out)
        self.assertIn("z-index:64;", out)


if __name__ == "__main__":
    unittest.main()
