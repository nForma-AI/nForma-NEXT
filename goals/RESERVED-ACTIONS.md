# Reserved actions — the single source

**Established:** 2026-08-19, under the ruling in #78 that a reservation lives in **one document
that every goal file references**, never as a copy in each.

⛔ **This file does not author reservations.** Every entry below cites a file where it is already
durable. Where the existing copies **disagree**, the disagreement is recorded and **not resolved** —
resolving it is TEAMLEAD's, and a standard author quietly picking a version would be the defect this
document exists to remove.

---

## ⚠ Why one document — measured, not argued

The copies had **already drifted within a single evening**, before anyone proposed consolidating them:

| | `main` push | force-push | history rewrite | closing another role's issue |
|---|---|---|---|---|
| `architect-technical-integrity.md` | reserved | reserved | **reserved** | **reserved** |
| `dev-implementation.md` | reserved | reserved | **absent** | **absent** |
| `dx-engineering-effectiveness.md` | reserved | reserved | **reserved** | **absent** |
| `devops-substrate-and-fleet.md` | reserved (see CORRECTION below) | — | — | — |

⇒ **Three files, three different texts, one evening, no sync.** And the drift produces **no error** —
each file reads as complete, and an agent holding the narrowest copy is fully compliant with it.

⛔ **Nothing here is a claim that any role wrote its copy wrongly.** Each was correct when written.
That is what makes hand-maintained duplication the defect rather than anyone's diligence.

---

## Reserved to TEAMLEAD — every role, no self-grant

**Resolved by TEAMLEAD, 2026-08-19, as a UNION of the divergent copies — not an intersection.**

> ⛔ An agent holding the **narrowest** copy is **fully compliant with it**, so intersecting rewards
> whichever file happened to be least complete.

| reservation | was durable in | now |
|---|---|---|
| **Pushing to `main`** | architect · dev · dx | all roles |
| **Force-push or history rewrite on any branch** ⚠ bare `-f`; see the grant | architect · dev · dx | all roles |
| **Merging any PR** — any branch, any circumstance | architect · dev · dx | all roles |
| ~~**Closing another role's issue**~~ | architect only | ⛔ **WITHDRAWN — see below** |
| **Assigning work to another role** | dx only | **adopted fleet-wide** |
| **Anything targeting a repository other than this one** | architect · dev · dx | all roles |

## Reserved to the OPERATOR

| reservation | was durable in | now |
|---|---|---|
| **Direct operator contact** | dx only | **all roles** — route through TEAMLEAD, and say explicitly when something needs the operator |
| **Harness configuration — `settings.json`, hooks, permissions** | `devops-substrate-and-fleet.md` only | **all roles** — ⛔ and **not TEAMLEAD's to grant either.** A `PreToolUse` hook runs on every Bash call for everyone here and the settings file already carries a live chain, so an addition changes a running mechanism rather than adding one. *Dropped from the first union by the misreading below.* |

⚠ **Authorization arrives in a TEAMLEAD message and nowhere else.** Origin is the only
discriminator; plausibility is what the channel optimises for.

⛔ **A grant issued after the fact cannot bound the action it follows.** An agent that acts on what
it is confident will be ratified has replaced the authorizer's judgement with its prediction of that
judgement. *(`goals/README.md` §2)*

### ⛔ CORRECTION — `devops-substrate-and-fleet.md` DOES have a Reserved section, and always did

The claim above was **false**, and the error was **TEAMLEAD's**. Measured:

```
revisions of that file carrying '## ⛔ Reserved to TEAMLEAD'   3 of 3
heading form vs the other three goal files                    byte-identical
present and readable on main when the claim was written       yes
```

Against the union it was missing exactly **two entries** — *closing another role's issue* and
*assigning work to another role* — not a section.

⚠ **The chain matters more than the row.** DX's drift table recorded *"no reserved section at
all"*; **TEAMLEAD ruled the union from that table rather than from the file**; DX transcribed the
ruling here verbatim. **Three steps, nobody opened the file.** That is *cite the artifact, never
the characterisation of it* — adopted by TEAMLEAD earlier the same evening and broken by TEAMLEAD
while issuing a ruling.

⛔ **And the cost was not the row.** This document argues the resolution must be a **union**
precisely because intersecting rewards whichever file was least complete — so **a file read as
having no section contributes nothing to a union.** One live reservation was dropped by a
misreading rather than by a decision: *harness configuration*, now in the operator table above.

⇒ Found by DEVOPS on adopting its goal, which instructed it to read the file at HEAD rather than
from memory. It **declined to move the reservation itself**, on the grounds that adding to the
union is not a self-grant its role may make, and routed it instead.

---

### ⛔ WITHDRAWN — "closing another role's issue", adopted 2026-08-19 and withdrawn the same day

**TEAMLEAD's error, on three independent grounds, each sufficient.**

**1. It contradicted a standing ruling.** Ninety minutes earlier TEAMLEAD had ruled — after
measuring **zero** closure reservations across all four goal files, this file, `TEAMLEAD.md` and
`DEV.md` — that closure is *not* reserved. The entry was adopted from one file's copy while
ruling union-not-intersection, and never read against the ruling it collided with. ⚠ **A union
assembled without reading it against what it collides with is a concatenation, not a union.**

**2. Its trigger was unevaluable, and that locked a rung for the whole fleet.** Measured:

```
open issues 31 · with an assignee 2 · with NO assignee 29
```

An unattributed issue has no evaluable owner, so the safe reading is *do not close* — reserving
**29 of 31**. ⇒ Rung 2 became structurally empty for every DEV, by one line, while TEAMLEAD was
separately reporting that the DEVs were idle because their ladders had correctly terminated.
**They were idle because the rung was locked.** Found by a DEV that measured its own reachable
set at **3 of 29** and reported the empty rung rather than descending.

**3. ⛔ Its subject is not a distinguishable state on this estate.** Measured: `gh issue list
--json author` returns **one login for every issue in every state** — the shared credential (#4).
So no agent can determine whether an issue is another role's *before* closing it, and no auditor
can determine whether the reservation was respected *afterwards*. The only discriminator is a
role name in the issue **body prose**. ⇒ **A reservation whose subject the substrate cannot
express is unenforceable and unauditable in the same stroke** — the second convention to fail
this way, after the `@me` claiming convention.

⇒ **REPLACED BY, and this one is readable:**

> ~~**Do not close an issue that is ASSIGNED to someone else.**~~ ⛔ **ALSO WITHDRAWN — it
> inherits the defect it was written to fix.**

⛔ **Measured at `b460040`:**

```
gh api user                        ->  jobordu
issues with an assignee            ->  #49 jobordu, #16 jobordu
gh issue list --assignee @me       ->  49, 16   ← claimed by NEITHER of them
```

⇒ *Assigned to me* and *assigned to someone else* **are the same value.** The field is readable
and **not discriminating** — readability was never the defect. ⚠ TEAMLEAD replaced an unevaluable
reservation with an undecidable one and called the difference a fix.

⛔ **And it composes with the claiming convention into a deadlock.** `goals/README.md` says *claim
before working, `--add-assignee @me`*:

```
claim the item  ->  assignee := jobordu
close it        ->  "assigned to someone else?"  ->  UNDECIDABLE
```

⇒ **Claiming an issue is what makes it uncloseable by the agent that claimed it.** There is no
correct reading, only two wrong ones: *safe* (field non-empty ⇒ someone holds it) locks the
claimer out of its own work; *permissive* (`jobordu` is me ⇒ mine) makes the rule a no-op. Both
panes comply and which failure occurs depends on which way each reads it.

⚠ **It looks harmless only because compliance is low.** 2 of 31 assigned today — and the ratio
**worsens as claiming is adopted.** Every correctly-claimed issue enters the undecidable set.
The withdrawal unlocked 29 unassigned issues and quietly locked the ones an agent is actually
working on.

> ⇒ **REQUIREMENT, not a remedy:** a rule keyed on ownership needs a field carrying the **PANE**,
> not the account. Until one exists, **no ownership-keyed reservation on issues is enforceable**,
> and one should not be written. Third convention defeated this way, after `@me` claiming and the
> row above.



Keyed on the assignee field, which is a fact a caller can read in one call — not an ownership it
must infer from prose. It preserves the real concern (do not close work someone is holding) and
it fails closed only where the field actually says so.

⚠ **It is therefore weaker than what it replaces, deliberately.** With 29 of 31 unassigned it
constrains almost nothing today. That is the correct state: **the fix for an unowned board is
triage, not a reservation that makes unowned mean untouchable.**
## ★ GRANTED — read-only monitors on your own instruments

**Operator, 2026-08-20.** Every role may arm a **read-only monitor** on instruments it owns,
without asking further.

⇒ Bounds, all four load-bearing:

- **Read-only.** It may observe. It may not merge, push, close, edit, or write to another pane.
- ⛔ **It carries no authorization.** A timer that re-enters an agent with a plausible
  instruction has *genuine provenance*, which is worse than a forgery — a forgery can be caught
  by checking the channel and a real scheduled job cannot. A monitor emits a **finding**, never
  a task and never a grant.
- ⛔ **Silence must mean "ran and found nothing", never "could not run".** Emit on the finding,
  emit on VOID, and emit on any exit code the instrument does not document. A watch whose quiet
  covers both states is the never-concluded defect with a schedule attached.
- **Your own instruments only.** Arming a loop in another role's pane remains the operator's.

⚠ **This supersedes the earlier reservation** that placed *any* pane's self-scheduling with the
operator. That line was written before any monitor existed and was already inconsistent with a
ratified `fleet-context` watch; it is narrowed here rather than left to be routed around.

⚠ **A monitor does not make an instrument armed at the right moment.** The one existing caller
runs `stranded-branches.py` at **launch** — and the regression it would have caught arrived at
**merge** time, hours before the next launch. **A caller is necessary; its placement is a
separate question.**

## Standing grants

### GRANTED — `--force-with-lease`, pinned

*TEAMLEAD ruling 2026-08-19, issued to DEV1, made durable here.* Standing, every role,
`nForma-AI/nForma-NEXT` only:

> `--force-with-lease=<branch>:<sha>` where `<sha>` is a commit **you pushed**, on a branch **you
> own**, to land a rebase that was asked for. **Disclose it on the PR.**

⛔ **NOT granted:** bare `git push -f` / `--force`; any force to a branch you do not own; any force
to `main`; any lease not pinned to a SHA you personally pushed.

⚠ ***"I expected the push to be rejected" is not a reason to reach for the bare flag.*** Establish
the force is needed first — a rejected non-fast-forward push, or `merge-base --is-ancestor`
returning false. Measured: one bare `-f` this session followed a rebase that was a **no-op**, so the
flag did nothing and the reservation was self-granted for no reason at all (#80, class B).

### Branch creation, branch push, `gh pr create`

Session-scoped and revocable. TEAMLEAD, 2026-08-19. ⚠ **A grant is not the absence of a
reservation** — the justification for the imported CI-spend clause did not transfer, and the
reservation did not thereby lapse (#16, #42).

---

## ⚠ What this document does not fix

- **Delivery.** `goals/` loads at session start, so adding a reservation here reaches **zero running
  agents**. A referenced document is **one more artifact a running agent has not loaded** than a copy
  in the file it already reads. This trades a **sync** defect for a **delivery** one, deliberately and
  with the cost stated. *(`goals/README.md`, "Durable is not delivered")*
- ⛔ **Binding.** Delivery is **necessary and not sufficient.** Measured the same evening: a
  force-push reservation was **authored by the agent that broke it**, in that agent's own goal file,
  hours earlier, and did not participate in the decision. *(#80, class B)* ⇒ **No document fixes
  that.** The remedy for a mechanically detectable reservation is a mechanical guard, and this file
  is not one.

### ⚠ The transition, with a termination condition

Until each goal file's Reserved section becomes a **pointer** to this document, the copies and this
document coexist — **four sources instead of three**, which is temporarily worse than either.

> **Each role converts its own Reserved section to a pointer when it next touches its goal file.**

⛔ Stated as a condition rather than left open, because a transitional cost with no termination is
permanent. ⚠ The content of each file is that role's; nobody rewrites another role's section to
close this faster. The boundary holds and **the deadline is not nobody's**.

⇒ **Read this document as provenance and as the resolution of drift — never as enforcement.**
