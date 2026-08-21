# Handoff — what landed, what is broken, and what would falsify each claim

*Written by TEAMLEAD (session `a10daa24`) 2026-08-21 ~04:00Z. **Every figure below carries the date
it was measured. A number without one is a rumour** — `CLAUDE.md`'s rule, applied to this file.*

⛔ **This file exists because doctrine delivery in this fleet runs through one pane, and that was
measured rather than feared:** `main` took **zero commits in two hours** while that pane was busy
elsewhere. Panes finish a turn and nothing re-invokes them. **Read this instead of asking it.**

---

## What is true right now

*Measured 2026-08-21 **08:59Z** on `origin/main`. ⚠ Every count uses `--limit 1000`: the default page size equals the returned count, so truncation is silent — that is how `30` was once read for a population of `85`.*

```
merged PRs        329          open issues   111          open PRs      0
main CI rollup    SUCCESS      quarantine    23 of 23 files recorded
role: unrouted    0            role:/dev: disagreements  15   <- #461, and I created all 15
no close condition 16 of 111 <- nobody can close these; 4 are role:OPERATOR (#4 #48 #49 #136)
gating job        ~185s +-2s   (was ~38s before #444 landed 04:29Z; +147s, 4.9x)
close conditions  NONE 8 · BURIED 0 · BODY 98        (was 70 · 12 · 19 at 21:00Z)
runnable          ASSERTED 38 · RUNNABLE 34 · NO-CONDITION 34
```

⚠ **`BODY 98` is PRESENCE ONLY** — `close-condition-scan.py` says so in its own output. It is not 98
good conditions. `runnable-condition.py` is the second dimension and it disagrees with the first by
construction; **neither is "the" number** and both name their predicate.

## ⛔ KNOWN-BROKEN, with the command that shows it

| what | reproduce | status |
|---|---|---|
| `tools/index-watch.py --self-test` **hangs** | `python3 tools/index-watch.py --self-test` → never returns | ⛔ live on main |
| **24 of 48 controls establish nothing** | `bash scripts/gate-selftests.sh` → `15 UNESTABLISHED · 9 UNVERIFIABLE` | ⛔ live |
| `bootstrap-audit.py`'s control **FAILS** | same command → `⛔ CONTROL FAILED` | ⛔ blocks #444 |
| `use-not-mention.py` is **UNVERIFIABLE** | accepts `--zzz-not-a-flag`, exits 0 | ⛔ the mention/use instrument cannot verify itself |
| estate vocabulary is a **closed list** | `scripts/check-tools-index.py:158` | ⛔ a novel estate reads as LOCAL (#348) |

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
