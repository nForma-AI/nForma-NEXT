# nForma-NEXT — Agent Onboarding Instructions

> **You are a coding agent.** The user gave you this file so you can install the nForma agent
> fleet into their repository. Follow the steps below. Be conversational, concise, and **always
> ask before running commands**.

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

## Step 2: Install four things, not one

From `https://github.com/nForma-AI/nForma-NEXT`:

| copy | to | why |
|---|---|---|
| `.daintree/recipes/nforma-fleet.json` | `.daintree/recipes/` | the launcher. **Daintree reads it in-repo — never from `~/.daintree`.** |
| `prompts/*.md` | `prompts/` | every pane's `NFORMA_ROLE_PROMPT` must resolve to a real file |
| `scripts/validate-recipe.py` | `scripts/` | ⛔ **step 3 runs this. Without it, step 3 establishes nothing.** |
| `goals/*.md` | `goals/` | optional, but a pane with no standing goal idles after one message |

**Adapt the recipe to this repo:** role names, `NFORMA_ROLE_PROMPT` paths, pane count. **Keep the
shape.**

### ⛔ The one mistake that costs the most

```json
"args": "-n DEV1"            ✅ correct
"args": ["-n", "DEV1"]       ⛔ schema-valid, loads with NO error, SILENTLY DISCARDS THE PANE
```

The list form was approved once in this repository and would have deleted **nine panes at once
while reporting success.**

---

## Step 3: Validate — and never read silence as success

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

## Step 4: Two gaps in the reference recipe — decide each, do not inherit them

Measured on the shipped recipe: **10 panes = 9 agent + 1 `PREFLIGHT` terminal.**

- **`NFORMA_GOAL` is set on 1 of 9 agent panes.** A pane without a standing objective answers its
  first message and then idles — measured here as *4 of 8 sessions consumed context and mutated
  nothing* across half an hour of waking.
- **No pane declares its own `cwd` or worktree**, so all nine share one working tree. ⛔ **A
  `git checkout` in any pane rewrites every other pane's files, including the role prompts they
  are operating on.** Give each pane its own worktree unless you have a reason not to.

---

## Step 5: Report as counts, never as "done"

Tell the user: panes, agent panes, prompt files resolved, `NFORMA_GOAL` coverage, validator exit
code, and whether the Daintree MCP is configured.

⛔ **Do not report success from the validator's silence.** Report the number it printed. If a step
could not run, say *"this established nothing"* rather than omitting it — an unrun check and a
passing one are otherwise the same silence, and that is the defect this entire repository exists
to catch.
