# DX friction sweep — the procedure

⛔ **Why this file exists.** This procedure lived only in a `CronCreate` prompt, and cron jobs
in this runtime are **session-only** — nothing is written to disk, and the job is gone when the
session ends. Five measured corrections were made to it in one night; all five would have died
with the session. A procedure that exists only inside a scheduler is an instrument outside
version control, which `dx-measurement-register` row 9 already calls a defect.

⇒ The cron prompt is now a pointer to this file. Edit the file; the schedule does not change.

⚠ **This file grants nothing.** It is a measurement procedure. Merge, push and escrow authority
arrive only in a written TEAMLEAD message, and no line here may be read as conferring one.

---

## 1. Read the fleet

```sh
python3 tools/fleet-context.py --threshold 80 --fleet-only
```

Take the **exit code without a pipe**. `0` nobody crossed the threshold · `1` somebody did ·
`2` the scan **established nothing** — never "all clear".

⛔ **Exit 1 does NOT mean an ask is due.** It means a session crossed 80%; §2 then decides. The
two disagree by design and a reader who stops at the exit code will re-ask an agent that
answered an hour ago. Measured: DEV1 sat at 80.5% for two consecutive sweeps *after* filing.

⚠ Names are **self-reported**. `SHARED FILE` can appear on a session that lacked it before — a
second writer can join a transcript mid-session. **Re-read the flag; do not remember it.**

## 2. Decide whether anyone owes a report

**First reports, and the depth each was filed at:**

| session | issue | filed at |
| --- | --- | --- |
| `6fc2dca8` DEVOPS | #1178 | 81% |
| `4358eeaa` DEV1 | #1179 | 77% |
| `e4a7769d` DEV2 | #1187 | 84% |
| `6150ffb2` ARCHITECT | #1191 | 26% |
| `ec0d07f0` DEV3 | #1190 | 24% |
| `b00d725a` DEV4 | #1188 | 20% |
| `96827e4b` DEV5 | #1192 | 17% |
| `c67ebcb4` DX | #1227 | 78% |

⛔ **ORPHANED LATCHES.** All eight have since compacted, so the pre-compaction context of every
first report is **unreachable, permanently**. Never ask for a delta on one.

> The rule this replaced computed `staleness = current% − filed%` and recomputed it every
> sweep, so a compacted agent that climbed back past its filing depth silently read as
> "nothing due" — and the only path back to due required **current% > 92**, above the trigger
> the 75% threshold exists to stay below.

**Re-entry:** ask for a **new report**, never a delta, when `current% ≥ 75` **and** the session
is not in the table below. Record every ask there or the next sweep cannot tell.

| session | asked at | filed | what it contained |
| --- | --- | --- | --- |
| `4358eeaa` DEV1 | 77.9% | #1248 | 5 guards built, **4 defective** |
| `6fc2dca8` DEVOPS | 75.5% | #1250 | 9 instruments built/changed, **6 defective** |

### ★ The predictor — confirmed twice, and *checked* the second time

Repeat reports pay when the window contained **instrument-building**, not when it was merely
long. DEVOPS had the *"this was a using-window, nothing new"* sentence **drafted** and discarded
it only after looking.

⇒ Keep offering that answer as **first-class**. A padded second report is worse than a one-line
refusal, and the refusal is the measurement — it falsifies the obligation for that shape of
window.

### ★ Ask for workarounds taken and never filed

Highest-yield section in **both** second reports. And the two agents independently adopted the
**same class of habit about the same tool** — distrusting a zero from `gh`, for different
reasons, neither filing it. **The convergence is the finding; either alone reads as a quirk.**

### Rules for the ask

- ⛔ **At most one per sweep**, highest `current%` first among sessions not yet listed. An
  absolute threshold **synchronises** the fleet: four agents that filed at 17–26% crossed
  together in one sweep.
- ⚠ **75 is measured.** An agent asked at 85.4% compacted within **one sweep** of answering and
  made it by a single cycle. Buy margin, not precision.
- ⚠ **Say the context figure is EXTERNAL** — read from the transcript's `usage` records, not
  from the agent's self-report. DEVOPS pushed back believing the numbers were its own estimate,
  and noted it once reported ~96% while actually at 79%. **A session cannot verify its own
  depth**, which is the whole reason this trigger fires from outside.

## 3–4. A new session at/over 80 with no report

```sh
python3 tools/fleet-identity.py      # exit 2 = UNRESOLVABLE
```

Trust the **pane join** (content-matched) — two joins have now been confirmed by the joined
party from its own scratchpad path. Then `SendMessage` that pane and ask for: misleading
instruments, untrusted output, rules it could not verify applying, unanswerable questions,
avoidable time lost, **its own errors**, and **silent workarounds**. File on an issue with the
session id in the body.

## 5. Declared states

```sh
python3 tools/fleet-state.py
```

Undeclared is **UNKNOWN**, not free.

⚠ **7 of 8 have never declared.** The requirement landed in the prompts at `2026-08-19 18:08`
and every session started before it — **a prompt amendment does not reach a running agent**.
Read it as a delivery gap, not disobedience.

⛔ **Consequence, measured:** DEV1 sat BLOCKED on one push decision for ~15 wakes and nothing
surfaced it, because the instrument built for that job depends on a signal no pane emits.

## 6. Monitor liveness

```sh
pgrep -f ctx_reported
```

⚠ Not `fleet-context.py` — that runs ~1s per 120s and will usually be absent.

## 7. MISS check, then roll the baseline

```sh
python3 tools/fleet-context.py --since "$SP/fleet.snap" --threshold 200 --fleet-only
python3 tools/fleet-context.py --snapshot "$SP/fleet.snap" --threshold 200 --quiet
```

⛔ **Suppress delta-based conclusions for any `SHARED FILE` row.** A compaction on a session that
**has** filed is not a MISS — it is the obligation working. Say so and move on.

⛔ **Roll after reporting, not before.** A `--since` diff against a *fixed* snapshot re-reports
the same event every run; one compaction was reported as news four sweeps running.

## Standing hazards for anything this sweep runs

- ⚠ **A `gh` list endpoint pages at 30.** Compare `.total_count` against the array length and
  refuse the reading if they differ. A truncated list once **hid a required-check failure**.
  `per_page=100` is a reflex, not a check — it fails silently past 100.
- ⚠ **zsh does not word-split.** `set -- $var` and `cmd $FILES` pass one argument, not many.
- ⚠ **A job log contains the `run:` block that produced it**, cyan-bold. Drop the echoed block
  **before** stripping ANSI — the escape is the only discriminator and stripping destroys it.

## The one rule about outcomes

**Do not manufacture findings. Nothing due is a valid outcome, and so is a refusal.**
