#!/usr/bin/env python3
"""Which reference implementations have MOVED since we recorded them?

⛔ Why this exists. A 249-line root-cause investigation of a failure this fleet spent a
night re-deriving from CI logs had been on this machine since 2026-07-20 — a month.
The standing rule "check just-akash before blaming a provider" existed and nobody
opened its `docs/`.

⚠ And searching is not the remedy. Measured 2026-08-20: 304 repositories under
~/code, and 14,517 markdown files mention "exec". A keyword sweep returns a haystack.
So `reference-implementations.md` is CURATED, and this tool answers the one question a
curated list cannot answer about itself: **has any of it moved?**

★ A CHANGED entry is not an instruction. It says the upstream artifact moved; whether
the change applies here is a judgement, and this deliberately does not make it.

⛔ MISSING is not UNCHANGED. A repo absent from this machine, or a path that no longer
exists, establishes nothing about the reference — and reporting it as "fine" is the
absence-read-as-success defect this repository has now caught in five of its own
instruments.

Exit: 0 every entry current · 1 at least one MOVED or MISSING · 2 established nothing
      (register unreadable, or no entries parsed — a table rename must not read clean)
"""
import os
import re
import subprocess
import sys

ROOT = os.path.expanduser("~/code")
REGISTER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "reference-implementations.md")

# | repo | artifact | authoritative for … | `blobsha` |
ROW = re.compile(r"^\|\s*`([^`]+)`\s*\|\s*`([^`]+)`\s*\|.*\|\s*`([0-9a-f]{40})`\s*\|\s*$")


def parse(text):
    return [(m.group(1), m.group(2), m.group(3))
            for m in (ROW.match(l) for l in text.split("\n")) if m]


def blob(repo, path):
    """Current blob sha of `path` at HEAD, or a reason it could not be read."""
    d = os.path.join(ROOT, repo)
    if not os.path.isdir(d):
        return None, f"repo not on this machine at {d}"
    try:
        p = subprocess.run(["git", "-C", d, "rev-parse", f"HEAD:{path}"],
                           capture_output=True, text=True)
    except OSError as exc:
        return None, f"cannot run git: {exc}"
    if p.returncode != 0:
        return None, f"path not at HEAD ({(p.stderr or '').strip()[:70]})"
    return p.stdout.strip(), None


def main():
    try:
        text = open(REGISTER).read()
    except OSError as exc:
        print(f"⛔ VOID: cannot read {REGISTER}: {exc}", file=sys.stderr)
        return 2

    rows = parse(text)
    if not rows:
        print(f"⛔ VOID: parsed 0 entries from {REGISTER}. The table shape moved — a rename "
              f"here would otherwise read as 'nothing to adopt'.", file=sys.stderr)
        return 2

    moved, missing = [], []
    for repo, path, recorded in rows:
        current, why = blob(repo, path)
        if current is None:
            missing.append((repo, path, why))
            print(f"⛔ MISSING   {repo}/{path}\n            {why}")
        elif current != recorded:
            moved.append((repo, path, recorded, current))
            print(f"★ MOVED     {repo}/{path}\n            recorded {recorded[:12]} "
                  f"→ now {current[:12]}\n            "
                  f"git -C ~/code/{repo} diff {recorded[:12]} {current[:12]} -- {path}")
        else:
            print(f"  current   {repo}/{path}")

    print(f"\n{len(rows)} entr{'y' if len(rows)==1 else 'ies'}: "
          f"{len(moved)} moved, {len(missing)} missing, "
          f"{len(rows)-len(moved)-len(missing)} current", file=sys.stderr)
    if moved:
        print("⚠ A MOVED entry is not an instruction — it says the artifact changed. Whether "
              "the change applies here is a judgement this tool does not make.", file=sys.stderr)
    if missing:
        print("⛔ A MISSING entry established NOTHING about that reference. It is not "
              "'unchanged'.", file=sys.stderr)
    return 1 if (moved or missing) else 0


if __name__ == "__main__":
    sys.exit(main())
