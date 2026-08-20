# Reference implementations — repos to watch, and what each is authoritative for

⛔ **Why this file exists.** A 249-line root-cause investigation of a failure this fleet spent a
night re-deriving from CI logs had been sitting on this machine since **2026-07-20** — a month,
not an evening. The standing rule *"check just-akash before blaming a provider"* existed, was
in a memory index, and **nobody opened its `docs/`.**

⚠ **And searching is not the remedy.** Measured 2026-08-20: **304 repositories** under
`~/code`, and **14,517 markdown files mention "exec"**. A keyword sweep returns a haystack. What
is needed is a *curated* list of what a repo is authoritative **for**, plus a way to notice when
it changes.

⇒ So each entry records a **blob sha at the time of writing**. `tools/reference-check.py` tells
you which entries have moved since — those are the fixes to consider adopting. A register that
cannot detect its own staleness is the thing this fleet has caught four times tonight.

## How to use it

```sh
python3 tools/reference-check.py          # 0 all current · 1 something moved · 2 established nothing
```

⚠ **A CHANGED entry is not an instruction.** It says the upstream artifact moved; whether the
change applies here is a judgement, and the tool deliberately does not make it.

⛔ **AND NEITHER IS AN ENTRY ITSELF.** A reference is authoritative for **its own repo's
findings**, not for this one's. Within twenty minutes of the first entry being read here, a
diagnosis from it — *a synthetic zero means the lease was closed* — was attached to a bucket in
this repo where it did not hold: the provider's own lease-status reported **1/1 READY, 0.3–0.7
seconds before the failing exec**. Same symptom, different cause.

⇒ ★ **Port the METHOD and the INSTRUMENT; re-derive the DIAGNOSIS.** The frame tracer, the
liveness check and the marker-echo transfer directly. *"It was a closed lease"* is a finding
about their provider on their day, and using it here without running the cheap direct check is
the wrong-population error one repo over.

## The register

| repo | artifact | authoritative for | blob at time of writing |
| --- | --- | --- | --- |
| `just-akash` | `docs/exec-reliability-investigation.md` | **lease-shell `exec` reliability** — distinguishing a transient SPDY/CRI stdout **drop** from a **synthetic `{"exit_code":0}` against a closed lease**. Method: upstream code trace + in-process frame instrumentation + live A/B on two providers + two-round quorum review. Refutes the "reorder" hypothesis in code. | `f4f3e9db392ac526cf204ba9ec7a71dd6139d545` |
| `just-akash` | `just_akash/transport/lease_shell.py` | the **exec transport itself** — the implementation measured at `exec pass=41 fail=0`. Carries the `stdin` handling that a hypothesis here named as prime suspect and this repo **refutes by running it**. | `ceaed425d28310c8832f249e22bb76264a1431d5` |
| `just-akash` | `just_akash/smoke_providers.py` | **`JUST_AKASH_TRACE_FRAMES`** — per-frame `(code, len, rel_time)` recording. ★ The instrument that separates a drop from a reorder from a synthetic zero. This fleet has no equivalent. | `d621760971eb7af1ed7f9bfde5e9307c6c4b86d3` |

⚠ **Three entries, one repo, and that is the honest state of it.** `just-akash` is the only
sibling I have *verified* is authoritative for anything this fleet re-derives — it is referenced
by four workflows in `DigitalFrontier-infra` and shares an org, so it is watchable on the forge
as well as on disk.

⛔ **Do not pad this table.** An entry that nobody verified is worse than a short list: it
manufactures the impression that the "has this been done?" question has been answered broadly
when it has been answered once. Add an entry when you have **read** the artifact and can say
what it is authoritative for in one sentence.

## What this does NOT do

- It does not tell you a change is relevant. It tells you the file moved.
- It does not search. Searching 304 repos was measured and returns a haystack; this is a
  curated list precisely because search failed.
- ⚠ It watches **files, not repos.** A fix landing in a file not listed here is invisible to it.
  That is the gap to close by adding entries, not by widening the tool.
