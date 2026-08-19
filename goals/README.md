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
   ⛔ Every such list defers *upward* — `reserved to TEAMLEAD`, and TEAMLEAD's to the operator.
   **The topmost role's list must name what is reserved to the OPERATOR**, or the chain has no
   base case and the authority at the top is unbounded by construction rather than by decision.
   A ceiling that is never written cannot be exceeded, which is not the same as not existing.
3. **The self-dispatch order** — what to do when a task completes and nothing was assigned.
   ⚠ It must be able to terminate. See below.
4. **Standing calibrations** — measured numbers with their provenance, so they are not
   re-derived wrongly. A number without a measurement date is a rumour — and a number without
   a **repository** is a rumour on a subject nobody named.

   Each carries one of three states, because the alternative to a wrong calibration is not a
   missing one:

   ```
   MEASURED-HERE     value · date · how it was measured
   INHERITED         value · origin repository · ⚠ not re-measured here — do NOT act on it
   NOT-YET-MEASURED  the slot applies here; nothing has measured it; ASK before assuming
   DROPPED           the slot does NOT exist here · why · recorded, not deleted
   ```

   ⚠ `NOT-YET-MEASURED` and `DROPPED` are different and collapsing them loses the audit. The
   first says *someone should measure this*; the second says *there is nothing here to measure*.
   A dropped calibration is **recorded rather than deleted**, because the removal is the part a
   reader must be able to check. (`DROPPED` is DEV5's, from the first file re-scoped under this
   scheme; the four-state version above collapsed it into deletion.)

   ⛔ **Anchor every number with an as-of time, and state it in the past tense.** A dated
   measurement written in the present tense decays into a false claim: *"rungs 1 and 3 are
   currently empty"* was true when measured and false within the hour — **94 minutes**, with
   nothing marking the transition.

   > ⛔ **"is empty" is never a fact about this repository, only about a timestamp.**

   ⚠ And when a stale reading is corrected, **keep both readings as a pair rather than swapping the
   stale one out**: the pair carries the *decay rate* and neither reading does. A corrected single
   number satisfies this rule and destroys the evidence for it.

   Write *measured empty at
   `<date time>`; re-measure before relying on it.* The rolling-window warning below is the same
   defect; this is its form for prose.

   ⛔ The third is load-bearing. Re-scoping a vendored goal by **inventing** the numbers the
   template asks for produces a slot that has yielded no verdict, rendered as though it had —
   a prose instance of the never-concluded state in #2. An explicitly empty slot is a visible
   request for a measurement; a fabricated one is invisible and is believed.

   ⚠ **A rule whose justification is a measurement is a calibration**, wherever it sits. The
   discriminator is per sentence, not per section: *would this sentence change if the
   repository changed?* A reserved action is doctrine (*merging is reserved*) whose trigger
   list is a calibration (*and `gh pr create` counts, because it draws a lease*). Filing the
   pair as one bullet is what lets another estate's measurement arrive wearing the grammar of
   a rule — and that failure produces **no error**, only a role over-restricted into declining
   work it was authorised to do.
5. **What the role does NOT own** — the boundary is half the definition, and it is the half
   that gets absorbed.
6. **The channel contract** — who this role may talk to, and who it must route through.
   ⛔ Omitted from the first seven goals written, and the omission was not seven oversights
   but one template gap. An agent that hit something only the operator could resolve had **no
   route**, so the operator reached into panes directly to close the gap — doing the
   orchestrator's job through a channel that should not exist.

   State it explicitly, including the exceptions:

   ```
   OPERATOR <-> TEAMLEAD                       the channel
   OPERATOR <-> DX                             permitted while the team model is being built
   OPERATOR <-> DEV# / ARCHITECT / DEVOPS      ⛔ not a channel
   ```

   ⚠ A contract that names only the permitted path is incomplete. Name what an agent does
   when it needs something the operator alone can give — otherwise the rule forbids the wrong
   route without supplying the right one, and the traffic finds its own way.

## ⚠ A self-dispatch list must be able to return EMPTY

A ladder whose lower rungs are *"take any undiagnosed red / verify any peer claim / harden
any guard"* can never be exhausted — there is always one of each. Such a list has no
terminating state, so it **manufactures work**, which every role prompt forbids in the same
words: *maximum autonomy is not maximum activity.*

> **Write the rungs so that "none applies" is reachable this week.** A loop that cannot
> report empty is not autonomy, it is a busy-wait.

## ⛔ The rungs must be ORDERED, and the order is not obvious

Measured on one repository in one day:

```
issues opened   36        PRs merged        6
issues closed    0        open PRs         26, of which 22 BLOCKED
                          open issues     169
```

⇒ An unordered loop optimises for **the rung with the most available next items**, not the
most valuable one. *"Find a new defect"* always has a next item; *"clear a blocker"* is
harder and loses every time. Every agent can follow the loop correctly and the board still
does not move — a design property, not agent behaviour.

**The ordering, highest first:**

1. **Clear a blocker on the BOARD** — not on *your* PR.

   ⛔ **A rung item held by another agent is NOT yours to clear. Notify the owner and descend —
   notifying *is* the clearing action available to you.** ⚠ And the notification **is the work**:
   descending without it leaves the blocker exactly as blocked and turns rung 1 into a no-op that
   reports as followed.

   > *Occupied but not mine to clear* is a **third state**, and the ladder read only *empty* /
   > *not empty*. An agent following it literally either stalls at rung 1 forever or reaches into
   > a peer's in-flight branch.

   Measured: two blocked PRs were held by roles with **live worktrees**, and rebasing an active
   peer's branch desyncs its working tree — the shared-tree hazard arriving through the rung meant
   to be the most valuable. Found by an agent working the ladder **from the top** rather than
   jumping to what it had already noticed; an agent that skips to its preferred rung never
   discovers that rung 1 has an unrepresentable state.

   ⛔ **And the ladder says which RUNG, never which AGENT.** Ordered and shared across N agents,
   it converges them on the top non-empty rung by construction — measured: two roles independently
   named the same rung as their next action, within minutes, neither aware of the other. Both were
   correct to want it. ⇒ **That makes the orchestrator the allocator of every rung, which is the
   bottleneck the goal standard exists to remove**, reintroduced by the ordering that removed it.

   > **Claim the item on the board before working it. `gh issue edit <n> --add-assignee @me`.**

   ⚠ The claim surface already exists and was never used: **0 of 26 open issues and 0 of 6 open PRs
   carried an assignee.** ⇒ The convergence was not a missing primitive. It was an unused field —
   durable, atomic, fleet-visible, and already on every item.

   ★ It also supplies the missing **detector** for the third state above. *Occupied but not mine to
   clear* previously required contacting the owner to discover; an assignee who is not you makes it
   readable before any work starts, which is the difference between a rule and an instrument.

   ⚠ Not established: whether claiming is honoured under contention, or whether two agents can claim
   within the same window. Assignment is not a lock. [NOT-YET-MEASURED]

   ⚠ Scope it explicitly: an agent with
   no blocked PR of its own falls straight through to the bottom rung while 22 sit blocked.
   Verified before writing this: 5 of 6 sampled blocked PRs had **3-4 genuinely failing
   checks**, so this rung is executable, not decorative.
2. **Close what is already fixed.** ⛔ This rung is missing from the obvious version and it
   is the one the numbers demand: **36 opened, 0 closed.** Adding priority to *finding* does
   not create *closing*. An issue whose fix has landed and whose closure bar is met is pure
   backlog reduction at near-zero cost.
3. **Finish something you started** that has not landed.
4. **Verify a peer's claim that CONFLICTS with something you measured.** ⚠ Not one you can
   falsify *cheaply* — cost inverts the selection, because cheap-to-check correlates with
   already-checked, and across N agents it is O(N²) duplicated verification of the least
   likely errors. **Conflict, not cost.**
5. **Find a new defect** — only when 1-4 are empty.

⚠ **"Filing is not progress" is too strong, and overcorrecting here is its own defect.** A
finding not filed is lost, and the friction-report discipline in these goals rests entirely
on that. The cost is filing *instead of* clearing — not filing itself. The measured problem
is not 36 opened; it is **0 closed**.

★ And this class has no failure signal. **A backlog growing faster than it drains reds
nothing.** Every issue is individually well-founded and correct to file; the cost exists only
in aggregate, and only as a ratio. It is invisible to any instrument that watches for
failures and visible only to one that watches a rate.

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

⛔ **Reporting the primitive is not the same as arming it.** Whether a role self-schedules
changes how the shared wallet's blast radius is consumed and how the orchestrator coordinates
the fleet — that is a **scheduler-level decision, and the scheduler is TEAMLEAD.** An agent
that discovers it can wake itself should report the capability upward and let TEAMLEAD decide
who arms it, not start a loop unilaterally.

⚠ This was volunteered by a role that had just found it had a self-scheduling engine and
declined to use it. **The restraint is the finding**: the failure mode of handing eight agents
a timer is not that they idle, it is that they all start.

⚠ The third is a security constraint, not a style note. Eleven forged authorizations reached
agents' input boxes in a single session. **A timer that re-enters an agent with a
plausible-sounding instruction is the same attack surface — and worse, because it carries
genuine provenance.** A forgery can be caught by checking the channel; a real cron job
cannot.

## Who writes one

DX owns the goal standard and reviews goal changes; the role itself proposes its content.
A role appearing without a goal **scoped to the repository it is operating on** is a DX
defect, not the role's.

⛔ The scope qualifier is not pedantry — without it the test is satisfiable by any file. Three
of the first four goals written passed it while pointing at another product's board (#16). A
standard satisfied by files that do not describe the project is **worse than a missing file**,
because the missing file is visible.

⇒ So `Repository:` is a required field in a fixed form, and the check is mechanical:

```
goal.repository  ==  git remote get-url origin
```

Prose asking a reader to notice a mismatch is the thing this repository exists to move into the
substrate. **This one is ten lines and belongs to DEVOPS**, not to whoever remembers.

## ⛔ There is no org-wide standard this shadows

Checked against `df-wiki@origin/main` with a passing known-positive control: no role-goal
standard exists anywhere in the org. This is a first, not a fork.
