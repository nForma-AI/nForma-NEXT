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
  # ⛔ The tally file is the ONLY channel by which this block's verdicts reach
  # the counters below. Without it the block printed FAIL and the summary still
  # said "0 fail / Preflight clean" — measured on this repo, all nine roles.
  panel_tally=$(mktemp)
  python3 - "${main_tree:-$toplevel}" "$panel_tally" <<'PANELS'
import glob, json, os, sys, time
top = sys.argv[1] if len(sys.argv) > 1 else ""
tally_path = sys.argv[2] if len(sys.argv) > 2 else ""
n_ok = n_warn = n_fail = 0

# ⚠ These reproduce ok()/note()/bad() from the shell above, spacing included.
# They exist so this block COUNTS what it prints instead of only printing it.
def emit_ok(msg):
    global n_ok
    print(f"  \033[32mok\033[0m    {msg}")
    n_ok += 1

def emit_warn(msg):
    global n_warn
    print(f"  \033[33mwarn\033[0m  {msg}")
    n_warn += 1

def emit_fail(msg):
    global n_fail
    print(f"  \033[31mFAIL\033[0m  {msg}")
    n_fail += 1

def write_tally():
    # ⛔ Every exit path writes this, including the early one. A path that
    # returns without writing is indistinguishable from a crash, and the
    # caller is required to treat a missing tally as a failure.
    if tally_path:
        with open(tally_path, "w") as fh:
            fh.write(f"{n_ok} {n_warn} {n_fail}\n")
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
    emit_warn("no Daintree project state for this repo — "
              "panel titles UNMEASURED, not verified")
    write_tally()
    sys.exit(0)
stamp = time.strftime("%H:%M:%S", time.localtime(mtime))
emit_ok(f"{len(found)} panes in Daintree state, read {stamp} "
        f"(persisted view — it can lag the live UI)")
roles = ["TEAMLEAD", "ARCHITECT", "DEVOPS", "DX", "DEV1", "DEV2", "DEV3", "DEV4", "DEV5"]
missing = [r for r in roles if r not in found]
loose = sorted(t for t, m in found.items() if m != "user")
if missing:
    emit_fail(f"roles with no panel: {', '.join(missing)}")
else:
    emit_ok("every declared role has a panel")
if loose:
    emit_warn(f"titles NOT pinned (titleMode != user, auto-titling may "
              f"overwrite): {', '.join(loose)}")
else:
    emit_ok("every title pinned (titleMode=user)")
write_tally()
sys.exit(1 if n_fail else 0)
PANELS
  panel_rc=$?
  if [ -s "$panel_tally" ]; then
    read -r p_ok p_warn p_fail < "$panel_tally"
    pass=$((pass + p_ok)); warn=$((warn + p_warn)); fail=$((fail + p_fail))
  else
    # ⛔ NOT 'clean'. The block established nothing, and an unrun check and a
    # passing one are otherwise the same silence.
    bad "panel identity established nothing (python3 exited $panel_rc, no tally)"
  fi
  rm -f "$panel_tally"
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
    # ⛔ Process substitution, NOT `cmd | while`. A pipe runs the loop body in a
    # SUBSHELL, so bad()'s `fail=$((fail+1))` increments a copy that dies with it.
    # Measured here: 8 worktree FAILs printed, 0 counted, summary said "1 fail" —
    # and the worktree FAILs are the blocking condition for launching at all.
    # ⚠ Same family as the `| tail` defect this repo already warns about: a pipe
    # discarding the thing the caller depends on. tools/pipe-exit-scan.py does not
    # see this shape — it looks for lost EXIT CODES, not lost VARIABLE STATE.
    while read -r st r pa rest; do
      case "$st" in
        MISSING) bad  "$r has NO isolated tree — it works in the SHARED tree; run fleet-worktree.sh create" ;;
        OUTSIDE) bad  "$r isolated OUTSIDE the convention at $pa — MOVE it; creating would duplicate it" ;;
        DUP)     note "$r has TWO trees ($pa $rest) — commits land in whichever the pane is in; needs a deliberate decision" ;;
      esac
    done < <(scripts/fleet-worktree.sh check 2>&1)
  fi
else
  note "scripts/fleet-worktree.sh not executable — worktree coverage UNMEASURED, not clean"
fi

section 'Repository self-checks'
# ★ #89 measured 13 instruments and ONE call-shaped reference from outside any of
# them — and that one was a fixture whose header says "Not run; scanned." A set of
# instruments none of which is ever called is a citation network, not a toolchain.
# These two are cheap, deterministic, and answer questions no reviewer reliably
# answers by eye. ⚠ This pane still does not gate: exit code is always 0.
for chk in scripts/check-tools-index.py scripts/check-goal-conformance.py \
           scripts/check-onboard.py; do
  if [ ! -x "$chk" ] && [ ! -r "$chk" ]; then
    note "$chk not present — that check is UNMEASURED, not passing"
    continue
  fi
  # ⛔ THREE OUTCOMES, NOT TWO. This read `if out=$(python3 "$chk")`, which scores
  # EVERY non-zero as FAILED — so exit 2 ("established nothing") was reported as
  # a finding. That is the one conflation this estate exists to prevent, sitting
  # in the acceptance test for the whole install, and it was not hypothetical:
  # check-tools-index.py carries 11 exit-2 paths and check-goal-conformance.py 3.
  # ⇒ A checker that could not open its subject was telling the operator it had
  # found a defect in it.
  out=$(python3 "$chk" 2>&1); rc=$?
  case "$rc" in
    0) ok "$(basename "$chk") clean" ;;
    2) note "$(basename "$chk") established NOTHING (exit 2) — UNMEASURED, not clean and not a finding:"
       printf '%s\n' "$out" | grep -E '(VOID|⛔)' | head -2 | sed 's/^/        /' ;;
    *) bad "$(basename "$chk") FAILED (exit $rc):"
       printf '%s\n' "$out" | grep -E '^\s*(FAIL|·|⛔)' | head -4 | sed 's/^/        /' ;;
  esac
done
section 'Exit codes read through a pipe'
# ★ #89 / #234 §4's shape: tools/pipe-exit-scan.py has a GATED CALLER for its
# --self-test and NONE for its scan. Measured 2026-09-07: the scan had never been
# run by anything, and a manual run found 113 occurrences across 19 sessions in
# this project alone.
#
# ⛔ AND IT CANNOT BE GATED IN CI, BY CONSTRUCTION. Its subject is
# ~/.claude/projects — the operator's own transcripts — which does not exist on a
# runner. An instrument whose subject is the operator's machine has no CI caller
# available to it, so this pane is the only host there is.
#
# ⚠ SCOPED TO THIS PROJECT ON PURPOSE. Unscoped it reads every repository on the
# machine: measured 809 findings vs 113, and #175 §3 declined that corpus in as
# many words — "a wider corpus than ~/.claude/projects is a different instrument
# with consent questions that are not an agent's to settle." The fleet's record of
# its own work is a different object from a user's machine.
#
# ⚠ REPORTED AS A WARN, NEVER A FAIL, even on findings. These are historical
# agent-behaviour defects in transcripts, not defects in THIS install, and this is
# the install's acceptance test. A fresh install would inherit a red board for
# something it did not do. Cost measured: 1s scoped.
if [ -r tools/pipe-exit-scan.py ]; then
  # ⛔ THE MAIN WORKTREE, NOT `--show-toplevel`. Transcript directories are keyed by
  # the cwd the agent was LAUNCHED in, which for this fleet is the main repo. From a
  # linked worktree `--show-toplevel` returns the WORKTREE path, so the derived slug
  # matched no directory and this check reported ESTABLISHED NOTHING — measured
  # 2026-09-07, and it failed CLOSED, which is the only reason it was visible.
  # ⚠ `sed`, not `awk '{print $2}'`: #234 §2 — a worktree path containing a space
  # is truncated by field-splitting, silently.
  _slug=$(git worktree list --porcelain 2>/dev/null | head -1 | sed 's/^worktree //' | tr '/' '-')
  if [ -z "$_slug" ]; then
    note "not inside a git repository — pipe-exit-scan is UNMEASURED, not clean"
  else
    out=$(python3 tools/pipe-exit-scan.py --transcripts --project "$_slug" 2>&1); rc=$?
    case "$rc" in
      0) ok "no exit code read through a pipe in this project's transcripts" ;;
      # ⛔ TAKE THE TOOL'S OWN TALLY, NEVER RE-COUNT ITS OUTPUT. This read
      # `grep -c '⇒ '` and reported 113 where the tool's own line said 108. Two
      # causes, both real: the ⇒ glyph also appears in header lines, AND before the
      # fix on tools/pipe-exit-scan.py `--transcripts` fell through into the
      # tracked-file scan, so 2 FILE findings were counted as transcript occurrences.
      # ⇒ A caller that re-derives a number the instrument already publishes is a
      # second reading of one noun (#345), and it drifted on its very first run.
      1) n=$(printf '%s\n' "$out" | sed -n 's/^\([0-9][0-9]*\) occurrence(s) in EXECUTED.*/\1/p' | head -1)
         if [ -z "$n" ]; then
           note "pipe-exit-scan found occurrences but published no tally — the COUNT is UNMEASURED, not clean"
         else
           note "pipe-exit-scan: $n occurrence(s) in this project's transcripts — historical, not an install defect"
         fi ;;
      *) note "pipe-exit-scan ESTABLISHED NOTHING (exit $rc) — not clean" ;;
    esac
  fi
else
  note "tools/pipe-exit-scan.py not present — that check is UNMEASURED, not passing"
fi
section 'Work left on merged branches'
# ★ #89: an instrument with no caller is an argument. This one answers a
# LAUNCH-TIME question — did anything get left behind since the last launch — and
# it would have caught all three of this role's own pushes to a ref whose PR had
# already merged. Giving it a caller is the fix for both.
#
# ⚠ It calls `gh`, so it is the only network-dependent check here. Failure is
# reported as UNMEASURED rather than clean, and never blocks: this pane reports.
if [ -r tools/stranded-branches.py ]; then
  if out=$(python3 tools/stranded-branches.py 2>&1); then
    ok "no merged branch carries unmatched commits"
  else
    rc=$?
    if [ "$rc" -ge 2 ]; then
      note "stranded-branches ESTABLISHED NOTHING (exit $rc) — not clean; likely gh auth or network"
    else
      # ⛔ `cmd | while` RAN THESE IN A SUBSHELL, so every note()/ok() below
      # incremented a copy of $warn/$pass that died with it. Measured: 73 warns
      # and 1 ok printed in the body, 0 of them reaching the summary.
      #
      # ⚠ #267 diagnosed this as "the section prints its verdicts directly
      # instead of using the counters". It does NOT — it calls note() and ok()
      # like every other section. The verdicts WERE counted and the COUNT was
      # discarded. Different defect, different fix: process substitution, not a
      # rewrite onto the counting functions.
      #
      # ★ Found by tools/pipe-exit-scan.py, which named `warn` and `pass` at
      # these exact lines — the matcher repaired under #266 for missing this
      # one-liner shape. Behavioural proof: piped -> warn=0 with 3 notes
      # emitted; `done < <(...)` -> warn=3.
      branch_warn=0
      while read -r _ ref rest; do
        note "$ref has commits with no upstream patch-match — ⚠ NOT proof of loss; recovery-by-recommit reads this way"
        branch_warn=$((branch_warn+1))
      done < <(printf '%s\n' "$out" | grep '^NO-UPSTREAM-MATCH')
      equiv=$(printf '%s\n' "$out" | grep -c '^EQUIVALENT-UPSTREAM')
      branch_ok=0
      if [ "$equiv" -gt 0 ]; then
        ok "$equiv ref(s) unreachable by sha but EQUIVALENT upstream — landed"
        branch_ok=1
      fi
      # ⇒ #267 option 3: the section carries its own subtotal, so the fleet
      # summary stays about the fleet while nothing the body printed is missing
      # from a total. A reader who trusts the summary must not be able to miss
      # what the body showed.
      printf '  branch subtotal: %d warn, %d ok (counted in the Summary below)\n' \
        "$branch_warn" "$branch_ok"
    fi
  fi
else
  note "tools/stranded-branches.py not readable — that check is UNMEASURED, not clean"
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

# ⛔ THE EXIT CODE MUST CARRY THE VERDICT. This was `exit 0` unconditionally: the script
# printed "Preflight found blocking problems" and then told every caller it had passed.
# $fail was read twice — to print the tally, and to choose the message — and never to exit.
#
# ⇒ onboard.md makes this the ACCEPTANCE TEST for an install ("resolve every FAIL"), and an
# acceptance test that cannot fail is #26 in the place it does the most damage. A sibling
# fleet found the same root one layer in: a check whose FAIL never reached the counter.
#
# 0 clean · 1 blocking failures · 2 the script could not establish its own verdict.
if [ -z "${fail+x}" ] || [ -z "${pass+x}" ]; then
  printf '  \033[31m⛔ VOID: counters unset — this run established NOTHING about the fleet.\033[0m\n'
  exit 2
fi
[ "$fail" -gt 0 ] && exit 1
exit 0
