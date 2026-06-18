#!/usr/bin/env python3
"""MessageDisplay worker (experimental inline timestamps).

Prepends a dim local-time ``[HH:MM:SS]`` to the FIRST streamed batch of each
assistant message. This is display-only: MessageDisplay never changes the
transcript or what the model sees, so the marker cannot confuse Claude.

Contract (verified against a working community plugin and docs.claude.com/hooks):
  stdin  : {"hook_event_name":"MessageDisplay","index":<int>,"delta":"<text>", ...}
           ``index`` is the zero-based batch number; ``delta`` is that batch's text.
  stdout : {"hookSpecificOutput":{"hookEventName":"MessageDisplay",
            "displayContent":"<text to show on screen for this batch>"}}

We stamp only ``index == 0`` so the time shows once per message, and echo
``delta`` unchanged for later batches. Any error -> no output -> Claude Code
shows the original text (assistant output is never swallowed).

Gating is handled cheaply by message-display.sh before this runs; this worker
only formats.
"""

import json
import sys
from datetime import datetime, timezone

DIM = "\033[2m"
RESET = "\033[0m"


def build_display(data, now, seconds=True):
    """Return the MessageDisplay hookSpecificOutput payload."""
    delta = data.get("delta", "")
    if data.get("index") == 0:
        ts = now.strftime("%H:%M:%S" if seconds else "%H:%M")
        delta = f"{DIM}[{ts}]{RESET} {delta}"
    return {
        "hookSpecificOutput": {
            "hookEventName": "MessageDisplay",
            "displayContent": delta,
        }
    }


def main():
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
        if not isinstance(data, dict):
            return
        now = datetime.now(timezone.utc).astimezone()
        print(json.dumps(build_display(data, now)))
    except Exception:
        return  # fail-safe: original text is displayed unchanged


if __name__ == "__main__":
    main()
