---
description: Display a timestamped timeline of the current conversation
allowed-tools: Bash(python3:*), Bash(py:*), Bash(python:*)
argument-hint: [count] [seconds] [tools] | inline on|off
model: haiku
---

## Context

- Current working directory: !`pwd`
- Arguments: $ARGUMENTS

## Task

Show a timestamped timeline of the current Claude Code session. The parser
locates the session transcript itself (by matching the recorded working
directory), so you do **not** need to find or pass any transcript path.

### Step 0: Inline-timestamp toggle (only if the first argument is `inline`)

If `$ARGUMENTS` begins with the word `inline`, this is a toggle for the
experimental inline-timestamp feature (a dim `[HH:MM:SS]` shown live on each
assistant message). Run the toggle script with the rest of the arguments
(`on`, `off`, `toggle`, or nothing/`status`), show its output, and stop — do
not render the timeline:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/inline-toggle.py" on
```

(Use the same Python launcher fallback as Step 2.) Otherwise continue below.

### Step 1: Interpret arguments

Parse `$ARGUMENTS` into options for the parser:

- **count** — the first whole number, if any (e.g. `50`). Otherwise omit it (defaults to 20). Never pass a non-numeric value as the count.
- **`--seconds`** — add this flag if the arguments contain `seconds` or `sec` (shows `HH:MM:SS`).
- **`--tools`** — add this flag if the arguments contain `tools` or `tool` (includes tool-call lines, which are hidden by default).

### Step 2: Run the parser

Run the parser, passing `--cwd "$PWD"` plus the options from Step 1. Example for `/timestamps 50 seconds`:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/parse-transcript.py" 50 --seconds --cwd "$PWD"
```

**Python launcher fallback (important for cross-platform use):** run the command with `python3`. If that fails — on Windows `python3` is often a non-functional Microsoft Store stub that prints an install message and exits non-zero — retry the identical command with `py -3`, and if that also fails, with `python`. Use the first launcher that prints a timeline.

### Step 3: Present output

Show the parser's output verbatim inside a code block so the columns line up. Do not add commentary beyond the timeline.

### Constraints

- Never read the transcript with the Read tool — it can be very large; the parser streams it.
- Only ever pass a validated whole number as the count.
- The parser only reads files under `~/.claude/projects/` and sends nothing anywhere.
