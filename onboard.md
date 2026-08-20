# nForma-NEXT — Agent Onboarding Instructions

> **You are a coding agent.** The user gave you this file so you can install the nForma agent
> fleet into their repository. Follow the steps below. Be conversational, concise, and **always
> ask before running commands**.

---

## ⛔ This sequence must be IDEMPOTENT. Running it twice must change nothing the second time.

**Every step checks whether it has already run, before it acts.** An install gets re-run whenever
someone is unsure it finished — which is exactly when a destructive step does its damage.

| step | the check that makes it safe to repeat |
|---|---|
| 2 copy | ⛔ **absent files only. NEVER overwrite.** A second run would put this estate's goal files back over the ones you re-scoped in step 3 — reverting them to `scope: FOREIGN`, and reporting success |
| 3 re-scope | a file already declaring **this** repo is DONE — verify and skip |
| 5 tree | a clean tree needs nothing |
| 6 worktrees | the no-argument form REPORTS; `create` makes only the missing. ⚠ `create` against a role whose tree is in the wrong place gives it a **second** tree |
| 7 preflight | read-only by construction |

★ The rule this repository already uses for exactly this: *read the file first; if it is already in
the target state, **verify and stop — do not act.*** ⇒ **Report "already present, skipped" as a
result.** A silent skip and a step that ran produce the same output otherwise.

---

## What is nForma-NEXT?

**An operating discipline for autonomous agent fleets, and a launcher for one.** This repository
has no application code — its artifacts *are* the product: role prompts (`TEAMLEAD` `ARCHITECT`
`DEVOPS` `DX` `DEV`), standing goals, fleet instruments, and the Daintree recipe that launches all
of them into one workspace.

⛔ **The single convention to carry into everything below:** `exit 2` means *"established
nothing"* and must **never** be read as *"all clear"*. Most of what follows is about not confusing
silence with success.

---

## Step 1: Detect everything

Run this one diagnostic from the root of the repository you are installing into.

```bash
python3 << 'NF_DETECT'
import json, os, glob, shutil
H = os.path.expanduser("~")
r = {"daintree": {}, "mcp": {}, "target": {}}

# Daintree reads recipes IN-REPO. ~/.daintree holds only the control socket.
r["daintree"]["control_socket"] = os.path.exists(f"{H}/.daintree/cli.sock")
r["daintree"]["control_json"]   = os.path.exists(f"{H}/.daintree/cli-control.json")

# The Daintree MCP is what lets an orchestrator pane set ANOTHER pane's goal.
srv = {}
if os.path.exists(f"{H}/.claude.json"):
    try: srv = (json.load(open(f"{H}/.claude.json")).get("mcpServers") or {})
    except Exception: srv = {}
d = srv.get("daintree")
r["mcp"]["configured"] = bool(d)
r["mcp"]["url"] = (d or {}).get("url")

# The repository being onboarded
r["target"]["is_git_repo"] = os.path.exists(".git")
r["target"]["recipes"]     = sorted(glob.glob(".daintree/recipes/*.json"))
r["target"]["validator"]   = os.path.exists("scripts/validate-recipe.py")
r["target"]["prompts"]     = sorted(os.path.basename(p) for p in glob.glob("prompts/*.md"))
r["target"]["goals"]       = len(glob.glob("goals/*.md"))
r["target"]["git"]         = bool(shutil.which("git"))
r["target"]["gh"]          = bool(shutil.which("gh"))
print(json.dumps(r, indent=2))
NF_DETECT
```

**Read the result before doing anything.** If `daintree.control_socket` is false, the Daintree app
is not running — installing the recipe still works, but nothing can launch it yet. If
`mcp.configured` is false, note it: **without the MCP, an orchestrator pane cannot set another
pane's goal**, and the fleet degrades to panes that answer one message and then idle.

---

## Step 2: Install seven things, not one — every later step invokes one of them

From `https://github.com/nForma-AI/nForma-NEXT` — ⛔ **absent files only, never overwriting:**

```bash
[ -e "$dst" ] && echo "  skip (present): $dst" || cp "$src" "$dst"
```

| copy | to | why |
|---|---|---|
| `.daintree/recipes/nforma-fleet.json` | `.daintree/recipes/` | the launcher. **Daintree reads it in-repo — never from `~/.daintree`.** |
| `prompts/*.md` | `prompts/` | every pane's `NFORMA_ROLE_PROMPT` must resolve to a real file |
| `scripts/validate-recipe.py` | `scripts/` | ⛔ **step 4 runs this. Without it, step 4 establishes nothing.** |
| `goals/*.md` | `goals/` | a pane with no standing goal idles after one message |
| `scripts/fleet-worktree.sh` | `scripts/` | ⛔ **step 6 runs this.** Without it every pane shares one tree |
| `scripts/fleet-preflight.sh` | `scripts/` | ⛔ **step 7 runs this. It is the acceptance test for the whole install** |
| `scripts/check-*.py` | `scripts/` | the preflight invokes them; missing ones make it report less than it appears to |

**Adapt the recipe to this repo:** role names, `NFORMA_ROLE_PROMPT` paths, pane count. **Keep the
shape.**

---

## Step 3: Re-scope every goal file, or `check-goal-conformance.py` will correctly refuse them

Each file in `goals/` carries a declaration naming the repository it was written **for**:

```
**Repository:** /path/to/nForma-NEXT → github.com/nForma-AI/nForma-NEXT
```

⇒ Copied unchanged into another repository, that line makes the file **vendored**, and the checker
reports `⛔ scope: FOREIGN — declares nforma-ai/nforma-next, this repo is <yours>`.

★ **That FAIL is the discriminator working, not breaking.** It exists because three of four goal
files here were once scoped to a different product and a presence test passed anyway — a file can
be *specimen* and *doctrine* at once with nothing to tell them apart. **Do not silence it.**

**Fix each file you keep** — rewrite the `**Repository:**` line to this repo — **and delete the
ones you do not.**

⚠ **Idempotent:** a file already declaring this repo is **done — skip it and say so.** Re-running
this step must not rewrite a line that is already correct. A goal file you neither re-scoped nor deleted is a standing objective pointing
at someone else's estate.

```bash
grep -n '^\*\*Repository:\*\*' goals/*.md      # every line here must name THIS repo
```

⚠ The same applies to `prompts/*.md` if they name a repository in their text, and to
`tools/README.md` if you bring instruments across — a tool index inherited from another estate
will report **your** tools as unindexed.

### ⛔ The one mistake that costs the most

```json
"args": "-n DEV1"            ✅ correct
"args": ["-n", "DEV1"]       ⛔ schema-valid, loads with NO error, SILENTLY DISCARDS THE PANE
```

The list form was approved once in this repository and would have deleted **nine panes at once
while reporting success.**

---

## Step 4: Validate — and never read silence as success

```bash
test -f scripts/validate-recipe.py || echo "⛔ VALIDATOR ABSENT — this step established nothing"
python3 scripts/validate-recipe.py .daintree/recipes/*.json ; echo "exit=$?"
```

⚠ **Read the exit code without a pipe.** `| tail` returns tail's status, not the validator's — a
defect measured six times across four roles in one session here.

**Why a validator at all:** Daintree's normalizer returns a fixed field set. **Schema-valid fields
are silently dropped; malformed ones silently drop the whole pane.** A recipe can be 100% valid
JSON, load without a single error, and still not do what it says.

Then assert the rest, **printing each count rather than asserting it passed**:

```bash
python3 << 'NF_ASSERT'
import json, glob, os
for f in glob.glob(".daintree/recipes/*.json"):
    t = json.load(open(f))["terminals"]
    agents = [x for x in t if x.get("type") == "claude"]
    print(f, len(t), "panes,", len(agents), "agent panes")
    assert all(isinstance(x.get("args"), str) for x in agents), "args must be a STRING"
    assert all(x.get("initialPrompt") for x in agents), "every agent pane needs an initialPrompt"
    for x in agents:
        pr = (x.get("env") or {}).get("NFORMA_ROLE_PROMPT")
        assert pr and os.path.exists(pr), f"missing prompt file: {pr}"
    print("  NFORMA_GOAL set on", sum(1 for x in agents if (x.get("env") or {}).get("NFORMA_GOAL")), "of", len(agents))
    print("  panes with their own cwd/worktree:", sum(1 for x in t if x.get("cwd") or x.get("worktree")))
NF_ASSERT
```

---

## Step 5: Commit or stash the working tree BEFORE any pane starts

```bash
git status --porcelain | head
```

⇒ A dirty tree is not cosmetic here: **every pane branches from uncommitted state**, and nine
agents branching from one person's half-finished edit produces nine branches nobody can reproduce.
**Resolve it before launch.**

---

## Step 6: Give every role its own worktree — this is not optional

```bash
scripts/fleet-worktree.sh          # REPORT FIRST — every time, including on a re-run
scripts/fleet-worktree.sh create   # then create only the missing ones
```

⚠ **Run the report form first, always.** `create` is safe for a role with no tree and **harmful for
a role whose tree is in the wrong place** — see below.

⛔ **The reference recipe declares `cwd` on 0 of 10 panes**, so without this every agent works in
one shared tree — and **a `git checkout` in any pane rewrites every other pane's files, including
the role prompts they are operating on.** Measured on a real install: **8 of 8 roles had no
isolated tree.**

⚠ If a role already has a tree in the wrong place, the script says **MOVE it — do not run
`create`**, which would give that role a second tree with commits landing in whichever one it
happens to be in. **Read its output; do not just run `create`.**

---

## Step 7: Run the preflight. It is the acceptance test, not a formality.

```bash
scripts/fleet-preflight.sh
```

**Every `FAIL` must be resolved or explicitly accepted in your report to the user.** Do not
proceed to launch with unexplained FAILs.

### ⛔ Two warnings you must NOT try to "fix"

| the preflight says | why it is correct |
|---|---|
| *"this pane cannot read another pane's environment: the nine `ROLE-READY` lines are self-reports, not measurements"* | **True and load-bearing.** Nine `ROLE-READY` lines are nine *claims*. On a real bootstrap here, **6 of 6 panes reported ROLE-READY for a bootstrap that had failed at step 1.** Treat a silent pane as *unverified*, which is the same as unknown — never as "still starting". |
| *"titles NOT pinned (`titleMode != user`)"* | Real, and **not fixable from inside a pane**: a model emitting `/rename X` produces text, not an effect. Auto-titling can overwrite the role names the recipe set. **Report it; the operator pins titles in the UI.** |

### What a FAIL usually means on a fresh install

- **`check-goal-conformance` → `scope: FOREIGN`** ⇒ you skipped step 3. **The checker is right.**
- **`check-tools-index` → no row for `<your own tools>`** ⇒ you inherited this estate's tool index
  and it does not know your instruments. Add rows or scope the checker to yours.
- **worktree FAILs** ⇒ step 6.

---

## Step 8: Report as counts, never as "done"

Tell the user, as numbers:

    panes / agent panes ............ from step 4
    prompt files resolved .......... from step 4
    NFORMA_GOAL coverage ........... n of m   (reference recipe ships 1 of 9)
    validator exit code ............ from step 4
    goal files re-scoped ........... n of m   (step 3)
    roles with their own worktree .. n of m   (step 6)
    preflight FAILs ................ n, each one named and resolved-or-accepted
    Daintree MCP configured ........ yes/no   (no ⇒ nobody can set another pane's goal)
    steps SKIPPED as already-done .. name them — otherwise a silent skip and a
                                     step that ran are the same output

⛔ **Do not report success from the validator's silence.** Report the number it printed. If a step
could not run, say *"this established nothing"* rather than omitting it — an unrun check and a
passing one are otherwise the same silence, and that is the defect this entire repository exists
to catch.
