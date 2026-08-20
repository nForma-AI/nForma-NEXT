#!/usr/bin/env python3
"""The GitHub quota is ONE 5,000/hr pool shared by every agent. Who is spending it?

⛔ MEASURED 2026-08-20, while the pool sat at 0/5000 with 42 minutes to reset and
every pane's `gh` call failing:

    10,049 gh invocations across nine live transcripts, one session
     4,553 from a single role (45%)
     3,301 of them bare `gh api`, plus 618 `gh api repos` and 509 `gh api graphql`

⚠⚠ AND ONE INVOCATION IS NOT ONE API CALL. This is the whole reason the number is
invisible:

  - `gh pr list --limit 200` paginates: one invocation, several calls.
  - `gh run view --log` downloads an archive: one invocation, many.
  - `gh pr view --json statusCheckRollup` is a GraphQL query whose cost is not 1.
  - `gh api graphql` costs by node count, not by request.

⇒ So the invocation count is a LOWER BOUND on spend and must never be reported as
the spend. This tool prints both, labelled, and refuses to derive one from the
other.

★ AND THE COST LANDS ON WHOEVER ASKS NEXT, not on whoever spent it. A pane that
made no calls all session gets the 403. That is why per-role attribution is the
useful output: the quota is a commons and nothing here shows a pane its own share.
"""
import argparse, collections, glob, json, os, re, subprocess, sys, time

TRANSCRIPTS = "~/.claude/projects/*/*.jsonl"
# a gh INVOCATION at a command position — a mention inside a string is not a call
GH = re.compile(r"(?:^|[;|&]\s*|\$\(\s*|\n\s*|`|&&\s*)gh\s+([a-z-]+)(?:\s+([a-z-]+))?")
SYSTEM_REMINDER = re.compile(r"<system-reminder>.*?</system-reminder>", re.S)
WAKE = re.compile(r"auto-wake|machine wake|Resume your goal's autonomous loop", re.I)
ROLE_RE = re.compile(r"You are (?:taking over as )?([A-Z][A-Z0-9]*)\b")
# commands whose single invocation is KNOWN to cost more than one call
MULTI = ("--limit", "--paginate", "run view", "--log", "graphql", "statusCheckRollup")


def bootstrap_role(path, window=40):
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


# ⛔ IT IS NOT ONE POOL. Measured 2026-08-20 with `core` fully drained for the
# SECOND consecutive hour, while every pane reported "we are rate limited":
#
#     core       0/5000  used=5000   resets in  7.9m   <- EXHAUSTED
#     graphql 3508/5000  used=1492   resets in 18.5m   <- 70% FREE
#     search    30/30    used=   0
#
# ⇒ "rate limited" named one bucket and was read as all of them. The heaviest
# consumers are REST (`gh api repos/...`, `gh pr view`), and the GraphQL bucket
# sat two-thirds idle the whole time. A read that can be expressed as a GraphQL
# query is spending from a different, emptier pool -- so reporting only `core`
# hides the capacity that is actually available.
BUCKETS = ("core", "graphql", "search")


def quota():
    """{bucket: (remaining, limit, reset_epoch)} or None — a failed read is NOT a full pool.

    ⚠ `rate_limit` is exempt from the quota it reports, so this call is free even
    when everything else is 403ing. If it fails anyway, the network or auth is the
    problem, and reporting 0 would blame the wrong thing.
    """
    try:
        r = subprocess.run(["gh", "api", "rate_limit"],
                           capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0 or not r.stdout.strip():
        return None
    try:
        res = (json.loads(r.stdout) or {}).get("resources") or {}
    except ValueError:
        return None
    out = {}
    for b in BUCKETS:
        v = res.get(b)
        if isinstance(v, dict) and "remaining" in v and "limit" in v:
            out[b] = (int(v["remaining"]), int(v["limit"]), int(v.get("reset", 0)))
    return out or None


def scan(root, limit):
    paths = sorted(glob.glob(os.path.expanduser(root)),
                   key=lambda p: -os.path.getmtime(p))[:limit]
    per, subs, multi = collections.Counter(), collections.Counter(), collections.Counter()
    unreadable = 0
    for p in paths:
        who = bootstrap_role(p) or os.path.basename(p)[:8]
        try:
            with open(p, errors="replace") as fh:
                for line in fh:
                    if '"name":"Bash"' not in line and '"name": "Bash"' not in line:
                        continue
                    try:
                        rec = json.loads(line)
                    except ValueError:
                        continue
                    c = (rec.get("message") or {}).get("content")
                    if not isinstance(c, list):
                        continue
                    for b in c:
                        if not isinstance(b, dict) or b.get("name") != "Bash":
                            continue
                        cmd = (b.get("input") or {}).get("command", "")
                        hits = GH.findall(cmd)
                        if not hits:
                            continue
                        per[who] += len(hits)
                        for a, bb in hits:
                            subs[("gh " + a + " " + (bb or "")).strip()] += 1
                        if any(m in cmd for m in MULTI):
                            multi[who] += len(hits)
        except OSError:
            unreadable += 1
    return per, subs, multi, len(paths), unreadable


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=TRANSCRIPTS)
    ap.add_argument("--limit", type=int, default=12, help="freshest N transcripts")
    a = ap.parse_args()

    q = quota()
    print("── QUOTA ── SEPARATE pools, all shared by every agent and every tool")
    exhausted = False
    if q is None:
        print("  ⛔ ESTABLISHED NOTHING — could not read rate_limit. That endpoint is")
        print("     EXEMPT from the quota, so a failure here is network or auth, not")
        print("     exhaustion. Reporting 0 would blame the wrong thing.")
    else:
        for b, (rem, lim, rst) in q.items():
            mins = max(0, int((rst - time.time()) // 60))
            state = "EXHAUSTED" if rem == 0 else f"{100 * rem // max(lim, 1)}% left"
            print(f"  {b:8s} {rem:5d}/{lim:<5d} ({state}), resets in {mins}m")
            if rem == 0:
                exhausted = True
        dead = [b for b, v in q.items() if v[0] == 0]
        free = [b for b, v in q.items() if v[1] and v[0] * 2 > v[1]]
        if dead and free:
            print(f"\n  ⚠ {', '.join(dead)} EXHAUSTED while {', '.join(free)} is over half"
                  " free.\n     \"We are rate limited\" names ONE bucket and is read as all"
                  " of them —\n     a read expressible as a GraphQL query spends from a"
                  " different pool.")

    per, subs, multi, files, unreadable = scan(a.root, a.limit)
    total = sum(per.values())
    print(f"\n── INVOCATIONS ── {files} transcript(s)"
          + (f", {unreadable} unreadable" if unreadable else ""))
    if not total:
        print("  ⛔ ESTABLISHED NOTHING — no gh invocation found. A transcript glob that")
        print("     matched nothing and a fleet that made no calls print the same zero.")
        return 2
    print(f"  {total} gh invocation(s) — ⚠ a LOWER BOUND on API calls, never the spend\n")
    for who, n in per.most_common():
        m = multi.get(who, 0)
        flag = f"   ⚠ {m} of them use --limit/--paginate/--log/graphql" if m else ""
        print(f"  {n:6d}  {who}{flag}")
    print("\n  most-called subcommands:")
    for k, n in subs.most_common(8):
        print(f"  {n:6d}  {k}")

    print("\n⚠⚠ ONE INVOCATION IS NOT ONE CALL. Pagination, `run view --log` and graphql")
    print("   each cost more than 1, so the true spend is higher than the count above and")
    print("   this tool does not guess the multiplier.")
    print("⚠ The cost lands on whoever asks NEXT. A pane that made no calls gets the 403.")
    return 1 if exhausted else 0


if __name__ == "__main__":
    sys.exit(main())
