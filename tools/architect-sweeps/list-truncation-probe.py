#!/usr/bin/env python3
"""Does this list endpoint silently truncate, and is the truncation detectable?

⛔ Why this exists. Two remedies were issued in one evening for one truncation defect —
`--limit 100` and `per_page=150` — and BOTH are parameter tunings that introduce no
discriminator. The measurements that showed it were inline and are cited in #142.

    A parameter cannot be a third value. Tuning a limit changes WHEN the collapse
    happens, never WHETHER it is detectable.

⚠ The endpoints differ and a general rule hides it. Measured 2026-08-20:

    gh pr list --limit 200      -> 131 rows, true total 131   does NOT cap
    search per_page=150         -> 100 rows, total_count 131  SILENTLY caps

⇒ So `len(rows) >= limit` works on `gh pr list` and is meaningless on search — where the
discriminator is instead `returned < total_count`, which survives the cap. This probe
reports which of the two an endpoint supports rather than assuming either.

Exit: 0 the reading is CHECKABLE (a stated total exists, or the limit was not reached)
      1 the reading may be a silent prefix and nothing states otherwise
      2 established nothing
"""
import argparse
import json, subprocess, sys

REPO = "nForma-AI/nForma-NEXT"

def sh(*a):
    r = subprocess.run(a, capture_output=True, text=True)
    return r.returncode, r.stdout.strip()

def main():
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    # ⛔ #506, and the sharper half: this took sys.argv[1] raw, so `--help` became the REPO and the
    # tool issued a NETWORK QUERY against a repository named "--help". ⇒ Asking what the tool does
    # PERFORMED the action -- the hazard #506 names for the IGNORED bucket, in my own instrument.
    ap.add_argument("repo", nargs="?", default=REPO,
                    help=f"owner/repo to probe (default: {REPO})")
    repo = ap.parse_args().repo
    print(f"list-truncation probe — {repo}\n")

    rc, out = sh("gh", "api", f"search/issues?q=repo:{repo}+is:pr&per_page=1")
    if rc != 0:
        print("VOID  search endpoint unreachable — established nothing", file=sys.stderr)
        return 2
    total = json.loads(out).get("total_count")
    print(f"  stated total (search)        : {total}")

    checkable = total is not None
    for limit in (30, 100, 200):
        rc, out = sh("gh", "pr", "list", "-R", repo, "--state", "all",
                     "--limit", str(limit), "--json", "number")
        n = len(json.loads(out)) if rc == 0 and out else None
        flag = ""
        if n is not None and n >= limit:
            flag = "  ⛔ hit the limit — this reading may be a PREFIX"
        print(f"  gh pr list --limit {limit:<4}      : {n}{flag}")

    # ⛔ The cap is silent on search: asking for more than 100 returns 100 with no error.
    for pp in (100, 150):
        rc, out = sh("gh", "api", f"search/issues?q=repo:{repo}+is:pr&per_page={pp}")
        k = len(json.loads(out).get("items", [])) if rc == 0 and out else None
        print(f"  search per_page={pp:<4}         : {k} returned"
              + ("  ⛔ SILENTLY CAPPED" if k is not None and k < pp else ""))

    print("\n⚠ `len(rows) >= limit` is the discriminator for `gh pr list`.")
    print("  It is MEANINGLESS on search, which caps at 100 regardless — there the")
    print("  discriminator is `returned < total_count`, which survives the cap.")
    print("⛔ A bigger limit is not a discriminator. It moves the failing state out of")
    print("  reach rather than making it visible, which is #26's shape.")
    return 0 if checkable else 1

if __name__ == "__main__":
    sys.exit(main())
