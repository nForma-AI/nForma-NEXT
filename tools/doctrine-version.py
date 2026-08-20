#!/usr/bin/env python3
"""Which version of its role prompt is each agent actually running?

⛔ Why this exists. `prompts/README.md` makes the identity argument correctly — `NFORMA_ROLE`
is load-bearing because `echo $NFORMA_ROLE` is *"an off-pane effect, not a claim the agent
makes about itself"* — and then never makes the same argument for the prompt's **content**.
`ROLE-READY` proves the prompt file was reachable. It does not say WHICH VERSION was read,
and the version is the part that decides behaviour.

Measured, and this is the incident: ARCHITECT ran a whole session on a 459-line
`prompts/ARCHITECT.md` while HEAD carried 592. The missing 133 lines contained the friction
obligation it was failing to discharge and the STATE-line contract it was failing to emit.
DEV5 held 383 against 652. Nine panes ran stale doctrine for hours and **no party could
answer "which prompt is DEV3 running?"** — not DEV3, not the orchestrator, not the operator.
`prompts/TEAMLEAD.md` already records the other half of the same fact: every prompt amendment
made in one day reached **zero** running agents.

★ It takes no cooperation from the agent. The bootstrap already runs `cat $NFORMA_ROLE_PROMPT`,
and that output lands in the session transcript. This reads it back and matches it against
every historical blob of that file. So the reading is an **off-pane effect**, not a claim a
possibly-stale agent makes about its own staleness — which is the whole point, because an
agent running old doctrine is exactly the party least able to report that it is.

⚠ Its known-positive is by construction: this tool is run from inside the repo whose prompts
it resolves, and any session that read a prompt must appear. If the sweep yields zero
readings, that is the instrument failing, not a fleet running current doctrine.

⛔ AND IT HAS YIELDED ZERO SINCE IT SHIPPED. Two separate causes, measured 2026-08-20.

  1. FIXED — the population was selected by the audited repo's NAME. Both selectors assume
     the repo whose prompts are audited is the repo the agents WORK in. It never is: the
     fleet works in one checkout and `cat`s its prompts out of another.

         project dirs whose name contains "nForma-NEXT"            0
         prompt-read records under -…-code-DigitalFrontier-infra  60

     ⇒ The matcher excluded the only directory that could answer, by construction. The guard
     fired correctly every time — VOID, exit 2, "that is the instrument failing" — so it
     never lied; it simply could not see. Now: when no directory matches the name, ALL are
     swept. The blob match is the discriminator, so a foreign directory cannot produce a
     false reading — only a slower sweep. Scoping by name was correct derivation over the
     wrong set.

  2. ⛔ STILL OPEN, and handed over with its evidence rather than guessed at. Over the
     CORRECTED population the sweep still recovers **zero prompt reads**, while a
     distinctive line from `prompts/DX.md` demonstrably appears in one transcript. So the
     content is present and the recovery step does not find it. Two candidate causes,
     neither confirmed: the recovery may inspect record types that do not carry it, or no
     WHOLE-FILE blob may exist in any transcript (only fragments), in which case exact
     containment can never match and the resolution predicate itself needs rethinking.
     [NOT-YET-MEASURED]

     ⚠ Do not read the fix in (1) as making this tool operational. It is not. It is now
     looking in the right place and still finding nothing, which is a better failure than
     looking in the wrong place — but it is still a failure, and the fleet-wide doctrine
     staleness this tool exists to detect remains unmeasured.

⛔ Two versions of one prompt can only be told apart if neither is a substring of the other.
That is checked FIRST, per `discriminates.py`: a session matching two mutually-contained
versions is reported AMBIGUOUS and never resolved to the convenient one.

⛔ Resolution is by EXACT CONTAINMENT of a historical blob in recovered output, and a
partial read therefore resolves to nothing rather than to a guess. A signature-line fallback
was built to close that gap and **discarded**: signatures computed within one file's history
are not comparable across files, so an amendment touching all five prompts made the same lines
look unique to each, and every session in the fleet — DEV panes included — resolved to
ARCHITECT.md@592 with an identical score. It was caught because the answer was too clean.
⇒ A matcher whose failure mode is a plausible uniform number is worse than one whose failure
mode is silence. UNKNOWN rows below are that silence, and they are honest.

★ Why this matcher is immune to the mention-vs-use class that bit two other tools here the
same afternoon: it compares blob CONTENT, not command text. A historical blob either is or is
not that byte sequence, so a transcript merely *discussing* a prompt version cannot resolve to
it. ⛔ Do not "harden" this into a keyword or path match — that would trade the one property
that makes it safe for an appearance of rigour. (Raised by DEV2, #33.)

Exit: 0 every reading current · 1 at least one agent is stale · 2 established nothing.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

PROJECTS = Path.home() / ".claude" / "projects"


def git(*args, cwd=None):
    r = subprocess.run(("git",) + args, capture_output=True, text=True, cwd=cwd)
    return r.stdout if r.returncode == 0 else None


def versions_of(path, repo):
    """Every distinct historical blob of `path`, newest commit first."""
    log = git("log", "--all", "--format=%H", "--", path, cwd=repo)
    if log is None:
        return None
    blobs = {}
    for commit in log.split():
        blob = git("rev-parse", f"{commit}:{path}", cwd=repo)
        if not blob:
            continue
        blobs.setdefault(blob.strip(), []).append(commit[:7])
    out = {}
    for blob, commits in blobs.items():
        body = git("cat-file", "-p", blob, cwd=repo)
        if body:
            out[blob] = {"body": body, "commits": commits, "lines": body.count("\n")}
    return out


def collisions(vers):
    """⚠ Pairs this instrument cannot tell apart. Checked before any verdict is formed."""
    bad = []
    for a, va in vers.items():
        for b, vb in vers.items():
            if a != b and va["body"] and va["body"] in vb["body"]:
                bad.append((a, b))
    return bad


def reads_in(transcript, catalogue):
    """Every recoverable read of a prompt in one transcript, in order.

    Two kinds, and conflating them is what this function now exists to stop.

    RESOLVED  a full read whose output contains a historical blob verbatim -> exact version.
    RANGED    a command that reads PART of a prompt -- `sed -n 'A,Bp'`, `head`, `tail`, a
              Read tool `file_path` -- recovered from the CALL, not from its output. The
              version is not knowable from it; that the agent looked is.

    ⛔ MEASURED, and it is why RANGED exists. Reporting only RESOLVED reads answered
    "how many times did this session run a full-file `cat` whose output matched a blob"
    while being read as "is this agent running current doctrine". Those are different
    propositions and the second is the one every consumer wanted. At least 7 of 9 panes
    had re-read -- `sed -n '383,652p' prompts/DEV.md`, `git show origin/main:prompts/DEV.md`
    -- and every one scored reads=1, identical to a pane that never looked again.

    ★ The delta read is the BEHAVIOUR WE WANT: an agent re-reading exactly what changed.
    It was the case this tool was blindest to. Found by TEAMLEAD, who checked whether the
    number it was about to quote was true before quoting it a second time.

    ⛔ A RANGED read NEVER promotes a session to current. It proves the agent saw a span,
    not that it holds the whole current file. Adding a state you can defend beats promoting
    to one you cannot.
    """
    ranged_re = re.compile(
        r"(?:sed\s+-n\s*['\"]?\s*(\d+)\s*,\s*(\d+)p|head\s+-\d+|tail\s+-\S+)"
        r"[^\n]*?(prompts/[A-Za-z0-9_.-]+\.md)")
    full_re = re.compile(r"(?:cat|git\s+show\s+\S*:)\s*(prompts/[A-Za-z0-9_.-]+\.md)")
    seen = []
    try:
        fh = open(transcript, errors="replace")
    except OSError:
        return None
    with fh:
        for line in fh:
            if "prompts/" not in line and '"stdout"' not in line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue

            for cmd in _strings(rec, ("command", "file_path")):
                for m in ranged_re.finditer(cmd):
                    seen.append({"kind": "RANGED", "path": m.group(3),
                                 "span": (m.group(1), m.group(2))})
                for m in full_re.finditer(cmd):
                    seen.append({"kind": "CALL-FULL", "path": m.group(1), "span": None})
                if cmd.endswith(".md") and "/prompts/" in cmd:
                    seen.append({"kind": "RANGED",
                                 "path": "prompts/" + cmd.split("prompts/")[-1], "span": None})

            res = rec.get("toolUseResult")
            out = res.get("stdout") if isinstance(res, dict) else None
            if not out:
                continue
            for path, vers in catalogue.items():
                hits = [b for b, v in vers.items() if v["body"] and v["body"] in out]
                if hits:
                    seen.append({"kind": "RESOLVED", "path": path, "blobs": hits})
    return seen


def _strings(rec, keys):
    """Every value under `keys`, at any depth."""
    if isinstance(rec, dict):
        for k, v in rec.items():
            if k in keys and isinstance(v, str):
                yield v
            else:
                yield from _strings(v, keys)
    elif isinstance(rec, list):
        for v in rec:
            yield from _strings(v, keys)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--repo", default=".", help="repository to resolve versions against")
    ap.add_argument("--path", action="append", help="prompt path (repeatable)")
    ap.add_argument("--projects", default=str(PROJECTS),
                    help="transcript root override — exists so the VOID and clean paths "
                         "can be EXERCISED against a fixture, per daintree-control.py")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    repo = git("rev-parse", "--show-toplevel", cwd=args.repo)
    if not repo:
        print("VOID  not a git repository — resolved no versions", file=sys.stderr)
        return 2
    repo = repo.strip()
    head = (git("rev-parse", "--short", "HEAD", cwd=repo) or "?").strip()

    paths = args.path or [
        p for p in (git("ls-files", "prompts/*.md", cwd=repo) or "").split()
        if not p.endswith("README.md")
    ]
    if not paths:
        print("VOID  no prompt files found to resolve against", file=sys.stderr)
        return 2

    catalogue, current = {}, {}
    for p in paths:
        vers = versions_of(p, repo)
        if not vers:
            continue
        catalogue[p] = vers
        cur = git("rev-parse", f"HEAD:{p}", cwd=repo)
        current[p] = cur.strip() if cur else None

    if not catalogue:
        print("VOID  no historical versions resolved for any prompt", file=sys.stderr)
        return 2

    # ⛔ Discrimination before verdicts.
    print(f"Doctrine versions  —  {repo}  @  {head}\n")
    undiscriminable = set()
    for p, vers in catalogue.items():
        bad = collisions(vers)
        for a, b in bad:
            undiscriminable |= {a, b}
        flag = f"  ⛔ {len(bad)} indistinguishable pair(s)" if bad else ""
        print(f"  {p:28} {len(vers)} versions, current {(current[p] or '?')[:7]}{flag}")
    if undiscriminable:
        print("\n  ⚠ Some versions are substrings of others. Any session matching such a pair")
        print("    is reported AMBIGUOUS below and is NOT resolved to one of them.")

    root = Path(args.projects)

    # ⛔ Enumerate worktrees from git, not from a name pattern. A role tree placed anywhere
    # without the repo name in its path is invisible to a name match — DEV5's improvised tree
    # under /private/tmp was covered by coincidence, not by construction. `git worktree list`
    # enumerates trees wherever they are. The name match is kept as a fallback for sessions
    # whose tree has since been removed, and each directory reports how it was found.
    def encode(path):
        return str(path).replace("/", "-").replace(".", "-")

    found = {}
    for line in (git("worktree", "list", "--porcelain", cwd=repo) or "").splitlines():
        if line.startswith("worktree "):
            d = root / encode(line[len("worktree "):])
            if d.is_dir():
                found[d] = "git"
    for d in root.glob("*"):
        if d.is_dir() and d not in found and \
                Path(repo).name.replace(".", "-").lower() in d.name.lower():
            found[d] = "name"

    # ⛔ THE DIRECTORY NAME WAS A PROXY FOR THE POPULATION, AND THE WRONG ONE.
    # Both selectors above assume the repo whose prompts are audited is the repo the
    # agents WORK in. It never is: the fleet works in one checkout and `cat`s its
    # prompts out of another, so every prompt read lands in the WORKING repo's
    # transcript directory. Measured 2026-08-20:
    #
    #     project dirs whose name contains "nForma-NEXT"          0
    #     prompt-read records under -…-code-DigitalFrontier-infra 60
    #
    # ⇒ This tool has never produced a reading. Its guard fired correctly every time
    # — VOID, exit 2, "that is the instrument failing" — so it never lied; it simply
    # could not see, and the fleet-wide staleness it exists to detect went unmeasured
    # for as long as it shipped.
    #
    # ★ The fix is to stop scoping by name at all. The DISCRIMINATOR is exact
    # containment of a historical blob in recovered output — a foreign project
    # directory cannot produce a false match, only a slower sweep. Deriving the
    # population from a name was correct derivation over the wrong set.
    scanned_all = False
    if not found:
        scanned_all = True
        for d in root.glob("*"):
            if d.is_dir():
                found[d] = "all"
    dirs = list(found)
    if not dirs:
        print(f"\nVOID  no transcript directories at all under {root}",
              file=sys.stderr)
        print("      established nothing about any agent's loaded doctrine", file=sys.stderr)
        return 2
    if scanned_all:
        print(f"⚠ no transcript directory matches {Path(repo).name!r}, so ALL {len(dirs)} "
              f"were swept. That is correct — the fleet works in one checkout and reads its "
              f"prompts out of another — and it is slower. The blob match is the "
              f"discriminator; a foreign directory cannot produce a false reading.",
              file=sys.stderr)

    by_git = sum(1 for m in found.values() if m == "git")
    print(f"\nSwept {len(dirs)} transcript director{'y' if len(dirs) == 1 else 'ies'} "
          f"({by_git} enumerated from `git worktree list`, "
          f"{len(dirs) - by_git} by name match):")
    for d in dirs:
        print(f"  [{found[d]:4}] {d.name}")

    rows, readings, swept = [], 0, 0
    for d in dirs:
        for t in sorted(d.glob("*.jsonl")):
            swept += 1
            seen = reads_in(t, catalogue)
            if not seen:
                continue
            resolved = [r for r in seen if r["kind"] == "RESOLVED"]
            if not resolved:
                continue
            readings += 1
            last = resolved[-1]
            p, hits = last["path"], last["blobs"]

            # Any read of the SAME prompt occurring after the last resolved one.
            idx = len(seen) - 1 - seen[::-1].index(last)
            later = [r for r in seen[idx + 1:] if r["path"] == p]

            if len(hits) > 1 and set(hits) & undiscriminable:
                verdict, detail = "AMBIG", f"{len(hits)} indistinguishable versions"
            else:
                blob = hits[-1]
                v = catalogue[p][blob]
                stale = blob != current[p]
                detail = (f"{v['lines']} lines, first seen {v['commits'][-1]}"
                          + (f", HEAD has {catalogue[p][current[p]]['lines']}"
                             if stale and current[p] in catalogue[p] else ""))
                if not stale:
                    verdict = "ok"
                elif later:
                    # ⛔ Does NOT become "ok". A ranged read proves the agent saw a span,
                    # not that it holds the current file.
                    verdict = "SAW-LATER"
                    spans = [f"L{r['span'][0]}-{r['span'][1]}" for r in later
                             if r.get("span") and r["span"][0]]
                    where = ", ".join(dict.fromkeys(spans)) if spans else "span not recoverable"
                    detail += f"; {len(later)} later read(s) of it [{where}]"
                else:
                    verdict = "LAUNCH-ONLY"
            rows.append((t.stem[:8], p.split("/")[-1], verdict, detail, len(seen)))

    if not readings:
        print("\nVOID  swept every transcript and recovered zero prompt reads", file=sys.stderr)
        print("      the bootstrap changed, or the transcript shape did;", file=sys.stderr)
        print("      this is an instrument failure, NOT a fleet on current doctrine",
              file=sys.stderr)
        return 2

    order = {"LAUNCH-ONLY": 0, "SAW-LATER": 1, "AMBIG": 2, "ok": 3}
    print(f"\n{'session':10} {'prompt':16} {'state':12} {'reads':>5}  detail")
    for sid, prompt, verdict, detail, n in sorted(rows, key=lambda r: (order.get(r[2], 9), r[0])):
        print(f"{sid:10} {prompt:16} {verdict:12} {n:>5}  {detail}")

    by = {k: sum(1 for r in rows if r[2] == k) for k in order}
    print(f"\nPopulation: {len(rows)} of {swept} transcripts carry a resolvable full read.")
    print(f"  LAUNCH-ONLY  {by['LAUNCH-ONLY']:3}  no later read of that prompt recovered")
    print(f"  SAW-LATER    {by['SAW-LATER']:3}  a later read exists — ⛔ proves the agent LOOKED,")
    print( "                    not that it holds the current file")
    print(f"  ok           {by['ok']:3}  most recent resolvable full read IS the current blob")
    print(f"  AMBIG        {by['AMBIG']:3}  versions this instrument cannot tell apart")
    print(f"  UNKNOWN      {swept - len(rows):3}  no resolvable full read at all")
    print("\n⛔ NOT A RATE. The denominator is transcripts this tool can resolve, not agents,")
    print("   and LAUNCH-ONLY is not 'never re-read' — it is 'no later read RECOVERED'.")
    print("⚠ Reports what a session READ, never what it is obeying. A read is not a load,")
    print("   and compaction can drop text that was read.")

    return 1 if (by['LAUNCH-ONLY'] or by['SAW-LATER']) else 0


if __name__ == "__main__":
    sys.exit(main())
