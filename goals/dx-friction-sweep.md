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
python3 tools/fleet-context.py --threshold 80
```

⛔ **DO NOT pass `--fleet-only`, and this procedure did for its whole life.** The DX goal file
forbids it explicitly, with a measured rationale: it excludes rows the tool cannot name, and
**worktree panes appear unnamed**. Over-inclusion costs a false alarm; under-inclusion misses a
compaction. Asymmetric — *a loud break outranks a red*.

Measured 2026-08-20, the rows the flag was hiding on every single sweep:

    734,421  73.4%  A          2edf7339   another project
    104,928  10.5%  (unnamed)  a7152a8d   worktree: 1038-live-idp-alert-coverage  ↻compacted
    103,341  10.3%  (unnamed)  2776dc7b   worktree: fix-1037-sentry-k8s-clients   ↻compacted
     97,074   9.7%  (unnamed)  ef380451   worktree: fix-1037-sentry-k8s-clients   ↻compacted
     59,648   6.0%  (unnamed)  a18b7702   another session

⇒ Three of the five are **worktree panes doing real issue work, and all three have compacted** —
unseen, never asked for a report, their friction gone. No compaction was missed *at a depth that
mattered*, which is luck rather than method: the excluded rows happened to be low.

★ And the cost lands on the headline metric. The friction-report coverage figure — *8 reports, 0
observed misses* — is measured over a population narrowed by a flag this goal file forbids. It
was already caveated for one ambiguous session; the scan around it was scoped the whole time.

Take the **exit code without a pipe**. `0` nobody crossed the threshold · `1` somebody did ·
`2` the scan **established nothing** — never "all clear".

⛔ **Exit 1 does NOT mean an ask is due.** It means a session crossed 80%; §2 then decides. The
two disagree by design and a reader who stops at the exit code will re-ask an agent that
answered an hour ago. Measured: DEV1 sat at 80.5% for two consecutive sweeps *after* filing.

⚠ Names are **self-reported**. `SHARED FILE` can appear on a session that lacked it before — a
second writer can join a transcript mid-session. **Re-read the flag; do not remember it.**

⚠ Unscoped output includes sessions that are not this fleet's. That is the intended cost: an
unnamed worktree pane and a stranger's session are indistinguishable to the scan, and only one
of those is safe to drop. Read the project column and judge; do not re-introduce a filter.

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

⚠ **A session that has already filed STAYS listed after it compacts.** DEVOPS reads 12.2% now,
which is not a new agent owed a first report — it is the same session, post-compaction, with
`#1250` already filed. Its next obligation arrives when it climbs back to 75%, and the table
below is the only thing that remembers that. A sweep reading depth alone would ask it again.

| session | asked at | filed | what it contained |
| --- | --- | --- | --- |
| `4358eeaa` DEV1 | 77.9% | #1248 | 5 guards built, **4 defective** |
| `6fc2dca8` DEVOPS | 75.5% | #1250 | 9 instruments built/changed, **6 defective** |

### ★ The predictor — confirmed twice, and *checked* the second time

Repeat reports pay when the window contained **instrument-building**, not when it was merely
long. DEVOPS had the *"this was a using-window, nothing new"* sentence **drafted** and discarded
it only after looking.

⛔ **CORRECTED by the third reporter, and the correction is narrower than the rule it fixes:** it
pays when the window built instruments **AND THE INSTRUMENTS WERE CHECKED**. Its seven
near-misses were reportable only because something forced each one to be tested.

⇒ **A window of UNCHECKED instrument-building produces a confident, empty report** — an author
who believes their tools worked, listing nothing, in good faith. That is worse than the "no",
because it reads as coverage. So when offering the refusal, offer it in this shape:

> *"Little new"* is first-class. So is *"I built things and never tested them, so I cannot tell
> you whether they were wrong."* The second is more useful than a clean report.

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
- ⚠ **75 is measured, and the margin it buys is now measured too — from both ends.**

  | asked at | runway after the ask | outcome |
  | --- | --- | --- |
  | **75.5%** | **5 sweeps** | answered, worked five more sweeps, compacted at 87.4% with the report already filed |
  | **85.4%** | **1 sweep** | answered, then compacted the next cycle. Made it by one. |
  | **87.8%** | **81 SECONDS** | ⛔ the ask landed at 06:34:13, the compaction step at 06:35:34 |

  ⛔ **THE THIRD ROW BREAKS THE MODEL, AND IT IS THE ONLY ONE MEASURED IN SECONDS.** DEV4's ask
  arrived 81 seconds before its context stepped 878,363 → 73,193. The window the report was
  *about* was compacted before a reply was possible; anything it sends now is reconstructed from
  a summary, which is not what the ask is for.

  ⚠ **Depth does not predict remaining time near the top, and the error is not small.** At the
  fleet's measured burn — DEV5 consumed 156,610 tokens in 46 minutes, **20.6 points/hour** — a
  linear model gives a session at 87.8% about **36 minutes**. DEV4 got **1.4**. That is a **25×
  overestimate**, because compaction does not fire at a depth; it fires on the next request that
  would not fit, and one large request is enough.

  ⇒ ★ **So "buy margin, not precision" is right for a stronger reason than it was written for.**
  Above roughly 85% the runway is not merely short — it is **unpredictable per session**, so
  asking early is not a preference for a tidier report. It is the only setting under which the
  answer arrives at all.

  ⛔ **And the one-ask-per-sweep cap is now the binding constraint, not the trigger.** Three
  sessions were at/over 80% this sweep. At 20.6 points/hour a session crosses 75% → compaction in
  about 73 minutes, so a fleet of eight cannot be covered one-per-sweep at any sweep cadence this
  cron runs. **The cap was set to avoid synchronising the fleet, not to ration coverage**, and it
  is now doing the second thing. Whether to raise it is a judgement about interrupt cost, and it
  belongs to whoever owns that cost — but the next sweep should not treat "one per sweep" as
  free.

  ⇒ The 75.5% case still settles the lower bound. DEVOPS filed `#1250` at 75.5%, was asked once, and went over the
  edge five sweeps later **with its report in hand** — the obligation working end to end rather
  than surviving by a cycle.

  ★ **Buy margin, not precision.** Ten points of context bought five sweeps of runway, and the
  cost of asking early is a report written slightly sooner than it had to be.
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

## 5b. The Option-1 conjunction check — report the first non-DX hit

TEAMLEAD ruled Option 1 (each role goal points at its canonical `prompts/<ROLE>.md`) and wants the
result reported **when the first pane that did not make the edit opens a role prompt**. Baseline
2026-08-20: **NONE YET**, which is the correct reading minutes after deployment.

```sh
python3 - <<'EOF'
import glob, json, os
hits = {}
for p in glob.glob(os.path.expanduser("~/.claude/projects/*/*.jsonl")):
    for line in open(p, errors="replace"):
        if "nForma-NEXT/prompts/" not in line and "nForma-NEXT:prompts/" not in line:
            continue
        try:
            rec = json.loads(line)
        except Exception:
            continue
        c = (rec.get("message") or {}).get("content")
        kinds = {b.get("type") for b in c if isinstance(b, dict)} if isinstance(c, list) else set()
        if kinds & {"tool_use", "tool_result"}:
            k = os.path.basename(p)[:8]
            hits[k] = hits.get(k, 0) + 1
hits.pop("c67ebcb4", None)          # the session that made the edit
print(hits or "NONE YET")
EOF
```

⛔ **`c67ebcb4` must stay excluded.** It is the session that wrote the pointer, and counting it
reproduces the void control in `docs/prompt-delivery-gap.md` exactly: *the reader must not be the
auditor.* A hit there measures this sweep, not the fleet.

⚠ A hit is half the test. The other half is that the pane's own goal file carries the pointer —
present ⇒ delivered, opened ⇒ consumed, and only both together mean anything. `DEV1` can never
satisfy it: it reads no goal file at all, and TEAMLEAD has taken that gap by another route.

## 6. Monitor liveness

```sh
pgrep -f ctx_reported
```

⚠ Not `fleet-context.py` — that runs ~1s per 120s and will usually be absent.

## 7. MISS check, then roll the baseline

```sh
python3 tools/fleet-context.py --since "$SP/fleet.snap" --threshold 200
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
