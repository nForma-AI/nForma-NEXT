# Role goals — what one must contain, and who owns it

A role goal is the durable answer to *"what do I do when nobody has dispatched me?"*
Without one a role is purely reactive, and the orchestrator becomes the fleet bottleneck
by construction rather than by choice.

## ⛔ Why these live in a repository

They previously lived only in `~/.claude/goals/` — machine-local, unversioned, with no
ownership metadata and no review gate. Three consequences, all measured:

- **No ownership.** Doctrine for seven agents was authored in one pass, by a role that does
  not own process, with no review. Nothing could have objected, because there was nowhere
  for an objection to attach.
- **No provenance.** A goal file cannot be diffed against what it said yesterday, so a
  calibration that drifts is indistinguishable from one that was always wrong.
- **No survival.** A machine-local file dies with the machine. The measurement register
  records this as a **falsified** row: instruments other roles depend on were living
  outside version control.

⇒ Vendored here so that changing another role's operating doctrine requires a **pull
request**, which is visible whether or not anyone remembers the rule.

## What a role goal must contain

1. **Desired state** — the condition that would make the role's work finished, written so
   that a reader can tell whether it currently holds.
2. **Reserved actions** — what the role must never self-grant. State them; do not imply them.
3. **The self-dispatch order** — what to do when a task completes and nothing was assigned.
   ⚠ It must be able to terminate. See below.
4. **Standing calibrations** — measured numbers with their provenance, so they are not
   re-derived wrongly. A number without a measurement date is a rumour.
5. **What the role does NOT own** — the boundary is half the definition, and it is the half
   that gets absorbed.

## ⚠ A self-dispatch list must be able to return EMPTY

A ladder whose lower rungs are *"take any undiagnosed red / verify any peer claim / harden
any guard"* can never be exhausted — there is always one of each. Such a list has no
terminating state, so it **manufactures work**, which every role prompt forbids in the same
words: *maximum autonomy is not maximum activity.*

> **Write the rungs so that "none applies" is reachable this week.** A loop that cannot
> report empty is not autonomy, it is a busy-wait.

## Who writes one

DX owns the goal standard and reviews goal changes; the role itself proposes its content.
A role appearing without a goal is a DX defect, not the role's.

## ⛔ There is no org-wide standard this shadows

Checked against `df-wiki@origin/main` with a passing known-positive control: no role-goal
standard exists anywhere in the org. This is a first, not a fork.
