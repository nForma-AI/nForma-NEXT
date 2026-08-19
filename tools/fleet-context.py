#!/usr/bin/env python3
"""Fleet context depth — the instrument behind TEAMLEAD §25 and the 90% friction report.

Reports every active agent session's context usage, so that "compact this agent"
and "collect this agent's friction report" are decisions made on a number rather
than on a proxy.

Why this exists: two roles independently inferred a context state from a proxy
(an empty input box; an unread percentage) and were wrong in the dangerous
direction — one re-tasked agents believed to have headroom, one recommended
compacting a session at 79%.

Exit status is meaningful:
    0  no session at or above --threshold
    1  at least one session at or above --threshold   (use this to gate an action)
    2  the scan itself failed to establish anything   (never read as "all clear")

⚠ Read the caveats in README before acting on a row.
"""
import argparse, glob, json, os, sys, time

LIMIT_DEFAULT = 1_000_000


def session_depth(path):
    """Context depth = the prompt size of the LAST COMPLETED assistant turn.

    A lower bound: a session mid-turn is already higher than this reports.
    Returns (name, depth) or (name, None) when no assistant turn carries usage.
    """
    name, last = None, None
    with open(path, errors="replace") as fh:
        for line in fh:
            try:
                rec = json.loads(line)
            except Exception:
                continue                      # a partial trailing write is normal
            if rec.get("type") in ("custom-title", "agent-name"):
                name = rec.get("customTitle") or rec.get("agentName") or name
            msg = rec.get("message")
            if isinstance(msg, dict) and msg.get("role") == "assistant" and msg.get("usage"):
                last = msg["usage"]
    if last is None:
        return name, None
    return name, (last.get("input_tokens", 0)
                  + last.get("cache_read_input_tokens", 0)
                  + last.get("cache_creation_input_tokens", 0)
                  + last.get("output_tokens", 0))


def scan(active_within_s, limit):
    """Sweep EVERY project directory.

    Not the current one: an agent working in a git worktree gets its own project
    directory, and a single-directory scan silently omits it. Measured — a pane at
    97.7% was missed exactly this way.
    """
    rows, unreadable = [], 0
    roots = glob.glob(os.path.expanduser("~/.claude/projects/*"))
    if not roots:
        return None, 0, 0                      # nothing to scan is not "all clear"
    for root in roots:
        for path in glob.glob(os.path.join(root, "*.jsonl")):
            try:
                idle_s = time.time() - os.path.getmtime(path)
                if idle_s > active_within_s:
                    continue
                name, depth = session_depth(path)
            except Exception:
                unreadable += 1
                continue
            if depth is None:
                continue
            rows.append({"name": name or "(unnamed)",
                         "depth": depth,
                         "pct": 100.0 * depth / limit,
                         "idle_min": int(idle_s // 60),
                         "project": os.path.basename(root)[-28:]})
    return sorted(rows, key=lambda r: -r["depth"]), unreadable, len(roots)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--threshold", type=float, default=90.0,
                    help="percent at which a session is reported as due (default 90)")
    ap.add_argument("--active-hours", type=float, default=6.0)
    ap.add_argument("--limit", type=int, default=LIMIT_DEFAULT)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--quiet", action="store_true", help="print only sessions at/over threshold")
    args = ap.parse_args()

    rows, unreadable, roots = scan(args.active_hours * 3600, args.limit)
    if rows is None:
        print("SCAN FAILED: no project directories found — this is not 'all clear'",
              file=sys.stderr)
        return 2

    due = [r for r in rows if r["pct"] >= args.threshold]

    if args.json:
        print(json.dumps({"rows": rows, "due": due, "unreadable": unreadable,
                          "roots_scanned": roots}, indent=2))
    else:
        for r in (due if args.quiet else rows):
            mark = "  <-- DUE" if r["pct"] >= args.threshold else ""
            print(f"{r['depth']:>9,} {r['pct']:>6.1f}%  {r['name']:<14} "
                  f"{r['idle_min']:>4}m  {r['project']}{mark}")
        if not args.quiet:
            print(f"\n{len(rows)} active session(s) across {roots} project dir(s); "
                  f"{len(due)} at/over {args.threshold:.0f}%", file=sys.stderr)

    # An unreadable transcript is not a low-context transcript. Say so loudly.
    if unreadable:
        print(f"⚠ {unreadable} transcript(s) unreadable — their depth is UNKNOWN, not zero",
              file=sys.stderr)

    return 1 if due else 0


if __name__ == "__main__":
    sys.exit(main())
