---
description: Display timestamps for messages in the current conversation
allowed-tools: Bash(python3:*), Bash(ls:*)
argument-hint: [count]
model: haiku
---

## Context

- Current working directory: !`pwd`
- Arguments: $ARGUMENTS

## Task

Display a timestamped timeline of messages from the current conversation transcript.

### Step 1: Find the transcript

Run this to locate the most recent transcript JSONL file for the current project:

```bash
PROJECT_KEY=$(pwd | sed 's|/|-|g; s|^|-|')
ls -t "$HOME/.claude/projects/${PROJECT_KEY}/"*.jsonl 2>/dev/null | head -1
```

If no file is found, report to the user: "No transcript found for this project directory. This command must be run from a directory with an active Claude Code session."

Do not proceed further if no transcript is found.

### Step 2: Parse and display

Extract the count from `$ARGUMENTS`. If it is a positive integer, use it. Otherwise default to 20. Reject any non-numeric value — do not pass arbitrary strings to the script.

Run the parser script, passing the transcript path and count as arguments:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/parse-transcript.py" "<transcript_path>" "<count>"
```

Replace `<transcript_path>` with the actual path found in step 1, and `<count>` with the validated integer.

### Step 3: Present output

Display the script output in a code block so columns align. Do not add commentary beyond the timeline.

### Constraints

- Never read the transcript with the Read tool — files can be very large.
- Only pass validated integers as the count argument.
- Only pass file paths that match the pattern `~/.claude/projects/*/*.jsonl`.
