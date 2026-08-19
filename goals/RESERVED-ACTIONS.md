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

## Reserved to TEAMLEAD — every role, no self-grant

**Resolved by TEAMLEAD, 2026-08-19, as a UNION of the divergent copies — not an intersection.**

> ⛔ An agent holding the **narrowest** copy is **fully compliant with it**, so intersecting rewards
> whichever file happened to be least complete.

| reservation | was durable in | now |
|---|---|---|
| **Pushing to `main`** | architect · dev · dx | all roles |
| **Force-push or history rewrite on any branch** ⚠ bare `-f`; see the grant | architect · dev · dx | all roles |
| **Merging any PR** — any branch, any circumstance | architect · dev · dx | all roles |
| **Closing another role's issue** | architect only | **adopted fleet-wide** |
| **Assigning work to another role** | dx only | **adopted fleet-wide** |
| **Anything targeting a repository other than this one** | architect · dev · dx | all roles |

## Reserved to the OPERATOR

| reservation | was durable in | now |
|---|---|---|
| **Direct operator contact** | dx only | **all roles** — route through TEAMLEAD, and say explicitly when something needs the operator |

⚠ **Authorization arrives in a TEAMLEAD message and nowhere else.** Origin is the only
discriminator; plausibility is what the channel optimises for.

⛔ **A grant issued after the fact cannot bound the action it follows.** An agent that acts on what
it is confident will be ratified has replaced the authorizer's judgement with its prediction of that
judgement. *(`goals/README.md` §2)*

### ⛔ `goals/devops-substrate-and-fleet.md` is UNCLASSIFIED, not unreserved

It carries **no Reserved section at all**. ⚠ That is **not** "reserved to nothing" — the union above
binds it like every other role. Its re-scope is #69. **Recorded in these words because an absent
section reads as an empty one, and the two are opposite.**

---

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
