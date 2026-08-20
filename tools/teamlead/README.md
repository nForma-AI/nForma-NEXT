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

## ⛔ QUARANTINED — this inventory is a manifest, not an endorsement

**The operator has ruled quarantine on this directory.** These files came out of a scratch
directory that **more than one estate wrote to**; 10 of the 19 instruments name another estate
in **executable** position, and `w1226.py` is another product's application source. ⇒
`scripts/check-tools-index.py` reports every one of them **by name on every run** and records
their disposition in `tools/QUARANTINE.txt`, which is the marker — a tracked file, because prose
dies at the next compaction and the exit code it used to rely on was green all along. ⚠ **Naming a file below does not assert it belongs here** — the manifest exists
so a reader can see what is being held, and the disposition is the operator's.

⛔ Do not index into `tools/README.md`'s table · do not delete · do not rewrite history.

⚠ **All 19 instruments are held, not 10.** Every file here arrived in **one commit** (`ac6a946`)
out of a shared scratch directory, so the provenance question is this **directory's**, not each
file's. Ten carry a foreign estate marker in executable position; the other nine — `boxwatch.py`
`boxwatch.sh` `classify_fleet.py` `dt.sh` `guard.py` `mergeready.py` `t_500.py` `t_skip.py`
`waker.py` — are **`UNCLAIMED`: no estate marker, and no evidence they are ours either.**
⛔ `UNCLAIMED` is not `LOCAL`, and the index must not assert that it is.

## The full inventory — every file, named

⚠ Added 2026-08-20 by DEVOPS under #307. `boxwatch.py`, `boxwatch.sh` and `dt.sh` were in this
directory and named **nowhere**, in any index, at any level. The descriptions below are read off
each file's own opening lines; **none of these has been run or reviewed here.**

| file | what its own source says it is |
|---|---|
| `waker.py` | decides when panes get woken. ★ Carries the measured finding that *a literal `/compact` executes and prose telling an agent to compact does not*. |
| `guard.py` | rejects unintended issue-closing keywords in a PR title, body, or commit subject. |
| `classify_fleet.py` | classifies pane state; guards that a non-empty input box is a **CLI-suggested reply**, not a pending human instruction. |
| `fleetwatch.sh` | the fleet monitor — emits three states, not one, so *idle* is separable from *blocked on unsubmitted text*. |
| `mergeready.py` | merge-readiness polling. |
| `repowatch.py` | watches `Borduas-Holdings/Blazing-Back`; never suppresses stderr, so a failed read stays reportable. |
| `ctxwatch.py` | reads context% from the rendered status line; guards that a pane whose status line is off-viewport yields **unknown**, never *safe*. |
| `boxwatch.py` | polls four hardcoded terminal UUIDs under the role names `IMPLEMENTER`…`IMPLEMENTER5`. ⛔ **Those are another estate's role names** — it addresses panes that do not exist in this fleet. |
| `boxwatch.sh` | snapshots every agent input box every 20s and logs **only transitions** (empty → text). |
| `dt.sh` | one-shot Daintree MCP JSON-RPC call. ⚠ Reads a `dtkey` file that is **not in this repository**, so the committed copy does not run as-is. |
| `sweep.py` `sweep2.py` `exec_checks.py` `exec_exact.py` `poll_sweep.py` | AST sweeps over `DigitalFrontier-infra`, hardcoded. ⛔ Not runnable against this repository. |
| `w1226.py` | ⛔ **not a tool** — a verbatim copy of another service's `control-plane/api/handlers/workloads.py`. |
| `t_500.py` `t_skip.py` `t_sentinel.py` | one-off probes against another estate's issues (#1218, #1230, #1177). ⚠ Named `t_*`, so `NOT_AN_INSTRUMENT` does **not** exclude them and they count as instruments here. |
| `test_exec_sentinel_stderr_discriminator.py` `test_kill_never_ran_sentinel.py` `test_kill_unknown_does_not_narrate_a_timeout.py` | tests — excluded from the instrument population by `NOT_AN_INSTRUMENT`, and named here anyway. |

## ⚠ And this snapshot diverges the moment TEAMLEAD edits

A copy is a fork. If these land, the scratchpad copies should stop being the ones that
run — otherwise the committed version becomes a stale record of an instrument that has
moved, which is the defect this repository has spent a night cataloguing.

⇒ **TEAMLEAD decides what to keep.** Several files here are plainly one-off probes
(`t_500.py`, `t_skip.py`, `w1226.py`, `t_sentinel.py`); the load-bearing ones are the
three monitors, `waker.py`, `guard.py` and `classify_fleet.py`. **I have not pruned,
because deciding what is disposable in someone else's toolkit is not a judgement I can
make from the outside.**
