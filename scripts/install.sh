#!/usr/bin/env bash
# Install or update chat-timestamps for a MANUAL (git) install.
#
#   bash install.sh            # install/update into ~/.claude/plugins/chat-timestamps
#   bash install.sh /custom/dir
#
# Idempotent: if the destination is already a git clone it is fast-forwarded to
# the latest release (old files overwritten); otherwise it is cloned fresh.
#
# Marketplace users don't need this — see README "Updating".
set -euo pipefail

REPO="https://github.com/s-a-s-k-i-a/claude-code-timestamps.git"
DEST="${1:-$HOME/.claude/plugins/chat-timestamps}"

if [ -d "$DEST/.git" ]; then
  echo "Updating existing install at: $DEST"
  git -C "$DEST" fetch --depth 1 origin main
  git -C "$DEST" reset --hard origin/main   # overwrite local copy with latest
else
  echo "Installing to: $DEST"
  rm -rf "$DEST"
  mkdir -p "$(dirname "$DEST")"
  git clone --depth 1 "$REPO" "$DEST"
fi

VERSION="$(grep -o '"version"[^,]*' "$DEST/.claude-plugin/plugin.json" | head -1 | cut -d'"' -f4 || true)"
echo "Done — chat-timestamps ${VERSION:-(unknown)} is in place."
echo "Restart Claude Code, or run /reload-plugins, to pick up the new version."
