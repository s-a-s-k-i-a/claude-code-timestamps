#!/usr/bin/env python3
"""Toggle the experimental inline message-timestamp feature on/off.

State is stored outside the plugin directory so it survives plugin updates:
``~/.claude/chat-timestamps/inline`` (override the dir with
CLAUDE_TIMESTAMPS_STATE_DIR). The MessageDisplay hook reads this file on every
message, so toggling takes effect on the next assistant message — no restart
needed once the plugin (v2.1+) is loaded.
"""

import os
import sys
from pathlib import Path

ON_VALUES = ("on", "1", "true", "yes", "enable", "enabled")


def state_dir():
    override = os.environ.get("CLAUDE_TIMESTAMPS_STATE_DIR")
    return Path(override) if override else Path.home() / ".claude" / "chat-timestamps"


def state_file():
    return state_dir() / "inline"


def read_state():
    try:
        return state_file().read_text(encoding="utf-8").strip().lower()
    except OSError:
        return "off"


def write_state(value):
    d = state_dir()
    d.mkdir(parents=True, exist_ok=True)
    state_file().write_text("on" if value else "off", encoding="utf-8")


def apply(action):
    """Return (new_state_bool, message) for an action; perform writes as needed."""
    current = read_state() in ON_VALUES
    action = (action or "status").strip().lower()

    if action in ("on", "enable"):
        write_state(True)
        new = True
    elif action in ("off", "disable"):
        write_state(False)
        new = False
    elif action == "toggle":
        new = not current
        write_state(new)
    elif action in ("status", ""):
        new = current
    else:
        return current, f"Unknown option '{action}'. Use: on | off | toggle | status"

    lines = [f"Inline message timestamps: {'ON' if new else 'OFF'}"]
    env = os.environ.get("CLAUDE_TIMESTAMPS_INLINE")
    if env:
        lines.append(f"Note: env CLAUDE_TIMESTAMPS_INLINE='{env}' overrides this stored state.")
    lines.append("Takes effect on the next assistant message (plugin v2.1+ must be loaded; "
                 "restart once after updating).")
    return new, "\n".join(lines)


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    _, message = apply(argv[0] if argv else "status")
    print(message)


if __name__ == "__main__":
    main()
