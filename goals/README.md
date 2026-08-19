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

## ⛔ A self-dispatch loop needs an ENGINE, and the engine must not carry authorization

A goal document cannot make an agent self-invoke. An agent executes when prompted and then
waits, so a written loop is an instruction with nothing behind it — measured: eight agents
sat at `waiting`, each having stated a next action and stopped.

**The primitive exists.** `CronCreate` enqueues a prompt to the agent itself on a schedule;
`Monitor` wakes it on an event. Verified by resolution rather than assumption: both resolve
for at least one DEV role. ⇒ **The loop was unrun because nobody said the primitive was
there.** That is a documentation failure, not a capability gap.

Three constraints, from reading the schemas rather than assuming them:

- **`ScheduleWakeup` is not the general primitive.** It is bound to `/loop` dynamic mode.
  `CronCreate` is the general one. Telling a fleet to "use ScheduleWakeup" sends most of it
  into a category error.
- **`CronCreate` is session-only and idle-gated.** Nothing is written to disk, and jobs fire
  only while the REPL is idle — so a loop dies silently at compaction or exit, which is the
  same failure as a goal file, later and harder to see. **Re-arming must be the loop's own
  first action**, or the fix reintroduces the defect on a delay.
- ⛔ **A scheduled prompt must never carry authorization.** If the timer says *"continue the
  queue"* and the queue's next item is a push, the agent has self-granted CI spend on a
  timer. A loop may dispatch diagnosis and preparation, and must stop at anything reserved.

⚠ The third is a security constraint, not a style note. Eleven forged authorizations reached
agents' input boxes in a single session. **A timer that re-enters an agent with a
plausible-sounding instruction is the same attack surface — and worse, because it carries
genuine provenance.** A forgery can be caught by checking the channel; a real cron job
cannot.

## Who writes one

DX owns the goal standard and reviews goal changes; the role itself proposes its content.
A role appearing without a goal is a DX defect, not the role's.

## ⛔ There is no org-wide standard this shadows

Checked against `df-wiki@origin/main` with a passing known-positive control: no role-goal
standard exists anywhere in the org. This is a first, not a fork.
