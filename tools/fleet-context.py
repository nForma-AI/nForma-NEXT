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

    ⚠ The returned name is SELF-REPORTED and is NOT an identity.

    Measured: one transcript carries TEAMLEAD, IMPLEMENTER2 and DEV2, and the
    records ALTERNATE — TEAMLEAD/DEV2/TEAMLEAD/DEV2 for a hundred cycles. A
    rename does not oscillate, so these records are not a rename history and
    last-wins is not "the current name": it is whichever record was written
    last. Reading it that way produced a confident false claim that TEAMLEAD had
    been renamed to DEV2, while both panes were in fact live and correctly named.

    `names` is therefore the DISTINCT set. More than one entry means the file
    cannot name its own session, not that the session was renamed.

    ⛔ There is no key joining a session to a Daintree pane: terminal.list gives
    id/title/worktreeId and no session id; the transcript gives a session id and
    a self-reported title. The only shared field is the title, which is stale on
    one side and duplicated on the other. Treat the depth as sound and the
    attribution as unverified.

    Returns (names, depth); names is an ordered list of every title seen.
    """
    names, last = [], None
    with open(path, errors="replace") as fh:
        for line in fh:
            try:
                rec = json.loads(line)
            except Exception:
                continue                      # a partial trailing write is normal
            if rec.get("type") in ("custom-title", "agent-name"):
                n = rec.get("customTitle") or rec.get("agentName")
                if n and n not in names:      # distinct set: these records ALTERNATE
                    names.append(n)
            msg = rec.get("message")
            if isinstance(msg, dict) and msg.get("role") == "assistant" and msg.get("usage"):
                last = msg["usage"]
    if last is None:
        return names, None
    return names, (last.get("input_tokens", 0)
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
                names, depth = session_depth(path)
            except Exception:
                unreadable += 1
                continue
            if depth is None:
                continue
            rows.append({"name": (names[-1] if names else "(unnamed)"),
                         "names": names,
                         "ambiguous": len(names) > 1,
                         "session": os.path.basename(path)[:8],
                         "depth": depth,
                         "pct": 100.0 * depth / limit,
                         "idle_min": int(idle_s // 60),
                         "project": os.path.basename(root)[-28:]})
    return sorted(rows, key=lambda r: -r["depth"]), unreadable, len(roots)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--threshold", type=float, default=80.0,
                    help="percent at which a session is reported as due (default 80). "
                         "80 rather than 90 because the binding cost of a friction report "
                         "is VERIFICATION, not composition — measured at ~2-2.5%% to write "
                         "and roughly two thirds of that re-deriving specifics.")
    ap.add_argument("--active-hours", type=float, default=6.0)
    ap.add_argument("--limit", type=int, default=LIMIT_DEFAULT)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--quiet", action="store_true", help="print only sessions at/over threshold")
    ap.add_argument("--snapshot", metavar="FILE", help="write the current reading, for a later --since")
    ap.add_argument("--since", metavar="FILE",
                    help="report the DELTA against a snapshot — what an event COST the fleet in "
                         "context. A broadcast that knocks seven agents off their in-flight work "
                         "is not free, and nothing else measures it.")
    args = ap.parse_args()

    rows, unreadable, roots = scan(args.active_hours * 3600, args.limit)
    if rows is None:
        print("SCAN FAILED: no project directories found — this is not 'all clear'",
              file=sys.stderr)
        return 2

    due = [r for r in rows if r["pct"] >= args.threshold]

    if args.snapshot:
        with open(args.snapshot, "w") as fh:
            json.dump({r["session"]: r["depth"] for r in rows}, fh)
        print(f"snapshot: {len(rows)} sessions -> {args.snapshot}", file=sys.stderr)

    if args.since:
        try:
            before = json.load(open(args.since))
        except Exception as exc:
            # An unreadable snapshot is not "no change". Fail loudly.
            print(f"⛔ cannot read {args.since}: {exc}", file=sys.stderr)
            return 2
        total = 0
        print(f"{'session':<10}{'before':>10}{'after':>10}{'delta':>10}  name (self-reported)")
        for r in rows:
            prev = before.get(r["session"])
            if prev is None:
                print(f"{r['session']:<10}{'-':>10}{r['depth']:>10,}{'NEW':>10}  {r['name']}")
                continue
            d = r["depth"] - prev
            total += max(d, 0)              # a large drop is a compaction, not a cost
            note = "  <-- COMPACTED" if d < -300_000 else ""
            print(f"{r['session']:<10}{prev:>10,}{r['depth']:>10,}{d:>+10,}  {r['name']}{note}")
        for sess, prev in before.items():
            if not any(r["session"] == sess for r in rows):
                print(f"{sess:<10}{prev:>10,}{'-':>10}{'GONE':>10}  "
                      f"⚠ vanished — not the same as idle")
        print(f"\nfleet-wide context consumed since snapshot: {total:,} tokens "
              f"({total / 1e6 * 100:.1f}% of one 1M window)", file=sys.stderr)

    if args.json:
        print(json.dumps({"rows": rows, "due": due, "unreadable": unreadable,
                          "roots_scanned": roots}, indent=2))
    else:
        for r in (due if args.quiet else rows):
            mark = "  <-- DUE" if r["pct"] >= args.threshold else ""
            # A name this session also answered to earlier. Printing only the last
            # one turns a guess into an assertion.
            warn = f"  ⚠name-ambiguous({'/'.join(r['names'])})" if r["ambiguous"] else ""
            print(f"{r['depth']:>9,} {r['pct']:>6.1f}%  {r['name']:<14} {r['session']}  "
                  f"{r['idle_min']:>4}m  {r['project']}{mark}{warn}")
        if not args.quiet:
            amb = sum(1 for r in rows if r["ambiguous"])
            print(f"\n{len(rows)} active session(s) across {roots} project dir(s); "
                  f"{len(due)} at/over {args.threshold:.0f}%", file=sys.stderr)
            print("⚠ names are SELF-REPORTED, not identities, and cannot be joined to a "
                  "Daintree pane. Depth is per-session and sound; attribution is not."
                  + (f" {amb} session(s) answered to more than one name." if amb else ""),
                  file=sys.stderr)

    # An unreadable transcript is not a low-context transcript. Say so loudly.
    if unreadable:
        print(f"⚠ {unreadable} transcript(s) unreadable — their depth is UNKNOWN, not zero",
              file=sys.stderr)

    return 1 if due else 0


if __name__ == "__main__":
    sys.exit(main())
