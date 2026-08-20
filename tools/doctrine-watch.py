#!/usr/bin/env python3
"""Which roles' doctrine changed under them, and who has not been told.

⛔ WHY THIS EXISTS. A prompt and a goal file load at SESSION START. Measured
2026-08-19: every amendment made in one evening reached ZERO running agents at the
moment it landed, and the fleet's standing conclusion became "a relaunch is the only
complete-delivery channel". That conclusion is wrong in the expensive direction.

⇒ The read is available ON DEMAND and nothing TRIGGERS it. Any pane can run
`git show origin/main:goals/README.md` this second. THE GAP IS A TRIGGER, NOT A
PRIMITIVE — so the fix is a nudge, not a restart. A relaunch buys exactly two things
that cannot be delivered live (cwd/worktree, and process env) and costs every pane its
working context.

⛔ WHAT THIS TOOL DOES NOT DO, stated first because it is the load-bearing limit.
It reports that a role's doctrine MOVED and that the role has not read the new
revision. It CANNOT establish that a notified agent re-read rather than noting the
notification and continuing on the copy it loaded. That is the difference between a
trigger and a guarantee, and it is UNMEASURED.

⚠ A notification is not authority. What this emits is a POINTER — a ref and a path.
It must never carry the changed text, an instruction, or a grant. The pane input box is
unauthenticated; a message that carries content there is indistinguishable from a
forgery that carries content there. See goals/RESERVED-ACTIONS.md.

Exit: 0 nothing to tell anyone · 1 at least one role is behind · 2 established nothing
"""
import argparse, json, os, subprocess, sys, glob, re

REPO_MARK = "nForma-NEXT"
DEVS = [f"DEV{i}" for i in range(1, 6)]
ALL_ROLES = ["TEAMLEAD", "ARCHITECT", "DEVOPS", "DX"] + DEVS

# path -> roles it binds. A file binding every role is listed as ALL.
BINDS = {
    "prompts/TEAMLEAD.md":  ["TEAMLEAD"],
    "prompts/ARCHITECT.md": ["ARCHITECT"],
    "prompts/DEVOPS.md":    ["DEVOPS"],
    "prompts/DX.md":        ["DX"],
    "prompts/DEV.md":       DEVS,
    "goals/architect-technical-integrity.md": ["ARCHITECT"],
    "goals/devops-substrate-and-fleet.md":    ["DEVOPS"],
    "goals/dx-engineering-effectiveness.md":  ["DX"],
    "goals/dev-implementation.md":            DEVS,
    "goals/README.md":            ALL_ROLES,
    "goals/RESERVED-ACTIONS.md":  ALL_ROLES,
}

def void(msg):
    print(f"⛔ VOID: {msg}", file=sys.stderr)
    print("      established nothing about any role's doctrine — this is UNKNOWN, never 'all current'",
          file=sys.stderr)
    sys.exit(2)

def git(*a, cwd=None):
    r = subprocess.run(["git", *a], capture_output=True, text=True, cwd=cwd)
    return r.returncode, r.stdout.strip(), r.stderr.strip()

def main_tree():
    """⚠ NEVER `rev-parse --show-toplevel`: in a worktree that returns the WORKTREE.
    Measured three times in one evening, each a confident wrong answer."""
    rc, out, _ = git("worktree", "list", "--porcelain")
    if rc != 0:
        void("`git worktree list` failed — not a git repository?")
    for line in out.splitlines():
        if line.startswith("worktree "):
            return line.split(" ", 1)[1]
    void("`git worktree list` named no tree")

def changed_between(base, head, root):
    rc, out, err = git("diff", "--name-only", f"{base}..{head}", cwd=root)
    if rc != 0:
        void(f"cannot diff {base}..{head}: {err or 'unknown'}")
    return [p for p in out.splitlines() if p in BINDS]

def transcripts_for(root):
    slug = root.replace("/", "-")
    return glob.glob(os.path.expanduser(f"~/.claude/projects/{slug}/*.jsonl"))

def role_of(path):
    """The role a session was BOOTSTRAPPED as. A name can be changed; this cannot."""
    try:
        with open(path, errors="replace") as fh:
            for line in fh:
                if '"type":"user"' not in line and '"type": "user"' not in line:
                    continue
                m = re.search(r"You are ([A-Z]+[0-9]*)\.", line)
                if m:
                    return m.group(1)
    except OSError:
        return None
    return None

def has_read(path, blob_paths, changed_at):
    """Has this session READ any of these files SINCE the change landed?

    ⛔ Two things this must not do, both learned by doing them.
    · It must match the tool CALL, never prose. A transcript that DISCUSSES
      goals/README.md is not one that read it — the first version of this function
      matched any occurrence and its known-positive could not fire, because every
      transcript mentions these paths constantly.
    · It must require the read to be LATER than the change. A read from before the
      amendment landed proves the agent saw the OLD revision, which is the condition
      being reported, not its remedy.
    """
    import datetime
    try:
        fh = open(path, errors="replace")
    except OSError:
        return False
    with fh:
        for line in fh:
            if not any(bp in line for bp in blob_paths):
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            ts = rec.get("timestamp")
            if ts:
                try:
                    when = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
                except Exception:
                    when = None
                if when is not None and when < changed_at:
                    continue
            msg = rec.get("message") or {}
            content = msg.get("content")
            if not isinstance(content, list):
                continue
            for b in content:
                if not isinstance(b, dict) or b.get("type") != "tool_use":
                    continue
                inp = b.get("input") or {}
                probe = f"{inp.get('command','')} {inp.get('file_path','')} {inp.get('pattern','')}"
                if any(bp in probe for bp in blob_paths):
                    return True
    return False


def changed_at_ts(base, head, paths, root):
    """When the newest of these files last moved. A read before this proves nothing."""
    newest = 0
    for p in paths:
        rc, out, _ = git("log", "-1", "--format=%ct", f"{base}..{head}", "--", p, cwd=root)
        if rc == 0 and out.strip().isdigit():
            newest = max(newest, int(out.strip()))
    return newest

def main():
    ap = argparse.ArgumentParser(description="Report which roles' doctrine moved under them.")
    ap.add_argument("--since", help="baseline ref or SHA (default: the last recorded watermark)")
    ap.add_argument("--head", default="origin/main", help="ref to compare against")
    ap.add_argument("--root", help="repository root (default: the MAIN worktree)")
    ap.add_argument("--self-test", action="store_true", help="run the controls and exit")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    root = args.root or main_tree()
    if REPO_MARK not in root:
        void(f"root {root!r} is not this repository — refusing to report on another tree")

    rc, head, err = git("rev-parse", args.head, cwd=root)
    if rc != 0:
        void(f"cannot resolve {args.head}: {err or 'unknown ref'}")

    base = args.since
    if not base:
        wm = os.path.join(root, ".claude", "doctrine-watermark")
        if os.path.exists(wm):
            base = open(wm).read().strip()
    if not base:
        void("no baseline: pass --since <sha>, or write one to .claude/doctrine-watermark")

    rc, base_sha, err = git("rev-parse", base, cwd=root)
    if rc != 0:
        void(f"cannot resolve baseline {base}: {err or 'unknown ref'}")

    if base_sha == head:
        print(f"doctrine watch — baseline {base_sha[:8]} == {args.head} {head[:8]}")
        print("  no doctrine file changed. Nothing to tell anyone.")
        print("⚠ 'nothing to tell' is not 'every agent is current' — a role that was already")
        print("  behind at the baseline stays behind and this tool cannot see it.")
        return 0

    changed = changed_between(base_sha, head, root)
    print(f"doctrine watch — {base_sha[:8]}..{head[:8]}")
    if not changed:
        print(f"  {len(changed)} doctrine file(s) changed. Nothing to tell anyone.")
        print("⚠ Other files changed in that range; only the paths that BIND a role are watched.")
        return 0

    affected = {}
    for p in changed:
        for r in BINDS[p]:
            affected.setdefault(r, []).append(p)

    seen = {}
    for t in transcripts_for(root):
        r = role_of(t)
        if r:
            seen.setdefault(r, []).append(t)

    behind, told, unknown = [], [], []
    for r in sorted(affected):
        paths = affected[r]
        sessions = seen.get(r, [])
        if not sessions:
            unknown.append((r, paths))
            continue
        cutoff = changed_at_ts(base_sha, head, paths, root)
        if any(has_read(s, paths, cutoff) for s in sessions):
            told.append((r, paths))
        else:
            behind.append((r, paths))

    for r, paths in behind:
        print(f"  BEHIND     {r:<10} {', '.join(paths)}")
    for r, paths in told:
        print(f"  read-since {r:<10} {', '.join(paths)}")
    for r, paths in unknown:
        print(f"  UNKNOWN    {r:<10} no transcript found — never 'current'")

    print(f"\n{len(behind)} behind · {len(told)} read-since · {len(unknown)} UNKNOWN"
          f" · {len(changed)} doctrine file(s) changed")
    print("⛔ 'read-since' proves the agent OPENED the file. It does not prove the agent is")
    print("   OBEYING it — a read is not a load, and compaction can drop text that was read.")
    print("⚠ UNKNOWN is not a pass. It is the count this instrument did not establish.")
    return 1 if behind else 0

def self_test():
    """Controls. ⛔ Every one must be reachable in the REPAIRED state — a control that
    only fires while something is broken goes silent the moment it is fixed."""
    ok = True
    def check(label, got, want):
        nonlocal ok
        good = got == want
        ok = ok and good
        print(f"  {'ok  ' if good else 'FAIL'}  {label} (got {got}, want {want})")

    root = main_tree()
    here = os.path.dirname(os.path.abspath(__file__))
    me = os.path.join(here, os.path.basename(__file__))

    def run(*a):
        r = subprocess.run([sys.executable, me, *a], capture_output=True, text=True)
        return r.returncode

    rc, head, _ = git("rev-parse", "origin/main", cwd=root)
    # known-NEGATIVE, from real data: baseline == head must report nothing, exit 0
    check("baseline == head reports nothing", run("--since", head), 0)
    # known-POSITIVE, from real data: a range that certainly touched a doctrine file
    rc2, older, _ = git("rev-list", "--max-count=1", "--skip=40", head, cwd=root)
    if rc2 == 0 and older:
        chg = changed_between(older, head, root)
        if chg:
            check("a range that moved doctrine exits 1", run("--since", older), 1)
        else:
            print("  ----  no doctrine file moved in the sampled range — positive NOT exercised")
            ok = False
    else:
        print("  ----  history too short to construct the positive — NOT exercised")
        ok = False
    # VOID paths
    check("unresolvable baseline exits 2", run("--since", "definitely-not-a-ref"), 2)
    check("unresolvable head exits 2", run("--since", head, "--head", "nope/nope"), 2)
    check("root outside this repo exits 2", run("--since", head, "--root", "/tmp"), 2)
    check("unrecognised flag exits 2", run("--not-a-flag"), 2)

    print("\n" + ("all controls reachable" if ok else "⛔ a control did not fire — VERDICT REFUSED"))
    return 0 if ok else 3

if __name__ == "__main__":
    sys.exit(main())
