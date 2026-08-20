#!/usr/bin/env python3
"""Pins grant-check.py's two non-optional properties against an agent that wants to break them.

Written from the DOCSTRING, which states them as not optional:

    1. IT READS origin/main AFTER FETCHING, NEVER THE WORKING TREE.
       "An agent could resurrect an expired or revoked grant by checking out an older
        commit — self-renewal by another route. A bound the bounded agent can raise is
        not a bound."
    2. IT EXITS 2 WHEN IT ESTABLISHES NOTHING.

⛔ Property 1 shipped defeated by a flag. `--ref` accepted any value and the query honoured
it, so the checkout route was closed and an identical one was left open on the command
line — warned about only in help text. Demonstrated with no forgery and no local edit, just
naming the parent of the commit that revoked a grant, on the remote's own history:

    --ref <tip>     NO LIVE GRANT  REVOKED demo-001   exit 1
    --ref <tip~1>   LIVE  demo-001  DEMO may merge …  exit 0

The harness below builds a real bare remote, because the property under test is about
whose history is authoritative — a fixture that fakes the remote cannot test it.

Run: python3 tools/test_grant_check.py
"""
import datetime as dt
import os
import shutil
import subprocess
import sys
import tempfile

TOOL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "grant-check.py")


def sh(cwd, *argv):
    p = subprocess.run(argv, cwd=cwd, capture_output=True, text=True)
    if p.returncode != 0 and argv[0] == "git":
        raise RuntimeError(f"{' '.join(argv)} -> {p.returncode}: {p.stderr.strip()}")
    return p.stdout.strip()


def tool(cwd, *args):
    p = subprocess.run([sys.executable, TOOL, *args], cwd=cwd, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def record(scope, revoked=False, expired=False):
    now = dt.datetime.now(dt.timezone.utc)
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    exp = (now - dt.timedelta(days=1)) if expired else (now + dt.timedelta(days=30))
    body = ["---", "id: demo-001", "grantee: DEMO", "capability: merge",
            f"scope: {scope}", "granted-by: TEAMLEAD",
            f"granted-at: {(now - dt.timedelta(hours=1)).strftime(fmt)}",
            f"expires-at: {exp.strftime(fmt)}", "uses: 1"]
    if revoked:
        body.append(f"revoked-at: {(now - dt.timedelta(minutes=5)).strftime(fmt)}")
    body += ["---", "demo grant for a test", ""]
    return "\n".join(body)


def build(tmp):
    """A real bare remote plus an agent-side clone. The remote is the authority."""
    remote = os.path.join(tmp, "remote.git")
    seed = os.path.join(tmp, "seed")
    sh(tmp, "git", "init", "--quiet", "--bare", "-b", "main", remote)
    sh(tmp, "git", "init", "--quiet", "-b", "main", seed)
    sh(seed, "git", "config", "user.email", "t@t.t")
    sh(seed, "git", "config", "user.name", "t")
    os.makedirs(os.path.join(seed, "grants"))
    open(os.path.join(seed, "grants", "README.md"), "w").write("# grants\n")
    sh(seed, "git", "add", "-A")
    sh(seed, "git", "commit", "--quiet", "-m", "seed store")
    sh(seed, "git", "remote", "add", "origin", remote)
    sh(seed, "git", "push", "--quiet", "-u", "origin", "main")

    clone = os.path.join(tmp, "clone")
    sh(tmp, "git", "clone", "--quiet", remote, clone)
    scope = sh(clone, "git", "remote", "get-url", "origin")
    scope = "/".join(scope.rstrip("/").split("/")[-2:]).removesuffix(".git")

    # state A: live grant.  state B: TEAMLEAD revokes it.
    open(os.path.join(seed, "grants", "demo-001.md"), "w").write(record(scope))
    sh(seed, "git", "add", "-A"); sh(seed, "git", "commit", "--quiet", "-m", "grant")
    sh(seed, "git", "push", "--quiet", "origin", "main")
    a = sh(seed, "git", "rev-parse", "HEAD")
    return remote, seed, clone, scope, a


def revoke(seed, scope):
    open(os.path.join(seed, "grants", "demo-001.md"), "w").write(record(scope, revoked=True))
    sh(seed, "git", "add", "-A"); sh(seed, "git", "commit", "--quiet", "-m", "revoke")
    sh(seed, "git", "push", "--quiet", "origin", "main")


def check(name, got, want):
    ok = got == want
    print(("  PASS  " if ok else "  FAIL  ") + f"{name}: got {got!r}, want {want!r}")
    return ok


def main():
    f = 0
    tmp = tempfile.mkdtemp()
    try:
        remote, seed, clone, scope, a = build(tmp)

        print("a live grant on origin/main redeems:")
        rc, out = tool(clone, "--grantee", "DEMO", "--capability", "merge")
        f += not check("exit", rc, 0)
        f += not check("says LIVE", "LIVE  demo-001" in out, True)
        f += not check("marks uses NOT ENFORCED", "NOT ENFORCED" in out, True)

        revoke(seed, scope)

        print("after TEAMLEAD revokes it, the same query is a refusal:")
        rc, out = tool(clone, "--grantee", "DEMO", "--capability", "merge")
        f += not check("exit", rc, 1)
        f += not check("names REVOKED", "REVOKED" in out, True)

        print("★ the attack — name the parent of the revoking commit, no forgery needed:")
        rc, out = tool(clone, "--grantee", "DEMO", "--capability", "merge", "--ref", a)
        f += not check("exit is VOID, not 0", rc, 2)
        f += not check("does NOT report LIVE", "LIVE  demo-001" in out, False)
        f += not check("says why", "--ref is not accepted" in out, True)

        print("the same flag with a LOCAL ref is refused too:")
        rc, out = tool(clone, "--grantee", "DEMO", "--capability", "merge", "--ref", "HEAD")
        f += not check("exit", rc, 2)

        print("★ the diagnostic survives — a listing authorizes nothing:")
        rc, out = tool(clone, "--list", "--ref", a)
        f += not check("exit", rc, 0)
        f += not check("shows the record at that ref", "demo-001" in out or "DEMO" in out, True)

        print("an unreachable remote is VOID, never a refusal:")
        broken = os.path.join(tmp, "gone.git")
        sh(clone, "git", "remote", "set-url", "origin", broken)
        rc, out = tool(clone, "--grantee", "DEMO", "--capability", "merge")
        f += not check("exit", rc, 2)
        f += not check("says established nothing", "established nothing" in out, True)

        print("the self-test still proves every verdict reachable:")
        # ⚠ Needs the real grants/ store, which lives beside the tool IN ITS REPO.
        # When the tool is copied elsewhere — which is exactly what a break test does
        # — that path has no store, and failing here would report a harness
        # portability bug as a defect in the code under test. Measured: it did, once.
        repo_root = os.path.dirname(os.path.dirname(TOOL))
        if os.path.exists(os.path.join(repo_root, "grants", "README.md")):
            rc, out = tool(repo_root, "--self-test")
            f += not check("exit", rc, 0)
        else:
            print("  SKIP  no grants/ store beside this copy of the tool — "
                  "not applicable, and not a failure")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if f:
        print(f"{f} FAILED")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
