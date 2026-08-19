#!/usr/bin/env bash
# Create or report per-role git worktrees. Built because the hazard recurred.
#
# ⛔ THE INCIDENT THIS EXISTS FOR. A pane tried to add a worktree for its own
# merged PR branch. origin had deleted the branch, so `git worktree add <path>
# <branch>` failed with `invalid reference`. The following `cd` into the
# non-existent path ALSO failed — and did not abort the enclosing `set -e`
# script. The edit, `git add` and `git commit` then all ran in the SHARED tree
# on main, and eight panes carried an unreviewed commit for about two minutes.
#
# ⚠ `set -e` does not abort on a failed `cd` in every shell context. That is a
# guard with no reachable failing state in the shape it was used. Every `cd`
# here is `cd X || exit 1`, explicitly, and never relies on `set -e`.
#
# ★ And the author who hit it had FILED THE ISSUE ABOUT IT FORTY MINUTES EARLIER
# and was actively being careful. A control that fails against an author who is
# watching for it is not a control — which is the argument for this script
# existing rather than for documenting the discipline.
set -u

ROLES=(architect devops dx dev1 dev2 dev3 dev4 dev5)

main_tree=$(git worktree list --porcelain 2>/dev/null | awk '/^worktree /{print $2; exit}')
[ -n "$main_tree" ] || { echo "not inside a git repository" >&2; exit 2; }

have() { git worktree list --porcelain | awk -v n="$1" '/^worktree /{split($2,a,"/"); if (a[length(a)]==n) f=1} END{exit !f}'; }

missing=()
for r in "${ROLES[@]}"; do have "$r" || missing+=("$r"); done

case "${1:-check}" in
check)
  printf 'role worktrees under %s\n' "$main_tree/.claude/worktrees"
  for r in "${ROLES[@]}"; do
    if have "$r"; then printf '  ok      %s\n' "$r"
    else                printf '  MISSING %s\n' "$r"; fi
  done
  if [ ${#missing[@]} -gt 0 ]; then
    printf '\n⚠ %d of %d roles have no isolated tree.\n' "${#missing[@]}" "${#ROLES[@]}"
    # ★ Partial isolation does not reduce the hazard proportionally — it
    # CONCENTRATES it. The shared tree gets quieter, which makes the remaining
    # collisions less EXPECTED rather than less likely, and the uncovered roles
    # become the only remaining source of exactly the failure the mechanism was
    # built to remove — in a tree nobody is watching any more.
    printf '  Those roles work in the SHARED tree, where a collision is now less expected\n'
    printf '  rather than less likely. Run: %s create\n' "$0"
    exit 1
  fi
  printf '\nall %d roles isolated\n' "${#ROLES[@]}"
  ;;
create)
  # Detached at origin/main on purpose: it claims no branch name, so it cannot
  # collide with a role's own branch, and `git checkout -b` from it inherits
  # main rather than a peer's unmerged work.
  git fetch -q origin || { echo "fetch failed — refusing to create trees from a stale base" >&2; exit 2; }
  created=0
  if [ ${#missing[@]} -eq 0 ]; then
    printf '  nothing to create — all %d roles already isolated\n' "${#ROLES[@]}"
    exit 0
  fi
  for r in "${missing[@]}"; do
    p="$main_tree/.claude/worktrees/$r"
    if git worktree add --detach "$p" origin/main >/dev/null 2>&1; then
      printf '  created %-10s detached at %s\n' "$r" "$(git -C "$p" rev-parse --short HEAD)"
      created=$((created+1))
    else
      printf '  FAILED  %-10s (path in use, or origin/main unreachable)\n' "$r"
    fi
  done
  printf '\nnext, INSIDE your tree: cd %s/.claude/worktrees/<role> || exit 1\n' "$main_tree"
  printf '                        git checkout -b <role>/<topic>\n'
  ;;
*)
  echo "usage: $0 [check|create]" >&2; exit 2 ;;
esac
