#!/usr/bin/env python3
"""UserPromptSubmit hook: give Claude lightweight, ground-truth time awareness.

Emits one line of hidden ``additionalContext`` each turn so the model knows the
current time, how long since its last reply, and how long the session has run —
useful for reasoning like "the TTL was 5h and 3h have passed, still cached".

Design goals:
  * Never block or slow the prompt: any error -> empty output, exit 0.
  * Cheap: reads only the head and tail of the transcript, not the whole file.
  * Opt-in: OFF by default so the plugin is token-free; this is the only surface
    that adds tokens. Enable with CLAUDE_TIMESTAMPS_INJECT=on (also 1/true/yes).

This only adds context the model sees; it does not change the visible prompt.
Verified contract: docs.claude.com/en/docs/claude-code/hooks (UserPromptSubmit
-> hookSpecificOutput.additionalContext).
"""

import json
import os
import sys
from datetime import datetime, timezone

ENABLED = {"1", "on", "true", "yes", "enable", "enabled"}
TAIL_BYTES = 128 * 1024
HEAD_BYTES = 64 * 1024


def enabled():
    # Opt-in: off unless explicitly enabled, so the plugin is token-free by default.
    return os.environ.get("CLAUDE_TIMESTAMPS_INJECT", "off").strip().lower() in ENABLED


def parse_ts(ts_raw):
    try:
        dt = datetime.fromisoformat(str(ts_raw).replace("Z", "+00:00"))
    except (ValueError, AttributeError, TypeError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone()


def _iter_json_lines(text):
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(entry, dict):
            yield entry


def session_start(path):
    """First recorded timestamp (reads only the head of the file)."""
    try:
        with open(path, "rb") as f:
            head = f.read(HEAD_BYTES).decode("utf-8", "replace")
    except OSError:
        return None
    for entry in _iter_json_lines(head):
        dt = parse_ts(entry.get("timestamp"))
        if dt:
            return dt
    return None


def last_reply(path):
    """Most recent assistant timestamp (reads only the tail of the file)."""
    try:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            f.seek(max(0, size - TAIL_BYTES))
            tail = f.read().decode("utf-8", "replace")
    except OSError:
        return None
    latest = None
    for entry in _iter_json_lines(tail):
        if entry.get("type") == "assistant":
            dt = parse_ts(entry.get("timestamp"))
            if dt and (latest is None or dt > latest):
                latest = dt
    return latest


def humanize(delta):
    secs = max(0, int(delta.total_seconds()))
    days, rem = divmod(secs, 86400)
    hours, rem = divmod(rem, 3600)
    mins, _ = divmod(rem, 60)
    if days:
        return f"{days}d {hours}h" if hours else f"{days}d"
    if hours:
        return f"{hours}h {mins}m" if mins else f"{hours}h"
    if mins:
        return f"{mins}m"
    return "under 1m"


def build_context(transcript_path, now):
    parts = [f"now {now.strftime('%Y-%m-%d %H:%M %Z').strip()}"]
    if transcript_path and os.path.isfile(transcript_path):
        reply = last_reply(transcript_path)
        if reply:
            parts.append(f"last assistant reply {humanize(now - reply)} ago")
        start = session_start(transcript_path)
        if start:
            parts.append(f"session started {start.strftime('%H:%M')} ({humanize(now - start)} ago)")
    return "[session timing] " + "; ".join(parts) + "."


def main():
    if not enabled():
        return
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, ValueError):
        data = {}

    try:
        now = datetime.now(timezone.utc).astimezone()
        context = build_context(data.get("transcript_path"), now)
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": context,
            }
        }))
    except Exception:
        # Never let a timing hook break the user's prompt.
        return


if __name__ == "__main__":
    main()
