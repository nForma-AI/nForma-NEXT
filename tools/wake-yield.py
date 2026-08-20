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

# ⛔ Measured undercount, on a two-hour window whose contents were known by
# construction: 28 counted, 16 distinct forge-write blocks missed — a 36%
# undercount, counting ONLY the unarguable ones. The misses were `gh pr merge`
# (8) and `gh api graphql` mutations (7, posting review replies and resolving
# threads). Both are squarely inside what the docstring promises to catch.
#
# ⚠ The bias has a sign. An agent using the forge's REST porcelain scores as
# WORK; one doing the same work through graphql or `pr merge` scores as churn.
# The instrument rewards a calling convention, not an action.
MUTATING_SHELL = re.compile(
    r"\b(git\s+(commit|push|tag)|"
    r"gh\s+(issue|pr)\s+(create|comment|edit|close|merge|ready|review)|"
    r"gh\s+release\s+(create|edit|delete)|"
    r"gh\s+api\b[^|]*(-X|--method)\s*(POST|PATCH|PUT|DELETE))", re.I)

# graphql needs its own test: it is POST by default, so there is no -X to match,
# and a graphql QUERY must not count as a mutation.
MUTATING_GRAPHQL = re.compile(r"gh\s+api\s+graphql[\s\S]*\bmutation\b", re.I)

# ⛔ The list above is ENUMERATED, and a shell can mutate in unbounded ways —
# a heredoc redirect, sed -i, a python one-liner that opens a file for writing.
# Rather than pretend the enumeration is complete, anything that matches neither
# the mutating forms nor this read-only set is counted as UNCLASSIFIED and
# reported. A coverage gap that is visible can be judged; one folded into
# "reads" is indistinguishable from an agent that did nothing.
READ_ONLY_SHELL = re.compile(
    r"^\s*(git\s+(status|log|diff|show|rev-list|rev-parse|fetch|ls-files|cherry|"
    r"merge-base|worktree\s+list|branch\s+(-r|--list|--show-current))|"
    r"gh\s+\w+\s+(view|list|status|checks)|"
    # `gh api` is read-only ONLY because classify() tests the mutating forms
    # first — -X/--method POST|PATCH|PUT|DELETE and a graphql `mutation`. Move
    # this above them and every forge write becomes a read.
    r"gh\s+api\b|"
    r"grep|rg|cat|head|tail|less|ls|find|wc|jq|sort|uniq|awk|echo|date|which|"
    r"pgrep|sed\s+-n|base64|curl\s+-s)\b", re.I)


# A real command is compound: `cd /tmp && gh pr view … | jq …`. Anchoring the
# read-only test at the start of the whole string therefore matched almost
# nothing and pushed 1,032 of 1,244 actions into UNCLASSIFIED — a bucket that
# swallows everything is as uninformative as one that swallows nothing. Segments
# are classified individually and a command is read-only only if EVERY segment is.
SEGMENT_SPLIT = re.compile(r"&&|\|\||;|\||\n")
CD_OR_ENV = re.compile(r"^\s*(cd\s+\S+|[A-Z_][A-Z0-9_]*=\S*)\s*$")


def read_only_command(command):
    segments = [seg for seg in SEGMENT_SPLIT.split(command) if seg.strip()]
    if not segments:
        return False
    checked = 0
    for seg in segments:
        if CD_OR_ENV.match(seg):
            continue                       # navigation is not an action
        if not READ_ONLY_SHELL.search(seg.strip()):
            return False
        checked += 1
    # A command that is nothing but `cd` establishes nothing either way; treat it
    # as read rather than manufacturing an unclassified.
    return True if checked or segments else False


def classify(name, args, command):
    """mutating · read · unclassified. `command` is the Bash string, if any."""
    if name in MUTATING_TOOLS:
        return "mutating"
    if MUTATING_SHELL.search(args) or MUTATING_GRAPHQL.search(args):
        return "mutating"
    if command is None:
        return "read"                      # a non-Bash tool that is not in MUTATING_TOOLS
    return "read" if read_only_command(command) else "unclassified"


def parse_ts(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def scan(path, since):
    """Return (cost, mutations, reads, unclassified, text_turns) after `since`."""
    first_depth = last_depth = None
    mutations = reads = unclassified = text_turns = 0
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
            inp = block.get("input", {})
            args = json.dumps(inp)
            command = inp.get("command") if name == "Bash" and isinstance(inp, dict) else None
            kind = classify(name, args, command)
            if kind == "mutating":
                mutations += 1
            elif kind == "read":
                reads += 1
            else:
                unclassified += 1
        if not used:
            text_turns += 1
    cost = (last_depth - first_depth) if (last_depth and first_depth) else None
    return cost, mutations, reads, unclassified, text_turns


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
            cost, mut, rd, unk, txt = scan(path, since)
            if cost is None and not (mut or rd or unk or txt):
                continue
            rows.append((os.path.basename(path)[:8], "/".join(names) or "(unnamed)",
                         cost, mut, rd, unk, txt))
    rows.sort(key=lambda r: -(r[2] or 0))

    print(f"{'session':<10}{'name':<26}{'cost':>9}{'mutate':>8}{'read':>6}{'??':>5}"
          f"{'text':>6}  verdict")
    tc = tm = tu = 0
    for sess, name, cost, mut, rd, unk, txt in rows:
        tc += cost or 0
        tm += mut
        tu += unk
        if mut:
            v = "WORK"
        elif unk:
            # ⛔ Not "looked, did not act". The tool cannot see what these were,
            # and folding a coverage gap into the read bucket manufactures the
            # churn verdict this instrument exists to make trustworthy.
            v = f"⚠ {unk} UNCLASSIFIED — no verdict"
        elif rd:
            v = "looked, did not act"
        elif txt:
            v = "⚠ text only"
        else:
            v = "silent"
        print(f"{sess:<10}{name[:26]:<26}{(f'{cost:+,}' if cost else '-'):>9}"
              f"{mut:>8}{rd:>6}{unk:>5}{txt:>6}  {v}")
    print(f"\ncost {tc:,} tokens · {tm} mutating actions · {tu} unclassified "
          f"across {len(rows)} sessions", file=sys.stderr)
    if tm == 0 and tc > 0 and tu == 0:
        print("⛔ COST WITH NO YIELD — every woken session consumed context and mutated "
              "nothing. That is the signature of churn, and it is the reading a "
              "cost-only instrument cannot produce.", file=sys.stderr)
    elif tm == 0 and tc > 0 and tu:
        print(f"⚠ NO VERDICT — 0 mutations counted, but {tu} shell actions were "
              f"unclassified. 'No yield' cannot be distinguished from 'yield the "
              f"classifier does not cover'.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
