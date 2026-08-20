#!/usr/bin/env python3
"""Which session first PRODUCED this text -- and is the only evidence my own reading?

⛔ WHY. A claim gets attributed to a session, a ruling gets made on it, and the
attribution is never checked. Twice in one day a search for a distinctive string
returned a clean set of hits that were ALL THIS SESSION'S OWN TOOL RECORDS:

  - six hits for a rule's text, read as "the rule reached six panes". They were
    six `tool_use` records in which I had searched for the rule.
  - fifteen hits for a measurement quoted in a PR closure. Every one was a
    `tool_result` from my own `gh pr view`, or my own quotation of it.

⇒ The hits were real, the string was right, and the conclusion inverted, because
grep counts OCCURRENCES and the question was about AUTHORSHIP. So this tool never
reports a count. It reports a CHANNEL per hit:

  AUTHORED  an assistant record -- this session produced or echoed the text
  FETCHED   a tool_result -- this session went and GOT it
  RECEIVED  an inbound user turn -- someone sent it here
  OTHER     queue/attachment plumbing

⛔ AND IT REFUSES A VERDICT when every hit belongs to the asking session. That is
not "no author found", it is "you have measured your own reading" -- exit 3, the
same shape as a control that failed.

⚠⚠ A LOCAL ABSENCE IS NOT AN ABSENCE. A session that authored the text on another
machine and a session that never authored it produce an IDENTICAL empty result
here. This was not hypothetical: a peer was reported FLATLINE for six hours while
it merged two PRs from a transcript this machine does not hold. So zero hits is
exit 2 -- ESTABLISHED NOTHING -- and never "nobody wrote it".
"""
import argparse, glob, json, os, sys

ROOT = "~/.claude/projects/*/*.jsonl"
AUTHORED, FETCHED, RECEIVED, OTHER = "AUTHORED", "FETCHED", "RECEIVED", "OTHER"


def channel(rec):
    """Which way did this text pass through this session?"""
    t = rec.get("type")
    if t == "assistant":
        return AUTHORED
    if t == "user":
        c = (rec.get("message") or {}).get("content")
        if isinstance(c, list) and any(isinstance(b, dict) and b.get("type") == "tool_result"
                                       for b in c):
            return FETCHED
        return RECEIVED
    return OTHER


def scan(needles, root=ROOT):
    """[(timestamp, session, record index, channel)], plus the file count read.

    Substring-matched on the raw line before parsing: a needle spanning a record
    boundary is not found, and that is stated rather than silently handled.
    """
    hits, files, unreadable = [], 0, 0
    for p in glob.glob(os.path.expanduser(root)):
        files += 1
        try:
            with open(p, errors="replace") as f:
                for i, line in enumerate(f):
                    if not any(n in line for n in needles):
                        continue
                    try:
                        rec = json.loads(line)
                    except ValueError:
                        continue
                    hits.append((rec.get("timestamp", "?"),
                                 os.path.basename(p)[:8], i, channel(rec)))
        except OSError:
            unreadable += 1
    hits.sort()
    return hits, files, unreadable


def verdict(hits, self_sid):
    """0 attributed · 1 present but unauthored · 2 established nothing · 3 own-reading only."""
    if not hits:
        return 2, ("⛔ ESTABLISHED NOTHING — no transcript on this machine holds it. "
                   "A session that authored it ELSEWHERE and one that never authored it "
                   "look identical from here.")
    sessions = {s for _, s, _, _ in hits}
    if self_sid and sessions == {self_sid}:
        return 3, (f"⛔ EVERY HIT IS {self_sid} — the asking session. You have measured "
                   "your own reading, not anyone's authorship. VERDICT REFUSED.")
    authors = sorted({s for _, s, _, ch in hits if ch == AUTHORED and s != self_sid})
    if not authors:
        return 1, ("⚠ present, but no session other than the asker AUTHORED it — every "
                   "other hit was fetched or received. The origin is not on this machine.")
    return 0, "authored by: " + ", ".join(authors)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("needle", nargs="+", help="literal string(s); a hit on ANY counts")
    ap.add_argument("--self", dest="self_sid", default=None,
                    help="your own 8-char session id. ⚠ Do NOT guess it — a session "
                         "identifying itself from memory is the defect fleet-identity.py "
                         "exists for. Omitting it disables the own-reading control.")
    ap.add_argument("--root", default=ROOT)
    ap.add_argument("--limit", type=int, default=30)
    a = ap.parse_args()

    hits, files, unreadable = scan(a.needle, a.root)
    print(f"searched {files} transcript(s)"
          + (f", {unreadable} unreadable" if unreadable else "")
          + f" for {len(a.needle)} needle(s)\n")
    if not a.self_sid:
        print("⚠ no --self given: the own-reading control is NOT RUNNING. A result of "
              "'authored here' may be your own records.\n")
    for ts, sid, i, ch in hits[:a.limit]:
        mine = "  ← you" if sid == a.self_sid else ""
        print(f"  {ts}  {sid}  rec={i:<7d} {ch}{mine}")
    if len(hits) > a.limit:
        print(f"  … {len(hits) - a.limit} more not shown (--limit)")

    code, why = verdict(hits, a.self_sid)
    print(f"\n{why}")
    if hits:
        first = hits[0]
        print(f"earliest anywhere: {first[0]}  {first[1]}  {first[3]}")
    return code


if __name__ == "__main__":
    sys.exit(main())
