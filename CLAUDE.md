# nForma-NEXT — orientation

**This repository has no application code.** Its artifacts *are* the product: role prompts,
role goals, fleet instruments, and the recipe that launches them. If you are looking for a
service to run or a test suite to go green, there isn't one — the thing under construction is
the operating discipline of an autonomous agent fleet.

⚠ This file is a **map, not doctrine.** Every rule lives in one of the four READMEs below and
is stated there once. Nothing here is the authority for anything; if this file and a README
disagree, the README wins and this file is the defect.

---

## Read these four, in this order

| # | file | the question it answers |
|---|---|---|
| 1 | `docs/FOUNDING-THESIS.md` | Why does this repository exist, and what was measured to justify it? |
| 2 | `prompts/README.md` | Who are the roles, how do they communicate, and how does the fleet launch? |
| 3 | `tools/README.md` | What can be measured here, and what does each instrument refuse to claim? |
| 4 | `goals/README.md` | What must a role's standing goal contain, and who owns it? |

`tools/README.md` is the densest. The convention worth carrying out of it: **exit 2 means
"established nothing" and must never be read as "all clear."**

## Where things live

| path | contents | its own doc |
|---|---|---|
| `./onboard.md` | **the entry point for a coding agent installing this fleet elsewhere** — hand it the one-line bootstrap and it reads this | — |
| `docs/` | the thesis the rest is derived from | — |
| `prompts/` | five role prompts (`TEAMLEAD` `ARCHITECT` `DEVOPS` `DX` `DEV`) | `prompts/README.md` |
| `goals/` | per-role standing goals + the standard they must meet | `goals/README.md` |
| `tools/` | fleet instruments (Python, run directly) | `tools/README.md` |
| `scripts/` | `scripts/validate-recipe.py`, `scripts/fleet-preflight.sh` | `prompts/README.md` |
| `.daintree/recipes/nforma-fleet.json` | the ten-pane launcher | `prompts/README.md` |

## Four things that will bite you in the first five minutes

Each is explained in full at the pointer; none of it is restated here.

- **Nine agents may share one working tree.** A `git checkout` in your pane rewrites every
  other pane's files, including the role prompts they are operating on. Prefer
  `git show <ref>:<path>` for reading, and `git worktree add` for writing.
  → `prompts/README.md` § *Each agent gets its own working tree*, issue #19
- **Your role prompt is not a fixed input, and `HEAD` is not doctrine.** It is a file in a tree
  other panes are committing to, and your tree is almost certainly behind. Re-read it at
  `git show origin/main:prompts/<ROLE>.md`, after a `git fetch` — **not** at `HEAD`.
  *(measured 2026-09-06: the shared tree is 414 commits behind and stale on all five prompts;
  `ARCHITECT.md` differs from doctrine in 18 of 19 worktrees. ⚠ Distance is not the test — a
  tree 611 commits behind can hold the byte-identical blob. Compare the blob, not the count.)*
  → `prompts/README.md` § *Treat these as a baseline* and its rule **"Doctrine is
  `origin/main`"**, issue #205
- **You cannot invoke a slash command.** A model emitting `/rename X` produces text, not an
  effect; slash commands are expanded by the CLI's input layer, not by you.
  → `prompts/README.md` § *What this recipe cannot do*
- **End every turn with a `STATE:` line.** It is parsed positionally — the last line — and
  `tools/fleet-state.py` is what reads it.
  → your own `prompts/<ROLE>.md`

## Facts with a measurement date, not standing claims

- ⛔ **~~No CI.~~ FALSE since 2026-08-20 — CI exists and GATES.** `.github/workflows/tools.yml`
  is present on `main` and on multiple refs; `hermetic suites (gating)` is a **required check**
  and has blocked a merge. *(re-measured 2026-08-20 at `2effc63`, `git ls-tree -r` over remote refs;
  #272.)*
  ★ **The commit that falsified this claim cited it as its justification** — *"this repository
  had no CI, so 23 instruments and 19 suites had never run"* (`239639a`). ⇒ **A measurement is
  most likely to be falsified by work it caused**, which is exactly when nobody re-checks it: the
  author of the fix already knows, and the files asserting it are not in the fix's blast radius.
  ⚠ The old line carried a date, a SHA, a method, and *"re-measure before relying on either"* —
  **all four, and it still decayed for ~7 hours.** Dating a claim tells a reader it CAN decay; it
  does not tell them it HAS. ⇒ `scripts/check-orientation.py` now re-measures this one.
- **One git credential for all panes** — GitHub records the operator for whatever any pane
  posts, so name yourself in the body of anything you file. *(issue #4.)*

⇒ Re-measure before relying on either. A number without a date is a rumour.

---

## Onboarding someone else's repository

One line, handed to a coding agent — it is a **pointer, not a copy**, so it stays valid while the
instructions change under it:

> Clone https://github.com/nForma-AI/nForma-NEXT, then read `./onboard.md` at the root — it contains
> your full instructions for onboarding me through this tool.

⚠ `./onboard.md` installs **four things, not one**: the recipe, the prompts, `scripts/validate-recipe.py`,
and the goals. ⛔ Without the validator its validation step establishes nothing and reports no error.

---

`scripts/check-orientation.py` asserts that every path named above exists. Run it after moving
or renaming anything. A map whose pointers rot silently is worse than no map, because it is
still believed.
