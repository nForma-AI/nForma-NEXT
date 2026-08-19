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

Exit: 0 every reading current · 1 at least one agent is stale · 2 established nothing.
"""
import argparse
import json
import os
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
    """Prompt reads recovered from one transcript, in the order they occurred."""
    seen = []
    try:
        fh = open(transcript, errors="replace")
    except OSError:
        return None
    with fh:
        for line in fh:
            if '"stdout"' not in line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            res = rec.get("toolUseResult")
            out = res.get("stdout") if isinstance(res, dict) else None
            if not out:
                continue
            for path, vers in catalogue.items():
                hits = [b for b, v in vers.items() if v["body"] and v["body"] in out]
                if hits:
                    seen.append({"path": path, "blobs": hits})
    return seen


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
    dirs = [d for d in root.glob("*") if d.is_dir()
            and Path(repo).name.replace(".", "-").lower() in d.name.lower()]
    if not dirs:
        print(f"\nVOID  no transcript directory under {root} matches {Path(repo).name}",
              file=sys.stderr)
        print("      established nothing about any agent's loaded doctrine", file=sys.stderr)
        return 2

    print(f"\nSwept {len(dirs)} transcript director{'y' if len(dirs) == 1 else 'ies'} "
          f"(worktrees included):")
    for d in dirs:
        print(f"  {d.name}")

    rows, readings, swept = [], 0, 0
    for d in dirs:
        for t in sorted(d.glob("*.jsonl")):
            swept += 1
            seen = reads_in(t, catalogue)
            if not seen:
                continue
            readings += 1
            last = seen[-1]
            p, hits = last["path"], last["blobs"]
            if len(hits) > 1 and set(hits) & undiscriminable:
                verdict, detail = "AMBIG", f"{len(hits)} indistinguishable versions"
            else:
                blob = hits[-1]
                v = catalogue[p][blob]
                stale = blob != current[p]
                verdict = "STALE" if stale else "ok"
                detail = (f"{v['lines']} lines, first seen {v['commits'][-1]}"
                          + (f", HEAD has {catalogue[p][current[p]]['lines']}"
                             if stale and current[p] in catalogue[p] else ""))
            rows.append((t.stem[:8], p.split("/")[-1], verdict, detail, len(seen)))

    if not readings:
        print("\nVOID  swept every transcript and recovered zero prompt reads", file=sys.stderr)
        print("      the bootstrap changed, or the transcript shape did;", file=sys.stderr)
        print("      this is an instrument failure, NOT a fleet on current doctrine",
              file=sys.stderr)
        return 2

    print(f"\n{'session':10} {'prompt':16} {'state':6} {'reads':>5}  detail")
    for sid, prompt, verdict, detail, n in sorted(rows, key=lambda r: (r[2] != "STALE", r[0])):
        print(f"{sid:10} {prompt:16} {verdict:6} {n:>5}  {detail}")

    stale = [r for r in rows if r[2] == "STALE"]
    ambig = [r for r in rows if r[2] == "AMBIG"]
    print(f"\n{swept} transcripts swept · {len(rows)} resolved · {len(stale)} stale "
          f"· {len(ambig)} ambiguous · {swept - len(rows)} UNKNOWN")
    print("⚠ Reports the version a session READ INTO CONTEXT, not the version it is obeying:")
    print("  an agent may have re-read since (`reads` > 1), or lost the text to compaction.")
    print("⚠ A session absent from this table read no prompt this tool could recover. That is")
    print("  UNKNOWN, never 'current'.")

    return 1 if stale else 0


if __name__ == "__main__":
    sys.exit(main())
