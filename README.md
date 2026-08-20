# nForma-NEXT

**An operating discipline for autonomous agent fleets — and the launcher for one.**

This repository has **no application code.** Its artifacts *are* the product: five role prompts,
per-role standing goals, fleet instruments, and the Daintree recipe that launches nine agents into
one workspace.

---

## Install the fleet into your repository

Give this line to a coding agent working in the repo you want the fleet in:

> Clone https://github.com/nForma-AI/nForma-NEXT, then read `onboard.md` at the root — it contains
> your full instructions for onboarding me through this tool.

That is the whole instruction. [`onboard.md`](onboard.md) carries the rest: it detects what is
already present, copies the seven files the later steps invoke, re-scopes the goal files to your
repository, validates the recipe, gives every role its own worktree, and ends by running
`scripts/fleet-preflight.sh` as the **acceptance test**.

⇒ **Every step is idempotent.** Running it twice changes nothing the second time, and a step that
skips says so — because a silent skip and a step that ran are otherwise the same output.

---

## The roles

| pane | fundamental question |
|---|---|
| `TEAMLEAD` | is this work reaching a justified terminal state? |
| `ARCHITECT` | is this technically correct, and does the evidence bind? |
| `DEVOPS` | does the substrate do what we believe it does? |
| `DX` | is the way we work getting better, and how would we know? |
| `DEV1`–`DEV5` | implementation |

## Read these four, in this order

| # | file | the question it answers |
|---|---|---|
| 1 | [`docs/FOUNDING-THESIS.md`](docs/FOUNDING-THESIS.md) | why does this repository exist, and what was measured to justify it? |
| 2 | [`prompts/README.md`](prompts/README.md) | who are the roles, and how does the fleet launch? |
| 3 | [`tools/README.md`](tools/README.md) | what can be measured here, and what does each instrument refuse to claim? |
| 4 | [`goals/README.md`](goals/README.md) | what must a role's standing goal contain, and who owns it? |

[`CLAUDE.md`](CLAUDE.md) is the map for an agent already working here. It is a **map, not doctrine** —
if it and a README disagree, the README wins and the map is the defect.

---

## The one convention to carry into everything else

> ⛔ **`exit 2` means *established nothing*, and must never be read as *all clear*.**

Most of what this repository has learned is a variation on that. A check that never ran and a check
that passed produce the same silence. A missing validator and a passing one produce the same
silence. A pinned tool that is current and one frozen forty commits back both report `pinned`.

⇒ The instruments here are built to **refuse a verdict** rather than report a clean one they cannot
support — which is why several of them exit `2` more often than they exit `0`.

## Where things live

| path | contents |
|---|---|
| [`onboard.md`](onboard.md) | the entry point for installing this fleet elsewhere |
| `docs/` | the thesis the rest is derived from |
| `prompts/` | the five role prompts |
| `goals/` | per-role standing goals, and `RESERVED-ACTIONS.md` — the single source for what is reserved to whom |
| `tools/` | fleet instruments (Python, run directly) |
| `scripts/` | recipe validator, worktree manager, preflight, conformance checkers |
| `.daintree/recipes/` | the ten-pane launcher |
