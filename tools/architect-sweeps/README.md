# ARCHITECT sweeps — the inline measurements, made reproducible

⛔ **Why these are files.** Every figure below was produced by an **inline heredoc** during
session `c83ecf77` and quoted into a durable artifact. The artifact survived; the code did not.
A number in a durable artifact whose instrument lives only in a transcript is **a citation to a
pane that may be gone** — which is `goals/README.md`'s rule about instruments outside version
control, applied to a measurement rather than to a tool.

⚠ **These are sweeps, not instruments.** They answer a question once and print what they did not
establish. None is a control, none has a known-negative, and they are deliberately **not** in
`tools/` — that directory's rows carry the incident that produced them and a proven failure path.
These carry neither, and they must **not** be promoted into `tools/`'s table.

⚠ **Updated 2026-08-20 (#307).** This paragraph used to end *"`scripts/check-tools-index.py`
indexes `tools/*.py`; this directory is outside its population by construction and should stay
there."* That was true and it was also how 22 unrelated files in `tools/teamlead/` stayed
invisible — one glob served as both a deliberate exclusion and an accidental blind spot, and
nothing could tell the two apart. The checker now recurses. ⇒ **The distinction survives as a
contract rather than as a glob:** these three are *named* in this README and are held to
nothing else — no row, no prose entry, no count, and no claim that any of them is a control.

## Provenance — which figure came from which script

| figure I reported | where I quoted it | script |
|---|---|---|
| *"7 distinct versions of `prompts/ARCHITECT.md`, 0 mutually-contained pairs"* | #29, and `tools/doctrine-version.py`'s docstring | `doctrine-discriminability.py` |
| *"`per_page=150` → 100 returned, silently capped"* | #142 | `list-truncation-probe.py` |
| *"`gh pr list --limit 200` → 131, true total 131 — does NOT cap"* | #186 | `list-truncation-probe.py` |
| *"118 PRs"* / *"131 PRs"* | #142, #186 | `list-truncation-probe.py` |

⛔ **Re-run before citing any of them.** Both moved between authoring and committing, in one hour:

```
prompts/ARCHITECT.md versions    7  ->  9
PRs                            118  -> 131 -> 135
```

★ That is the reason to commit a sweep rather than its output. **A number decays; the thing that
regenerates it does not** — and four observers produced four different PR counts in one hour
because each held a number and none held the query.

## `known-negative.py` — is this control a control, or has it only ever passed?

#26's acceptance test, run rather than argued. Sabotage a tool's **analyser**, re-run its control,
and see whether the control notices.

```
python3 tools/architect-sweeps/known-negative.py --ref origin/main --limit 6 \
    tools/fleet-identity.py:tools/test_fleet_identity.py
```

**Measured at `2effc63d`, all 24 tool/control pairs, 6 mutants each:**

```
pairs 24 · examined 21 · VOID 3 · CONTROL 18 · DECORATIVE 3
DECORATIVE: daintree-control.py · doctrine-watch.py · fleet-identity.py
```

⇒ **Three predicates for "controlled" give three different answers**, and only the third measures
the property #26 is about:

| predicate | answer | what it actually measures |
|---|---|---|
| has a `test_` file | **24 of 28** | a file exists |
| names `--self-test` | **28 of 28** | a string appears |
| **catches analyser sabotage** | **18 of 21 examined** | the control can fail |

⛔ **Two guards this tool exists to carry**, both from figures that were wrong without them:

- **A crashed mutant is `VOID`, never a detection.** A sabotaged copy that dies on a `Traceback`
  exits non-zero, and a probe scoring `exit != 0` reads that as the control firing. Two published
  #26 figures were artifacts of this. (TEAMLEAD)
- **Mutate the analyser, not the dispatch.** Inverting comparisons inside `main()` breaks argument
  handling, so the mutant never reaches the cases — the same artifact one layer up.

⚠ **`VOID` is load-bearing and it fired for two different reasons.** `reference-check.py`'s control
**fails on `main` today** — genuinely red. `stranded-branches.py`'s failed only inside the sandbox,
which holds `tools/` and no `.git`. **Same verdict, different causes, and the tool is right to
refuse rather than score either.**

## `prior-art.py` — has anyone already written this, in a channel that could hold the answer?

```
python3 tools/architect-sweeps/prior-art.py "<the phrase you are about to write about>"
```

**Measured defect, three panes, one night:** DEV2 opened #353 at `22:56:00Z`; DEV3 opened #356 at
`22:59:25Z` on the same ruling; ARCHITECT then ruled on the question twice. **All three checked
`main`.** ⇒ An open PR is not on `main`, so the probe's corpus **structurally could not contain the
answer.**

★ **Its first run produced the sharper reading:** `main-tree` finds *"positive control"* in 16
files, so checking `main` was **not empty — it was answering a different question.** *"Does this
exist?"* and *"is someone writing it right now?"* both come back as *"prior art"*, and **only the
open-PR channel answers the second.** ⇒ The tool reports **per channel and refuses to aggregate.**

⛔ **Controls are two-sided and run before every query** (DEV2, #353): a term certain to be present
must be **FOUND**, and a **per-run uuid nonce** must be found **nowhere**. A one-sided control
catches a false ABSENT and is blind to a predicate matching everything.

⚠ **Three channels only** — it says nothing about peer messages, transcripts, or another estate's
board, and the bound is printed on every run.

## What is NOT here

- ⛔ **The activity-burst analysis** (5 bursts, gaps of 49/4/72/72 minutes — the evidence that a
  depth monitor measures *invocation*, not idleness) reads a session transcript by path. It is
  omitted deliberately: a committed script that walks `~/.claude/projects` invites being pointed
  at another pane's transcript, and *whether one role may read another's transcript* is not mine
  to settle by committing a convenience. The finding is in #177; the code is not.
- **The `Held by:` census and the queue-criteria census** were three-line loops over files already
  in this repo. Anyone can rewrite them from the finding; committing them adds nothing but a row.
