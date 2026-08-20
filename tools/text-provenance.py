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

⛔⛔ THE PROBE CONTAMINATES THE POPULATION, AND A PEER PROVED IT ON THIS TOOL.
Asking a peer about a phrase writes that phrase into the peer's transcript. DEV4
had ZERO hits for four of five needles before I messaged it and TWO each after --
all at one timestamp, all my message plus its own search for it. So the same
question returns different answers depending on how much you have investigated
it, and the spread looks like distribution while being your own footprints.

⇒ Two consequences, both implemented rather than noted:

  INSTRUMENT is a FOURTH CLASS. A needle inside a tool_use input is the session
  RUNNING A COMMAND that contains the string, not asserting it. Measured on my
  own transcript: two of my three AUTHORED hits were a search script with the
  needle as a literal argument. That is a CONFIDENT FALSE POSITIVE -- worse than
  a refusal -- and it would have named the peer who searched on my behalf as the
  author of a phrase it first saw when I sent it. ⚠ The classifier is
  deliberately biased toward INSTRUMENT: publishing tools are an allowlist, and
  everything else with the needle in its input refuses to count as authorship.

  POST-DATES is not a heuristic. If a session's EARLIEST occurrence is later than
  the asker's earliest, that session cannot be the origin of the asker's copy.
  Such sessions are excluded from the authorship candidates and labelled, because
  after a round of asking they are the majority of the hits.
"""
import argparse, glob, json, os, sys

ROOT = "~/.claude/projects/*/*.jsonl"
AUTHORED, FETCHED, RECEIVED, OTHER = "AUTHORED", "FETCHED", "RECEIVED", "OTHER"
INSTRUMENT = "INSTRUMENT"

# ⚠ An ALLOWLIST, not a denylist of search verbs. Keying on `grep`/`rg` misses a
# python heredoc doing `if needle in line` -- which is exactly how both of this
# tool's own false positives were produced. So: a needle in a tool_use input is
# INSTRUMENT unless the tool PUBLISHES, and the cost of being wrong is a missed
# attribution (exit 1, honest) rather than a false one (exit 0, confident).
PUBLISHING_TOOLS = {"SendMessage", "Write", "Edit", "NotebookEdit"}
PUBLISHING_BASH = ("gh pr comment", "gh pr create", "gh issue create",
                   "gh issue comment", "gh pr edit", "--body", "commit -m")


def _publishes(block):
    name = block.get("name") or ""
    if name in PUBLISHING_TOOLS:
        return True
    if name == "Bash":
        cmd = (block.get("input") or {}).get("command", "")
        return any(m in cmd for m in PUBLISHING_BASH)
    return False


def channel(rec, needles=()):
    """Which way did this text pass through this session?

    ⛔ needles matter: the same assistant record is AUTHORED when the string is in
    its prose and INSTRUMENT when it is an argument to a command it ran.
    """
    t = rec.get("type")
    c = (rec.get("message") or {}).get("content")
    if t == "assistant":
        if isinstance(c, list):
            for b in c:
                if not isinstance(b, dict):
                    continue
                if b.get("type") == "text" and any(n in b.get("text", "") for n in needles):
                    return AUTHORED           # prose: the session asserted it
                if b.get("type") == "tool_use":
                    inp = json.dumps(b.get("input", {}))
                    if any(n in inp for n in needles):
                        return AUTHORED if _publishes(b) else INSTRUMENT
        return AUTHORED
    if t == "user":
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
                                 os.path.basename(p)[:8], i, channel(rec, needles)))
        except OSError:
            unreadable += 1
    hits.sort()
    return hits, files, unreadable


def postdates(hits, self_sid):
    """Sessions whose EARLIEST hit is later than the asker's earliest.

    ⛔ Not a heuristic: if you already held the text at T0, a session that first
    saw it at T1 > T0 cannot be the origin of your copy. After one round of asking
    peers about a phrase, these are most of the hits — they are your own probe.
    """
    if not self_sid:
        return None                       # no reference point: the check DID NOT RUN
    first = {}
    for ts, sid, _, _ in hits:
        first.setdefault(sid, ts)
    mine = first.get(self_sid)
    if mine is None:
        return set()                      # asker holds none: nothing to compare against
    return {sid for sid, ts in first.items() if sid != self_sid and ts > mine}


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
    late = postdates(hits, self_sid) or set()
    authors = sorted({s for _, s, _, ch in hits
                      if ch == AUTHORED and s != self_sid and s not in late})
    if not authors:
        why = ("⚠ present, but no session other than the asker AUTHORED it — every other "
               "hit was fetched, received, or an INSTRUMENT (a command with the string as "
               "an argument). The origin is not on this machine.")
        if late:
            why += (f"\n⛔ {len(late)} session(s) POST-DATE your own first sight of it "
                    f"({', '.join(sorted(late))}) — they cannot be its origin, and after a "
                    "round of asking peers they are your own probe's residue.")
        return 1, why
    return 0, "authored by: " + ", ".join(authors)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("needle", nargs="+", help="literal string(s); a hit on ANY counts")
    ap.add_argument("--self", dest="self_sid", default=None,
                    help="your own 8-char session id. ⚠ Do NOT guess it — a session "
                         "identifying itself from memory is the defect fleet-identity.py "
                         "exists for.")
    ap.add_argument("--no-self", action="store_true",
                    help="⛔ run WITHOUT the own-reading control. A control you can omit "
                         "silently is a control that will be omitted, so this is explicit "
                         "and the run is labelled NOT RUN rather than clean.")
    ap.add_argument("--root", default=ROOT)
    ap.add_argument("--limit", type=int, default=30)
    a = ap.parse_args()

    if not a.self_sid and not a.no_self:
        ap.error("--self is required (or --no-self to run without the own-reading "
                 "control). Every hit being your own is this tool's most common result.")

    hits, files, unreadable = scan(a.needle, a.root)
    print(f"searched {files} transcript(s)"
          + (f", {unreadable} unreadable" if unreadable else "")
          + f" for {len(a.needle)} needle(s)\n")
    if not a.self_sid:
        print("⛔ --no-self: the own-reading control and the POST-DATES check are NOT RUN. "
              "This is not a clean result; it is an unchecked one.\n")
    for ts, sid, i, ch in hits[:a.limit]:
        late = postdates(hits, a.self_sid) or set()
        tag = "  ← you" if sid == a.self_sid else ("  ⛔ POST-DATES you" if sid in late else "")
        print(f"  {ts}  {sid}  rec={i:<7d} {ch}{tag}")
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
