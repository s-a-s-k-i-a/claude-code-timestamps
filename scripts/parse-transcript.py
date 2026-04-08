#!/usr/bin/env python3
"""Parse a Claude Code transcript JSONL file and display a timestamped message timeline."""

import json
import os
import sys
from datetime import datetime, timezone


def validate_transcript_path(path):
    """Validate that the path points to a real file inside ~/.claude/projects/."""
    resolved = os.path.realpath(path)
    claude_dir = os.path.realpath(os.path.expanduser("~/.claude/projects"))
    if not resolved.startswith(claude_dir + os.sep):
        sys.exit("Error: transcript path must be inside ~/.claude/projects/")
    if not resolved.endswith(".jsonl"):
        sys.exit("Error: transcript file must be a .jsonl file")
    if not os.path.isfile(resolved):
        sys.exit("Error: transcript file not found")
    return resolved


def extract_preview(entry):
    """Extract a short text preview from a message entry."""
    msg = entry.get("message", {})
    content = msg.get("content", [])

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "text":
                return block.get("text", "")
            if block.get("type") == "tool_use":
                return f"[tool: {block.get('name', '?')}]"

    return ""


def truncate(text, max_len=80):
    """Truncate text to max_len, collapsing whitespace."""
    text = " ".join(text.split()).strip()
    if len(text) > max_len:
        return text[: max_len - 3] + "..."
    return text if text else "(no text content)"


def format_timestamp(ts_raw, today):
    """Format an ISO timestamp as HH:MM (same day) or YYYY-MM-DD HH:MM (older)."""
    try:
        dt = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
        local_dt = dt.astimezone()
        if local_dt.date() == today:
            return local_dt.strftime("%H:%M")
        return local_dt.strftime("%Y-%m-%d %H:%M")
    except (ValueError, AttributeError, TypeError):
        return "??:??"


def parse_messages(transcript_path):
    """Read the JSONL file and yield (timestamp_raw, role, preview) tuples.

    Skips entries without meaningful text content (e.g. tool-approval responses).
    """
    with open(transcript_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("type") not in ("user", "assistant"):
                continue
            preview = truncate(extract_preview(entry))
            if preview == "(no text content)":
                continue
            yield (
                entry.get("timestamp", ""),
                entry.get("type", ""),
                preview,
            )


def main():
    if len(sys.argv) < 2:
        sys.exit("Usage: parse-transcript.py <transcript_path> [count]")

    transcript_path = validate_transcript_path(sys.argv[1])

    count = 20
    if len(sys.argv) >= 3 and sys.argv[2].isdigit() and int(sys.argv[2]) > 0:
        count = int(sys.argv[2])

    messages = list(parse_messages(transcript_path))
    tail = messages[-count:]

    today = datetime.now(timezone.utc).astimezone().date()

    print()
    print("--- Message Timeline ---")
    print()
    for ts_raw, role, preview in tail:
        ts = format_timestamp(ts_raw, today)
        label = "You" if role == "user" else "Claude"
        print(f"{ts}  {label:<6}  {preview}")
    print()
    print(f"Showing {len(tail)} of {len(messages)} messages.")
    if len(messages) > count:
        print("Tip: use /timestamps <number> to show more messages.")


if __name__ == "__main__":
    main()
