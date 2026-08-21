# Handoff — what landed, what is broken, and what would falsify each claim

*Written by TEAMLEAD (session `a10daa24`) 2026-08-21 ~04:00Z. **Every figure below carries the date
it was measured. A number without one is a rumour** — `CLAUDE.md`'s rule, applied to this file.*

⛔ **This file exists because doctrine delivery in this fleet runs through one pane, and that was
measured rather than feared:** `main` took **zero commits in two hours** while that pane was busy
elsewhere. Panes finish a turn and nothing re-invokes them. **Read this instead of asking it.**

---

## What is true right now

*Measured 2026-08-21 04:00Z on `origin/main`, `gh pr list --limit 1000`, `gh issue list --limit 400`.*

```
merged PRs        290          open issues   106          instruments   50 + 49 suites
main CI rollup    SUCCESS      quarantine    23 of 23 files recorded
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

## ⇒ The three guards on the merge loop, each added after it cost something

```
reviews read before merge     ← a review was merged over; CI status cannot carry an objection
base must be main             ← a stacked PR's squash orphans (2 of 287, perfect predictor)
ancestry verified after merge ← `MERGED` is not `landed`; verify by content, not by exit code
```

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
3. **The estate question.** Quarantine holds (23 of 23 recorded, gate reports `HELD` not `clean`).
   The reverse direction — whether this repo's instruments leaked into another estate — **is
   unmeasured and no pane has standing to check it.**
