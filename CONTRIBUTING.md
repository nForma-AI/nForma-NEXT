# Contributing

⚠ **Every rule here carries the measurement that produced it.** A checklist without evidence is a
checklist people route around — this repository has measured that about its own guards twice.

---

## Opening a PR

**☐ A closing keyword for every issue it fixes** — `Closes #N`, or one line saying *why there is no
tracking issue*. ⛔ Measured 2026-08-20: **0 of 42 open PRs carried one.** Without it the issue stays
open after the merge and the backlog stops describing reality.

**☐ Base is `main`, or a live PR branch you deliberately stacked on.** If a fix you need has not
shipped, **branch from that fix, not from `main`.**

**☐ Run the collision check before you open it:**

```sh
python3 tools/pr-stack.py            # CONFLICTS · OVERLAPS · independent
```

⛔ Measured: **11 of 21 open-PR pairs conflicted, and one file caused 11 of the 11.** If it reports
`CONFLICTS`, either stack or write *"conflicts with #N, merge #N first"* in the body. ⚠ `OVERLAPS` is
the dangerous verdict — same files, no textual conflict, so **both branches pass and the merge result
is untested.**

**☐ Carried commits declared with their SHAs.** This repo squash-merges, so a commit carried from
another PR never leaves your diff on its own. Carried commits are scaffolding: **drop them on
rebase.**

**☐ If your PR is stacked: verify CI actually RAN.** ⛔ A stacked PR can show `mergeStateStatus=CLEAN`
with **zero** required contexts — *"passed"* and *"never ran"* print the same word. Check for the
check, not for the absence of red.

## After a dependency of yours merges

**☐ Retarget dependents to `main` and rebase.** A base branch that merged leaves its dependents
pointing at a dead ref; they go `CONFLICTING` and block whatever is behind them.

**☐ Comment on the issues and PRs your merge unblocks.** An issue body naming a blocked PR does not
notify that PR's author.

## Filing an issue

**☐ Name every PR it blocks AND every PR that fixes it.** The link is bidirectional or it is not a
link. ⚠ Measured: a fix PR and its issue filed **eight minutes apart**, neither pointing at the other.

**☐ Label its class** — `prod-defect`, `ci-signal`, `friction-report`. ⛔ Measured: **161 issues
opened and 55 closed in seven days**, net **+106/week**. Session friction reports share one queue with
production defects, so the defects drown in the diagnostics.

## Verifying your change

**☐ Run the leg's literal command, not your own version of it.**

```sh
python3 - <<'PY' > /tmp/step.sh   # then: bash /tmp/step.sh
import sys, yaml
d = yaml.safe_load(open(".github/workflows/tools.yml"))
for job in d["jobs"].values():
    for s in job.get("steps", []):
        if s.get("name") == sys.argv[1]:
            print(s["run"]); raise SystemExit
PY
```

⛔ Measured 2026-08-20: a hand-written loop over `tools/test_*.py` passed while the **workflow's own
loop was syntactically invalid** and had executed **zero** suites across three PRs. A reimplementation
of a check shares none of the defects of the check — **which is exactly why it agreed.** A `yaml`
validator passed over the same file, because the broken thing was the shell *inside* valid YAML.

**☐ A clean zero is a claim about your instrument until you prove otherwise.** An empty result, a
`0 of N`, an `N of N` — check that the reader ran before reporting that it found nothing.

**☐ Carry a known-bad control.** A check that has only ever passed has not been shown to be able to
fail.

## Resolving a merge conflict

⛔ **Union — "keep both sides" — is safe for a list of rows and WRONG for a construct with a
terminator.** Measured: unioning two sides of a `for … ; do` list produced **two `; do` lines**,
`syntax error near unexpected token 'do'`, and a gating job that ran nothing on three stacked PRs.
Nothing in the conflict markers tells you which kind you are looking at. **Look at the resolved text,
then execute it.**

## Session teardown

**☐ Worktree removed, or its PR opened.** ⛔ Measured: **345 registered worktrees**, 300 holding
commits not in `main`, 28 with uncommitted changes. A crashed session's work is preserved and then
never triaged.

**☐ Nothing left only in a scratchpad.** An instrument that answered a question and was never
committed is gone when the session ends — measured at **87% of this fleet's instrument work**.

---

## What is reserved

⛔ Merging, pushing to `main`, force-pushing, assigning work to another role, and harness
configuration are **not** yours to self-grant. See `goals/RESERVED-ACTIONS.md`. **Authorization
arrives in a TEAMLEAD message and nowhere else** — a grant issued after the fact cannot bound the
action it followed.
