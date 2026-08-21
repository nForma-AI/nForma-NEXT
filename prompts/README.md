# Role prompts — the current, hand-run version

## ⇒ Installing the fleet recipe — hand this to a coding agent

**Copy everything between the rules into a coding agent working in the repository you want the
fleet to run in.** It installs `.daintree/recipes/`, and it is written to fail loudly rather than
install something that loads cleanly and does not do what it says.

---

> Install the nForma fleet recipe into this repository.
>
> **1. Recipes are read IN-REPO.** Daintree loads `.daintree/recipes/*.json` from the repository
> root. It does **not** read `~/.daintree` — that holds only `cli.sock` and `cli-control.json`.
> Create `.daintree/recipes/` here; do not install anything into the home directory.
>
> **2. Copy TWO files from `nForma-AI/nForma-NEXT`, not one:**
> - `.daintree/recipes/nforma-fleet.json` — adapt the role names, the `NFORMA_ROLE_PROMPT` paths
>   and the pane count to this repo. **Keep the shape.**
> - `scripts/validate-recipe.py` — ⛔ **step 4 runs this. Without it that step silently does
>   nothing and you proceed on an unvalidated recipe.** If you cannot bring it across, say so
>   explicitly and treat step 5 as the minimum bar rather than skipping validation quietly.
>
> **3. ⛔ `args` MUST be a JSON string, never a list.** `"args": "-n DEV1"` is correct.
> `"args": ["-n", "DEV1"]` is schema-valid, loads without an error, and **silently discards the
> entire pane**. This is the single most expensive mistake available here — an approved list-form
> edit would have deleted nine panes at once and reported success.
>
> **4. Run the validator and require exit 0:**
> ```
> test -f scripts/validate-recipe.py || echo "⛔ VALIDATOR ABSENT — step 4 established nothing"
> python3 scripts/validate-recipe.py .daintree/recipes/*.json ; echo "exit=$?"
> ```
> ⚠ Read the exit code **without a pipe**. `| tail` returns tail's status, not the validator's.
> The validator exists because Daintree's normalizer returns a fixed field set: **schema-valid
> fields are silently dropped, and malformed ones silently drop the pane.** A recipe can be 100%
> valid JSON, load with no error, and still not do what it says.
>
> **5. Assert these, and print each count rather than asserting it passed:**
> ```
> python3 - <<'EOF'
> import json, glob, os, sys
> for f in glob.glob(".daintree/recipes/*.json"):
>     t = json.load(open(f))["terminals"]
>     agents = [x for x in t if x.get("type") == "claude"]
>     print(f, len(t), "panes,", len(agents), "agent panes")
>     assert all(isinstance(x.get("args"), str) for x in agents), "args must be a STRING"
>     assert all(x.get("initialPrompt") for x in agents), "every agent pane needs an initialPrompt"
>     for x in agents:
>         pr = (x.get("env") or {}).get("NFORMA_ROLE_PROMPT")
>         assert pr and os.path.exists(pr), f"missing prompt file: {pr}"
>     print("  NFORMA_GOAL set on", sum(1 for x in agents if (x.get("env") or {}).get("NFORMA_GOAL")), "of", len(agents))
>     print("  panes with their own cwd/worktree:", sum(1 for x in t if x.get("cwd") or x.get("worktree")))
> EOF
> ```
>
> **6. Two known gaps in the reference recipe. Decide each deliberately; do not copy them by
> default.**
> - **`NFORMA_GOAL` is set on 1 of 9 agent panes.** A pane without it has no standing objective at
>   launch, and an agent woken with no objective consumes context and mutates nothing.
> - **No pane declares its own `cwd` or worktree**, so every pane shares one working tree. A
>   `git checkout` in any pane rewrites every other pane's files, including the role prompts they
>   are operating on.
>
> **7. Report what you installed as counts, not as "done":** panes, agent panes, prompt files
> resolved, `NFORMA_GOAL` coverage, validator exit code. ⛔ Do not report success from the
> validator's silence — report the number it printed.

---

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

### ⛔ The baseline is a REF, not these files — and treating them as both has already cost it

Reasons 2 and 3 ask these files to be a **captured specimen**. Reason 1 and every running pane ask
them to be **live doctrine**. ⚠ **Nothing in a file says which reading applies**, so an edit that
improves doctrine silently destroys the specimen (#16).

**Measured — the specimen is already gone, and nothing reported it:**

```
                  first commit 2e4c9d2 (2026-08-19)   at origin/main
ARCHITECT.md              459 lines             ->        660   (+44%)
TEAMLEAD.md               724 lines             ->       1113   (+54%)
DEV.md                    537 lines             ->        698   (+30%)
```

⇒ A reader opening `prompts/ARCHITECT.md` today to see *"what prose was asked to carry"* gets a file
half again as long as the one that was asked to carry it. **The dual reading did not preserve the
specimen. It made the loss invisible**, which is worse than deleting it, because a deletion is
visible.

> **The baseline is `2e4c9d2`. Doctrine is `origin/main`. A file is never both, and a claim about
> the baseline that names no ref is a claim about whatever the file happens to say today.**

★ **This costs nothing to adopt** — the specimen was never in the working file; it was always in the
history, and this only writes down where. ⇒ It is this repo's own rule (*name the ref per claim*)
applied to its own prompts, and it means an edit to a live prompt **no longer trades doctrine
against provenance**. ⚠ An annotated tag would be the durable form; **the SHA above is durable
whether or not one is ever cut.**

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

### ⛔ A ROLE NAME IS NOT AN ADDRESS

**Measured 2026-08-20, two callers, independently.** A message addressed to the bare name
`TEAMLEAD` reached a `TEAMLEAD` on **another company's fleet**, returned `success:true`, and was
stopped only because that recipient chose to check and decline.

```
ListAgents      51 rows   repository / worktree field on any row:  NONE
terminal_list    9 panes  worktreeId on EVERY one
```

⇒ **The routing key exists one layer down and the messaging layer discards it.** Three identifier
spaces are in play — **pane title**, **peer registry name**, **worktreeId** — and no rendering
shows more than two at once.

```
REPLYING      uds:/tmp/cc-socks/<pid>.sock, copied from the `from=` stamp
              ⇒ a value that ARRIVES WITH THE MESSAGE and cannot be resolved wrong
INITIATING    terminal_list → read worktreeId → terminal_sendCommand <terminalId>
              ⇒ the only send whose receipt echoes an id resolving to an estate
BARE NAME     ⛔ not an address, and not rescued by appending a [ref]
```

⛔ **The documented `[ref]` disambiguator cannot fire here.** It triggers on *two rows sharing a
name*; in the failing case **only one row is ever listed**. There is nothing to disambiguate
against, and a convention keyed on a signal the listing does not emit is not a mitigation.

★ **Uniqueness is read as correctness, and uniqueness is produced by the defect.** The foreign row
looked unambiguous *because the correct local target was absent from that namespace*. ⚠ And the
listing **excludes the caller**, so every pane sees its own role name as one rarer than it is —
every pane is biased toward believing its own name is unique, which is the condition that reads
as safe.

⚠ **`success:true` establishes transport, never target.** A correct receipt and a misdelivered one
render identically.

⇒ **The check that actually worked was not at the sender.** Citing `owner/repo#number` in every
reference made the misdelivery **self-detecting for the recipient** — every filename cited existed
in their repo too; only the issue numbers disagreed. **Cite `owner/repo#number` always.**


Consequences per role: ARCHITECT is GitHub-heavy for substantive review; DX produces nearly all
mature findings as durable artifacts; DEVOPS uses Daintree for transient outages but GitHub/code
for persistent operational work; DEV keeps reasoning that matters to future engineers attached to
the relevant issue or PR.

### ⛔ A LABEL IS NOT AN ASSIGNMENT EITHER — `role:` is the queue, `dev:N` is usually provenance

⚠ **The limits first, because they bound everything below.** This rule is derived from **15 open
issues on one board on one night**, all labelled by one pane. ⛔ **It is not derived from a stated
intent** — nobody wrote down what `dev:N` was supposed to mean, and I did not ask the panes that
carry it. **What follows is the reading the board best supports, not the reading anyone declared.**
⇒ **A pane that meant its `dev:N` as an assignment should say so and this rule loses.**

**The defect (#461).** `role:` and `dev:N` are both queryable, both populated, and until this
paragraph **nothing said which wins.** A pane running `--label dev:5` and a pane running
`--label role:DEVOPS` both got an authoritative-looking answer naming a different owner, and **#374
was in both.**

```
role:X              THE QUEUE. Authoritative for routing, always.
dev:N + role:DEV    THE ADDRESS within that queue.
dev:N + any other   PROVENANCE — which pane the content came from.
                    ⛔ NOT an assignment. No pane should act on it.
dev:N + no role:    invisible to every role query. Report it; do not act on it.
```

★ **`role:DEV` is the exception for a measured reason, not a carve-out.** DEV is the **only**
subdivided role — there is no `dx:N`, no `architect:N`, no `devops:N`. ⇒ For every one-pane role
`role:X` **is** the address; **`role:DEV` stopped being an address when DEV was split into five, and
the label did not change.** (Measured by DEV5 on #489.)

#### ⇒ The measurement that picks PROVENANCE over the alternatives

Of the 15 open issues carrying a `dev:N` beside a non-`role:DEV` role, on 2026-08-21:

```
dev:N names the pane that FILED it            11 of 15   (read from each body's self-naming)
dev:N names the pane the content is ABOUT      1         (#271 — a capture OF DEV3, promoted by TEAMLEAD)
dev:N disagrees with the filer                 1         (#282 — filed by DEV3, labelled dev:2)
filer not determinable from the body           2
issues containing assignment language          1 of 15   (#268, and it is a section heading)
```

⇒ **Twelve of thirteen determinable cases record where the work came from. None assigns it.**
⚠ **The two undetermined and the one disagreement are not explained away** — #282 in particular is
either a mislabelling or a meaning nobody has stated, and this rule does not settle it.

#### ⛔ Therefore a collision count of ZERO is the wrong target, and driving it there is the defect

**#461's own Done-when says so:** the query can be driven to 0 by stripping labels, which **destroys
the record of which pane produced the work** and reproduces the *"what is mine?"* gap with a
clean-looking board. ⇒ **The 15 are intentional under this rule and stay.**

★ **The one shape that IS a defect is a `dev:N` beside a queue that RESERVES action from panes.**
That already bit: **#319** carried `role:OPERATOR` **and** `dev:2`, so **the board was telling a pane
to work inside a quarantine the operator had reserved.** From the forge's own timeline:

```
2026-08-20T19:11:23Z  labeled   dev:2
2026-08-21T04:25:14Z  labeled   role:OPERATOR   <- the hazard opens here
2026-08-21T04:47:53Z  unlabeled dev:2           <- and closes, 22m39s later
```

⇒ **Checked by `tools/label-precedence.py`**, which reports the four kinds separately and **never a
bare collision count**: exit 1 on a hazard, 0 otherwise, **2 if the forge could not be read.**

⚠ **Its clean run on the live board proves less than it looks like.** `HAZARD 0` today is a board
**already repaired** — the hazard was removed before the tool existed. ⇒ The known-positive is
therefore pinned as a **regression test on #319's real historical labels**, both states of the same
real issue, **not on the current board.**

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

### Each agent gets its own working tree — and the name of that tree is the audit trail

Eight agent panes carry `-w <role>` alongside `-n <ROLE>`. `claude -w` creates a git worktree for the
session and sets the session's `cwd` to it, so every relative path an agent touches is its own.

```json
{ "type": "claude", "title": "DEV1", "env": {"NFORMA_ROLE": "DEV1"}, "args": "-n DEV1 -w dev1" }
```

Without this there is **one working tree and nine agents in it** (#19). Any pane's `git checkout`
rewrites every other pane's files, silently and with no event — so a role prompt is not a fixed input,
`git checkout -b` inherits a peer's unmerged work, and concurrent `DEV` work is not merely unwise but
impossible: the second `DEV` to check out destroys the first's state.

Measured properties, each load-bearing:

- the worktree is cut from **`main`**, not from whatever branch is checked out, so a new agent cannot
  inherit a peer's unmerged work — it never sees it;
- creating one is **additive**: the main tree's HEAD does not move, so it cannot disturb a peer;
- worktrees land in `.claude/worktrees/`, which is gitignored — otherwise each one dirties `git status`
  in every other pane.

⚠ **`TEAMLEAD` deliberately has no `-w`.** It is the integrator: it merges, and it verifies what landed
on `main`. Giving it an isolated tree would isolate it from the thing it exists to check.

★ **The worktree name must be the role**, and this is not cosmetic. A worktree's HEAD reflog lives in
the common `.git`, is readable by every peer, and is **keyed by worktree name** — so `dev1`/`devops`/`dx`
yields a per-actor record of checkouts, which is a per-actor identifier at the VCS layer that #4 says
does not exist at the credential layer. `wt-1`/`wt-2` gives identical isolation and **zero** attribution.
It is one argument, free at creation and impossible to retrofit.

⛔ **The checkout trail is deleted by `git worktree remove`, and the commit trail by `git branch -D`** —
both measured. Today the shared HEAD reflog is the backstop that outlives branch deletion; isolation
namespaces that backstop and then teardown deletes it, so two erasure paths that do not currently
overlap would begin to. Archive `.git/worktrees/<role>/logs/HEAD` before removing a tree, or do not
remove role trees at all and let `git worktree prune` handle genuinely dead ones. (Anything **pushed**
survives on the remote regardless; this is local forensics, not history loss.)

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

  Nor can a recipe launch its way around this. `daintree-assistant` — the built-in agent that
  "creates worktrees, launches runs across your projects, watches their state" — *is* a legal pane
  `type` (`Fi = new Set(["terminal","dev-preview",...Ae])`, where `Ae` is the full 18-entry agent
  list). But its Daintree tools are gated on a `DAINTREE_MCP_TOKEN` minted per session by
  `HelpSessionService`, and a recipe spawn does not go through that service — so an Assistant pane
  launched from a recipe comes up with **no orchestration surface at all**. Supplying a token
  through `env` makes it worse rather than better: an invalid or displaced token causes the pane to
  *refuse to spawn* rather than degrade. Post-launch sequencing therefore requires Daintree
  actions/MCP at `action` tier, which a recipe cannot grant itself.
- **An agent cannot invoke a slash command.** `initialPrompt` is shell-quoted and passed as *argv*
  to the agent CLI, with newlines collapsed to spaces. Slash commands are expanded by the CLI's
  input layer; a model emitting `/rename X` produces text, not an effect. An earlier version of
  this recipe instructed `/rename` and it silently did nothing — which is precisely the
  "check with no execution record" failure the ⚠ note above warns about, committed by the very
  file meant to remove it.

TEAMLEAD is consequently **not** told to gate on the other eight `ROLE-READY` lines.

> ⚠ **CORRECTED.** This paragraph previously gave the reason as *"it cannot read other panes' output
> without the Daintree MCP, so that check would have no execution record from inside the pane."*
> **The premise is false, and it was false when written.** It is true of a pane's *stdout* and false
> of its *transcript*: `~/.claude/projects/*/<sessionId>.jsonl` is readable by every pane with no MCP,
> `tools/fleet-identity.py` already reads peers' assistant text from it, and TEAMLEAD's own cold-start
> inventory was built by parsing peer transcripts **before** this passage was cited as a constraint —
> 14 of 14 readable, measured. Two instruments for the same content; only one of them was barred.
> ⇒ **"A readiness gate is impossible" is retired as a reason and must not be cited again.** The
> correction is recorded rather than silently rewritten, because a reason that was used to justify a
> design decision has to stay visible after it collapses. (#20, #33.)

The decision stands on a different and stronger footing. **Every fact the token asserts is already
readable from substrate, more reliably, without asking the agent** — the role from the session
registry's `name` (written by the owning process), the repo from that row's `cwd`, and the branch
from the `gitBranch` the harness stamps onto the very record carrying the claim. So a gate on the
three assertions would check a self-report against better evidence, and its only reachable negative
is *"the pane never launched"*, which the registry answers directly.

⛔ Measured across the nine-pane fleet: **9 of 9 tokens were true in all three facts, and 9 of 9
bootstraps contained a step with no execution record.** A consumer of the assertions passes every
pane. ⇒ The auditable thing is not what the line claims but the **interval it delimits** — see
`tools/bootstrap-audit.py`, which treats `ROLE-READY` as punctuation closing the bootstrap window
and audits what actually ran inside it. Verifying fleet readiness remains an operator or DEVOPS
action, against the PREFLIGHT checklist and that audit.

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
- `env` **survives** normalization for every pane type, agent and terminal alike. It is the
  only pane field kept unconditionally — which is exactly why identity rides on it rather
  than on `title` (overwritable) or `initialPrompt` (advisory).
- One malformed `env` value drops the **entire pane**, not just that variable.
- `exitBehavior` accepts `keep` / `trash` / `remove`. `restart` appears in the schema but the
  normalizer rejects it.
- `initialPrompt` supports `{{issue_number}}`, `{{pr_number}}`, `{{number}}`, `{{worktree_path}}`,
  and `{{branch_name}}`, resolved at launch.
- Launch flags are not set here: `--dangerously-skip-permissions` is already configured globally
  for the `claude` agent in Daintree's settings, and duplicating it would create a second place to
  keep in sync.
