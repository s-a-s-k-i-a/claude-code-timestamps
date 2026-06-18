#!/usr/bin/env bash
# MessageDisplay hook gate for the experimental inline-timestamp feature.
#
# This runs once per streamed batch of every assistant message, so the DISABLED
# path is kept deliberately cheap: it reads one small state file and exits
# without spawning Python. Only when the feature is ON do we hand off to the
# Python worker that formats the timestamp.
#
# Enable/disable at runtime with:  /timestamps inline on   |   /timestamps inline off
# Or force via env:                CLAUDE_TIMESTAMPS_INLINE=on|off
#
# Invoked as `bash <this script>` (see hooks.json) so it does not rely on the
# executable bit surviving clones/zips/Windows.
set -u

STATE_DIR="${CLAUDE_TIMESTAMPS_STATE_DIR:-$HOME/.claude/chat-timestamps}"

state="${CLAUDE_TIMESTAMPS_INLINE:-}"
[ -z "$state" ] && state="$(cat "$STATE_DIR/inline" 2>/dev/null || true)"

case "$state" in
  on|ON|On|1|true|yes) ;;
  *) exit 0 ;;   # disabled -> show original message, no Python spawned
esac

WORKER="$(dirname "$0")/message-display.py"
for PY in python3 "py -3" python; do
  if command -v ${PY%% *} >/dev/null 2>&1; then
    exec $PY "$WORKER"
  fi
done
exit 0   # no Python launcher -> show original message
