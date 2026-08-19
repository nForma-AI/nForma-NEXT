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

section 'Known substrate limits'
cat <<'LIMITS'
  · Panel titles set by a recipe are NOT pinned (titleMode defaults to
    "default"), so agent auto-titling may overwrite them after launch. The
    authoritative identity is $NFORMA_ROLE inside each pane, not the tab label.
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
