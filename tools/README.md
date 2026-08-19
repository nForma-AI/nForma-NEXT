# Fleet instruments

Each built because a reading was believed and turned out to be wrong. ⚠ No count in this sentence on purpose: a hand-maintained integer describing a directory drifts on the next addition with no error, and three PRs were racing on it at once. The table below carries the count. Every one
carries the incident that produced it in its own docstring — the measurement is the
justification, not the description.

⚠ **Exit codes are load-bearing.** Every tool distinguishes *the answer is no* from *I
established nothing*. A run that establishes nothing exits **2** and must never be read as
"all clear". This is the single convention worth carrying to any other tool here.

| tool | question | exit codes |
|---|---|---|
| `fleet-context.py` | how much context does each agent have left? | 0 none due · 1 due · **2 scan established nothing** |
| `fleet-identity.py` | which role is this session, and which pane runs it? | 0 resolved · **2 population too small** · **2 own-session control failed** |
| `discriminates.py` | can this check tell the two states apart at all? | 0 discriminated · **2 non-discriminating, verdict refused** |
| `daintree-control.py` | is the fleet-status instrument answering, or blind? | 0 control passes · **2 VOID** |
| `wake-yield.py` | did that interruption produce work, or churn? | 0 |
| `pipe-exit-scan.py` | is any exit code here read through a pipe? | 0 clean · 1 findings · **2 established nothing** |

## What each one is for

**`fleet-context.py`** — reports per-session context depth so "compact this agent" and
"collect its friction report" are decisions made on a number rather than a proxy. Two roles
independently inferred a context state from a proxy and were wrong in the dangerous
direction: one read an empty input box as a completed compaction and re-tasked agents it
believed had headroom; one recommended compacting a session at 79% it had never measured.

⚠ Carries three hard-won behaviours: it sweeps **every** project directory (an agent in a
worktree gets its own, and a pane at 97.7% was missed by a single-directory scan); it treats
the fleet as a **declared** roster and demands a *distinct session per role*; and it flags
**`SHARED FILE`** when one transcript carries two interleaved agents, because a file is not
an agent.

**`fleet-identity.py`** — answers two joins, and they are not equally hard.

*Session → name and role* is **exact**: `~/.claude/sessions/<pid>.json` carries `sessionId`, which
IS the transcript filename. ⚠ This file previously said "there is no shared key" flatly. That is
true of `terminal.list` and false of the registry, and the over-broad claim was read as a property
of the system — one role rebuilt the name join by hand because this paragraph said it was
impossible. The registry also carries `nameSource`, the only field that separates a renamed session
from an auto-named one; ⛔ the predicate is **key absence**, never `== "user"`, and a checker
written against the value never fires.

*Session → pane* genuinely has no shared key and still joins on **content** — rare tokens from
recent output matched against pane scrollback. That path needs the Daintree MCP; without it the tool
falls back to the registry report and says `UNAVAILABLE` on stderr rather than printing an empty
table. ★ Its known-positive is by construction: the process runs inside a session, so that session
must appear in the join. Proven to discriminate — break the join and it exits **2** with zero rows,
rather than printing a clean-looking table of nothing.

**`discriminates.py`** — refuses a verdict when two states produce identical readings.
Built after `grep -c "46.6%"` returned `1` on both a worktree and `origin/main` and was read
as *"the states agree"*: the worktree was 163 commits behind and the figure had been
retracted, and **a retraction quotes the number it retracts.**

> Identical readings from a discriminator are an instrument failure, not evidence of sameness.

**`daintree-control.py`** — a known-positive control for the fleet-status instrument, so a
blind poller cannot log a quiet cycle that reads as a healthy fleet. ★ It terminates the
regress on something known **by construction**: at least one pane must report `working`,
because the agent running the check is one.

**`wake-yield.py`** — pairs an interruption's cost with its yield. Cost alone is
uninterpretable: an agent woken into useful work and one woken into churn consume context
identically.

**`pipe-exit-scan.py`** — finds `cmd | cmd; echo $?` and `${PIPESTATUS[n]}`, the shapes that
print something which looks like a measurement and is not. Replaces a written convention that
three roles missed.

⛔ It is its own hardest case, and the reason it is worth reading. A scanner for this is a
content matcher, and the document warning about the trap *contains the string*. Measured: the
only two occurrences of `PIPESTATUS` in this repository are in the paragraph below warning about
it, so a naive identifier scan reports **two findings here and both are false** — a 100%
false-positive rate on the live repo, in the direction that reads as work-to-do.

⇒ So it matches on what a **mention cannot produce**: prose lives in `.md` and a markdown file is
never executed (markdown is scanned only inside ```` ```bash ```` fences, never inline backticks);
a `#` comment inside a shell script is a mention where code is a use; and the finding is a
*pipeline whose status is read*, not the identifier alone. ★ The fleet has now solved this same
problem five times without naming it once — a nonce (citation cannot precede creation), line
position (a quotation cannot occupy a position), a path form (prose has no path separator), an
execution record (a description is not an effect), and here. **Match on something a mention
cannot produce.**

`--selftest` proves both directions against real data: the known-negative is this file, and the
known-positive is a fixture of three idioms taken from three real incidents rather than invented
to match the regex.

## Conventions worth copying

- **Exit 2 for "established nothing."** Absence of a finding and absence of a measurement are
  different states and must not share an exit code.
- **State the caveat on every run, not in the docs.** Each tool prints what its numbers do
  *not* establish, because a caveat that lives only in a README is read once.
- **Prove the failure path.** `daintree-control.py` takes a `DAINTREE_CFG` override purely so
  its VOID path can be exercised — a control that has only ever passed is not a control.
- **Roll the baseline forward.** A `--since` diff against a *fixed* snapshot re-reports the
  same event on every run. Measured: one compaction was reported as news four sweeps in a
  row, against a baseline 172 minutes old. **An alarm that fires forever on one event trains
  its reader to ignore it** — which is worse than not firing, because the reader also stops
  seeing the next one. Snapshot *after* reporting, so each run measures one interval.
- **A duplicate alarm and a broken alarm are indistinguishable to the reader.** Both produce
  output that is safe to skip. Treat repeat-firing as a defect with the same severity as
  silence.
- **Never read an exit code through a pipe.** ⇒ RETIRED AS PROSE, enforced by
  `tools/pipe-exit-scan.py`. It is kept as a one-line pointer rather than a rule because the
  prose form was measured not to work: three instances, in three roles, in four hours — and the
  third happened in a role that had been warned about it *in the same message that assigned the
  task*, against this very paragraph. ⛔ A rule that exists and does not fire is worse than no
  rule, because its presence is mistaken for coverage.

- **No secrets in source.** Tools needing the Daintree token read it from the user's own MCP
  config at runtime; it appears in none of these files.
