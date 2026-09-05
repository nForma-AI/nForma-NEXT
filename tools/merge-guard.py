#!/usr/bin/env python3
"""Refuse a merge this session is not entitled to make — and fail CLOSED.

⛔ THIS IS LEG 4 OF FOUR ISSUES, and all four state it identically:
`#193` `#296` `#302` `#304` — *"an instrument REFUSES a merge attempt from a session
that is not the holder, and has been shown to refuse one"* — each with the note
`tools/merge-guard.py DOES NOT EXIST`. One remedy, four issues.

⛔⛔ AND IT EXISTS BECAUSE AN INLINE VERSION FAILED OPEN, ON A REAL MERGE. Merging
`#581` on 2026-09-05 the guards ran as shell with `python3 -c json.load` per leg and no
exit code was checked. A control character in a review body made every parse raise;
every guard variable came back EMPTY; every line printed a blank that read as benign;
the merge proceeded. The PR was fine, so nothing went wrong — **which is the worst
outcome, because the guard was never tested and looked like it worked.**

⇒ Every leg here returns UNESTABLISHED rather than a value it could not obtain, and
**UNESTABLISHED is fatal**. A guard that cannot establish a leg must block, not shrug.

## ⛔ Leg 0 parses the LAST holder, and that is not a style choice

`docs/MERGE-AUTHORITY.md` records successions by APPENDING. Measured 2026-09-05 it
carries **two** `HOLDER` lines — `a10daa24…` at line 14 and `15b69750…` at line 180.

    grep -m1 HOLDER   ->  a10daa24   ⛔ the STALE holder
                          would REFUSE the real holder and AUTHORIZE a lapsed session

★ So the count is reported on every run rather than assumed. A positional read that
does not say it is positional is the defect this repository keeps filing (#23: verify
by content, never by position). Here position IS the semantics — successions append —
so the honest form is to use the last AND print how many were found.

## ⛔ WHAT THIS DOES NOT DO — stated first-class, because #193's own proxy test says so

> *An instrument that refuses non-holder merges runs inside a pane that could edit or
> bypass it. The only enforcement a pane cannot route around is branch protection, and
> that is operator-only by rule 2.*

⇒ **This raises the cost of an accident. It does not make the policy unbypassable.**
Any pane can edit this file, skip this tool, or call `gh pr merge` directly — the
credential reports `push=true, admin=true` for every pane. Closing those four issues on
this tool alone would be claiming an enforcement that does not exist.

Legs, each with the finding it comes from:
  0 holder == this session   #193/#296/#302/#304 — the leg all four wait on
  1 base == main             #445  a stacked PR squashes onto an orphaned base
  2 required gate green      rule 2; the gate is the only enforcement that exists
  3 reviews READ             #316/#336  a green board cannot carry an objection
  4 three-dot not a revert   #510, and ⛔ THREE dots — two-dot measures branch age
  5 age at merge             #224  25 of 100 PRs merged inside 60s of creation

Exit: 0 every leg established and passed · 1 a leg FAILED · 2 a leg could not be
established, or the arguments were rejected.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

REPO = "nForma-AI/nForma-NEXT"
AUTHORITY = "docs/MERGE-AUTHORITY.md"
HOLDER_RE = re.compile(r"^HOLDER\s+session\s+([0-9a-fA-F-]{8,})\s*$", re.M)


class Unestablished(Exception):
    """A leg could not be measured. ⇒ exit 2. Never a pass."""


def sh(args, allow_fail=False):
    try:
        p = subprocess.run(args, capture_output=True, text=True)
    except OSError as exc:
        raise Unestablished(f"cannot run {args[0]}: {exc}")
    if p.returncode != 0 and not allow_fail:
        raise Unestablished(f"{args[0]} exited {p.returncode}: {(p.stderr or '').strip()[:200]}")
    return p.stdout


# ── Leg 0 ─────────────────────────────────────────────────────────────────────

def holders(text):
    """Every HOLDER line, in file order. ⇒ The LAST is current; successions append."""
    return HOLDER_RE.findall(text or "")


def holder_check(text, session):
    """(ok, detail). ⛔ Refuses when the session is unknown — an unset
    CLAUDE_CODE_SESSION_ID is not permission, it is an unanswered question."""
    found = holders(text)
    if not found:
        return False, f"UNESTABLISHED — no `HOLDER    session <id>` line in {AUTHORITY}"
    if not session:
        return False, (f"UNESTABLISHED — CLAUDE_CODE_SESSION_ID is unset; cannot establish "
                       f"who is asking ({len(found)} holder line(s) on file)")
    current = found[-1]
    note = f"{len(found)} HOLDER line(s); using the LAST (successions append)"
    if current.lower() != session.lower():
        return False, f"{note} — current holder {current[:8]}…, this session {session[:8]}… ⇒ REFUSE"
    return True, f"{note} — {current[:8]}… matches this session"


# ── Legs 1-5 ──────────────────────────────────────────────────────────────────

def pr_json(n, fields):
    raw = sh(["gh", "pr", "view", str(n), "--repo", REPO, "--json", fields])
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        # ⛔ THE FAILURE THAT MOTIVATED THIS FILE. Do not "handle" it by continuing
        # with a default — that is what printed blanks on #581.
        raise Unestablished(f"gh --json {fields} was not parseable: {exc}")


def evaluate(n, session, authority_text, shape_only=False):
    legs = []

    def leg(name, ok, detail):
        legs.append((name, ok, detail))

    # ⛔ --shape-only OMITS leg 0 AND SAYS SO. It exists for CI, which has no holder
    # session and cannot have one: the holder is a running pane, not a runner. A flag
    # that made leg 0 PASS without a session would be a hole shaped exactly like the
    # thing this tool guards, so it is omitted and named rather than defaulted true.
    # ⇒ Shape-only ESTABLISHES NOTHING ABOUT AUTHORITY. It answers #510 leg 1's other
    # half — "a check exists, CI step OR merge-time" — and only that half.
    if shape_only:
        leg("0 holder == session", True, "⚠ SKIPPED — --shape-only. This run establishes "
                                         "NOTHING about who may merge.")
    else:
        ok, detail = holder_check(authority_text, session)
        leg("0 holder == session", ok, detail)

    d = pr_json(n, "baseRefName,mergeStateStatus,reviews,headRefOid,createdAt,state,statusCheckRollup")
    if d.get("state") != "OPEN":
        raise Unestablished(f"PR #{n} is {d.get('state')}, not OPEN")

    leg("1 base == main", d["baseRefName"] == "main", d["baseRefName"])

    # ⛔ --shape-only OMITS LEG 2 TOO, and for a reason measured on this tool's own PR.
    # A CI job asking "is the required gate green?" from INSIDE the run that CONTAINS
    # that gate is asking a self-referential question. Measured on PR #597, both jobs
    # in the same run:
    #     hermetic suites (gating)     started 23:22:19  completed 23:23:29  success
    #     PR shape (advisory)          started 23:22:19  completed 23:22:25  FAILURE
    # ⇒ pr-shape read the gate SIX SECONDS in, 64s before the gate finished. The gate
    # was necessarily unfinished, so leg 2 was necessarily unestablished, and the job
    # went red for a fact about ITS OWN CONCURRENCY rather than about the PR.
    # ⚠ `needs:` would serialise it, but that is the wrong fix: it makes an ADVISORY job
    # a prerequisite of nothing while doubling the run's latency, and it still leaves the
    # runner asserting a green gate that the merger must re-read at merge time anyway.
    # ⇒ The honest move is the same one leg 0 already makes: SKIP AND SAY SO.
    if shape_only:
        leg("2 required gate", True, "⚠ SKIPPED — --shape-only. A run cannot establish "
                                     "the outcome of a gate it CONTAINS. Re-read at merge.")
    else:
        rollup = d.get("statusCheckRollup") or []
        req = [c for c in rollup if (c.get("name") or c.get("context") or "") == "hermetic suites (gating)"]
        if not req:
            leg("2 required gate", False, "UNESTABLISHED — 'hermetic suites (gating)' absent from rollup")
        else:
            concl = req[0].get("conclusion") or req[0].get("state") or ""
            leg("2 required gate", concl == "SUCCESS", concl or "UNESTABLISHED")

    revs = d.get("reviews") or []
    changes = [r for r in revs if r.get("state") == "CHANGES_REQUESTED"]
    leg("3 reviews read", not changes, f"{len(revs)} review(s), {len(changes)} CHANGES_REQUESTED")

    sha = d["headRefOid"]
    sh(["git", "fetch", "origin", "--quiet"], allow_fail=True)
    # ⛔ THREE dots. Two-dot bills every commit main gained since the merge-base to the
    # branch as a deletion. Measured 2026-09-05: #499 two-dot −4396, three-dot −2.
    stat = sh(["git", "diff", "--numstat", f"origin/main...{sha}"], allow_fail=True)
    if not stat.strip():
        leg("4 three-dot diff", False, "UNESTABLISHED — empty numstat (unfetched ref?)")
    else:
        add = dele = 0
        losers = []          # files this PR removes more from than it adds
        for line in stat.strip().splitlines():
            parts = line.split("\t")
            if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
                # ⚠ NOT `a, d` — `d` is the PR dict in this scope. Shadowing it made
                # `d.get("createdAt")` raise AttributeError on an int, and the paired
                # suite caught it where --self-test could not: leg 5 is only reached
                # when a PR record exists, which self_test() never builds.
                ins, dels = int(parts[0]), int(parts[1])
                add += ins; dele += dels
                if dels > ins:
                    losers.append((parts[2] if len(parts) > 2 else "?", ins - dels))
        # ⛔ NAME THE FILES, not just the total. #510 leg 1: "it must state which files
        # and how many lines, per #500 — a count with no direction is a bound, not a
        # measurement." A net figure tells a reader THAT something was removed and
        # gives them nowhere to look.
        losers.sort(key=lambda x: x[1])
        detail = f"+{add} -{dele} (net {add - dele:+d})"
        if add < dele:
            top = "; ".join(f"{f} {n:+d}" for f, n in losers[:5])
            more = f" (+{len(losers) - 5} more)" if len(losers) > 5 else ""
            detail += f"  ⛔ net-negative in {len(losers)} file(s): {top}{more}"
        leg("4 three-dot diff", add >= dele, detail)

    created = d.get("createdAt") or ""
    try:
        age = (datetime.now(timezone.utc)
               - datetime.fromisoformat(created.replace("Z", "+00:00"))).total_seconds()
        leg("5 age at merge", age >= 120, f"{int(age)}s since creation")
    except Exception:
        leg("5 age at merge", False, f"UNESTABLISHED — unparseable createdAt {created!r}")

    return legs


# ── Controls ──────────────────────────────────────────────────────────────────

def self_test():
    """⛔ TWO-SIDED AND NAMED (#405). Leg 0 is driven with SYNTHETIC authority text, so
    the control needs no live forge and no particular session — #402: for a stateful
    instrument, a caller that still runs it means one that drives the DECISION with
    synthetic state."""
    ok = True

    def check(name, got, want):
        nonlocal ok
        good = got == want
        ok &= good
        print(f"  {'✅' if good else '⛔'} {name:50s} got {got!r}")

    A = "aaaaaaaa-1111-2222-3333-444444444444"
    B = "bbbbbbbb-5555-6666-7777-888888888888"
    one = f"HOLDER    session {A}\n"
    two = f"HOLDER    session {A}\n...prose...\nHOLDER    session {B}\n"

    print("── leg 0: holder ──")
    check("known-POSITIVE  the recorded holder passes", holder_check(one, A)[0], True)
    check("known-NEGATIVE  a non-holder is REFUSED", holder_check(one, B)[0], False)
    # ⛔ The trap this file was written around.
    check("⛔ TWO holders: the LAST one passes", holder_check(two, B)[0], True)
    check("⛔ TWO holders: the FIRST is now STALE and REFUSED", holder_check(two, A)[0], False)
    check("known-NEGATIVE  no HOLDER line at all is UNESTABLISHED",
          holder_check("no holder here", A)[0], False)
    check("known-NEGATIVE  an unset session is REFUSED, not waved through",
          holder_check(one, "")[0], False)
    check("holders() finds both, in order", holders(two), [A, B])

    print(f"\n{'✅ controls pass' if ok else '⛔ CONTROLS FAILED'} — 7 legs, both directions named")
    print("⚠ Legs 1-5 are exercised by tools/test_merge_guard.py against a stubbed forge;")
    print("   they are not self-tested here because they require a PR to exist.")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(
        description="Refuse a merge this session is not entitled to make. Fails closed.")
    ap.add_argument("prs", nargs="*", help="PR numbers to evaluate")
    ap.add_argument("--session", default=os.environ.get("CLAUDE_CODE_SESSION_ID", ""),
                    help="session id to test as (default: $CLAUDE_CODE_SESSION_ID)")
    ap.add_argument("--authority", default=AUTHORITY, help=f"path to {AUTHORITY}")
    ap.add_argument("--shape-only", action="store_true",
                    help="omit the holder leg — for CI, which has no holder session. "
                         "⛔ Establishes nothing about authority.")
    ap.add_argument("--self-test", action="store_true", help="run the controls; no network")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    # ⛔ NO PR NAMED = the HOLDER QUESTION ALONE, not a refusal to answer.
    # #193/#296/#302/#304's leg 4 asks for an instrument that "REFUSES a merge attempt
    # from a session that is not the holder", and their own runnable check invokes this
    # with `--session <id>` and NO pr. The first version returned VOID there, so the
    # condition's own command could not be satisfied by the instrument written for it.
    # ⇒ A holder check needs no PR: "may this session merge at all?" is answerable, and
    # is exactly the question those four issues pose.
    if not args.prs and args.shape_only:
        print("⛔ VOID — --shape-only needs a PR: without one there is no shape to check, "
              "and it is not a holder check.", file=sys.stderr)
        return 2
    if not args.prs:
        try:
            text = Path(args.authority).read_text(encoding="utf-8")
        except OSError as exc:
            print(f"⛔ VOID — cannot read {args.authority}: {exc}", file=sys.stderr)
            return 2
        ok, detail = holder_check(text, args.session)
        print(f"  {'✅' if ok else '⛔'} 0 holder == session    {detail}")
        print("  ⇒ " + ("THIS SESSION MAY MERGE (subject to the per-PR legs)"
                        if ok else "REFUSED — this session is not the holder"))
        return 0 if ok else 1

    try:
        text = Path(args.authority).read_text(encoding="utf-8")
    except OSError as exc:
        print(f"⛔ VOID — cannot read {args.authority}: {exc}\n"
              f"   ADDABLE — run from a checkout that has it, or pass --authority.",
              file=sys.stderr)
        return 2

    worst = 0
    for arg in args.prs:
        print(f"══ PR #{arg} ══")
        try:
            legs = evaluate(int(arg), args.session, text, args.shape_only)
        except (Unestablished, ValueError) as exc:
            print(f"  ⛔ UNESTABLISHED — {exc}")
            print("  ⇒ BLOCK. A leg that cannot be measured is not a leg that passed.\n")
            worst = max(worst, 2)
            continue
        failed = [n for n, ok, _ in legs if not ok]
        for name, ok, detail in legs:
            print(f"  {'✅' if ok else '⛔'} {name:22s} {detail}")
        if failed:
            print(f"  ⇒ BLOCK: {', '.join(failed)}\n")
            worst = max(worst, 1)
        else:
            print("  ⇒ CLEAR (squash, and NO --delete-branch — rule 5 / #294)\n")
    return worst


if __name__ == "__main__":
    sys.exit(main())
