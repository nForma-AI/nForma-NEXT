#!/usr/bin/env python3
"""Which issues has NOBODY opened? Derived from the record, never from asking.

⛔ WHY IT CANNOT BE ASKED, AND WHY GITHUB CANNOT ANSWER IT.

  1. The credential is shared. `gh issue list --json author,assignee` returns ONE
     login for every issue in every state, which is why two ownership conventions
     already failed here (goals/RESERVED-ACTIONS.md). GitHub knows WHAT happened
     and not WHO.
  2. An agent's answer about its own history is unreliable. Measured 2026-08-20:
     asked whether they had read their own role prompt, three of four roles said
     "never" while their transcripts held 14, 11 and 9 reads from that morning.
     The one that checked its transcript first was the one that got it right, and
     said so: "from memory I would have told you I had never seen it."

⇒ So the only discriminator is what a pane ACTUALLY OPENED, in a tool_use, and
this reads that.

★ CONTACT IS NOT REVIEW, and the two are reported separately because collapsing
them is the defect this fleet keeps filing. `OPENED` means a pane fetched the
issue. It does not mean anyone thought about it.

⚠ AND THE BOUND CUTS ONE WAY. This reads transcripts ON THIS MACHINE. An issue
reviewed from a session that has ended, or from a pane whose transcript lives
elsewhere, reads as untouched -- a peer merged two PRs while being reported
FLATLINE for six hours on exactly that basis. ⇒ The untouched count is an UPPER
BOUND and the per-role counts are LOWER bounds. Never quote either as exact.

⚠ THE SECOND BOUND, added with identity selection: a session that never declared
a role IS NOT READ. Measured 2026-08-21, three such sessions had opened 25, 2 and
2 issues. This is a bound worth paying -- it is FIXED and stateable, where the
recency window it replaced varied with the clock -- but it is not free, and it is
the reason `--recency` still exists as a cross-check rather than being deleted.
"""
import argparse, collections, glob, json, os, re, subprocess, sys

TRANSCRIPTS = "~/.claude/projects/*/*.jsonl"
# a real fetch of one issue -- not a number appearing in prose or in a list dump
OPENED_RE = re.compile(r"gh issue (?:view|edit|close|comment|reopen)\s+(\d+)|/issues/(\d+)\b")
ACTED_RE = re.compile(r"gh issue (?:edit|close|comment|reopen)\s+(\d+)")
SYSTEM_REMINDER = re.compile(r"<system-reminder>.*?</system-reminder>", re.S)
WAKE = re.compile(r"auto-wake|machine wake|Resume your goal's autonomous loop", re.I)
ROLE_RE = re.compile(r"You are (?:taking over as )?([A-Z][A-Z0-9]*)\b")

OPENED, ACTED = "OPENED", "ACTED"


def bootstrap_role(path, window=40):
    """The role a pane was launched as. None = no launch prompt here; "" = none named."""
    try:
        with open(path, errors="replace") as fh:
            for i, line in enumerate(fh):
                if i > window:
                    return None
                if '"type":"user"' not in line and '"type": "user"' not in line:
                    continue
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                c = (rec.get("message") or {}).get("content")
                if isinstance(c, list) and any(
                        isinstance(b, dict) and b.get("type") == "tool_result" for b in c):
                    continue
                t = c if isinstance(c, str) else ("".join(
                    b.get("text", "") for b in c
                    if isinstance(b, dict) and b.get("type") == "text")
                    if isinstance(c, list) else "")
                t = SYSTEM_REMINDER.sub("", t).strip()
                if t:
                    if WAKE.search(t[:400]):
                        return None
                    m = ROLE_RE.search(t)
                    return m.group(1) if m else ""
    except OSError:
        return None
    return None


def contacts(path):
    """({issue: set(OPENED|ACTED)}, skipped) for one transcript. None if unreadable.

    ⛔ `skipped` EXISTS BECAUSE A COUNT IS AN ABSENCE CLAIM.

        A witness that certifies PROVENANCE does not certify COMPLETENESS,
        and every absence claim needs the second one.

    This function's product is "which issues were NOT contacted", and an
    unparseable line is silently skipped — so a partial read and a genuinely
    quiet pane produced the SAME output, and the difference was invisible.
    The bias runs one way: dropped lines mean fewer contacts, which means MORE
    issues reported as "opened by NOBODY". It over-reports the alarming direction.

    ⚠ MEASURED 2026-08-21 BEFORE ADDING THIS, and the result refuted the reason
    I went looking: 0 unparseable lines in 170,364 across all 12 role-named
    transcripts, 0 of 12 ending on a partial line — including panes writing while
    I read them. The writer appends whole lines. ⇒ So this is NOT a fix for a
    live defect and must not be described as one. The COUNT is zero; the COUNTER
    was missing, and an instrument that cannot report a zero cannot report a one.
    """
    out = collections.defaultdict(set)
    skipped = 0
    try:
        with open(path, errors="replace") as fh:
            for line in fh:
                if "issue" not in line:
                    continue
                try:
                    rec = json.loads(line)
                except ValueError:
                    skipped += 1      # ⇒ counted, never silent
                    continue
                if rec.get("type") != "assistant":
                    continue
                c = (rec.get("message") or {}).get("content")
                if not isinstance(c, list):
                    continue
                for b in c:
                    if not isinstance(b, dict) or b.get("type") != "tool_use":
                        continue
                    inp = json.dumps(b.get("input", {}))
                    for m in OPENED_RE.finditer(inp):
                        out[int(m.group(1) or m.group(2))].add(OPENED)
                    for m in ACTED_RE.finditer(inp):
                        out[int(m.group(1))].add(ACTED)
    except OSError:
        return None
    return out, skipped


def open_issues(repo=None):
    """{number: (created, title)}. None if gh could not answer -- NOT an empty board."""
    cmd = ["gh", "issue", "list", "--state", "open", "--limit", "1000",
           "--json", "number,title,createdAt"]
    if repo:
        cmd += ["--repo", repo]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    try:
        rows = json.loads(r.stdout)
    except ValueError:
        return None
    if not rows:
        return None                    # ⛔ an empty board is indistinguishable from a
                                       # failed query that exited 0; refuse both
    return {x["number"]: (x["createdAt"][:10], x["title"]) for x in rows}


def select_panes(root, limit, recency=None):
    """The transcripts that ARE the fleet, and a note about how they were chosen.

    ⛔ THE DEFECT THIS REPLACES. Selection was `sorted(paths, key=-mtime)[:9]` --
    the nine most recently-TYPING panes. Measured 2026-08-21, two runs 90s apart
    against an unchanged board:

        run 1   covered 153 · untouched 80 (34%)   TRIAGE contributed 41
        run 2   covered 149 · untouched 84 (36%)   TRIAGE contributed  0

    Nothing happened in between. TRIAGE fell out of the top nine by going quiet
    for ~2 minutes, and its 41 issues reverted to "opened by NOBODY".

    ★ SO THE INSTRUMENT DROPPED THE IDLE PANES -- which is the exact population
    the question is usually about ("architect is idle, has it reviewed these?").
    A rank cut over a clock puts the boundary where the churn is: at the moment
    of measurement two slots were held by transcripts with ZERO issue contacts
    while DEVOPS sat one rank outside.

    ⇒ Identity, not recency. `bootstrap_role` already names the fleet, and it
    reads 40 lines, so classifying ALL of them is cheap. Measured: 6,323
    transcripts classified in 2.2s, of which 12 name a role -- 270MB to parse
    against the 262MB the recency window was already parsing. Same cost.
    """
    all_paths = glob.glob(os.path.expanduser(root))
    if recency is not None:
        chosen = sorted(all_paths, key=lambda p: -os.path.getmtime(p))[:recency]
        return chosen, ("⚠ --recency reproduces the OLD selection: the {} most recently\n"
                        "   ACTIVE transcripts. A pane that is thinking or blocked leaves the\n"
                        "   population and its issues revert to untouched. The counts below\n"
                        "   are a function of WHEN you ran this.").format(recency)

    named = [(bootstrap_role(p), p) for p in all_paths]
    named = [(r, p) for r, p in named if r]
    named.sort(key=lambda rp: -os.path.getmtime(rp[1]))
    chosen = [p for _, p in named[:limit]]
    note = "  selection: identity — {} of {} transcript(s) bootstrapped as a role".format(
        len(named), len(all_paths))
    if len(named) > limit:                      # the ceiling BOUND; say so, never silently
        dropped = " · ".join(r for r, _ in named[limit:])
        note += ("\n  ⛔ --limit {} BOUND: {} role-named pane(s) were NOT read: {}\n"
                 "     Their issues are counted as untouched. Raise --limit.").format(
            limit, len(named) - limit, dropped)
    return chosen, note


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=None)
    ap.add_argument("--root", default=TRANSCRIPTS)
    ap.add_argument("--limit", type=int, default=64,
                    help="ceiling on role-named transcripts read; reported when it binds")
    ap.add_argument("--recency", type=int, default=None, metavar="N",
                    help="OLD behaviour: the freshest N transcripts regardless of role. "
                         "Drops idle panes — see select_panes.")
    ap.add_argument("--match", default=None,
                    help="regex over titles, to slice the untouched set by subject")
    ap.add_argument("--show", type=int, default=20)
    a = ap.parse_args()

    issues = open_issues(a.repo)
    if issues is None:
        print("⛔ ESTABLISHED NOTHING — the issue query failed or returned nothing. "
              "An empty board and a failed query are the same output; neither is a "
              "coverage result.")
        return 2

    paths, how = select_panes(a.root, a.limit, a.recency)
    if not paths:
        print("⛔ ESTABLISHED NOTHING — no transcript names a role, so there is no "
              "fleet to measure. Zero coverage and zero visibility print the same "
              "table. (Pass --recency N to select by mtime instead.)")
        return 2

    touched, per_role, unreadable = collections.defaultdict(set), collections.Counter(), 0
    skipped_total, skipped_panes = 0, []
    for p in paths:
        got = contacts(p)
        if got is None:
            unreadable += 1
            continue
        c, sk = got
        skipped_total += sk
        if sk:
            skipped_panes.append((bootstrap_role(p) or os.path.basename(p)[:8], sk))
        who = bootstrap_role(p) or os.path.basename(p)[:8]
        for n, kinds in c.items():
            if n in issues:
                touched[n].add(who)
                per_role[who] += 1

    never = sorted(set(issues) - set(touched))
    print(f"── COVERAGE ── {len(issues)} open issue(s), {len(paths)} transcript(s)"
          + (f", {unreadable} unreadable" if unreadable else ""))
    print(how)
    print(f"  opened by at least one pane   {len(touched):4d}")
    print(f"  opened by NOBODY              {len(never):4d}  "
          f"({100 * len(never) / len(issues):.0f}%)")
    # ⛔ COMPLETENESS, PRINTED EVERY RUN — not only when it is bad. A line that
    # appears only on failure is a line nobody has ever seen working, and its
    # absence then reads as "fine" rather than as "the check did not run".
    if skipped_total:
        print(f"  ⛔ {skipped_total} unparseable line(s) SKIPPED across "
              f"{len(skipped_panes)} pane(s): "
              + " · ".join(f"{r}+{n}" for r, n in skipped_panes))
        print("     ⇒ contacts are UNDER-counted, so 'opened by NOBODY' is "
              "OVER-stated by an unknown amount.")
    else:
        print(f"  completeness: every line parsed in all {len(paths)} transcript(s)")
    print("\n  per pane (LOWER bounds): "
          + " · ".join(f"{r} {n}" for r, n in per_role.most_common()))

    rows = never
    if a.match:
        rx = re.compile(a.match, re.I)
        rows = [n for n in never if rx.search(issues[n][1])]
        print(f"\n  {len(rows)} of the untouched match /{a.match}/")
    for n in rows[:a.show]:
        d, t = issues[n]
        print(f"    #{n:<6} {d}  {t[:72]}")
    if len(rows) > a.show:
        print(f"    … {len(rows) - a.show} more (--show)")

    print("\n⚠ CONTACT IS NOT REVIEW — 'opened' means a pane fetched it, nothing more.")
    print("⚠ Transcripts on THIS MACHINE only: a pane working from a transcript held "
          "elsewhere\n   reads as having opened nothing. The untouched count is an "
          "UPPER bound; per-pane counts are LOWER bounds.")
    if a.recency is None:
        print("⚠ Sessions that never declared a role are NOT read at all. Cross-check "
              "with\n   --recency N, which reads the freshest N regardless of role — and "
              "whose\n   own counts move as panes go idle.")
    return 1 if never else 0


if __name__ == "__main__":
    sys.exit(main())
