#!/usr/bin/env bash
# Deterministic fleet preflight. No agent in the loop.
#
# Launched as pane 10 of .daintree/recipes/nforma-fleet.json. Its job is to
# establish, by execution rather than by assertion, the facts the nine agent
# panes will each *claim* in their ROLE-READY line — so those claims have
# something to be checked against.
#
# Exit code is always 0: this pane reports, it does not gate.

ROLES=(TEAMLEAD ARCHITECT DEVOPS DX DEV1 DEV2 DEV3 DEV4 DEV5)

pass=0; fail=0; warn=0
ok()   { printf '  \033[32mok\033[0m    %s\n' "$1"; pass=$((pass+1)); }
bad()  { printf '  \033[31mFAIL\033[0m  %s\n' "$1"; fail=$((fail+1)); }
note() { printf '  \033[33mwarn\033[0m  %s\n' "$1"; warn=$((warn+1)); }
section() { printf '\n\033[1m%s\033[0m\n' "$1"; }

printf '\033[1mnForma fleet preflight\033[0m  —  %s\n' "$(date '+%Y-%m-%d %H:%M:%S')"

section 'Workspace'
# ⛔ This pane measures ONE tree. Under the per-role worktree isolation of #19
# there are ten, and a single-tree result reported as a fleet result is a
# wrong-population instrument by construction — the exact defect this repo
# files issues about. So state which tree was measured, enumerate the others,
# and never let their absence read as their health.
if ! toplevel=$(git rev-parse --show-toplevel 2>/dev/null); then
  bad "not inside a git repository (cwd: $PWD)"
  toplevel=""; repo=""; branch=""
else
  # ⛔ NOT basename "$toplevel" — in a worktree that is the worktree's directory
  # name ("devops"), not the repository ("nForma-NEXT"). The main tree is always
  # the first entry of `git worktree list --porcelain`.
  main_tree=$(git worktree list --porcelain 2>/dev/null | awk '/^worktree /{print $2; exit}')
  repo=$(basename "${main_tree:-$toplevel}")
  branch=$(git branch --show-current 2>/dev/null)
  ok "repo=$repo branch=${branch:-<detached>} — THIS TREE ONLY"
  ok "toplevel=$toplevel"
  if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
    note "working tree is dirty — agents will branch from uncommitted state"
  else
    ok "working tree clean"
  fi

  # Scope declaration. Not decoration: it is what stops the reader generalising.
  wt_count=$(git worktree list --porcelain 2>/dev/null | grep -c '^worktree ')
  if [ "${wt_count:-1}" -gt 1 ]; then
    note "$wt_count worktrees exist; this preflight measured 1 of them"
    git worktree list 2>/dev/null | sed 's/^/        /'
    note "the other $((wt_count-1)) are UNMEASURED, not clean — no pane here can see them"
  else
    ok "single working tree — every agent shares it"
    note "shared tree: any pane's 'git checkout' rewrites every other pane's files (#19)"
  fi
fi

section 'Role prompts'
for f in TEAMLEAD ARCHITECT DEVOPS DX DEV; do
  p="prompts/$f.md"
  if [ -r "$p" ]; then
    ok "$(printf '%-14s' "$p") $(wc -l < "$p" | tr -d ' ') lines"
  else
    bad "$p missing or unreadable — the pane that needs it will start roleless"
  fi
done

section 'Tooling'
for bin in git gh claude; do
  if command -v "$bin" >/dev/null 2>&1; then
    ok "$(printf '%-7s' "$bin") $(command -v "$bin")"
  else
    bad "$bin not on PATH"
  fi
done
if command -v gh >/dev/null 2>&1; then
  if gh auth status >/dev/null 2>&1; then
    ok "gh authenticated"
  else
    note "gh present but not authenticated — GitHub is the team's durable memory (see prompts/README.md)"
  fi
fi

section "Expected roster (${#ROLES[@]} agent panes)"
echo '  Each pane below must print exactly one ROLE-READY line. Check them off'
echo '  against this list. A pane that is silent is not "still starting" — it is'
echo '  unverified, which is the same thing as unknown.'
echo
for r in "${ROLES[@]}"; do
  case "$r" in
    DEV[0-9]*) src='prompts/DEV.md' ;;
    *)    src="prompts/$r.md" ;;
  esac
  printf '    [ ] ROLE-READY %-10s repo=%s branch=%s      (%s)\n' \
    "$r" "${repo:-?}" "${branch:-?}" "$src"
done

section 'Panel identity (measured, not asserted)'
# ⛔ This section exists because the prose it replaces was FALSE against the live
# fleet and an orchestrator believed it: it stated recipe-set titles are unpinned,
# a reader generalised that to "titles are unpinned", and explained a stale pane
# name as auto-titling overwriting a panel. Both halves were wrong — the titles
# were pinned and the session was dead. An instrument asserting a substrate fact
# in an operator-facing readout must measure it or say it did not.
if ! command -v python3 >/dev/null 2>&1; then
  note "python3 not on PATH — panel titles UNMEASURED, not verified"
else
  python3 - "${main_tree:-$toplevel}" <<'PANELS'
import glob, json, os, sys, time
top = sys.argv[1] if len(sys.argv) > 1 else ""
base = os.path.expanduser("~/Library/Application Support/Daintree/projects")
found, mtime = {}, None
for path in glob.glob(os.path.join(base, "*", "state.json")):
    try:
        doc = json.load(open(path))
    except Exception:
        continue
    panes = [t for t in doc.get("terminals", []) if t.get("cwd") == top]
    if not panes:
        continue
    mtime = os.path.getmtime(path)
    for t in panes:
        if t.get("title"):
            found[t["title"]] = t.get("titleMode")
if not found:
    print("  \033[33mwarn\033[0m  no Daintree project state for this repo — "
          "panel titles UNMEASURED, not verified")
    sys.exit(0)
stamp = time.strftime("%H:%M:%S", time.localtime(mtime))
print(f"  \033[32mok\033[0m    {len(found)} panes in Daintree state, read {stamp} "
      f"(persisted view — it can lag the live UI)")
roles = ["TEAMLEAD", "ARCHITECT", "DEVOPS", "DX", "DEV1", "DEV2", "DEV3", "DEV4", "DEV5"]
missing = [r for r in roles if r not in found]
loose = sorted(t for t, m in found.items() if m != "user")
if missing:
    print(f"  \033[31mFAIL\033[0m  roles with no panel: {', '.join(missing)}")
else:
    print("  \033[32mok\033[0m    every declared role has a panel")
if loose:
    print(f"  \033[33mwarn\033[0m  titles NOT pinned (titleMode != user, auto-titling may "
          f"overwrite): {', '.join(loose)}")
else:
    print("  \033[32mok\033[0m    every title pinned (titleMode=user)")
PANELS
fi

# ⚠ The companion half of the same claim. "$NFORMA_ROLE is the authoritative
# identity" is true only WHEN IT IS SET, and it was empty in every pane of the
# fleet that first shipped it — so the readout pointed the operator at an
# authority that did not exist while dismissing one that did.
if [ -n "${NFORMA_ROLE:-}" ]; then
  ok "\$NFORMA_ROLE=$NFORMA_ROLE in this pane — env carrier is live here"
else
  note "\$NFORMA_ROLE is EMPTY in this pane — the env carrier is NOT established here"
fi
note "this pane cannot read another pane's environment: the nine ROLE-READY lines are self-reports, not measurements"

section 'Worktree coverage'
# ★ Partial isolation CONCENTRATES the hazard rather than reducing it
# proportionally: the shared tree gets quieter, so a collision there becomes
# less EXPECTED rather than less likely, and the uncovered roles become the only
# remaining source of exactly the failure isolation was built to remove — in a
# tree nobody is watching any more. Measured: a role with no tree hit the
# shared-tree hazard forty minutes after filing the issue about it.
if [ -x scripts/fleet-worktree.sh ]; then
  if scripts/fleet-worktree.sh check >/dev/null 2>&1; then
    ok "every declared role has an isolated worktree"
  else
    scripts/fleet-worktree.sh check 2>&1 | while read -r st r pa rest; do
      case "$st" in
        MISSING) bad  "$r has NO isolated tree — it works in the SHARED tree; run fleet-worktree.sh create" ;;
        OUTSIDE) bad  "$r isolated OUTSIDE the convention at $pa — MOVE it; creating would duplicate it" ;;
        DUP)     note "$r has TWO trees ($pa $rest) — commits land in whichever the pane is in; needs a deliberate decision" ;;
      esac
    done
  fi
else
  note "scripts/fleet-worktree.sh not executable — worktree coverage UNMEASURED, not clean"
fi

section 'Known substrate limits'
cat <<'LIMITS'
  · Recipes have no `titleMode` field, so a recipe-set title starts unpinned and
    agent auto-titling may overwrite it. ⚠ That is a claim about recipe-set
    titles ONLY — a human rename pins the title afterwards. This readout no
    longer asserts which case holds; see "Panel identity" above, which MEASURES
    it. An earlier version stated the unpinned case unconditionally, was false
    against a live fleet whose nine panes all read titleMode "user", and an
    orchestrator built a wrong attribution on it.
  · A recipe cannot sequence: all 10 panes spawn concurrently via
    Promise.allSettled. There is no ordering and no inter-pane dependency.
    A daintree-assistant pane does not solve this — it is a legal pane type,
    but launched from a recipe it has no MCP token and so no orchestration
    tools at all.
  · initialPrompt newlines are collapsed to spaces before the prompt is passed
    as argv, and slash commands cannot be invoked by an agent at all.
LIMITS

section 'Summary'
printf '  %d ok, %d warn, %d fail\n' "$pass" "$warn" "$fail"
if [ "$fail" -gt 0 ]; then
  printf '  \033[31mPreflight found blocking problems. Fix them before trusting the fleet.\033[0m\n'
else
  printf '  \033[32mPreflight clean. Now verify the %d ROLE-READY lines above.\033[0m\n' "${#ROLES[@]}"
fi
echo
exit 0
