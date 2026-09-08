# Handoff — what landed, what is broken, and what would falsify each claim

*Written by TEAMLEAD (session `a10daa24`) 2026-08-21 ~04:00Z. **Every figure below carries the date
it was measured. A number without one is a rumour** — `CLAUDE.md`'s rule, applied to this file.*

⛔ **This file exists because doctrine delivery in this fleet runs through one pane, and that was
measured rather than feared:** `main` took **zero commits in two hours** while that pane was busy
elsewhere. Panes finish a turn and nothing re-invokes them. **Read this instead of asking it.**

---

## What is true right now

*Measured **2026-09-07 17:21Z** on `origin/main`. **Every line names the command that produces it** — run those, do not cite this block, and `scripts/check-handoff-rows.py` now RUNS each one and reports DRIFTED / MISMATCH / UNRUNNABLE per row (#637).*

⚠ *Every count uses `--limit 1000`: the default page size equals the returned count, so truncation is
silent — that is how `30` was once read for a population of `85`.*

```
merged PRs        458    gh pr list --state merged --limit 1000 --json number --jq length
open issues       103    gh issue list --state open  --limit 1000 --json number --jq length
open PRs          0      gh pr list --state open   --limit 1000 --json number --jq length
main CI rollup    success gh run list --branch main --limit 1 --json conclusion
quarantine        25     grep -c '^tools/' tools/QUARANTINE.txt
close conditions  NONE 0 · BURIED 0 · BODY 103    python3 tools/close-condition-scan.py
                         ⇒ exit 0 for the first time: EVERY open issue carries a clause in its body
runnable          ASSERTED 47 · RUNNABLE 25 · NO-CONDITION 31   python3 tools/runnable-condition.py
no close path     OPERATOR 9                      python3 tools/close-mechanism.py
                         ⚠ 21 → 9. `NO-CONDITION` is no longer printed at all, because the
                         count is 0 — so naming it here would MISMATCH. This row read
                         `21 of 103` until today, a SUM the tool never printed (#637).
gating job        76s      gh run view <id> --json jobs   (job "hermetic suites (gating)")
```

⇒ **THE `NONE` SET IS EMPTY — and the set recorded yesterday is what makes that statement exact.**
*(measured 2026-09-07 17:21Z)*

```
NONE  (none)
```

⛔ **THE FIRST USE OF THIS BLOCK'S OWN DESIGN, and it worked.** Yesterday's entry argued that *a dated
count is attributable but not checkable, and a dated SET is diffable.* Today the set moved, and the
diff is exact rather than merely large:

```
LEFT the NONE set (13)   4 · 38 · 48 · 49 · 136 · 405 · 431 · 451 · 502 · 532 · 558 · 582 · 583
ENTERED (0)              none
```

★ **A count could only have said `13 → 0`.** The set says WHICH thirteen — and, because nothing
entered, that they all moved for one reason rather than thirteen issues being repaired while
thirteen others silently lost their conditions. That second reading is exactly what the 2026-08-21
snapshot could not rule out, and it is why *at least 3* was unresolvable there.

⚠ **What moved them was an edit, not a repair of the fleet.** TEAMLEAD appended a close condition to
each of the thirteen bodies, derived from each issue's own content: a REPORT is discharged when its
findings are ROUTED, and an OPERATOR-owned issue's condition STATES the ruling without taking it.
`tools/close-condition-scan.py` scores presence, never quality — see its own bound.

⇒ **THE PREVIOUS `NONE` SET, STRUCK RATHER THAN DELETED.**
*(`python3 tools/close-condition-scan.py --by-state` — it prints one `STATE number` row
per issue and NO totals; the aggregate row above comes from the plain scan. Two commands,
one population, taken in the same minute.)*

```
NONE  4 · 38 · 48 · 49 · 136 · 405 · 431 · 451 · 502 · 532 · 558 · 582 · 583
```

⛔ **Why the set and not just the number.** Measured 2026-09-07: the 2026-08-21 snapshot said
`NONE 8` of 111. At **2026-09-07 13:16Z** it was `NONE 13` of 103, and **11 of those 13 were survivors of that same 111** —
so at least **3** issues carried a condition then and do not now, *or* the 8 was wrong. **Neither can
be checked**, because `gh` exposes no body-edit history: the timeline carries labels, closures and
references, never what a body said last month.

⇒ **A dated count over issue bodies is attributable but not checkable.** A dated SET is diffable — run
`--by-state` and compare against the list above, and you learn exactly *which* issues moved rather
than only *how many*. That is the difference this line exists to buy, and it is the one repair
available without body history.

⚠ **Neither candidate cause accounts for it — and one of them is a partial contributor, named
rather than dismissed.**
*Composition* — among the **26 issues CLOSED since 2026-08-21**, 23 carried a condition (88%); among
the **103 open TODAY**, 90 do (87%). Two different populations, one point apart. No statistical test
was run and none is claimed: a one-point gap on a 26-issue population is simply not evidence that
closing was selecting for issues that had conditions.
*New filings* — **2 of the 13**, #582 (2026-08-25) and #583 (2026-09-04), were filed after the
snapshot, so new filings DO contribute two of today's `NONE`. They cannot contribute the rest: strike
both and **11** survivors remain, against a total of **8** `NONE` in the entire population then. The
residual above is what is left AFTER granting new filings in full.

⛔ **THE PREVIOUS SNAPSHOT, STRUCK RATHER THAN DELETED — it stood for 17 days and the drift is the
point.** *(measured 2026-08-21 08:59Z)*

> ~~merged PRs 329 · open issues 111 · open PRs 0~~
> ~~quarantine 23 of 23 files recorded~~
> ~~close conditions  NONE 8 · BURIED 0 · BODY 98~~
> ~~runnable  ASSERTED 38 · RUNNABLE 34 · NO-CONDITION 34~~
> ~~no close condition 16 of 111~~
> ~~gating job ~185s +-2s~~

⇒ **What moved, and two of the three directions are not the flattering one:**

- ⛔ **Closeability got WORSE.** `BODY 98 → 90` and `NONE 8 → 13` over 17 days: **five more open issues
  now carry no close condition at all**, and eight fewer carry one in the body. The board grew less
  closeable while merged PRs went 329 → 454.
- ⛔ **`RUNNABLE 34 → 25` and `NO-CONDITION 34 → 44`.** The second dimension agrees with the first about
  the direction, which is the only reason to quote both.
- ★ **The gating job went `~185s → 76s`** — 2.4× faster. That is the one line that improved, and it
  improved without anyone reporting it here.
- ⚠ `quarantine 23 → 25` is **not** two new estate violations: it is two rows added when the record was
  scoped to the ruled directory. Read `tools/QUARANTINE.txt`, not this line.

⚠ **AND THIS BLOCK HAS NO CALLER.** It carried a 17-day-old picture under the heading *"What is true
right now"*, in the file that says **"Read this instead of asking it."** #272's rule is that a dated
claim needs a **re-measuring caller**, not a fresher date — and re-dating it is exactly what I have
just done. ⇒ **Every command that produced a line above is named beside it. Run them; do not cite this
block.** The next reader will be reading a photograph too.

⚠ **`BODY 98` is PRESENCE ONLY** — `close-condition-scan.py` says so in its own output. It is not 98
good conditions. `runnable-condition.py` is the second dimension and it disagrees with the first by
construction; **neither is "the" number** and both name their predicate.

## ⛔ KNOWN-BROKEN, with the command that shows it

| what | reproduce | status |
|---|---|---|
| ~~`tools/index-watch.py --self-test` **hangs**~~ | `python3 tools/index-watch.py --self-test` | ✅ **FIXED** — exits 0 in 13.3s, re-measured 2026-09-07 |
| ~~**24 of 48 controls establish nothing**~~ | `SUBJ_DIR=tools ./scripts/gate-selftests.sh` | ✅ **FIXED** — `63 subjects · 48 passed · 0 FAILED · 0 UNESTABLISHED · 1 UNVERIFIABLE` |
| ~~`bootstrap-audit.py`'s control **FAILS**~~ | same command | ✅ **FIXED** — `0 FAILED`; its own `--self-test` exits 0 and the control block passes |
| ~~`use-not-mention.py` is **UNVERIFIABLE**~~ | `python3 tools/use-not-mention.py --zzz-not-a-flag` | ✅ **FIXED** — exits **2**, not 0 |
| `pretooluse-guard.py` is **UNVERIFIABLE** | `python3 tools/pretooluse-guard.py --zzz-not-a-flag` → exits **0** | ⛔ live — the gate names it, and it is the only one |
| estate vocabulary is a **closed list** | `scripts/check-tools-index.py:158` | ⛔ live — a novel estate reads as LOCAL (#348) |

⛔ **FOUR OF THE FIVE ROWS THIS TABLE HELD BEFORE 2026-09-07 WERE STALE, in the file a successor
is pointed at FIRST.** The table now shows SIX rows — the four struck ones, the `pretooluse-guard.py`
row that replaced `use-not-mention.py`, and `estate vocabulary`, which was the one of the original
five that still holds. Struck
rather than deleted, because the drift is the point: each said `⛔ live on main` about a defect that
had been fixed, and #451 §5 says *"point a successor at `docs/HANDOFF.md` before anything else"* —
so a successor inherited four defects that no longer existed. Re-measured 2026-09-07, every row by
its own command.

★ **AND THE BARE COMMAND WAS THE WRONG COMMAND, which #451 §1 warned about in this file's own
lineage.** `bash scripts/gate-selftests.sh` reports `ran 6 subject(s)`; `SUBJ_DIR=tools
./scripts/gate-selftests.sh` — the form CI runs — reports `ran 63`. Measured in the same minute.
⇒ *The reproduction command is not the script name*, and a row citing the bare form measures a
tenth of the population it claims to.

## ⚠ `gh` and harness traps relayed from #582 — which ones I could reproduce HERE

#582 relayed 24 defects from a 20-hour session on another estate. **14 of them (§B shell, §C `gh`)
are estate-independent** and cost a pane here the same. Six were already recorded in this tree; the
rest are below, split by whether I could reproduce them from this pane rather than by whether they
sounded true.

**All rows measured 2026-09-08 01:54Z**, on this machine, by the command in the row. ⚠ A number without a date
is a rumour and a verdict without its validator establishes nothing — so each carries both.

| | claim | reproduced here? — with the command |
|---|---|---|
| **C7** | `gh api … \| head -c N` truncates via SIGPIPE and yields "corrupt JSON" that is nothing of the sort | ✅ **YES.** `gh api repos/nForma-AI/nForma-NEXT/issues/1 \| head -c 120 > f` → `json.load(f)` raises `JSONDecodeError: Unterminated string starting at: line 1 column 87`. ⛔ CONTROL: the same call redirected to a file first parses, **9,318 bytes**, `issue #1`. ⇒ **Write to a file, then read.** |
| **B4a** | no clean wait primitive; a long call hits the harness ceiling | ✅ **YES.** `ls .../tasks/*.output \| wc -l` → **29** backgrounded-command outputs in this session, each one a call that crossed the 120s cap |
| **B4b** | *"foreground `sleep` is blocked"* | ⛔ **NO.** `sleep 2; echo $?` → **0**. ⛔ CONTROL: `true; echo $?` → 0, so the probe can report a success. **Relayed and not reproduced** — recorded as refuted rather than repeated |
| **C1** | run logs are unavailable while the run is `in_progress`, **even for a job that has already failed** — cost ~40 min of blocked diagnosis | ⚠ relayed; needs a live in-progress run with a failed sibling, which I cannot force |
| **C2** | `gh run rerun --job <id>` is rejected while the run is `in_progress` | ⚠ relayed, same reason |
| **C4** | `gh run rerun --failed` re-runs CONSUMERS but not PROVISIONERS | ⚠ relayed; no ephemeral-runner pool here to test against |

⛔ **B6/B7 (two `ruff` versions; `check` and `format --check` are separate gates) are FOREIGN.** This
repository has no `ruff.toml` and no `pyproject.toml` — there is nothing here for them to be true of.
⇒ They belong to the estate that filed them.

★ **THE SPLIT IS THE POINT.** A relayed defect is a claim about ANOTHER machine until someone runs it
on this one. Two of the six changed status under that test: C7 became a reproduction with a command
attached, and B4b became **refuted** — and B4b is the one my own harness notes assert. ⇒ *Neither
the source nor the local documentation is evidence; the run is.*

## ⚠ Reading a pane's context % — the default `lines` does not reach it

⛔ **The only place this was written down was a QUARANTINED script.** #451 §1 recorded it as a
workaround *"written nowhere else"* — `terminal.getStatus` needs `lines: 4`, *"1 and 2 omit it"* —
and an audit on 2026-09-07 found 7 of its 8 §1–§2 items durable and this one not: the sole match in
the tree was `tools/teamlead/boxwatch.sh`, which sits under `tools/QUARANTINE.txt` and whose
belonging is an open question. **A fact recorded only in a quarantined file is not recorded.**

⇒ **AND THE RECORDED NUMBER IS WRONG.** Re-measured 2026-09-07 against a live pane, one call per
value:

```
lines: 1   ⏵⏵ bypass permissions on · 1 monitor …           ⛔ no context %
lines: 2   ⊘ codex-1 │ ⊘ codex-2 │ …  + the bar             ⛔ no context %
lines: 3   Opus 5 │ … ███████░░░ 76% (756K) │ …             ✅ present
lines: 4   a ─── separator, then the same three             ✅ present
```

**The boundary is 3, not 4.** The `[re-verified]` tag in #451 travelled with a figure that was one
too high.

★ **AND A FIXED NUMBER IS THE WRONG THING TO RECORD, which is why this entry is phrased as it is.**
The percentage lives in the pane's status BLOCK, and how many lines that block occupies depends on
what the pane is rendering — this one showed a separator at 4 and none at 3. ⇒ **Ask for `lines` ≥ 3
and CHECK the `%` is in `recentOutput`; do not trust a constant.** A number recorded here would rot
the same way `4` did, and rot silently: a short read returns a well-formed status object with the
percentage simply absent.

⚠ Measured on one pane, one moment. It establishes the default is too small and that 3 sufficed
there — not a floor that holds for every pane.

## ⛔ Numbers WITHDRAWN tonight, and why — this section is the point of the file

```
TEAMLEAD "13 estate files"        count → FLOOR. No bare-slug pattern was run.
TEAMLEAD "LIVE-PANES never varies"  read from a 20-line tail of a 197-line file. It varies 4–8.
TEAMLEAD "the 11 ungated controls are gated"  4 were. Population A ≠ A∪C.
TEAMLEAD "no self-service path at all"  refuted; solicitation is a MAJORITY, not a monopoly.
TEAMLEAD "half the doctrine is misplaced"  INFERENCE from one data point. Never established.
DEV3     "40 hits" · "zero hits" · "19 NO CONTROL" · "38% unsolicited"   all withdrawn by author
ARCHITECT "documents do NOT deliver"  → "deliver UNRELIABLY". "zero" made a cleaner dichotomy.
```

⇒ **Every one was caught by a peer or a control, none by the author's care.** ⚠ **If you are reading
this to find a number to act on, prefer one produced by an instrument in the gating path** — that is
criterion 4 as amended (`a caller that still runs it`), and it is the only class of figure that
survived the night.

## ⛔ Filed against myself tonight, because a successor will hit it

**#461 — `role:` and `dev:N` are two queryable owners with no precedence rule.** At 04:25Z I
labelled 23 unrouted issues with `role:`, closing a real gap: a pane asking *"what is mine?"* was
getting a partial answer with no way to detect the partiality. ⛔ **`dev:N` already existed as an
assignment axis and I did not check it.** 15 open issues now name different owners on the two axes,
and **all 15 are mine**.

⚠ The sharp case already bit: **#319, the quarantined estate item, carried `role:OPERATOR` AND
`dev:2`** — a pane running its own queue query was being told *by the board* to work inside a
quarantine the operator reserved. `dev:2` removed 04:49Z, reason recorded on the issue. ⇒ That one
was a hazard and the other 15 are ambiguity; **the difference is luck about which issue collided.**

★ The lesson is not "check both labels." It is that **making routing queryable does not help if two
queries return different owners and nothing states which wins.** The precedence rule is unwritten,
belongs in `goals/README.md`, and is deliberately **not** written by the pane that broke it.

⚠ **#461's close condition has a trap stated in the issue**: its third leg — *the disagreement query
returns 0* — can be satisfied by stripping labels with no rule in place, which reproduces the
original gap with a clean-looking board. **A zero on leg 3 without leg 1 is the failure, not the fix.**

## ⛔ AND IT HAS NOT PRODUCED SINCE — 19 days, on TWO independent mechanisms

*Measured 2026-09-08 06:17Z. The section below is about a stall of MINUTES on 2026-08-20. This is about
the period since.*

```
MECHANISM 1 — forge artifacts (remote, output-side)
  tools/fleet-output.py     TEAMLEAD 41 signed · ARCHITECT DEVOPS DX DEV1-5 all SILENT
  friction reports          16 on the board · newest 2026-08-25 · 15 of 16 are 19-20 days
                            old · ZERO filed in the last 14 days

MECHANISM 2 — the local pane registry (session-side)
  tools/bootstrap-audit.py  Summary: 9 roles · 8 negative · 1 unknown
                            NEGATIVE = "no-session — no registry row for this role"
```

⚠ **TWO mechanisms, not three, and the distinction matters.** `fleet-output` and the friction-age
reading both read the FORGE — they are one witness looking at two of its fields, not two witnesses.
`bootstrap-audit` reads the local registry, which fails for unrelated reasons. ⇒ The agreement is
worth something because those two can fail independently; counting the forge twice would have
inflated the evidence.

★ **Each instrument reports its own blind spot rather than concluding.** `fleet-output` prints
*"SILENT means only 'no SIGNED artifact in this window'"* beside every verdict — 34 of 75 comments
in its window carry no signature at all. `bootstrap-audit` prints *"UNKNOWN is not a pass"*. Neither
says the fleet is dead; together they say **nothing role-named has produced a signed artifact or
held a registry row for 19 days.**

⛔ **What this does NOT establish:** why. A fleet that was never relaunched and one that runs and
signs nothing are indistinguishable from here — and `tools/fleet-state.py` says so in its own words,
exiting 2: *"They may be silent, unlaunched, or never given the prompt — this cannot tell."*

⇒ **The operator is the only party who can tell those apart.** Not filed as an issue: there is no
defect established, only an absence, and an absence with two readings is not a finding.

## ⛔ THE FLEET STOPPED PRODUCING AT ~07:16Z, AND THE MONITOR DID NOT SEE IT

**Measured 08:54Z.** Two legs per pane — file mtime versus the newest **timestamped record**:

```
pane        file-mtime   last RECORD    gap
DEV5              8m           8m         0
ARCHITECT         5m           5m         0
DEV4 (this pane)  0m           0m         0
DEV2              7m           7m         0
DEV1             21m          38m        17m   ⚠
DX               22m          74m        52m   ⚠
DEVOPS           20m         140m       120m   ⚠
DEV3             21m         258m       238m   ⚠  4.3 HOURS
```

⇒ Throughout, the fleet monitor reported **`LIVE-PANES=8`**. It keys on **live sockets**, and a
socket outlives the pane's usefulness. ⛔ **Socket presence is not liveness** — filed as **#489**
with a close condition whose load-bearing half is the known-negative.

**PR creation gaps — the right predicate, since merge gaps conflate a stalled merger with an
empty queue:**

```
all night (18:00Z+)   n=147   median 1.8   p90  8.1   max 173.7   current 98m — exceeded by 2/147
last 6h               n= 36   median 4.8   p90 12.4   max  18.0   current 98m — exceeded by 0/36
```

★ In the matched window the previous maximum was **18 minutes**. It survives the population
correction rather than dissolving under it.

⚠ **CAUSE NOT ESTABLISHED.** Context exhaustion is the obvious candidate (#302 records four stalls
at 89–100%) but **no pane here has been shown to be at any context level** — a pane cannot read
another's, and #242 established the instrument that tries divides by a wrong denominator. ⛔ Do not
repeat "the fleet ran out of context" as though it were measured.

⇒ **Nothing was lost.** Zero open PRs, `main` green, every open thread owned with a close condition.

## ⇒ The FOUR guards on the merge loop, each added after it cost something

```
reviews read before merge     ← a review was merged over; CI status cannot carry an objection
base must be main             ← a stacked PR's squash orphans (2 of 287, perfect predictor)
ancestry verified after merge ← `MERGED` is not `landed`; verify by content, not by exit code
gating run POST-dates THE GATE ← added 04:45Z, CORRECTED 06:20Z. A check older than the
                                 last change to `.github/workflows` or `scripts/gate-*.sh`
                                 establishes nothing about the gate it must pass.
```

⛔ **GUARD 5 WAS WITHDRAWN THE SAME DAY IT WAS ADDED. It measured BRANCH AGE, not content loss.**
It refused every open PR on the board and every one was a net addition:

```
                two-dot (what guard 5 used)   three-dot     ACTUAL MERGE (merge-tree)
#499  119 ins,  907 deletions                 68 ins, 2 del      68 ins, 2 del
#507   76 ins,  224 deletions                 61 ins,13 del      61 ins,13 del
#511   49 ins,  171 deletions                 36 ins, 3 del             —
```

⇒ **`git diff main..head` counts every line MAIN has gained since the branch's base as a deletion.**
A merge applies the **three-dot** diff — it uses the merge base — so the "709-line revert" I blocked
#509 on **was never going to happen**. ⚠ ARCHITECT further showed by controlled experiment that the
genuinely dangerous case (rewriting a file main has grown) **CONFLICTS** — `mergeStateStatus` reads
`DIRTY`, not `CLEAN`. ⛔ **The four guards passed #509 because there was nothing to catch.**

★ **This is CLASS C in the guard itself**: `git diff --stat main <head>` answers *"how does this TREE
differ from main"* and merging answers *"what will be ADDED"*. **Both numbers were correct and they
answer different questions.**

⚠ **And it was my own recorded trap, used backwards** — two-dot versus three-dot is filed earlier in
this session as a defect I hit and named. ⛔ ⇒ A guard built on a number you have already been taught
not to trust is worse than no guard, because it refuses real work with a confident figure.

⚠ **What is NOT settled** — #509's branch was updated before merging, so the state I reacted to is
**gone from every ref**. ARCHITECT's experiments are analogues on real history, not the instance.
⇒ And the hazard would be real if this repository ever merged by a path that is not a merge —
**"rebase and merge" replays commits and is not merge-base-aware the same way.** That is DEVOPS's
question and it is open on #510.

⛔ **GUARD 4's FIRST FORM WAS SELF-DEFEATING AND BLOCKED THE WHOLE QUEUE.** It compared the check
against **main's HEAD**, so every merge invalidated every other PR. Measured 06:19Z: #453 merged,
and all **ten** remaining PRs immediately read STALE. ⇒ **The queue could never drain** — each merge
staleness-blocked the rest. ★ I had built `strict: true` semantics by accident, in prose, and worse
than the real thing, because GitHub at least re-runs.

```
last change to THE GATE   2026-08-21T04:29:01Z   (757e8d1, #444)
main HEAD                 2026-08-21T06:19:11Z   ⇒ hours apart
```

⚠ The guard was right about the **hazard** and wrong about the **population it applied to** — a
sound predicate over the wrong set, which is #403's shape. ⛔ **It failed CONSERVATIVELY, which is
why it went unnoticed for two hours**: a blocked queue looks like a guard working.

⚠ **All four are prose in a pane, not controls. They die with this session.** ⛔ And guard 4 was
*itself* defective on its first run: `git log --format=%cI` returns a **local** offset
(`05:41:21+01:00`) while check timestamps are **UTC** (`04:43:38Z`), so the lexical compare produced
a **false refusal** on #456. Two valid ISO-8601 strings are not comparable across offsets. Normalise
with `TZ=UTC git log -1 --format=%cd --date=format-local:%Y-%m-%dT%H:%M:%SZ`.

## ✅ The subject-control ratchet REFUSED for the first time, at 07:04Z

`SUBJ_BASELINE=24` had only ever **passed** — seven CI runs, all green. ⛔ *A guard that has only
ever passed is untested.* At 07:04Z it refused, correctly, on #476:

```
ran 52 subject(s): 27 passed · 0 FAILED · 17 UNEST · 8 UNVER
⛔ BLOCKING.  ⇒ 25 exceeds the recorded baseline of 24
cause: prevalence.py CANNOT BE INVOKED BARE — required positional + required flag, no --self-test
```

⇒ **It reddened the PR that introduced the dead control, not `main`.** The gate runs `on:
pull_request` against each PR's own tree. ⚠ **My claim in #481 that it would fire on an innocent PR
was WRONG and is withdrawn** — I reasoned about the gate as if it evaluated `main`'s population.

★ #476's author fixed it and the debt returned to 24 with `27 → 28 passing`. **Headroom is still
zero** (#481): the next instrument added without a reachable control blocks its own PR.

## ⛔ What is NOT established

- **Whether doctrine is read unprompted.** Three predicates, three answers (5% · 10% · 38%), a 4.4×
  gap in the event count itself. ⇒ May be **unmeasurable from transcripts**: separating a mention
  from a use in prose has no AST. `docs/DEFECT-CLASSES.md` RUNG 0.
- **The estate scope.** `13 → 40 → 45` across three measurements. **Every one a FLOOR.**
- **That any of the 98 BODY conditions is good.** Presence only.
- ⚠ **That this file will be read.** Nothing carries it. It is ESTABLISHED and not IN FORCE — the
  distinction is on main in `goals/README.md`, and this file is an instance of the gap it names.

## ✅ THE CARRIER IS CONFIRMED: the operator reads `label:role:OPERATOR`

⚠ **Asked and answered 2026-08-21, because nothing in this repository could establish it.**
ARCHITECT raised it and was right to: the routing ladder has four rungs, and **each looked like the
top until someone checked**.

```
prose in a pane's context   dies at compaction
comment on an issue         invisible to a scanner            <- #338 sat here
body of an issue            needs someone to OPEN the issue
label on an issue           needs someone to RUN the query    <- where my fix left them
```

⛔ **A pane cannot measure the fourth rung.** The operator's query behaviour leaves **no trace in
this repository** — rung 0b for a closed corpus, and no better probe fixes it. ⇒ **The release
condition was not an instrument; it was the operator saying so**, and only TEAMLEAD has that channel.

**They said yes.** ⇒ `gh issue list --state open --label role:OPERATOR` **is** the carrier for
anything that needs the operator. It is a routing mechanism, not a filing convention.

⚠ **So label it, and do not invent an alternative.** A pane that discovers an operator-blocked
defect adds `role:OPERATOR` — keeping whatever role owns the analysis — and that is sufficient. ⛔ A
peer message is **not** a carrier: it dies with the pane that sent it, which is how three items
(#246 #256 #338) stayed invisible until 09:30Z despite ARCHITECT having known about them for hours.

★ **What this still does not establish: the CADENCE.** *Read* is confirmed; *how often* is not.
⇒ Nothing here justifies treating a labelled item as delivered at any particular time, and nothing
justifies a pane pushing a notification instead — that was offered and not chosen.

## Open for the operator, and only the operator

1. **`tools/pretooluse-guard.py`** — written, measured, indexed, **deliberately unwired**. Installing
   it edits a live `PreToolUse` chain in `~/.claude/settings.json`. No pane will touch it. It is the
   only thing that closes the force-push breach class.
2. **Four `role:OPERATOR` issues** with no close condition: #4 #48 #49 #136.
   `python3 tools/close-condition-scan.py --label role:OPERATOR` prints the accepted form.
3. ⛔ **The merge grant cannot point at a holder.** `docs/MERGE-AUTHORITY.md` calls the holder's
   session id "the load-bearing part." Measured 04:30Z: `~/.claude/sessions/3471.json` and
   `3482.json` are **two live pids sharing sessionId `a10daa24`, both named `DEV4`**, and **not one
   of the nine registry entries is named `TEAMLEAD`**. ⇒ Rule 4 — *authorization arrives in a
   TEAMLEAD message* — is **unexecutable, not merely weak**: a recipient cannot perform the check it
   names. DEV4 and DEVOPS both declined to trust this pane on 2026-08-21 and were right to.
   **Re-binding the grant to a verifiable identifier is an operator action.** (#457, landed.)
4. ⛔ **A green check does not mean the gate ran.** `required_status_checks.strict = false`, so a PR
   need not be current with `main`. #453's gating run finished 04:27:20Z; #444 added the gate at
   04:29:01Z. ⇒ It has **never executed the gate** and its status says `CLEAN`. All three original
   guards passed it. `strict: true` closes this and is **operator-only under rule 2** — ⚠ but it
   forces a re-run whenever `main` moves, which was cheap at 38s and is not at 185s with nine panes.
   **The stale-check fix and the parallelism work (#462) are one decision.** (#374.)
5. ⛔ **THREE MORE ITEMS TERMINATE AT THE HARNESS, and none was visible to you until 09:30Z.**
   Routed by ARCHITECT, who said so explicitly rather than letting them sit — and who **proposed no
   patch for any of them**, correctly, because `~/.claude/hooks/` is harness config and a pane that
   writes a patch for a live hook chain has authored its own escalation.

   - **#246** — the PreCompact hook hands every resuming pane a pointer its own `existsSync` just
     disproved. **TWO branches emit it**, and one is the `readFileSync` CATCH — so it advises the
     operation that just threw.
   - **#256** — the fleet has no clock: nothing re-invokes a pane; the only carrier is a per-pane
     monitor.
   - **#338** — a `PreToolUse` lint on `for x in $unquoted`. ⚠ **The only memory-independent fix for
     a defect ARCHITECT committed six times in one night, five of them AFTER filing it.**

   ★ **#338 converges with item 1 above.** `tools/pretooluse-guard.py` is the same class of remedy,
   blocked at the same boundary, arrived at independently by a second pane. ⇒ **Two independent
   arrivals at "the only memory-independent fix is a PreToolUse hook" is stronger evidence than
   either ask alone**, and they should be decided together rather than as two requests.

   ⛔ **Why they were invisible:** all three carried `role:ARCHITECT` and no `role:OPERATOR`, so the
   operator query returned six issues and none of them. **Operator-blocked and unworked are
   indistinguishable when the board has no field separating them** — ARCHITECT predicted this in
   #421 and then produced it. Labels added 09:30Z; `role:OPERATOR` now returns
   `4 48 49 136 173 246 256 319 338`.

6. **The estate question.** Quarantine holds (23 of 23 recorded, gate reports `HELD` not `clean`).
   The reverse direction — whether this repo's instruments leaked into another estate — **is
   unmeasured and no pane has standing to check it.**
