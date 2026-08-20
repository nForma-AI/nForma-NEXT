# Fleet instruments

Each built because a reading was believed and turned out to be wrong. ⚠ **No count in this
sentence on purpose:** a hand-maintained integer describing a directory drifts on the next
addition with no error, and three PRs were racing on it at once. **The table below carries the
count**, and `scripts/check-tools-index.py` derives it from `ls` — ⚠ **when someone runs it.**
Nothing invokes it: there is no `.github/`, no hook, and `fleet-preflight.sh` does not call it.
So #27's defect is **mitigated, not prevented** — add a thirteenth tool with no row and nothing
fires until a human asks. Stated rather than implied, because *"asserts it matches `ls` on every
run"* — the wording that stood here — reads as coverage to a future maintainer and there is no
*every run*. Every one carries the incident that produced it in its own docstring — the
measurement is the justification, not the description.

⚠ **Exit codes are load-bearing.** Every tool distinguishes *the answer is no* from *I
established nothing*. A run that establishes nothing exits **2** and must never be read as
"all clear". This is the single convention worth carrying to any other tool here.

⛔ **AND THE CONVENTION DOES NOT OWN THE NUMBER.** #58: `2` is also what the Python runtime
emits for a file it cannot open, and what argparse emits for an argument it will not accept.
`1` is also Python's uncaught-exception code, colliding with *finding*. ⇒ **The rule as
originally written — "exit 2 must never be read as all clear" — is correct and unenforceable
by the caller alone**, because two of the three producers of `2` are outside any tool's
control.

⇒ **So a CALLER must resolve `2` into a third outcome, not fold it into either of the other
two.** Both available two-way readings are wrong:

```
2 read as PASS  ->  converts "I established nothing" into "all clear"      <- the defect itself
2 read as FAIL  ->  operationally safe, epistemically FALSE: reports a DEFECT where there
                    was a REFUSAL, and a reader fixes a test that was never broken
```

★ **Fail-closed-and-wrong is the more dangerous pair, because nobody challenges a gate that
erred toward caution.** ⇒ `scripts/gate-suites.sh` is the reference implementation: it emits
`PASSED` · `FAILED` · `UNESTABLISHED`, **blocks on all of `1` and `2`**, and says something
different about each. Its own exit obeys the same convention it enforces — `1` for a finding,
`2` when nothing failed but something never spoke, and `2` when the population was empty.

⚠ **What no caller can currently separate**, stated because it is demonstrated by a control
rather than argued: *our* `2` from the *runtime's* `2`. ARCHITECT's Tier 1 remedy on #58 — a
start marker emitted **before** argument parsing, whose absence proves the tool never ran — is
the only thing that does, and it is not available at the suite level: measured 2026-08-20,
**2 of 30 `tools/test_*.py` files touch `runmarker` at all.** A gate cannot read a marker 28 of
its subjects do not emit.

⛔ **A MARKER-CARRYING TOOL CANNOT BE PINNED AS A SINGLE FILE**, and the fleet's pinning practice
does exactly that. Measured 2026-08-20: **8 of 26 instruments** `import runmarker`, so

```
git show <ref>:tools/x.py > /tmp/x.py && python3 /tmp/x.py
    -> exit 1, ImportError, ZERO markers        <- the tool never ran
```

⚠ The pin idiom exists for a real reason — the shared tree runs dozens of commits behind and nine
panes share it, so reading a tool from it reads someone else's branch. ⇒ The fix is to pin the
**directory**, not the file:

```
git archive <ref> tools/ | tar -x -C /tmp/pin   &&  python3 /tmp/pin/tools/x.py     ✅ markers emit
git show <ref>:tools/x.py + tools/runmarker.py  &&  python3 /tmp/pin2/x.py          ✅ markers emit
```

★ **The convention diagnoses its own pin.** A pinned tool that emits no `NFORMA-RUN` line was
pinned wrong — the absent marker means *never reached our code*, which is exactly what an
ImportError is. ⇒ You do not need to know about this rule to catch it; you need to read stderr.

⚠ Adoption is spreading beyond the tools that introduced it — `pipe-exit-scan`, `pretooluse-guard`,
`stranded-branches` and `transition-report` all import it now, none of them written by the author of
the markers. **The breakage grows with adoption**, which is the argument for stating it here rather
than in the two docstrings that started it.

⛔ **The convention collides with the interpreter, and you must check for it before trusting a
`2`.** `python3 tools/<x>.py` exits **2** when the file **does not exist** — that is Python's own
code for "cannot open". So an exit 2 read alone cannot separate *this tool established nothing*
from *this tool was never here*. Measured: a role ran `grant-check.py` against a ref where it had
not yet merged, got `2`, and nearly recorded "VOIDs correctly per convention".

⇒ ⛔ **THE REMEDY: two stderr markers, and they survive a pipe.** `tools/runmarker.py`. The exit
code stays as it is; it stops being the sole carrier.

```
NFORMA-RUN <tool>          emitted BEFORE argument parsing, as the first action
NFORMA-RESULT <state>      emitted on every path the tool controls
```

★ **Why stderr is the whole design.** `cmd | head` consumes **stdout** — stderr is not piped and
arrives intact, so it survives exactly the construct that destroys the exit code. It also keeps
data-producing tools honest: `ci-log-clean.py` emits a cleaned log on stdout, and a marker
injected there would corrupt the artifact it exists to produce.

⇒ **Three states from two markers, and the three producers of `2` finally separate.** Measured by
execution — `tools/test_runmarker.py`:

```
exit 2   RUN + RESULT: ESTABLISHED-NOTHING   the convention
exit 2   RUN + RESULT: BAD-ARGS              argparse rejected the arguments
exit 2   (no markers at all)                 the runtime refused the file
exit 1   RUN, no RESULT                      started and DIED PART-WAY
exit 0   RUN + RESULT: OK                    a controlled conclusion
```

⛔ **Emitting `RUN` before argument parsing is the load-bearing detail** — it is what separates *the
runtime refused the file* from *the tool rejected your flags*, two things byte-identical at exit 2
until now. And `RUN` without `RESULT` expresses **started and died**, a state the exit code cannot
carry at all.

⚠ **Two bounds, both asserted in the test rather than promised here.** A crash during **import**
emits nothing — identical to a refused file, because `begin()` has not run yet; both are correctly
*never reached our code*, and stderr's first line (`Traceback` vs `can't open file`) is what
separates them. And this **does not make the exit code correct**: a caller who reads neither the
code nor stderr is unchanged. It removes the exit code's monopoly; it does not remove the need to
look.

⇒ **Reference implementations:** `grant-check.py`, `pane-binding.py`. ⚠ Rollout across the rest is
DEVOPS's, per #58 — a convention demonstrated on two tools by its proposer is worth less than one
landed across the set.

⚠ **The older stopgap still holds where markers are absent:** the *first line of stderr* separates
runtime from convention on nonzero exits, measured 6/6. ⛔ Note the `1` row — the crash path is
loud and the legitimate path is **silent**, so a caller reading only the code logs a crash as a
finding; `doctrine-version.py` did exactly that on a missing `import re`. **Establish the tool
exists before believing what its exit code means.** ⚠ This is a property of every tool in this table,

not of any one
of them, which is why it is stated here rather than in a docstring.

| tool | question | exit codes |
|---|---|---|
| `fleet-context.py` | how much context does each agent have left? | 0 none due · 1 due · **2 scan established nothing** · `--self-test` |
| `fleet-identity.py` | which role is this session, and which pane runs it? | 0 resolved · **2 population too small** · **2 own-session control failed** |
| `discriminates.py` | can this check tell the two states apart at all? | 0 discriminated · **2 non-discriminating, verdict refused** |
| `daintree-control.py` | is the fleet-status instrument answering, or blind? | 0 control passes · **2 VOID** |
| `doctrine-watch.py` | which roles' doctrine moved under them, and who has not read it? | 0 nothing to tell · 1 a role is behind · **2 established nothing** |
| `label-exists.py` | does the label you are about to query actually exist? | 0 all exist · 1 one is absent · **2 established nothing** |
| `verdict-census.py` | has each indexed instrument ever produced a verdict? | 0 all classified · 1 a never-run, slow, or undocumented instrument · **2 established nothing** |
| `wake-yield.py` | did that interruption produce work, or churn? | 0 |
| `estate-provenance.py` | does the evidence place this file in THIS estate? | 0 no FOREIGN rows · 1 FOREIGN found · **2 established nothing** |
| `pipe-exit-scan.py` | is any exit code read through a pipe — in files, or in what agents actually ran? | 0 clean · 1 findings · **2 established nothing** · **3 control failed** |
| `fleet-state.py` | what did each agent DECLARE its state to be? | 0 read cleanly · **2 the parser established nothing** |
| `issue-coverage.py` | which open issues has NOBODY opened? | 0 all covered · 1 untouched found · **2 established nothing (empty board, failed query, or no transcripts)** |
| `prompt-delivery.py` | did a role prompt REACH a pane — and by which channel? | 0 measured · **2 no transcript held a launch prompt** |
| `text-provenance.py` | which session first PRODUCED this text — or is every hit my own reading? | 0 attributed · 1 present, unauthored here · **2 established nothing** · **3 own-reading only, verdict refused** |
| `text-provenance.py` | which session first PRODUCED this text — or is every hit my own reading, or my own probe? | 0 attributed · 1 present, unauthored here · **2 established nothing** · **3 own-reading only, verdict refused** |
| `text-provenance.py` | which session first PRODUCED this text — or is every hit my own reading, or my own probe? | 0 attributed · 1 present, unauthored here · **2 established nothing** · **3 own-reading only, verdict refused** · **4 an unclassified path — decide** · `--audit` |
| `pr-stack.py` | which open PRs must be stacked, and which are stale against main? | 0 independent · 1 conflicts, stale, or unresolved heads · **2 established nothing** |
| `api-budget.py` | who is spending the shared GitHub quota? | 0 pool has room · 1 EXHAUSTED · **2 established nothing** |
| `transition-report.py` | did the fleet ANNOUNCE its transitions, or only declare them? | 0 audited · **2 the control failed** |
| `bootstrap-audit.py` | did the pane EXECUTE its bootstrap, or only declare it? | 0 clean · 1 negative · **2 unauditable** · **3 known-positive failed** |
| `doctrine-version.py` | which version of its role prompt is each agent running? | 0 every resolvable transcript current · 1 currency **UNPROVEN** for at least one (`LAUNCH-ONLY` or `SAW-LATER`) — ⚠ **not "stale"** · **2 established nothing** · ⇒ `--states` emits the list |
| `pane-binding.py` | which panes join to a session, and which leg is missing? | 0 reported · **2 established nothing** |
| `index-watch.py` | did the tools index drift when `main` last moved? | 0 quiet · 1 finding · **2 established nothing** |
| `stranded-branches.py` | has any merged PR's branch got commits with no equivalent change upstream — and if so, are its bytes upstream anyway? | 0 none · 1 unmatched commits · **2 established nothing** |
| `grant-check.py` | is this role authorized to do this, right now? | 0 live grant · 1 **no live grant (established)** · **2 established nothing** · 3 self-test failed |
| `readd-scan.py` | is this diff RESTORING a line a commit deliberately removed? | 0 none · 1 re-additions · **2 established nothing** |
| `runmarker.py` | ⚠ **a module, not an instrument** — the two stderr markers every tool emits | n/a, it is imported |
| `ci-log-clean.py` | is this CI log's text OUTPUT, or the echoed script? | 0 cleaned · **2 established nothing** |
| `gh-complete.py` | is this `gh api` list reading COMPLETE, or a silent prefix of its own population? | 0 complete · 1 **TRUNCATED — the reading is a prefix** |
| `reference-check.py` | which recorded reference implementations have MOVED since we recorded them? | 0 every entry current · 1 MOVED or MISSING · **2 established nothing** |
| `use-not-mention.py` | does this file CALL `<pattern>`, or merely TALK ABOUT calling it? | 0 no call · 1 at least one CALL · **2 established nothing** |
| `pointer-verified.py` | did this pane READ the artifact a pointer NAMED, before acting? | 0 all read · 1 at least one not · **2 established nothing** · **3 control failed** |
| `pretooluse-guard.py` | would this command produce a confident wrong measurement? | 0 clean · 1 would warn · **2 established nothing** |
| `named-referent-check.py` | does a requirement sentence name an identifier that does not exist? | 0 none · 1 candidates · **2 established nothing** |
| `exists-anywhere.py` | does this name exist at ANY ref, or only on the one checked out? | 0 on the ref · 1 exists unmerged · 2 absent everywhere · **3 established nothing** |
| `memory-index-check.py` | does the memory index cover the memory files, and can it be loaded whole? | 0 covered · 1 orphans/dangling/oversize · **2 established nothing** |
| `marker-reachability.py` | can any CI invocation actually collect this test? | 0 all reachable · 1 unreachable found · **2 established nothing** |
| `close-condition-scan.py` | which open issues carry no close condition — and which hide one in a comment? | 0 every open issue has one **in its body** · 1 `NONE` or `BURIED` found · **2 established nothing (failed query, empty board, or a truncated reading)** · **3 known-positive failed** · `--self-test` `--states` |
| `merge-watch.sh` | did a merge leave work behind, or drift the worktrees? | emits FINDING · VOID · UNDOCUMENTED; silence means ran-and-found-nothing |

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

**`ci-log-clean.py`** — strips the echoed `run:` block from a CI job log, **before** anything
strips ANSI. ⛔ GitHub echoes the script into the log ahead of its output, so the log contains the
text of the grep you are about to run: `grep -c FAILED` returned **4** on a job whose conclusion was
**SUCCESS** — all four hits were the echoed script declaring `FAILED_FILES`, and the command's real
output contained zero.

★ **The order cannot be reversed.** The cyan-bold escape is the *only* thing separating the echoed
block from real output — the words are identical — so stripping ANSI first destroys the
discriminator irrecoverably and no later pass can rebuild it. ⚠ And the escape is not what a reader
expects: measured on a real 153 KB log, **0** actual `\x1b` bytes and **218** literal `^[` pairs,
because `gh` renders it as two characters. A reader stripping `\x1b\[[0-9;]*m` removes nothing and
believes it cleaned the log. Both forms are handled.

⇒ Two discriminators — the per-line `[36;1m` marker (precise, dies if ANSI is stripped first) and
the `##[group]Run `…`##[endgroup]` envelope (survives an ANSI strip, but `--log-failed` and some
fetch paths omit group markers). ⛔ **With neither present it refuses — exit 2 — rather than passing
the log through**, because handing back an uncleaned log unchanged is exactly how a count of the
script becomes a count of the output.

**`runmarker.py`** — ⚠ **not an instrument; a module.** It is imported, never run, and has no
exit codes of its own. It is indexed here only because `check-tools-index.py`'s population is
`tools/*.py` minus `test_*` — a shared module is not excluded, so leaving it out would read as
drift. ⇒ Reported to that checker's owner rather than worked around: **the same reasoning that
excludes tests (*"tests are not instruments and must not be indexed as ones"*) applies to a
library module**, and the population rule has no clause for one.

It provides `begin()` / `result()` / `guard()` — the `NFORMA-RUN` and `NFORMA-RESULT` markers
described in the exit-code convention above. See #58 for why the exit code could not carry this
alone, and `test_runmarker.py` for the three-producer demonstration.

**`readd-scan.py`** — flags an added line that an earlier commit **deliberately removed**, and
prints *that commit's own subject* next to it. ⛔ Built for the **ADDITION** failure mode (#220):
of the three ways to resolve a contradiction between a document and a claim about it — deletion,
narrowing, addition — **the third attracts the least scrutiny while doing identical work.** A
deletion has an obvious victim; an addition *reads as fixing a gap*. Measured case: a drift row
asserted a goal file *"carries no pushing-to-`main` clause — a live gap."* It had converted to a
pointer and was the only conformant file; acting on the row would have undone the conversion.

⇒ **It does not judge.** A revert is a legitimate re-addition. It puts the earlier decision in
front of the person reversing it — *"you are adding a line that `988d932` removed, saying: convert
Reserved to a pointer"* — so the reversal is a **choice** rather than an omission.

⛔ **The obvious mechanic is wrong and was measured wrong before this shipped.** `git log -S'<line>'
-- <path>` finds the **add** and **misses the removal**; so does `--full-history -m`; without a
pathspec it answers about other files. All three reported *no prior removal* for a line provably
absent from `main` and removed in `988d932`. ⇒ It **presence-walks** the file's history instead —
one pass per file, O(commits) rather than O(commits × lines). ★ A detector built on the pickaxe
would have returned a clean scan for the exact case it exists to catch.

⚠ `MIN_LEN = 24` is a stated calibration: short lines (```` ``` ````, `---`) recur across unrelated
edits and would bury the finding in noise. ⚠ Its known-positive is **constructed**, not sampled —
the live repo's re-additions are whatever exists today, and a control anchored to them goes silent
when they are resolved (#26).

**`grant-check.py`** — answers *"is `<role>` authorized to do `<capability>` here, right now?"*
from a record in `grants/`, never from the message that asked. Built after seven forged
authorizations reached agents' input boxes in one session, **one of which matched a real ruling**
— the forged and the genuine grants were the same kind of object (a sentence in an
unauthenticated channel), so no amount of care on the reading side could separate them (#3).

⚠ Two properties are load-bearing. It reads **`origin/main` after fetching, never the working
tree** — an agent controls its own checkout, and reading it would let an agent resurrect an
expired grant by checking out an older commit, which is thesis §7's self-renewal by another
route. And it **requires network**: offline it exits 2 rather than falling back to a source the
caller controls.

★ Its known-positives are permanent by construction (#26): three fixtures make `LIVE`, `EXPIRED`
and `REVOKED` reachable forever, because a *real* grant cannot serve — every real grant expires,
so a self-test anchored to one goes silent the moment it lapses. `--self-test` also proves the
`VOID` path executes and that fixtures cannot satisfy a real query. Verified by breaking it:
un-revoking the revoked fixture turns the run red at exactly that check.

**`discriminates.py`** — refuses a verdict when two states produce identical readings.
Built after `grep -c "46.6%"` returned `1` on both a worktree and `origin/main` and was read
as *"the states agree"*: the worktree was 163 commits behind and the figure had been
retracted, and **a retraction quotes the number it retracts.**

> Identical readings from a discriminator are an instrument failure, not evidence of sameness.

**`daintree-control.py`** — a known-positive control for the fleet-status instrument, so a
blind poller cannot log a quiet cycle that reads as a healthy fleet. ★ It terminates the
regress on something known **by construction**: at least one pane must report `working`,
because the agent running the check is one.

**`doctrine-watch.py`** — reports which roles' prompt or goal file changed since a
watermark, and which of those roles has not read the new revision. ⛔ Built because the fleet's
standing conclusion — *"a relaunch is the only complete-delivery channel"* — is wrong in the
expensive direction: **the read is available on demand and nothing triggers it**, so the fix is a
nudge rather than a restart. A relaunch buys exactly two things that cannot be delivered live
(cwd/worktree and process env) and costs every pane its working context.

⚠ Two behaviours it was given after its own controls refused to pass: it matches the tool CALL
rather than prose (the first version matched any occurrence of the path and its known-positive
could not fire, because every transcript mentions these files constantly), and it requires the
read to POSTDATE the change (a read from before the amendment proves the agent saw the old
revision, which is the condition being reported).

⛔ It cannot establish that a notified agent re-read rather than noting the notification and
continuing on the copy it loaded. That is the difference between a trigger and a guarantee.

⚠ **2026-08-20: `role_of` promised the one thing it did not deliver.** *"The role a session was BOOTSTRAPPED as — a name can be changed; this cannot"* — and it scanned the **whole file** for `You are X.`, taking the first hit anywhere. Measured over nine live transcripts: **3 resolved, 2 of the 3 wrong.** One came from a **correction sent a day later** (*"your identity was wrong … You are DEV2"*, record 17155, against a bootstrap reading MAINTAINER); one from a **quotation** of someone else's prompt; and a session bootstrapped as `DX` was reported `DEV2` because it had spent the day discussing DEV2. ⇒ It returned **the mutable thing it promised immunity from**, and a **mention** rather than a use. ★ Now anchored to the bootstrap record, with three outcomes — `None` unreadable or no launch prompt, `""` read and names no role, a role otherwise. **6 of 9 after, all from bootstraps.** ⚠ The two accepted phrasings are a **measured snapshot**, not a closed set.

**`label-exists.py`** — answers one question about the command every role in this fleet uses to find its
work: **is this string a label in this repository at all?** ⛔ Measured 2026-08-20: `gh issue list --label`
with a label that **does not exist** and with a label that exists and **matches nothing** produce
**byte-identical output and identical exit `0`.** Both print nothing. ★ That is this repository's dominant
defect class sitting inside the queue query itself — and the decision downstream is standing doctrine (*if
it returns nothing, say NOTHING QUEUED*), so **one typo makes an agent confidently report an empty queue and
go idle**, which this fleet has already done once across every pane simultaneously. ⚠ The same collapse one
layer up is refused explicitly: *"this label does not exist"* and *"I could not reach the forge to find
out"* are **not** one answer — an unreachable or unauthenticated forge is exit 2, never *absent*. A label
set that comes back at the 500 bound is treated as possibly truncated and **refused**, because a partial set
manufactures false absents. ★ Near misses are reported, because the useful output is not *no* but *did you
mean*: two schemes coexist here (`dev:1 … dev:5` and `role:ARCHITECT … role:TEAMLEAD`), and `role:dev1` is a
plausible blend of both that matches neither — **the live case that produced this tool**, and the one that
let four panes fix #307 independently. ⛔ **Similarity alone finds the wrong neighbour here, measured:**
`difflib` scores `role:dev1` against `role:DEV` · `role:DEVOPS` · `role:DX` and misses `dev:1`, because the
`role:` prefix dominates the ratio. ⇒ Labels are tokenised at every letter/digit boundary and matched on a
**token SUFFIX** — `role dev 1` ends with `dev 1`, so `dev:1` is the same referent under another scheme,
while `role dev` is a **prefix** and deliberately excluded: admitting prefixes would rank `role:DEV` above
the right answer on length alone. Similarity survives only as a labelled fallback for a genuine typo. ⚠ Its `0` means
the label exists; it is **not** a statement that your queue is non-empty. Known-positive: synthetic label
sets, never this repository's, so `dev:1` ceasing to exist cannot silence it.

**`verdict-census.py`** — answers #2's question for every instrument this table indexes: *has it ever
produced a verdict?* ⛔ **By running them**, never by reading the index — an index entry is a claim that a
tool exists, and asserting verdict-history from it would reproduce the defect #2 is about. It separates four
states that a single exit code would collapse: `VERDICT-SEEN` (exited a code its own docstring documents as
a conclusion), `ESTABLISHED-NOTHING` (exit 2 — a refused verdict, which is the honest form of silence and
**not** a verdict), `NO-VERDICT-VOCAB` (ran, but documents no exit codes, so *did it conclude?* cannot be
read from its contract), and `NEVER-RUN` (crashed, or exited a code it does not document). ⚠ A traceback is
classified before the exit code, because a crash that happens to exit `1` would otherwise read as a
conclusion. ⚠ A timeout is reported as `NO-VERDICT-IN-TIME`, never `NEVER-RUN` — measured: a 25s bound
labelled a 45s instrument never-run, which is a statement about the caller's parameter rather than the
tool. Its known-positive is a set of **synthetic fixtures outside `tools/`**, one per state, so repairing
any real instrument cannot silence it.

**`wake-yield.py`** — pairs an interruption's cost with its yield. Cost alone is
uninterpretable: an agent woken into useful work and one woken into churn consume context
identically.

**`pane-binding.py`** — reports which panes can be joined to a session and **which leg is
missing** when they cannot. Built for #6, where five independent investigations — an authorization
check, an attribution query, a compensation detector, an addressing resolver, a telemetry reading —
each terminated at the same unjoined edge.

★ That edge is one layer above the remedy. Daintree's own state file carries
`terminals[].agentSessionId`, in the same namespace as `CLAUDE_CODE_SESSION_ID`, populated for
exactly those panes launched with `--session-id` — 2 of 2 in both directions. ⛔ The join needs two
legs and **nothing currently holds both**: the nine fleet panes have a registry row and no
`agentSessionId`; the two that have one are child sessions, which write no registry row. ⇒ The join
has never been observed working — a different problem from a missing primitive, and a cheaper one.

⚠ It reports; it never infers. A pane whose legs do not join is `UNBOUND`, **never** guessed at from
a matching title — title agreement is the unreliable join #6 documents on both sides. Its self-test
builds a synthetic population, because the live one contains no `BOUND` fleet pane today and will
contain no `UNBOUND` one after the fix: a live-anchored control goes half-blind either way, which is
#26's sharp subtype.

⛔ Read the source before changing the launcher: Daintree **generates** the uuid itself
(`crypto.randomUUID()` behind `assignSessionIdArgs`) and has code that **strips** a caller-supplied
`--session-id`. Putting the flag in the recipe's `args` is therefore likely inert — see #6.

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

**`fleet-state.py`** — reads the `STATE:` line every role prompt requires on every turn. ⛔ It
exists as a self-correction: the signal was demanded and **nothing consumed it**, and an agent
that complied was re-woken seven times at 88–93% context with its named blockers unchanged. *A
wake that cannot hear its own answer is a drain, not a nudge.* ★ Parsed **positionally** — the
final non-empty line of the last assistant turn — never by searching for the token anywhere in
the text, because a keyword scan is tripped by any turn *discussing* blockage and this fleet
produced five such instances in one session. A quoted example is never the last line.

**`issue-coverage.py`** — ⛔ built because **92 of 241 open issues had been opened by nobody**, 34 of them older than a month, **measured while a pane sat idle waiting to be assigned something**. ⚠ **It cannot be asked and GitHub cannot answer it.** The credential is shared, so `author` and `assignee` are one login for every issue in every state — GitHub knows *what* happened, never *who*. And an agent's memory is worse: asked whether they had read their own role prompt, **three of four roles said "never" while their transcripts held 14, 11 and 9 reads from that morning**; the one that grepped its transcript before answering was the one that got it right. ⇒ So it reads what a pane **actually opened**, in a `tool_use`. ★ **Contact is not review** — `OPENED` means a pane fetched it, and the two are never collapsed. ⚠ Three ways to print a clean zero are three exits: an empty board, a `gh` query that failed, and a transcript glob that matched nothing are all **exit 2**, never "fully covered". ⚠⚠ **The bound cuts one way**: transcripts on THIS MACHINE only, so a pane working from a transcript held elsewhere reads as having opened nothing — the untouched count is an **upper** bound and per-pane counts are **lower** bounds.
**`prompt-delivery.py`** — did a role prompt **reach** a pane, and by which channel? ⛔ It exists
because `9 of 9` was true of the **files** and false of the **sessions**, and both populations had
nine members: nine goal files carry a pointer at `prompts/<ROLE>.md`, and nine sessions were active
when that was measured. **The installed count is a property of the filesystem; the delivered count
is a property of a transcript**, and nothing in either number says which one it is. ⇒ So it never
prints one number, and it splits delivery by channel because they are not equal evidence: `LAUNCH`
(the pane started with it), `RECEIVED` (a peer had to say it), `PULLED` (the session fetched or
wrote it **itself**). ⚠ **`PULLED` is not delivery** — the session with the most hits on this fleet
was the one that wrote the pointer into the goal files. ★ And a transcript whose head holds a wake
rather than a launch prompt **establishes nothing** about how that pane was launched; that is its
own verdict, never a `no`.
**`text-provenance.py`** — ⛔ built after the same mistake **twice in one day**: a search for a
distinctive string returned hits that were **entirely this session's own tool records**, and the
count was read as reach. Six hits for a rule's text were six `tool_use` records *searching for the
rule*; fifteen hits for a measurement quoted in a PR closure were `tool_result`s from my own
`gh pr view`. **The hits were real, the string was right, and the conclusion inverted — because grep
counts OCCURRENCES and the question was AUTHORSHIP.** ⇒ So it never reports a count: every hit is
`AUTHORED` (an assistant record), `FETCHED` (a tool_result — the session went and got it),
`RECEIVED` (an inbound turn), `INSTRUMENT` or `OTHER`. ⛔⛔ **`INSTRUMENT` and the `POST-DATES` check were both added after a peer broke the shipped tool in one message.** **The probe contaminates the population**: asking a peer about a phrase writes that phrase into the peer's transcript — DEV4 had **zero** hits for four of five needles before I messaged it and **two each** after. And a needle inside a `tool_use` input is the session **running a command** that contains the string, not asserting it: two of my own three `AUTHORED` hits were a search script with the needle as a literal argument, so the shipped tool **would have named the peer who searched on my behalf as the author of a phrase it first saw when I sent it.** ⚠ Publishing is an **allowlist**, not a denylist of search verbs — keying on `grep`/`rg` misses a python heredoc doing `if needle in line`, which is how both false positives were produced — so the bias is toward refusing attribution. ★ And **`POST-DATES` is not a heuristic**: if you already held the text at T0, a session that first saw it at T1 > T0 cannot be the origin of your copy. ⛔⛔ **And the allowlist itself DRIFTS.** The first version listed `commit -m` and not `commit -F -`; a peer measured **61** uses of the second and 13 of the first in its own transcript, plus **24** `gh issue create` and **55** `gh issue comment` — none of them listed. **Nothing failed; the numerator just quietly shrank.** ⇒ So an unrecognised path is **`UNCLASSIFIED` (exit 4), never a silent `INSTRUMENT`**, and `--audit` enumerates the tools actually present and names what nothing classifies — **17 on its first run, on this repo's own machine**, which is the only evidence a staleness check works. ⚠ `gh` is not one tool: `create`/`comment`/`edit` publish, `view`/`list`/`api` read. ⚠ And the `gh` and `commit` forms are **anchored at a command position**, not matched as bare substrings: the literal version classified `echo "listed: commit -m and gh pr comment"` as **AUTHORED** — a *quotation* of the allowlist read as an *invocation* of it, which is use-vs-mention and was caught by this suite's own negative control. Measured on a peer's transcript afterwards: **all 10** bare `commit -m` occurrences were quotations of this very discussion, and its true invocation count matched mine exactly once the anchor excluded them. ★ **And it refuses a verdict when every hit belongs to the
asker** — exit 3, the shape of a failed control, not of "no author found". ⚠⚠ **A local absence is
not an absence**: a session that authored the text on another machine and one that never authored it
produce an identical empty result here, which is not hypothetical — a peer was reported `FLATLINE`
for six hours while merging two PRs from a transcript this machine does not hold. Zero hits is
**exit 2**, never "nobody wrote it".
**`pr-stack.py`** — ⛔ every PR branches from `main`, so **a fix that has not shipped is absent from every PR opened after it**, and whoever lands second rebases under conflict pressure. Measured 2026-08-20: **11 of 21 open-PR pairs conflicted, and ONE file caused 11 of the 11.** ★ The merge order is a decision somebody makes anyway — either now with the pairs visible, or later by whichever PR happens to land first. ⚠ **Three verdicts, because *both apply cleanly* is not *compatible*:** `CONFLICTS` (one must rebase on the other, and choosing which is the whole decision); `OVERLAPS` — **the dangerous one** — same files, no textual conflict, so both branches pass and the *merge result* is untested; and `independent`. ⚠⚠ `merge-tree` is **textual**: `independent` is the absence of a signal, never a claim of compatibility — a PR can delete what another starts calling. ⛔ And an **unfetched head is UNKNOWN, never clean**: its first run skipped 2 of 4 PRs and printed a conflict count from the half it could see, and **a smaller conflict count reads as better news**.

**`close-condition-scan.py`** — ⛔ built because **TEAMLEAD reported "~31 open issues lack completion conditions" and nothing had ever produced that number.** Measured on the first run: **61 of 85**, roughly double. An issue with no falsifiable close condition cannot be *closed*, only abandoned or declared, so the count decides how much of the board is closeable at all. ★ **The second state is why this is a tool and not a grep.** All five of one role's queued issues carried a `Done when` clause and **none carried it in the BODY** — every clause sat in a comment, three of them under six others. A closer who opens the issue and reads it sees no condition. ⇒ `BURIED` is therefore a **distinct verdict, not a weaker `NONE`**: the defect is different, the repair is different (move the clause into the body), and it is invisible to any check that asks only *does a condition exist somewhere*. Board-wide: **19 BURIED, and only 5 of 85 issues carry a condition where a closer reads it.** ⚠ **The pattern is anchored at line start**, so a clause must be a structural element rather than a phrase in a sentence — a bare substring match flags #189, a friction report *about* close conditions, as *having* one. That use-vs-mention case is the suite's load-bearing negative, and it is **shown to fail**: swapping the anchored regex for the naive substring form takes the self-test from 5/5 to exit 3. ⚠ Three ways to print a clean zero are all **exit 2** — a failed query, an empty board, and a reading shorter than the population `search/issues` states. ⛔ **A mistyped label is the sharp case: `gh issue list --label <nonexistent>` exits 0 with zero bytes on stdout AND stderr**, byte-identical to an empty queue, which is how a wake message routed a role to a label that did not exist. ⛔⛔ **THE BOUND: it detects PRESENCE, never FALSIFIABILITY.** `## Done when: it feels done` passes. Exit 0 means every open issue carries a clause in its body — never that any of them can be closed honestly.

**`api-budget.py`** — ⛔ the GitHub quota is **one 5,000/hr pool shared by every agent and every tool**, and nothing showed a pane its own share. Measured 2026-08-20 while the pool sat at **0/5000 with 42 minutes to reset** and every pane's `gh` call 403ing: **10,214 invocations across nine live transcripts in one session**, 4,553 from a single role, **3,352 of them bare `gh api`**. ⚠⚠ **One invocation is not one API call** — `--limit`/`--paginate` paginate, `run view --log` downloads an archive, and `gh api graphql` costs by node count — so the count is a **lower bound on spend and is never reported as the spend**; the tool flags which invocations used a multi-call flag and refuses to guess a multiplier. ★ **The cost lands on whoever asks NEXT**: a pane that made no calls all session gets the 403, which is why per-role attribution is the useful output. ⛔ A failed `rate_limit` read is **`None`, never a full pool** — that endpoint is *exempt* from the quota it reports, so a failure there is network or auth and printing a number would blame the wrong thing.

**`transition-report.py`** — the STATE line is a **pull**; the role prompts also require a
**push** on transition into `FREE` or `BLOCKED`, and this is that rule's execution record. Built
the same day as the rule, because `prompts/README.md` names the alternative: a rule asking a
reader to check something mechanical is *"a check with no execution record: its compliance is
unobservable, so its violation rate is unmeasurable."* ★ **Its two directions are not equally
strong.** `MISSED` is strong — no message at all between your previous declaration and this one,
so this channel cannot have carried it. `notified` is weak — a message exists in the window and
the tool cannot read what it was about. ⇒ It finds omissions; it is not a compliance rate, and
quoting the notified count as one is the way to misuse it. ⚠ A `MISSED` row is a **candidate**:
a pane can also be spoken to directly. It imports `fleet-state.py`'s parser rather than
re-implementing it, so the positional rule has one home and two readings can never corroborate
each other by both being wrong.

**`doctrine-version.py`** — answers which version of its role prompt each agent is actually
running. `ROLE-READY` proves the prompt file was *reachable*; it never says which version was
read, and the version is the part that decides behaviour. ★ It takes no cooperation from the
agent: the bootstrap already runs `cat $NFORMA_ROLE_PROMPT`, so the read lands in the transcript
and is matched against every historical blob — **an off-pane effect, not a claim a possibly-stale
agent makes about its own staleness**, which matters because that agent is the party least able
to report it. Two versions are only distinguishable if neither contains the other; a session
matching both is reported AMBIGUOUS rather than resolved to the convenient one.

**`bootstrap-audit.py`** — audits the interval a `ROLE-READY` line closes, rather than the
three facts it asserts. ⛔ Measured on the live nine-pane fleet: **every token was true in all
three facts it carries, and every bootstrap had a step with no execution record** — so a
consumer that verified the assertions would have passed all nine. The token is treated as
punctuation delimiting the bootstrap window, never as a claim; the audit is of what ran inside
that window. See #20.

**`index-watch.py`** — runs `scripts/check-tools-index.py` when `main` moves and relays what it
found. ⛔ Built because `ci-log-clean.py` reached `main` undocumented while the checker that detects
exactly that had existed for hours and **nothing invoked it**; the defect surfaced only because a human
ran the check by hand after a merge. ★ **Event-driven, not clocked** — it polls
`git ls-remote origin refs/heads/main` and runs the subject only when the SHA changes, because the
defect is caused by an event and a timer on a quiet repo fires all day with nothing to say. ⚠ Its
known-positive is the **subject's own** `--self-test`, deliberately outside the population it measures:
a control of the form *"the repo has a drift right now"* is silenced by repairing the repo. It emits a
**finding**, never a task and never a grant — a scheduled job that re-enters an agent with a plausible
instruction has genuine provenance, which is harder to catch than a forgery. Armed under the operator's
read-only monitor grant in `goals/RESERVED-ACTIONS.md`.

**`stranded-branches.py`** — commits sitting on a branch whose PR already merged. Found 2 of 15 by
hand; the mechanism (`git for-each-ref` + `git rev-list --count`) already existed and **had no
reader**, which is `fleet-state.py`'s shape one layer over — a signal demanded with no consumer built.

★ Every row is stamped with the ref's object id **at measurement time**, and that is why this is a
tool rather than a doctrine line. Three observers measured one ref within an hour and got three
different values — 3 commits, 749 lines, then 4 commits and 755 lines — **none of them wrong when
taken.** The ref moved, inside a thread about refs moving, among agents who had just finished
diagnosing that class. A count without its sha is not comparable to the same count from another run.

⚠ Its fixture is synthetic on purpose. The two live stranded branches were the obvious
known-positive and **both went to zero within the hour** as their follow-up PRs merged — #26
instance 3, realised rather than hypothetical: a control propped up by a defect queued for repair
stops being a control the moment the defect is fixed.

⇒ **A fourth state, because patch id was answering a different question.** `git cherry` asks *is
there an equivalent COMMIT upstream*; the thing worth knowing is *is this WORK upstream*. Two branch
commits squash-merged into one upstream commit can never match by patch id — the diffs are different
sizes — so the branch reads NO-UPSTREAM-MATCH forever while its bytes sit on `main`. `CONTENT-UPSTREAM`
answers the second question directly: every path those unmatched commits touched is byte-identical at
`origin/main`. It establishes **landedness only, never authorship** — if the content is there the work
is not lost, whoever put it there.

⛔ **The empty path set must not read as landed.** `all(...)` over zero paths is true, so a
forgotten guard reports work as recovered having compared nothing. The decision therefore lives in a
pure `content_state(unmatched, same, tot)` that takes counts and needs no repository, and the
`(2, 0, 0) -> UNRESOLVED` row is asserted in both `--self-test` and the suite. Deleting the guard
makes `--self-test` exit 2 — verified by mutation 2026-08-20, not by assertion.

⚠ **The path ratio is the number worth reading, and the reason the state is rare here.** The
predicate is all-or-nothing across paths, so a single shared index file that every pane edits vetoes
the whole ref even when the branch's own deliverables are byte-identical upstream. *Measured
2026-08-20 at `6faec9a` across the 4 refs then carrying unmatched commits: 1 read CONTENT-UPSTREAM,
and 2 of the remaining 3 were vetoed by `tools/README.md` alone* — this file. A row reading n-1 of n
is near-certainly landed; 0 of n is a different animal, and collapsing both to one verdict threw away
the only signal separating them. The ratio is now printed on negative rows too.

**`gh-complete.py`** — ⛔ `gh api …/check-runs` returns **30 of 54** by default and it is not an
error: the response still carries `total_count: 54`, so a filter over `.check_runs[]` evaluates the
thirty it received and **returns a clean answer about a set it never saw**. Measured: it hid a
required-check failure, and made two instruments by one author contradict each other about one PR.
⚠ `per_page=100` is the reflex and **it is not the check** — it fails silently the moment a
population exceeds it. This compares the stated total against what arrived and refuses the reading
when they differ.

**`reference-check.py`** — answers the one question a curated list cannot answer about itself:
**has any of it moved?** ⇒ Built because a 249-line root-cause investigation of a failure this fleet
re-derived from CI logs overnight had been on this machine for a month, and the standing rule that
pointed at it existed while nobody opened its `docs/`. ⚠ And searching is not the remedy — 304
repositories under `~/code` and 14,517 markdown files mention *exec*, so a keyword sweep returns a
haystack. `reference-implementations.md` is therefore CURATED, and this watches the curation.

**`pointer-verified.py`** — ⛔ *"verify at the artifact, never the message"* is this fleet's
mitigation for #3 and it is **doctrine with no execution record** (#2). ⚠ The obvious tool is #26:
*"did **any** artifact command run after the pointer"* scores 21 of 23 on its author's transcript
and would score **any live pane clean**, because a working pane always runs `git` for something
else. ⇒ So the predicate is specific — *did a command read **the ref-and-path the pointer
named***. ⛔⛔ And the false positive is **guaranteed**: a pointer's text *contains* the command
that would verify it, so any scan over the turn reports the pointer as self-verifying. **The
population of false positives is created by the pointer format itself** (#36). Named artifacts are
read from the inbound turn; **evidence only from `tool_use` command fields** — a quotation cannot
occupy a tool call. ⚠ `READ-DIFFERENT` **over-reports on purpose**: a pointer names every file in a
role's row including ones with a `+0/-0` delta, and reading only the changed ones is correct and
scores FAIL. Narrowing it to guess which named file mattered would trade a *visible* over-report
for an *invisible* under-report.

**`use-not-mention.py`** — ⛔ a grep for a command finds every sentence *discussing* that command.
Measured in a sweep its author wrote minutes after working on this exact class: two false
positives, one a `print()` warning about the very defect being scanned for and one a fixture
string inside a test of a different matcher. ★ **The sub-class that makes it worse over time:**
correct handling *generates* mentions — a tool that documents the defect necessarily contains the
pattern — so a *"does this code handle X"* scan gets **noisier as the estate improves**, with the
noise concentrated in the files that are already right. ⇒ Resolves the **sink** rather than
matching the text. (#36)

**`memory-index-check.py`** — ⛔ measured on the machine it was written on: **348 memory files,
232 indexed, 115 ORPHANS**, and the index **42.5 KB against a recalled ~25 KB load budget**. An
orphan is not degraded, it is **invisible** — recall works from the index, so a file nobody links
is a file nobody reads, and nothing says so. ★ The recursion is the point: that directory already
held an entry titled *"Memory index truncates by AGE, not importance"*, and the index then grew
past the limit **again** and acquired 115 unindexed files on top. A recorded lesson did not fire.
⚠ It reports **orphan**, **dangling** and **oversize** separately because their remedies are
opposite — an orphan is fixed by adding a line, and oversize is made **worse** by adding one. ⚠ The
25 KB budget is a **recalled** figure, not one this tool established, which is why it is a flag.

**`exists-anywhere.py`** — ⛔ built after **four instances in one session, by three agents**, of
concluding about a repository from a single ref. One reached publication and had to be retracted:
`ci_guard_closing_keywords.py`, reported as never having existed by two agents who each ran
`git ls-files | grep`, is **161 lines with its own test file** on an unmerged branch. ★ The
object-store count is the discriminator and it is one command — `iter_console_backends` returns
**0**, that guard returns **6**. ⇒ *"Never existed"* and *"exists on a ref you did not search"*
are different defects with different remedies, **a wrong sentence versus an unmerged branch**, and
`git grep`, `git ls-files` and a working-tree scan cannot tell them apart. ⚠ Deliberately a tool
and **not** a `pretooluse-guard` rule: the wrong reading is not a wrong command, it is a correct
command answering a narrower question than the one asked, so a guard would fire on the correct use
— which this repository has already shipped once.
**`marker-reachability.py`** — the static half of #2. #2 specifies five states from RUN
HISTORY, and a test excluded by every `-m` selector generates no runs to query: ⇒ **you cannot
ask "has this gate ever spoken?" about something you do not know exists.** This supplies that
population from the repository alone — no API, no rate limit, gates in CI. ⛔ Its known positive
is `tests/test_cluster_spec_drift.py`, reported by two agents and filed as Blazing-Back#1115:
`pytestmark = pytest.mark.network`, and the only selector covering `tests/` is
`-m "not e2e and not network"`. ★ **Its first working version reported 870 files, 0 unreachable,
and missed that guard** — because it matched `pytest` inside COMMENTS, and those mis-parses
yielded `paths=[] -m=None`, which the rule reads as *collects everything*. **One comment marked
the whole repository reachable.** ⚠ Three states, and `UNKNOWN-PATH` (a `${var}` path) is counted
in neither column: resolving it either way would overstate the evidence. A direct
`python3 e2e/test_x.py` counts as run — asking "can pytest collect it" gave a *true answer to the
wrong question* for 11 e2e files.

**`named-referent-check.py`** — converted from a **convergence**, not from one report: two
agents, different subsystems, no contact, within one hour found a named enforcement mechanism
with no referent (`iter_console_backends`, asserted in capitals as mandatory, defined nowhere;
`EXEC_REQUIRE_EVIDENCE`, three exec sites "held behind a flag" that does not exist). ★ Neither
is a stale reference to something removed — both describe machinery **never built**, in prose
confident enough that the author stopped checking. ⛔ Its narrowing history is the point: **126
candidates → 8 → 1** on the same 1,559-file repo, and only hand-verification forced each step —
at 8 it was **7/8 false**, calling real config keys phantoms because string literals and kwargs
were missing from its universe. ⚠ It is deliberately narrow and says so: a convention naming
*nothing* is invisible here, an identifier that exists but is never called passes, and one of
its own two founding cases is undetectable by it. A clean run means *no requirement sentence
names an undefined identifier* — **not** that stated and enforced conventions agree.

**`pretooluse-guard.py`** — matches, over a single command string, the idioms that produce a
confident WRONG measurement: `$?` read after a pipeline, `${PIPESTATUS[n]}` under zsh, and a
`$VAR:` history modifier eating a path.

⛔ **NOT INSTALLED, and installing it is not a DEVOPS decision.** It would run as a `PreToolUse`
hook on every Bash call for everyone here — harness configuration, which is the operator's, and
`~/.claude/settings.json` already carries a live PreToolUse chain, so an addition changes a
running mechanism rather than adding one. Nothing in this repository wires it.

⇒ It is committed because `pipe-exit-scan.py` cited a number this file produced, and this file
lived in a scratchpad with zero tracked copies. ★ And committing it corrected the citation
immediately: `--measure` over the whole fleet gives **25 of 1720, 1.5%**, where the cited 2.5%
was **one role's 204-command session quoted without its denominator** — a rumour on a subject
nobody named, in a tool's docstring, written by the author of that rule.

⚠ Two slots stay empty rather than plausible. The `INVERTED`-severity rule — the one whose failure
replaces a measurement with a confident claim about the *repository* — has **zero hits** in the
corpus, so its false-positive rate is *unmeasured, not zero*. And the **hook mechanism is
untested**: this measures the matcher, never that a hook fires on the right event or surfaces
output an agent reads. [NOT-YET-MEASURED]
**An absence report must name its REMEDY, not only the absence.**

`daintree-control.py` printed `⛔ VOID: no daintree MCP server configured` on every run for four
hours. Correct every time, and three instruments announced it. It was read, quoted, and **built
around** — a state-file route for one identity leg, a transcript route for pane output — and nobody
asked whether the absent thing could be *added*. The operator supplied the config in ninety seconds.

⛔ That tool's header already said *"a VOID run must never be read as 'the fleet is quiet'."*
**It guards the wrong door.**

```
VOID != "the fleet is quiet"       anticipated, documented, NOT the failure
VOID != "this cannot be obtained"  unanticipated, undocumented, cost four hours
```

⇒ **An absence report that does not name its remedy converts a gap into a wall.** A refusal collapses
four states with four different actions — *fixable by me* / *fixable by another role* / *needs the
operator* / *genuinely impossible* — and only the fourth justifies a workaround. The fleet built
workarounds against the third.

⇒ Exit-2-for-established-nothing needs its second half: **established nothing, AND here is who could
change that.** Written `ADDABLE — <who>: <what>`.

⚠ Swept: `daintree-control.py` (both paths), `fleet-identity.py`, `stranded-branches.py`,
`fleet-context.py`, `fleet-state.py`. **`discriminates.py` and `wake-yield.py` need no annotation** —
their refusals are *the verdict*, not an obstacle: a non-discriminating comparison and an
un-analysable interval have no remedy beyond a different input, and inventing an `ADDABLE` line for
them would be a remedy slot filled to look complete. **NOT swept:** tools owned by other roles.
[measured: nForma-NEXT 2026-08-19] (#73)

**`merge-watch.sh`** — a read-only monitor under the operator grant of 2026-08-20. Runs the
merge-time instruments **when `main` moves**, not on a clock.

★ **Placement, not schedule, is the finding.** `stranded-branches.py` already had a caller — at
**launch** — and the regression it exists to catch arrives at **merge** time, hours before the next
launch. A clock would be no better: the defect is not periodic, it is *caused by an event*. ⇒ So the
cadence **is** the event.

⛔ **Silence means ran-and-found-nothing.** It emits on findings, on VOID, and on any exit code the
callee does not document — a watch whose quiet covers both states is the never-concluded defect with
a schedule attached. Proven by stubbing the instrument's control to fail: the watch emits `VOID`
rather than going dark.

★ **Its control is one a fix cannot silence.** Before trusting a scan it asserts the instrument's own
`--self-test`, which is synthetic and does not decay — unlike a known-positive drawn from live fleet
state, which the fleet repairing itself turns negative. (An orchestrator declared exactly that defect
in its own watch: its positive was propped up by the defect it detected, and both arms went to zero
when the panes it notified read their files.)

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
- **A missing wrapper binary makes the command under test never run — and the output reads as a
  result from it.** ⚠ Two instances, two roles, one session. `timeout` **does not exist on
  macOS**: `env … timeout 180 claude --session-id …` died inside `env` with
  `env: timeout: No such file or directory` and never reached `claude`. Read unguarded, that
  says *"the launch produced no session"* — a false negative about the thing under test,
  produced by a wrapper that never invoked it. ARCHITECT hit the same absent binary an hour
  later and got **`127` from all nine tools at once**, which renders as a clean, uniform,
  entirely wrong table.
  ⇒ ★ Same shape as the pipe rule below and worth pairing with it: **the status you read
  belongs to the outermost thing that ran, and when a wrapper is missing that is the wrapper's
  failure, not your subject's.** `127` and `126` are never verdicts about the tool you were
  testing. Check the wrapper exists (`command -v`), or drop it — the probe above needed no
  timeout at all, because `-p` terminates on its own.
- **Quote or `./`-prefix a `<ref>:<path>` argument.** zsh reads `:t` `:s` `:h` `:r` `:e` as history
  modifiers, so `git show $S:tools/README.md` silently loses the path and returns `fatal:` — and a
  `grep -c` over that failure scores **0 mentions**: a mangled instrument reading as a clean negative.
  `git show "$S:./tools/README.md"` defeats it. ⚠ `pipe-exit-scan.py` does **not** catch this — there
  is no pipe. Same signature, different mechanism, and the scanner finding nothing says nothing about
  it. [measured: nForma-NEXT 2026-08-19, DEV5 and DEV1]
- **Never read an exit code through a pipe.** ⇒ RETIRED AS PROSE, enforced by
  `tools/pipe-exit-scan.py`. It is kept as a one-line pointer rather than a rule because the
  prose form was measured not to work: three instances, in three roles, in four hours — and the
  third happened in a role that had been warned about it *in the same message that assigned the
  task*, against this very paragraph. ⛔ A rule that exists and does not fire is worse than no
  rule, because its presence is mistaken for coverage.

- ⛔ **A known-positive proves a control CAN fire. It does not prove the control fires
  CORRECTLY.** Measured, inside the tool built for #26: `bootstrap-audit.py`'s known-positive
  passed — it genuinely discriminated a defective bootstrap from a clean one — and the same run
  reported two **false passes** against live data, because a step was matched against any tool
  input containing its text, and two panes had *messaged each other that the step did not
  execute*. A report of non-execution quotes the thing that did not execute. ⇒ #26's test
  (*name the input that makes this emit a negative*) is **necessary and not sufficient**; it
  says nothing about the false-positive direction, and a control that passes it can still be
  wrong in the direction that reads as healthy. Pair every known-positive with a known-negative
  drawn from **real** data, not from a fixture.
- **Match execution against what was RUN, never against what was SAID about it.** The false
  passes above came from searching a tool call's whole input. Prose that discusses a command
  contains the command; only the `command` field is evidence that it ran. This is
  `discriminates.py`'s retraction case — *a retraction quotes the claim it retracts* — one
  layer up, in a different instrument, found the same day.
- **Always brace a ref variable — `${REF}:path`, never `$REF:path`.** zsh applies its history
  modifiers to an unbraced `$VAR:`, so `$P:tools/README.md` expands to `c29aa60ools/README.md`
  (`:t` = tail) and `$B:scripts/…` expands with `:s` consumed. ⛔ **The failure mimics a domain
  answer:** git replies `unknown revision or path not in the working tree`, which reads as *the
  file is not there*. Measured twice in one session — one produced two empty fixtures and four
  exit codes nearly filed as a broken checker; the other was one step from reporting
  `tools/README.md` missing from `main` and inverting a closure verdict about that very file.
  ★ **It is data-dependent, which is the part that makes it dangerous:** in the same script
  `$P:goals/`, `$P:scripts/` and `$P:.daintree/` were all correct, because only the letters that
  happen to be modifiers bite. A script can be right nine times and wrong on the tenth path.
  Same family as the exit-code rule above — an idiom that answers a different question while
  looking like it answers yours.
  ⛔ **Double-quoting is NOT protection, and that is the hole this rule had.** The shell-safety
  reflex is to quote, and `"$REF:path"` fails identically to the bare form — the modifier is
  applied during parameter expansion, before quoting means anything. Measured: `"$X:scripts/f"`
  and `$X:scripts/f` both fail; only `"${X}:scripts/f"` is correct. **Braces, not quotes.** The
  author of this bullet then wrote `git show "$M:scripts/check-tools-index.py"` two hours later
  while verifying a merge, and was protected by nothing.
  ⚠ **And the data-dependence is worse than "sometimes wrong": the same idiom fails LOUDLY or
  SILENTLY depending on the path.** `:s` needs delimiters, so a path that supplies them is
  rewritten and a path that does not raises `bad substitution`:

  ```
  $X:scripts/f                    -> zsh: bad substitution        (exit 1, obvious)
  $M:scripts/check-tools-index.py -> <sha>k-tools-index.py        (silent; git then says
                                     "unknown revision or path" — i.e. THE FILE IS NOT THERE)
  ```

  ⇒ You cannot learn this rule from experience, because the instance that teaches it is the one
  that does not announce itself.
  ⛔ **It hits three of this repository's five directories, and the fleet's own doctrine
  recommends the form that breaks.** Measured in zsh 5.9 (DEV3, reproduced here) — 11 of 14
  modifier letters are active (`a A c e h l q Q r s t u`); only `g p x` are inert alone, and `g`
  stops being inert when the next letter is a modifier:

  ```
  "$M:tools/README.md"    -> <sha>ools/README.md       :t    MANGLED
  "$M:scripts/…"          -> <sha>k-tools-index.py     :s    MANGLED
  "$M:grants/README.md"   -> <sha>ants/README.md       :gr   MANGLED
  "$M:goals/README.md"    -> unharmed                  :go   'o' is not a modifier
  "$M:docs/…" "$M:prompts/…" "$M:README.md" "$M:CODEOWNERS"  -> unharmed
  ```

  ★ **`goals/` and `grants/` are one letter apart and land on opposite sides.** Nobody holds that
  in their head. ⚠ And `CLAUDE.md` and `goals/dev-implementation.md` both tell every agent to
  *"prefer `git show <ref>:<path>`"* — correct advice for #19's shared tree, and the unbraced
  spelling of it mangles worst on `tools/`, the highest-traffic path here.
- ⛔ **A redirect truncates the file before the command runs, so a failed fetch leaves an empty
  file that runs clean.** `git show "$BAD" > out.py` exits non-zero and still leaves a 0-byte
  `out.py`; `python3 out.py` then exits **0** with no output. Measured while verifying that a
  merged PR's checker worked from `main`: both the live run and the `--selftest` reported exit 0,
  from a file that was never written. **A clean pass and a control that never ran are
  byte-identical here.** ⇒ Guard on the artifact, not on the command: check the byte count before
  running what you just fetched, and refuse rather than report clean. This is the same shape as
  reading an exit code through a pipe, one layer out — the thing you measured is not the thing
  you meant to measure.
  ⚠ **This is not a Python property and not a shell property — an empty file exits 0 under every
  runtime**, because there is no statement present to fail. Measured: `python3` 0 · `bash` 0 ·
  `zsh` 0 · `node` 0. ⇒ **No exit-code guard can see it.** Only a byte count, or a required
  start-marker in the fetched artifact, discriminates *ran clean* from *never ran*. (DEV3, whose
  #58 exit-code paragraph covered the result being empty and not the FILE being empty.)
  ⛔ **And the byte-count guard covers file-EMPTY, not file-WRONG.** The unbraced idiom has a
  third outcome that defeats it. Measured, all four from `scripts/` on one commit:

  ```
  scripts/x.py                  rc=1    empty      zsh: bad substitution   LOUD
  scripts/fleet-preflight.sh    rc=1    empty      zsh: bad substitution   LOUD
  scripts/check-tools-index.py  rc=128  empty      "ambiguous argument"    INVERTED
  scripts/validate-recipe.py    rc=0    NON-EMPTY  a COMMIT HEADER         WRONG OBJECT
  ```

  ⚠ **No byte count here on purpose.** The last row's size is the length of whatever commit
  header git printed, so it varies **by commit** — 304 to 323 across five consecutive refs, merge
  commits carrying an extra `Merge:` line — and **by measurement method**: `wc -c` and `${#var}`
  differ by 2 on the same commit, because command substitution strips trailing newlines. Two
  agents measured two commits with two methods and got two numbers, both correct. ⇒ **`rc=0` and
  *non-empty* are the invariants; the number never was one.** Citing it would only start a fourth
  argument with a future reader who measures a fourth commit. (The rule is #34's — *cite the
  property, never the number* — and this is DEV3 applying it to its own table one commit after
  filing it.)
  ⚠ **Observation, n=1, recorded rather than proposed as a rule:** the two numbers above came
  from *one agent* — `wc -c` in a scratch run, `${#var}` forty minutes later — and nothing in
  either run flagged the disagreement. It surfaced only when a peer's number differed. ⇒ So
  **"I measured it twice" is not the control it sounds like.** Two invocations that agree
  establish that the method is deterministic, not that the number is a property of the thing;
  only two runs known to differ in *method* test that. A single observer cannot detect this class
  from the inside, because the discrepancy is the instrument.

  ★ In the last case the modifier eats the **entire** path, the argument collapses to the bare
  ref, and `git show "$M:scripts/validate-recipe.py"` runs as `git show <commit>` — **exit 0,
  non-empty, structurally valid, and about a different object entirely.** A byte-count guard
  passes it because it is non-empty; an exit-code guard passes it because rc is 0; a downstream
  reader parses the commit header without
  hesitation. ⇒ **Only bracing, or verifying the content is what you asked for, catches this
  one.** Four filenames in one directory, three different outcomes, one of which announces
  itself — which is why the rule is *brace unconditionally* rather than *remember which paths are
  dangerous*. (Measured by DEV3, reproduced here.)
- ★ **A name-presence test is not merely blind to a documented gap — it is ANTI-CORRELATED with
  it.** A document admitting a gap discusses the missing thing by name, so the gap note is
  typically the *highest-density* occurrence of that name in the file. Measured on this file:
  `fleet-state.py` scored 2 mentions while having **zero** table rows and **zero** prose entries,
  which put it mid-pack among genuinely documented tools (2–4). Three agents independently read
  the directory as fully documented. ⇒ Match **structure** — `^| \`x.py\` |` for a row,
  `^**\`x.py\`**` for an entry — never a bare name. Sibling of `discriminates.py`'s *a retraction
  quotes the claim it retracts*, with the difference that matters: quotation makes a matcher
  **uninformative**, negation makes it **inverted**. An inverted instrument argues for the wrong
  conclusion in the voice of a measurement.
- **Pin a sweep to an immutable SHA, not to a ref.** `git rev-parse origin/main` once, then read
  everything at that SHA. ⛔ A worktree gets its own `HEAD`, index and logs, but `refs/remotes`
  lives in the **common** `.git` — so `git show origin/main:<path>` resolves the ref *at read
  time* and follows every peer's fetch. Measured: `origin/main` advanced mid-audit under a
  pinned-*looking* read; two `git ls-tree origin/main scripts/` calls twenty minutes apart
  returned 2 files and then 3. **Only an immutable SHA pins**, and worktree isolation does not
  change this — it isolates the working tree, not the refs.
  ⚠ **Pinning protects the READ, not the WRITE.** The two are different propositions and the
  rule covers only the first. A branch cut from a pinned SHA still has to land on a moving
  target, so a peer editing the same file mid-flight produces a merge conflict that no amount of
  pinning prevents — measured, on the very PR that added this rule. Re-pin and rebase before
  pushing; expect the conflict rather than being surprised by it.
- **Whitespace-normalise before matching a rendered body.** `#23`'s rule is *verify by content,
  never by position* — this is the failure mode one step inside it. A content predicate is still
  positional if its unit is the LINE: `"no reachable passing state"` returned **False** against a
  PR body that contains exactly that phrase, wrapped. ⇒ The artifact was correct and the check was
  not, which is indistinguishable from the artifact being wrong. Collapse runs of whitespace on
  both sides first. ⚠ Measured twice the same day, at two altitudes: once against a rendered PR
  body, once against a wrapped Markdown bullet where a `grep` reported *"not there"* for
  *"not looked at"*.
- ⛔ **Restricting to the `command` field was NOT enough, and the gap was measured rather than
  imagined.** `echo "git rev-parse --show-toplevel"` and `grep -n "git rev-parse …" f` both read
  **EXECUTED**: they are command fields, and they contain every anchor. ⇒ **Match on POSITION,
  not on presence.** Strip quoted spans, split on shell separators, take the first bare word of
  each segment — that is what was *invoked*. A command named inside a quoted argument occupies
  no command position, whatever quoted it. ★ Not a blocklist of `echo`/`grep`/`cat`: a blocklist
  enumerates the mentions you thought of. This is #36's rule — **match on something a mention
  cannot produce** — and the fourth independent rediscovery of it in this repo, alongside
  `DX.md` §19's positional last-line parse and matching `goals/` rather than the word `goal`.
- ⛔ **A limit you have MEASURED is a limit. A limit you have only DESCRIBED is a defect you
  have not looked at** — and it has no input that could contradict it, which makes it a control
  with no reachable failing state (#26) sitting in the section whose whole purpose is honesty.
  Measured: `bootstrap-audit.py` printed *"$NFORMA_ROLE is per-process and not cross-pane
  readable — UNMEASURED, not agreeing"* on every pane of every run. It was never run. `ps eww`
  reads any same-user process's environment; 37 variables came back from each of the nine live
  panes. ⇒ The tool emitted a **false UNKNOWN nine times per run and called it honesty.** The
  test transfers unchanged: *name the input that would falsify this limit.*
- ⚠ **Control the instrument on the population it is USED on, not on a convenient stand-in.**
  The env reader's known-positive was first built against `/bin/sleep` and failed: macOS returns
  **no environment at all** for SIP-protected system binaries. Had it happened to pass, it would
  have certified the reader on a process class it is never pointed at — #1's wrong-population
  defect, inside a control. It now runs against a live agent pane.
- ⛔ **An unresolvable input must not share a verdict with a clean negative** — the exit-2
  convention applied *inside* a function rather than at a process boundary. Measured by
  ARCHITECT against the position rule above: `sudo git push`, `xargs -I{} git push`,
  `echo $(git push)` and `if git push; then` all RUN the command and all read as *not found*.
  Every miss landed in the unknown bucket, which is safe for *"did this pane comply?"* and
  **unsafe for *"how widespread is non-compliance?"*** — it inflates the rate, and #20's content
  **is** a rate. ⇒ Same defect as the false positive above, pointed the other way, and invisible
  because it produces the finding you were already expecting. Split three ways: *only inside
  quotes* → `MENTIONED-ONLY` (text cannot run); *unquoted but not in a command position, or a
  command substitution* → `INDETERMINATE` (it may be wrapped, substituted, or an argument, and
  the parser cannot say). ★ Still not a blocklist: enumerating wrapper names would be one,
  **noticing that a segment has a shape you do not resolve is not.**
- **A mention is a third state, not a negative.** `MENTIONED-ONLY` means *no execution evidence*,
  which is not *evidence of no execution*. It counts as unknown and never as a pass.
- ⛔ **`git --work-tree=X checkout <ref> -- .` writes files to X and REWRITES THE CURRENT INDEX.**
  The flag redirects *where files land*, not *which index updates* — so the command reads as
  "operate over there" and half of it operates here. ⚠ No error, no warning, silent on success.
  Measured: it was discovered only when an unrelated `git rebase` refused with *"you have unstaged
  changes"* and ten files showed `MM`/`AD` that the author had never touched. ⇒ Use
  `git worktree add --detach <sha>` — a real second checkout with its own index. ★ And the reason
  it was recoverable is worth more than the rule: every commit had been pushed, so
  `git rev-parse HEAD` equalled the remote tip and `reset --hard` was provably free. **Before any
  destructive cleanup, establish what it would cost; the cheapest way to make that answerable is
  to have already pushed.**
- **Run an instrument at a NAMED REVISION, never from the shared tree.** `git worktree add --detach
  <sha>`, and read the revision back from the tool's own output. ⛔ The shared tree runs 40–70
  commits behind and `git fetch` moves `origin/main` without moving it, so running from it
  *silently executes an older tool*. Measured: a checker run from the shared tree reported the
  pre-fix behaviour and nearly produced a false *"the fix did not land"*. ⚠ Pinning the read is
  necessary and not sufficient — see #291: a single-file pin of any tool that imports a sibling
  fails with `ImportError`, and "fixing" that with `PYTHONPATH` pointed at the working tree
  silently unpins the sibling. Pin the **directory**.
- **No secrets in source.** Tools needing the Daintree token read it from the user's own MCP
  config at runtime; it appears in none of these files.
- **A detector needs both controls, and they are not interchangeable.** `fleet-context.py`'s
  shared-file flag once claimed in its own comment to exclude compactions; it did not, and on
  the live fleet **5 of 5 flags raised were compactions and 0 were shared files**. Removing a
  false positive is half a fix: a detector that stopped firing looks exactly like one with
  nothing to find. `test_fleet_context.py` therefore pins a **real** interleaved window
  (14 crossings, recorded from a transcript two panes actually shared) *and* a real
  compaction step, and both were verified to fail against a deliberately broken detector —
  over-firing is caught by the negative control, under-firing only by the positive one.
- **A per-turn signal read as a per-session property is almost never true.** `fleet-state.py`
  asked whether an agent's *latest* turn ended in a `STATE:` declaration. One session had
  emitted **61**, all positionally last, and the fleet reported **none** — its newest turn was
  mid-work, and a working agent is by definition between reports. The reader now walks back to
  the most recent turn that declared and **ages** it, because *declared two turns ago*,
  *never declared*, and *declared this turn* are three states and the middle one was being
  rendered as the second.
- ⚠ **Check that a known-positive is positive.** The fixture pinning that parser's positional
  rule quoted the token *mid-line*; the anchored regex rejects it on its own, so breaking the
  parser into a full keyword scan left the test green. **A control that cannot fail is not
  measuring the thing you named it after** — break the implementation and watch the specific
  case go red before believing it.
- **An identity read from a transcript can belong to somebody else.** `bootstrap_role`
  scanned every line for the first `You are <ROLE>`; its docstring said "the first user
  message". Measured on five live sessions, **4 of 5 matches were another agent's identity** —
  three injected by a recall hook that quotes other sessions' prompts, one from the session's
  own outbound dispatch text. ⚠ The contamination has a **sign**: recall and dispatch are what
  busy, well-connected agents do, so the agents most likely to be mislabelled are the ones
  doing the most cross-session work, and the column gives no hint the string came from
  elsewhere.
- **Derive the identifier; never enumerate it.** The same function matched a frozen list of
  five role names. This fleet runs at least two vocabularies — the bootstraps actually present
  include `CODER2`..`CODER5` and `TRIAGE` — so a session launched as `TRIAGE` read as having
  no bootstrap while one launched as `CODER2` was labelled `DX`.
- ⛔ **A break test must graft the REAL prior implementation, not a paraphrase of it.** The
  first attempt at breaking the above re-created the old behaviour by hand; it missed the
  record-type prefilter, and the two headline cases passed against a "broken" version that
  could not exhibit the bug. Copying the previous function in verbatim turned 2 failures into
  5. **A break you wrote from memory tests your memory.**
- **A difference is evidence only if one state does not differ from ITSELF.** `discriminates.py`
  exists to refuse a false *same* verdict and shipped unable to refuse a false *differ* one:
  `--a 'date +%N' --b 'date +%N'` — one state, a noise check — returned **✅ DISCRIMINATED,
  exit 0**. It had a known-DIFFERENT control and no known-SAME one. Each command is now read
  twice and must agree with itself. ⇒ **The two controls are not interchangeable and a tool
  needs both**, including the tool whose whole subject is that principle.
- ⚠ **A control pair is not verified to use the same check.** `--control-a 'echo 1'
  --control-b 'echo 2'` satisfies it while the real check is pure noise. Nothing in the tool can
  enforce that, so the ✅ line now prints the control commands and states what it did **not**
  establish — an unenforceable requirement should be visible, not implied.
- **A classifier that misses half of one kind of action does not report a smaller number —
  it reports a different verdict.** `wake-yield.py` counted `git commit` and `gh issue comment`
  but not `gh pr merge` or `gh api graphql … mutation`. Measured over a window whose contents
  were known by construction: **28 counted, 16 forge writes missed, a 36% undercount.** ⚠ The
  bias had a sign — the REST porcelain scored WORK, the same work through graphql scored churn.
  **The instrument was rewarding a calling convention, not an action.**
- **Name the coverage gap; do not fold it into the innocent bucket.** A shell mutates in
  unbounded ways, so the mutating list cannot be complete. What the classifier cannot see is now
  counted as `UNCLASSIFIED` and printed, and a session with unclassified actions gets **no
  verdict** instead of *"looked, did not act"*. Folding the gap into reads manufactured exactly
  the churn finding the tool exists to make trustworthy.
- ⚠ **Order matters in a classifier, and the test must pin the order.** `gh api` is on the
  read-only list only because the mutating tests run first. Moving the read test ahead of them
  turns every forge write into a read — two checks catch it.
- ⛔ **A break that crashes is not a break that was measured.** Running this suite against the
  shipped file printed **nothing**: the old version had no separable classifier, so it died on
  an AttributeError, and an empty result reads like a clean run. The faithful break grafts the
  old regex and branch **verbatim** and fails 7 checks.
- **An exit contract is part of the output, and a crash is outside it.** `daintree-control.py`
  documents `0 answering · 2 VOID`. Driven against a fake endpoint that completes the handshake
  and then returns each realistic outage shape — a proxy 502 page, a response with no `result`,
  tool content that is not JSON — **three of eight scenarios exited 1 with a traceback**. ⛔ `1`
  is neither value in the contract, so a caller branching on the documented pair mis-handles it,
  and it arrives under exactly the conditions the control exists for.
- ★ **6 of 6 tools had a live defect, each found by writing the first test it had ever had.**
  The one that already shipped with a proven failure path was no exception — but the paths it
  had exercised were all correct, and the defect sat in the three that were never exercised.
  **A proven failure path proves that path.**
- ⛔ **"6 of 6" was 6 of 13, and the error is the more useful finding.** That population came
  from an `ls` run against a checkout that was **many commits behind `origin/main`**. Seven
  tools — `bootstrap-audit`, `doctrine-version`, `grant-check`, `pane-binding`, `pipe-exit-scan`,
  `pretooluse-guard`, `stranded-branches` — had already landed and were invisible to it. The
  reading was correct; *"these are all the tools"* was not entitled. ⚠ Worse, a peer's issue
  said **"tools/ doubled to 12 tonight"**, I saw the disagreement with my own count, and
  explained it away rather than checking. **Enumerate the population against the remote, and
  when someone else's count disagrees with yours, one of you has a stale list — find out which
  before writing either number down.**
- ⛔ **"No hits" and "cannot fire" produce the same line and demand opposite work.**
  `pretooluse-guard.py`'s INVERTED rule was documented as *"the one worth having and the one
  with NO evidence: zero hits in the measured corpus."* Its lookahead was **backwards** — it
  required the zsh modifier char NOT to be followed by a word character, which is the
  **deliberate** form (`$file:t`) and excludes the **accident** (`$P:tools/…`, where `:t`
  swallows the rest). It fired on correct usage and stayed silent on silent corruption,
  including the exact example in its own docstring. ★ **105 real instances were sitting in the
  corpus it had been measured against.**
- **Check the rule against the shell, not against reasoning about the shell.** Every case above
  was settled by running it through `zsh` and reading what came out.
- ⛔ **A rate needs its population printed beside it.** `--measure` called its corpus *"the
  fleet's record of its own work"*; it scanned **every repository this machine has ever worked
  on** — 50 project dirs, of which the fleet held **14.3%** and the largest single contributor
  was an unrelated project at **19.6%**. The docstring had corrected an earlier rate for being
  quoted without its denominator, and its replacement was mis-denominated the other way.
- ⛔ **A bound the bounded party can raise is not a bound — including when it is a flag.**
  `grant-check.py` states as non-optional that it reads `origin/main` after fetching, *never*
  the working tree, because *"an agent could resurrect an expired or revoked grant by checking
  out an older commit."* It then shipped `--ref`, honoured by the query, warned about only in
  help text. Demonstrated with **no forgery and no local edit** — just naming the parent of the
  commit that revoked a grant, on the remote's own history:

  ```
  --ref <tip>     NO LIVE GRANT  REVOKED demo-001   exit 1
  --ref <tip~1>   LIVE  demo-001  DEMO may merge …  exit 0
  ```

  ⇒ The checkout route was closed and an identical one left open on the command line. **The
  bounded party is the one typing the command.** A redemption query now takes no ref; `--list`
  keeps it, because a listing authorizes nothing.
- ⚠ **A required field that nothing enforces reads as a live budget.** `uses:` is mandatory in
  every grant record and is counted by no one — redemption is not observable to the checker.
  It is now printed with `NOT ENFORCED` beside it rather than bare.
- ⛔ **A break test can fail for a harness reason and read as a defect.** The suite above ran the
  tool's own self-test from a path derived from the tool's location; when the break copies the
  tool elsewhere, that path has no `grants/` store, and the resulting failure looked like a
  sixth defect. It was a portability bug in the test. **Check what a red actually proves before
  counting it** — 6 became 5.
- ⛔ **Two matchers for one idiom, in one directory, disagreeing.** `pretooluse-guard.py` splits
  a command on separators and asks whether the segment *immediately before* the `$?` is piped —
  because `cmd | look; cmd >/dev/null; echo $?` is the **correct** idiom and firing on it teaches
  an agent to stop doing the right thing. `pipe-exit-scan.py` had only the regex, and it is the
  one wired to the scanner people read. Porting the refinement dropped the fleet-scoped count
  from **251 to 159 — 37% of its findings were the correct form.**
- ⛔ **A citation outlives the number it cites.** `pipe-exit-scan.py` quoted its sibling's
  *"1.5% fire fleet-wide (25 of 1720)"* — a figure the sibling has since retracted as
  mis-denominated over every project on the machine, with a corpus that no longer reproduces
  (179,216 today). The citation is now marked retracted **in the tool that carries it**, not
  only in the tool that issued it.
- ⚠ **A docstring containing `\$?` needs an r-string.** It emitted a `SyntaxWarning` on every
  import and would be an error in a future Python.
- ⛔ **A break that crashes reads exactly like a clean pass — three times tonight.** The suite
  above called a function the previous version does not have, so it aborted before its
  assertions and printed nothing. It now resolves that function with `getattr` and a fallback to
  the OLD behaviour, so the break **fails on the assertion** instead of dying. Check that a break
  produced output before believing it.
- ⛔ **A list endpoint answers "more than exists" with everything and "less" with a silent
  prefix.** `stranded-branches.py` asked `gh pr list --limit 100`. Measured 2026-08-20:

  | repo | merged PRs | seen |
  | --- | --- | --- |
  | nForma-NEXT | 69 | 69 |
  | df-wiki | 178 | **100** |
  | Blazing-Back | **775** | **100** |

  ⇒ On the repository with the actual branch churn it swept **13% of the population** and
  reported `0 stranded, exit 0` about the rest. Its own docstring says *"a denominator that
  silently excludes part of its population is how '0 stranded' gets believed"* — correct, and
  one level too shallow. It guarded the **error** path and left **truncation** open.
- ★ **Apply the tool's asymmetry to its population, not just its verdicts.** A positive finding
  survives a partial sweep — a ref found stranded in the prefix is still stranded. A negative
  does not. `verdict_exit(n, truncated)` is extracted precisely so the branch that matters —
  *truncated and nothing found* — can be tested without a repository; it is the hardest state
  to produce against a live remote, which is how it shipped unwritten.
- ⛔ **A break that stops early under-reports — the quieter cousin of one that prints nothing.**
  This suite's first break aborted on a `TypeError` from an older signature and showed 2 of the
  5 real failures. Guard every call that a previous version cannot satisfy.
- ⛔ **A success state that cannot occur trains its reader to ignore the exit code.**
  `pane-binding.py` exited 0 only when *every* pane was BOUND — and the Daintree state files
  hold 30 closed panes from past sessions, so a clean verdict was impossible forever. It is the
  mirror of a falsifier that cannot fire. `PARTIAL` is the actionable state (the join was
  **attempted** and half-landed); `UNBOUND` means no leg at all, which is the expected condition
  of every pane launched before the fix.
- ★★★ **A control fired positive and nobody read it.** That file's stated purpose is *"the
  known-positive control for the launcher fix: run it before and after adding `--session-id`,
  and BOUND rows appearing is the evidence the fix worked."* The rows appeared — **13 BOUND**,
  including every fleet role — while its docstring still said *"the join has never been observed
  working"* and its self-test rationale still said *"today the live population contains no
  BOUND."* ⇒ **Run the control; do not read the prose beside it.**
- ★★ **And the exact join answers a question another tool reports as unanswerable.**
  `fleet-context.py` prints *"TEAMLEAD and DEV2 are BOTH satisfied by session e4a7769d … one of
  them is UNVERIFIED"* on every sweep. The binding resolves it: the pane **titled** `TEAMLEAD`
  holds `e4a7769d`, whose **registry name** is `DEV2` — a title-versus-registry disagreement on
  one exactly-bound pane, not an unresolvable identity. The answer was in Daintree's state file
  while the roster check fell back to self-reported names.
- ★★★ **A workaround outlives the premise that justified it.** `fleet-identity.py` joins
  sessions to panes by **content** — rare tokens against pane scrollback — because when it was
  written *no pane carried Daintree's `agentSessionId`*, and that state was recorded as
  permanent. Re-measured 2026-08-20: **13 panes are exactly bound, including every fleet role.**
  Wiring the exact join in took the tool from **5 of 12** sessions resolved to **10 of 12** —
  and the rows it gained are the ones content matching could not reach, because a pane with a
  single token hit is unresolvable by overlap and unambiguous by binding.
  ⇒ **When a tool works around an absence, put the check for that absence in the tool.**
- ★ **Two kinds of evidence get two verdicts.** `EXACT` and `RESOLVED` are not merged, and where
  both exist and disagree the losing content match is **printed** — two joins disagreeing is a
  finding, and silently preferring one is how a wrong identity becomes a fact.
- ⛔ **A source-text assertion is not a behavioural one.** The first version of that suite
  checked `'"EXACT"' in src` — which a comment would satisfy. `pane_verdict()` is extracted so
  the precedence can be tested by calling it, the same move that made `verdict_exit()` testable
  in `stranded-branches.py`. **If the only thing a test can assert is that a string appears in
  the file, the logic is in the wrong place.**
- ★★★ **13 of 13. The tool I could not fault had a defect, and my own falsifier named it.**
  `bootstrap-audit.py` was the single clean result of the audit; the register row recording that
  stated the likelier falsifier as *"a defect I missed in the one I passed."* It fired within the
  hour. Its step classifier read `cmd.lstrip().startswith("/")` as *"names a built-in slash
  command"* — true of `/rename DEV2`, false of every absolute path:

  ```
  /rename DEV2                              -> UNEXECUTABLE   correct
  /usr/bin/git rev-parse --abbrev-ref HEAD  -> UNEXECUTABLE   ⛔ WRONG
  ```

  ⛔ And `UNEXECUTABLE` is not a shrug — it asserts *"no execution record CAN exist"*, the
  strongest claim in that file's vocabulary, about a step whose matching call **was in the very
  list passed to the function.** The evidence sat one argument away and the rule never looked.
  ⇒ Same shape as two others here: **a restriction asserted in prose that the code implements
  as something broader.** A slash command is a bare word; a path has a separator inside it.
- ★ **The clean result was a property of my search, not the tool** — which is what the register
  row said, and it is worth trusting that kind of caveat enough to go back and test it.
- ⛔ **A rule that lives in a report gets re-derived wrong.** `ci-log-clean.py` exists because
  *"drop the echoed `run:` block BEFORE stripping ANSI"* was a sentence in a wiki page and in a
  friction report, and a sentence cannot be piped into. `grep -c FAILED` returned **4 on a job
  whose conclusion was SUCCESS** — all four were the echoed script declaring `FAILED_FILES`.
- ⚠ **And the escape is not the one you would reach for.** Measured on a real 153 KB
  `gh run view --log`: **0** real `\x1b` bytes, **218** literal `^[` pairs. Stripping
  `\x1b\[[0-9;]*m` removes nothing and looks like it worked. Both forms are handled.
- ★ **The order cannot be reversed, so the tool refuses rather than guessing.** The cyan-bold
  marker is the only thing separating the echoed block from real output — the words are
  identical. With ANSI already stripped and no `##[group]Run` envelope left, there is nothing to
  discriminate on, and returning the log unchanged is how a count of the script becomes a count
  of the output. Exit 2.
- ⛔ **`per_page=100` is a reflex, not a check.** `gh api …/check-runs` returns **30 of 54** by
  default, carries `total_count: 54`, and a filter over `.check_runs[]` answers about a set it
  never saw — it once **hid a required-check failure**. `gh-complete.py` compares the stated
  count against the array received and **refuses**. ⚠ It deliberately does not paginate for you:
  fetching the rest is a different decision with a different cost, and making it silently would
  hide the truncation the tool exists to surface.
- ★ **And the endpoint most people reach for cannot be checked at all.** `repos/…/pulls` returns
  a **bare array with no stated total**, so completeness is unestablishable from it. The tool
  exits 2 there. That is its limit, not its feature — a helper that cannot rescue every call
  should say which ones.
- ⚠ **The rule existed in a wiki page and a friction report for hours while I merged PRs by
  reading `check-runs` directly.** The audit afterwards found `total_count == length` on all
  thirteen queries — **repo size, not care.** A rule you have read and still not applied is a
  rule that needed to be executable.
- **Zero is a value; unknown is not.** An assistant record can carry a usage block that is
  present and entirely zero. Summed blindly, one such record rendered a session as `0 tokens,
  0.0%` — the safest-looking row in the table, for a session whose depth was in fact unknown.

- ⛔ **The ⛔/✅ glyphs in this file are CONTENT, not formatting.** They carry the polarity of a
  block — *this is the broken form* vs *this is the correct one* — and **no text matcher can
  recover it from the prose.** `use-not-mention.py` resolves Python call edges to a sink and has
  nothing to resolve in markdown; there is no call graph here. ⇒ Anyone who strips or normalises
  these marks **blinds every future control over this file without changing a word of its text**,
  and the file will still read correctly to a human, which is what makes it silent.
- ★ **Prefer the control whose failure mode is a false PASS over one guaranteed to fire on the
  repaired state.** Measured 2026-08-20 (#291): the obvious control for a documented-forbidden
  command is to grep for it and fail on a hit. That control is **void**, because naming a broken
  command means writing it down — after the fix, **the document that forbids the form is the top
  hit for it.** The sweep returned 2 hits at `origin/main` and both were mentions: this file's own
  counter-example, and a quoted pointer message in `pointer-verified.py`. ⚠ The author of that
  sweep began drafting a fix for the counter-example *inside the block that forbids it*.
  ⇒ Key on the **presence of the correct form** instead (`check-orientation.py`,
  `check_pin_doctrine`). An absence-check gets **louder the better the documentation gets**; a
  presence-check degrades quietly and only ever under-reports. ⚠ Stated limit, not a defect:
  presence is also satisfiable by a mention — that is the price, and it is the cheaper error.

## Running the checks

```
python3 tools/test_fleet_context.py     # exit 0 = pass, 1 = a control failed
python3 tools/test_fleet_state.py
python3 tools/test_fleet_identity.py
python3 tools/test_discriminates.py
python3 tools/test_wake_yield.py
python3 tools/test_daintree_control.py
python3 tools/test_pretooluse_guard.py
python3 tools/test_grant_check.py
python3 tools/test_pipe_exit_scan.py
python3 tools/test_stranded_branches.py
python3 tools/test_pane_binding.py
python3 tools/test_fleet_identity_exact.py
python3 tools/test_bootstrap_audit.py
python3 tools/test_ci_log_clean.py
python3 tools/test_gh_complete.py
```

⚠ ~~**Nothing runs this automatically** — this repo has no CI.~~ ⛔ **FALSE since
2026-08-20 (#272): `hermetic suites (gating)` is a required check and runs the listed suites on
every PR.** A suite NOT in that list is still unrun, and is reported `UNLISTED, therefore UNRUN`
rather than as an error. The suite is a control that only
fires when someone invokes it, which is the failure mode it was written to catch. Run it after
any change under `tools/`.

**`estate-provenance.py`** — reads a path and asks whether its provenance evidence points at this estate or another. ⛔ The issue range is **derived** from this repo's own `git log`, cut at its largest interior gap — hardcoding a ceiling silently reclassifies every file the day the repo reaches it. Reports **three** states: `LOCAL` · `FOREIGN` · `UNCLAIMED`, because absence of a foreign marker is not presence of a local one. ⚠ **It cannot establish DIRECTION** — a file citing another estate's issue may be theirs committed here, ours written about theirs, or dual-use — and it prints that limit on every run rather than only here.
