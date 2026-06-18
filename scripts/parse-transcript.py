#!/usr/bin/env python3
"""Display a timestamped timeline of the current Claude Code session.

Reads the session transcript JSONL that Claude Code already writes under
``~/.claude/projects/`` and renders a human-readable timeline with day
dividers and idle-gap markers. No data leaves the machine.

The transcript is located by matching the ground-truth ``cwd`` field stored
in each entry, so it works regardless of how Claude Code sanitizes folder
names (paths with spaces, dots, etc.).
"""

import argparse
import json
import locale
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

NO_TEXT = "(no text content)"


# --------------------------------------------------------------------------- #
# Transcript discovery
# --------------------------------------------------------------------------- #
def projects_root():
    """Return the Claude projects directory (overridable for tests)."""
    override = os.environ.get("CLAUDE_TIMESTAMPS_PROJECTS_DIR")
    if override:
        return Path(override)
    return Path.home() / ".claude" / "projects"


def sanitize(path):
    """Mirror Claude Code's project-dir naming: every non-alphanumeric -> '-'."""
    return re.sub(r"[^A-Za-z0-9]", "-", path)


def _same_path(a, b):
    if not a or not b:
        return False
    return os.path.normpath(a) == os.path.normpath(b)


def transcript_cwd(path):
    """Return the first ``cwd`` recorded in a transcript, or None."""
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(entry, dict) and entry.get("cwd"):
                    return entry["cwd"]
    except OSError:
        return None
    return None


def find_transcript(target_cwd):
    """Find the newest transcript whose recorded cwd matches ``target_cwd``.

    Strategy (robust to directory-name sanitization changes):
      1. Ground-truth match inside the sanitized-name directory (newest first).
      2. Ground-truth match anywhere under the projects root (newest first).
      3. Fallback: newest file in the sanitized-name directory.
    """
    root = projects_root()
    if not root.is_dir():
        return None
    try:
        files = sorted(
            root.glob("*/*.jsonl"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
    except OSError:
        files = []
    if not files:
        return None

    san = sanitize(target_cwd.rstrip("/\\"))
    in_san = [f for f in files if f.parent.name == san]

    for candidate in in_san:
        if _same_path(transcript_cwd(candidate), target_cwd):
            return candidate
    for candidate in files:
        if _same_path(transcript_cwd(candidate), target_cwd):
            return candidate
    if in_san:
        return in_san[0]
    return None


def validate_transcript_path(path):
    """Validate an explicit --transcript path stays inside the projects dir."""
    resolved = os.path.realpath(path)
    base = os.path.realpath(str(projects_root()))
    if not (resolved == base or resolved.startswith(base + os.sep)):
        sys.exit("Error: transcript path must be inside the Claude projects directory")
    if not resolved.endswith(".jsonl"):
        sys.exit("Error: transcript file must be a .jsonl file")
    if not os.path.isfile(resolved):
        sys.exit("Error: transcript file not found")
    return resolved


# --------------------------------------------------------------------------- #
# Parsing
# --------------------------------------------------------------------------- #
def extract_preview(entry):
    """Return (preview_text, is_tool) for a user/assistant entry.

    ``is_tool`` is True when the entry has no prose text and we fell back to a
    tool-call summary, so the caller can hide tool churn by default.
    """
    msg = entry.get("message", {})
    if not isinstance(msg, dict):
        return "", False
    content = msg.get("content", [])

    if isinstance(content, str):
        return content, False

    if isinstance(content, list):
        for block in content:
            if not isinstance(block, dict):
                continue
            btype = block.get("type")
            if btype == "text":
                return block.get("text", ""), False
            if btype == "tool_use":
                return f"[tool: {block.get('name', '?')}]", True
            # thinking / tool_result blocks are intentionally skipped
    return "", False


def truncate(text, max_len=80):
    """Collapse whitespace and truncate; return NO_TEXT sentinel when empty."""
    text = " ".join(text.split()).strip()
    if not text:
        return NO_TEXT
    if len(text) > max_len:
        return text[: max_len - 1] + "…"  # ellipsis
    return text


def parse_timestamp(ts_raw):
    """Parse an ISO timestamp into a local-time datetime, or None."""
    try:
        dt = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
    except (ValueError, AttributeError, TypeError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone()


def parse_messages(transcript_path):
    """Yield (datetime|None, role, preview, is_tool) for each meaningful message.

    Skips tool-result carriers, sidechain (subagent) turns, and entries with
    no displayable text. Tool-only entries are tagged ``is_tool=True`` so the
    caller can filter them out for a clean conversation view.
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
            if not isinstance(entry, dict):
                continue
            if entry.get("type") not in ("user", "assistant"):
                continue
            if entry.get("isSidechain"):
                continue
            raw, is_tool = extract_preview(entry)
            preview = truncate(raw)
            if preview == NO_TEXT:
                continue
            yield (
                parse_timestamp(entry.get("timestamp", "")),
                entry.get("type", ""),
                preview,
                is_tool,
            )


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #
def humanize_gap(delta):
    """Render a timedelta as a compact '4h 12m' / '2d 3h' / '45m' / '30s'."""
    secs = max(0, int(delta.total_seconds()))
    days, rem = divmod(secs, 86400)
    hours, rem = divmod(rem, 3600)
    mins, s = divmod(rem, 60)
    if days:
        return f"{days}d {hours}h" if hours else f"{days}d"
    if hours:
        return f"{hours}h {mins}m" if mins else f"{hours}h"
    if mins:
        return f"{mins}m"
    return f"{s}s"


def format_time(dt, seconds=False):
    return dt.strftime("%H:%M:%S" if seconds else "%H:%M")


def divider(dt, unicode=True):
    bar = ("─" if unicode else "-") * 8
    return f"{bar}  {dt.strftime('%A, %d %B %Y')}  {bar}"


def gap_line(delta, unicode=True):
    mark = "⋯" if unicode else "..."
    return f"          {mark} {humanize_gap(delta)} later {mark}"


def render(messages, count=20, seconds=False, gap_min=15, unicode=True):
    """Build the timeline text from parsed messages."""
    tail = messages[-count:] if count else list(messages)
    out = ["", "--- Message Timeline ---", ""]

    prev_date = None
    prev_dt = None
    for dt, role, preview, _is_tool in tail:
        if dt is not None:
            day = dt.date()
            if day != prev_date:
                out.append(divider(dt, unicode))
                prev_date = day
                prev_dt = None
            elif prev_dt is not None and gap_min and (dt - prev_dt) >= timedelta(minutes=gap_min):
                out.append(gap_line(dt - prev_dt, unicode))
            prev_dt = dt
            ts = format_time(dt, seconds)
        else:
            ts = "??:??:??" if seconds else "??:??"
        label = "You" if role == "user" else "Claude"
        out.append(f"  {ts}  {label:<6}  {preview}")

    total = len(messages)
    out.append("")
    out.append(f"Showing {len(tail)} of {total} message{'s' if total != 1 else ''}.")
    if count and total > count:
        out.append("Tip: /timestamps <number> shows more; /timestamps seconds adds HH:MM:SS.")
    return "\n".join(out)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _supports_unicode():
    enc = (getattr(sys.stdout, "encoding", None) or "").lower()
    return "utf" in enc


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Render a Claude Code session timeline.")
    p.add_argument("count", nargs="?", type=int, default=20,
                   help="number of recent messages to show (<=0 means all; default 20)")
    p.add_argument("--cwd", default=None, help="project directory (default: current)")
    p.add_argument("--transcript", default=None, help="explicit transcript .jsonl path")
    p.add_argument("--seconds", action="store_true", help="show HH:MM:SS")
    p.add_argument("--tools", action="store_true",
                   help="include tool-call lines (hidden by default)")
    p.add_argument("--gap", type=int, default=15,
                   help="idle-gap marker threshold in minutes (0 disables; default 15)")
    return p.parse_args(argv)


def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # robust unicode on Windows
    except Exception:
        pass
    try:
        locale.setlocale(locale.LC_TIME, "")  # localized day/month names
    except (locale.Error, ValueError):
        pass

    args = parse_args(argv)

    if args.transcript:
        path = validate_transcript_path(args.transcript)
    else:
        target = args.cwd or os.getcwd()
        path = find_transcript(target)
        if not path:
            print("No transcript found for this directory.")
            print(f"  Looked under: {projects_root()}")
            print("  Run /timestamps from a folder with an active Claude Code session.")
            return

    messages = list(parse_messages(str(path)))
    if not args.tools:
        messages = [m for m in messages if not m[3]]
    if not messages:
        print("\n--- Message Timeline ---\n\n(No messages with text content yet.)")
        return

    count = args.count
    if count is not None and count <= 0:
        count = None
    print(render(
        messages,
        count=count,
        seconds=args.seconds,
        gap_min=max(0, args.gap),
        unicode=_supports_unicode(),
    ))


if __name__ == "__main__":
    main()
