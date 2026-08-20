# The role prompts are not on the launch path

**Measured 2026-08-20 against the eight fleet sessions active in the last 12 hours.**

`prompts/*.md` is 3,949 lines of role specification. `docs/FOUNDING-THESIS.md` is written about
operating it. `prompts/README.md` calls it "the five role prompts as they exist **today**".

It had reached **one** of the eight sessions running when this was written, and that one is the
session that wrote this file — by opening `prompts/DX.md` with a tool, not by being launched
with it.

## What was measured

| session | role as resolved | STATE declarations (positional) | `SendMessage` calls | `NFORMA_ROLE` present |
|---|---|---|---|---|
| `c67ebcb4` | DX | 98 | 48 | only as text this session read |
| `e4a7769d` | TEAMLEAD / DEV2 | 0 | 119 | no |
| `ec0d07f0` | DEV3 | 0 | 32 | no |
| `b00d725a` | DEV4 | 0 | 26 | no |
| `96827e4b` | DEV5 | 0 | 19 | no |
| `6fc2dca8` | DEVOPS | 0 | 18 | no |
| `4358eeaa` | DEV1 | 0 | 9 | no |
| `6150ffb2` | ARCHITECT | 0 | 9 | no |

⚠ **Declarations are counted positionally** — final non-empty line of an assistant turn — never by
searching for the token. The distinction is not academic here: `e4a7769d` contains the string
`STATE: WORKING` on five lines and has declared **zero** times. All five are quotations, in
messages *about* the protocol. A keyword scan would have reported that pane as compliant.

`tools/fleet-state.py --active-hours 12` reports the same split independently: **1 of 8 fleet
sessions has declared a STATE at all**, across 881 to 3,001 assistant turns each.

Three further readings, each cheap and each pointing the same way:

- **`NFORMA_ROLE` appears in exactly one transcript on this machine** — the one that grepped the
  README for it. The identity mechanism `prompts/README.md` calls "the load-bearing choice" has
  never been observed in a running pane.
- **`ROLE-READY` likewise: one transcript.** The handshake the recipe section is built around has
  not been performed by the fleet in operation.
- **The live bootstraps are a different artifact, not a stale copy of this one.** Sampled three
  panes; each opens `You are <ROLE>, an IMPLEMENTER reporting to TEAMLEAD. Repo: … Work in YOUR
  OWN worktree`, 2–4 KB of hand-written task prose. None of those three phrases occurs anywhere
  in `prompts/*.md` — which opens `You are DEVOPS for an autonomous software-engineering team`.
  `IMPLEMENTER` is not this repository's word for these roles. One pane still bootstraps as
  `CODER2 … supervised by MAINTAINER`, a vocabulary two renames old.

★ **The push channel this protocol needs is already in heavy use.** The same eight sessions made
**274 `SendMessage` calls** in the window — every pane sends, DEV2/TEAMLEAD 119 times. So the
transition protocol is not asking for a new channel or a new capability; it is putting a **format
and a trigger** on one the fleet already runs. That is the cheapest kind of convention to adopt and
the easiest to audit, and it is why the audit could be built the same day as the rule.

⇒ The committed prompts are **not the source the live bootstraps are cut from.** They are a
parallel specification of a fleet that has not been launched.

## A control I had to throw away

The first version of this measurement grepped each transcript for the literal rule text
(`End every turn with a declared STATE line`) and found **6 hits in DX, 0 in all seven others** —
which reads as a clean delivery result with a working control.

**It is not one.** Every hit in DX is inside a `tool_use` or `tool_result` block: they are this
session's own `grep`s of `prompts/DEV.md`, run minutes earlier while writing this. The control
proved that a session which reads the file contains the file's text. It could not have fired for
any other reason, in any session, ever.

## ★ The rule: the reader must not be the auditor

> **THE READER MUST NOT BE THE AUDITOR.**
>
> Evidence that a subject received something is void when the only subject that shows it is the
> one doing the counting. Ask *who read it, and why* — never *what kind of record it is*.

⛔ **The tempting shorthand — "tool records don't count" — is wrong, and this document contains a
measurement that refutes it.** Probing whether panes receive their `~/.claude/goals/*.md` returned
**5 of 5 present, 0 as given records, 1–3 as tool records**: panes are never handed their goal,
every one of them goes and reads it. Those tool records are valid evidence of a working channel.

⇒ **Same evidence type, opposite verdicts, for a stated reason.** Above, the sole reader was the
auditor and the measurement was of its own auditing. There, the readers are five independent panes
performing routine startup and the auditor is not among the subjects. The record type is identical
in both. The standing is not.

⚠ It also subsumes the older rule it sharpens — *a control must come from a population the failure
cannot reach.* An auditor counting itself is a population of one that the failure reaches by
construction. Prefer the new form: it is checkable by asking a single question, and it does not
require knowing the failure mode in advance.

The finding survives because the *other* three readings do not share that defect — `NFORMA_ROLE`,
`ROLE-READY`, and the bootstrap-text comparison are each properties of what the pane was **given**
rather than of what it later went looking for. Recorded here rather than quietly dropped, because
the discarded control is the more transferable half.

## Why this is a fifth delivery-failure mode, not one of the known four

`docs/FOUNDING-THESIS.md` §2 names three ways `sendCommand` reports `{"sent": true}` for a message
that reached nobody; issue #8 asks for a fourth — *alive, queued, and not yet read.* All four are
about a **message in flight**.

This is not that. Nothing was sent. There is no queue entry, no acknowledgement to be false, and
no `lastTransitionAt` to compare against. The **standing instruction** was edited in a file that
the launch path does not open, so the edit was complete, correct, reviewed, merged — and inert.

> The four known modes ask *did this message arrive?* This one asks *was this file ever on the
> path at all?* — and the honest answer is that nobody had checked, for 3,949 lines.

It is also the mode with the worst failure signature: a message that vanishes leaves an agent
visibly unresponsive, whereas an undelivered standing rule leaves the fleet looking **disobedient**.
Seven roles were, until this measurement, not declaring a STATE line that no one had ever asked
them for.

## What this does not establish

- **Not that the panes are misconfigured.** They were launched by hand with bespoke task prompts,
  which is a legitimate way to run a fleet. The defect is the belief that editing `prompts/*.md`
  changes their behaviour.
- **Not that the recipe is broken.** `.daintree/recipes/nforma-fleet.json` and
  `scripts/validate-recipe.py` are unexercised here, not disproven. Nothing was measured about
  what happens when the recipe *is* used, because on this machine it has not been.
- **Not a compliance finding about any role.** No agent ignored anything.

## The remedy is a launch-path decision, and it is not DX's to take

Three shapes, in ascending cost:

1. **Bootstrap by reference.** The hand-written prompt gains one line: *read `prompts/<ROLE>.md`
   before starting.* Cheapest, and it makes the file's content load-bearing on the next launch of
   any pane. It does not reach a pane already running.
2. **Launch through the recipe.** Uses the mechanism already built, validated, and documented, and
   gets `NFORMA_ROLE` / `ROLE-READY` for free. Costs a fleet restart, and the recipe has never been
   exercised against real work.
3. **Reach the panes that are already running.** The only option that touches today's fleet, and
   the only one with no mechanism behind it — the running sessions cannot be re-prompted, so it is
   a message to eight panes and a request that they read a file.

⚠ Whichever is chosen, the check that makes it stick is not a review of the prompt: it is
`grep -c NFORMA_ROLE` (or the rule text, in a **non-tool** record) against a freshly launched
pane's transcript. **An edit to a prompt is a hypothesis about a launch path until a launched pane
is read back.**

## Standing consequence

Any change to `prompts/*.md` — including the transition protocol added alongside this file —
should state its delivery status rather than assume it. The four implementer prompts and
`TEAMLEAD.md` now each carry that caveat inline, pointing here.

---

# Option 1, executed — and the target moved

TEAMLEAD ruled Option 1 (bootstrap by reference) and authorised it, with the acceptance test
*"an edit to a prompt is a hypothesis about a launch path until a launched pane is read back."*
Executing it moved the target twice.

## The hand-written bootstrap has no file, but the goal file does

Option 1 as stated adds a line to "the hand-written prompt". That prompt is typed per launch and
exists nowhere on disk — grepping both repositories and the operator's config for its distinctive
phrasing returns nothing. There is no artifact to edit.

**The goal file is the durable equivalent, and unlike the prompt it demonstrably arrives.** Probed
five panes with the longest prose line unique to each one's own goal file:

| pane | goal content present | as a *given* record | as a *tool* record |
|---|---|---|---|
| DEVOPS | yes | 0 | 3 |
| ARCHITECT | yes | 0 | 1 |
| DX | yes | 0 | 3 |
| DEV3 | yes | 0 | 2 |
| DEV4 | yes | 0 | 1 |

⇒ **Panes are never handed their goal; every one of them goes and reads it.** The channel is a
pull, and it works — which is exactly what a pointer needs.

⚠ **This is the reading discarded earlier in this document, and here it is valid** — by the rule
stated there: *the reader must not be the auditor.* Above, the sole positive was my own grep. Here
the readers are five independent panes performing their own routine startup and I am not among the
subjects counted.

## What changed, verbatim

An `## ⚠ Authority` section was added at the top of each role goal in `~/.claude/goals/`, naming
the canonical prompt by **absolute path** — panes work in `DigitalFrontier-infra`, so a
repo-relative `prompts/DEV.md` does not resolve from their tree.

| goal file | prompt | reaches |
|---|---|---|
| `dx-engineering-effectiveness.md` | `DX.md` | DX — *already had it* |
| `teamlead-verified-progress.md` | `TEAMLEAD.md` | TEAMLEAD |
| `architect-technical-integrity.md` | `ARCHITECT.md` | ARCHITECT |
| `architect-technical-knowledge-integrity.md` | `ARCHITECT.md` | ARCHITECT |
| `devops-substrate-and-fleet.md` | `DEVOPS.md` | DEVOPS |
| `devops-control-plane.md` | `DEVOPS.md` | DEVOPS |
| `dev-implementation.md` | `DEV.md` | DEV2, DEV3, DEV4, DEV5 |
| `dev3-implementation-and-verification.md` | `DEV.md` | DEV3 |
| `dev2-state-handoff.md` | `DEV.md` | DEV2 |

All 47 files were backed up first; the diff is **purely additive** — 8 files changed, 0 original
lines removed, verified line-by-line against the backup.

⛔ **Coverage is 7 of 8, not 8 of 8. `DEV1` reads no goal file at all** — zero references to
`.claude/goals/` across its entire transcript. It cannot be reached by this route, and saying
"Option 1 is deployed" without that clause would be the same overstatement this document exists
to correct.

★ **`dx-engineering-effectiveness.md` already carried this pointer, and DX is the one pane of eight
that has the prompt.** That is a single-case validation of the mechanism, and it is **confounded**:
DX's task tonight *was* the prompts, so it had a second reason to open the file. n=1 with a
confound is a promising sign, not proof. The other six panes are the real test.

## ⛔ The stated acceptance test cannot pass, and would have failed a working deployment

TEAMLEAD's test is `grep -c NFORMA_ROLE` against a freshly launched pane. **`NFORMA_ROLE` is set by
the recipe** — it is Option **2**'s mechanism. Under Option 1 nothing sets it, so the grep returns
**0 on a perfectly successful deployment**, and the deployment would be reported as failed.

The principle behind the test is right and is kept; only the observable is wrong. Under Option 1 the
correct test is a **conjunction**, because either half alone reproduces a known defect:

```
(a) the pointer is in the goal file the pane read     → delivered
(b) a tool record shows prompts/<ROLE>.md was opened  → consumed
```

- **(b) alone is the contaminated control** from earlier in this document: a pane that opened the
  file for its own reasons satisfies it.
- **(a) alone is delivery without consumption** — precisely the mode #8 exists to name.

⇒ Both, on a pane that is **not** the one that made the edit. `NFORMA_ROLE` returns as the correct
test if and when Option 2 is chosen; it is not wrong, it is measuring the other option.

## The vendoring did not establish a direction, and `goals/README.md` says it did

`goals/README.md` states these were vendored into the repository *"so that changing another role's
operating doctrine requires a **pull request**, which is visible whether or not anyone remembers
the rule."*

⛔ **It does not.** The repo copies and the live copies have diverged — 296 lines against 67,
462 against 80, 301 against 87, 260 against 186 — and **the live copy is the one panes read.** (Live counts are as measured *before* this change added
the pointer.)
Changing a role's operating doctrine still requires editing an unversioned machine-local file,
which is what this change had to do to have any effect at all.

⇒ Vendoring produced a *reviewable* copy without making it the *delivered* one. That is the same
shape as the prompts: two artifacts, one authoritative in review and the other in effect, with no
mechanism keeping them equal and no alarm when they diverge. **A copy under review is not a copy
in force**, and the README's claim should be corrected to say which of the two it is.

## Status: deployed, NOT verified

Half (a) holds now — nine goal files carry the pointer. Half (b) cannot be observed until a pane
reads a role prompt, so **Option 1 is not done**, and reporting the commit as completion is the
exact substitution TEAMLEAD's rule forbids. The literal check, runnable by anyone:

```sh
python3 - <<'PY'
import glob, json, os
hits = {}
for p in glob.glob(os.path.expanduser("~/.claude/projects/*/*.jsonl")):
    for line in open(p, errors="replace"):
        if "nForma-NEXT/prompts/" not in line:
            continue
        try:
            rec = json.loads(line)
        except Exception:
            continue
        c = (rec.get("message") or {}).get("content")
        kinds = {b.get("type") for b in c if isinstance(b, dict)} if isinstance(c, list) else set()
        if kinds & {"tool_use", "tool_result"}:
            hits[os.path.basename(p)[:8]] = hits.get(os.path.basename(p)[:8], 0) + 1
print(hits or "no pane has opened a role prompt yet")
PY
```

⚠ **Exclude `c67ebcb4`** when reading the result — that is the session that made the change, and
counting it repeats the discarded control at the top of this document.
