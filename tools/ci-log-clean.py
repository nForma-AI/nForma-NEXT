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

Exit: 0 cleaned (or `--self-test` passed) · 1 a control failed
      · 2 established nothing (no discriminator, empty input, or a bad flag)
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


def self_test():
    """⛔ TWO-SIDED AND NAMED. Every fixture is a LITERAL, so the control survives a
    repair to `clean()` — and every case comes from a measurement recorded in this
    file's own docstring rather than from what the implementation happens to do.

    ★ Hermetic by construction: `clean()` is text-in/text-out, so this needs no log,
    no network and no `gh`. That is why this tool gets a control rather than a
    `# NO-SELF-TEST:` declaration — declaring an absence that is cheap to fill is
    dodging, not honesty."""
    ok = True

    def check(name, got, want):
        nonlocal ok
        good = got == want
        ok &= good
        print(f"  {'PASS' if good else 'FAIL'}  {name}: got {got!r}, want {want!r}")

    def cleaned(text):
        """⛔ A fixture that SHOULD clean but raises is a FAILED control, not a crash.
        Without this the sabotage path exits 1 from an unhandled ValueError — and a
        crash and a reported failure are the same exit code, which is #58's collision
        arriving inside the control itself. Measured: breaking CYAN_BOLD produced
        exit 1 with ZERO `FAIL` lines."""
        try:
            return clean(text)
        except ValueError as exc:
            check(f"clean() must not refuse this fixture ({exc.args[0][:38]}…)", False, True)
            return [], {"lines": 0, "dropped": 0, "marked": 0, "groups": 0}

    CB = "^[[36;1m"          # what `gh` actually emits — measured: 218 pairs, 0 real ESC
    ESCB = "\x1b[36;1m"     # a real ESC byte, the form a reader would guess

    print("⛔ the defect this exists for: an echoed script counted as output")
    log = "\n".join([
        f"{CB}grep -c FAILED $FAILED_FILES^[[0m",
        "0",
    ])
    out, st = cleaned(log)
    check("the echoed grep line is dropped", any("FAILED" in l for l in out), False)
    check("the real output survives", out, ["0"])
    check("it was the MARKER that fired", st["marked"], 1)

    print("★ and the known-NEGATIVE, without which over-stripping reads the same")
    real = "\n".join([f"{CB}pytest^[[0m", "3 FAILED"])
    out2, _ = cleaned(real)
    check("a REAL failure line is kept", out2, ["3 FAILED"])

    print("⛔ the escape is `^[` two chars, not ESC — both must match")
    out3, s3 = clean("\n".join([f"{ESCB}echo hi\x1b[0m", "hi"]))
    check("a real ESC byte also marks", s3["marked"], 1)
    check("and its output survives", out3, ["hi"])

    print("ENVELOPE fallback: group markers with no cyan-bold")
    env = "\n".join(["##[group]Run pytest", "shell: bash", "##[endgroup]", "3 FAILED"])
    out4, s4 = cleaned(env)
    check("group envelope drops the preamble", out4, ["3 FAILED"])
    check("it was the ENVELOPE that fired", (s4["marked"], s4["groups"]), (0, 1))

    print("⛔ refusals — a log with no discriminator must NOT pass through")
    for name, text in (("empty input", "   \n  "),
                       ("no discriminator", "3 FAILED\nsome output")):
        try:
            clean(text)
            check(f"{name} raises", False, True)
        except ValueError:
            check(f"{name} raises", True, True)

    print("surviving lines have ANSI removed")
    out5, _ = clean("\n".join([f"{CB}x^[[0m", "^[[31mred^[[0m"]))
    check("ANSI stripped from kept lines", out5, ["red"])

    print("\n" + ("all controls pass" if ok else "⛔ CONTROLS FAILED"))
    return 0 if ok else 1


def main():
    if "--self-test" in sys.argv:
        # ⛔ Dispatched BEFORE the stdin read, or `--self-test` blocks on a terminal.
        # ⚠ And a companion flag is still refused: measured across this repo, a
        # `--self-test` that ignores an unknown flag produces an exit 0 that cannot be
        # told from the flag being dropped (#591).
        _extra = [a for a in sys.argv[1:] if a != "--self-test"]
        if _extra:
            print(f"\u26d4 unrecognised argument(s) alongside --self-test: {_extra}",
                  file=sys.stderr)
            return 2
        return self_test()
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
