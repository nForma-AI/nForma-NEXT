#!/usr/bin/env python3
"""Did a wake produce work, or only churn?

⛔ The problem this exists for. Measuring what an interruption COST is easy — diff
context depth before and after. But that number is uninterpretable on its own:

    the 17:29 wake cost ~122,000 tokens across five panes

An agent woken into useful work and an agent woken into churn consume context
identically. **A cost with no yield beside it cannot justify or condemn anything**, and
reporting it alone invites whichever conclusion the reader already held.

So this pairs the cost with a yield signal taken from the same window: after the wake
timestamp, did the session actually MUTATE anything, or did it only emit text?

    mutating   Write · Edit · NotebookEdit · a Bash call that commits, pushes,
               or creates an issue/PR/comment
    reading    everything else — Read, Grep, Glob, a plain query
    text-only  no tool calls at all

⚠ What this does NOT establish, stated because the temptation is obvious: a mutation is
not automatically valuable, and a text-only turn is not automatically waste — a correct
"BLOCKED, and here is why" is exactly what a blocked agent should produce. This
separates *acted* from *did not act*. Judging the action is still a person's job.

⚠ And it cannot attribute across the shared credential: a git commit made by a session
is visible here only because the session's own transcript records the call. Two sessions
committing under one identity are not separable by this tool, or by any other we have.
"""
import argparse, glob, json, os, re, sys
from datetime import datetime, timezone

MUTATING_TOOLS = {"Write", "Edit", "NotebookEdit", "MultiEdit"}
MUTATING_SHELL = re.compile(
    r"\b(git\s+(commit|push|tag)|gh\s+(issue|pr)\s+(create|comment|edit|close)|"
    r"gh\s+api\b[^|]*-X\s*(POST|PATCH|PUT|DELETE))", re.I)


def parse_ts(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def scan(path, since):
    """Return (tokens_after, mutations, reads, text_turns) for records after `since`."""
    first_depth = last_depth = None
    mutations = reads = text_turns = 0
    for line in open(path, errors="replace"):
        try:
            rec = json.loads(line)
        except Exception:
            continue
        ts = parse_ts(rec.get("timestamp"))
        msg = rec.get("message")
        if not isinstance(msg, dict):
            continue
        if msg.get("role") == "assistant" and msg.get("usage"):
            u = msg["usage"]
            depth = (u.get("input_tokens", 0) + u.get("cache_read_input_tokens", 0)
                     + u.get("cache_creation_input_tokens", 0) + u.get("output_tokens", 0))
            if ts and ts < since:
                first_depth = depth            # last reading BEFORE the window
            else:
                last_depth = depth
        if not ts or ts < since:
            continue
        if msg.get("role") != "assistant":
            continue
        content = msg.get("content")
        if not isinstance(content, list):
            continue
        used = False
        for block in content:
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            used = True
            name = block.get("name", "")
            args = json.dumps(block.get("input", {}))
            if name in MUTATING_TOOLS or MUTATING_SHELL.search(args):
                mutations += 1
            else:
                reads += 1
        if not used:
            text_turns += 1
    cost = (last_depth - first_depth) if (last_depth and first_depth) else None
    return cost, mutations, reads, text_turns


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", required=True,
                    help="ISO timestamp of the wake, e.g. 2026-08-19T17:29:16Z")
    ap.add_argument("--active-hours", type=float, default=6.0)
    args = ap.parse_args()

    since = parse_ts(args.since if args.since.endswith("Z") else args.since + "Z")
    if since is None:
        sys.exit(f"unparseable timestamp: {args.since}")

    # ⛔ A window in the future returns zero sessions and reads exactly like a quiet
    # fleet. Measured: a wake logged at 17:29:16 LOCAL was queried as 17:29:16Z while
    # the clock read 16:39Z, so the query asked about the next ten minutes and answered
    # "nothing happened". Transcript timestamps are UTC; wall-clock logs usually are not.
    now = datetime.now(timezone.utc)
    if since > now:
        sys.exit(f"⛔ --since {since.isoformat()} is in the FUTURE (now {now.isoformat()[:19]}Z). "
                 f"This would return zero sessions and look like a quiet fleet. "
                 f"Local time is not Z — convert it.")
    if (now - since).total_seconds() > 12 * 3600:
        print(f"⚠ window is {(now - since).total_seconds()/3600:.1f}h wide — it will span "
              f"compactions, and a session that compacted inside it reports a NEGATIVE cost "
              f"that is a context reset, not a saving.", file=sys.stderr)

    rows = []
    for proj in glob.glob(os.path.expanduser("~/.claude/projects/*")):
        for path in glob.glob(os.path.join(proj, "*.jsonl")):
            if (datetime.now(timezone.utc).timestamp() - os.path.getmtime(path)
                    > args.active_hours * 3600):
                continue
            names = []
            for line in open(path, errors="replace"):
                if '"custom-title"' in line or '"agent-name"' in line:
                    try:
                        rec = json.loads(line)
                    except Exception:
                        continue
                    n = rec.get("customTitle") or rec.get("agentName")
                    if n and n not in names:
                        names.append(n)
            cost, mut, rd, txt = scan(path, since)
            if cost is None and not (mut or rd or txt):
                continue
            rows.append((os.path.basename(path)[:8], "/".join(names) or "(unnamed)",
                         cost, mut, rd, txt))
    rows.sort(key=lambda r: -(r[2] or 0))

    print(f"{'session':<10}{'name':<26}{'cost':>9}{'mutate':>8}{'read':>6}{'text':>6}  verdict")
    tc = tm = 0
    for sess, name, cost, mut, rd, txt in rows:
        tc += cost or 0
        tm += mut
        if mut:
            v = "WORK"
        elif rd:
            v = "looked, did not act"
        elif txt:
            v = "⚠ text only"
        else:
            v = "silent"
        print(f"{sess:<10}{name[:26]:<26}{(f'{cost:+,}' if cost else '-'):>9}"
              f"{mut:>8}{rd:>6}{txt:>6}  {v}")
    print(f"\ncost {tc:,} tokens · {tm} mutating actions across {len(rows)} sessions",
          file=sys.stderr)
    if tm == 0 and tc > 0:
        print("⛔ COST WITH NO YIELD — every woken session consumed context and mutated "
              "nothing. That is the signature of churn, and it is the reading a "
              "cost-only instrument cannot produce.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
