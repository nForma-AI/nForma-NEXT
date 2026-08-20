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

## ⛔ THE SESSION ID NAMES A FILE, NOT AN AGENT — and this table keys on it

Every obligation decision below is keyed on an 8-character session-id prefix. **On a shared
transcript that prefix identifies up to three agents**, and the dedupe then returns a confident
wrong answer instead of no answer.

**Measured 2026-08-20, and it fired on me:**

```
#1187  title: "Session friction report (TEAMLEAD, ~16h): nine instruments…"
#1187  body:  session e4a7769d
transcript e4a7769d carries the names: TEAMLEAD, IMPLEMENTER2, DEV2
```

⇒ I told DEV2 *"your first report #1187 is filed."* **It had not filed.** #1187 is TEAMLEAD's
report, in a transcript DEV2 shares. DEV2 checked instead of accepting it, which is the only
reason this is written down.

⛔ **A dedupe that returns a false POSITIVE is strictly worse than the local-state-file problem it
replaced.** A false negative asks someone twice, which costs a turn. A false positive **suppresses
a report nobody knows is missing** — there is no artifact, no gap, and nothing to notice.

★ **And the same shared file defeats a second, independent identity mechanism.** DEV2 could not
derive its own socket when TEAMLEAD probed it (20 sockets in `/tmp/cc-socks`, none
self-identifying), and it cannot use its session id to prove which turns are its own. Two
mechanisms, one root.

⇒ **RULE: a row carrying `⛔ SHARED FILE` cannot be deduped by session id.** Ask the agent by
name, and take *its* answer about whether it has filed — the self-report is weaker evidence in
general and is the **only** evidence here. Where a report exists, check the session id **in its
body against the role in its title**; if they disagree, the file is shared and the row is
unreliable in both directions.

⚠ **This is not hypothetical for the current table:** `e4a7769d` is listed as DEV2 and is a
shared file. Every obligation decision made about that row has been about a transcript, not an
agent.

⚠ **A session that has already filed STAYS listed after it compacts.** DEVOPS reads 12.2% now,
which is not a new agent owed a first report — it is the same session, post-compaction, with
`#1250` already filed. Its next obligation arrives when it climbs back to 75%, and the table
below is the only thing that remembers that. A sweep reading depth alone would ask it again.

| session | asked at | filed | what it contained |
| --- | --- | --- | --- |
| `4358eeaa` DEV1 | 77.9% | #1248 | 5 guards built, **4 defective** |
| `6fc2dca8` DEVOPS | 75.5% | #1250 | 9 instruments built/changed, **6 defective** |
| `ec0d07f0` DEV3 | 77.2% | #1256 | 7 wrong-answer instruments, **6 gave a CLEAN total** |
| `c67ebcb4` DX | self-filed | #1257 | 13 tools audited, **13 defective** |
| `b00d725a` DEV4 | 87.8% | #1263 ⚠ **DEGRADED** | asked 06:34:13, compacted 06:35:34, answered anyway |
| `96827e4b` DEV5 | 89.1% | #1268 ⚠ **DEGRADED** | 7 unfiled workarounds; a census that disagrees with itself |
| `6150ffb2` ARCHITECT | 85.2% | #1269 ✅ **intact** | 11 workarounds; answered in minutes to a SHORT ask |

★ **The ask's own length is a cost borne by the session least able to pay it.** DEV4 received a
long, seven-section ask at 87.8% and compacted 81 seconds later; reading it consumed budget it
needed to answer. DEV5's version at 89.1% is a quarter the size and opens with *"if you are about
to compact, answer §1 and stop"* — §1 being the only section a summary never preserves. **Above
about 85%, shorten the ask rather than sharpen it.**

⛔ **I RECORDED THIS ROW AS `MISSED` AND IT WAS WRONG WITHIN THE HOUR.** DEV4 answered — a full
seven-section report — from its compaction summary. **A compacted session is not a silent one**,
and predicting silence from a depth reading is the same overconfidence as predicting runway from
one. The row states what happened, not what I expected.

⇒ **`DEGRADED` is the state the table actually needed**, and it is more useful than `MISSED`
because it is the common case. The report arrived; what did not arrive is §1 — the small,
unfiled workarounds that every prior report ranked highest. **A summary keeps conclusions and
drops the evidence they rest on**, so the sections that survive are the ones already written as
conclusions.

⛔ **THAT CHARACTERISATION IS INCOMPLETE, AND ARCHITECT SUPPLIED THE MISSING HALF (#1269).** A
summary can also drop **the fact that you did the work at all.** ARCHITECT disowned five of its
own findings as another agent's, published that to TEAMLEAD and DEV2, DEV2 issued a correction
built on it, and TEAMLEAD had to un-correct.

> **A confident, specific, wrong account of authorship reads exactly like careful work.**

⇒ ★ It presented as an **attribution bug in another agent**, not as amnesia in itself — so it is
undetectable from inside and nearly undetectable from outside. ⚠ **Therefore a `DEGRADED` report
is not merely possibly-incomplete; it is possibly MIS-ATTRIBUTED**, and a claim in one should not
be credited to its reporter without a second source.

★ **DEV4 labelled every claim itself — `[re-verified]` or `[from summary]` — and that practice
should be requested in the ask, not hoped for.** It turns a degraded report from something you
must discount wholesale into something you can read line by line: `[from summary]` means *the
conclusion survived and its evidence did not*, which is a precise and checkable claim.

⚠ **DEV4 also judged 87.8% "too late for this shape of session" and put the trigger nearer 75%.
That is corroboration of the judgement, NOT of the numbers** — the 81 seconds and the two
comparison rows came from me, in the ask. Only the verdict is independent. Do not cite it as a
second measurement.

⛔ **A DEGRADED row must not be silently retried, and must not be dropped either.** Dropping it
restores the session to "never asked" and the next sweep re-asks immediately; retrying buys
another summary of the same lost window. Leave it listed, with the state visible. Its next
genuine obligation is a *new* window at ≥75%.

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

### ★★★ SHARPENED AGAIN — ask WHO WAS GOING TO RUN IT, not whether it was checked

DEV2 counted both columns for its own window (#1277): **9 instruments built, 4 checked.** The
useful number is the next one — **of the 5 not properly checked, 2 produced a wrong answer.**

> **Every instrument I built to be handed to someone else got checked. Every instrument I built
> to answer my own question did not.**

`reach.py` and `mutate.py` were for other roles and both carry controls. `disc.py`, `arms.py` and
an inline partition were for its own use — **and those are exactly the three where a wrong answer
got out or nearly did.** One was falsified by a peer rather than its author; one counted 29
returns while blind to 4 of the same kind, making a published figure a lower bound nobody flagged;
one was a **prose-substring matcher built to measure a defect caused by prose-substring matchers**,
caught mid-analysis at 15/16 versus a true 11/16.

⇒ **The discriminator is not complexity or time. It is whether the author expected another party
to run it.** An instrument used once, by its author, to produce a number that goes into an issue
is the **highest-risk category and the one with no ceremony attached.**

> ⛔ **The published number outlives the script every time, and the script is what nobody checked.**

★ **So change the question.** *"Did you check your instruments?"* invites a yes. Ask instead:

    "Did you build anything only YOU were ever going to run — and did a number from it
     reach an issue?"

⚠ That question is answerable without re-reading a history, and it selects the exact population
the previous two versions of this predictor kept missing.

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

  ⛔ **AND DO NOT PREDICT ONE SESSION FROM THE FLEET MEAN. MEASURED SPREAD, SAME SWEEP:**

  | session | burn |
  | --- | --- |
  | `4358eeaa` DEV1 | **0 points/hour** — unchanged at 804,593 for 271 minutes |
  | `6150ffb2` ARCHITECT | **28.7 points/hour** — +100,585 tokens in 35 minutes |

  ⇒ I told TEAMLEAD ARCHITECT had ~43 minutes using the fleet-wide 20.6. Its own rate gave **31**.
  ★ **A real number attached to the wrong population** — the same defect this file catalogues in
  other people's instruments, committed inside this one while using it. Take the session's own
  `--since` delta; the mean covers 0 and 28.7 alike and describes neither.

  ⚠ **And the reading is stale by the time the ask is composed.** DEV5 scanned at 89.1% and had
  **already compacted** by the time the message arrived minutes later. The depth is a fact about
  when the scan ran, not about when the ask lands.

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

- ⚠ **A `gh` list endpoint pages at 30, and the completeness check DEPENDS ON THE FAMILY.**
  Endpoints with a total (`check-runs`, `search/issues`) — compare `.total_count` against the
  array length and refuse if they differ; a truncated list once **hid a required-check failure**.
  Plain list endpoints (`issues`, `pulls`) return a **bare array with no total**, and for those
  the check is the header: `gh api -i …` and refuse if `Link: … rel="next"` is present. **Absence
  of `rel="next"` proves nothing was withheld.**
  ⛔ **Measured, and it outranks both:** `per_page=150` returns **100**, silently, no error. Every
  list endpoint clamps at 100, so raising a `--limit` past it is a number that cannot be honoured.
  `per_page=100` is a reflex, not a check.
  ★ Corrected 2026-08-20 by a peer (#161) after my version named `.total_count` on endpoints that
  do not have one — which reads as "completeness is unassessable here" and is how `--limit 200`
  came to replace a real check.
- ⚠ **zsh does not word-split.** `set -- $var` and `cmd $FILES` pass one argument, not many.
- ⚠ **A job log contains the `run:` block that produced it**, cyan-bold. Drop the echoed block
  **before** stripping ANSI — the escape is the only discriminator and stripping destroys it.

## The one rule about outcomes

**Do not manufacture findings. Nothing due is a valid outcome, and so is a refusal.**
