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

> A control drawn from a population the bug cannot reach measures the drawing, not the bug.

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
