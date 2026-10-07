"""
Library:        test_mfdb_ref_integrity_suite.py
Family:         Core (tests)
Description:    Exhaustive unittest suite for Phase 6 (105-series MFDB
                 Referential Integrity): the Ref_Integrity switch, FK
                 write-time exists-checks, delete-time restrict/cascade/null
                 resolution, cascade cycle detection, entity-droppable
                 check, the standalone audit function, and -- the hard
                 requirement -- proof that a 104-series entity coexisting in
                 the same manifest is completely untouched regardless of
                 the switch state.

                 Every test creates a real MFDB (manifest + entity files) on
                 disk in a fresh temp dir via setUp() and deletes the whole
                 tree in tearDown(). No shared state, no leftover files.

                 Run:  python3 tests/test_mfdb_ref_integrity_suite.py

Version:        1.1.0
Date:           2026-08-19
Author:         Elton Boehnen
Contact:        eltonboehnen@gmail.com | boehnenelton2024.pages.dev | github.com/boehnenelton
Format_Creator: Elton Boehnen
RELATIONAL_ID:  82fb32a4-e649-4bba-90d3-ca21260264c4
Release_Version: 300

Changelog:
  1.1.0 - Added TestMFDBAutoFieldMap (5 tests): reading a 105 entity warms
          its field map; 104 entities untouched; cache never written to disk.
"""

import os
import sys
import json
import shutil
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import lib_bejson_Core_mfdb_core as M
import lib_bejson_Core_mfdb_validator as V
import lib_bejson_Core_bejson_core as Core


AUTHOR_FIELDS = [{"name": "author_name", "type": "string"}]

BOOK_FIELDS = [
    {"name": "title", "type": "string"},
    {"name": "author_fk", "type": "string", "fk_target_entity": "authors", "fk_on_delete": "restrict"},
]

REVIEW_FIELDS = [
    {"name": "review_text", "type": "string"},
    {"name": "book_fk", "type": "string", "fk_target_entity": "books", "fk_on_delete": "cascade"},
]

LEGACY_NOTE_FIELDS = [{"name": "note_text", "type": "string"}]


class MFDBTestCase(unittest.TestCase):
    """Base class: every subclass gets a fresh real MFDB (manifest + entity
    files) on disk in setUp(), fully deleted in tearDown()."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="mfdb_refint_test_")
        self.manifest_path = M.mfdb_core_create_database(
            root_dir=self.tmpdir,
            db_name="test_db",
            entities=[
                {"name": "authors", "fields": AUTHOR_FIELDS, "format_version": "105"},
                {"name": "books", "fields": BOOK_FIELDS, "format_version": "105"},
                {"name": "reviews", "fields": REVIEW_FIELDS, "format_version": "105"},
                {"name": "legacy_notes", "fields": LEGACY_NOTE_FIELDS, "format_version": "104"},
            ],
        )
        self.assertTrue(os.path.exists(self.manifest_path))

    def tearDown(self):
        self.assertTrue(os.path.isdir(self.tmpdir))
        shutil.rmtree(self.tmpdir)
        self.assertFalse(os.path.exists(self.tmpdir))

    def add_author(self, name="Elton Boehnen"):
        doc = M.mfdb_core_add_entity_record_105(self.manifest_path, "authors", [name])
        return doc["Values"][-1][0]  # record_uuid

    def add_book(self, title, author_uuid):
        doc = M.mfdb_core_add_entity_record_105(self.manifest_path, "books", [title, author_uuid])
        return doc["Values"][-1][0]

    def add_review(self, text, book_uuid):
        doc = M.mfdb_core_add_entity_record_105(self.manifest_path, "reviews", [text, book_uuid])
        return doc["Values"][-1][0]


# ---------------------------------------------------------------------------
# 1. The switch
# ---------------------------------------------------------------------------

class TestRefIntegritySwitch(MFDBTestCase):

    def test_default_off(self):
        self.assertFalse(M._mfdb_ref_integrity_enabled(self.manifest_path))

    def test_enable_sets_header_true(self):
        M.mfdb_core_enable_ref_integrity(self.manifest_path)
        self.assertTrue(M._mfdb_ref_integrity_enabled(self.manifest_path))
        doc = json.load(open(self.manifest_path))
        self.assertEqual(doc["Ref_Integrity"], "true")

    def test_disable_after_enable(self):
        M.mfdb_core_enable_ref_integrity(self.manifest_path)
        M.mfdb_core_disable_ref_integrity(self.manifest_path)
        self.assertFalse(M._mfdb_ref_integrity_enabled(self.manifest_path))

    def test_off_bypasses_fk_check_entirely(self):
        """With the switch off, a garbage FK value is accepted without complaint."""
        author_uuid = self.add_author()
        doc = M.mfdb_core_add_entity_record_105(self.manifest_path, "books", ["Some Book", "not-a-real-uuid"])
        self.assertEqual(doc["Values"][-1][2], "not-a-real-uuid")


# ---------------------------------------------------------------------------
# 2. Write-time FK exists-check
# ---------------------------------------------------------------------------

class TestFKWriteCheck(MFDBTestCase):

    def setUp(self):
        super().setUp()
        M.mfdb_core_enable_ref_integrity(self.manifest_path)

    def test_valid_fk_accepted(self):
        author_uuid = self.add_author()
        book_uuid = self.add_book("Valid Book", author_uuid)
        self.assertIsInstance(book_uuid, str)

    def test_unresolvable_fk_rejected_no_partial_write(self):
        with self.assertRaises(M.MFDBCoreError) as ctx:
            self.add_book("Bad Book", "nonexistent-uuid")
        self.assertEqual(ctx.exception.code, M.E_MFDB_FK_UNRESOLVED)
        books = M.mfdb_core_load_entity(self.manifest_path, "books")
        self.assertEqual(len(books), 0, "rejected write must leave zero rows")

    def test_null_fk_accepted(self):
        doc = M.mfdb_core_add_entity_record_105(self.manifest_path, "books", ["Orphan-OK Book", None])
        self.assertIsNone(doc["Values"][-1][2])

    def test_fk_to_unregistered_entity_rejected(self):
        # Plant a field pointing at an entity that doesn't exist in this manifest.
        entity_path = M._get_entity_path(self.manifest_path, "books")
        doc = json.load(open(entity_path))
        doc["Fields"][1]["fk_target_entity"] = "nonexistent_entity"
        json.dump(doc, open(entity_path, "w"))
        with self.assertRaises(M.MFDBCoreError) as ctx:
            self.add_book("x", "some-uuid")
        self.assertEqual(ctx.exception.code, M.E_MFDB_FK_TARGET_ENTITY_UNKNOWN)

    def test_update_fk_field_checked(self):
        author1 = self.add_author("Author One")
        author2 = self.add_author("Author Two")
        book_uuid = self.add_book("Book", author1)
        M.mfdb_core_update_entity_record_105(self.manifest_path, "books", book_uuid, "author_fk", author2)
        books = M.mfdb_core_load_entity(self.manifest_path, "books")
        self.assertEqual(books[0]["author_fk"], author2)

    def test_update_fk_field_rejects_unresolvable(self):
        author1 = self.add_author()
        book_uuid = self.add_book("Book", author1)
        with self.assertRaises(M.MFDBCoreError) as ctx:
            M.mfdb_core_update_entity_record_105(self.manifest_path, "books", book_uuid, "author_fk", "garbage")
        self.assertEqual(ctx.exception.code, M.E_MFDB_FK_UNRESOLVED)

    def test_non_fk_field_update_unaffected(self):
        author1 = self.add_author()
        book_uuid = self.add_book("Old Title", author1)
        M.mfdb_core_update_entity_record_105(self.manifest_path, "books", book_uuid, "title", "New Title")
        books = M.mfdb_core_load_entity(self.manifest_path, "books")
        self.assertEqual(books[0]["title"], "New Title")


# ---------------------------------------------------------------------------
# 3. Delete-time resolution: restrict / cascade / null
# ---------------------------------------------------------------------------

class TestDeleteRestrict(MFDBTestCase):

    def setUp(self):
        super().setUp()
        M.mfdb_core_enable_ref_integrity(self.manifest_path)

    def test_restrict_blocks_delete_of_referenced_author(self):
        author_uuid = self.add_author()
        self.add_book("Referencing Book", author_uuid)
        with self.assertRaises(M.MFDBCoreError) as ctx:
            M.mfdb_core_delete_entity_record_105(self.manifest_path, "authors", author_uuid)
        self.assertEqual(ctx.exception.code, M.E_MFDB_FK_RESTRICT_VIOLATION)
        authors = M.mfdb_core_load_entity(self.manifest_path, "authors")
        self.assertEqual(len(authors), 1, "restricted delete must leave the record untouched")

    def test_unreferenced_author_deletes_cleanly(self):
        author_uuid = self.add_author()  # no book references this one
        M.mfdb_core_delete_entity_record_105(self.manifest_path, "authors", author_uuid)
        authors = M.mfdb_core_load_entity(self.manifest_path, "authors")
        self.assertEqual(len(authors), 0)

    def test_deleting_the_book_then_frees_the_author(self):
        author_uuid = self.add_author()
        book_uuid = self.add_book("Book", author_uuid)
        M.mfdb_core_delete_entity_record_105(self.manifest_path, "books", book_uuid)
        M.mfdb_core_delete_entity_record_105(self.manifest_path, "authors", author_uuid)  # no longer blocked
        authors = M.mfdb_core_load_entity(self.manifest_path, "authors")
        self.assertEqual(len(authors), 0)


class TestDeleteCascade(MFDBTestCase):

    def setUp(self):
        super().setUp()
        M.mfdb_core_enable_ref_integrity(self.manifest_path)

    def test_deleting_book_cascades_to_its_reviews(self):
        author_uuid = self.add_author()
        book_uuid = self.add_book("Book", author_uuid)
        review1 = self.add_review("Great!", book_uuid)
        review2 = self.add_review("Meh.", book_uuid)

        M.mfdb_core_delete_entity_record_105(self.manifest_path, "books", book_uuid)

        reviews = M.mfdb_core_load_entity(self.manifest_path, "reviews")
        self.assertEqual(len(reviews), 0, "both reviews must cascade-delete with their book")
        books = M.mfdb_core_load_entity(self.manifest_path, "books")
        self.assertEqual(len(books), 0)

    def test_cascade_does_not_touch_unrelated_reviews(self):
        author_uuid = self.add_author()
        book1 = self.add_book("Book 1", author_uuid)
        book2 = self.add_book("Book 2", author_uuid)
        review_for_book1 = self.add_review("r1", book1)
        review_for_book2 = self.add_review("r2", book2)

        M.mfdb_core_delete_entity_record_105(self.manifest_path, "books", book1)

        reviews = M.mfdb_core_load_entity(self.manifest_path, "reviews")
        self.assertEqual(len(reviews), 1)
        self.assertEqual(reviews[0]["book_fk"], book2)

    def test_cascade_through_two_hops_still_respects_restrict_at_author_level(self):
        """book -> author is restrict, book -> reviews is cascade. Deleting the
        AUTHOR must still be blocked by the book even though the book's own
        dependents (reviews) would cascade -- restrict wins at its own level."""
        author_uuid = self.add_author()
        book_uuid = self.add_book("Book", author_uuid)
        self.add_review("r", book_uuid)
        with self.assertRaises(M.MFDBCoreError) as ctx:
            M.mfdb_core_delete_entity_record_105(self.manifest_path, "authors", author_uuid)
        self.assertEqual(ctx.exception.code, M.E_MFDB_FK_RESTRICT_VIOLATION)
        # nothing should have been touched -- the restrict check fires before any cascade work
        self.assertEqual(len(M.mfdb_core_load_entity(self.manifest_path, "books")), 1)
        self.assertEqual(len(M.mfdb_core_load_entity(self.manifest_path, "reviews")), 1)


class TestDeleteNull(MFDBTestCase):

    def setUp(self):
        super().setUp()
        # Rebuild with author_fk as "null" on delete instead of "restrict" for this class.
        shutil.rmtree(self.tmpdir)
        self.tmpdir = tempfile.mkdtemp(prefix="mfdb_refint_test_")
        null_book_fields = [
            {"name": "title", "type": "string"},
            {"name": "author_fk", "type": "string", "fk_target_entity": "authors", "fk_on_delete": "null"},
        ]
        self.manifest_path = M.mfdb_core_create_database(
            root_dir=self.tmpdir, db_name="null_test_db",
            entities=[
                {"name": "authors", "fields": AUTHOR_FIELDS, "format_version": "105"},
                {"name": "books", "fields": null_book_fields, "format_version": "105"},
            ],
        )
        M.mfdb_core_enable_ref_integrity(self.manifest_path)

    def test_deleting_author_nulls_the_book_fk_instead_of_deleting_book(self):
        author_uuid = self.add_author()
        book_uuid = self.add_book("Book", author_uuid)
        M.mfdb_core_delete_entity_record_105(self.manifest_path, "authors", author_uuid)
        books = M.mfdb_core_load_entity(self.manifest_path, "books")
        self.assertEqual(len(books), 1, "null on_delete must NOT delete the dependent row")
        self.assertIsNone(books[0]["author_fk"])


# ---------------------------------------------------------------------------
# 4. Cascade cycle detection
# ---------------------------------------------------------------------------

class TestCascadeCycle(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="mfdb_refint_cycle_")
        # Two entities that reference each other, both cascade -- a genuine cycle.
        a_fields = [
            {"name": "label", "type": "string"},
            {"name": "b_fk", "type": "string", "fk_target_entity": "entity_b", "fk_on_delete": "cascade"},
        ]
        b_fields = [
            {"name": "label", "type": "string"},
            {"name": "a_fk", "type": "string", "fk_target_entity": "entity_a", "fk_on_delete": "cascade"},
        ]
        self.manifest_path = M.mfdb_core_create_database(
            root_dir=self.tmpdir, db_name="cycle_db",
            entities=[
                {"name": "entity_a", "fields": a_fields, "format_version": "105"},
                {"name": "entity_b", "fields": b_fields, "format_version": "105"},
            ],
        )
        M.mfdb_core_enable_ref_integrity(self.manifest_path)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_mutual_cascade_cycle_raises_not_infinite_loop(self):
        doc_a = M.mfdb_core_add_entity_record_105(self.manifest_path, "entity_a", ["A1", None])
        a_uuid = doc_a["Values"][-1][0]
        doc_b = M.mfdb_core_add_entity_record_105(self.manifest_path, "entity_b", ["B1", a_uuid])
        b_uuid = doc_b["Values"][-1][0]
        M.mfdb_core_update_entity_record_105(self.manifest_path, "entity_a", a_uuid, "b_fk", b_uuid)

        with self.assertRaises(M.MFDBCoreError) as ctx:
            M.mfdb_core_delete_entity_record_105(self.manifest_path, "entity_a", a_uuid)
        self.assertEqual(ctx.exception.code, M.E_MFDB_FK_CASCADE_CYCLE)


# ---------------------------------------------------------------------------
# 5. Entity-droppable check
# ---------------------------------------------------------------------------

class TestEntityDroppable(MFDBTestCase):

    def test_empty_when_nothing_references_it(self):
        self.assertEqual(M.mfdb_core_check_entity_droppable(self.manifest_path, "reviews"), [])

    def test_reports_referencing_rows_for_authors(self):
        author_uuid = self.add_author()
        book_uuid = self.add_book("Book", author_uuid)
        refs = M.mfdb_core_check_entity_droppable(self.manifest_path, "authors")
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0], ("books", "author_fk", book_uuid))

    def test_does_not_require_switch_enabled(self):
        """Read-only check works regardless of Ref_Integrity state."""
        self.assertFalse(M._mfdb_ref_integrity_enabled(self.manifest_path))
        author_uuid = self.add_author()
        self.add_book("Book", author_uuid)
        refs = M.mfdb_core_check_entity_droppable(self.manifest_path, "authors")
        self.assertEqual(len(refs), 1)


# ---------------------------------------------------------------------------
# 6. Standalone audit function (validator, independent of the switch)
# ---------------------------------------------------------------------------

class TestStandaloneAudit(MFDBTestCase):

    def test_clean_database_reports_zero_errors(self):
        author_uuid = self.add_author()
        self.add_book("Book", author_uuid)
        errors = V.mfdb_validator_check_referential_integrity(self.manifest_path)
        self.assertEqual(errors, [])

    def test_audit_works_even_when_switch_is_off(self):
        """The switch only gates live enforcement; the audit is standalone."""
        self.assertFalse(M._mfdb_ref_integrity_enabled(self.manifest_path))
        author_uuid = self.add_author()
        self.add_book("Book", author_uuid)
        # plant an orphan directly (bypassing enforcement, since switch is off)
        entity_path = M._get_entity_path(self.manifest_path, "books")
        doc = json.load(open(entity_path))
        doc["Values"][-1][2] = "totally-fake-uuid"
        json.dump(doc, open(entity_path, "w"))

        errors = V.mfdb_validator_check_referential_integrity(self.manifest_path)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]["code"], "E_MFDB_FK_UNRESOLVED")

    def test_validate_mfdb_database_strict_fk_now_wired(self):
        """strict_fk existed as a dead parameter before Phase 6; confirm it's live now."""
        author_uuid = self.add_author()
        self.add_book("Book", author_uuid)
        entity_path = M._get_entity_path(self.manifest_path, "books")
        doc = json.load(open(entity_path))
        doc["Values"][-1][2] = "totally-fake-uuid"
        json.dump(doc, open(entity_path, "w"))

        res_lenient = V.validate_mfdb_database(self.manifest_path, strict_fk=False)
        self.assertTrue(res_lenient.valid, "strict_fk=False must not run the FK audit")

        res_strict = V.validate_mfdb_database(self.manifest_path, strict_fk=True)
        self.assertFalse(res_strict.valid)

    def test_104_entities_skipped_entirely_by_audit(self):
        """legacy_notes is 104-series; even if it somehow had FK-shaped keys,
        the audit must never touch a non-105-series entity."""
        errors_before = V.mfdb_validator_check_referential_integrity(self.manifest_path)
        entity_path = M._get_entity_path(self.manifest_path, "legacy_notes")
        doc = json.load(open(entity_path))
        doc["Fields"][0]["fk_target_entity"] = "authors"  # nonsensical on a 104 field, must be ignored
        json.dump(doc, open(entity_path, "w"))
        errors_after = V.mfdb_validator_check_referential_integrity(self.manifest_path)
        self.assertEqual(errors_before, errors_after)


# ---------------------------------------------------------------------------
# 7. Legacy 104-series entity: zero behavior change, in a mixed-version MFDB
# ---------------------------------------------------------------------------

class TestLegacy104Untouched(MFDBTestCase):
    """The hard requirement: legacy_notes (104-series) coexists in the same
    manifest as three 105-series entities, with Ref_Integrity ON, and every
    existing 104-series function behaves exactly as it did before Phase 6."""

    def setUp(self):
        super().setUp()
        M.mfdb_core_enable_ref_integrity(self.manifest_path)  # ON, to prove it doesn't matter

    def test_legacy_add_record_unaffected(self):
        doc = M.mfdb_core_add_entity_record(self.manifest_path, "legacy_notes", ["a note"])
        self.assertEqual(doc["Values"][-1], ["a note"])  # no uuid prefix -- proves plain 104 path

    def test_legacy_update_record_unaffected(self):
        M.mfdb_core_add_entity_record(self.manifest_path, "legacy_notes", ["original"])
        doc = M.mfdb_core_update_entity_record(self.manifest_path, "legacy_notes", 0, "note_text", "updated")
        self.assertEqual(doc["Values"][0][0], "updated")

    def test_legacy_remove_record_unaffected(self):
        M.mfdb_core_add_entity_record(self.manifest_path, "legacy_notes", ["note 1"])
        M.mfdb_core_add_entity_record(self.manifest_path, "legacy_notes", ["note 2"])
        M.mfdb_core_remove_entity_record(self.manifest_path, "legacy_notes", 0)
        notes = M.mfdb_core_load_entity(self.manifest_path, "legacy_notes")
        self.assertEqual(len(notes), 1)
        self.assertEqual(notes[0]["note_text"], "note 2")

    def test_105_only_functions_reject_the_104_entity(self):
        """Calling a *_105 function on a 104-series entity must raise cleanly,
        never silently corrupt it."""
        with self.assertRaises(M.MFDBCoreError) as ctx:
            M.mfdb_core_add_entity_record_105(self.manifest_path, "legacy_notes", ["x"])
        self.assertEqual(ctx.exception.code, M.E_MFDB_CORE_INVALID_OPERATION)
        notes = M.mfdb_core_load_entity(self.manifest_path, "legacy_notes")
        self.assertEqual(len(notes), 0, "rejected call must not have written anything")

    def test_legacy_entity_file_format_version_never_changes(self):
        entity_path = M._get_entity_path(self.manifest_path, "legacy_notes")
        M.mfdb_core_add_entity_record(self.manifest_path, "legacy_notes", ["x"])
        doc = json.load(open(entity_path))
        self.assertEqual(doc["Format_Version"], "104")


# ---------------------------------------------------------------------------
# Automatic field map -- reading / using an MFDB never needs a manual build
# ---------------------------------------------------------------------------

class TestMFDBAutoFieldMap(MFDBTestCase):

    def _warm(self, doc):
        return Core._bejson_is_105_cache(doc.get("_bejson_field_map"))

    def test_reading_a_105_entity_warms_its_field_map(self):
        doc = M.mfdb_core_get_entity_doc(self.manifest_path, "authors")
        self.assertTrue(self._warm(doc))

    def test_lookup_on_a_freshly_read_entity_just_works(self):
        a = self.add_author("Ann")
        doc = M.mfdb_core_get_entity_doc(self.manifest_path, "authors")
        idx = Core.bejson_core_get_field_index(doc, "full_name")
        self.assertEqual(doc["Values"][-1][idx], "Ann")
        self.assertEqual(doc["Values"][-1][0], a)

    def test_every_read_gets_a_correct_map_after_the_entity_changes(self):
        self.add_author("Ann")
        first = M.mfdb_core_get_entity_doc(self.manifest_path, "authors")
        self.add_author("Bob")
        second = M.mfdb_core_get_entity_doc(self.manifest_path, "authors")
        self.assertEqual(len(second["Values"]), len(first["Values"]) + 1)
        self.assertEqual(second["Values"][-1][Core.bejson_core_get_field_index(second, "full_name")], "Bob")

    def test_104_entity_read_is_unchanged(self):
        doc = M.mfdb_core_get_entity_doc(self.manifest_path, "legacy_notes")
        self.assertNotIn("_bejson_field_map", doc)

    def test_cache_is_never_written_into_the_entity_file(self):
        self.add_author("Ann")
        M.mfdb_core_get_entity_doc(self.manifest_path, "authors")
        path = M._get_entity_path(self.manifest_path, "authors")
        self.assertNotIn("_bejson_field_map", json.load(open(path)))


if __name__ == "__main__":
    runner = unittest.TextTestRunner(verbosity=2)
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    result = runner.run(suite)
    print(f"\n{'='*70}\nRan {result.testsRun} tests | "
          f"Failures: {len(result.failures)} | Errors: {len(result.errors)}\n{'='*70}")
    sys.exit(0 if result.wasSuccessful() else 1)
