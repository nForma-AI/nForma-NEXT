#!/usr/bin/env python3
"""Did a role prompt REACH a pane -- and by which channel?

⛔ THE DEFECT THIS EXISTS FOR: "9 of 9" was true of the FILES and false of the
SESSIONS, and both populations have nine members.

  9 goal files carry a pointer at `prompts/<ROLE>.md`   <- INSTALLED
  9 sessions were active when that was measured          <- the other nine
  1 of those sessions saw the pointer near its launch    <- DELIVERED

A remedy that writes a pointer into N files, measured against N sessions, offers
"N of N" as the most plausible-looking wrong answer available. The installed
count is a property of the FILESYSTEM. The delivered count is a property of a
TRANSCRIPT. Nothing in either number says which one it is.

⇒ So this tool never prints one number. It prints INSTALLED and DELIVERED
separately, and it splits DELIVERED by channel, because they are not equivalent
evidence:

  LAUNCH    the pointer is in the bootstrap window -- the pane started with it
  RECEIVED  it arrived later, in an inbound turn -- a peer had to say it
  PULLED    the session fetched or wrote it ITSELF -- tool_result or assistant

⚠ PULLED IS NOT DELIVERY. A session that greps for the pointer and finds it has
demonstrated only that it can read. Counting those hits reports the auditor's own
reading as the subject's receipt -- measured on this fleet, the session with the
most hits (11) was the one that WROTE the pointer into the goal files.

★ And a transcript whose head holds no launch prompt -- a wake, a resumption --
ESTABLISHES NOTHING about how that pane was launched. The launch is in another
file, or in no file. That is reported as its own verdict, never as "no".
"""
# NO-SELF-TEST: controlled by tools/test_prompt_delivery.py, which the CI glob gates and which
# passes on main. ⛔ This is a DECLARATION of where the control lives, not a
# claim that none exists — tools/README.md records two control conventions in
# one directory (`--self-test` and `test_*.py`, the fork #164 §4 named), and
# this tool uses the second. ⚠ Verified anchored: the suite carries no
# `^# SUITE-DEPENDS:` line, so it is in the gating population rather than
# self-exempt. A loose `grep -c SUITE-DEPENDS` reads 1 on some of these and
# matches a SENTENCE ABOUT the marker — use-versus-mention, measured here.
import argparse, glob, json, os, re, sys, time

GOALS = os.path.expanduser("~/.claude/goals")
TRANSCRIPTS = os.path.expanduser("~/.claude/projects/*")

POINTER = re.compile(r"(?:nForma-NEXT[:/]|origin/main:)prompts/[A-Za-z0-9_.-]+\.md")
SYSTEM_REMINDER = re.compile(r"<system-reminder>.*?</system-reminder>", re.S)
# A machine wake is not a launch prompt. It carries no role and grants nothing.
WAKE = re.compile(r"auto-wake|machine wake|Resume your goal's autonomous loop", re.I)

LAUNCH, RECEIVED, PULLED = "LAUNCH", "RECEIVED", "PULLED"


def installed(goals_dir=GOALS):
    """Files carrying a prompt pointer. None = the directory could not be read.

    This is a fact about the FILESYSTEM. It is never evidence that any session
    read any of them.
    """
    try:
        paths = sorted(glob.glob(os.path.join(goals_dir, "*.md")))
    except OSError:
        return None
    if not paths:
        return None                       # ⛔ no goal files is not "0 installed"
    out = []
    for p in paths:
        try:
            with open(p, errors="replace") as f:
                if POINTER.search(f.read()):
                    out.append(os.path.basename(p))
        except OSError:
            continue                      # unreadable file, not an absent pointer
    return out, len(paths)


def text_of(rec):
    m = rec.get("message") or {}
    c = m.get("content")
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        return "".join(b.get("text", "") for b in c
                       if isinstance(b, dict) and b.get("type") == "text")
    return ""


def is_tool_result(rec):
    c = ((rec.get("message") or {}).get("content"))
    return isinstance(c, list) and any(
        isinstance(b, dict) and b.get("type") == "tool_result" for b in c)


def bootstrap(path, window):
    """(record index, text) of the launch prompt, or (None, None).

    ⚠ Skips `<system-reminder>` records: the reminder sits BEFORE the bootstrap
    in every transcript here, and taking the first user record verbatim reads
    a 119-byte reminder as the launch prompt -- which reported "no pointer" for
    the four panes whose bootstrap it had not yet reached.
    """
    try:
        with open(path, errors="replace") as f:
            for i, line in enumerate(f):
                if i > window:
                    return None, None
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                if rec.get("type") != "user" or is_tool_result(rec):
                    continue
                t = SYSTEM_REMINDER.sub("", text_of(rec)).strip()
                if t:
                    return i, t
    except OSError:
        return None, None
    return None, None


def delivery(path, window=40):
    """Channels by which a prompt pointer reached this session.

    Returns None when the transcript holds no launch prompt -- ESTABLISHED
    NOTHING, not "not delivered". Returns a dict of channel -> first record
    index otherwise; an empty dict means the file was read and carried none.
    """
    idx, boot = bootstrap(path, window)
    if boot is None:
        return None
    if WAKE.search(boot[:400]):
        return None            # a wake at the head: the launch is in another file
    chans = {}
    if POINTER.search(boot):
        chans[LAUNCH] = idx
    try:
        with open(path, errors="replace") as f:
            for i, line in enumerate(f):
                if i <= idx or POINTER.search(line) is None:
                    continue
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                if rec.get("type") == "user" and not is_tool_result(rec):
                    ch = RECEIVED
                else:
                    ch = PULLED     # tool_result or assistant: the session's own
                chans.setdefault(ch, i)
    except OSError:
        return None
    return chans


def active(within_s, root_glob=TRANSCRIPTS):
    now = time.time()
    out = []
    for root in glob.glob(root_glob):
        for p in glob.glob(os.path.join(root, "*.jsonl")):
            try:
                idle = now - os.path.getmtime(p)
            except OSError:
                continue
            if idle <= within_s:
                out.append((idle, os.path.basename(root), p))
    out.sort()
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--active-hours", type=float, default=12.0)
    ap.add_argument("--window", type=int, default=40,
                    help="records searched for the launch prompt")
    ap.add_argument("--goals", default=GOALS)
    a = ap.parse_args()

    inst = installed(a.goals)
    print("── INSTALLED ── a property of the filesystem, not of any session")
    if inst is None:
        print(f"  ⛔ ESTABLISHED NOTHING — {a.goals} unreadable or empty.")
    else:
        files, total = inst
        print(f"  {len(files)} of {total} goal file(s) carry a prompt pointer")

    rows = active(a.active_hours * 3600)
    print(f"\n── DELIVERED ── {len(rows)} transcript(s) touched in "
          f"{a.active_hours:g}h")
    tally = {LAUNCH: 0, RECEIVED: 0, PULLED: 0}
    nothing = none_seen = 0
    for idle, proj, p in rows:
        sid = os.path.basename(p)[:8]
        chans = delivery(p, a.window)
        if chans is None:
            nothing += 1
            print(f"  {sid}  {idle/60:6.0f}m  ⛔ NO LAUNCH PROMPT IN THIS FILE — "
                  f"ESTABLISHED NOTHING about how this pane was launched")
            continue
        if not chans:
            none_seen += 1
            print(f"  {sid}  {idle/60:6.0f}m  read, no pointer anywhere")
            continue
        for c in chans:
            tally[c] += 1
        order = [c for c in (LAUNCH, RECEIVED, PULLED) if c in chans]
        print(f"  {sid}  {idle/60:6.0f}m  " +
              "  ".join(f"{c}@{chans[c]}" for c in order))

    print(f"\n  LAUNCH   {tally[LAUNCH]:3d}  started with the pointer")
    print(f"  RECEIVED {tally[RECEIVED]:3d}  a peer had to say it")
    print(f"  PULLED   {tally[PULLED]:3d}  ⚠ the session's own reading — NOT delivery")
    print(f"  none     {none_seen:3d}  read, carried no pointer")
    print(f"  unknown  {nothing:3d}  no launch prompt in the file")
    if inst is not None and tally[LAUNCH] != len(inst[0]):
        print(f"\n⇒ INSTALLED {len(inst[0])} ≠ LAUNCH {tally[LAUNCH]}. "
              "These are different populations; neither is 'N of N panes'.")
    # ⛔ "0 sessions were delivered to" and "0 sessions could be read" are the
    # same printed table. They are not the same result, so they are not the
    # same exit code.
    if not rows or nothing == len(rows):
        print("\n⛔ ESTABLISHED NOTHING — no transcript in the window held a "
              "launch prompt. This is not 'nothing was delivered'.")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
