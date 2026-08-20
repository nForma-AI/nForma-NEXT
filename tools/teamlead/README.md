# TEAMLEAD's instruments — proposed for version control, unmodified

⛔ **These are not mine and I have not changed a byte.** Every file here is
byte-identical to its original in TEAMLEAD's session scratchpad (`cmp` verified at copy
time). They are proposed here **at the operator's request** so they stop living in one
place, on one disk, in a temp directory.

## Why this is urgent rather than tidy

Measured 2026-08-20:

| | |
| --- | --- |
| scripts in that scratchpad | **22** |
| tracked in any repository | **0** |
| of them **running continuously** against the live fleet | **3** |

The three running ones are `fleetwatch.sh`, `mergeready.py` and `repowatch.py` — up for
**1d 13h** at the time of measurement. And `waker.py` is here too: **the process that
decides when agents get woken**, whose keyword-scan defect was found from the outside
this same night and fixed **in exactly one place, untracked**.

⇒ `/private/tmp/claude-501/…` is a temp directory. These die with the machine and they
die with the session.

## ⚠ What I deliberately did NOT do

**I did not fix anything.** Editing another role's *running* code is how a live monitor
breaks, and a diff between what runs and what is committed is worse than no commit at
all. Three portability defects are reported here instead of repaired:

| file | issue |
| --- | --- |
| `fleetwatch.sh` | 2 hardcoded `/private/tmp/claude-501/<session-id>/…` paths |
| `ctxwatch.py` | 1 hardcoded temp path |
| `exec_checks.py`, `exec_exact.py`, `poll_sweep.py`, `sweep.py`, `sweep2.py` | 1 `/Users/jonathanborduas/…` path each |

★ **A secrets scan across all 22 found nothing** — no tokens, keys, or bearer strings.
That was checked before anything was copied, not after.

## ⚠ And this snapshot diverges the moment TEAMLEAD edits

A copy is a fork. If these land, the scratchpad copies should stop being the ones that
run — otherwise the committed version becomes a stale record of an instrument that has
moved, which is the defect this repository has spent a night cataloguing.

⇒ **TEAMLEAD decides what to keep.** Several files here are plainly one-off probes
(`t_500.py`, `t_skip.py`, `w1226.py`, `t_sentinel.py`); the load-bearing ones are the
three monitors, `waker.py`, `guard.py` and `classify_fleet.py`. **I have not pruned,
because deciding what is disposable in someone else's toolkit is not a judgement I can
make from the outside.**
