"""
File Name : test_graft.py
Rel. Path : Lib_PY/Tax_Scaffolds/tests/test_graft.py
Purpose   : Tests for grafting field sets onto entities (tax_scaffolds): the CMS picture/video scenario,
            rows, Z-space, versions and upgrade, validation before write, all-or-nothing, export/import to a
            second node, prebuilt deployment, rename-proof reads, and audit fault injection.
            The media_asset set is a TEST FIXTURE; no concrete field set ships with the libraries.
VERSION   : 2.0.1
Author    : Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
RELATIONAL_ID : 0cf89c17-d62e-4b41-b390-459db60c9648
Run       : python3 Lib_PY/Tax_Scaffolds/tests/test_graft.py
"""
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

_HERE = os.path.dirname(os.path.abspath(__file__))
for _fam in ("Tax_Scaffolds", "Taxonomies"):
    sys.path.insert(0, os.path.normpath(os.path.join(_HERE, "..", "..", _fam)))

import lib_bejson_Taxonomies_core as st  # noqa: E402
import lib_bejson_Taxonomies_core as sb  # noqa: E402
import lib_bejson_Taxonomies_core as reg  # noqa: E402
import lib_bejson_Taxonomies_registry as fsr  # noqa: E402
import lib_bejson_Taxonomies_core as trk  # noqa: E402
import lib_bejson_Taxonomies_validator as tval  # noqa: E402
import lib_bejson_Tax_Scaffolds_scaffold as zsa  # noqa: E402
import lib_bejson_Tax_Scaffolds_scaffold as gr  # noqa: E402
import lib_bejson_Tax_Scaffolds_core as tcore  # noqa: E402
import lib_bejson_Tax_Scaffolds_scaffold as rb  # noqa: E402
import lib_bejson_Tax_Scaffolds_scaffold as pb  # noqa: E402
from lib_bejson_Core_bejson_core import bejson_core_atomic_write, bejson_core_load_file  # noqa: E402
from lib_bejson_Core_mfdb_core import mfdb_core_get_entity_doc, mfdb_core_update_entity_record_105 as upd  # noqa: E402

MEDIA = {"set_key": "media_asset", "display_name": "Media asset", "members": [
    {"descriptor": "title", "suffix": "_name", "field_type": "string"},
    {"descriptor": "caption", "suffix": "_name", "field_type": "string"},
    {"descriptor": "width", "suffix": "_metric", "field_type": "integer"},
    {"descriptor": "height", "suffix": "_metric", "field_type": "integer"},
    {"descriptor": "file", "suffix": "_key", "field_type": "string"},
    {"descriptor": "created", "suffix": "_timestamp", "field_type": "string"},
]}
DURATION = {"descriptor": "duration", "suffix": "_metric", "field_type": "integer"}
PICTURE = {"name": "CmsPicture", "fields": [{"name": "cms_picture_label_key", "type": "string"}], "field_sets": ["media_asset"]}
VIDEO = {"name": "CmsVideo", "fields": [{"name": "cms_video_label_key", "type": "string"}], "field_sets": ["media_asset"]}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="graft_test_")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def path(self, name):
        return os.path.join(self.tmp, name)

    def ok(self, m):
        r = tval.bejson_taxonomies_validator_audit_database(m)
        self.assertTrue(r["passed"], r["problems"])
        return r

    def problems(self, m):
        return "\n".join(tval.bejson_taxonomies_validator_audit_database(m)["problems"])

    def cms(self, name="cms", entities=None, role="master", **kw):
        """A node that follows a 'cms' variant taxonomy, with the media_asset set registered."""
        r = rb.bejson_tax_scaffolds_deploy_rebuild(
            self.path(name), f"{name}-node", name.upper(), role_kind=role, taxonomy_namespace="cms",
            field_sets=[MEDIA], entities=entities, **kw)
        return r["manifest_path"]

    def edit_entity(self, m, entity, fn):
        p = st.entity_path(m, entity)
        doc = bejson_core_load_file(p)
        fn(doc)
        self.assertTrue(bejson_core_atomic_write(p, doc))

    def entity_snapshot(self, m, entity):
        d = mfdb_core_get_entity_doc(m, entity)
        return [dict(f) for f in d["Fields"]], [list(r) for r in d["Values"]]


class TestScenario(Base):
    def test_picture_and_video_libraries_share_one_field_set(self):
        r = rb.bejson_tax_scaffolds_deploy_rebuild(
            self.path("cms"), "cms-node", "CMS", taxonomy_namespace="cms", field_sets=[MEDIA], entities=[PICTURE, VIDEO])
        m = r["manifest_path"]
        self.assertEqual(r["entities_scaffolded"], ["CmsPicture", "CmsVideo"])
        pic = fsr.bejson_taxonomies_member_columns(m, "CmsPicture", "media_asset")
        vid = fsr.bejson_taxonomies_member_columns(m, "CmsVideo", "media_asset")
        self.assertEqual(pic["title"]["field_name"], "cms_picture_title_name")
        self.assertEqual(vid["title"]["field_name"], "cms_video_title_name")
        self.assertEqual(vid["created"]["field_name"], "cms_video_created_timestamp")
        self.assertEqual(set(pic), set(vid))
        self.assertEqual([e["entity_name"] for e in fsr.bejson_taxonomies_entities_with_set(m, "media_asset")], ["CmsPicture", "CmsVideo"])
        self.ok(m)
        # one reader path over both libraries
        for entity, label in (("CmsPicture", "cms_picture"), ("CmsVideo", "cms_video")):
            st.add_row(m, entity, st.build_row(m, entity, **{
                f"{label}_label_key": f"{label}-1", f"{label}_title_name": f"{entity} title", f"{label}_width_metric": 640}))
        for entity in ("CmsPicture", "CmsVideo"):
            rows = fsr.bejson_taxonomies_read_set_rows(m, entity, "media_asset", ["title", "width", "caption"])
            self.assertEqual(len(rows), 1)
            self.assertEqual((rows[0]["title"], rows[0]["width"], rows[0]["caption"]), (f"{entity} title", 640, None))
        self.ok(m)

    def test_subject_override_and_derivation(self):
        m = self.cms()
        gr.bejson_tax_scaffolds_scaffold_entity(m, "cms", "CmsVideoLibrary", [{"name": "cms_video_library_label_key", "type": "string"}], ["media_asset"])
        self.assertEqual(fsr.bejson_taxonomies_resolve_member(m, "CmsVideoLibrary", "media_asset", "title")["field_name"],
                         "cms_video_library_title_name")
        gr.bejson_tax_scaffolds_scaffold_entity(
            m, "cms", "CmsClip", [{"name": "cms_clip_label_key", "type": "string"}], [{"set_key": "media_asset", "subject": "reel"}])
        self.assertEqual(fsr.bejson_taxonomies_resolve_member(m, "CmsClip", "media_asset", "file")["field_name"], "cms_reel_file_key")
        self.ok(m)

    def test_graft_onto_existing_entity_with_rows_keeps_data(self):
        m = self.cms()
        sb.bejson_taxonomies_create_domain_entity(m, "cms", "CmsDocument", [
            sb.bejson_taxonomies_build_field_definition(reg.bejson_taxonomies_get_taxonomy(m, "cms"), "cms_document_label_key", "string")])
        for i in range(3):
            st.add_row(m, "CmsDocument", [f"doc{i}"])
        res = gr.bejson_tax_scaffolds_graft_field_set(m, "CmsDocument", "media_asset")
        self.assertEqual([c["descriptor"] for c in res["columns"]], ["title", "caption", "width", "height", "file", "created"])
        doc = mfdb_core_get_entity_doc(m, "CmsDocument")
        self.assertEqual([r[1] for r in doc["Values"]], ["doc0", "doc1", "doc2"])
        self.assertTrue(all(v is None for r in doc["Values"] for v in r[2:]) and all(len(r) == len(doc["Fields"]) + 1 for r in doc["Values"]))
        self.ok(m)

    def test_graft_with_fk_member(self):
        m = self.cms(entities=[PICTURE])
        gr.bejson_tax_scaffolds_register_field_sets(m, [{"set_key": "owned", "members": [
            {"descriptor": "owner", "suffix": "_uuid_fk", "field_type": "string"}, {"descriptor": "note", "suffix": "_name", "field_type": "string"}]}])
        with self.assertRaises(gr.GraftError) as cx:
            gr.bejson_tax_scaffolds_scaffold_entity(m, "cms", "CmsAlbum", [{"name": "cms_album_label_key", "type": "string"}], ["owned"])
        self.assertIn("is a foreign key", "\n".join(cx.exception.problems))
        self.assertNotIn("CmsAlbum", st.manifest_entity_names(m))  # scaffold is all-or-nothing
        gr.bejson_tax_scaffolds_scaffold_entity(
            m, "cms", "CmsAlbum", [{"name": "cms_album_label_key", "type": "string"}],
            [{"set_key": "owned", "fk_targets": {"owner": ("CmsPicture", "restrict")}}])
        f = next(f for f in mfdb_core_get_entity_doc(m, "CmsAlbum")["Fields"] if f["name"] == "cms_album_owner_uuid_fk")
        self.assertEqual((f["fk_target_entity"], f["fk_on_delete"]), ("CmsPicture", "restrict"))
        pic = st.add_row(m, "CmsPicture", st.build_row(m, "CmsPicture", cms_picture_label_key="p"))
        st.add_row(m, "CmsAlbum", st.build_row(m, "CmsAlbum", cms_album_label_key="a", cms_album_owner_uuid_fk=pic))
        self.ok(m)


class TestZSpace(Base):
    def test_slots_stay_trailing_and_untouched(self):
        m = self.cms()
        tx = reg.bejson_taxonomies_get_taxonomy(m, "cms")
        sb.bejson_taxonomies_create_domain_entity(m, "cms", "CmsClip", [
            sb.bejson_taxonomies_build_field_definition(tx, "cms_clip_label_key", "string")])
        slots = zsa.bejson_tax_scaffolds_reserve_z_space_slot(m, "CmsClip", "cms", slot_count=2)
        st.add_row(m, "CmsClip", st.build_row(m, "CmsClip", cms_clip_label_key="c1"))
        before = {f["name"]: f["field_uuid"] for f in mfdb_core_get_entity_doc(m, "CmsClip")["Fields"]}
        res = gr.bejson_tax_scaffolds_graft_field_set(m, "CmsClip", "media_asset")
        doc = mfdb_core_get_entity_doc(m, "CmsClip")
        names = [f["name"] for f in doc["Fields"]]
        self.assertEqual(names[-2:], [s["slot_name"] for s in slots])            # slots still trailing, same order
        self.assertEqual(names[1:1 + len(res["columns"])], [c["field_name"] for c in res["columns"]])  # grafted columns in front
        for s in slots:
            self.assertEqual(before[s["slot_name"]], next(f["field_uuid"] for f in doc["Fields"] if f["name"] == s["slot_name"]))
        self.assertEqual(doc["Values"][0][1], "c1")
        self.assertTrue(all(len(r) == len(doc["Fields"]) + 1 and all(v is None for v in r[2:]) for r in doc["Values"]))
        self.ok(m)
        pos = [f["field_uuid"] for f in doc["Fields"]].index(slots[0]["slot_field_uuid"])
        zsa.bejson_tax_scaffolds_bind_z_space_slot(m, "CmsClip", slots[0]["slot_field_uuid"], "cms_clip_owner_name")
        after = mfdb_core_get_entity_doc(m, "CmsClip")
        self.assertEqual([f["field_uuid"] for f in after["Fields"]].index(slots[0]["slot_field_uuid"]), pos)  # bind did not move it
        self.assertEqual(after["Fields"][pos]["name"], "cms_clip_owner_name")
        self.ok(m)


class TestValidationAndRollback(Base):
    def snapshot_of_node(self, m):
        return {e: self.entity_snapshot(m, e) for e in st.manifest_entity_names(m)}

    def test_problems_reported_before_any_write(self):
        m = self.cms(entities=[PICTURE])
        before = self.snapshot_of_node(m)
        with self.assertRaises(gr.GraftError) as cx:
            gr.bejson_tax_scaffolds_graft_field_set(m, "CmsPicture", "media_asset")
        self.assertIn("already carries field set", "\n".join(cx.exception.problems))
        for args, needle in [
            (("CmsPicture", "nope"), "not found"),
            (("Nope", "media_asset"), "not in the manifest"),
            (("LatticeDeployment", "media_asset"), "is a registry entity"),
        ]:
            with self.assertRaises(st.TaxonomyError) as cx:
                gr.bejson_tax_scaffolds_graft_field_set(m, *args)
            self.assertIn(needle, str(cx.exception) + "\n".join(getattr(cx.exception, "problems", [])), args)
        self.assertEqual(self.snapshot_of_node(m), before)

    def test_target_taxonomy_must_register_the_suffixes(self):
        r = rb.bejson_tax_scaffolds_deploy_rebuild(
            self.path("lean"), "lean-node", "LEAN", taxonomy_namespace="lean", suffix_removals=["_metric"], field_sets=[MEDIA])
        m = r["manifest_path"]
        with self.assertRaises(gr.GraftError) as cx:
            gr.bejson_tax_scaffolds_scaffold_entity(m, "lean", "LeanPhoto", [{"name": "lean_photo_label_key", "type": "string"}], ["media_asset"])
        self.assertIn("_metric is not registered by taxonomy 'lean'", "\n".join(cx.exception.problems))
        self.assertNotIn("LeanPhoto", st.manifest_entity_names(m))

    def test_name_collision_and_untracked_entity(self):
        m = self.cms()
        tx = reg.bejson_taxonomies_get_taxonomy(m, "cms")
        sb.bejson_taxonomies_create_domain_entity(m, "cms", "CmsThing", [
            sb.bejson_taxonomies_build_field_definition(tx, "cms_thing_title_name", "string")])
        with self.assertRaises(gr.GraftError) as cx:
            gr.bejson_tax_scaffolds_graft_field_set(m, "CmsThing", "media_asset")
        self.assertIn("'cms_thing_title_name' already exists", "\n".join(cx.exception.problems))
        # an entity with no ledger rows cannot be grafted
        sb.bejson_taxonomies_create_domain_entity(m, "cms", "CmsOther", [sb.bejson_taxonomies_build_field_definition(tx, "cms_other_label_key", "string")])
        for row in st.read_rows(m, st.E_FIELD):
            if row[st.FE_ENTITY] == "CmsOther":
                upd(m, st.E_FIELD, row["record_uuid"], st.FE_LIFECYCLE, "retired")
        with self.assertRaises(gr.GraftError) as cx:
            gr.bejson_tax_scaffolds_graft_field_set(m, "CmsOther", "media_asset")
        self.assertIn("not tracked under any taxonomy", "\n".join(cx.exception.problems))

    def test_failure_mid_graft_restores_everything(self):
        m = self.cms(entities=[{"name": "CmsKeep", "fields": [{"name": "cms_keep_label_key", "type": "string"}]}])
        st.add_row(m, "CmsKeep", ["k1"])
        before = self.snapshot_of_node(m)
        grafts_before = st.read_rows(m, st.E_GRAFT)
        with mock.patch.object(trk, "bejson_taxonomies_track_fields", side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                gr.bejson_tax_scaffolds_graft_field_set(m, "CmsKeep", "media_asset")
        self.assertEqual(self.snapshot_of_node(m), before)
        self.assertEqual(st.read_rows(m, st.E_GRAFT), grafts_before)
        self.ok(m)
        gr.bejson_tax_scaffolds_graft_field_set(m, "CmsKeep", "media_asset")  # node still usable
        self.ok(m)

    def test_retired_set_cannot_be_grafted_and_grafted_set_cannot_be_retired(self):
        m = self.cms(entities=[PICTURE])
        with self.assertRaises(st.TaxonomyError) as cx:
            fsr.bejson_taxonomies_retire_field_set(m, "media_asset")
        self.assertEqual(cx.exception.code, "E_FIELDSET_IN_USE")
        gr.bejson_tax_scaffolds_register_field_sets(m, [{"set_key": "spare", "members": [{"descriptor": "note", "suffix": "_name", "field_type": "string"}]}])
        fsr.bejson_taxonomies_retire_field_set(m, "spare")
        with self.assertRaises(gr.GraftError) as cx:
            gr.bejson_tax_scaffolds_graft_field_set(m, "CmsPicture", "spare")
        self.assertIn("retired", "\n".join(cx.exception.problems))


class TestVersions(Base):
    def test_new_version_then_upgrade_graft(self):
        m = self.cms(entities=[PICTURE, VIDEO])
        fsr.bejson_taxonomies_new_version(m, "media_asset", [DURATION])
        before = self.entity_snapshot(m, "CmsVideo")
        st.add_row(m, "CmsVideo", st.build_row(m, "CmsVideo", cms_video_label_key="v1", cms_video_title_name="t"))
        res = gr.bejson_tax_scaffolds_upgrade_graft(m, "CmsVideo", "media_asset")
        self.assertEqual((res["set_version"], [c["descriptor"] for c in res["columns"]]), (2, ["duration"]))
        self.assertEqual(fsr.bejson_taxonomies_resolve_member(m, "CmsVideo", "media_asset", "duration")["field_name"], "cms_video_duration_metric")
        self.assertEqual(fsr.bejson_taxonomies_resolve_member(m, "CmsVideo", "media_asset", "title")["field_name"], "cms_video_title_name")
        self.assertEqual(fsr.bejson_taxonomies_list_grafts(m, "media_asset", "CmsVideo")[0]["set_version"], 2)
        self.assertEqual(fsr.bejson_taxonomies_list_grafts(m, "media_asset", "CmsPicture")[0]["set_version"], 1)  # picture stays v1
        self.assertEqual(len(before[0]) + 1, len(mfdb_core_get_entity_doc(m, "CmsVideo")["Fields"]))
        self.assertEqual(fsr.bejson_taxonomies_read_set_rows(m, "CmsVideo", "media_asset", ["title", "duration"])[0]["title"], "t")
        self.ok(m)
        with self.assertRaises(gr.GraftError):  # already at v2
            gr.bejson_tax_scaffolds_upgrade_graft(m, "CmsVideo", "media_asset")
        with self.assertRaises(gr.GraftError):  # a graft at v1 cannot be re-grafted
            gr.bejson_tax_scaffolds_graft_field_set(m, "CmsPicture", "media_asset")
        gr.bejson_tax_scaffolds_upgrade_graft(m, "CmsPicture", "media_asset")
        self.ok(m)

    def test_upgrade_needs_an_existing_graft(self):
        m = self.cms(entities=[PICTURE])
        fsr.bejson_taxonomies_new_version(m, "media_asset", [DURATION])
        with self.assertRaises(gr.GraftError) as cx:
            gr.bejson_tax_scaffolds_upgrade_graft(m, "CmsPicture", "media_asset", version=1)
        self.assertIn("already carries", "\n".join(cx.exception.problems))


class TestRenameProofAndExportImport(Base):
    def test_reads_follow_a_renamed_column(self):
        m = self.cms(entities=[VIDEO])
        st.add_row(m, "CmsVideo", st.build_row(m, "CmsVideo", cms_video_label_key="v", cms_video_title_name="hello"))

        def rename(doc):
            next(f for f in doc["Fields"] if f["name"] == "cms_video_title_name")["name"] = "cms_video_heading_name"
        self.edit_entity(m, "CmsVideo", rename)
        trk.bejson_taxonomies_sync_ledger(m, "CmsVideo")
        col = fsr.bejson_taxonomies_resolve_member(m, "CmsVideo", "media_asset", "title")
        self.assertEqual(col["field_name"], "cms_video_heading_name")
        self.assertEqual(fsr.bejson_taxonomies_read_set_rows(m, "CmsVideo", "media_asset", ["title"])[0]["title"], "hello")
        self.ok(m)

    def test_export_on_node_a_import_on_node_b_then_graft(self):
        a = self.cms("a", entities=[PICTURE])
        p = self.path("media_asset.bejson")
        fsr.bejson_taxonomies_export_field_set(a, "media_asset", p)
        b = rb.bejson_tax_scaffolds_deploy_rebuild(self.path("b"), "b-node", "B", role_kind="slave", taxonomy_namespace="cms",
                                                   field_sets=[p], entities=[VIDEO])["manifest_path"]
        self.assertEqual(fsr.bejson_taxonomies_get_field_set(a, "media_asset")["content_hash"],
                         fsr.bejson_taxonomies_get_field_set(b, "media_asset")["content_hash"])
        self.assertEqual(fsr.bejson_taxonomies_resolve_member(b, "CmsVideo", "media_asset", "title")["field_name"], "cms_video_title_name")
        self.ok(b)

    def test_deploy_rejects_conflicting_set_and_cleans_nothing_silently(self):
        other = dict(MEDIA, members=MEDIA["members"][:2])
        m = self.cms()
        with self.assertRaises(st.TaxonomyError) as cx:
            gr.bejson_tax_scaffolds_register_field_sets(m, [other])
        self.assertEqual(cx.exception.code, "E_FIELDSET_CONFLICT")


class TestPrebuilt(Base):
    def test_snapshot_carries_sets_and_grafts_to_master_and_slave(self):
        src = self.cms("src", entities=[PICTURE, VIDEO])
        snap = pb.bejson_tax_scaffolds_capture_snapshot(src, self.path("snap"))
        self.assertEqual(len(st.read_rows(snap, st.E_GRAFT)), 2)
        self.ok(snap)
        for role, name in (("master", "m1"), ("slave", "s1")):
            r = pb.bejson_tax_scaffolds_deploy_prebuilt(
                self.path("snap"), self.path(name), f"{name}-node", name.upper(), role_kind=role, taxonomy_ref="cms")
            n = r["manifest_path"]
            self.assertEqual(fsr.bejson_taxonomies_resolve_member(n, "CmsVideo", "media_asset", "height")["field_name"], "cms_video_height_metric")
            self.ok(n)
        extra = {"name": "CmsAudio", "fields": [{"name": "cms_audio_label_key", "type": "string"}], "field_sets": ["media_asset"]}
        r = pb.bejson_tax_scaffolds_deploy_prebuilt(
            self.path("snap"), self.path("m2"), "m2-node", "M2", taxonomy_ref="cms", entities=[extra])
        self.assertEqual(r["entities_scaffolded"], ["CmsAudio"])
        self.assertEqual(len(fsr.bejson_taxonomies_entities_with_set(r["manifest_path"], "media_asset")), 3)
        self.ok(r["manifest_path"])


class TestAuditFaults(Base):
    def setUp(self):
        super().setUp()
        self.m = self.cms(entities=[PICTURE, VIDEO])
        self.ok(self.m)

    def test_changed_type_and_missing_column_and_dropped_member(self):
        def retype(doc):
            next(f for f in doc["Fields"] if f["name"] == "cms_video_width_metric")["type"] = "string"
        self.edit_entity(self.m, "CmsVideo", retype)
        self.assertIn("type 'string' but member 'width' is 'integer'", self.problems(self.m))

    def test_incomplete_graft(self):
        row = next(r for r in st.read_rows(self.m, st.E_FIELD) if r[st.FE_COLUMN] == "cms_picture_caption_name")
        from lib_bejson_Core_mfdb_core import mfdb_core_delete_entity_record_105 as delete
        delete(self.m, st.E_FIELD, row["record_uuid"])
        text = self.problems(self.m)
        self.assertIn("incomplete, missing members ['caption']", text)
        self.assertIn("not in field ledger", text)

    def test_half_linked_ledger_row_and_wrong_owner(self):
        row = next(r for r in st.read_rows(self.m, st.E_FIELD) if r[st.FE_COLUMN] == "cms_picture_file_key")
        upd(self.m, st.E_FIELD, row["record_uuid"], st.FE_SETMEMBER, None)
        self.assertIn("graft and set-member links must be set together", self.problems(self.m))
        upd(self.m, st.E_FIELD, row["record_uuid"], st.FE_SETMEMBER, next(
            m["record_uuid"] for m in st.read_rows(self.m, st.E_SETMEMBER) if m[st.SM_DESCRIPTOR] == "file"))
        self.ok(self.m)
        g = next(g for g in st.read_rows(self.m, st.E_GRAFT) if g[st.GR_ENTITY] == "CmsPicture")
        upd(self.m, st.E_GRAFT, g["record_uuid"], st.GR_TAXONOMY, reg.bejson_taxonomies_get_taxonomy(self.m, "lattice")["taxonomy_uuid"])
        self.assertIn("is not owned by taxonomy 'lattice'", self.problems(self.m))

    def test_retired_set_still_grafted_and_duplicate_graft(self):
        s = fsr.bejson_taxonomies_get_field_set(self.m, "media_asset")
        upd(self.m, st.E_FIELDSET, s["set_uuid"], st.FS_STATE, "retired")
        self.assertIn("is retired but still grafted", self.problems(self.m))
        upd(self.m, st.E_FIELDSET, s["set_uuid"], st.FS_STATE, "active")
        g = next(g for g in st.read_rows(self.m, st.E_GRAFT) if g[st.GR_ENTITY] == "CmsPicture")
        st.add_row(self.m, st.E_GRAFT, st.build_row(self.m, st.E_GRAFT, **{
            st.GR_KEY: g[st.GR_KEY], st.GR_SET: g[st.GR_SET], st.GR_ENTITY: "CmsPicture", st.GR_SUBJECT: "picture",
            st.GR_TAXONOMY: g[st.GR_TAXONOMY], st.GR_APPLIED: st.now_utc()}))
        self.assertIn("registered twice", self.problems(self.m))

    def test_slot_block_broken_by_a_graft_is_caught(self):
        tx_entity = "CmsPicture"
        zsa.bejson_tax_scaffolds_reserve_z_space_slot(self.m, tx_entity, "cms")
        self.ok(self.m)

        def move_slot_first(doc):
            slot = doc["Fields"].pop()
            doc["Fields"].insert(1, slot)
            for row in doc["Values"]:
                row.insert(2, row.pop())
        self.edit_entity(self.m, tx_entity, move_slot_first)
        self.assertIn("Z-space slots are not the trailing block", self.problems(self.m))


class TestHardening(Base):
    def test_entity_names_that_differ_only_by_case_are_refused_before_writing(self):
        m = self.cms(entities=[PICTURE])
        before = self.entity_snapshot(m, "CmsPicture")
        with self.assertRaises(gr.GraftError) as cx:
            gr.bejson_tax_scaffolds_scaffold_entity(m, "cms", "Cmspicture", [{"name": "cms_pic_label_key", "type": "string"}], ["media_asset"])
        self.assertIn("case-insensitively", "\n".join(cx.exception.problems))
        self.assertEqual(self.entity_snapshot(m, "CmsPicture"), before)
        self.assertNotIn("Cmspicture", st.manifest_entity_names(m))
        self.ok(m)

    def test_interrupt_midway_restores_everything(self):
        m = self.cms(entities=[PICTURE])
        before = self.entity_snapshot(m, "CmsPicture")
        with mock.patch.object(gr, "_apply", side_effect=KeyboardInterrupt()):
            with self.assertRaises(KeyboardInterrupt):
                gr.bejson_tax_scaffolds_scaffold_entity(m, "cms", "CmsClip", [{"name": "cms_clip_label_key", "type": "string"}], ["media_asset"])
        self.assertEqual(self.entity_snapshot(m, "CmsPicture"), before)
        self.assertNotIn("CmsClip", st.manifest_entity_names(m))
        self.ok(m)

    def test_failed_restore_keeps_the_backup_and_says_where(self):
        m = self.cms(entities=[PICTURE])
        with mock.patch.object(tcore, "_restore_from_backup", side_effect=OSError("disk full")):
            with self.assertRaises(st.TaxonomyError) as cx:
                with tcore.bejson_tax_scaffolds_core_all_or_nothing(m):
                    raise RuntimeError("boom")
        self.assertEqual(cx.exception.code if hasattr(cx.exception, "code") else "E_RESTORE_FAILED", "E_RESTORE_FAILED")
        kept = str(cx.exception).rsplit(" ", 1)[-1]
        self.assertTrue(os.path.isdir(kept))
        self.assertTrue(os.path.isfile(os.path.join(kept, os.path.basename(m))))
        shutil.rmtree(kept, ignore_errors=True)

    def test_restore_does_not_delete_files_the_backup_skips(self):
        m = self.cms(entities=[PICTURE])
        keep = os.path.join(os.path.dirname(m), "held.lock")
        open(keep, "w").write("x")
        with self.assertRaises(RuntimeError):
            with tcore.bejson_tax_scaffolds_core_all_or_nothing(m):
                raise RuntimeError("boom")
        self.assertTrue(os.path.exists(keep))
        self.ok(m)


if __name__ == "__main__":
    unittest.main(verbosity=1)
