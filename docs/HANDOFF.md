# Handoff — what landed, what is broken, and what would falsify each claim

*Written by TEAMLEAD (session `a10daa24`) 2026-08-21 ~04:00Z. **Every figure below carries the date
it was measured. A number without one is a rumour** — `CLAUDE.md`'s rule, applied to this file.*

⛔ **This file exists because doctrine delivery in this fleet runs through one pane, and that was
measured rather than feared:** `main` took **zero commits in two hours** while that pane was busy
elsewhere. Panes finish a turn and nothing re-invokes them. **Read this instead of asking it.**

---

## What is true right now

*Measured 2026-08-21 **04:55Z** on `origin/main`. ⚠ Every count uses `--limit 1000`: the default page size equals the returned count, so truncation is silent — that is how `30` was once read for a population of `85`.*

```
merged PRs        304          open issues   108          open PRs      3 (1 held)
main CI rollup    SUCCESS      quarantine    23 of 23 files recorded
role: unrouted    0            role:/dev: disagreements  15   <- #461, and I created all 15
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

## ⇒ The FOUR guards on the merge loop, each added after it cost something

```
reviews read before merge     ← a review was merged over; CI status cannot carry an objection
base must be main             ← a stacked PR's squash orphans (2 of 287, perfect predictor)
ancestry verified after merge ← `MERGED` is not `landed`; verify by content, not by exit code
gating run POST-dates main     ← added 04:45Z; see KNOWN-BROKEN. A check older than main's
                                 head establishes nothing about main's head.
```

⚠ **All four are prose in a pane, not controls. They die with this session.** ⛔ And guard 4 was
*itself* defective on its first run: `git log --format=%cI` returns a **local** offset
(`05:41:21+01:00`) while check timestamps are **UTC** (`04:43:38Z`), so the lexical compare produced
a **false refusal** on #456. Two valid ISO-8601 strings are not comparable across offsets. Normalise
with `TZ=UTC git log -1 --format=%cd --date=format-local:%Y-%m-%dT%H:%M:%SZ`.

## ⛔ What is NOT established

- **Whether doctrine is read unprompted.** Three predicates, three answers (5% · 10% · 38%), a 4.4×
  gap in the event count itself. ⇒ May be **unmeasurable from transcripts**: separating a mention
  from a use in prose has no AST. `docs/DEFECT-CLASSES.md` RUNG 0.
- **The estate scope.** `13 → 40 → 45` across three measurements. **Every one a FLOOR.**
- **That any of the 98 BODY conditions is good.** Presence only.
- ⚠ **That this file will be read.** Nothing carries it. It is ESTABLISHED and not IN FORCE — the
  distinction is on main in `goals/README.md`, and this file is an instance of the gap it names.

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
5. **The estate question.** Quarantine holds (23 of 23 recorded, gate reports `HELD` not `clean`).
   The reverse direction — whether this repo's instruments leaked into another estate — **is
   unmeasured and no pane has standing to check it.**
