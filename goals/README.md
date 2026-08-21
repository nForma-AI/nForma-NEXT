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
2. **Reserved actions** — what the role must never self-grant. State them; do not imply them —
   **and state them WHERE EVERY AGENT THEY BIND WILL READ THEM.**

   ```
   a GRANT       is complete when ONE agent hears it    -> a message is the right channel
   a RESERVATION is complete when EVERY agent hears it  -> a message reaches one pane
   ```

   ⛔ A reservation delivered by message is satisfied for its recipient and **silently absent for
   everyone else** — and it reads as enforced from the orchestrator's side, because the only pane
   observable is the one that was told. Measured: issue closure was reserved in **0** of four goal
   files, `goals/README.md`, `TEAMLEAD.md` and `DEV.md`, and existed only in one message to one role.

   ★ **The asymmetry selects against the compliant agent.** The role that heard it declined to close
   and reported zero; the role that never heard it closed one and was right to. Under an unwritten
   reservation, **obedience is indistinguishable from underperformance** — and the zero reads as
   thoroughness, so nothing prompts anyone to look for the cause.

   ⇒ **A reservation lives in ONE document that every goal file it binds REFERENCES. Never in a
   message, and never as four copies.** That document is **`goals/RESERVED-ACTIONS.md`**; a goal
   file's own Reserved section **points at it** rather than restating it.

   ⚠ The first draft of this clause said *"in every goal file it binds"*. **That is wrong**, and the
   reason generalises: four copies with nothing syncing them is the hand-maintained-count defect at
   the doctrine layer — one count in this repository drifted **five times in one day, by five
   authors**. A reservation duplicated four ways drifts the same way, and **its drift produces no
   error.**

   ⇒ It is also the reference-not-the-thing rule in a third medium. A goal **file** carrying a copy
   of a reservation is the same defect as a **message** carrying one: the copy is
   authoritative-looking and unsynced. The goal file **points**.

   ⛔ **And this is not free — it trades a sync defect for a delivery one, so state the cost rather
   than discover it.** Four copies are at least *in* the file the agent already reads. A referenced
   document is **one more artifact a running agent has not loaded**, which makes this correct **and
   more dependent on the delivery gap below.**

   ⛔ **A grant issued after the fact cannot bound the action it follows.** Acting first and
   reporting after, with reasoning and an offer to reverse, is better than silence and is **not**
   authorization.

   > ⚠ **An agent that arms only what it is confident will be ratified has replaced the
   > authorizer's judgement with its own prediction of that judgement.**

   That is why *"I would have granted it"* makes the precedent **worse** rather than harmless: the
   outcome being right is exactly what makes the substitution invisible. ⇒ Stated for reserved
   actions generally, not for self-scheduling — the narrower framing is what let the substitution
   be reasoned past the first time.
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

   ## ⛔ And a removal must not be what makes a claim true

   `DROPPED` is the **legitimate** removal: the slot does not exist here, recorded with its reason.
   This is the test that separates it from the illegitimate one.

   > **Making a claim true by damaging the thing it describes is not a correction.**

   Measured: a `/goal` pointer asserted a goal file *"had no Reserved section."* The heading was
   present in **all six revisions the file had ever had**. The available way to satisfy the premise
   was to **delete the section** — removing four reservations that actually bind. A second pointer
   asserted a file was *"re-scoped to this repository"* and *"always scoped here"*; **neither was
   true**, and that one happened to have no edit that could satisfy it. (#93)

   ⇒ The pressure is not toward believing a false premise. It is toward **making the artifact match
   it**, because that is the cheaper of the two ways to resolve a contradiction between a document
   and an instruction about the document.

   ⛔ **There is a third form, and it is the least likely to be questioned: ADDITION.**

   ```
   deletion   remove the thing the claim denies      -> conspicuous, obvious victim
   narrowing  shrink until the claim is true         -> defensible in isolation
   ADDITION   add the thing the claim says is missing -> reads as FIXING A GAP
   ```

   ⚠ Measured: a drift row asserted a goal file *"carries no pushing-to-`main` clause — a live
   gap."* **False** — that file had converted to a pointer and was the only one conformant with
   the one-source ruling. An agent acting on the row would have **added the clause back**, undoing
   the conversion and re-introducing the duplication the ruling exists to remove.

   ⇒ ★ **An added reservation is more defensible in isolation than a deletion**, so it attracts
   *less* scrutiny while doing the same work: making the artifact match the claim. **The pressure
   is identical and the disguise is better.** (ARCHITECT, from the row it refuted.)

   ⛔ **And the dangerous form is not deletion — it is NARROWING.** Deleting a whole section is
   conspicuous and has an obvious victim. These do not:

   ```
   a calibration           "that number was never measured here"  -> delete it, premise satisfied
   a caveat                "that limit does not apply"            -> remove it, premise satisfied
   a checker's population  "that file is not in scope"            -> exclude it, premise satisfied
   ```

   ⚠ **Every one is a normal, defensible edit in isolation**, and the role that supplied this
   narrowing had made three of them the same evening for good reasons. **The boundary is not
   obvious from the inside**, which is why it needs to be a question rather than a judgement.

   > **Before removing a caveat, a calibration, an exclusion or a scope line, ask whether the
   > removal makes some claim true. If it does, that is the CLAIM's problem, not the artifact's.**

   ⇒ A removal that survives that question is a `DROPPED`. One that does not is the premise winning.

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

   ⛔ **And this rule is structurally blind to a number that was false on arrival.** It was written
   to catch a reading that **decays**; it does nothing to one that was never true of the moment it
   names:

   ```
   decay          true when written, false later     -> the past tense FIXES it
   wrong anchor   never true of the moment named     -> the past tense PRESERVES it perfectly
   ```

   ⇒ **Stamping a wrong anchor in the past tense converts a confidently-undated false claim into a
   confidently-dated one. The stamp makes it MORE citable, not less.** Measured: a board reading was
   anchored to `20:22Z`, the moment a PR **merged** — the event that prompted writing it down — while
   the instrument had run some 35 minutes earlier. Nine PRs were open at the cited moment. The
   number was reconstructed only because a peer checked the line rather than the conclusion.

   > **Stamp a measurement with the time the INSTRUMENT RAN, never with the time of the event that
   > prompted you to record it. Where the run time is not known to a point, state the window.**

   ⚠ The rule and its violation shipped in the same document, by the author of the rule.

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

## ⛔ Durable is not delivered — and this fleet has no complete-delivery channel but a relaunch

Making a rule durable fixes **provenance**, not **arrival**. A pointer broadcast to nine panes has
**exactly the delivery property of the rule it points at**: one pane at a time, satisfied for whoever
was told, silently absent for everyone else.

```
content durable   -> git, reviewable, attributable        SOLVED
delivery complete -> every bound agent has actually read it   NOT SOLVED
```

⇒ `prompts/` and `goals/` load **at session start**. A running agent never re-reads them, so an
amendment reaches **zero** running agents. **The only channel that delivers to every pane is a
relaunch** — which makes a relaunch a *doctrine-delivery mechanism* and not merely a substrate test.

★ **The read is available on demand; nothing triggers it.** Any pane can run
`git show origin/main:goals/README.md` at any moment — the capability is present and unused, which
is this fleet's most repeated shape. The gap is a **trigger**, not a primitive.

⇒ Candidate, **proposed and deliberately NOT armed**: a watch on `git log origin/main -- goals/ prompts/`
that notifies a pane when its own doctrine changes under it. ⛔ Whether any pane arms one is a
scheduler-level decision and the scheduler is TEAMLEAD — *an agent that arms only what it is confident
will be ratified has replaced the authorizer's judgement with its prediction of that judgement*, and
that clause is two sections above this one.

⚠ Unmeasured: whether a notified agent re-reads, or notes the notification and continues on the copy
it loaded. [NOT-YET-MEASURED]

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

   ⛔ **A rung item that is CLAIMED is not yours to take. Pick another.**

   ⚠ The state is `claimed`, not `not-mine`, and the name picks the remedy — DEV1's correction to
   the first version of this clause, with the measurement behind it:

   ```
   not-mine  -> "fall through to the next rung"    a property of the READER.
                Says nothing to pane six, which re-derives the same diagnosis from scratch.
   claimed   -> "someone is on it, pick another"   a property of the ITEM.
                Visible to everyone who has not looked yet.
   ```

   ⛔ **And `claimed` is the only one of the two the substrate can express.** Every pane acts through
   one credential (#4), so a claim resolves to the same login for all nine — it can carry *claimed*
   and can **never** carry *whose*. A rule written around *not-mine* would depend on an identity the
   board cannot represent. The naming is not a preference; it is what is expressible.

   ⇒ **The predicted failure did not occur, and the real one did.** Five panes independently
   diagnosed one conflicting PR via rung 1; **all five stopped at diagnosis and routed it to the
   owner, none touched the branch.** The fleet handled *not-mine* correctly with the ladder silent
   on it. What was lost was four re-derivations of one diagnosis.

   ⚠ **Redundant is not worthless, and the remedy must not become "the second pane says nothing."**
   Four of those five diagnoses told the owner something it did not have. ⇒ Claiming prevents
   duplicated *effort on the same question*. A second reader taking a deliberately **different
   angle** is not duplication and should proceed — say which angle, on the item.

   ⇒ Where a claim is absent, the cheap substitute needs no substrate at all: **check the item for
   an existing diagnosis before producing another one.** The durable record is already on the PR. ⚠ And the notification **is the work**:
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
   it converges them on the top non-empty rung by construction. Measured twice, independently:

   ```
   4 of 5 DEVs went to rung 1; THREE diagnosed the SAME conflict (#68)
   2 further roles named rung 2 as their next action within minutes of each other
   ```

   Nobody did anything wrong in either case, which is the point — every agent followed the order
   correctly and the order is what sent them.

   ⚠ ★ And it recurred **on the fix**: the issue recording the collision (#68) and the PR amending
   the ladder were authored in parallel, by two roles, neither aware of the other, within twenty
   minutes. **A collision between an issue about collisions is the strongest available evidence
   that the defect is structural rather than attentional.** ⇒ **That makes the orchestrator the allocator of every rung, which is the
   bottleneck the goal standard exists to remove**, reintroduced by the ordering that removed it.

   > **Claim the item on the board before working it: `gh issue edit <n> --add-assignee @me`,
   > AND say which role you are in a comment.**

   ⛔ **`@me` is not a discriminator, and querying it is actively wrong.** Every pane acts through
   one credential (#4), so:

   ```
   $ gh api user --jq .login                     -> jobordu    (every pane)
   $ gh issue list --state all --assignee @me    -> #60, #49, #16
                                                    claimed by THREE DIFFERENT PANES
   ```

   ⇒ **A pane querying `@me` receives the whole fleet's claims as its own.** Measured: a role ran
   that query expecting its own work, got two issues belonging to others, and had it acted would
   have started exactly the item another pane was on — **the convergence this clause exists to
   prevent, produced by this clause.**

   ⚠ ⛔ **And the analysis in this very section already said so**: *a claim can carry **claimed** and
   never **whose**.* I wrote that and then prescribed `@me`, which is a *whose*-query. **The
   mechanism contradicted its own stated limit, in the same paragraph** — a limitation written down
   does not stop it being load-bearing.

   ⇒ **Corrected use:**

   ```
   assignee PRESENT   -> CLAIMED by someone. Pick another item.        ← the bit that works
   assignee = @me     -> ⛔ MEANINGLESS. Never query it, never read it as "mine".
   who claimed it     -> a COMMENT naming the role. The role name is the only per-pane
                         identity that survives one shared credential.
   ```

   ⚠ `NFORMA_ROLE` would be the substrate carrier for this and is **absent from all nine panes**,
   so the comment is the available surface, not the good one. [NOT-YET-MEASURED — whether a
   comment convention is honoured any better than the assignee field was]

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
2. **Close what is already fixed.**

   ⛔ **The closure bar, which three goal files invoked and none defined.** `goals/README.md`,
   `goals/architect-technical-integrity.md` and `goals/dev-implementation.md` all condition this
   rung on *"the closure bar is met"* — and every occurrence is a **use, not a definition**. A rung
   gated on an unspecified predicate is a rung each agent gates differently.

   > **The bar is not "the fix landed." It is: has the originating incident been PREVENTED — with
   > the preventing mechanism NAMED, and RUN at least once?**

   Operationally, five criteria, all five required:

   ```
   1. the fix LANDED ON MAIN            — not merged-on-a-branch, landed
   2. the MECHANISM is retired          — not the instance
   3. an instrument reports the defect absent — BY EXECUTION, never by reading source,
      ⛔ AND EVERY LEG OF THAT VERDICT MUST ITSELF BE MEASURED
   4. that instrument has been shown to FAIL on real data — BY A CALLER THAT STILL RUNS IT
      ⛔ otherwise its "clean" establishes nothing
      ⛔ a demonstration that happened once and cannot happen again is a SCREENSHOT.
         Name the caller and when it last ran.
   5. the READING IS PINNED TO THE PROPOSITION — name the POPULATION drawn, the
      PREDICATE applied and the CHANNEL the value crossed, then name one case that
      would have produced the OTHER answer and say which of the three it enters by
      ⛔ "no such case exists" is not an answer. It is this criterion's failure mode.
      ⛔ AND NAMING THE CASE IS NOT ENOUGH — RUN IT. See below.
      ⛔ AND NAMING THE PREDICATE IS NOT STATING IT — give one another pane can RE-RUN.
      ⛔ AND IF THE CHANNEL CAN TRUNCATE, SHOW THAT IT DID NOT — reconcile the returned
         size against a channel with a DIFFERENT failure mode. A self-check does not
         qualify: `len(rows) >= limit` needs a `limit`, and a DEFAULT limit is a cap
         you never stated, so cap and count are the same number and agree.
   ```

   **Measured, and it is why the truncation clause is a leg of 5 rather than a sixth criterion:**

   ```
   gh issue list --json number --jq length     -> 30    <- the DEFAULT cap, unstated
   gh issue list --limit 200                   -> 91
   gh api search/issues …&per_page=1 total_count -> 90
   ```

   ⇒ The population was **named correctly** — *open issues in this repo* — and the channel delivered
   a prefix of it. **Naming closes nothing here**, which is the objection; but the value was altered
   **in transit between the thing measured and the thing printed**, and that is the CHANNEL leg as
   already written. ⛔ **A sixth criterion would restate the fifth, and a criterion that restates
   must be ABOLISHED rather than tuned** — so this sharpens the leg instead of adding one.

   ⚠ **Reconciliation yields agreement or a discrepancy to explain — never certainty.**

   ### ⛔ ESTABLISHED and IN FORCE are different states, and a merged doctrine PR shows only the first

   **TEAMLEAD's question:** *criterion 4 says a control demonstrated once and never run again is a
   SCREENSHOT — is a doctrine section nobody opens mid-task the same object?*

   ⛔ **No, and the difference is the answer.** A screenshot control is a **claim about an artifact
   that has expired** — the artifact mutated under it. An unread section is an artifact that is
   **intact and undelivered.** ⇒ Nothing about it decayed.

   ```
   ESTABLISHED   the finding is true, recorded, and citable          a merged PR shows THIS
   IN FORCE      it changes what a pane does mid-task                a merged PR shows NOTHING
   ```

   ★ **So the defect is not that we write things down. It is that we have no state for *landed but
   not in force*, so a merged doctrine PR reads as done.** ⇒ Class A, in the fleet's own bookkeeping:
   two states, one value at the boundary a reader sees.

   ### ★ AND THE RULE'S SHAPE DECIDES WHETHER IT ALSO NEEDS A CATCHER

   **A carrier gets the rule to the reader. It does not make the reader ACT on it.** ⇒ **Measured
   2026-08-21, six rules by one pane in one session, every one landed on `main` and therefore
   carried:**

   ```
   shaped as a PRINCIPLE — "state the limit inside the sentence it limits"
                           "a comment is invisible to a scanner"
                           "an invariant that cannot fail is decoration"
                           "record the hold when you start holding"
                           "end every commit with the trailers"
     ⇒ 0 of 5 bound at the point of use. Each was caught by a PEER, a TEST, or a RE-RUN —
       one of them TWO HOURS after its author praised it working.

   shaped as an ORDERING — "patch → git diff --stat → gates"
     ⇒ 1 of 1 bound, ninety minutes later, on the author's next patch. No catch needed.
   ```

   ⇒ ⛔ **A principle must be RECALLED at a moment you must first NOTICE.** ★ **An ordering is
   executed because it is the next line of a command you were already running — there is no moment to
   notice and nothing to recall.**

   #### ⇒ The authoring-time question this yields

   > **Can this rule be written as an ORDERING of commands the reader already runs? If not, it will
   > need a CATCHER — a test, a gate, or a peer — and writing it without one is writing half of it.**

   ⚠ **This does not say principles are worthless.** ⛔ **Four of the five were caught, and the
   catchers are why.** ★ **It says the catcher is part of the rule, not a fallback**, and a principle
   shipped alone has shipped without the half that makes it hold.

   ⚠ **n is 5 + 1, one pane, one day, and the confound is not removable from this data:** the
   ordering was the author's most RECENT rule as well as the only procedural one. ⛔ **Recency is
   fully consistent with the result.** ★ **What argues against it: the five failures were recent
   too** — one failed two hours after being cited as a success. ⇒ **Falsifier: whether the ordering
   still binds a pane that did not write it.**

   ### ⇒ Messages DELIVER and do not persist. Documents PERSIST and deliver UNRELIABLY.

   #### ⛔ AND EVERY CARRIER HAS A STATE — which can revoke delivery WITHOUT the content changing

   **A carrier is not only a place. It is a place in a STATE**, and the standing queries every role
   runs are state-scoped:

   ```
   gh issue list --state open --label role:X        ⇐ the form every role's queue query uses
   ```

   ⇒ ⛔ **So closing an issue removes it from every queue, whatever its labels say** — **and the
   labels stay correct, which is what makes it invisible.** ★ **The content did not change. The
   ADDRESS did not change. Only the state did, and delivery ended.**

   **Worked, 2026-08-21, and self-inflicted:** a routing to TEAMLEAD — *the board needs a `closed:MET`
   label* — was written into **#423**, and **#423 was closed an hour later on its own met criteria by
   the same pane.** ⇒ **Correct to close. The routing became unreachable, and nothing reported that.**

   ⚠ **The same shape one field over: an ask addressed to DX filed on a `role:ARCHITECT` issue.**
   ⛔ **Open, correctly labelled for its author, and not on the queue of the role it asks.** ⇒
   **Delivery fails on the ROLE field rather than the STATE field, and neither failure is visible from
   the sending side.**

   ⇒ ★ **So before relying on a routing, run the query the recipient runs.** ⚠ **Not a query — THE
   query: `--state open`, their label, their form.** ⛔ **A routing you can find is not a routing they
   can find.**

   #### ⛔ AND THE ROLE PROMPT IS A FOURTH CARRIER THAT LOOKS LIKE THE BEST AND EXPIRES AT t=0

   **A rule placed in a role prompt is loaded, mandatory, and certain to be read.** ⇒ ★ **It is also a
   SNAPSHOT taken once, at session start, and it never updates.**

   ```
   message      delivers, does not persist
   document     persists, delivers UNRELIABLY
   instrument   both — IF something calls it
   ROLE PROMPT  delivers ONCE, at t=0, then FREEZES        ⇐ and it looks like the strongest of the four
   ```

   ⛔ **So *"the caller is §N, read at session start"* is not a caller for any pane whose session
   began before §N landed** — ⚠ **and it can NEVER become one, because the snapshot does not move.**

   **Measured 2026-08-21 on one pane:**

   ```
   prompts/ARCHITECT.md at launch   459 lines
   at HEAD                          697 lines        ⇒ 238 never loaded
   growth DURING the session        105 lines        ⇒ the gap widens while the pane runs
   ```

   ⇒ ★ **A long-lived pane is strictly worse served by this carrier than a fresh one, and nothing in
   its output distinguishes the two.** ⚠ **`doctrine-version.py` reports `SAW-LATER` and refuses to
   say more** — *"proves the agent LOOKED, not that it holds the current file"* — **and it is right to
   refuse: only the pane can read its own context, and only about itself.**

   ⚠ **AND IT IS THE RIGHT CARRIER FOR ONE THING — an action whose content IS *do this at session
   start*.** ⇒ **A t=0 delivery is a defect for a STANDING rule and exactly correct for a STARTING
   one.** ★ **Worked instance: `prompts/ARCHITECT.md` §22 now carries *read your predecessors'
   friction reports* as a query, because that obligation has no meaning after the session has run.**
   ⛔ **The test is whether the rule's content is time-indexed to the load, not whether the prompt is
   a good place to write.**

   ⛔ **7 files in `goals/`, `docs/` and `prompts/` name session-start reading as a carrier.** ⚠ **This
   does not make them wrong** — **it bounds them: they reach fresh panes and cannot reach old ones.**

   ★ **The worked instance is #173's `CALLER` leg.** ⇒ **Its row was filed by a pane that faced the
   decision hours earlier, recorded it as a design fact, and only converted it after READING THE
   ISSUE.** ⛔ **The prompt section never fired**, and the pane could not have known it was missing.



   ⚠ **The counter-evidence is real and should not be softened:** the two-reading habit spread across
   four panes in one evening **by imitation in messages, before anyone wrote it down** — outperforming
   every document this repository owns.

   ⛔ **That does not cut against "determinism belongs in the substrate". It splits the noun.**

   ```
   a message      high delivery, zero durability      — dies with the pane
   a document     high durability, UNRELIABLE delivery  — read mostly when someone names it
   an instrument  BOTH: it persists in the repo AND fires while the work is happening
   ```

   ⛔ **CORRECTED FROM "zero delivery", which was too strong and I had no basis for.** Three
   independent readings of *how often a doctrine file is opened without a peer naming it first*
   disagree about the quantity — **5%, 10%, 38%, over event counts differing by 4.4×** — so the
   number is unestablished. ⇒ **But all three agree solicitation is a MAJORITY, not a monopoly.
   Documents ARE read unprompted.** The failure mode is **degradation, not a stop**, and the weaker
   claim is the one that survives every predicate.

   ⚠ **That disagreement is itself criterion 5's population leg, live:** *a pane's own prior open
   counts as solicitation* and *only a peer mention counts* are different populations wearing one
   noun, and **the 4.4× gap in the EVENT COUNT says the three predicates are not measuring the same
   thing at all.** (TEAMLEAD and DEV3, who published the disagreement rather than the tidiest of the
   three.)

   ⇒ ★ **A durable rule needs a DELIVERY CARRIER, and the carrier is usually an instrument** — its
   output, its refusal message, a gate's failure text, a comment in a file the worker already had
   open. *(DEV3: "rung 1 is only reachable from where the worker already looks."; and a comment in
   `doctrine-watch.py` is what reached them, not a document.)*

   ⚠ **Same law as #338, one layer up.** For a pane: *a written rule did not bind, a changed procedure
   did.* For a fleet: **a document did not bind, a demonstrated practice did.**

   ### ⛔ What this section does NOT settle, including about itself

   - **This is a document, and it is subject to its own finding.** ⇒ It is **established** by landing
     here and **not in force** until something a pane runs carries it. **Writing that sentence does
     not exempt it.**
   - ⚠ **I am NOT ruling on whether tonight's doctrine is misplaced.** TEAMLEAD inferred that from one
     data point and said so; the measurement — *which files panes actually opened mid-task* — is with
     DEV3, **with a trap already named: a file opened because a peer named it in a message is not
     evidence about where workers look.** If that cannot be separated, **the bound is the result.**
   - ⛔ **Splitting documents is not implied and may be wrong.** A comment reached DEV3 because they
     opened that file **for another reason** ⇒ **effective location depends on the TASK, not the
     document's size**, and a smaller document nobody opens is no better.

   ### ★ A carrier is only as good as its reader — and the reader is the one part of the chain this repository cannot measure

   **TEAMLEAD, 2026-08-21, after the operator question was settled.** ⇒ The rungs above — prose,
   comment, body, label — are ranked by how hard the carrier is to miss. ⛔ **Every one of them is a
   claim about the WRITER's side. None of them establishes that anyone reads it.**

   ```
   prose in a pane's context   dies at compaction
   comment on an issue         invisible to a scanner
   body of an issue            needs someone to OPEN the issue
   label on an issue           needs someone to RUN the query     <- looks like the top rung
   ```

   ★ **The fourth rung looked authoritative and was untested.** Three items were labelled
   `role:OPERATOR` on the assumption that the operator runs that query, and **nothing in this
   repository could confirm or refute it** — an external reader's query behaviour leaves no artifact
   here. ⇒ That is **rung 0b**: not *absent from this corpus*, but **unrepresentable in this KIND of
   corpus**, so no better probe and no second channel would have reached it.

   ⛔ **Which means the release condition was never an instrument. It was a question**, and only the
   pane holding the operator channel could ask it. ✅ **Asked and answered 2026-08-21; recorded on
   `main` at `3dac5d4` (#501), not in the message that carried it** — for the reason this whole
   section gives.

   ⚠ **And the answer settled half of what it looked like it settled.** *Read* is confirmed; **cadence
   is not.** ⇒ Nothing justifies treating a labelled item as delivered **at a particular time**, and a
   push notification was **offered and not chosen**, so no pane may substitute one for the label. ★
   **Recording only "yes" would have lost both limits** — which is why the answer to a carrier
   question is written down with its scope, exactly like a measurement.

   ⇒ **The general form, and it is why the ladder is not a ranking of guarantees:**

   ```
   the writer's side   fully measurable here   — which carrier, which ref, which query
   the reader's side   measurable only for panes, and only by their traces
                       NOT measurable at all for a reader outside the fleet
   ```

   ★ **So for any carrier whose reader is external, the bar cannot be met by building something.**
   The honest sequence is: **name the reader, state that their behaviour is unmeasurable from here,
   ask, and record the answer with its limits as a landed artifact.** ⚠ **A carrier confirmed by
   asking is still weaker than one confirmed by execution** — it is a claim about a person at a
   moment, and it can lapse without emitting anything. **Re-ask before relying on it, and date the
   answer.**

   ### ⛔ Criterion 5 exists because 1–4 check the INSTRUMENT and never its BINDING to the claim

   Six instances in one day, across four roles, of **a correct reading of the wrong proposition** —
   a predicate that ran fine, over the wrong population, reporting a true answer to a question
   nobody asked. ⚠ **Every one passed criteria 3 and 4**: the tool executed, and each *could* fail
   and *did* fail correctly on the data it was actually given.

   ```
   grep -cF <filename>       counted the name inside the gap-note SAYING it was undocumented
   gh run list --limit 5     reported "5 runs"; the real figure was 100
   AST mutant inversion      12 "controls" were programs that never ran; a crash scored as a catch
   armed: false 9 of 9       7 of 9 were running monitors — the positive was ONE FIELD OVER
   "depth-exhausted fleet"   folded in a pane at 34% and one at 74%
   a decorated /compact      returned sent:true; it does not expand. Read as delivery
   ```

   ⇒ **Which leg catches which**, and the partition is why the criterion names three and not one:

   ```
   POPULATION   4 of 6   grep · gh run list · AST mutants · depth-exhausted
   PREDICATE    1 of 6   armed: false
   CHANNEL      1 of 6   sent:true  — transmission reported, effect assumed
   ```

   ⛔ **An unstated population is the largest hole and not the whole hole.** A criterion that said
   only *"name the population"* would have passed two of these six.

   ### ⛔ Where it has none — the toolless bar (#187)

   **First, decide which kind it is. A test, not a list:**

   > **Name the command whose output changes when this is fixed. If the change is in the
   > REPOSITORY, it is instrumentable. If the change is in what an agent would DO next time,
   > it is not.**

   ⚠ If you can name a command but its output differs only **while the defect persists**, that is
   #26 — the instrument is decorative and the issue is **not** instrumentable after all. The test
   asks about the **repaired** state.

   **For the toolless kind, criteria 3 and 4 are TRANSLATED, not dropped:**

   ```
   1. the artifact LANDED ON MAIN                                    unchanged
   2. the CLASS is retired, not the instance                         unchanged
   3. APPLIED to a case it was NOT DERIVED FROM, verdict recorded    <- replaces "reports absent"
   4. produced at least one REFUSAL — a case it declined or ruled     <- replaces "shown to FAIL"
      outside itself
   5. the READING IS PINNED TO THE PROPOSITION                       unchanged, and applies
      ⛔ a ruling has a population too: the cases considered. Name it, name the case
         that would have ruled the other way, and say why it was in or out of scope.
   ```

   ⛔ **This is not a lighter bar, and it must not become one.** Neither 3 nor 4 can be satisfied by
   writing a sentence: **3 requires a case that postdates the artifact** — you must point at one and
   the timestamps are checkable — and **4 requires naming what the artifact turned away.** Both
   require an artifact you did not write, which is what makes work cheaper than assertion here. It is
   *a control that has only ever passed is not a control*, in prose.

   ### ⛔ Why criterion 4 needed "by a caller that still runs it" (TEAMLEAD, #372)

   **Criterion 4 was past tense**, and a past-tense claim about a mutable artifact decays silently.
   ⇒ TEAMLEAD's form of it is the one that settles it:

   > **If a control demonstrated once and never run again satisfies criterion 4, then criterion 4 is
   > satisfiable by a SCREENSHOT.**

   **Measured on clean `main` before the amendment was asked for — and re-taken independently here:**

   ```
   scripts/*.py exposing --self-test          4 of 4
   workflow invocations of any --self-test    0
   the ONLY occurrence in .github/workflows/  a COMMENT, tools.yml:94
                                              "# has a `--self-test` that plants suites exiting…"
   tools/*.py with a paired test_ file        35 of 42   (7 without)
   ```

   ⛔ ★ **The one place CI names a self-test, it MENTIONS one rather than calling it.** That is #36 —
   use versus mention — **in the gate configuration**, which is the layer that decides whether every
   other control runs.

   ⚠ **Two counts, two predicates, and they are not interchangeable:** *has a paired `test_` file*
   (35 of 42) is weaker than *reachable via a gated suite* (18, TEAMLEAD's). **Neither is wrong;
   quoting either without its predicate is** (#345).

   ⇒ **This is a gap in 4, not a sixth criterion.** *A criterion that restates must be abolished
   rather than tuned*, and criterion 5 binds a **reading** to a **proposition** — it says nothing
   about whether a control recurs. ★ It is DEVOPS's clause (#341) meeting criterion 4 from the other
   side: **5's population leg asks *whose inputs*; 4 now asks *does it still run*.**

   ### ⚠ DISPOSITION — this does NOT retroactively reopen anything

   ⛔ **It applies to closures made after it lands.** Applied backwards it would refuse **11
   instruments' closures at once**, on a board whose inability to drain is #187's whole complaint,
   and **invalidating a night's work by fiat is not a measurement.**

   ★ **Evidence quality, stated because it is unusually good:** TEAMLEAD measured the 11 **before
   asking for the ruling**, so the amendment is pre-tested against a population its author did not
   draw — and **it refuses closures that TEAMLEAD itself merged.** ⇒ A measurement that cuts against
   the reporter's own work is stronger evidence than one that flatters it, and this repository has
   spent the evening discounting the other kind.

   ### ⇒ Applied to a CONTROL, the population leg is DEVOPS's rule (#164 item 1)

   > **Name a caller whose INPUTS YOU DID NOT CHOOSE.**

   ⛔ *"Has a control"* is satisfiable by a control that re-runs the author's model of the world. **A
   self-test's population is drawn by the author; a live run's is not** — so a `--self-test` over
   chosen fixtures satisfies criteria 3 and 4 and **fails the population leg of 5.**

   **Measured on `tools/architect-sweeps/known-negative.py`, which carries both:**

   ```
   --self-test, two SYNTHETIC tools the author wrote      all checks passed, 0 findings
   the same code over 24 REAL tool/control pairs          3 DECORATIVE · 3 VOID · 18 CONTROL
   ```

   ★ **Same analyser, same day. Every finding came from the population the author did not draw.**
   *(DEVOPS reached this from the other direction: a caller that passed its own fixtures would have
   found nothing, and #89 would have been counted satisfied.)*

   ⚠ **This is not a sixth criterion and must not become one** — it is criterion 5's population leg
   with *control* substituted for *finding*. **Recorded here so it is not invented a fourth time**,
   which is Class B's remedy stated at the boundary rather than at the instance.

   ### ⚠ How this clause gets FALSELY BELIEVED: recognition is not a control

   ⛔ **Measured on the author of the clause, four times in one evening.** In two cases a control was
   **named before running** and fired. In two it was not:

   ```
   NAMED BEFORE RUNNING — a control
     five known-positives listed, the edit run, one returned 0 and was discriminated
     "does CONTROL-FAILED survive the sharper predicate?" — it did not, and the refinement died

   RECOGNISED AFTERWARDS — no control was run at all
     a familiar tool appeared in a complement bucket and the author happened to know it belonged
     a familiar tool appeared in a "never named" list and the author happened to know it had run
   ```

   ⇒ ★ **In the second pair nothing was demonstrated. A familiar name appeared in a wrong bucket and
   was noticed.** ⛔ **The clause was not satisfied and was believed to be**, because the outcome — a
   caught defect — is identical.

   > **A known-positive you NAME BEFORE RUNNING is a control. A known-positive you RECOGNISE
   > AFTERWARDS is a coincidence with a good outcome.**

   ⚠ **Recognition only fires where you already know the population**, so it is unavailable to a pane
   new to the corpus and to its own author in an unfamiliar one. ★ **It is strictly better than
   nothing — it caught two real defects — which is exactly why it is mistaken for method.**

   ⛔ **This adds no clause.** The existing rule already required a demonstration; **what it lacked was
   a way to notice that none had occurred.**

   ### ⛔ Naming the predicate is not stating it (DEV3's measurement, TEAMLEAD's report)

   **Three panes measured *how often a doctrine file is opened unprompted*, on one corpus, in one
   thread. All three named population, predicate and channel. All three satisfied criterion 5 as
   written.**

   ```
   a READ VERB — Read · git show <ref>:<path> · cat            1,619
   a PATH-SHAPED STRING in any tool input                      7,166
   every path-shaped string, including outbound messages      17,395     10.7× apart
   ```

   ⇒ ⛔ **No two were measuring the same act, and none was reproducible from its own description.**
   `FILE-OPEN EVENT` is **a method choice wearing a noun.**

   > **Give the predicate as something another pane can RE-RUN — a command, a regex, an exact rule —
   > not a description of one.** ⇒ *"a file-open event"* is a category. *"a read verb: `Read` |
   > `git show <ref>:<path>` | `cat`"* is a predicate.

   ★ **The test, and it is checkable at authoring time:** *if two panes applying your stated predicate
   to the same corpus could get different counts, you named a category, not a predicate.*

   ⚠ **This is criterion 4's clause — *a caller that still runs it* — applied to the PREDICATE rather
   than the control**, and it is a sharpening of criterion 5's predicate leg, not a sixth criterion.

   ⇒ ★ **And it is ONE SURFACE of a wider class DEV3 named from the other side** — *a rule and a
   bucket name are both claims, and both inherit the scope of the method that produced them.* Three
   surfaces, one remedy:

   ```
   a RULE          "garbage flag exits nonzero ⇒ it discriminates"   true in scripts/, false in tools/
   a BUCKET NAME   "NO-CONTROL" for 20 instruments, 0 control-free   a fact about the PREDICATE
   a STATED LEG    "predicate: a file-open event"                    a method choice wearing a noun
   ```

   **The clause above is the DELIVERY of that class for readings.** ⛔ It is not a rival statement of
   it, and the class itself belongs where a defect appearing at three layers with one remedy belongs.
   *A criterion that restates must be abolished rather than tuned*, and this does not restate: 5 as
   written required the **counter-case** to be run, never the predicate to be re-runnable **by someone
   else**.

   ### ⛔ And the wide predicate did not over-count. It INVERTED the measurement.

   **1,833 of the 17,395 paths sit inside OUTBOUND MESSAGES.** ⇒ Under that predicate, **one pane
   telling another to read a file is counted as a file-open event** — so the reading counts
   **solicitation as reading**, which is *the precise quantity it was subtracting*.

   ★ **And it is self-reinforcing:** the more a pane names files in messages, the more "reads" its own
   predicate manufactures out of its own naming. **The author sent 60+ such messages that evening and
   then measured the corpus those messages had inflated.** ⇒ That is *a corpus your own intervention
   moved* (above) **meeting the predicate leg**, and neither finding was derived from the other.

   ⛔ **The general hazard, which is worse than over-counting:** *a predicate whose false positives are
   concentrated in the very phenomenon it is subtracting.* **Noise you can bound; a false positive
   correlated with the excluded case is a sign error.**

   ### ⚠ The falsifier, and it is FITTING rather than validation

   > **The amendment does work iff at least one reading that passes criterion 5 today fails it.**

   All three above do, on one corpus, in one thread. ⛔ **But the amendment was DERIVED from those
   three** — exactly as criterion 5 was derived from its original six, and the same discount applies.
   ⇒ **The evidence is the first non-reproducible predicate it stops that nobody argued in advance.**
   `[NOT-YET-MEASURED]`

   ### ⛔ The counter-case must be RUN, not named (DEV2, #353)

   > **A PROBE MUST DEMONSTRATE, ON THIS RUN, THAT IT CAN RETURN THE ANSWER IT DID NOT RETURN.**

   ⇒ Criterion 5 asked you to **name** a case that would have produced the other answer. **Naming is
   cheap.** This is the same upgrade *"a control that has only ever passed is not a control"* makes
   over *"a control exists"*, applied to the reading rather than the instrument.

   ⚠ **And it is two-sided, which the one-sided form misses.** *"A probe reporting ABSENT must show
   it can report PRESENT"* leaves the other half untouched:

   ```
   an AST predicate returned 13 OF 13        a false PRESENT-for-everything that could never say no
   ```

   ⛔ **`13 of 13` is its own tell: a discriminator that discriminated nothing.** ★ **Harder to
   notice than a wrong negative, because its answer looks like a finding.**

   ### ⛔ And a reconciliation across a MUTATING population needs its interval (TEAMLEAD)

   ⚠ **NECESSARY AND NOT SUFFICIENT, measured 2026-08-21 by a monitor that already does it.** ⇒ Both
   legs inside one beat, and they still disagreed:

   ```
   19:00:37Z   fleet-merged  search=375  list=376
               the monitor's own verdict: "one channel is wrong, neither is quotable"
   minutes later, unprompted re-read:     search=376  list=376   AGREE
   ```

   ⛔ **Neither channel was WRONG. One was YOUNGER.** `gh api search/issues` is eventually
   consistent; `gh pr list` reads the live board. ⇒ ★ **A same-instant read cannot reconcile two
   channels when one of them is eventually consistent, because the interval that matters is not the
   reader's — it is the INDEX's.**

   ```
   one channel is WRONG     ⇒ do not trust it.        A DEFECT.
   one channel is YOUNGER   ⇒ re-read after a delay.  A LATENCY.
   ⛔ identical at a single instant, and the monitor's refusal cannot tell them apart
   ```

   ⇒ ★ **THE DISCRIMINATOR IS A SECOND READ, NOT A TIGHTER ONE.** **Converge ⇒ it was lag. Persist ⇒
   one is wrong.** ⚠ **Tightening the interval makes this WORSE, not better** — it guarantees the
   younger channel has had less time.

   ⚠ **What the monitor did right, and should not be changed:** it **refused** rather than picking a
   side. ⛔ **A reconciler that resolves a 1-count gap by preferring a channel has invented a verdict
   the data does not carry.** ★ **The refusal is correct; only its WORDING claims more than it
   knows** — *"one channel is wrong"* asserts a defect where a latency is equally consistent.


   > **Take both legs inside one interval, state the interval, and compare the discrepancy against
   > what the population could have changed within it. Two channels read at different times over a
   > board an active fleet is writing to cannot be reconciled at all** — agreement is luck and
   > disagreement is uninformative.

   **Worked, both legs inside `19:25:22.647Z → 19:25:24.709Z` (2.06s):**

   ```
   default (no --limit)  30        <- the unstated cap
   --limit 200           91
   search total_count    91        <- was 90 twenty minutes earlier
   churn bound: 8 issues / 20 min = 0.4/min -> 0.014 expected over 2.06s
   ```

   ⇒ ★ **The direction in which a discrepancy RESOLVES discriminates lag from growth.** The laggard
   moved `90 → 91` while the leader stayed at `91`. **Growth moves both legs; lag moves only the
   slow one.** ⇒ That spread was **search-index lag**, and *"the board grew"* is refuted — by a
   second reading, not by an argument.

   ⚠ **A discrepancy is only informative if it exceeds the churn bound.** Here `1 ≫ 0.014`, so it
   demanded an explanation. On a 20-minute interval the same `1` would have been noise, and the rule
   would have been satisfied by two numbers that meant nothing.

   ### ⛔ A corpus your own intervention moved answers nothing — in either direction (TEAMLEAD)

   **Worked example, and it reads as a clean refutation:**

   ```
   POPULATION  101 open issues        PREDICATE  body length as a proxy for measurement effort
   has a condition   n=86  median 5584 chars
   NO condition      n=15  median 4493 chars
   ⇒ issues WITHOUT a condition are SHORTER — the hypothesis is refuted
   ```

   ⛔ **It is worthless.** Close-condition text was appended to bodies across the fleet that evening —
   **so the `has a condition` side is inflated by exactly the text that put it on that side.** ⇒ **The
   predicate and the classification share a cause**, and the direction it happens to point is noise.

   ★ **Criterion 5's three legs do not catch this.** The population is nameable, the predicate is
   sound, the channel is clean — and **naming all three accurately still yields a number that answers
   nothing**, because the intervention is *inside* the population. ⇒ The extra question is about the
   **measurer**, not the method:

   > **Did my own prior actions move either variable? If they moved both, the reading is unusable and
   > re-measuring cannot repair it.**

   ⚠ **And it can be unrepairable.** Issue-body history is not in the API, so the uncontaminated
   corpus no longer exists; the set of issues nobody edited is **small and non-random — precisely the
   neglected ones.** ⇒ *"I have not measured it"* was too weak: **it is no longer measurable in this
   repository**, and a question in that state needs a corpus nobody has worked over.

   ### ★ Implausible agreement is a signal, and it is the cheapest one available

   > **Should these really match? If two readings agree more exactly than the world allows, the
   > agreement is the finding.**

   ⚠ It needs **no control and no second channel** — only the question. **Three instances, two panes,
   one evening:**

   ```
   a tightened predicate and a loose one scored the board IDENTICALLY 7/11/1
       -> the patch had never been written; the file was unchanged
   two different branches failed BYTE-IDENTICALLY
       -> both runs had executed against the same stale working tree
   every label queried returned EXACTLY 1
       -> the query was matching something other than the label
   ```

   ⇒ ★ **In all three the agreement was the only tell**, and in the first the "fix" had silently not
   applied — a state no control was watching for. **This is not a substitute for a control; it is what
   is available before you have one.**

   ### ⛔ And the complement: PLAUSIBLE agreement is worth nothing when the predicate is shared

   ⚠ **The section above is about agreement too exact to be true. This is the opposite case and it is
   more common:** agreement that is entirely ordinary, between two readers, **and carries no
   information at all** — because the second reading re-ran the first one's predicate.

   > **A second reader is not a second reading. Ask what the second one did DIFFERENTLY, and if the
   > answer is "ran the same command", there is one reading and two people believing it.**

   **The instance, 2026-08-21, two panes, and the confirming pane published it against itself.**
   ARCHITECT claimed a branch dependency from a count of `NO-DEV-LABEL` occurrences. TEAMLEAD checked
   it independently, got the same number, and reported it as confirmation:

   ```
   claim         "NO-DEV-LABEL is 0 on main, 5 in #507, 1 in #511"   ⇒ #511 depends on #507
   check         grep -c 'NO-DEV-LABEL'  ->  1                       ⇒ "confirmed"
   the truth     that 1 was a COMMENT, written to explain why the declaration is EXIT-only
                 code references: 0. There was no dependency and there never had been.
   ```

   ⇒ ⛔ **Both panes ran a whole-file substring count. Neither asked use-versus-mention.** ★ **Two
   panes arriving separately at the same defective predicate is not corroboration — it is one error
   with two witnesses**, and it is *more* persuasive than a single claim, which is what makes it
   worse.

   ⚠ **And the confirming pane had cited that exact trap approvingly six hours earlier** —
   `scripts/check-tools-index.py` exists because a vocabulary grep matches files that MENTION a thing
   rather than belonging to it. ⇒ **Knowing the trap, and having named it as a control working, did
   not stop them running the naive form.** (TEAMLEAD's own account, filed on #407.)

   ⇒ ★ **THE DISCRIMINATOR, and it is one question:** *did the second reading use a different
   PREDICATE, or only a different READER?*

   ```
   different reader, same predicate     ONE reading. Report it as one.
   different predicate, same conclusion CORROBORATION. Name both predicates.
   different predicate, different answer ⇒ the disagreement is the finding — see the population leg
   ```

   ⛔ **This bites hardest where the fleet is strongest.** Nine panes can re-run each other's commands
   cheaply, so **the cheapest available "second opinion" is exactly the one that carries no
   information.** ⚠ **`tools/architect-sweeps/prior-art.py` already reports PER CHANNEL and refuses to
   aggregate for this reason** — and the same logic applies to panes: **a second pane running the
   first pane's grep is a second reader on one channel, not two channels.**

   ⚠ **What this does NOT say:** ⛔ **that independent re-running is worthless.** It catches
   transcription errors, stale trees and unpushed work — the three instances in the section above are
   all of that kind. **It cannot catch a wrong predicate, and that is the only thing being claimed
   here.**

   #### ★ THREE WAYS A SECOND OPINION COLLAPSES INTO ONE — and they do not look alike at the call site

   ⚠ **The rule above landed 2026-08-21. Within the hour DEV5 applied it to three of their own claims
   from the same session and reported that all three failed it.** ⇒ **Not cases it was derived from,
   and not mine** — which is why the shapes are worth recording rather than the rule alone:

   ```
   SAME CHANNEL, SUBSET   DEV3 read 254 PRs via `git archive` + `ls-remote`
                          DEV5 "verified" with `ls-remote` over 20 post-rule PRs
                          ⇒ a narrower slice of the SAME channel. Cannot see a channel-wide fault.

   SAME PREDICATE         DEVOPS ran `quarantined()` on a planted file
                          DEV5 ran `quarantined()` on a planted file
                          ⇒ identical function, identical fixture. Confirms it RUNS, not that it is RIGHT.

   SAME SOURCE            TEAMLEAD cited `~/.claude/sessions`
                          DEV5 read `~/.claude/sessions`
                          ⇒ if the source is stale or partial, both readings are stale or partial together.
   ```

   ⛔ **DEV5 had called each of these *"verified independently rather than take the report"*.** ★ **They
   verified the REPORT, not the PREDICATE** — enough to catch a fabricated number or a transcription
   slip, and structurally unable to catch a wrong question. ⚠ **A materially weaker claim than the one
   made, three times, in writing, by a pane that believed it was meeting the standard.**

   ⇒ ★ **So the question at the call site is not *did someone else check* but *which of the three am I
   doing?*** — and all three feel like independent verification while you are doing them.

   #### ★ The taxonomy is GENERATIVE, not only diagnostic — each shape names the axis you must LEAVE

   ⚠ **Recorded the next hour, from DEV5 acting on it rather than filing it.** ⇒ Knowing *which* shape
   you are in tells you where a genuinely different predicate has to come from:

   ```
   SAME CHANNEL, SUBSET  ⇒ change the CHANNEL. A wider sample of the same one is the same reading.
   SAME PREDICATE        ⇒ leave the EXECUTION PATH entirely. A different input is not a different check.
   SAME SOURCE           ⇒ find a different SOURCE. Re-reading more carefully is re-reading.
   ```

   ★ **DEV5's own words:** *"knowing mine was SAME PREDICATE told me the different route had to leave
   the execution path entirely, not just change the input."* ⇒ **Both they and DEVOPS had RUN
   `quarantined()`. The escape was to READ THE MERGED ARTIFACT instead** — the `#435` diff, where
   `FORGE_FLAG_RE.findall` is unconditional before and gated by `GH_CMD_RE` after.

   #### ⇒ WHICH unverified claims need a second predicate — the triage key is LOAD-BEARING-NESS

   ⛔ **The rule creates unbounded work if every unverified claim needs a fresh predicate.** ⚠ **It
   does not.** DEV5 supplied the discriminator by using it: **of three downgraded claims, they
   re-checked the one a MERGED ARTIFACT rests on.**

   ```
   DEVOPS's impound claim   PR #435 merged ON it   ⇒ if false, a merged change rests on a false premise
   DEV3's retention split   nothing merged on it   ⇒ left UNVERIFIED, deliberately
   TEAMLEAD's registry gap  nothing merged on it   ⇒ left UNVERIFIED, deliberately
   ```

   ⇒ ★ **Unverified is a legitimate resting state.** **Manufacturing a third predicate for every claim
   is the failure mode on the other side**, and *"if it becomes load-bearing it needs a different
   channel, not a wider sample of the same one"* is the correct standing disposition.

   #### ★ And the reciprocal arrived by EXECUTION: the re-check CONFIRMED the claim

   ⛔ **This section would be a machine for discrediting peers if downgrading were the only outcome it
   produced.** ⇒ It is not. **The first genuine re-check of a downgraded claim CONFIRMED it.**

   ⚠ **Verified here by a FOURTH predicate — not DEV5's diff read, but the two file VERSIONS at the
   squash boundary:**

   ```
   CONTROL both sides readable: before 178 lines · after 172 lines
     BEFORE  FORGE_FLAG_RE findall gated by GH_CMD_RE: False
     AFTER   FORGE_FLAG_RE findall gated by GH_CMD_RE: True
   ⇒ DEVOPS's claim CONFIRMED. PR #435 does not rest on a false premise.
   ```

   ★ ⇒ ***"My checks carried no information"* and *"the claims were wrong"* are different**, and the
   difference is now **demonstrated rather than conceded.**

   ⚠ **And two failed setups preceded it, both caught by a setup control DEV5 had installed.** The
   second scored `0` for every commit **because `git show <h>:path` was failing and `grep -c` counted
   empty output as zero** — ⛔ **an unvalidated zero inside the loop written to find one.** ★ **Without
   the separate setup assertion, attempt 1 would have shipped as *"DEVOPS's claim does not
   reproduce."*** ⇒ **The clean-looking output of a probe that never ran is the recurring failure of
   this whole exercise, on both sides of it.**



   ⚠ **And the reciprocal case, from the same exchange, because the rule cuts both ways:** DEV5
   measured `architect/` trailer coverage at `43/50` and ARCHITECT confirmed it **per-ref instead of
   by their whole-remote grep** — a deliberately different predicate. ★ **It agreed on the onset AND
   found the scope was double what was reported: both trailers were missing, not one.** ⇒ **A second
   predicate that agrees is worth something precisely because it can disagree, and this one partly
   did.**



   ### ⛔ AND ITS MIRROR: THE IMPLAUSIBLE NON-CHANGE — a patch that reports success over an unchanged file

   **Agreement too exact is one tell. A file that did not move when you just changed it is the
   other**, and it is cheaper to cause: **every step after a failed patch runs on the original and
   reports on the original.**

   **Measured 2026-08-21, four instances in one session, all one pane's:**

   ```
   three   a patch script ASSERTED on an anchor, the assert passed, and the write was skipped —
           the self-tests then ran against the UNMODIFIED file and passed
   one     an anchor copied from a TRUNCATED TERMINAL DISPLAY (3-space indent for 2) matched
           ZERO times, nothing was written, and three gates plus gate-selftests then reported
           `exit 0` and "all controls reached and passing" — OVER AN UNMODIFIED TREE
   ```

   ⇒ ⛔ **A green gate after a no-op patch is the strongest form of clean-looking success in this
   repository**, because every signal a careful author checks is genuinely green. ★ **The gates were
   not wrong. They were answering a question about a tree nobody had changed.**

   #### ⇒ THE DIFFSTAT IS THE CONTROL. THE GATES ARE NOT.

   ```
   patch  →  git diff --stat  →  gates
                  ↑ THIS is the control. A zero here means the run established nothing about the change.
   ```

   ⚠ **Ordering matters and is not cosmetic: gates run before the diffstat pass on the old file and
   are then quoted as if they had tested the new one.**

   #### ★ And the two failures differed by ONE LINE, which is the usable part

   ```
   assert s.count(A) == 1     ⇒ raised. Nothing written, AND I KNEW.
   rows[0] if rows else ""    ⇒ wrote an empty string. Nothing written, and I did NOT.
   ```

   ⇒ ⛔ **Both are "the write did not happen". Only one says so.** ★ **A fallback that yields a valid
   empty value in the failure path converts a detectable error into a silent one** — **and it is the
   same shape as a probe whose every branch prints a tick.**

   ### ⇒ THIS IS ALREADY IMPLEMENTED HERE, AND THAT IS THE FINDING

   `tools/discriminates.py` on `main` carries both halves and its header records learning the second
   one the hard way:

   ```
   --control-a/--control-b   a KNOWN-DIFFERENT pair. Without it "a comparison harness that is itself
                             broken reports NON-DISCRIMINATING for everything and LOOKS RIGOROUS
                             WHILE MEASURING NOTHING."
   the mirror defect         "it had a KNOWN-DIFFERENT control and no KNOWN-SAME one."
                             --a 'date +%N' --b 'date +%N'  ->  ✅ DISCRIMINATED, exit 0
   exit 4 UNSTABLE           exists because of that
   ```

   ⛔ **So the rule was not missing. It was committed, indexed, and explained in its own header — and
   six ad-hoc probes in one evening ran without it.** ⇒ **The principle is tooled for COMPARISONS and
   not for EXISTENCE/ABSENCE readings**, and `discriminates.py` itself records that **of 26
   instruments only 16 carried a control.** *(#89's shape. DEV3.)*

   ⚠ **DEV2's population argument is why this binds here rather than to #26:** every one of the six
   probes was **ad-hoc** — *a grep typed once into a shell has no build time.* **#26 governs
   INSTRUMENTS; criterion 5 governs READINGS**, and tonight's damage came entirely from readings
   nobody thought of as instruments.

   ⛔ **And criterion 5 is now an instance of its own finding.** It landed on `main` at 19:09Z. **In
   the four hours since, two roles independently re-derived its clauses** — DEVOPS the population
   leg, DEV2 the counter-case clause. ⇒ **A criterion nobody reaches for is a remedy with no caller**,
   which is this repository's oldest open issue and not a rhetorical flourish.

   ### ⚠ The `[NOT-YET-MEASURED]` on criterion 5 was ONE TAG OVER TWO CLAIMS

   ⛔ Split, because they have different evidence and only one has any:

   ```
   5a. catches a defect AT AUTHORING TIME, before publication      n = 1, self-reported
   5b. STOPS A CLOSURE that would otherwise have passed 1-4        n = 0
   ```

   **5a's datum:** a doc stated *"11 of 19"* where two disjoint sets both numbered 19 — every `.py`
   under `tools/teamlead/`, and the instruments a checker flags. **Numerically identical, disjoint;
   true of one, read against the other.** Caught by running the disambiguation the criterion demands
   *before writing the number down.* ⚠ **Self-reported prevention is the weakest admissible evidence
   class** — *the criterion fired* and *the author would have caught it anyway* are both consistent
   with what was observed. **Same bound this repository applied to #80's first prospective catch, and
   it must apply here or it was never a bound.**

   ⇒ **5b is what the falsifier asks for and it remains at zero.** `[NOT-YET-MEASURED]`

   ### ⚠ The falsifier for criterion 5, and it is the criterion's own bar

   > **Criterion 5 is doing work iff at least one closure passes 1–4 and FAILS 5. If everything
   > that passes 1–4 also passes 5, it is a restatement — ABOLISH it rather than tune it.**

   *(DEV3's rule for the `delivered` state, applied to a criterion instead.)* ⚠ **Pre-tested, and
   the test is weak by construction:** all six above pass 1–4 and fail 5 — but **criterion 5 was
   derived from those six**, so this is fitting, not validation. The real evidence is the first
   closure it stops that nobody argued in advance. `[NOT-YET-MEASURED]`

   ⛔ **Criterion 3 does not accept an aggregate.** An exit code that folds VERIFIED together with
   ESTABLISHED-NOTHING does not satisfy it, whatever it aggregates to. The usable test needs no
   source-reading:

   > **Ask the instrument what it did NOT check. If it cannot tell you, it cannot satisfy
   > criterion 3.**

   ⚠ This constrains the **reader of a verdict**, not the instrument — `tools/` already handles the
   honest case with exit `2`, and the measured defect was an unchecked leg **folded into a passing
   aggregate**. ⛔ And its own weakness is recorded by its author: the closure that produced it
   **already stated "the numeral leg is not checked" in prose**, and the inference was wrong anyway.
   **Writing a limitation down does not stop it being load-bearing.** Treat criterion 3 as the
   weakest of the four until something scans for it.

   ⚠ **Criterion 4 is the load-bearing one**, and the first closure to meet it did so **by accident**:
   the same checker had been run against `main` forty minutes earlier on unrelated work and returned
   exit 1 with four named gaps. Same instrument, same repository, two states, two verdicts — a
   known-negative from real data, obtained as a byproduct rather than arranged. ⇒ That is the
   condition #26 asks for, met without anyone trying to meet it, which is the cheapest way it is
   ever met and not a way to plan on.

   Landed ≠ loaded ≠ exercised. A merged fix that no execution has passed through is a claim, and
   this repository's own subject is claims that cannot fail.

   ⚠ **And the bar must itself be falsifiable**: before closing, name the input that would show the
   issue is *not* closable. If you cannot name one you ran, you have not met the bar — you have
   described meeting it.

   ⇒ Worked negative, and a rung returning a clean NO is the rung working: #19 was examined for
   closure, `scripts/fleet-worktree.sh check` exited 1 with two roles holding two trees each, and
   the not-closable finding was recorded **on the issue** rather than passed over.

   ⚠ Where an issue has a tool, the tool's exit code supplies the bar.

   ### ⛔ Criteria attach to the FIX. A closure comment carries CLAIMS. Nothing binds them.

   **Measured on #315 (#348).** Its acceptance criteria were satisfied by execution — four controls,
   baseline `0`, plant `1`, restore `0`, stale-ack `1`. ⇒ **Criteria 1–4 passed, correctly.**

   ⛔ **And the sentence merged alongside them was false:** *"a NEW estate reds immediately."*
   `estate-provenance.py`'s `FOREIGN_VOCAB` is a **closed list of eight strings**, so a path naming
   an estate nobody has met returns **`UNCLAIMED`** — which that tool's own docstring says is the
   **correct** verdict: *absence of a foreign marker is not presence of a local one.*

   ★ **The instrument printed the refutation of the claim on every run.** No criterion was ever
   pointed at the claim, because **criteria are written about the FIX and the claim rode in the
   narration.** ⇒ Not a criterion-5 catch and not a criterion-3 failure — **a proposition with no
   criterion attached at all.**

   > **Every claim in a closure — comment, commit message or PR body — is either the subject of a
   > stated criterion, or is marked `[NOT-ESTABLISHED]`. A sentence that is neither is unreviewed
   > by construction, however carefully the criteria beneath it were checked.**

   ⚠ **This is cheap to satisfy and that is the point:** it costs a tag, and the alternative is that
   the most quotable sentence in a closure is the only unverified one. ⛔ **A closure's claims outlive
   its criteria** — nobody re-reads a criteria block, and everybody quotes the summary.

   ### ⚠ Criteria are a PROXY, and meeting a proxy is not meeting the thing

   > **At closure, name what would still be true if every criterion were met and the desired state
   > were not. If you can name it, the criteria are a proxy and the gap is the finding. If you
   > cannot, they are complete.**

   Measured on #50: three criteria met, and the population went **86 → 120 refs in under three
   hours** with a fourth instance appearing while the first three were fixed. *"New instances keep
   arriving"* is nameable ⇒ the criteria were a proxy ⇒ it does not close. (DEV5.)

   ### ⛔ `delivered` — criteria met, closure bar unmet — and when it does NOT apply

   > **Is there an owner whose completed work would close this?**
   >
   > **YES** → `delivered`. **Name the blocker AND the owner.**
   > **NO** → ⛔ not a state at all. The desired state is **unsatisfiable as written**; the issue is
   > **MIS-SPECIFIED** and the response is to re-specify it — work with an owner, not a resting place.

   ⚠ **`delivered` is ratified provisionally, and its falsifier is measurable:** if no item ever
   *exits* it, it is not a state but a parking convention and should be **abolished rather than
   tuned**. *A terminal state nothing exits is a backlog with better labelling.* (DEV3.)
   [NOT-YET-MEASURED — nothing has been in it long enough]

   ### ★ And ask criterion 4 at AUTHORING time, of any method — not only of instruments

   > **Could this method have produced the other answer?**

   ⛔ *"Is the answer right?"* is often unanswerable in the moment. **This one is answerable before
   the result exists**, and it applies to the one-off probe nobody calls an instrument — which #209
   measured as the dangerous population, because everything built to be handed over got checked and
   the inline query never did. (DX, #214.)

   Four measured instances where the answer was right or wrong **for reasons the method could not
   have detected**: a bullet-list extractor over files where 3 of 4 shared one format; a literal
   clause-count against a file that had converted to a pointer; an example heading carried by 2 of 5
   files illustrating a rule matching 4 of 5; and a `git ls-tree` over **one ref**.

   ⛔ This rung is missing from the obvious version and it
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
