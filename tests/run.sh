#!/usr/bin/env bash
# Run the chat-timestamps test suite. Uses whichever Python 3 launcher works
# (python3 on macOS/Linux; py -3 on Windows where python3 is a Store stub).
set -e
cd "$(dirname "$0")/.."

for PY in "python3" "py -3" "python"; do
  if $PY -c "import sys; assert sys.version_info[0]==3" >/dev/null 2>&1; then
    echo "Using launcher: $PY"
    exec $PY -m unittest discover -s tests -v
  fi
done

echo "No working Python 3 launcher found (tried python3, py -3, python)." >&2
exit 1
