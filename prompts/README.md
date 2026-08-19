# Role prompts — the current, hand-run version

These are the five role prompts as they exist **today**, running by hand across Daintree panes.
They are the artifact `docs/FOUNDING-THESIS.md` is written about: the thesis is derived from
operating this exact set, not from speculation about what such a set might need.

They are committed here as the **baseline**, for three reasons:

1. **A starting point.** nForma-NEXT productizes this discipline. The prompts are the current
   specification of it.
2. **A measurement baseline.** Every improvement is a hypothesis (DX §18). Comparing against a
   committed baseline is how "did it work?" becomes answerable rather than remembered.
3. **A record of what prose was asked to carry.** Much of what is here is prose asking a reader
   to remember something a machine could check. Identifying which parts those are — and moving
   them into the substrate — is a large part of the work ahead.

| file | role | fundamental question |
|---|---|---|
| `TEAMLEAD.md` | orchestrator, sole USER interface | What should the team do next, and why? |
| `ARCHITECT.md` | technical and knowledge integrity | Is the system technically right, coherent, verified, and understood? |
| `DEVOPS.md` | operational integrity, control plane | Is the machinery working, and how can it work better? |
| `DX.md` | developer experience, organizational learning | How can engineering work better next time, here and across the organization? |
| `DEV.md` | implementation | How do I satisfy my goal correctly? |

`DEV.md` is a template — `DEV#` is replaced with the canonical name (`DEV1`, `DEV2`, …).

## The communication model these encode

```
USER  ⇄  TEAMLEAD          (only)

Daintree  — the nervous system   : transient coordination, low latency
GitHub    — institutional memory : durable engineering communication
Code/docs — implementation state : what the system actually is
```

The load-bearing rule: **if future engineering work depends on understanding an interaction,
it must not exist only in Daintree.**

Consequences per role: ARCHITECT is GitHub-heavy for substantive review; DX produces nearly all
mature findings as durable artifacts; DEVOPS uses Daintree for transient outages but GitHub/code
for persistent operational work; DEV keeps reasoning that matters to future engineers attached to
the relevant issue or PR.

## ⚠ Treat these as a baseline, not as settled

The thesis argues that several things these prompts ask an agent to *remember* cannot be solved
from outside the substrate — delivery verification and instrument validity in particular. Where a
rule here asks a reader to check something mechanical, the rule is a **check with no execution
record**: its compliance is unobservable, so its violation rate is unmeasurable.

Those are the parts most worth replacing with the product.
