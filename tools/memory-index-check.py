#!/usr/bin/env python3
"""Does the memory INDEX cover the memory FILES — and is it small enough to be read?

⛔ MEASURED ON THIS MACHINE, 2026-08-20: **348 memory files, 232 indexed, 115 orphans.**
An orphaned memory is not degraded, it is **invisible** — recall works from the index, so a
file nobody links is a file nobody reads, and nothing anywhere says so.

★ THE RECURSION IS THE POINT. That memory directory already contains an entry titled
*"Memory index truncates by AGE, not importance"*, written after 35 entries were hidden.
The index then grew past the limit again **and acquired 115 unindexed files on top**. ⇒ A
recorded lesson did not fire; only a mechanical check does. (#1263 §7.)

⚠ TWO DIFFERENT FAILURES, AND THEY NEED SEPARATE COUNTS:

    ORPHAN      a file with no link in the index          -> never reachable
    TRUNCATION  an index too large to be loaded whole     -> reachable entries hidden by size

An orphan is fixed by adding a line. Truncation is fixed by shortening lines or splitting
the index, and **no amount of adding lines fixes it** — so reporting them as one number
would send the reader to the wrong remedy.

⚠ THE SIZE LIMIT IS NOT MEASURED HERE. `--limit-kb` defaults to 25, which is what this
fleet's own memory records as the observed truncation point — a RECALLED number, not one
this tool established. It is a flag precisely so a reader can set what they actually know.

Exit: 0 covered and within budget · 1 orphans or oversize · 2 established nothing.
"""
import argparse, os, re, sys

LINK = re.compile(r"\]\(([A-Za-z0-9_.-]+\.md)\)")


def analyse(index_text, filenames, limit_bytes):
    """Pure, so the verdicts can be tested without a memory directory."""
    linked = set(LINK.findall(index_text))
    files = {f for f in filenames if f != "MEMORY.md"}
    orphans = sorted(files - linked)
    dangling = sorted(linked - files)
    size = len(index_text.encode("utf-8"))
    return {
        "files": len(files),
        "linked": len(linked & files),
        "orphans": orphans,
        # ⛔ A link to a file that no longer exists is the OTHER direction, and it is not an
        # orphan. Reported separately because deleting a memory and leaving its line behind
        # makes the index claim coverage it does not have.
        "dangling": dangling,
        "size": size,
        "oversize": size > limit_bytes,
    }


def main():
    ap = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        epilog="An ORPHAN is fixed by adding a line. TRUNCATION is not — adding lines makes "
               "it worse. The counts are separate so the reader is sent to the right remedy.",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default=os.path.expanduser(
        "~/.claude/projects/-Users-jonathanborduas-code-DigitalFrontier-infra/memory"))
    ap.add_argument("--limit-kb", type=float, default=25.0)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()

    idx = os.path.join(args.dir, "MEMORY.md")
    if not os.path.isdir(args.dir) or not os.path.exists(idx):
        print(f"⛔ no MEMORY.md under {args.dir} — a fact about the PATH, not about "
              "coverage. ESTABLISHED NOTHING.", file=sys.stderr)
        return 2

    r = analyse(open(idx, errors="replace").read(),
                os.listdir(args.dir), int(args.limit_kb * 1024))

    for o in r["orphans"][:20]:
        print(f"⛔ ORPHAN     {o}")
    if len(r["orphans"]) > 20:
        print(f"   … and {len(r['orphans']) - 20} more")
    for d in r["dangling"][:10]:
        print(f"⚠ DANGLING   {d}  (indexed, file absent)")

    print(f"\n{r['files']} memory file(s), {r['linked']} indexed, "
          f"{len(r['orphans'])} ORPHANED, {len(r['dangling'])} dangling.", file=sys.stderr)
    print(f"index is {r['size'] / 1024:.1f} KB against a {args.limit_kb:.0f} KB budget"
          f"{'  ⛔ OVERSIZE — entries below the cut are not loaded' if r['oversize'] else ''}",
          file=sys.stderr)
    if r["orphans"]:
        print("⚠ An orphan is INVISIBLE, not degraded: recall works from the index, so a "
              "file nobody links is a file nobody reads.", file=sys.stderr)
    if r["oversize"]:
        print("⛔ Adding index lines does not fix oversize — it makes it worse. Shorten "
              "lines or split the index.", file=sys.stderr)
    return 1 if (r["orphans"] or r["dangling"] or r["oversize"]) else 0


def self_test():
    idx = "- [a](a.md) — x\n- [b](b.md) — y\n"
    r = analyse(idx, ["a.md", "b.md", "c.md", "MEMORY.md"], 10_000)
    ok = True
    ok &= _c("an unlinked file is an orphan", r["orphans"], ["c.md"])
    ok &= _c("MEMORY.md is not its own orphan", "MEMORY.md" in r["orphans"], False)
    ok &= _c("linked count excludes missing files", r["linked"], 2)
    r2 = analyse(idx + "- [gone](gone.md)\n", ["a.md", "b.md"], 10_000)
    ok &= _c("a link to an absent file is DANGLING, not an orphan", r2["dangling"], ["gone.md"])
    ok &= _c("and dangling is not counted as coverage", r2["linked"], 2)
    r3 = analyse("x" * 30_000, ["a.md"], 25 * 1024)
    ok &= _c("oversize is detected", r3["oversize"], True)
    ok &= _c("oversize is separate from orphans", r3["orphans"], ["a.md"])
    r4 = analyse(idx, ["a.md", "b.md"], 10_000)
    ok &= _c("a fully covered index is clean", (r4["orphans"], r4["dangling"], r4["oversize"]),
             ([], [], False))
    print("\nselftest PASS" if ok else "\nselftest FAIL")
    return 0 if ok else 2


def _c(name, got, want):
    good = got == want
    print(f"  {'ok  ' if good else 'FAIL'} {name}: got {got!r} want {want!r}")
    return good


if __name__ == "__main__":
    sys.exit(main())
