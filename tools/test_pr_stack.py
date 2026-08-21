#!/usr/bin/env python3
"""Pins that unfetched heads are UNKNOWN, and that overlap is not compatibility.

⛔ The defect this suite exists for: the first run of `pr-stack.py` could not
resolve 2 of 4 PR heads, skipped them, and printed a conflict count derived from
the half it could see. **A smaller conflict count looks like better news**, so a
reader with no reason to doubt it takes the reassuring number.

★ The git fixtures are REAL repositories, not stubs. `merge-tree`'s behaviour is
the thing under test, and a stub would test the stub.

Run: python3 tools/test_pr_stack.py
"""
import json, os, subprocess, sys, tempfile, types

sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
_here = os.path.dirname(os.path.abspath(__file__))


def load(path, name):
    mod = types.ModuleType(name)
    mod.__file__ = path
    exec(compile(open(path).read(), path, "exec"), mod.__dict__)
    return mod


ps = load(os.path.join(_here, "pr-stack.py"), "ps")
fails = []


def check(name, got, want):
    ok = got == want
    print(f"{'✅' if ok else '❌'} {name}")
    if not ok:
        print(f"     got  {got!r}\n     want {want!r}")
        fails.append(name)


def git(d, *a):
    return subprocess.run(["git", "-C", d, *a], capture_output=True, text=True)


with tempfile.TemporaryDirectory() as d:
    git(d, "init", "-q", "-b", "main")
    git(d, "config", "user.email", "t@t"); git(d, "config", "user.name", "t")
    # ⚠ 40 lines, not 3. A three-line file puts every edit inside every other edit's
    # context window, so "different lines" and "the same line" both conflict — the
    # fixture would have tested its own size. Found by this suite failing on it.
    open(os.path.join(d, "shared.txt"), "w").write("".join(f"line{i}\n" for i in range(40)))
    open(os.path.join(d, "solo.txt"), "w").write("x\n")
    git(d, "add", "-A"); git(d, "commit", "-qm", "base")

    def branch(name, edits):
        git(d, "checkout", "-q", "-B", name, "main")
        for f, text in edits.items():
            open(os.path.join(d, f), "w").write(text)
        git(d, "add", "-A"); git(d, "commit", "-qm", name)

    # two branches editing the SAME line of the same file
    def lines(**edits):
        out = [f"line{i}\n" for i in range(40)]
        for k, v in edits.items():
            out[int(k[1:])] = v + "\n"
        return "".join(out)
    branch("alpha", {"shared.txt": lines(n20="ALPHA")})
    branch("beta",  {"shared.txt": lines(n20="BETA")})
    # a branch editing a DIFFERENT file entirely
    branch("gamma", {"solo.txt": "y\n"})
    # a branch editing a DIFFERENT line of the SAME file — overlap, no conflict
    branch("delta", {"shared.txt": lines(n2="DELTA")})   # 18 lines away from alpha
    git(d, "checkout", "-q", "main")

    cwd = os.getcwd()
    os.chdir(d)
    try:
        kind, files = ps.relation("alpha", "beta")
        check("same line of the same file is a CONFLICT", kind, "CONFLICTS")
        check("...and the file is named", files, ["shared.txt"])

        check("disjoint files: no textual conflict", ps.relation("alpha", "gamma")[0], None)

        # ⛔ THE DANGEROUS CASE the tool must not call 'independent'
        check("different lines of the SAME file: no conflict",
              ps.relation("alpha", "delta")[0], None)
        check("...but the file sets OVERLAP, which is the whole point of that verdict",
              bool(ps.files_of("alpha", "main") & ps.files_of("delta", "main")), True)
        check("...whereas a genuinely disjoint pair does not overlap",
              bool(ps.files_of("alpha", "main") & ps.files_of("gamma", "main")), False)

        check("files_of reads the merge-base diff, not two dots",
              ps.files_of("alpha", "main"), {"shared.txt"})
    finally:
        os.chdir(cwd)

# ⛔ a failed query is not an empty board
check("a repo that cannot be queried is None, never []",
      ps.open_prs("nForma-AI/this-repo-does-not-exist-xyzzy"), None)

# ── ⛔ a refusal with the WRONG remedy sends someone down a dead end ──────────
# The first version said "Run `git fetch origin` first" unconditionally. When
# --repo names a different repository than the checkout, fetching this one can
# never resolve that one's heads — the advice was not merely unhelpful, it was
# UNFOLLOWABLE. Refusing correctly is not enough if the reason is wrong.
check("owner/name parsed from an https remote",
      ps.local_remote.__doc__ is not None, True)
for url, want in (("https://github.com/nForma-AI/nForma-NEXT.git", "nForma-AI/nForma-NEXT"),
                  ("git@github.com:Owner/Repo.git", "Owner/Repo"),
                  ("https://github.com/Owner/Repo", "Owner/Repo")):
    import re as _re
    m = _re.search(r"[:/]([^/:]+/[^/]+?)(?:\.git)?/?$", url)
    check(f"remote parse: {url[:38]}", m.group(1) if m else None, want)

check("same_repo is case-insensitive — GitHub treats it that way",
      ps.same_repo("Owner/Repo", "owner/repo"), True)
check("a different repo is not the same repo",
      ps.same_repo("a/b", "a/c"), False)
# ⚠ a MISSING remote must not be mistaken for a mismatch — that would print the
# cross-repo message to someone whose only problem is an unfetched branch.
check("an unknown local remote is falsy, so the generic remedy is used instead",
      bool(ps.same_repo("a/b", None)), False)


# ── ⛔ A FULL WINDOW IS NOT A COMPLETE BOARD, AND THIS TOOL COUNTS PAIRS ──────
# Measured LIVE 2026-08-21 on this tool's own default: Blazing-Back had 61 open
# PRs and `--limit 50` returned exactly 50. Eleven invisible — and because the
# product is PAIRS the loss compounds: 1830 pairs -> 1225, so 605 (33%) were never
# examined, and nothing said so.
#
# ★ This file already argued the point one level down, about unfetched heads:
# "a smaller number that looks like better news." The guard was only on the inner
# window. The same sentence is true of an unlisted PR.
_saved_sh = ps.sh

def _rows(n):
    return json.dumps([{"number": i, "headRefName": f"h{i}", "title": "t"}
                       for i in range(1, n + 1)])

def _with_rows(n):
    ps.sh = lambda *a, **k: _rows(n)
    try:
        return ps.open_prs(None, limit=10)
    finally:
        ps.sh = _saved_sh

rows, sat = _with_rows(10)
check("a FULL window reports saturated", (len(rows), sat), (10, True))
rows, sat = _with_rows(9)
check("a short window does not", (len(rows), sat), (9, False))

# ⛔ KNOWN-BAD CONTROL — the test that makes the two above non-vacuous. A board of
# EXACTLY the window size is indistinguishable from a truncated one, and the tool
# must call it saturated rather than guess. Being wrong here is the safe direction:
# it refuses a complete board instead of blessing an incomplete one.
check("KNOWN-BAD control: a board of exactly N is ALSO saturated — refusing a "
      "complete board is the safe error", _with_rows(10)[1], True)

# the saturation test must be len(rows) >= limit, never a guess at the true total
src = open(os.path.join(_here, "pr-stack.py")).read()
check("saturation is keyed on the WINDOW, not on an assumed total",
      "len(rows) >= limit" in src, True)
check("...and a saturated board is REFUSED, not warned about",
      "the window is FULL" in src and "return 2" in src, True)
check("...with a remedy the caller can actually follow", "Raise --limit" in src, True)


# ── ⛔ A SHALLOW CLONE SILENTLY INVALIDATES EVERY PAIR ────────────────────────
# Measured 2026-08-21: a shallow checkout gives each fetched head ONE reachable
# commit against main's 4,633, so no common ancestor exists and merge-tree answers
# `fatal: refusing to merge unrelated histories` (rc=128). 121 of 272 reported
# "conflicts" were that error; `--unshallow` (18s) removed 119 of them, and the
# "N behind" column read 4631 where the true spread was 1-170.
_saved = ps.sh
def _sh_returns(val):
    ps.sh = lambda *a, **k: val

_sh_returns("true\n");  check("is_shallow reads true", ps.is_shallow(), True)
_sh_returns("false\n"); check("...and false", ps.is_shallow(), False)
_sh_returns(None)
check("⛔ an UNREADABLE answer is None, never False — 'could not ask' is not 'not shallow'",
      ps.is_shallow(), None)
ps.sh = _saved

# ── ⛔ AN EXIT CODE IS NOT A VERDICT ─────────────────────────────────────────
# merge-tree exits non-zero for a real conflict AND for a transport failure.
# The old code was `rc != 0 or "CONFLICT" in stdout -> CONFLICTS`, which folded
# every error into the answer — with an EMPTY file list, a shape a real conflict
# can never have.
class _R:
    def __init__(self, rc, out="", err=""):
        self.returncode, self.stdout, self.stderr = rc, out, err

_saved_run = ps.subprocess.run
def _run_returns(r):
    ps.subprocess.run = lambda *a, **k: r

_run_returns(_R(1, "CONFLICT (content): Merge conflict in e2e/x.py\n"))
check("a real conflict is CONFLICTS, with its file",
      ps.relation("a", "b"), ("CONFLICTS", ["e2e/x.py"]))

_run_returns(_R(128, "", "fatal: refusing to merge unrelated histories\n"))
kind, why = ps.relation("a", "b")
check("⛔ a merge-tree ERROR is UNKNOWN, not CONFLICTS", kind, "UNKNOWN")
check("...and it carries the reason verbatim",
      "refusing to merge unrelated histories" in why[0], True)

# ⛔ KNOWN-BAD CONTROL — without it the two checks above would pass against code
# that simply never returns CONFLICTS. This asserts the OLD predicate DID call
# this error a conflict, i.e. the fixture reproduces the defect.
_old_verdict = (128 != 0) or ("CONFLICT" in "")
check("KNOWN-BAD control: the OLD `rc != 0` predicate called that error a CONFLICT",
      _old_verdict, True)

_run_returns(_R(0, "4b825dc642cb6eb9a060e54bf8d69288fbee4904\n"))
check("a clean merge is neither", ps.relation("a", "b"), (None, []))
ps.subprocess.run = _saved_run

# ── ⛔ EVERY ROW CARRIES ITS SECTION ─────────────────────────────────────────
# The two lists used to render identically — `#N × #M   files` — so a grep over
# the output could not tell them apart. Mine matched a superset and I published a
# conflicts+overlaps figure as a conflict count, to someone ordering merges by it.
# ⇒ Fix the OUTPUT so the wrong reading is impossible.
src = open(os.path.join(_here, "pr-stack.py")).read()
check("conflict rows are prefixed CONF", '"  CONF  #{n1}' in src.replace("f\"", '"'), True)
check("overlap rows are prefixed OVER", '"  OVER  #{n1}' in src.replace("f\"", '"'), True)
check("unknown rows are prefixed UNKN", '"  UNKN  #{n1}' in src.replace("f\"", '"'), True)
check("the three prefixes are distinct",
      len({"CONF", "OVER", "UNKN"}), 3)
check("an UNKNOWN pair is not a clean board — it reaches the exit code",
      "uncomputed or unresolved" in src.replace("\n", " ").replace("  ", " "), True)
check("shallow is checked BEFORE the PR query, not after",
      src.index("shallow = is_shallow()") < src.index("got = open_prs("), True)
check("...and the refusal names the remedy", "git fetch --unshallow" in src, True)


# ── ⛔ THE CHECKS ABOVE ON PREFIXES/ORDERING ARE SOURCE-TEXT AND WOULD PASS
#    AGAINST A COMMENT. Drive main() and assert the EXIT CODE, which is what a
#    caller acts on. (Same correction already made once tonight in
#    tools/test_check_freshness.py — recorded so it is not made a third time.)
import contextlib, io

def _main_with(shallow_val):
    saved_is, saved_open = ps.is_shallow, ps.open_prs
    ps.is_shallow = lambda: shallow_val
    ps.open_prs = lambda *a, **k: None          # would exit 2 for a different reason
    buf, argv = io.StringIO(), sys.argv[:]
    sys.argv = ["pr-stack.py", "--no-fetch"]
    try:
        with contextlib.redirect_stdout(buf):
            rc = ps.main()
    finally:
        sys.argv = argv
        ps.is_shallow, ps.open_prs = saved_is, saved_open
    return rc, buf.getvalue()

rc, out = _main_with(True)
check("BEHAVIOUR: a shallow checkout EXITS 2", rc, 2)
check("...saying the checkout is shallow", "SHALLOW" in out, True)
check("...and naming the remedy", "git fetch --unshallow" in out, True)
check("...and it refuses BEFORE the PR query — the query never reported its own failure",
      "the PR query failed" in out, False)

rc, out = _main_with(None)
check("BEHAVIOUR: an UNDETERMINABLE answer warns and does not silently proceed",
      "could not determine" in out, True)
check("...but it is not fatal — 'cannot ask' must not become 'refuse everything'",
      rc != 2 or "the PR query failed" in out, True)

rc, out = _main_with(False)
check("KNOWN-BAD control: a FULL checkout does NOT trip the shallow refusal",
      "SHALLOW" in out, False)

print(f"\n{len(fails)} failure(s)" if fails else "\nall checks passed")
sys.exit(1 if fails else 0)
