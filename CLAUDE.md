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
- **Your role prompt is not a fixed input.** It is a file in a tree other panes are committing
  to. Re-read it at `HEAD` before acting on what you remember of it.
  → `prompts/README.md` § *Treat these as a baseline*
- **You cannot invoke a slash command.** A model emitting `/rename X` produces text, not an
  effect; slash commands are expanded by the CLI's input layer, not by you.
  → `prompts/README.md` § *What this recipe cannot do*
- **End every turn with a `STATE:` line.** It is parsed positionally — the last line — and
  `tools/fleet-state.py` is what reads it.
  → your own `prompts/<ROLE>.md`

## Facts with a measurement date, not standing claims

- **No CI.** Zero workflow or `*.yml`/`*.yaml` files on any local or remote ref.
  *(measured 2026-08-19 at `c465e8e`, 9 refs, `git ls-tree -r` per ref.)* Nothing here gates on
  a green check, and opening a PR draws no runner.
- **One git credential for all panes** — GitHub records the operator for whatever any pane
  posts, so name yourself in the body of anything you file. *(issue #4.)*

⇒ Re-measure before relying on either. A number without a date is a rumour.

---

`scripts/check-orientation.py` asserts that every path named above exists. Run it after moving
or renaming anything. A map whose pointers rot silently is worse than no map, because it is
still believed.
