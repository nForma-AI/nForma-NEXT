#!/usr/bin/env python3
r"""Strip the echoed `run:` block from a CI job log — BEFORE anything strips ANSI.

⛔ THE DEFECT, measured. GitHub echoes the `run:` block itself into the job log,
cyan-bold, before the command's output. So the log contains the text of the grep you
are about to run:

    grep -c FAILED  <a real A2 job log>   ->  4
    that job's conclusion                 ->  SUCCESS

All four hits were the echoed script, which declares `FAILED_FILES`. The command's
real output contained zero.

★ AND THE ORDER CANNOT BE REVERSED. The cyan-bold escape is the ONLY thing that
distinguishes the echoed block from real output — the words are identical. Strip ANSI
first and the discriminator is gone irrecoverably; no later pass can recover it. The
agent who found this had already written its reader the other way round.

⛔ AND THE ESCAPE IS NOT WHAT YOU EXPECT. Measured on a real 153 KB log from
`gh run view --log`, 1,137 lines:

    real \x1b bytes            0
    literal `^[` two-char pairs  218   <- `^` then `[`, not ESC
    `##[group]Run ` markers      10

⇒ `gh` renders the escape as the literal characters `^[`. A reader stripping
`\x1b\[[0-9;]*m` removes NOTHING and believes it has cleaned the log. Both forms are
handled here.

TWO DISCRIMINATORS, and the fallback matters:

    1. MARKER    each echoed line carries `[36;1m` … `[0m`. Precise, and the one
                 that dies if ANSI is stripped first.
    2. ENVELOPE  the block sits between `##[group]Run ` and `##[endgroup]`. Survives
                 an ANSI strip, but `--log-failed` and some fetch paths omit group
                 markers entirely.

⛔ IF NEITHER IS PRESENT THIS REFUSES (exit 2) rather than passing the log through.
A log with no discriminator cannot be cleaned, and handing it back unchanged is how a
count of the script becomes a count of the output.

Usage:
    gh run view <id> --log | python3 tools/ci-log-clean.py
    gh run view <id> --log | python3 tools/ci-log-clean.py --stats

Exit: 0 cleaned · 2 established nothing (no discriminator, or empty input)
"""
import re
import sys

# `^[` as two literal characters, or a real ESC byte. Measured: gh emits the first.
ESC = r"(?:\x1b|\^\[)"
CYAN_BOLD = re.compile(ESC + r"\[36;1m")
ANSI = re.compile(ESC + r"\[[0-9;]*m")
GROUP_RUN = re.compile(r"##\[group\]Run ")
GROUP_END = re.compile(r"##\[endgroup\]")


def clean(text):
    """Returns (cleaned_lines, stats). Raises ValueError when nothing discriminates."""
    lines = text.split("\n")
    marked = sum(1 for l in lines if CYAN_BOLD.search(l))
    groups = sum(1 for l in lines if GROUP_RUN.search(l))

    if not text.strip():
        raise ValueError("empty input — nothing was read, which is not a clean log")
    if marked == 0 and groups == 0:
        raise ValueError(
            "no echoed-script discriminator found: 0 cyan-bold markers and 0 "
            "`##[group]Run` envelopes. Either this log has no `run:` steps, or "
            "something already stripped ANSI and destroyed the marker. Refusing to "
            "return it unchanged — a count taken from it may be counting the script."
        )

    out, dropped, in_group = [], 0, False
    for line in lines:
        if GROUP_RUN.search(line):
            in_group = True
            dropped += 1
            continue
        if in_group and GROUP_END.search(line):
            in_group = False
            dropped += 1
            continue
        # The marker wins where present: inside a group, the `shell:`/`env:` preamble
        # is not the script but is equally not the command's output.
        if CYAN_BOLD.search(line) or in_group:
            dropped += 1
            continue
        out.append(ANSI.sub("", line))

    return out, {"lines": len(lines), "dropped": dropped, "marked": marked, "groups": groups}


def main():
    text = sys.stdin.read()
    try:
        out, stats = clean(text)
    except ValueError as exc:
        print(f"⛔ VOID: {exc}", file=sys.stderr)
        return 2
    sys.stdout.write("\n".join(out))
    if "--stats" in sys.argv:
        print(
            f"\nci-log-clean: {stats['lines']} lines in, {stats['dropped']} dropped "
            f"({stats['marked']} cyan-bold marked, {stats['groups']} run-groups), "
            f"{len(out)} out",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
