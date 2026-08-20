#!/usr/bin/env python3
"""Has anyone already written this — in a channel that could actually contain the answer?

⛔ THE MEASURED DEFECT, three panes in one night, 2026-08-20:
   DEV2 opened #353 at 22:56:00Z. DEV3 opened #356 at 22:59:25Z on the same ruling, holding
   the same rule. ARCHITECT then ruled on the question twice. All three had checked for
   prior art first. ALL THREE CHECKED `main`.

   ⇒ An OPEN PR is not on `main`. The probe's corpus structurally could not contain the
   answer, so ABSENT was returned three times and was correct about a population nobody
   meant. That is `goals/README.md` criterion 5's POPULATION leg, and the near-miss was an
   instance of the very rule the three panes were writing.

⚠ THIS TOOL IS NOT A SEARCH ENGINE AND MUST NOT BE READ AS ONE. It reports WHICH CHANNELS
   WERE READ and what each returned. "Nothing found" from one channel is not absence; it is
   one channel's silence, and the row says which.

Exit codes:
  0  every channel read, no prior art in any of them      (and both controls fired)
  1  prior art found — the rows say where
  2  ESTABLISHED NOTHING — a channel was unreadable, or the controls did not fire
     ⚠ never "all clear"
  3  CONTROL FAILED — the positive did not fire, or the negative did
"""
import argparse, json, subprocess, sys, uuid

CHANNELS = ("open-prs", "merged-prs", "main-tree")


def gh(*args):
    """⚠ Exit status read directly. `$?` after a pipe is the pipe's, not the program's."""
    p = subprocess.run(("gh",) + args, capture_output=True, text=True, timeout=120)
    return p.returncode, p.stdout


def search(term, repo, merged_limit):
    """Returns {channel: (ok, [hit, ...])}. ok=False means the channel could not be read —
    which is VOID for that channel, never zero hits."""
    low, out = term.lower(), {}

    rc, s = gh("pr", "list", "-R", repo, "--state", "open", "--limit", "200",
               "--json", "number,title,body,files")
    out["open-prs"] = _scan(rc, s, low, "PR")

    rc, s = gh("pr", "list", "-R", repo, "--state", "merged", "--limit", str(merged_limit),
               "--json", "number,title,body,files")
    out["merged-prs"] = _scan(rc, s, low, "PR")

    # ⚠ Deliberately NOT GitHub code search: it is index-backed and lags, so its silence is
    #   a timing artifact rather than a reading. `main-tree` is done locally against a ref.
    rc2 = subprocess.run(["git", "grep", "-l", "-i", "-F", term, "origin/main"],
                         capture_output=True, text=True)
    if rc2.returncode not in (0, 1):
        out["main-tree"] = (False, [])
    else:
        hits = [f"file {l.split(':', 1)[1]}" for l in rc2.stdout.splitlines() if ":" in l]
        out["main-tree"] = (True, hits)
    return out


def _scan(rc, stdout, low, kind):
    if rc != 0 or not stdout.strip():
        return (False, [])
    try:
        rows = json.loads(stdout)
    except ValueError:
        return (False, [])
    hits = []
    for r in rows:
        where = []
        if low in (r.get("title") or "").lower():
            where.append("title")
        if low in (r.get("body") or "").lower():
            where.append("body")
        paths = [f["path"] for f in (r.get("files") or [])]
        if any(low in p.lower() for p in paths):
            where.append("path")
        if where:
            hits.append(f"{kind} #{r['number']} ({'+'.join(where)}) {(r.get('title') or '')[:54]}")
    return (True, hits)


def controls(repo, merged_limit):
    """⛔ TWO-SIDED, per DEV2 (#353): a probe must demonstrate ON THIS RUN that it can return
    the answer it did not return. A one-sided control catches a false ABSENT and is blind to
    a predicate that matches everything.

      POSITIVE  a term certain to be present -> must be FOUND
      NEGATIVE  a fresh nonce -> must be found NOWHERE

    ⚠ The nonce is generated per run, so no mention of it can exist anywhere (#36: match on
    something a mention cannot produce)."""
    pos = search("README", repo, merged_limit)
    neg = search("prior-art-nonce-" + uuid.uuid4().hex[:16], repo, merged_limit)
    fired, blind = [], []
    for ch in CHANNELS:
        ok_p, hits_p = pos[ch]
        ok_n, hits_n = neg[ch]
        if not ok_p or not ok_n:
            continue                       # unreadable: reported separately, not scored
        if hits_p and not hits_n:
            fired.append(ch)
        else:
            blind.append(f"{ch}: positive={'hit' if hits_p else 'MISS'} "
                         f"negative={'FALSE-HIT' if hits_n else 'clean'}")
    return fired, blind


def main():
    ap = argparse.ArgumentParser(
        description=__doc__.split("\n")[0],
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    ap.add_argument("term", nargs="?", help="the phrase you are about to write about")
    ap.add_argument("--repo", default="nForma-AI/nForma-NEXT")
    ap.add_argument("--merged-limit", type=int, default=100)
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()

    if a.self_test:
        return self_test()
    if not a.term:
        print("⛔ no term given — ESTABLISHED NOTHING.", file=sys.stderr)
        return 2

    fired, blind = controls(a.repo, a.merged_limit)
    res = search(a.term, a.repo, a.merged_limit)

    print(f"prior art for {a.term!r} in {a.repo}\n")
    total, unread = 0, []
    for ch in CHANNELS:
        ok, hits = res[ch]
        if not ok:
            print(f"  ⛔ VOID        {ch:<12} channel unreadable — ESTABLISHED NOTHING")
            unread.append(ch)
            continue
        ctl = "control fired" if ch in fired else "⛔ CONTROL DID NOT FIRE"
        print(f"  {'FOUND' if hits else 'none ':<12} {ch:<12} {len(hits):>3} hit(s)   [{ctl}]")
        for h in hits[:6]:
            print(f"                   {h}")
        total += len(hits)

    print(f"\n  channels read {len(CHANNELS) - len(unread)} of {len(CHANNELS)}"
          f" · controls fired on {len(fired)} · hits {total}")
    if blind:
        print("\n⛔ CONTROL FAILED — a channel could not demonstrate it can answer both ways:")
        for b in blind:
            print(f"     {b}")
        return 3
    if unread:
        print("\n⚠ A channel was unreadable. 'none' from the others is NOT absence.")
        return 2
    print("\n⚠ Absence here means these three channels are silent. It is not a claim about "
          "\n   messages, transcripts, or another estate's board.")
    return 1 if total else 0


def self_test():
    ok = True

    def check(name, got, want):
        nonlocal ok
        if got != want:
            print(f"⛔ FAIL  {name}: got {got!r}, want {want!r}"); ok = False
        else:
            print(f"  PASS  {name}: {got!r}")

    # the scanner, both directions, without touching the network
    rows = json.dumps([{"number": 7, "title": "Widen the noun", "body": "",
                        "files": [{"path": "goals/README.md"}]}])
    check("a title hit is found", _scan(0, rows, "widen", "PR")[1] != [], True)
    check("a path hit is found", _scan(0, rows, "goals/", "PR")[1] != [], True)
    check("a term in neither is NOT found", _scan(0, rows, "zzz-absent", "PR")[1], [])
    # ⛔ a failed channel must be VOID, never 'no hits' — the whole point of the tool
    check("rc!=0 is VOID, not empty", _scan(2, rows, "widen", "PR")[0], False)
    check("empty stdout is VOID, not empty", _scan(0, "", "widen", "PR")[0], False)
    check("unparseable stdout is VOID", _scan(0, "not json", "widen", "PR")[0], False)
    print("all checks passed" if ok else "⛔ self-test FAILED")
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(main())
