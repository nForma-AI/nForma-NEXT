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
| `devops-substrate-and-fleet.md` | **no reserved section at all** | — | — | — |

⇒ **Three files, three different texts, one evening, no sync.** And the drift produces **no error** —
each file reads as complete, and an agent holding the narrowest copy is fully compliant with it.

⛔ **Nothing here is a claim that any role wrote its copy wrongly.** Each was correct when written.
That is what makes hand-maintained duplication the defect rather than anyone's diligence.

---

## Reserved to TEAMLEAD — no role self-grants these

| reservation | already durable in |
|---|---|
| **Merging.** Any PR, any branch, any circumstance — regardless of what the session is named. | architect · dev · dx |
| **Pushing to `main`.** | architect · dev · dx |
| **Force-push to any branch.** ⚠ See the grant below — bare `-f` and `--force-with-lease` differ. | architect · dev · dx |
| **History rewrite on any branch.** | architect · dx — ⚠ **absent from dev** |
| **Closing another role's issue.** | architect — ⚠ **absent from dev and dx** |
| **Anything targeting a repository other than this one**, including `Borduas-Holdings/Blazing-Back` and `Digital-Frontier-LDA/df-wiki`. | architect · dev · dx |
| **Contacting the operator.** Route through TEAMLEAD, saying explicitly that it needs the operator. | dx — ⚠ **absent from architect and dev** |
| **Assigning work to another role.** | dx — ⚠ **absent from architect and dev** |

⚠ **Authorization arrives in a TEAMLEAD message and nowhere else.** Origin is the only
discriminator; plausibility is what the channel optimises for. *(all three)*

⛔ **A grant issued after the fact cannot bound the action it follows.** An agent that acts on what
it is confident will be ratified has replaced the authorizer's judgement with its prediction of that
judgement. *(`goals/README.md` §2)*

---

## Standing grants

| grant | scope | provenance |
|---|---|---|
| Branch creation, branch push, `gh pr create` | session-scoped, revocable | TEAMLEAD, 2026-08-19. ⚠ A grant is not the absence of a reservation. |
| `--force-with-lease` **pinned to a SHA you pushed**, on **your own** branch | standing | ⛔ **NOT YET DURABLE — see below** |

### ⛔ NOT YET DURABLE — exists only in messages

> `--force-with-lease` pinned to a SHA you pushed, on your own branch, is granted. **Bare `-f` is
> not**, and *"I expected the push to be rejected"* is not a reason to reach for it — check whether
> it is needed first.

⚠ This currently exists in **two messages to two roles** and in no committed file. It is recorded
here as **pending TEAMLEAD's confirmation**, not as in force. ⇒ Until TEAMLEAD lands it, **treat
bare `-f` as reserved**. Recording the pending state rather than silently promoting it is the
distinction this document exists for: *a reservation is complete only when every agent it binds has
it; a note that one is coming is not that.*

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

⇒ **Read this document as provenance and as the resolution of drift — never as enforcement.**
