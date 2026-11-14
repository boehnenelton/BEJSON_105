"""
File Name : test_standards_state.py
Rel. Path : Lib_PY/Standards/tests/test_standards_state.py
Purpose   : Tests for the Standards stateful loaded-chamber logging module.
VERSION   : 1.0.0
Author    : Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
RELATIONAL_ID : fde17b7e-a252-446f-84a3-05948f80a940
"""
import os
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_STD = os.path.normpath(os.path.join(_HERE, ".."))
if _STD not in sys.path:
    sys.path.insert(0, _STD)

import lib_bejson_Standards_registry as reg
import lib_bejson_Standards_state as st


class TestStandardsState(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.state_file = os.path.join(self.temp_dir.name, "test_state.json")
        self.log_file = os.path.join(self.temp_dir.name, "test_log.bejson")
        # Ensure fresh state
        st.bejson_standards_clear_context(persist=True, custom_state_file_path=self.state_file)

    def tearDown(self):
        st.bejson_standards_clear_context(persist=False, custom_state_file_path=self.state_file)
        self.temp_dir.cleanup()

    def test_set_and_get_context(self):
        context = st.bejson_standards_set_context(
            subsystem="audit_engine",
            category="compliance",
            actor="test_runner",
            session="sess-12345",
            key_prefix="audit.test",
            flags=["automated", "test"],
            priority=2,
            target_uuid="uuid-001",
            persist=True,
            custom_state_file_path=self.state_file
        )
        self.assertEqual(context["active_subsystem"], "audit_engine")
        self.assertEqual(context["active_category"], "compliance")
        self.assertEqual(context["active_actor"], "test_runner")
        self.assertEqual(context["active_session"], "sess-12345")
        self.assertEqual(context["active_key_prefix"], "audit.test")
        self.assertEqual(context["active_default_flags"], ["automated", "test"])
        self.assertEqual(context["active_default_priority"], 2)
        self.assertTrue(context["is_locked"])

        # Verify disk persistence
        self.assertTrue(os.path.isfile(self.state_file))

        # Re-read from disk
        loaded = st.bejson_standards_load_state(self.state_file)
        self.assertEqual(loaded["active_subsystem"], "audit_engine")

    def test_resolve_context_fallback_and_override(self):
        st.bejson_standards_set_context(
            subsystem="chamber_subsystem",
            category="chamber_cat",
            actor="chamber_actor",
            session="chamber_sess",
            key_prefix="chamber.prefix",
            flags=["chamber_flag"],
            priority=3,
            persist=False,
            custom_state_file_path=self.state_file
        )

        # 1. Complete fallback: all omitted arguments inherit from chamber
        (sub, cat, actor, sess, key, flags, prio, target) = st.bejson_standards_resolve_context(
            explicit_subsystem=None,
            explicit_category=None,
            explicit_actor=None,
            explicit_session=None,
            explicit_event_key="init",
            explicit_flags=None,
            explicit_priority=None,
            explicit_target_uuid=None,
            custom_state_file_path=self.state_file
        )
        self.assertEqual(sub, "chamber_subsystem")
        self.assertEqual(cat, "chamber_cat")
        self.assertEqual(actor, "chamber_actor")
        self.assertEqual(sess, "chamber_sess")
        self.assertEqual(key, "chamber.prefix.init")
        self.assertIn("chamber_flag", flags)
        self.assertEqual(prio, 3)

        # 2. Explicit overrides take absolute precedence
        (sub, cat, actor, sess, key, flags, prio, target) = st.bejson_standards_resolve_context(
            explicit_subsystem="override_sub",
            explicit_category="override_cat",
            explicit_actor="override_actor",
            explicit_session="override_sess",
            explicit_event_key="chamber.prefix.explicit",
            explicit_flags=["new_flag"],
            explicit_priority=1,
            explicit_target_uuid="uuid-999",
            custom_state_file_path=self.state_file
        )
        self.assertEqual(sub, "override_sub")
        self.assertEqual(cat, "override_cat")
        self.assertEqual(actor, "override_actor")
        self.assertEqual(sess, "override_sess")
        self.assertEqual(key, "chamber.prefix.explicit")
        self.assertIn("new_flag", flags)
        self.assertIn("chamber_flag", flags)  # merged default flags
        self.assertEqual(prio, 1)
        self.assertEqual(target, "uuid-999")

    def test_log_inherits_stateful_context(self):
        # Configure sink
        reg.bejson_standards_configure_sink(self.log_file, row_cap=100)

        # Set chamber context
        reg.bejson_standards_set_context(
            subsystem="auto_subsystem",
            category="auto_cat",
            actor="auto_actor",
            session="auto_session",
            key_prefix="auto.test",
            flags=["auto_flag"],
            persist=False,
            custom_state_file_path=self.state_file
        )

        # Write log with minimal arguments (inherits chamber context!)
        ok = reg.bejson_standards_log(
            self.log_file,
            level="INFO",
            event_key="probe",
            message="Inheriting chamber context seamlessly"
        )
        self.assertTrue(ok)
        reg.bejson_standards_flush(self.log_file)

        # Read back log
        records = reg.bejson_standards_read_logs(self.log_file)
        self.assertEqual(len(records), 1)
        row = records[0]
        self.assertEqual(row.get("log_sender_subsystem_name"), "auto_subsystem")
        self.assertEqual(row.get("log_event_category_key"), "auto_cat")
        self.assertEqual(row.get("log_sender_actor_name"), "auto_actor")
        self.assertEqual(row.get("log_sender_session_key"), "auto_session")
        self.assertEqual(row.get("log_event_key"), "auto.test.probe")
        self.assertEqual(row.get("log_event_message_text"), "Inheriting chamber context seamlessly")
        flags_payload = row.get("log_event_flags_payload") or "[]"
        self.assertIn("auto_flag", flags_payload)


if __name__ == "__main__":
    unittest.main()
