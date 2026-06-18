#!/usr/bin/env python3
"""Tests for the experimental inline-timestamp worker and toggle (stdlib only)."""

import importlib.util
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "scripts"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


md = _load("message_display", SCRIPTS / "message-display.py")
tg = _load("inline_toggle", SCRIPTS / "inline-toggle.py")

NOW = datetime(2026, 6, 17, 9, 5, 0, tzinfo=timezone(timedelta(hours=2)))


class TestMessageDisplay(unittest.TestCase):
    def _content(self, data):
        return md.build_display(data, NOW)["hookSpecificOutput"]["displayContent"]

    def test_first_batch_is_stamped(self):
        dc = self._content({"index": 0, "delta": "hello"})
        self.assertIn("[09:05:00]", dc)
        self.assertTrue(dc.endswith("hello"))
        self.assertIn("\033[2m", dc)  # dim ANSI
        self.assertIn("\033[0m", dc)  # reset

    def test_later_batch_is_echoed_unchanged(self):
        self.assertEqual(self._content({"index": 1, "delta": " more"}), " more")

    def test_missing_index_is_not_stamped(self):
        self.assertEqual(self._content({"delta": "x"}), "x")

    def test_output_event_name(self):
        out = md.build_display({"index": 0, "delta": "y"}, NOW)
        self.assertEqual(out["hookSpecificOutput"]["hookEventName"], "MessageDisplay")

    def test_minutes_only_option(self):
        dc = md.build_display({"index": 0, "delta": "z"}, NOW, seconds=False)
        dc = dc["hookSpecificOutput"]["displayContent"]
        self.assertIn("[09:05]", dc)
        self.assertNotIn("[09:05:00]", dc)


class TestInlineToggle(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["CLAUDE_TIMESTAMPS_STATE_DIR"] = self.tmp.name
        os.environ.pop("CLAUDE_TIMESTAMPS_INLINE", None)

    def tearDown(self):
        os.environ.pop("CLAUDE_TIMESTAMPS_STATE_DIR", None)
        self.tmp.cleanup()

    def test_default_is_off(self):
        new, _ = tg.apply("status")
        self.assertFalse(new)

    def test_on_off_persist(self):
        new, _ = tg.apply("on")
        self.assertTrue(new)
        self.assertEqual(tg.read_state(), "on")
        new, _ = tg.apply("off")
        self.assertFalse(new)
        self.assertEqual(tg.read_state(), "off")

    def test_toggle_flips(self):
        tg.apply("off")
        new, _ = tg.apply("toggle")
        self.assertTrue(new)
        new, _ = tg.apply("toggle")
        self.assertFalse(new)

    def test_unknown_action(self):
        _, msg = tg.apply("frobnicate")
        self.assertIn("Unknown", msg)

    def test_env_override_is_reported(self):
        tg.apply("off")
        os.environ["CLAUDE_TIMESTAMPS_INLINE"] = "on"
        _, msg = tg.apply("status")
        self.assertIn("overrides", msg)


if __name__ == "__main__":
    unittest.main(verbosity=2)
