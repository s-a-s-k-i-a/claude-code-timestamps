#!/usr/bin/env python3
"""Tests for the chat-timestamps parser and discovery logic (stdlib only).

Run from the repo root:  python3 -m unittest discover tests
(On Windows use:          py -3 -m unittest discover tests)
"""

import importlib.util
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures"
SCRIPT = HERE.parent / "scripts" / "parse-transcript.py"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


pt = _load("parse_transcript", SCRIPT)

FIXED_TZ = timezone(timedelta(hours=2))  # deterministic offset for render tests


def at(y, mo, d, h, mi):
    return datetime(y, mo, d, h, mi, tzinfo=FIXED_TZ)


class TestSanitize(unittest.TestCase):
    def test_spaces_and_slashes_become_dashes(self):
        # This is the exact bug that broke discovery on a path with spaces.
        self.assertEqual(
            pt.sanitize("/Users/s/Claude Code Improvements/chat-timestamps"),
            "-Users-s-Claude-Code-Improvements-chat-timestamps",
        )

    def test_dots_become_dashes(self):
        self.assertEqual(pt.sanitize("/a/b.c.d/e"), "-a-b-c-d-e")

    def test_no_double_leading_dash(self):
        self.assertTrue(pt.sanitize("/x").startswith("-"))
        self.assertFalse(pt.sanitize("/x").startswith("--"))


class TestHumanizeGap(unittest.TestCase):
    def test_units(self):
        self.assertEqual(pt.humanize_gap(timedelta(seconds=30)), "30s")
        self.assertEqual(pt.humanize_gap(timedelta(seconds=90)), "1m")
        self.assertEqual(pt.humanize_gap(timedelta(hours=1)), "1h")
        self.assertEqual(pt.humanize_gap(timedelta(hours=1, minutes=1)), "1h 1m")
        self.assertEqual(pt.humanize_gap(timedelta(hours=4, minutes=12)), "4h 12m")
        self.assertEqual(pt.humanize_gap(timedelta(days=1)), "1d")
        self.assertEqual(pt.humanize_gap(timedelta(days=1, hours=1)), "1d 1h")

    def test_negative_clamped(self):
        self.assertEqual(pt.humanize_gap(timedelta(seconds=-50)), "0s")


class TestFormatTime(unittest.TestCase):
    def test_minutes_vs_seconds(self):
        dt = at(2026, 6, 17, 9, 5)
        self.assertEqual(pt.format_time(dt), "09:05")
        self.assertEqual(pt.format_time(dt, seconds=True), "09:05:00")


class TestExtractPreview(unittest.TestCase):
    def test_string_content(self):
        self.assertEqual(pt.extract_preview({"message": {"content": "hi"}}), ("hi", False))

    def test_text_block(self):
        e = {"message": {"content": [{"type": "text", "text": "yo"}]}}
        self.assertEqual(pt.extract_preview(e), ("yo", False))

    def test_tool_use_flagged(self):
        e = {"message": {"content": [{"type": "tool_use", "name": "Bash"}]}}
        self.assertEqual(pt.extract_preview(e), ("[tool: Bash]", True))

    def test_tool_result_is_empty(self):
        e = {"message": {"content": [{"type": "tool_result", "content": "x"}]}}
        self.assertEqual(pt.extract_preview(e), ("", False))

    def test_thinking_skipped_text_wins(self):
        e = {"message": {"content": [
            {"type": "thinking", "thinking": "secret"},
            {"type": "text", "text": "final"},
        ]}}
        self.assertEqual(pt.extract_preview(e), ("final", False))


class TestParseMessages(unittest.TestCase):
    def test_edge_cases_fixture(self):
        msgs = list(pt.parse_messages(str(FIXTURES / "edge_cases.jsonl")))
        previews = [(role, preview, is_tool) for _dt, role, preview, is_tool in msgs]
        # tool_result, sidechain, attachment, ai-title, invalid json,
        # and whitespace-only content are all filtered out.
        self.assertEqual(previews, [
            ("user", "plain string prompt", False),
            ("assistant", "text after thinking", False),
            ("assistant", "[tool: Read]", True),
            ("assistant", "entry with no timestamp", False),
        ])

    def test_missing_timestamp_yields_none(self):
        msgs = list(pt.parse_messages(str(FIXTURES / "edge_cases.jsonl")))
        no_ts = [m for m in msgs if m[2] == "entry with no timestamp"][0]
        self.assertIsNone(no_ts[0])


class TestRender(unittest.TestCase):
    def _msgs_multi_day(self):
        return [
            (at(2026, 6, 16, 8, 42), "user", "start", False),
            (at(2026, 6, 16, 8, 43), "assistant", "ok", False),
            (at(2026, 6, 16, 12, 55), "assistant", "done", False),   # 4h12m gap
            (at(2026, 6, 17, 9, 3), "user", "tests", False),          # new day
            (at(2026, 6, 17, 9, 5), "assistant", "adding", False),
        ]

    def test_day_dividers_only_on_change(self):
        out = pt.render(self._msgs_multi_day(), count=20, gap_min=15)
        dividers = [l for l in out.splitlines() if l.startswith("─")]
        self.assertEqual(len(dividers), 2)

    def test_idle_gap_marker(self):
        out = pt.render(self._msgs_multi_day(), count=20, gap_min=15)
        gaps = [l for l in out.splitlines() if "later" in l]
        self.assertEqual(len(gaps), 1)
        self.assertIn("4h 12m", gaps[0])

    def test_gap_disabled(self):
        out = pt.render(self._msgs_multi_day(), count=20, gap_min=0)
        self.assertEqual([l for l in out.splitlines() if "later" in l], [])

    def test_ascii_fallback(self):
        out = pt.render(self._msgs_multi_day(), count=20, gap_min=15, unicode=False)
        self.assertNotIn("─", out)
        self.assertTrue(any(l.startswith("-") for l in out.splitlines()))

    def test_none_timestamp_renders_placeholder(self):
        out = pt.render([(None, "assistant", "no ts", False)], count=20)
        self.assertIn("??:??", out)


class TestFindTranscript(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        os.environ["CLAUDE_TIMESTAMPS_PROJECTS_DIR"] = str(self.root)

    def tearDown(self):
        os.environ.pop("CLAUDE_TIMESTAMPS_PROJECTS_DIR", None)
        self.tmp.cleanup()

    def _write(self, dirname, filename, cwd):
        d = self.root / dirname
        d.mkdir(parents=True, exist_ok=True)
        f = d / filename
        f.write_text(
            '{"type":"user","cwd":"%s","timestamp":"2026-06-17T09:00:00Z",'
            '"message":{"role":"user","content":"hi"}}\n' % cwd,
            encoding="utf-8",
        )
        return f

    def test_fast_path_sanitized_dir(self):
        target = "/work/My Project"
        f = self._write(pt.sanitize(target), "session.jsonl", target)
        self.assertEqual(pt.find_transcript(target), f)

    def test_ground_truth_match_when_dirname_differs(self):
        # Even if the directory name does not match our sanitize(), the cwd
        # field inside the transcript is authoritative.
        target = "/work/Other Project"
        f = self._write("totally-unexpected-name", "s.jsonl", target)
        self.assertEqual(pt.find_transcript(target), f)

    def test_no_match_returns_none(self):
        self._write("some-dir", "s.jsonl", "/work/elsewhere")
        self.assertIsNone(pt.find_transcript("/work/not-recorded"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
