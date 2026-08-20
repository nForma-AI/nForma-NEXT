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
    """{issue number: set(OPENED|ACTED)} for one transcript. None if unreadable."""
    out = collections.defaultdict(set)
    try:
        with open(path, errors="replace") as fh:
            for line in fh:
                if "issue" not in line:
                    continue
                try:
                    rec = json.loads(line)
                except ValueError:
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
    return out


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


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=None)
    ap.add_argument("--root", default=TRANSCRIPTS)
    ap.add_argument("--limit", type=int, default=9, help="freshest N transcripts")
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

    paths = sorted(glob.glob(os.path.expanduser(a.root)),
                   key=lambda p: -os.path.getmtime(p))[:a.limit]
    if not paths:
        print("⛔ ESTABLISHED NOTHING — no transcripts readable. Zero coverage and "
              "zero visibility print the same table.")
        return 2

    touched, per_role, unreadable = collections.defaultdict(set), collections.Counter(), 0
    for p in paths:
        c = contacts(p)
        if c is None:
            unreadable += 1
            continue
        who = bootstrap_role(p) or os.path.basename(p)[:8]
        for n, kinds in c.items():
            if n in issues:
                touched[n].add(who)
                per_role[who] += 1

    never = sorted(set(issues) - set(touched))
    print(f"── COVERAGE ── {len(issues)} open issue(s), {len(paths)} transcript(s)"
          + (f", {unreadable} unreadable" if unreadable else ""))
    print(f"  opened by at least one pane   {len(touched):4d}")
    print(f"  opened by NOBODY              {len(never):4d}  "
          f"({100 * len(never) / len(issues):.0f}%)")
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
    return 1 if never else 0


if __name__ == "__main__":
    sys.exit(main())
