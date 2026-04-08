# Chat Timestamps for Claude Code

**See when every message was sent — right inside Claude Code.**

---

## The Problem

Claude Code doesn't show timestamps on messages. In long sessions, you lose track of *when* things happened — when you asked a question, when Claude started working, how long a task took. This information exists in the transcript data, but it's buried in JSON files.

## The Solution

This plugin adds a simple `/timestamps` command that displays a clean timeline of your conversation with timestamps for every message.

```
--- Message Timeline ---

14:02  You     Can you refactor the auth module?
14:02  Claude  I'll start by reading the current auth implementation...
14:03  Claude  [tool: Read]
14:05  Claude  I've refactored the auth module. Here's what changed...
14:32  You     Looks good. Now add tests for the new token refresh logic.
14:32  Claude  I'll create tests for the token refresh functionality...
```

Same-day messages show **HH:MM**. Older messages show **YYYY-MM-DD HH:MM**.

## Installation

### 1. Clone this plugin

```bash
git clone https://github.com/s-a-s-k-i-a/claude-code-timestamps.git ~/.claude/plugins/chat-timestamps
```

### 2. Register the plugin in your settings

Open (or create) `~/.claude/settings.json` and add the plugin path:

```json
{
  "plugins": [
    "~/.claude/plugins/chat-timestamps"
  ]
}
```

If you already have other plugins listed, just add this path to the existing array.

### 3. Restart Claude Code

Start a new Claude Code session. The `/timestamps` command is now available.

## Usage

```
/timestamps        # Show the last 20 messages with timestamps
/timestamps 50     # Show the last 50 messages
/timestamps 5      # Show just the last 5 messages
```

## How It Works

Claude Code already records a timestamp for every API call in its transcript files (`~/.claude/projects/.../*.jsonl`). This plugin reads that transcript data and presents it as a human-readable timeline. No data is collected or sent anywhere — everything stays local.

## Requirements

- Claude Code (with plugin support)
- Python 3 (used to parse the transcript JSON — pre-installed on macOS and most Linux systems)

## Related

This plugin was built in response to these open feature requests on the Claude Code repo:

- [#2447 — Timestamps on messages](https://github.com/anthropics/claude-code/issues/2447)
- [#30144 — Show timestamps in chat](https://github.com/anthropics/claude-code/issues/30144)
- [#31271 — Add timestamp display](https://github.com/anthropics/claude-code/issues/31271)

If native timestamp support lands in Claude Code, this plugin will no longer be needed — and that's a good thing!

## License

MIT
