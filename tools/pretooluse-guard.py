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

    # ── Converted from friction reports #1263 / #1268 / #1269, 2026-08-20 ──────────
    #
    # ⛔ WHY THESE ARE RULES AND NOT ANOTHER REPORT. #1263 §7: "A recorded lesson does
    # not fire at the moment of the mistake. Only a mechanical check does." Its author
    # had re-committed two of its own written-down lessons *after* writing them down.
    # Every rule below is a habit some agent adopted privately, never filed, and paid
    # for at least once. The count in each comment is INDEPENDENT reporters, and it is
    # the reason to trust the rule over its false-positive cost.
    #
    # ★ Each carries a known-positive and a known-negative in self_test(). A rule that
    # fires on the correct form is the worst kind — this file already shipped one.

    # 3 reporters (DEV4 §1d, DEV5, ARCHITECT §1.10). Two-dot against a behind-branch
    # renders main's commits as DELETIONS, so a merge reads as a revert. The negative
    # is the three-dot form, which must stay silent — hence the (?!\.) lookahead.
    # ⛔ THE FIRST VERSION OF THIS RULE FIRED ON THE THREE-DOT FORM — i.e. on the
    # CORRECT usage — because `.` was inside the left character class, so it matched
    # from the first dot of `...` onward and the (?!\.) lookahead never saw it. That
    # is the same inversion documented for `zsh-var-modifier` twenty lines above, in
    # the same file, committed while reading it. Caught by the known-NEGATIVE, which
    # is the entire reason every converted rule ships with one.
    ("two-dot-diff", "INVERTS",
     re.compile(r"git\s+diff\s[^|;&\n]*?[A-Za-z0-9_/-]\.\.(?!\.)[A-Za-z0-9_/-]")),

    # 2 reporters (DEV5 §1.4, ARCHITECT §1.1). Without the flag the command writes an
    # EMPTY FILE and exits 1 — ARCHITECT read seven 0-byte files as "the logs do not
    # exist". The failure is indistinguishable from absence.
    ("gh-logs-no-escape", "EMPTY-READS-AS-ABSENT",
     re.compile(r"gh\s+api\s+(?![^|;&\n]*--allow-escape-sequences)[^|;&\n]*/logs\b")),

    # 2 reporters (DEV5 §1.2, DEV4 §1f). zsh expands an unquoted glob against the CWD
    # before grep sees it. DEV5 measured 0 call sites where the true count was 112.
    ("unquoted-glob-arg", "SILENT-ZERO",
     re.compile(r"--include=(?![\"'])\S*[*?]")),

    # DEV5 §1.1: zsh does NOT word-split an unquoted var, so `for b in $BRANCHES`
    # passes 12 names as ONE argument. Cost: two published-then-retracted findings.
    # The negative is any quoted/expanded form — $(...), "${a[@]}", a literal list.
    ("zsh-for-unsplit", "ONE-ARG",
     re.compile(r"\bfor\s+\w+\s+in\s+\$[A-Za-z_][A-Za-z0-9_]*\s*(?:;|\n|$)")),

    # ARCHITECT §1.2: `git grep -E` does not support \b. A repo-wide sweep returned
    # ZERO while `git grep -c` on one file returned 7. Silent zero, no error.
    ("git-grep-word-boundary", "SILENT-ZERO",
     re.compile(r"git\s+grep\s[^|;&\n]*\\b")),

    # DEV5 §1.3 — its own "if you act on one line". `git archive` archives the COMMIT,
    # not the worktree, so verifying an UNCOMMITTED fix tests the OLD code; and it
    # omits .git, which produced 252 suite failures against a 253 control on pristine
    # main. Both failures read as "your change broke it".
    ("git-archive-tree", "STALE-TREE",
     re.compile(r"\bgit\s+archive\b")),
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

    # ⛔ PER-RULE, because an aggregate cannot answer the only question that decides
    # whether a rule ships: does THIS rule earn its interruptions? A pooled 2.47% hides
    # both a rule that never fires (unfireable, like `zsh-var-modifier` was) and one
    # firing on half the corpus. I needed this breakdown the moment I added six rules
    # and had to compute it outside the tool, which is the definition of a missing view.
    per_rule = {}
    for c in cmds:
        for name, _sev in check(c):
            per_rule[name] = per_rule.get(name, 0) + 1
    print(f"\n{'rule':<26}{'hits':>7}{'rate':>9}")
    for name, n in sorted(per_rule.items(), key=lambda kv: -kv[1]):
        print(f"{name:<26}{n:>7}{100*n/len(cmds):>8.2f}%")
    silent = [n for n, _s, _r in RULES if n not in per_rule]
    if silent:
        print(f"\n⚠ {len(silent)} rule(s) fired ZERO times here: {', '.join(silent)}.\n"
              "   A zero is NOT evidence the defect is rare — it is equally the "
              "signature of a rule that CANNOT match, which is what `zsh-var-modifier` "
              "turned out to be. Check the known-positive in --self-test before "
              "reading a zero as good news.")
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


def hook_status():
    """Is this guard wired into anything that would RUN it?

    ⛔ Converted from ARCHITECT's #1269 §4, which is about this exact tool's category:

        "A gate that never refuses looks identical to one that does not exist.
         It has now refused twice, which is the ONLY reason I know it works.
         Before that I was reporting 'scan clean' as evidence, and it was
         evidence of nothing."

    ★ So the tool now answers that question about ITSELF, mechanically, instead of
    leaving a reader to assume that a file named `pretooluse-guard` is wired to
    PreToolUse. Measured 2026-08-20: it was not, in any settings file on this
    machine — a guard exhibiting the defect it was written to catch.

    ⚠ This reports; it does not wire anything. Adding a hook changes how every
    session on this machine runs commands, which is an operator decision and not an
    agent's — and specifically not one a peer can grant.

    Returns (wired, files_checked, where).
    """
    where, checked = [], []
    candidates = [
        os.path.expanduser("~/.claude/settings.json"),
        os.path.expanduser("~/.claude/settings.local.json"),
        os.path.join(os.getcwd(), ".claude", "settings.json"),
        os.path.join(os.getcwd(), ".claude", "settings.local.json"),
    ]
    for c in candidates:
        if not os.path.exists(c):
            continue
        checked.append(c)
        try:
            raw = open(c, errors="replace").read()
        except OSError:
            continue
        if "pretooluse-guard" in raw:
            where.append(c)
    return bool(where), checked, where


def enforcement_banner(stream=sys.stderr):
    """Print the standing of any reading this tool produces. Never silent."""
    wired, checked, where = hook_status()
    if not checked:
        print("⚠ ENFORCEMENT UNKNOWN — no settings file was readable, so this "
              "establishes nothing about whether the guard runs.", file=stream)
        return None
    if wired:
        print(f"✓ WIRED — referenced in {', '.join(where)}. A clean scan below is "
              "evidence that the guard ran and refused nothing.", file=stream)
        return True
    print("⛔ NOT WIRED — no PreToolUse hook in "
          f"{len(checked)} settings file(s) references this guard, so IT NEVER RUNS "
          "BEFORE A COMMAND.\n"
          "   ⇒ Every rule below is a rule ON PAPER. A clean scan is evidence of "
          "nothing, exactly as ARCHITECT measured for its own gate (#1269 §4).\n"
          "   ⚠ Wiring it changes how every session on this machine runs commands. "
          "That is an operator decision; this tool will not make it.", file=stream)
    return False


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

    # ⛔ EVERY CONVERTED RULE CARRIES BOTH DIRECTIONS. A rule proven only to fire is
    # half-tested, and the half that goes untested is the one this file got wrong
    # before: `zsh-var-modifier` fired on the DELIBERATE use and stayed silent on the
    # accident, and its zero-hit count was read as "rare" rather than "unfireable".
    PAIRS = [
        ("two-dot-diff",
         "git diff main..HEAD -- goals/",
         "git diff main...HEAD -- goals/"),
        ("gh-logs-no-escape",
         "gh api repos/o/r/actions/jobs/123/logs > /tmp/j.log",
         "gh api --allow-escape-sequences repos/o/r/actions/jobs/123/logs > /tmp/j.log"),
        ("unquoted-glob-arg",
         "grep -rn foo --include=*.py .",
         "grep -rn foo --include='*.py' ."),
        ("zsh-for-unsplit",
         "for b in $BRANCHES; do echo $b; done",
         'for b in "${BRANCHES[@]}"; do echo $b; done'),
        ("git-grep-word-boundary",
         r"git grep -E '\bassert_called\b' -- '*.py'",
         "git grep -E 'assert_called' -- '*.py'"),
        ("git-archive-tree",
         "git archive HEAD | tar -x -C /tmp/iso && cd /tmp/iso && pytest",
         "git worktree add --detach /tmp/iso HEAD && cd /tmp/iso && pytest"),
    ]
    print()
    for name, pos, neg in PAIRS:
        fires = name in [h for h, _ in check(pos)]
        quiet = name not in [h for h, _ in check(neg)]
        status = "ok  " if (fires and quiet) else "FAIL"
        print(f"  {status} {name:<24} positive={'fires' if fires else 'MISSED'} "
              f"negative={'silent' if quiet else 'FIRES — would interrupt correct work'}")
        ok = ok and fires and quiet

    print("\nselftest PASS" if ok else "\nselftest FAIL")
    return 0 if ok else 2


def main():
    if "--enforcement" in sys.argv:
        wired = enforcement_banner(sys.stdout)
        return 0 if wired else (1 if wired is False else 2)
    if "--self-test" in sys.argv:
        # ⛔ Standing FIRST. A passing self-test says the rules discriminate; it says
        # nothing about whether anything invokes them, and the two are routinely
        # conflated — that conflation is what #1269 §4 is about.
        enforcement_banner()
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
