#!/usr/bin/env bash
# Prove the NODOCTRINE state DISCRIMINATES, and that `create <ref>` honours the ref.
#
# ⛔ The defect this covers is a tree that EXISTS, sits in the conventional
# location, and carries none of the doctrine. Every path-shaped check passed it,
# and every pane launched into it died on `cat $NFORMA_ROLE_PROMPT`.
#
# ★ Both states are constructed here. A test that only ever sees the empty tree
# cannot tell "detects a missing doctrine" from "always says NODOCTRINE", and the
# whole point of the state is that it distinguishes two trees a path check cannot.
#
# Exit: 0 every case behaved as specified · 1 otherwise

SCRIPT="$(cd "$(dirname "$0")" && pwd)/fleet-worktree.sh"
[ -f "$SCRIPT" ] || { echo "⛔ VOID: $SCRIPT absent — this test established nothing"; exit 1; }

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
failures=0

say() { printf '\n--- %s\n' "$1"; }
check() { # $1=label $2=expected $3=actual
  if [ "$2" = "$3" ]; then printf '    PASS  %s (got %s)\n' "$1" "$3"
  else printf '    ⛔ FAIL %s — expected %s, got %s\n' "$1" "$2" "$3"; failures=$((failures+1)); fi
}

# ── a repository with TWO commits: one before the doctrine, one after ────────
REPO="$WORK/repo"
mkdir -p "$REPO" && cd "$REPO" || exit 1
git init -q -b main .
git config user.email t@t; git config user.name t
echo x > README.md && git add -A && git commit -qm "before the doctrine"
BEFORE=$(git rev-parse HEAD)
mkdir -p prompts goals && echo "ARCHITECT doctrine" > prompts/ARCHITECT.md \
  && echo "g" > goals/x.md && git add -A && git commit -qm "vendor the fleet"
AFTER=$(git rev-parse HEAD)
printf 'repo: %s\n  before=%s  after=%s\n' "$REPO" "${BEFORE:0:8}" "${AFTER:0:8}"

WT=".claude/worktrees"

# ── case 1: tree built from the ref that PREDATES the doctrine ───────────────
say "case 1: tree at the conventional path, built from a ref with no prompts/"
git worktree add --detach "$WT/architect" "$BEFORE" >/dev/null 2>&1
out=$(bash "$SCRIPT" check 2>&1); rc=$?
echo "$out" | grep -qE '^\s+NODOCTRINE\s+architect' && got=NODOCTRINE || got=$(echo "$out" | awk '/architect/{print $1; exit}')
check "state for architect" "NODOCTRINE" "$got"
check "check exit code" "1" "$rc"
echo "$out" | grep -q 'dies on' && printf '    PASS  names the consequence, not just the state\n' \
  || { printf '    ⛔ FAIL no remedy text\n'; failures=$((failures+1)); }

# ── case 2: same path, tree built from the ref that CARRIES the doctrine ─────
say "case 2: same path, built from a ref that carries prompts/"
git worktree remove --force "$WT/architect" >/dev/null 2>&1
git worktree add --detach "$WT/architect" "$AFTER" >/dev/null 2>&1
out=$(bash "$SCRIPT" check 2>&1)
got=$(echo "$out" | awk '/architect/{print $1; exit}')
check "state for architect" "ok" "$got"

# ── case 3: create honours an explicit local ref ─────────────────────────────
say "case 3: create <ref> builds from the ref it is given, not origin/main"
git worktree remove --force "$WT/architect" >/dev/null 2>&1
out=$(bash "$SCRIPT" create "$AFTER" 2>&1); rc=$?
built=$(git -C "$WT/devops" rev-parse HEAD 2>/dev/null)
check "devops built at the requested ref" "$AFTER" "$built"
check "create exit code" "0" "$rc"
echo "$out" | grep -q 'NO prompts/ AT THIS REF' \
  && { printf '    ⛔ FAIL flagged a good ref as doctrine-less\n'; failures=$((failures+1)); } \
  || printf '    PASS  a good ref is not flagged\n'

# ── case 4: create against a doctrine-less ref REPORTS it and exits non-zero ─
say "case 4: create against a ref with no prompts/ must not report success"
for r in architect devops dx dev1 dev2 dev3 dev4 dev5; do
  git worktree remove --force "$WT/$r" >/dev/null 2>&1
done
out=$(bash "$SCRIPT" create "$BEFORE" 2>&1); rc=$?
echo "$out" | grep -q 'NO prompts/ AT THIS REF' && got=flagged || got=silent
check "doctrine-less ref is flagged" "flagged" "$got"
check "create exit code" "1" "$rc"

# ── case 5: a ref that does not resolve is refused, not guessed at ───────────
# ⚠ The trees from case 4 must go first. With none missing, `create` short-circuits
# on "nothing to create" and exits 0 BEFORE validating the ref — correct behaviour
# (nothing was built, so a bad ref harmed nothing), but it means this case measures
# the early return rather than the ref check unless the trees are cleared.
say "case 5: an unresolvable ref is refused"
for r in architect devops dx dev1 dev2 dev3 dev4 dev5; do
  git worktree remove --force "$WT/$r" >/dev/null 2>&1
done
out=$(bash "$SCRIPT" create refs/heads/nope 2>&1); rc=$?
echo "$out" | grep -q 'does not resolve' && got=refused || got=other
check "unresolvable ref refused" "refused" "$got"
check "exit code" "2" "$rc"

printf '\n'
if [ "$failures" -eq 0 ]; then echo "all cases behaved as specified — the state discriminates."
else echo "⛔ $failures assertion(s) failed."; fi
exit "$failures"
