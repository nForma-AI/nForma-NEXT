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

def delta_for(base, head, path, root):
    """How BIG was the change, and WHERE — so a role can read the delta, not the file.

    ⛔ SIZE IS NOT SEVERITY, and this must never be read as though it were. A six-line
    strike-through that withdraws a reservation is small and load-bearing; an eighty-line
    re-wrap is large and binds nobody. DEVOPS held a withdrawn reservation for a day
    precisely because every BEHIND row looked identical — the remedy is to make the delta
    CHEAP TO READ, never to let it be cheaply SKIPPED.

    ⇒ Returns (added, removed, [(start, end)]) in HEAD's numbering, or None if the diff
    established nothing — in which case the caller must say so rather than print zeros.
    """
    rc, out, _ = git("diff", "--unified=0", f"{base}..{head}", "--", path, cwd=root)
    if rc != 0:
        return None
    added = removed = 0
    spans = []
    for line in out.splitlines():
        if line.startswith("@@"):
            m = re.search(r"\+(\d+)(?:,(\d+))?", line)
            if m:
                start = int(m.group(1))
                count = int(m.group(2)) if m.group(2) is not None else 1
                # a pure deletion reports +N,0 — point at the seam, not at nothing
                spans.append((start, start + count - 1) if count else (start, start))
        elif line.startswith("+") and not line.startswith("+++"):
            added += 1
        elif line.startswith("-") and not line.startswith("---"):
            removed += 1
    return added, removed, spans


def read_delta_cmd(path, spans, head_sha):
    """The exact command, not a description of one.

    ★ `doctrine-version.py` credits a delta read (`sed -n 'A,Bp'`) as SAW-LATER, so
    emitting the command a role should run makes the cheap read the DETECTABLE one too.
    A pane that follows this line is visible to the instrument that asks whether it read.

    ⛔ Pinned to the head SHA, never `HEAD` and never `origin/main`. Nine panes may share
    one tree, so a reader's `HEAD` can be somebody's feature branch; and refs are shared
    across worktrees, so `origin/main` can move between this line being printed and being
    run. Only a SHA names the revision this tool actually measured.
    """
    if not spans:
        return None
    merged, pad = [], 3
    for lo, hi in sorted(spans):
        lo = max(1, lo - pad); hi = hi + pad
        if merged and lo <= merged[-1][1] + 1:
            merged[-1] = (merged[-1][0], max(merged[-1][1], hi))
        else:
            merged.append((lo, hi))
    expr = ";".join(f"{lo},{hi}p" for lo, hi in merged)
    return f"git show {head_sha[:12]}:{path} | sed -n '{expr}'"


def transcripts_for(root):
    slug = root.replace("/", "-")
    return glob.glob(os.path.expanduser(f"~/.claude/projects/{slug}/*.jsonl"))

# ⚠ A `<system-reminder>` precedes the bootstrap in some transcripts and not
# others, so "the first user record" is not "the launch prompt" -- taking it
# verbatim reads a reminder as the bootstrap for a subset of panes.
_REMINDER = re.compile(r"<system-reminder>.*?</system-reminder>", re.S)
# ⛔ NOT `You are X\.` -- a period matched 0 of 9 live bootstraps, which all read
# "You are DX, an IMPLEMENTER ...". A trailing comma is the norm, not the edge.
# ⚠ TWO forms, both MEASURED in this fleet's live bootstraps, not imagined:
#   "You are DX, an IMPLEMENTER ..."         5 of 9
#   "You are taking over as MAINTAINER ..."  1 of 9
# ⇒ This is a SNAPSHOT of observed phrasing, not a closed set. A bootstrap whose
# wording is not here yields "" -- read it, recognised no role -- which is why ""
# and None are different values.
_ROLE = re.compile(r"You are (?:taking over as )?([A-Z][A-Z0-9]*)\b")

BOOTSTRAP_WINDOW = 40


def _bootstrap_text(path):
    """The launch prompt's text, or None if this file does not contain one.

    ⛔ Bounded to the first records ON PURPOSE. Scanning the whole file is what
    made the previous version wrong: see role_of.
    """
    try:
        with open(path, errors="replace") as fh:
            for i, line in enumerate(fh):
                if i > BOOTSTRAP_WINDOW:
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
                if isinstance(c, str):
                    t = c
                elif isinstance(c, list):
                    t = "".join(b.get("text", "") for b in c
                                if isinstance(b, dict) and b.get("type") == "text")
                else:
                    t = ""
                t = _REMINDER.sub("", t).strip()
                if t:
                    return t
    except OSError:
        return None
    return None


def role_of(path):
    """The role a session was BOOTSTRAPPED as. A name can be changed; this cannot.

    ⛔ THE PROMISE ABOVE WAS FALSE IN EVERY LIVE CASE. The previous version scanned
    the WHOLE FILE for `You are X.` and took the first hit anywhere. Measured over
    the nine active fleet transcripts: it resolved 2, and NEITHER came from a
    bootstrap.

      e4a7769d -> "DEV2"   from record 17155, a CORRECTION sent a day later:
                           "your identity was wrong ... You are DEV2". Its actual
                           bootstrap reads "You are taking over as MAINTAINER".
      6fc2dca8 -> "DEVOPS" from record 3132, inside a QUOTATION:
                           `3. "TEAMLEAD — ROLE ESTABLISHED. You are DEVOPS..."`

    ⇒ So it returned the mutable thing it promised immunity from, and a MENTION
    rather than a USE. The other seven returned None, which the code also uses for
    "could not read the file" -- one value for two states.

    ⚠ Three outcomes now, never two:
      None  the file could not be read, OR holds no launch prompt at all (a wake
            at the head means the launch is in another file) -- ESTABLISHED NOTHING
      ""    a launch prompt was read and names no role
      "DX"  a role, taken from the bootstrap record and nowhere else
    """
    t = _bootstrap_text(path)
    if t is None:
        return None                     # ⛔ unreadable or no launch prompt here
    m = _ROLE.search(t)
    return m.group(1) if m else ""      # read it; no role in it

def last_read_ts(path, blob_paths):
    """The NEWEST timestamp at which this session read any of these files, or None.

    ★ Same matcher as `has_read` — the tool CALL, never prose — but it returns WHEN
    rather than WHETHER. That distinction is the whole of #183: one stored watermark was
    answering two questions with opposite optima.
    """
    import datetime
    newest = None
    try:
        fh = open(path, errors="replace")
    except OSError:
        return None
    with fh:
        for line in fh:
            if not any(bp in line for bp in blob_paths):
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            ts = rec.get("timestamp")
            if not ts:
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
                    try:
                        when = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
                    except Exception:
                        continue
                    if newest is None or when > newest:
                        newest = when
    return newest


def derived_base(path, head, when, root):
    """The commit this role has actually SEEN for `path` — derived, never stored.

    ⛔ #183's ruling, from DEV1: a stored baseline is what decays. `changed_between` and
    `changed_at_ts` WANT an old base — a stale one only widens the search and the max still
    lands on the true last change, so BEHIND stays correct. `delta_for` wants a NEW base and
    a stale one makes the delta cumulative, which is #151's targeting decaying back into the
    defect it replaced.

    ⇒ One value, two propositions, opposite optima. So the delta baseline is DERIVED per
    role from that role's newest recorded read. A derived value cannot go stale.

    Falls back to the path's previous commit, then to None — and None now means VOID for that
    (role, path) pair, not "use the watermark": the watermark was deleted in #183 —
    correct for a role that has never read the file, because it needs everything.
    """
    if when is None:
        return None
    iso = __import__("datetime").datetime.utcfromtimestamp(when).strftime("%Y-%m-%dT%H:%M:%S")
    rc, out, _ = git("log", "-1", f"--before={iso}", "--format=%H", head, "--", path, cwd=root)
    if rc == 0 and out.strip():
        return out.strip()
    return None


def derived_scan(head, root, seen):
    """#183's remedy: NO GLOBAL BASELINE. Each (role, path) is judged against the newest commit
    of that path THAT ROLE HAS EVIDENCE OF READING.

    ⛔ WHY THE WATERMARK HAD TO GO, measured rather than argued (TEAMLEAD's ruling, #183):
        commits ever touching .claude/doctrine-watermark          1
        committed value        b2a3d470   322 behind origin/main
        shared working tree    eb222305   316 behind, UNCOMMITTED, 6 commits newer
    ⇒ NINE PANES, TWO BASELINES, and which you got depended on which tree you stood in. The file
      had no writer at all — one line read it and another told a HUMAN to write it, which in a
      shared tree is a working-tree edit, not a commit. ★ Two failure modes: nobody remembered,
      and the one who did had nowhere to put it that would persist.

    ★ A derived value cannot go stale, and it cannot fork per tree either.

    ⚠ VOID, NEVER BEHIND, WHERE EVIDENCE IS ABSENT — required by the ruling regardless of the
    rest. #58: *established nothing* is not *behind by zero*, and the old tool reported the second
    meaning the first. A pair with no recorded read is a pair this tool CANNOT judge.

    Returns (behind, told, void) as lists of (role, [paths]).
    """
    behind, told, void_pairs = {}, {}, {}
    for path, roles in sorted(BINDS.items()):
        for r in sorted(roles):
            sessions = seen.get(r, [])
            if not sessions:
                continue                      # UNKNOWN — the caller already reports this
            when = None
            for sess in sessions:
                t = last_read_ts(sess, [path])
                if t and (when is None or t > when):
                    when = t
            rbase = derived_base(path, head, when, root) if when else None
            if rbase is None:
                # ⛔ NOT "behind by zero". This role has no recorded read of this path, so the
                # question "has it changed since you read it" HAS NO BASE. Established nothing.
                void_pairs.setdefault(r, []).append(path)
                continue
            if path in changed_between(rbase, head, root):
                behind.setdefault(r, []).append(path)
            else:
                told.setdefault(r, []).append(path)
    tolist = lambda d: sorted((r, ps) for r, ps in d.items())
    return tolist(behind), tolist(told), tolist(void_pairs)


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
    ap.add_argument("--since", help="explicit baseline ref or SHA. ⚠ OVERRIDE ONLY — the default\n                                is DERIVED per (role, path); there is no stored baseline")
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

    seen = {}
    for t in transcripts_for(root):
        r = role_of(t)
        if r:
            seen.setdefault(r, []).append(t)

    # ⇒ #183, TEAMLEAD's ruling: DERIVED BY DEFAULT. The watermark is gone — it had one commit
    # in its entire history, no writer, and two live values that forked by working tree.
    # ⚠ `--since` remains as the EXPLICIT override, for asking about a range you name yourself.
    if not args.since:
        behind, told, void_pairs = derived_scan(head, root, seen)
        unknown = [(r, ["(no transcript)"]) for r in sorted(set(
            r for rs in BINDS.values() for r in rs) - set(seen))]
        print(f"doctrine watch — DERIVED per (role, path); no global baseline")
        print(f"  ⚠ each pair is judged against the newest commit of that path THAT ROLE has"
              f" evidence of reading. A derived value cannot go stale, and cannot fork per tree.")
        for r, paths in behind:
            print(f"  BEHIND     {r:<10} {', '.join(paths)}")
            for pth in paths:
                when = max((t for sess in seen.get(r, [])
                            for t in [last_read_ts(sess, [pth])] if t), default=None)
                rb = derived_base(pth, head, when, root)
                d = delta_for(rb, head, pth, root) if rb else None
                if d is None:
                    print(f"             ⚠ delta for {pth} ESTABLISHED NOTHING — size unknown")
                    continue
                a, rm, spans = d
                cmd = read_delta_cmd(pth, spans, head)
                print(f"             +{a}/-{rm} in {len(spans)} hunk(s) since {rb[:8]}"
                      f"{' — read just the delta:' if cmd else ''}")
                if cmd:
                    print(f"             {cmd}")
        for r, paths in told:
            print(f"  read-since {r:<10} {', '.join(paths)}")
        for r, paths in void_pairs:
            print(f"  ⛔ VOID     {r:<10} {', '.join(paths)}")
            print(f"             no recorded read of these paths — this tool CANNOT judge them.")
            print(f"             ⚠ VOID is not 'behind by zero' and not 'current' (#58).")
        for r, paths in unknown:
            print(f"  UNKNOWN    {r:<10} no transcript found — never 'current'")
        bp = sum(len(ps) for _, ps in behind)
        vp = sum(len(ps) for _, ps in void_pairs)
        print(f"  ---- {bp} (role,path) BEHIND · {sum(len(ps) for _, ps in told)} read-since"
              f" · {vp} VOID · {len(unknown)} role(s) UNKNOWN")
        # ⛔ VOID does not make the run a finding, and does not make it clean either. It is
        # counted and named; the exit code reports only what was ESTABLISHED.
        return 1 if bp else 0

    base = args.since

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
        # ⛔ PER PATH, not per path-SET. Both helpers already take a list; calling them with
        # the whole set is what produced two collapses in four lines:
        #   1. cutoff was max(change time) ACROSS paths, so a file read the moment it changed
        #      did not count if a DIFFERENT file changed later.
        #   2. one boolean decided all paths — read ONE of four and you were marked read-since
        #      on ALL FOUR, and told rows print no delta, so the three you never opened were
        #      reported current with no signal of any kind.
        # ⚠ The safe direction was visible (BEHIND next to a +0/-0 targeted delta, which is how
        # this was found). The dangerous direction was SILENT. (DEV1, #183.)
        # ⇒ A role may now appear in BOTH lists — behind on some paths, read-since on others.
        # That is the point: the verdict is a property of the (role, path) pair, never of the role.
        behind_paths, told_paths = [], []
        for p in paths:
            cutoff = changed_at_ts(base_sha, head, [p], root)
            if any(has_read(s, [p], cutoff) for s in sessions):
                told_paths.append(p)
            else:
                behind_paths.append(p)
        if behind_paths:
            behind.append((r, behind_paths))
        if told_paths:
            told.append((r, told_paths))

    deltas = {}
    for p in changed:
        deltas[p] = delta_for(base_sha, head, p, root)

    for r, paths in behind:
        print(f"  BEHIND     {r:<10} {', '.join(paths)}")
        for p in paths:
            # ⇒ #183: DERIVE this role's delta baseline from its newest recorded read.
            # ⚠ This is the --since OVERRIDE path. The default no longer has a global base at
            # all; here the caller named one, so a cumulative figure is meaningful.
            rbase = None
            for sess in seen.get(r, []):
                rbase = derived_base(p, head, last_read_ts(sess, [p]), root) or rbase
            d = delta_for(rbase, head, p, root) if rbase else deltas.get(p)
            # ⛔ ALWAYS print the cumulative line, even when it equals the targeted one.
            # Suppressing it when identical made a 4-file row print 3 cumulative against 4
            # targeted, so the pairs no longer aligned by position and a reader mis-attributed
            # numbers by one file. ⇒ "suppressed because identical" and "missing" arrived as
            # the same value — Class A, in the presentation of the fix built to remove it.
            cum = deltas.get(p)
            if rbase and cum and d:
                same = d[:2] == cum[:2]
                print(f"             ⚠ cumulative since the GIVEN baseline: +{cum[0]}/-{cum[1]}"
                      + ("  — SAME as targeted; you have seen none of it"
                         if same else
                         " — the targeted delta below is what YOU have not seen"))
            if d is None:
                print(f"             ⚠ delta for {p} ESTABLISHED NOTHING — size unknown, not small")
                continue
            a, rm, spans = d
            cmd = read_delta_cmd(p, spans, head)
            print(f"             +{a}/-{rm} in {len(spans)} hunk(s)"
                  f"{' — read just the delta:' if cmd else ''}")
            if cmd:
                print(f"             {cmd}")
    for r, paths in told:
        print(f"  read-since {r:<10} {', '.join(paths)}")
    for r, paths in unknown:
        print(f"  UNKNOWN    {r:<10} no transcript found — never 'current'")

    # ⚠ UNITS. The verdict is now per (role, path), so a role can appear in BOTH lists and a
    # bare count is ambiguous between roles and pairs. Both are printed, labelled.
    behind_pairs = sum(len(ps) for _, ps in behind)
    told_pairs = sum(len(ps) for _, ps in told)
    behind_roles = len({r for r, _ in behind})
    print(f"\n{behind_pairs} behind · {told_pairs} read-since · {len(unknown)} UNKNOWN"
          f" · {len(changed)} doctrine file(s) changed")
    print(f"  counted as (role, path) PAIRS, not roles. {behind_roles} distinct role(s) are"
          f" behind on at least one path; a role behind on one file and current on another now"
          f" appears in BOTH lines.")
    print("⚠ NOT comparable to a run before the per-path change (#183). Both directions move:"
          " falsely-BEHIND paths drop out, and paths that were falsely read-since APPEAR."
          " A rise or a fall are both consistent with the fix.")
    print("⛔ 'read-since' proves the agent OPENED the file. It does not prove the agent is")
    print("   OBEYING it — a read is not a load, and compaction can drop text that was read.")
    print("⚠ UNKNOWN is not a pass. It is the count this instrument did not establish.")
    if behind:
        print("⛔ +N/-M is SIZE, never SEVERITY. A six-line strike-through withdrawing a")
        print("   reservation binds you; an eighty-line re-wrap does not. The delta command")
        print("   exists to make the read CHEAP — it is not a licence to skip the small ones.")
    return 1 if behind else 0

def synthetic_case(check):
    """A known-positive and known-negative on a throwaway tree, OUTSIDE the live fleet.

    Returns True if both fired. ⚠ If the fixture cannot be built, this returns False and
    says so — an unbuildable control established nothing and must not read as a pass.
    """
    import tempfile, shutil, datetime
    base_dir = tempfile.mkdtemp(prefix="dw-synth-")
    # ⛔ the path must carry REPO_MARK or main() refuses the root — that guard is correct
    # and the fixture accommodates it rather than the fixture weakening the guard.
    root = os.path.join(base_dir, REPO_MARK)
    doc = "goals/RESERVED-ACTIONS.md"
    doc2 = "goals/dev-implementation.md"   # also BINDS DEV1 — needed for the per-path control
    slug = root.replace("/", "-")
    tdir = os.path.expanduser(f"~/.claude/projects/{slug}")
    try:
        os.makedirs(os.path.join(root, "goals"))
        def g(*a):
            return subprocess.run(["git", *a], cwd=root, capture_output=True, text=True)
        g("init", "-q")
        g("config", "user.email", "synth@localhost")
        g("config", "user.name", "synth")
        target = os.path.join(root, doc)
        target2 = os.path.join(root, doc2)
        open(target, "w").write("original\n")
        open(target2, "w").write("original\n")
        g("add", "-A"); g("commit", "-q", "-m", "base")
        base_sha = g("rev-parse", "HEAD").stdout.strip()
        open(target, "w").write("amended\n")
        open(target2, "w").write("amended\n")
        g("add", "-A"); g("commit", "-q", "-m", "move the doctrine")
        head_sha = g("rev-parse", "HEAD").stdout.strip()

        os.makedirs(tdir, exist_ok=True)
        tpath = os.path.join(tdir, "synth.jsonl")
        boot = json.dumps({"type": "user", "message": {"role": "user",
                          "content": "You are DEV1. Adopt the role."}})
        later = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
        read = json.dumps({"type": "assistant", "timestamp": later, "message": {"content": [
            {"type": "tool_use", "input": {"file_path": doc}}]}})

        me = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.path.basename(__file__))
        def run_on(*a):
            return subprocess.run([sys.executable, me, "--root", root,
                                   "--since", base_sha, "--head", head_sha, *a],
                                  capture_output=True, text=True).returncode

        def run_out(*a):
            return subprocess.run([sys.executable, me, "--root", root,
                                   "--since", base_sha, "--head", head_sha, *a],
                                  capture_output=True, text=True).stdout

        # POSITIVE: bootstrapped, never read the changed file -> BEHIND -> exit 1
        open(tpath, "w").write(boot + "\n")
        pos = run_on()
        check("synthetic: doctrine moved, role has NOT read it -> 1", pos, 1)
        # NEGATIVE: same tree, same range, BOTH changed files read AFTER the change -> exit 0.
        # ⚠ This used to write ONE read and pass, because the per-set verdict credited a single
        # read to every path. Adding doc2 to the fixture changed what "current" MEANS for this
        # control, and it failed until both reads were written. ⇒ A fixture shared across
        # controls couples them: extending it for a new case silently restated an old one.
        read2_neg = json.dumps({"type": "assistant", "timestamp": later, "message": {"content": [
            {"type": "tool_use", "input": {"file_path": doc2}}]}})
        open(tpath, "w").write(boot + "\n" + read + "\n" + read2_neg + "\n")
        neg = run_on()
        check("synthetic: same tree, role HAS read it since -> 0", neg, 0)

        # ⛔ PER-PATH CONTROL. TWO watched files changed; the role reads exactly ONE.
        # Before the per-path change this was the SILENT failure: `any(has_read(...))` over the
        # set marked the role read-since on BOTH, and told rows print no delta, so the unread
        # file was reported current with no signal of any kind. (DEV1, #183.)
        read2 = json.dumps({"type": "assistant", "timestamp": later, "message": {"content": [
            {"type": "tool_use", "input": {"file_path": doc2}}]}})
        open(tpath, "w").write(boot + "\n" + read2 + "\n")
        out = run_out()
        split_behind = any(l.startswith("  BEHIND") and doc in l and doc2 not in l
                           for l in out.splitlines())
        split_told = any(l.startswith("  read-since") and doc2 in l and doc not in l
                         for l in out.splitlines())
        check("per-path: reading ONE of two changed files leaves the other BEHIND",
              split_behind, True)
        check("per-path: ...and marks only the file actually read as read-since",
              split_told, True)
        return pos == 1 and neg == 0 and split_behind and split_told
    except Exception as exc:
        print(f"  ----  synthetic fixture could not be built ({exc}) — NOT exercised")
        return False
    finally:
        shutil.rmtree(tdir, ignore_errors=True)
        shutil.rmtree(base_dir, ignore_errors=True)


def derived_delta_case(check):
    """⛔ THE CONTROL FOR #183's FIX, and it must be synthetic because live data cannot show it.

    A role that is BEHIND has by definition not read since the change, so its derived base
    sits at or before the change point and the targeted delta EQUALS the cumulative one.
    ⇒ The two diverge only where a role read the file AFTER the given baseline and BEFORE the
    latest change — a real case, and absent from this estate today.

    ★ So a live run cannot distinguish the fix from a no-op. Measured: identical output
    before and after, on every BEHIND row. This constructs the divergence instead.
    """
    import tempfile, shutil
    base_dir = tempfile.mkdtemp(prefix="dw-derive-")
    root = os.path.join(base_dir, REPO_MARK)
    doc = "goals/RESERVED-ACTIONS.md"
    doc2 = "goals/dev-implementation.md"   # also BINDS DEV1 — needed for the per-path control
    try:
        os.makedirs(os.path.join(root, "goals"))
        def g(*a):
            return subprocess.run(["git", *a], cwd=root, capture_output=True, text=True)
        g("init", "-q"); g("config", "user.email", "s@l"); g("config", "user.name", "s")
        t = os.path.join(root, doc)
        open(t, "w").write("one\n"); g("add", "-A"); g("commit", "-q", "-m", "c1")
        wm = g("rev-parse", "HEAD").stdout.strip()
        open(t, "w").write("one\ntwo\n"); g("add", "-A"); g("commit", "-q", "-m", "c2")
        mid = g("rev-parse", "HEAD").stdout.strip()
        open(t, "w").write("one\ntwo\nthree\n"); g("add", "-A"); g("commit", "-q", "-m", "c3")
        head = g("rev-parse", "HEAD").stdout.strip()

        cum = delta_for(wm, head, doc, root)      # watermark base: spans c2 AND c3
        tgt = delta_for(mid, head, doc, root)     # a role that read after c2: only c3
        check("derived delta is NARROWER than cumulative", (cum[0] > tgt[0]), True)
        check("cumulative spans both commits", cum[0], 2)
        check("targeted spans only the unread one", tgt[0], 1)
        # ⚠ [NOT-YET-MEASURED] THIS PROVES THE MECHANISM, NOT THE WIRING.
        # It calls delta_for with two hand-chosen bases and shows a narrower base yields a
        # narrower delta. It does NOT establish that the REPORT path actually reaches
        # derived_base — that needs a fixture where a role is BEHIND *and* has a mid-history
        # read, and this does not build one. ⇒ Sabotaging derived_base would leave these
        # three controls green, which is the neighbouring-question defect this fleet keeps
        # filing. Recorded rather than implied.
        return cum[0] > tgt[0] and cum[0] == 2 and tgt[0] == 1
    except Exception as exc:
        print(f"  ----  derived-delta fixture could not be built ({exc}) — NOT exercised")
        return False
    finally:
        shutil.rmtree(base_dir, ignore_errors=True)


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

    # ⛔ THE KNOWN-POSITIVE IS SYNTHETIC, AND THAT IS THE WHOLE POINT.
    #
    # The previous version built it from real data: take a range 40 commits back, assert
    # exit 1. But this tool exits 1 only when SOME ROLE IS BEHIND — so that control fired
    # only while the FLEET was broken, and went silent the moment every pane caught up.
    # Measured 2026-08-20 at 0 behind / 9 read-since: FAIL, verdict refused, on a tool
    # whose readings were being quoted as authoritative all session.
    #
    # ⇒ The known-positive was drawn from INSIDE the population being measured. That is
    # #26's class, and this function's own docstring states the rule it broke: a control
    # that only fires while something is broken goes silent the moment it is fixed.
    #
    # ★ The pair below is a DISCRIMINATING pair on a throwaway tree: identical in every
    # respect except whether the transcript contains a READ of the changed file after it
    # changed. Repairing the real fleet cannot silence it, and neither can breaking it.
    synth = synthetic_case(check)
    ok = ok and synth
    ok = derived_delta_case(check) and ok
    # VOID paths
    check("unresolvable baseline exits 2", run("--since", "definitely-not-a-ref"), 2)
    check("unresolvable head exits 2", run("--since", head, "--head", "nope/nope"), 2)
    check("root outside this repo exits 2", run("--since", head, "--root", "/tmp"), 2)
    check("unrecognised flag exits 2", run("--not-a-flag"), 2)

    print("\n" + ("all controls reachable" if ok else "⛔ a control did not fire — VERDICT REFUSED"))
    # ==================================================================================
    # ⛔ #183's RULING, CLAUSE 2: VOID WHERE EVIDENCE IS ABSENT — never BEHIND, never current.
    # #58: "established nothing" is not "behind by zero", and the old tool reported the second
    # meaning the first. Controlled in BOTH directions, because a derived_scan that returned
    # VOID for everything would satisfy the first half and report nothing at all.
    # ==================================================================================
    real_root = main_tree()
    seen_real = {}
    for t in transcripts_for(real_root):
        r = role_of(t)
        if r:
            seen_real.setdefault(r, []).append(t)
    rc_h, head_sha, _ = git("rev-parse", "origin/main", cwd=real_root)
    if rc_h == 0 and seen_real:
        head_sha = head_sha.strip()
        # ⛔ a role with NO sessions at all must never appear as BEHIND — it must not appear here
        b0, t0, v0 = derived_scan(head_sha, real_root, {})
        check("no sessions at all -> nothing BEHIND, nothing told", (len(b0), len(t0)), (0, 0))

        # ★ THE KNOWN-POSITIVE FOR VOID: a role whose sessions exist but have read NOTHING.
        # Synthesised by handing derived_scan a session file that contains no tool calls.
        import tempfile as _tf
        with _tf.TemporaryDirectory() as _d:
            empty = os.path.join(_d, "empty.jsonl")
            open(empty, "w").write('{"type":"user","message":{"content":"hello"}}\n')
            fake = {r: [empty] for r in set(x for rs in BINDS.values() for x in rs)}
            b1, t1, v1 = derived_scan(head_sha, real_root, fake)
            vp = sum(len(ps) for _, ps in v1)
            check("a role with a session but NO reads -> VOID, not BEHIND",
                  (len(b1), len(t1), vp > 0), (0, 0, True))

        # ⚠ AND THE DENSITY MEASUREMENT AS A CONTROL. Published on #183 before this was built:
        # 35 of 35 (role, path) pairs derivable, 0 VOID. A future DROP is now visible rather
        # than silent — if this fires, the tool has started refusing where it used to answer.
        b2, t2, v2 = derived_scan(head_sha, real_root, seen_real)
        judged = sum(len(ps) for _, ps in b2) + sum(len(ps) for _, ps in t2)
        voided = sum(len(ps) for _, ps in v2)
        check("read-evidence density: every bound pair is still derivable (0 VOID)", voided, 0)
        print(f"         ---- density: {judged} pair(s) judged, {voided} VOID."
              f" Published as 35/35 on #183 before this was written.")

    return 0 if ok else 3

if __name__ == "__main__":
    sys.exit(main())
