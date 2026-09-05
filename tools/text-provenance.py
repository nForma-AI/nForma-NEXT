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

⚠ ON MUTATION-TESTING THIS FILE: assert the replacement string's LENGTH, never
eyeball it. A one-byte mutation that does not apply reads as a clean SURVIVED on
the very check written to prevent clean SURVIVEDs -- measured four times here in
one day, once on `or` -> `and`.

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
# NO-SELF-TEST: controlled by tools/test_text_provenance.py, which the CI glob gates and which
# passes on main. ⛔ This is a DECLARATION of where the control lives, not a
# claim that none exists — tools/README.md records two control conventions in
# one directory (`--self-test` and `test_*.py`, the fork #164 §4 named), and
# this tool uses the second. ⚠ Verified anchored: the suite carries no
# `^# SUITE-DEPENDS:` line, so it is in the gating population rather than
# self-exempt. A loose `grep -c SUITE-DEPENDS` reads 1 on some of these and
# matches a SENTENCE ABOUT the marker — use-versus-mention, measured here.
import argparse, glob, json, os, re, sys

ROOT = "~/.claude/projects/*/*.jsonl"
AUTHORED, FETCHED, RECEIVED, OTHER = "AUTHORED", "FETCHED", "RECEIVED", "OTHER"
INSTRUMENT, UNCLASSIFIED = "INSTRUMENT", "UNCLASSIFIED"

# ⚠ An ALLOWLIST, not a denylist of search verbs. Keying on `grep`/`rg` misses a
# python heredoc doing `if needle in line` -- which is exactly how both of this
# tool's own false positives were produced.
#
# ⛔ AND AN ALLOWLIST DRIFTS, WHICH A PEER MEASURED ON THE FIRST VERSION OF IT.
# That version listed `commit -m` and not `commit -F -`. Counted in one peer's
# transcript: `commit -F` 61, `commit -m` 13; `gh issue create` 24, `gh pr create`
# 19, `gh issue comment` 55 -- every one of them publishing, none of them listed.
# It would have reported a session that published four PR/issue bodies in three
# hours as having authored nothing. That is the fail-safe direction, so it is not
# dangerous -- it is SILENTLY DEGRADING: quieter over time, equally confident.
#
# ⇒ So an unrecognised path is UNCLASSIFIED, never a silent INSTRUMENT. A new
# publishing route -- a new `gh` subcommand, an MCP send -- forces a decision the
# FIRST time it appears instead of quietly shrinking the numerator. `--audit`
# enumerates the tools actually present and names the ones nothing classifies.
#
# ⚠ `gh` is not one tool. `create`/`comment`/`edit`/`close` publish; `view`/`list`/
# `api` read. Keying on `gh` alone is wrong in one direction or the other.
# ⇒ Populated by running `--audit` on this machine, which named 17 unclassified
# tools on its first run -- the staleness test failing on its own author, which is
# the only evidence that it works. ⚠ This list is a SNAPSHOT of one machine's 12h
# window, not a closed set; `--audit` is what keeps it honest as new paths appear.
PUBLISHING_TOOLS = {
    # text this session composed and sent onward, to a person, a peer, or a queue
    "SendMessage", "Write", "Edit", "NotebookEdit", "Artifact",
    "SendUserFile", "PushNotification", "AskUserQuestion",
    "TaskCreate", "TaskUpdate",
    "Agent",                      # the prompt is authored text handed to a peer
    "CronCreate", "ScheduleWakeup",   # authored text, delivered later
    "mcp__claude-1__claude", "mcp__codex-1__codex",
    "mcp__antigravity-1__antigravity", "mcp__claude-kimi__claude",
    "mcp__claude-minimax__claude", "mcp__claude-z-ai__claude",
    "mcp__copilot-1__copilot",
}
READING_TOOLS = {
    "Read", "Grep", "Glob", "WebFetch", "WebSearch", "ListAgents",
    "ToolSearch", "TaskOutput", "Monitor", "CronList",
    "Skill", "TaskStop", "CronDelete",       # carry ids and args, not prose
    "mcp__claude-1__health_check", "mcp__codex-1__health_check",
    "mcp__claude-1__ping", "mcp__codex-1__ping",
    "mcp__plugin_vercel_vercel__authenticate",
}

# ⛔ ANCHORED AT A COMMAND POSITION, not matched as a bare substring. The literal
# form classified `echo "listed: commit -m and gh pr comment"` as AUTHORED --
# a QUOTATION of the allowlist read as an invocation of it. That is use-vs-mention,
# which this repo already has a tool for, and it was found by this suite's own
# negative control rather than in the field.
_CMD_START = r"(?:^|[;|&]\s*|\$\(\s*|\n\s*|`)"
GH_PUBLISH = re.compile(
    _CMD_START + r"gh\s+(?:issue|pr)\s+(?:create|comment|edit|close|review)\b|"
    + _CMD_START + r"gh\s+(?:release|gist)\s+create\b")
GH_READ = re.compile(
    _CMD_START + r"gh\s+(?:pr|issue|run)\s+(?:view|list|checks|diff|status)\b|"
    + _CMD_START + r"gh\s+api\b")
# ⚠ A heredoc landing in a file IS authoring -- but a bare `>` appears in prose
# constantly, so only the redirect-into-a-path forms count.
HEREDOC_WRITE = re.compile(r">>?\s*[\w./~-]+\s*<<|\|\s*tee\s+[\w./~-]+")

PUBLISHING_BASH = ("git notes", "git tag -m", "git tag -a")
READING_BASH = (
    "grep", "rg ", "ugrep", "python3 -", "cat ", "sed -n", "awk ", "git log",
    "git show", "git rev-list", "git diff", "git status",
    # ⇒ A DECISION, recorded rather than assumed: `echo` writes to a terminal, and
    # terminal output is not publication. It surfaced as UNCLASSIFIED first, which
    # is the tool working — an unrecognised path asked, and this is the answer.
    "echo ",
)


# ⛔ NOT a literal list of commit forms. The first attempt enumerated `commit -m`,
# `commit -F`, `commit -q -F` -- which is an enumeration of FLAG ORDERS, and those
# are unbounded: `commit -a -F`, `commit --amend -m` and `commit -am` all fell
# through it. That is the SAME drift the tool-level allowlist just failed at, one
# level down, and it was found by a peer correcting its own count of these very
# forms. ⚠ `git` is required before `commit` so that `grep commit -m file` -- where
# `-m` is grep's max-count -- cannot read as authorship.
COMMIT_PUBLISH = re.compile(
    r"\bgit\b[^\n;|&]*?\bcommit\b[^\n;|&]*?(?:\s-[a-zA-Z]*[mF]\b|\s--(?:message|file)\b)")


def classify_use(block):
    """AUTHORED · INSTRUMENT · UNCLASSIFIED for a tool_use carrying the needle.

    ⛔ Returns UNCLASSIFIED rather than guessing. An allowlist that silently
    absorbs what it does not recognise stops being an allowlist.
    """
    name = block.get("name") or ""
    if name in PUBLISHING_TOOLS:
        return AUTHORED
    if name in READING_TOOLS:
        return INSTRUMENT
    if name != "Bash":
        return UNCLASSIFIED
    cmd = (block.get("input") or {}).get("command", "")
    # ⚠ PUBLISH is tested first: one command can both read and write, and the
    # write is the part that makes it authorship.
    if (COMMIT_PUBLISH.search(cmd) or GH_PUBLISH.search(cmd)
            or HEREDOC_WRITE.search(cmd) or any(m in cmd for m in PUBLISHING_BASH)):
        return AUTHORED
    if GH_READ.search(cmd) or any(m in cmd for m in READING_BASH):
        return INSTRUMENT
    return UNCLASSIFIED


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
                        return classify_use(b)
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
    undecided = sorted({s for _, s, _, ch in hits
                        if ch == UNCLASSIFIED and s != self_sid and s not in late})
    if not authors and undecided:
        return 4, ("⛔ UNCLASSIFIED — " + ", ".join(undecided) + " carry the text through a "
                   "path nothing in the table classifies. That is a DECISION, not an answer: "
                   "run --audit and classify it. Absorbing it silently as INSTRUMENT is how an "
                   "allowlist goes quiet while staying confident.")
    if not authors:
        why = ("⚠ present, but no session other than the asker AUTHORED it — every other "
               "hit was fetched, received, or an INSTRUMENT (a command with the string as "
               "an argument). The origin is not on this machine.")
        if late:
            why += (f"\n⛔ {len(late)} session(s) POST-DATE your own first sight of it "
                    f"({', '.join(sorted(late))}) — they cannot be its origin, and after a "
                    "round of asking peers they are your own probe's residue.")
        return 1, why
    why = "authored by: " + ", ".join(authors)
    if undecided:
        why += (f"\n⚠ and {len(undecided)} session(s) carry it through an UNCLASSIFIED path "
                f"({', '.join(undecided)}) — the author list may be short.")
    return 0, why


def audit(root, within_s):
    """Tool names actually present, and which the table does not classify.

    ⛔ A staleness test for the allowlist itself. The first version of this table
    listed `commit -m` and not `commit -F -`; a peer used the second form 61 times
    and the first 13. Nothing failed -- the numerator just quietly shrank. This
    fails loudly on its own author instead.
    """
    import time
    now = time.time()
    seen, files, contributors = {}, 0, set()
    for p in glob.glob(os.path.expanduser(root)):
        try:
            if now - os.path.getmtime(p) > within_s:
                continue
            files += 1
            with open(p, errors="replace") as f:
                for line in f:
                    if '"tool_use"' not in line:
                        continue
                    try:
                        rec = json.loads(line)
                    except ValueError:
                        continue
                    c = (rec.get("message") or {}).get("content")
                    if not isinstance(c, list):
                        continue
                    for b in c:
                        if isinstance(b, dict) and b.get("type") == "tool_use":
                            seen[b.get("name") or "?"] = seen.get(b.get("name") or "?", 0) + 1
                            contributors.add(os.path.basename(p)[:8])
        except OSError:
            continue
    known = PUBLISHING_TOOLS | READING_TOOLS | {"Bash"}
    unknown = sorted((n for n in seen if n not in known), key=lambda n: -seen[n])
    return files, seen, unknown, len(contributors)


def audit_verdict(files, seen, unknown, contributors=None):
    """0 all classified · 2 established nothing · 4 something needs deciding.

    ⛔ "Every tool present is classified" is VACUOUSLY TRUE over an empty set. The
    first version of this printed ✅ and exited 0 against a root that matched no
    files -- a clean zero reading as a clean result, in the tool whose whole
    purpose is refusing that. A broken enumerator and a fully-classified fleet
    produced the identical line.
    """
    if not files or not seen:
        return 2, ("⛔ ESTABLISHED NOTHING — the enumeration found "
                   f"{files} transcript(s) and {len(seen)} tool(s). An empty corpus "
                   "satisfies 'every tool is classified' vacuously; it is not a pass.")
    if unknown:
        return 4, (f"⛔ {len(unknown)} tool(s) nothing classifies: " + ", ".join(unknown)
                   + "\n   Each is a DECISION. Until made, a needle carried through one "
                     "is UNCLASSIFIED — not silently INSTRUMENT.")
    # ⛔ NON-EMPTY IS NOT REPRESENTATIVE. A corpus of one transcript enumerates ONE
    # SESSION'S HABITS, and a ✅ over it certifies the table as though it had
    # enumerated the fleet. The provenance side already refuses a population of one
    # (exit 3); this is the same shape, and a floor on COUNT does not establish
    # DIVERSITY.
    if contributors is not None and contributors < 2:
        return 2, (f"⛔ ESTABLISHED NOTHING ABOUT THE FLEET — all {len(seen)} tool(s) "
                   f"came from {contributors} transcript(s). Every one is classified, "
                   "and that is a fact about one session's habits. A tool this fleet "
                   "uses and this session does not cannot appear here.")
    return 0, (f"✅ every one of the {len(seen)} tool(s) present is classified"
               + (f", across {contributors} transcript(s)" if contributors else ""))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("needle", nargs="*", help="literal string(s); a hit on ANY counts")
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
    ap.add_argument("--audit", action="store_true",
                    help="enumerate the tools present and name the ones nothing classifies")
    ap.add_argument("--audit-hours", type=float, default=12.0)
    a = ap.parse_args()

    if a.audit:
        files, seen, unknown, contributors = audit(a.root, a.audit_hours * 3600)
        print(f"── AUDIT ── {files} transcript(s) touched in {a.audit_hours:g}h, "
              f"{contributors} of them using tools, {len(seen)} distinct tool(s)")
        for n in sorted(seen, key=lambda n: -seen[n]):
            mark = ("PUBLISHES" if n in PUBLISHING_TOOLS else
                    "reads    " if n in READING_TOOLS else
                    "by verb  " if n == "Bash" else "⛔ UNCLASSIFIED")
            print(f"  {seen[n]:7d}  {mark}  {n}")
        code, why = audit_verdict(files, seen, unknown, contributors)
        print("\n" + why)
        return code

    if not a.needle:
        ap.error("give at least one needle (or --audit to enumerate the tool table)")
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
