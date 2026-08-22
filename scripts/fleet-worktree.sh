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
#
# ⚠ bash 3.2 compatible: macOS ships /bin/bash 3.2, which has no associative
# arrays. An earlier revision used `declare -A`, printed usage errors, and STILL
# EXITED 0 — an entrypoint that could not fail, in the script written against
# checks that cannot fail. Keep it POSIX-ish.
set -u

ROLES="architect devops dx dev1 dev2 dev3 dev4 dev5"

main_tree=$(git worktree list --porcelain 2>/dev/null | awk '/^worktree /{print $2; exit}')
[ -n "$main_tree" ] || { echo "not inside a git repository" >&2; exit 2; }
WT_DIR="$main_tree/.claude/worktrees"

# ⛔ THREE STATES, because there are three remediations.
#
# An earlier version tested BASENAME while its header claimed LOCATION: a tree at
# /tmp/dev1 satisfied coverage for dev1 under a heading asserting the tree lived
# in .claude/worktrees. The displayed proposition and the tested one were
# different, and the location half had NO REACHABLE FAILING STATE, because
# nothing in the script read a location.
#
# Measured instance: DEV5 was isolated AND attributable — its `.git/worktrees/`
# key `wt-dev5` preserves the per-actor trail — and INVISIBLE to a coverage check
# keyed on the conventional directory, because its tree sat in a scratchpad.
#
# ⚠ Name and location are load-bearing for DIFFERENT CONSUMERS: the name serves
# the audit trail, the location serves the coverage check. A role can satisfy one
# and fail the other. Collapsing OUTSIDE into MISSING applies the wrong remedy —
# `create` would give that role a SECOND tree, with commits landing in whichever
# it happened to be in and no signal either way.
#
#   ok       conventional tree at $WT_DIR/<role>
#   OUTSIDE  a tree that looks like this role's, elsewhere   -> move it
#   MISSING  no tree at all                                  -> create it
where() {
  git worktree list --porcelain | awk -v want="$WT_DIR/$1" -v role="$1" '
    /^worktree /{ p = $2
      if (p == want) { found = 1; next }
      # HEURISTIC, and it is one: a path whose last element contains the role
      # token is PROBABLY that tree. Nothing binds a worktree to a role, so this
      # can only ever be a hint - reported as OUTSIDE for a human to judge, and
      # never auto-remediated.
      n = split(p, a, "/"); if (index(a[n], role)) { out = p }
    }
    END {
      if (found && out != "") { print "DUP\t" want " + " out }
      else if (found)         { print "ok\t" want }
      else if (out != "")     { print "OUTSIDE\t" out }
      else                    { print "MISSING\t-" }
    }'
}

n_missing=0; n_outside=0; n_dup=0; missing_list=""; outside_list=""; dup_list=""
report=""
for r in $ROLES; do
  line=$(where "$r")
  st=${line%%	*}; pa=${line#*	}
  report="$report$(printf '  %-8s %-10s %s' "$st" "$r" "$pa")
"
  case "$st" in
    MISSING) n_missing=$((n_missing+1)); missing_list="$missing_list $r" ;;
    OUTSIDE) n_outside=$((n_outside+1)); outside_list="$outside_list $r" ;;
    DUP)     n_dup=$((n_dup+1));     dup_list="$dup_list $r" ;;
  esac
done

case "${1:-check}" in
check)
  # Emit the RESOLVED PATH per role, not a verdict. A predicate that prints
  # true/false where it could print the evidence gives its reader nothing to be
  # suspicious of — which is exactly how the basename/location mismatch above
  # survived authoring.
  printf 'conventional location: %s\n' "$WT_DIR"
  printf '%s' "$report"
  # ⛔ TWO PREDICATES, TWO PROPOSITIONS, AND THEY CURRENTLY DISAGREE.
  #
  # An earlier revision of this block said occupancy was NOT MEASURABLE from
  # outside. That is falsified. It measured SESSION cwd, found every pane under the
  # main tree, and attached a cwd reading to an occupancy claim.
  #
  #   session cwd    would a `git checkout` HERE move files under other panes?
  #                  -> YES, fleet-wide. All 8 agent panes launched in the main tree.
  #   worktree HEAD  are agents doing their work in ISOLATION?
  #                  -> YES. 9 of 10 role worktrees sit on a role-named branch.
  #
  # ⚠ NEITHER PREDICATE IS BROKEN. Agents `cd` per commit, so cwd answers "where was
  # this session STARTED", never "where is this agent WORKING" — and a worktree on a
  # role-named branch is positive evidence that work happened there. The defect was
  # attaching one measurement to the other proposition.
  #
  # ⇒ This script already reads HEAD. It had the right instrument before anyone had
  # the right question, which is why the fix is a sentence and not a rewrite.
  #
  # ⛔ What remains true, and is the part worth printing: a role worktree existing
  # does not stop any pane from working in the shared tree, and the #19 hazard lives
  # there. Provisioning is necessary and not sufficient.
  printf '\n⚠ These states are PROVISIONING. Occupancy is a different question and is\n'
  printf '  answerable — by worktree HEAD, not by session cwd: a role tree sitting on a\n'
  printf '  role-named branch is evidence that work happened in it.\n'
  printf '  ⇒ But provisioning does not PREVENT a pane working in the shared tree, and\n'
  printf '    a `git checkout` there still rewrites every other pane files. The #19\n'
  printf '    hazard lives in that gap, not in whether a tree exists.\n'
  if [ "$n_outside" -gt 0 ]; then
    printf '\n⚠ %d role(s) isolated OUTSIDE the conventional location:%s\n' "$n_outside" "$outside_list"
    printf '  Attributable but invisible to any check keyed on that directory.\n'
    printf '  MOVE it — do NOT run `create`, which would give the role a second tree.\n'
  fi
  if [ "$n_dup" -gt 0 ]; then
    printf '\n⚠ %d role(s) have TWO trees:%s\n' "$n_dup" "$dup_list"
    printf '  Commits land in whichever the pane happens to be in, with no signal either way.\n'
    printf '  Needs a deliberate decision, not tidying by whoever notices.\n'
  fi
  if [ "$n_missing" -gt 0 ]; then
    printf '\n⚠ %d role(s) have NO isolated tree:%s\n' "$n_missing" "$missing_list"
    # ★ Partial isolation CONCENTRATES the hazard rather than reducing it
    # proportionally: the shared tree gets quieter, so a collision there becomes
    # less EXPECTED rather than less likely, and the uncovered roles become the
    # only remaining source of exactly the failure isolation was built to remove
    # — in a tree nobody is watching any more.
    printf '  They work in the SHARED tree, where a collision is now less expected\n'
    printf '  rather than less likely. Run: %s create\n' "$0"
  fi
  [ "$n_missing" -gt 0 ] || [ "$n_outside" -gt 0 ] || [ "$n_dup" -gt 0 ] && exit 1
  printf '\nall roles provisioned in the conventional location\n'

  ;;
create)
  if [ "$n_missing" -eq 0 ]; then
    printf 'nothing to create — no role is without a tree\n'
    [ "$n_outside" -gt 0 ] && printf '⚠ but%s sit outside %s; MOVE those, creating would duplicate them\n' \
      "$outside_list" "$WT_DIR"
    exit 0
  fi
  # Detached at origin/main on purpose: it claims no branch name, so it cannot
  # collide with a role's own branch, and `git checkout -b` from it inherits main
  # rather than a peer's unmerged work — the failure this whole line started from.
  git fetch -q origin || { echo "fetch failed — refusing to create trees from a stale base" >&2; exit 2; }
  rc=0
  for r in $missing_list; do
    p="$WT_DIR/$r"
    if git worktree add --detach "$p" origin/main >/dev/null 2>&1; then
      printf '  created %-10s detached at %s\n' "$r" "$(git -C "$p" rev-parse --short HEAD)"
    else
      printf '  FAILED  %-10s (path in use, or origin/main unreachable)\n' "$r"; rc=1
    fi
  done
  printf '\nnext, INSIDE your tree: cd %s/<role> || exit 1\n' "$WT_DIR"
  printf '                        git checkout -b <role>/<topic>\n'
  exit $rc
  ;;
*)
  echo "usage: $0 [check|create]" >&2; exit 2 ;;
esac
