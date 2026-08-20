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

⛔ AND COMMITTING IT IMMEDIATELY CORRECTED THE CITED NUMBER. `--measure` over more
than one role's session:

    corpus                     1720 Bash invocations                204   (one role)
    as shipped                   25  1.5%                             5   2.5%

The 2.5% was ONE ROLE'S SESSION quoted without its denominator — a rumour on a
subject nobody named, by this repository's own definition, cited in a tool's
docstring by the author of the rule.

⛔ AND THE REPLACEMENT WAS MIS-DENOMINATED TOO, IN THE OTHER DIRECTION. `--measure`
scanned EVERY project directory under ~/.claude/projects — every repository this
machine has ever worked on — while the docstring called it "the fleet". Measured
2026-08-20:

    scope                                corpus      fires    rate
    every project on the machine        179,216        956    0.53%
    this fleet's project dir             28,008        166    0.59%
    ⤷ largest single contributor is an UNRELATED project at 19.6% of the corpus;
      the fleet held 14.3% of the number that was published as the fleet's.

⚠ And the cited 1,720 does not reproduce: the same command reports 179,216 today.
A number a docstring attributes to its own tool, which the tool no longer produces,
is exactly the thing this file was committed to prevent.

★ So `--measure` now takes `--project SUBSTR` and ALWAYS prints its scope, the
project count, and the largest contributor's share. A fire rate is meaningless
without the population it was taken over, and this corpus GROWS — quote the corpus
size and the date beside any rate taken from it, or it decays into a rumour the way
the two above did.

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

⛔ THE INVERTED RULE WAS UNFIREABLE, AND ITS "no evidence" WAS THE PROOF. This
docstring used to read: *"the one worth having and the one with NO evidence: zero
hits in the measured corpus, so its false-positive rate is UNMEASURED rather than
zero."* The zero was not scarcity. Its lookahead was **backwards** — it required the
modifier char NOT to be followed by a word character, which is the DELIBERATE form
(`$file:t`) and excludes the accident (`$P:tools/...`, where `:t` swallows the rest).

Ground truth, run against zsh rather than reasoned about:

    $P:tools/README.md  -> abc123ools/README.md   MANGLED    rule was SILENT
    $IMAGE:tag          -> imgag                  MANGLED    rule was SILENT
    $file:t             -> c.txt                  INTENDED   rule FIRED
    $V:h/sub            -> /a/b/sub               INTENDED   rule FIRED

⇒ It fired on correct usage and stayed silent on silent corruption — including the
exact example three paragraphs above, which it was written for. Corrected 2026-08-20:

    scope                     corpus     INVERTED old   new
    this fleet                28,025            2        27
    every project             179,240           2       105

★ **105 real instances were sitting in the corpus the rule was measured against.**
`git show $B:e2e/lib/failure_classifier.py` and its siblings, exactly the founding
shape. "No hits, so the false-positive rate is unmeasured" and "no hits, because the
rule cannot match the defect" produce the same line in a report and demand opposite
work. ⚠ Its false-positive rate is now measurable and still UNMEASURED — 105 hits
have not been hand-classified. [NOT-YET-MEASURED]

⚠ And the HOOK MECHANISM is untested. This measures the MATCHER. Whether a hook
fires on the right event, receives the command string, and surfaces output an agent
reads is unestablished. [NOT-YET-MEASURED]

Exit: 0 clean · 1 would warn · 2 established nothing.
"""
import glob, json, os, re, sys

RULES = [
    ("pipestatus", "LOST", re.compile(r"\$\{PIPESTATUS\[")),
    # ⛔ THE LOOKAHEAD WAS BACKWARDS, and it made this rule unfireable on the very
    # incident the docstring cites. Ground truth, run against zsh:
    #
    #   $P:tools/README.md   -> abc123ools/README.md   MANGLED   was: silent
    #   $IMAGE:tag           -> imgag                  MANGLED   was: silent
    #   $file:t              -> c.txt                  INTENDED  was: FIRED
    #   $V:h/sub             -> /a/b/sub               INTENDED  was: FIRED
    #
    # The old form required the modifier char NOT to be followed by a word
    # character — which is the DELIBERATE use (`:t` at a word boundary) and
    # excludes the accident (`:t` swallowing the text after it). It fired on
    # correct usage and stayed silent on silent corruption.
    #
    # ⚠ And that inversion is why the docstring reports "zero hits in the measured
    # corpus" for this rule. It read that as *the defect is rare, so the
    # false-positive rate is unmeasured*. The actual reason is that the rule COULD
    # NOT MATCH the defect — an unfireable rule reported as an unproven one.
    ("zsh-var-modifier", "INVERTED",
     re.compile(r"\$[A-Za-z_][A-Za-z0-9_]*:[tshreglqxAa](?=[A-Za-z0-9_])")),
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


def commands(project=None):
    """Bash invocations recorded under ~/.claude/projects, optionally scoped.

    ⛔ This is NOT "the fleet's record of its own work", which is what the docstring
    used to claim. ~/.claude/projects holds every repository this machine has ever
    worked on — measured 2026-08-20: 50 project dirs, 6,364 transcripts, and the
    single largest contributor was an unrelated project at 19.6% of all commands
    while this fleet held 14.3%.

    `project` is a substring matched against the project directory name. Returns
    (commands, projects_included, per_project_counts) so the caller can print the
    population rather than implying one.

    ⚠ Shell history and anything wider is a different instrument, with consent
    questions that are not an agent's to settle.
    """
    out = []
    per = {}
    for proj in glob.glob(os.path.expanduser("~/.claude/projects/*")):
        base = os.path.basename(proj)
        if project and project not in base:
            continue
        before = len(out)
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
        if len(out) > before:
            per[base] = len(out) - before
    return out, per


def measure(project=None):
    cmds, per = commands(project)
    if not cmds:
        where = f"matching {project!r}" if project else "under ~/.claude/projects"
        print(f"⛔ no Bash invocations found {where} — ESTABLISHED NOTHING, not a clean "
              f"rate.\n   ADDABLE — FIXABLE HERE: check the path exists and holds "
              f"transcripts, and that --project is not filtering everything out.",
              file=sys.stderr)
        return 2
    naive = [c for c in cmds if check(c, strip=False)]
    fired = [c for c in cmds if check(c)]
    # ⛔ Print the population. A rate whose denominator is implied is the defect
    # this file's own docstring was written to correct, twice.
    top = max(per.items(), key=lambda kv: kv[1]) if per else ("-", 0)
    print(f"scope                           {project or 'ALL PROJECTS on this machine'}")
    print(f"project dirs included           {len(per)}")
    print(f"largest single contributor      {top[1]}  {100*top[1]/len(cmds):.1f}%  {top[0][-44:]}")
    print(f"corpus                          {len(cmds)} Bash invocations")
    print(f"naive (no heredoc strip)        {len(naive):>4}  {100*len(naive)/len(cmds):.2f}%")
    print(f"as shipped                      {len(fired):>4}  {100*len(fired)/len(cmds):.2f}%")
    if not project and len(per) > 1:
        print(f"\n⚠ UNSCOPED — this is every repository this machine has worked on, not "
              f"this fleet. {len(per)} project dirs. Pass --project SUBSTR to scope it, "
              f"and quote the corpus size and date beside any rate taken from it: this "
              f"corpus grows, so an undated rate decays into a rumour.", file=sys.stderr)
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
        project = None
        if "--project" in sys.argv:
            i = sys.argv.index("--project")
            if i + 1 >= len(sys.argv):
                print("⛔ --project needs a value", file=sys.stderr)
                return 2
            project = sys.argv[i + 1]
        return measure(project)
    hits = check(sys.stdin.read())
    for n, sev in hits:
        print(f"{sev}\t{n}")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
