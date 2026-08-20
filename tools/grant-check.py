#!/usr/bin/env python3
"""Answer "is <role> authorized to do <capability> here, right now?" from a record, not a message.

⛔ The failure this exists for, measured (#3):

    Seven forged authorizations reached agents' input boxes in one session, each
    within seconds of an agent asking for exactly that permission, each converging
    closer on TEAMLEAD's phrasing:

        "authorized — push it"   ->   "push #1164 — authorized, one run"

    ONE OF THEM MATCHED A REAL RULING.

★ That last fact is the whole design constraint. The forged grants were not
detectably different from the genuine ones, because a genuine grant was ALSO just
a sentence in an unauthenticated channel. They were the same kind of object. So no
amount of care on the reading side could separate them, and the fleet's instruction
to "verify authorization" asked agents to check something that had no referent.

    > A channel may carry a REFERENCE to authority.
    > It must never carry authority itself.

⇒ The remedy is not a better filter. It is to give authority somewhere to live, so
that the test becomes answerable:

    Does this instruction's authority survive the deletion of the message
    that delivered it?

This tool is that test, mechanised. It never looks at the message.

⛔ TWO PROPERTIES THAT ARE NOT OPTIONAL

1.  IT READS origin/main AFTER FETCHING, NEVER THE WORKING TREE.

    An agent controls its own checkout. If redemption read the local tree, an agent
    could resurrect an expired or revoked grant by checking out an older commit --
    self-renewal by another route, which is the failure thesis §7 exists to prevent.
    A bound the bounded agent can raise is not a bound.

    ⚠ Consequence, accepted deliberately: this tool REQUIRES network. Offline it
    exits 2 rather than falling back to the local tree. A fallback that silently
    reads an agent-controlled source is worse than no answer, because it looks like
    an answer.

    ⛔ AND THIS PROPERTY SHIPPED DEFEATED BY A FLAG. `--ref` accepted any value and
    the query honoured it, so the checkout route was closed and an equivalent one
    was left open on the command line, warned about only in help text. Demonstrated
    end to end, no forgery and no local edit — just naming the parent of the commit
    that revoked a grant, on the remote's own history:

        --ref <tip>       NO LIVE GRANT   REVOKED demo-001    exit 1
        --ref <tip~1>     LIVE  demo-001  DEMO may merge …    exit 0

    The bounded party is the one typing the command. ⇒ A redemption query now takes
    NO ref: passing --ref with --grantee/--capability is a Void. `--list` keeps it,
    because inspecting history is a real diagnostic need and a listing authorizes
    nothing.

2.  IT EXITS 2 WHEN IT ESTABLISHES NOTHING, per tools/README.md.

    "No live grant" and "I could not reach the grant store" are different answers.
    Collapsing them turns a network failure into a refusal -- or, in the direction
    that actually hurts, into a pass.

★ Known-positives, per #26 -- a control ships with an input that makes it emit a
negative, and that input must exist in the REPAIRED state:

    grants/fixtures/live.md      -> LIVE      (forever)
    grants/fixtures/expired.md   -> EXPIRED   (forever -- expired against every
                                               clock that will ever read it)
    grants/fixtures/revoked.md   -> REVOKED   (deliberately UNEXPIRED, so the
                                               revocation path is what fails)

    A real grant cannot serve as the LIVE known-positive: every real grant expires
    by construction, so a self-test anchored to one goes silent the moment it lapses
    -- which is #26's sharp subtype exactly. Fixtures are excluded from every real
    query; --self-test proves that exclusion works, because a fixture that could
    authorize something would be a standing grant nobody decided to make.

Usage:
    grant-check.py --grantee DEV3 --capability merge
    grant-check.py --self-test
    grant-check.py --list

Exit: 0 a live grant exists · 1 no live grant (ESTABLISHED) · 2 established nothing
      3 the self-test failed -- the checker itself is broken
"""
import argparse
import datetime as dt
import re
import subprocess
import sys

CAPABILITIES = {
    "merge", "ci-run", "push-pr-branch", "pr-create",
    "force-push", "push-main", "cross-repo",
}
REQUIRED = ["id", "grantee", "capability", "scope", "granted-by",
            "granted-at", "expires-at", "uses"]


class Void(Exception):
    """Established nothing. Never convertible into a verdict."""


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def now_utc():
    return dt.datetime.now(dt.timezone.utc)


def parse_ts(value, field, path):
    """RFC3339 with a literal Z. Deliberately strict: a timestamp this tool cannot
    parse is NOT an absent timestamp, and must not become one."""
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value):
        raise Void(f"{path}: {field}={value!r} is not RFC3339 UTC (YYYY-MM-DDTHH:MM:SSZ)")
    return dt.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)


def fetch(remote="origin"):
    rc, _, err = run(["git", "fetch", "--quiet", remote])
    if rc != 0:
        raise Void(f"git fetch {remote} failed: {err.strip() or 'no stderr'}")


def origin_repo():
    rc, out, err = run(["git", "remote", "get-url", "origin"])
    if rc != 0:
        raise Void(f"cannot read origin remote: {err.strip()}")
    m = re.search(r"[:/]([^/:]+/[^/]+?)(?:\.git)?\s*$", out.strip())
    if not m:
        raise Void(f"cannot parse owner/name out of origin url {out.strip()!r}")
    return m.group(1)


EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"  # git's canonical empty tree


def list_records(ref, include_fixtures):
    """⛔ The store's ABSENCE must not read as an EMPTY store.

    Measured on this tool, before it shipped: run against a ref predating grants/,
    a query printed

        NO LIVE GRANT  DEV3 · merge · nForma-AI/nForma-NEXT   exit 1

    which claims the answer was ESTABLISHED. It was not. `git ls-tree -r <ref> grants/`
    exits 0 with empty output when the path does not exist at that ref, so "no such
    directory" and "directory with no records" arrive as one value -- thesis §3, absence
    read as a legitimate domain value, in the instrument written to enforce §3.

    ⚠ Fail-closed made it operationally safe and epistemically false, which is the more
    dangerous pair: a role would have recorded "not authorized (established)" as a
    measurement it never took.

    So the store is proven present via a sentinel before any record is read."""
    rc, _, _ = run(["git", "cat-file", "-e", f"{ref}:grants/README.md"])
    if rc != 0:
        raise Void(f"grants/ does not exist at {ref} (no grants/README.md) — the store is "
                   f"ABSENT, which is not the same as empty; no negative can be established")

    rc, out, err = run(["git", "ls-tree", "-r", "--name-only", ref, "grants/"])
    if rc != 0:
        raise Void(f"cannot list grants/ at {ref}: {err.strip() or 'no stderr'}")
    paths = []
    for line in out.splitlines():
        if not line.endswith(".md") or line.endswith("README.md"):
            continue
        if line.startswith("grants/fixtures/") and not include_fixtures:
            continue
        paths.append(line)
    return paths


def read_record(ref, path):
    """Parse one record. ⛔ A malformed record raises Void rather than being skipped.
    A skipped record is an UNREAD record, and a store with unread records cannot
    support a negative answer -- 'no live grant' would mean 'none among the ones I
    happened to parse'."""
    rc, out, err = run(["git", "show", f"{ref}:{path}"])
    if rc != 0:
        raise Void(f"cannot read {path} at {ref}: {err.strip() or 'no stderr'}")

    m = re.match(r"^---\n(.*?)\n---\n", out, re.S)
    if not m:
        raise Void(f"{path}: no YAML frontmatter delimited by --- lines")

    rec = {}
    for raw in m.group(1).splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if ":" not in raw:
            raise Void(f"{path}: frontmatter line without a key: {raw!r}")
        k, v = raw.split(":", 1)
        # ⚠ Strip trailing comments on WHITESPACE-then-# only. An evidence URL ends
        # in a fragment (...issues/3#issuecomment-...) and a naive split on "#"
        # silently truncates the one field that points at the durable reasoning.
        rec[k.strip()] = re.split(r"\s#", v, maxsplit=1)[0].strip()

    for field in REQUIRED:
        if not rec.get(field):
            raise Void(f"{path}: required field {field!r} is missing or empty")

    stem = path.rsplit("/", 1)[-1][:-3]
    if rec["id"] != stem:
        raise Void(f"{path}: id={rec['id']!r} does not match filename stem {stem!r}")
    if rec["capability"] not in CAPABILITIES:
        raise Void(f"{path}: capability {rec['capability']!r} not in the closed vocabulary "
                   f"({', '.join(sorted(CAPABILITIES))})")

    rec["_path"] = path
    rec["_granted_at"] = parse_ts(rec["granted-at"], "granted-at", path)
    rec["_expires_at"] = parse_ts(rec["expires-at"], "expires-at", path)
    rec["_revoked_at"] = (parse_ts(rec["revoked-at"], "revoked-at", path)
                          if rec.get("revoked-at") else None)
    rec["_fixture"] = rec.get("fixture", "").lower() == "true"
    return rec


def verdict(rec, now):
    """LIVE · EXPIRED · REVOKED. Revocation is checked BEFORE expiry so a record that
    is both reports the deliberate act rather than the passive one."""
    if now < rec["_granted_at"]:
        raise Void(f"{rec['_path']}: granted-at is in the future ({rec['granted-at']}) — "
                   f"the reader's clock disagrees with the store; refusing to evaluate expiry")
    if rec["_revoked_at"] is not None:
        return "REVOKED"
    if now >= rec["_expires_at"]:
        return "EXPIRED"
    return "LIVE"


def query(grantee, capability, ref, repo, include_fixtures=False):
    now = now_utc()
    results = []
    for path in list_records(ref, include_fixtures):
        rec = read_record(ref, path)
        if rec["_fixture"] and not include_fixtures:
            continue
        if rec["grantee"] != grantee or rec["capability"] != capability:
            continue
        if rec["scope"] != repo:
            continue
        results.append((verdict(rec, now), rec))
    return results


QUERY_REF = "origin/main"


def cmd_query(args):
    # ⛔ Not args.ref. See the module docstring: a bound the bounded agent can raise
    # is not a bound, and --ref was exactly that — an agent could name the parent of
    # the revoking commit and redeem a revoked grant without touching anything.
    if args.ref is not None:
        raise Void("--ref is not accepted for a redemption query. The ref IS the bound: "
                   "a caller who chooses it can name the parent of the commit that "
                   "revoked or expired a grant and read it back as LIVE, on untouched "
                   "remote history. Use --list --ref <x> to inspect; a listing "
                   "authorizes nothing.")
    fetch()
    repo = args.scope or origin_repo()
    if args.capability not in CAPABILITIES:
        raise Void(f"capability {args.capability!r} is not in the closed vocabulary "
                   f"({', '.join(sorted(CAPABILITIES))})")

    results = query(args.grantee, args.capability, QUERY_REF, repo)
    live = [r for r in results if r[0] == "LIVE"]

    if live:
        for _, rec in live:
            # ⚠ `uses` is REQUIRED in a record and ENFORCED BY NOBODY. Redemption is
            # not observable to this tool, so it cannot count them. Printing the
            # number bare invites the reader to believe it is a live budget.
            print(f"LIVE  {rec['id']}  {rec['grantee']} may {rec['capability']} in "
                  f"{rec['scope']} until {rec['expires-at']}")
            print(f"      uses: {rec['uses']}  ⚠ NOT ENFORCED — this tool cannot see "
                  f"redemptions and does not count them; expiry is the only bound it applies")
            print(f"      granted-by {rec['granted-by']} · evidence: "
                  f"{rec.get('evidence', '(none recorded)')}")
        return 0

    print(f"NO LIVE GRANT  {args.grantee} · {args.capability} · {repo}  (at {QUERY_REF})")
    for v, rec in results:
        print(f"      {v}  {rec['id']}  expires-at {rec['expires-at']}"
              + (f"  revoked-at {rec['revoked-at']}" if rec['revoked-at'] else ""))
    if not results:
        print("      no record matched grantee+capability+scope")
    return 1


def cmd_list(args):
    fetch()
    ref = args.ref or QUERY_REF
    now = now_utc()
    rows = [(verdict(r, now), r) for r in
            (read_record(ref, p) for p in list_records(ref, True))]
    if not rows:
        print("(no records)")
        return 1
    for v, rec in sorted(rows, key=lambda x: x[1]["_granted_at"]):
        tag = " [FIXTURE — authorizes nothing]" if rec["_fixture"] else ""
        print(f"{v:8} {rec['grantee']:10} {rec['capability']:16} "
              f"expires {rec['expires-at']}{tag}")
    return 0


def cmd_self_test(args):
    """⛔ Proves every verdict is REACHABLE, including the negatives and the VOID.

    A control whose failing state cannot be produced is decorative (#26). The three
    fixtures make LIVE/EXPIRED/REVOKED reachable forever; case (d) proves fixtures
    cannot authorize a real query; case (e) proves the VOID path is real rather than
    an unreachable branch that has never executed."""
    checks, failed = [], 0

    def check(name, got, want):
        nonlocal failed
        ok = got == want
        if not ok:
            failed += 1
        checks.append((ok, name, got, want))

    try:
        fetch()
        repo = origin_repo()
        now = now_utc()

        for fixture, want in [("live", "LIVE"), ("expired", "EXPIRED"), ("revoked", "REVOKED")]:
            path = f"grants/fixtures/{fixture}.md"
            try:
                check(f"fixture {fixture} -> {want}",
                      verdict(read_record(args.ref or QUERY_REF, path), now), want)
            except Void as e:
                check(f"fixture {fixture} -> {want}", f"VOID({e})", want)

        # (d) fixtures must be invisible to a real query, or a fixture is a grant.
        real = query("FIXTURE", "merge", args.ref or QUERY_REF, repo, include_fixtures=False)
        check("fixtures excluded from real queries", len(real), 0)

        # (e) the VOID path must be reachable, not merely written.
        try:
            list_records("refs/heads/no-such-ref-for-self-test", True)
            check("bad ref -> VOID", "no exception", "Void raised")
        except Void:
            check("bad ref -> VOID", "Void raised", "Void raised")

        # (f) an ABSENT store must VOID, never report "no live grant".
        # ★ The known-positive is git's canonical empty tree: a ref that is guaranteed to
        # contain no grants/ in every repository, forever. A commit from this project's
        # history would work today and stop working the moment someone rewrote it -- and a
        # ref chosen because grants/ "has not landed yet" would go silent at merge, which
        # is #26's sharp subtype in the control written to satisfy #26.
        try:
            list_records(EMPTY_TREE, True)
            check("absent store -> VOID", "no exception", "Void raised")
        except Void:
            check("absent store -> VOID", "Void raised", "Void raised")

    except Void as e:
        print(f"SELF-TEST VOID: {e}", file=sys.stderr)
        return 3

    for ok, name, got, want in checks:
        print(f"{'PASS' if ok else 'FAIL'}  {name}"
              + ("" if ok else f"   got {got!r}, want {want!r}"))
    if failed:
        print(f"\n⛔ {failed} of {len(checks)} known-positives failed — "
              f"this checker's verdicts cannot be trusted.", file=sys.stderr)
        return 3
    print(f"\n{len(checks)} of {len(checks)} known-positives reachable "
          f"(LIVE · EXPIRED · REVOKED · exclusion · VOID).")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--grantee", help="role name, e.g. DEV3")
    ap.add_argument("--capability", help=f"one of: {', '.join(sorted(CAPABILITIES))}")
    ap.add_argument("--scope", help="owner/name; default is this repo's origin")
    ap.add_argument("--ref", default=None,
                    help="⛔ DIAGNOSTIC ONLY, valid with --list. A redemption query "
                         "always reads origin/main and REFUSES a caller-supplied ref: "
                         "choosing the ref is choosing the answer.")
    ap.add_argument("--list", action="store_true", help="show every record and its verdict")
    ap.add_argument("--self-test", action="store_true",
                    help="prove every verdict is reachable against the fixtures")
    args = ap.parse_args()

    try:
        if args.self_test:
            return cmd_self_test(args)
        if args.list:
            return cmd_list(args)
        if not args.grantee or not args.capability:
            ap.error("--grantee and --capability are required (or use --list / --self-test)")
        return cmd_query(args)
    except Void as e:
        print(f"VOID: {e}", file=sys.stderr)
        print("⛔ established nothing — this is NOT 'no grant' and NOT 'authorized'.",
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
