# Chat Timestamps for Claude Code

> See exactly **when** every message in your Claude Code session happened — as an on-demand timeline or live on each message — privately, and without spending tokens.

Claude Code doesn't show times on messages. In a long or multi-day session you
can't tell whether an exchange was five minutes or three days ago, how long a
build ran, or what you were doing before lunch. The timing is already recorded
in your local session files — this plugin surfaces it, cleanly.

```
--- Message Timeline ---

────────  Tuesday, 16 June 2026  ────────
  10:42  You     start the auth refactor
  10:43  Claude  On it, reading the module.
          ⋯ 4h 12m later ⋯
  14:55  Claude  Done after a long-running build.
────────  Wednesday, 17 June 2026  ────────
  11:03  You     add tests now
  11:05  Claude  Adding tests for the new logic.
```

## What you get

- 🕑 **`/timestamps` timeline** — your conversation with a time on every turn, **day dividers** for multi-day sessions, and **idle-gap markers** (`⋯ 4h 12m later ⋯`) that show where time jumped.
- ⚡ **Live inline timestamps** *(optional, 0 tokens)* — a dim `[HH:MM:SS]` on each assistant message as it streams. It's display-only, so it never enters the transcript or Claude's context and costs nothing.
- 🧠 **Time-aware Claude** *(optional)* — let Claude know how long since your last message and how long the session has run, for reasoning like *"the DNS TTL was 5h and 3h have passed — still cached."*
- 🔒 **Local & ground-truth** — reads only the session files Claude Code already writes on your machine. Times come from the recorded data, so they stay correct even when a self-reported clock would drift. Nothing is sent anywhere.

## Install

**Recommended — plugin marketplace:**

```
/plugin marketplace add s-a-s-k-i-a/claude-code-timestamps
/plugin install chat-timestamps@chat-timestamps
```

Restart Claude Code. `/timestamps` is now available, and the plugin auto-updates on future releases.

<details>
<summary><b>Alternative — manual (git) install</b></summary>

```bash
git clone https://github.com/s-a-s-k-i-a/claude-code-timestamps.git \
  ~/.claude/plugins/chat-timestamps
```

Add the path to `~/.claude/settings.json`:

```json
{ "plugins": ["~/.claude/plugins/chat-timestamps"] }
```

Restart Claude Code.
</details>

## Use it

### 1. See the timeline

```
/timestamps              # last 20 conversation turns
/timestamps 50           # last 50
/timestamps 5            # last 5
```

Add any of these words to tweak the view (combine freely, e.g. `/timestamps 50 tools seconds`):

| Word | Effect |
| --- | --- |
| `seconds` | show `HH:MM:SS` instead of `HH:MM` — handy for matching external logs |
| `tools` | include tool-call lines (hidden by default to keep the view clean) |
| *a number* | how many recent turns to show (default `20`; `0` shows all) |

### 2. Turn on live inline timestamps *(free)*

Show the time on each assistant message as it appears:

```
/timestamps inline on      # enable
/timestamps inline off     # disable
/timestamps inline         # show current state
```

```
[10:42:03] Both workers are active...
[10:47:12] gc-694 finished, gc-695 still running...
```

This uses Claude Code's display-only `MessageDisplay` hook: the marker is drawn
**on screen only**, never enters the transcript or Claude's context, and **costs
zero tokens**. Your choice is remembered across plugin updates. *(Experimental —
see [Compatibility](#compatibility).)*

### 3. Make Claude time-aware *(optional)*

If you want Claude itself to reason about elapsed time during long-running work,
enable the timing hook before starting Claude Code:

```bash
export CLAUDE_TIMESTAMPS_INJECT=on
```

Each turn, one hidden line is added to Claude's context (your visible prompt is
untouched):

```
[session timing] now 2026-06-18 10:05 CEST; last assistant reply 3m ago; session started 09:39 (25m ago).
```

This is the **only** feature that uses tokens, so it's **off by default**.
Remove the variable (or set `=off`) to disable it again.

## Token cost & privacy

Free and private by default — you opt in to the one feature that isn't.

| Feature | Default | Token cost | Sends data off your machine? |
| --- | --- | --- | --- |
| `/timestamps` timeline | on | only when you run it (small) | no |
| Live inline timestamps | off | **none** (display-only) | no |
| Time-aware Claude | off | small, per turn (by design) | no |

Everything is computed locally from the transcript Claude Code already stores
under `~/.claude/projects/`. No network calls, no telemetry, nothing leaves your
machine.

## Updating

Each release bumps the `version` field in `.claude-plugin/plugin.json`, and
Claude Code uses that version as the signal that a newer build exists. How you
pull it in depends on how you installed.

### If you installed via the marketplace (recommended)

Two steps — refresh the catalog, then update the plugin:

```
/plugin marketplace update chat-timestamps      # 1. re-read marketplace.json from the repo
/plugin update chat-timestamps@chat-timestamps  # 2. fetch & switch to the new version
```

- **Step 1** re-fetches the marketplace definition from the GitHub repo, so
  Claude Code learns that a new version is available.
- **Step 2** downloads it and repoints the plugin at the new files. If you are
  already current, it reports *"already at the latest version"* and changes
  nothing.
- **Automatic:** Claude Code also checks for plugin updates at startup, so a
  simple restart usually pulls new versions for you. If an update arrives
  mid-session, run `/reload-plugins` to switch the commands and hooks over to
  it without restarting.

You can check what you have with `/plugin` (opens the plugin manager) or by
reading the `version` in `~/.claude/plugins/.../plugin.json`.

### If you installed manually (git clone)

Run the bundled helper — it is idempotent (clones if the folder is missing,
otherwise fetches and hard-resets to the latest release, so local cruft never
blocks the update):

```bash
bash ~/.claude/plugins/chat-timestamps/scripts/install.sh
```

Or do it by hand in a clean clone:

```bash
git -C ~/.claude/plugins/chat-timestamps pull --ff-only
```

Either way, restart Claude Code or run `/reload-plugins` afterwards so the new
version is loaded.

## Compatibility

- **macOS / Linux** — works out of the box.
- **Windows** — `/timestamps` auto-detects the right Python launcher (`python3`
  is often a non-functional Microsoft Store stub there, so it falls back to
  `py -3`). The optional **inline** and **time-aware** hooks need `bash` on
  `PATH` (Git Bash) and a recent Claude Code; inline rendering has been reported
  as unreliable in some Windows setups. The `/timestamps` timeline is the
  dependable surface everywhere.

## How it works

Claude Code records every turn — with a timestamp and the working directory — in
a local JSONL transcript under `~/.claude/projects/`. This plugin:

1. **Finds the right transcript** by matching the working directory stored
   *inside* the file — not by guessing the folder name, which breaks for paths
   containing spaces or dots.
2. **Streams it** (never loading it into the editor) and renders the timeline
   with day dividers and idle-gap markers.
3. For the optional hooks, uses Claude Code's documented `UserPromptSubmit`
   (adds context) and `MessageDisplay` (display-only) hook points.

Because the times come straight from the recorded data, they're accurate even
when a model-reported clock would drift.

## Troubleshooting

- **"No transcript found for this directory."** Run `/timestamps` from a folder
  with an active Claude Code session — the plugin locates the session by working
  directory.
- **`/timestamps` does nothing on Windows.** Make sure Python 3 is installed; the
  command uses the `py` launcher automatically. Verify with `py -3 --version`.
- **Inline timestamps don't appear.** Confirm they're on with `/timestamps
  inline`, and restart once after updating so the hook loads. They need a recent
  Claude Code and `bash` on `PATH`; if they don't render in your setup, the
  `/timestamps` timeline still works.

## Requirements

- Claude Code with plugin support
- Python 3 (pre-installed on macOS and most Linux; on Windows the `py` launcher
  is used automatically)

## Development

Plain Python with a stdlib-only test suite — no dependencies:

```bash
python3 -m unittest discover -s tests -v
# or:  ./tests/run.sh   (auto-detects the Python launcher)
```

## Background

Built in response to community requests for message timestamps in Claude Code:

- [#44763 — Show timestamps on conversation messages](https://github.com/anthropics/claude-code/issues/44763)
- [#2447](https://github.com/anthropics/claude-code/issues/2447) · [#30144](https://github.com/anthropics/claude-code/issues/30144) · [#31271](https://github.com/anthropics/claude-code/issues/31271)

If native timestamps ever land in Claude Code, this plugin won't be needed — and
that's a good thing.

## License

MIT © [s-a-s-k-i-a](https://github.com/s-a-s-k-i-a)
