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


---

## Launching the set — `.daintree/recipes/nforma-fleet.json`

The prompts above describe roles; the recipe launches them. It is an **in-repo Daintree recipe**,
discovered automatically when this project is opened, and it travels with the repo rather than
living in one operator's app config.

Ten panes — the cap is ten:

| pane | type | carries |
|---|---|---|
| `TEAMLEAD` | `claude` | `NFORMA_ROLE=TEAMLEAD`, `NFORMA_ROLE_PROMPT=prompts/TEAMLEAD.md` |
| `ARCHITECT` | `claude` | `NFORMA_ROLE=ARCHITECT`, → `prompts/ARCHITECT.md` |
| `DEVOPS` | `claude` | `NFORMA_ROLE=DEVOPS`, → `prompts/DEVOPS.md` |
| `DX` | `claude` | `NFORMA_ROLE=DX`, → `prompts/DX.md` |
| `DEV1`–`DEV5` | `claude` | `NFORMA_ROLE=DEV<n>`, → `prompts/DEV.md` |
| `PREFLIGHT` | `terminal` | runs `scripts/fleet-preflight.sh` — no agent involved |

Panes are given a short bootstrap, not a copy of their prompt, so `prompts/*.md` stays the single
source of truth: editing a role prompt changes behaviour on the next launch with no recipe edit.

### Identity comes from the environment, not from memory

`DEV.md` §1 and `DEVOPS.md` §4 require

```
logical identity = Daintree panel name = Claude session name
```

The recipe sets `NFORMA_ROLE` as a **per-pane environment variable**. This is the load-bearing
choice. An environment variable is set by the substrate before the agent exists, cannot be
forgotten, misremembered, or drifted away from, and — crucially — is *readable back*: `echo
$NFORMA_ROLE` is an off-pane effect, not a claim the agent makes about itself. Each pane's
`ROLE-READY` line is required to quote the value it read, never a value recalled from its prompt.

```
ROLE-READY <$NFORMA_ROLE> repo=<basename of toplevel> branch=<branch>
```

That single line carries three facts that were otherwise three assumptions: the role prompt
loaded, the identity is what it should be, and the pane is in the workspace it was meant to be in.
The third matters because a workspace silently flipping to another project is one of the three
delivery failures in FOUNDING-THESIS §2.

### The session name is the third leg, and it is set by `args`, not by the agent

`NFORMA_ROLE` establishes the *role* leg. It does not touch the **Claude session name** — the name
`ListAgents` shows and `SendMessage` routes on. That leg is set by a launch flag:

```json
{ "type": "claude", "title": "DEVOPS", "env": {"NFORMA_ROLE": "DEVOPS"}, "args": "-n DEVOPS" }
```

`claude -n <name>` sets the session's display name at launch. Measured: a session launched with it
writes `"name":"DEVOPS"` into `~/.claude/sessions/<pid>.json` **with no `nameSource` key**, where an
auto-named session carries `"nameSource":"derived"`. The name is addressable — the probe resolved in
another session's `ListAgents` as `RENAME-PROBE-B [af61a4]`.

⚠ **The audit predicate is key-absence, not a value.** `nameSource` is *removed* by a successful
rename, never set to `"user"`. The strings `auto` and `user` do occur in the CLI binary and are the
obvious thing to test for; a checker written against them never fires on any row this system
produces. The check is `"nameSource" not in row`.

⛔ **`args` must be a single string.** The normalizer's predicate is
`typeof r.args != "string" → return null`, and `return null` discards **the whole pane**. The array
form `["-n", "DEVOPS"]` does not drop the flag — it drops the agent. Nine of them produce a recipe
that launches nothing, presenting as panes nobody opened. `scripts/validate-recipe.py` catches this
(`ERR pane[2] DEVOPS: args must be a single-line string`, exit 1), which is why it is run rather
than trusted-by-reading.

⇒ The three legs now have three different owners: `title` (panel, unpinned and therefore a hint),
`NFORMA_ROLE` (role, authoritative), `args: -n <ROLE>` (session name, what routing resolves). They
are set by the substrate at launch and none of them depends on the agent remembering anything.

### `PREFLIGHT` — the pane with no agent in it

Pane 10 is a plain terminal running `scripts/fleet-preflight.sh`. It verifies the repo, branch,
working-tree cleanliness, the five prompt files, `git`/`gh`/`claude` on PATH, and `gh` auth — then
prints the expected roster as a checklist.

It exists because **nine agents asserting they are ready is not the same as nine agents being
ready**. The preflight establishes by execution what the agent panes each claim in prose, so the
claims have something to be checked against. It reports and never gates: exit code is always 0.

### What this recipe cannot do

Three limits are properties of the substrate, not oversights. `scripts/fleet-preflight.sh` prints
them at launch so they are never quietly forgotten:

- **Panel titles are not pinned.** A recipe sets `title` but leaves `titleMode` unset, which is the
  state that *permits* agent auto-titling to overwrite it. (Daintree's own `agent.launch` action
  pins titles by explicitly setting `titleMode: "custom"`; recipes have no equivalent field.) The
  tab label is therefore a hint. `$NFORMA_ROLE` is the identity.
- **A recipe cannot sequence.** All ten panes spawn concurrently through `Promise.allSettled`.
  There is no ordering, no inter-pane dependency, and no way to make one pane wait for another.
  Post-launch sequencing requires Daintree actions/MCP at `action` tier, which the recipe cannot
  grant itself.
- **An agent cannot invoke a slash command.** `initialPrompt` is shell-quoted and passed as *argv*
  to the agent CLI, with newlines collapsed to spaces. Slash commands are expanded by the CLI's
  input layer; a model emitting `/rename X` produces text, not an effect. An earlier version of
  this recipe instructed `/rename` and it silently did nothing — which is precisely the
  "check with no execution record" failure the ⚠ note above warns about, committed by the very
  file meant to remove it.

TEAMLEAD is consequently **not** told to gate on the other eight `ROLE-READY` lines: it cannot read
other panes' output without the Daintree MCP, so that check would have no execution record from
inside the pane. Verifying fleet readiness is an operator or DEVOPS action, against the PREFLIGHT
checklist.

More broadly, a recipe is **substrate**. It launches panes and delivers a first prompt. It cannot
express authority grants, instruction lifecycle, evidence validity, admission/merit, or budgets —
those are the nForma-NEXT half of the boundary in FOUNDING-THESIS, and nothing here covers them.

### Editing the recipe

Run `python3 scripts/validate-recipe.py` after any change. Daintree's loader is *quietly* lossy —
its normalizer returns a fixed field set, so a recipe can be schema-valid, load without a single
error, and still not do what it says. The validator separates the two failure modes:

```
ERR    the pane or recipe is rejected outright
WARN   the field is accepted, then silently dropped
```

Constraints worth knowing before hand-editing:

- **10 panes maximum.** This recipe uses all ten.
- `initialPrompt` and `args` are kept only for **agent** types; `command` only for
  `type: "terminal"`; `devCommand` only for `type: "dev-preview"`. The wrong one for a pane type is
  dropped without a warning.
- `agentModelId` and `agentLaunchFlags` pass schema validation and are then **discarded**.
- `args` is split on whitespace, so it carries flag tokens only — no quoted multi-word values and
  no `$(...)` substitution.
- One malformed `env` value drops the **entire pane**, not just that variable.
- `exitBehavior` accepts `keep` / `trash` / `remove`. `restart` appears in the schema but the
  normalizer rejects it.
- `initialPrompt` supports `{{issue_number}}`, `{{pr_number}}`, `{{number}}`, `{{worktree_path}}`,
  and `{{branch_name}}`, resolved at launch.
- Launch flags are not set here: `--dangerously-skip-permissions` is already configured globally
  for the `claude` agent in Daintree's settings, and duplicating it would create a second place to
  keep in sync.
