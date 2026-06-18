#!/usr/bin/env bash
# Zero-token timeline — print the session timeline WITHOUT involving the model.
#
# `/timestamps` is a slash command, so it goes through Claude (a small token
# cost). Run THIS in your own terminal instead and no agent is involved at all:
# no tokens, and instant.
#
#   bash timeline.sh                 # last 20 turns for the current directory
#   bash timeline.sh 50              # last 50
#   bash timeline.sh 50 --seconds    # extra args pass straight to the parser
#   bash timeline.sh 0 --tools       # all turns, including tool calls
#
# Tip: alias it for everyday use, e.g.
#   alias cct='bash ~/.claude/plugins/chat-timestamps/scripts/timeline.sh'
#
# The parser self-discovers the right transcript from the working directory, so
# there is nothing to configure. Auto-detects the Python launcher (handles the
# Windows `py -3` case).
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
PARSER="$DIR/parse-transcript.py"

for PY in python3 "py -3" python; do
  if command -v ${PY%% *} >/dev/null 2>&1; then
    exec $PY "$PARSER" --cwd "$PWD" "$@"
  fi
done

echo "No Python 3 launcher found (tried python3, py -3, python)." >&2
exit 1
