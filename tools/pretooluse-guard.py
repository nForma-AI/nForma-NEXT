#!/usr/bin/env python3
"""Idioms that produce a confident WRONG measurement, matched over a command string.

⛔ NOT INSTALLED, AND INSTALLING IT IS NOT A DEVOPS DECISION. This would run as a
`PreToolUse` hook on every Bash call for everyone in the repository. That is harness
configuration and it belongs to the operator — and `~/.claude/settings.json` already
carries a live PreToolUse chain, so an addition changes a running mechanism rather
than adding a new one. Nothing here wires anything.

⇒ SO WHY IS IT COMMITTED. `tools/pipe-exit-scan.py` cites *"matcher measured at 2.5%
fire / 80% precision"* and this file is what produced that. It lived in a scratchpad
with zero tracked copies — a number in a durable artifact whose instrument is one
session from gone, which this repository's own rule calls not existing.

⛔ AND COMMITTING IT IMMEDIATELY CORRECTED THE CITED NUMBER. `--measure` over the
whole fleet rather than one role's session:

    corpus                     1720 Bash invocations   (fleet)      204   (one role)
    as shipped                   25  1.5%                             5   2.5%

The 2.5% was ONE ROLE'S SESSION quoted without its denominator — a rumour on a
subject nobody named, by this repository's own definition, cited in a tool's
docstring by the author of the rule. Both figures are real and they answer
different questions; only the fleet one is a fleet rate.

⚠ `--measure` re-derives the FIRE RATE only. Precision was hand-classified once at
4 true / 1 false on 204 commands and is NOT reproducible here: deciding whether a
hit is a real defect needs a human reading the intent of the command.

THE SEVERITY SPLIT, which is the part that should drive warn-vs-block:

    LOST      the measurement is missing, and the output looks odd enough to question
    INVERTED  the measurement is REPLACED by a confident, plausible, actionable claim
              about the DOMAIN. `$P:tools/README.md` became `c29aa60ools/README.md`,
              git answered "unknown revision or path not in the working tree", and
              that reads as THE FILE IS NOT THERE. One role was a step from filing a
              closure verdict on it.

⚠ The INVERTED rule is the one worth having and the one with NO evidence: zero hits
in the measured corpus, so its false-positive rate is UNMEASURED rather than zero.
[NOT-YET-MEASURED]

⚠ And the HOOK MECHANISM is untested. This measures the MATCHER. Whether a hook
fires on the right event, receives the command string, and surfaces output an agent
reads is unestablished. [NOT-YET-MEASURED]

Exit: 0 clean · 1 would warn · 2 established nothing.
"""
import glob, json, os, re, sys

RULES = [
    ("pipestatus", "LOST", re.compile(r"\$\{PIPESTATUS\[")),
    # zsh history-modifier chars only. `$VAR:` before anything else is not this
    # defect, and matching every colon would drown the signal.
    ("zsh-var-modifier", "INVERTED",
     re.compile(r"\$[A-Za-z_][A-Za-z0-9_]*:[tshreglqxAa](?![A-Za-z0-9_])")),
]

HEREDOC = re.compile(r"<<-?\s*'?\"?([A-Za-z_][A-Za-z0-9_]*)'?\"?\n(.*?)^\1\s*$", re.S | re.M)
DOLLAR_Q = re.compile(r"\$\?")


def executable_part(cmd):
    """⛔ Strip heredoc BODIES. Measured on 204 real commands: the dominant false
    positive was a command WRITING DOCUMENTATION ABOUT the idiom — a README
    paragraph, a fixture, a commit message. A body is content; the shell around it
    is code."""
    return HEREDOC.sub("\n", cmd)


def pipeline_status_read(line):
    """Does `$?` here read the status of a PIPELINE?

    ⛔ Not *does the line contain a pipe and a `$?`*. Split on separators and ask
    whether the segment IMMEDIATELY BEFORE the read is piped. `cmd | display;
    cmd > /dev/null; echo $?` is the CORRECT idiom — run piped to look at it, re-run
    redirected to measure it — and a guard that fires on the correct form is the
    worst kind, because it interrupts an agent doing the right thing.
    """
    segs = re.split(r"(?<![|&])[;&](?![&|])|&&", line)
    for i, seg in enumerate(segs):
        if not DOLLAR_Q.search(seg):
            continue
        prev = next((s for s in reversed(segs[:i]) if s.strip()), "")
        if "|" in prev:
            return True
    return False


def check(cmd, strip=True):
    target = executable_part(cmd) if strip else cmd
    hits = [(n, sev) for n, sev, rx in RULES if rx.search(target)]
    if any(pipeline_status_read(l) for l in target.splitlines()):
        hits.insert(0, ("exit-after-pipe", "LOST"))
    return hits


def commands():
    """Every Bash invocation this fleet has recorded — the population the defect
    lives in. ⚠ Scoped to ~/.claude/projects, the fleet's record of its own work.
    Shell history and anything wider is a different instrument with consent
    questions that are not an agent's to settle."""
    out = []
    for proj in glob.glob(os.path.expanduser("~/.claude/projects/*")):
        for path in glob.glob(os.path.join(proj, "*.jsonl")):
            try:
                fh = open(path, errors="replace")
            except OSError:
                continue
            for line in fh:
                if '"tool_use"' not in line:
                    continue
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                for b in (rec.get("message") or {}).get("content") or []:
                    if (isinstance(b, dict) and b.get("type") == "tool_use"
                            and b.get("name") == "Bash"):
                        c = (b.get("input") or {}).get("command")
                        if c:
                            out.append(c)
    return out


def measure():
    cmds = commands()
    if not cmds:
        print("⛔ no Bash invocations found — ESTABLISHED NOTHING, not a clean rate.\n"
              "   ADDABLE — FIXABLE HERE: check ~/.claude/projects exists and holds "
              "transcripts.", file=sys.stderr)
        return 2
    naive = [c for c in cmds if check(c, strip=False)]
    fired = [c for c in cmds if check(c)]
    print(f"corpus                          {len(cmds)} Bash invocations")
    print(f"naive (no heredoc strip)        {len(naive):>4}  {100*len(naive)/len(cmds):.1f}%")
    print(f"as shipped                      {len(fired):>4}  {100*len(fired)/len(cmds):.1f}%")
    print("\n⚠ FIRE RATE, not precision. Precision was hand-classified once at "
          "4 true / 1 false on 204 commands; it is NOT re-derived here, because "
          "classifying a hit as true or false needs a human reading the intent.",
          file=sys.stderr)
    return 1 if fired else 0


def self_test():
    KP = 'python3 validate-recipe.py 2>&1 | tail -6; echo "exit=$?"'
    KN = 'python3 t.py 2>&1 | tail -4; python3 t.py >/dev/null 2>&1; echo "exit=$?"'
    KN2 = 'echo "the | cmd; echo $? shape"'
    kp, kn = bool(check(KP)), bool(check(KN))
    print(f"  known-positive  the founding incident        : {'fires' if kp else 'MISSED'}")
    print(f"  known-negative  the CORRECT re-run idiom     : {'silent' if not kn else 'FIRES — false positive'}")
    print(f"  known-positive  a string literal             : "
          f"{'fires (known FP, 1 of 5 measured)' if check(KN2) else 'silent'}")
    ok = kp and not kn
    print("\nselftest PASS" if ok else "\nselftest FAIL")
    return 0 if ok else 2


def main():
    if "--self-test" in sys.argv:
        return self_test()
    if "--measure" in sys.argv:
        return measure()
    hits = check(sys.stdin.read())
    for n, sev in hits:
        print(f"{sev}\t{n}")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
