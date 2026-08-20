#!/usr/bin/env python3
"""Pins wake-yield.py's classifier against its own docstring.

Written from the DOCSTRING. It promises to count as mutating:

    Write · Edit · NotebookEdit · a Bash call that commits, pushes,
    or creates an issue/PR/comment

⛔ Measured on a two-hour window whose contents were known by construction:
**28 counted, 16 distinct forge-write blocks missed — a 36% undercount.** The misses were
`gh pr merge` (8) and `gh api graphql` mutations (7 — posting review replies and resolving
threads). Both are squarely inside what the docstring promises.

⚠ The bias had a sign: an agent using the REST porcelain scored WORK, one doing the same
work through graphql or `pr merge` scored churn. The instrument was rewarding a calling
convention, not an action — and "churn" is the verdict it exists to make trustworthy.

The second half of the repair is the UNCLASSIFIED bucket. A shell mutates in unbounded
ways, so an enumerated list cannot be complete; folding what it misses into "reads"
manufactures the churn verdict. What the classifier cannot see is now counted and shown.

Run: python3 tools/test_wake_yield.py
"""
import importlib.util
import json
import os
import subprocess
import sys

# ⛔ A STALE __pycache__ SILENTLY SERVES THE PRE-MUTATION MODULE. Measured with a
# 4-cell table: {clean,mutant} x {cache cleared,stale} -> the mutant PASSED on a stale
# cache and failed 3 checks once cleared. Every suite here loads its tool through
# spec_from_file_location, so a false SURVIVED sends you rewriting a correct test.
# CI is safe (fresh checkout, no cache); local mutation testing was not.
sys.dont_write_bytecode = True
# ⚠ and the env var too: a SUBPROCESS does not inherit sys.dont_write_bytecode,
# which is why three suites still produced a cache after the first fix.
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

_here = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("wake_yield", os.path.join(_here, "wake-yield.py"))
wake_yield = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(wake_yield)


def bash(command):
    return wake_yield.classify("Bash", json.dumps({"command": command}), command)


def check(name, got, want):
    ok = got == want
    print(("  PASS  " if ok else "  FAIL  ") + f"{name}: got {got!r}, want {want!r}")
    return ok


def main():
    f = 0

    print("★ the measured misses — forge writes that scored as churn:")
    f += not check("gh pr merge", bash("gh pr merge 200 --repo o/r --squash"), "mutating")
    f += not check("graphql mutation", bash(
        "gh api graphql -f query='mutation($t:ID!){resolveReviewThread(input:{threadId:$t}){thread{isResolved}}}'"),
        "mutating")

    print("a graphql QUERY is not a mutation — the fix must not over-fire:")
    f += not check("graphql query", bash(
        "gh api graphql -f query='{repository(owner:\"o\",name:\"r\"){pullRequest(number:1){title}}}'"),
        "read")

    print("★ --method is the long form of -X, and was not matched:")
    f += not check("--method POST", bash(
        "gh api repos/o/r/issues/1/comments --method POST -f body=hi"), "mutating")

    print("the forms it already counted still count:")
    for cmd in ("git commit -q -m x", "git push -u origin br",
                "gh issue comment 5 --body hi", "gh pr create --title t --body b"):
        f += not check(cmd.split()[1], bash(cmd), "mutating")

    print("tools, not shells:")
    f += not check("Write", wake_yield.classify("Write", "{}", None), "mutating")
    f += not check("Read", wake_yield.classify("Read", "{}", None), "read")

    print("★ compound commands — anchoring at the string start matched almost nothing:")
    # A real command begins with `cd`. Classifying the whole string against an
    # anchored pattern pushed 1,032 of 1,244 actions into UNCLASSIFIED.
    f += not check("cd && view | jq", bash(
        "cd /tmp && gh pr view 200 --json state --jq .state"), "read")
    f += not check("cd && merge", bash("cd /tmp && gh pr merge 200 --squash"), "mutating")
    f += not check("read then mutate", bash("git status && git commit -m x"), "mutating")

    print("★ what it cannot see is UNCLASSIFIED, not a read:")
    f += not check("heredoc python", bash("python3 - <<'PY'\nopen('f','w').write('x')\nPY"),
                   "unclassified")
    f += not check("sed -i", bash("sed -i '' s/a/b/ file.txt"), "unclassified")
    f += not check("redirect", bash("cat > out.txt <<'EOF'\nhi\nEOF"), "unclassified")

    print("the future-window guard still refuses:")
    p = subprocess.run([sys.executable, os.path.join(_here, "wake-yield.py"),
                        "--since", "2099-01-01T00:00:00Z"], capture_output=True, text=True)
    f += not check("exit nonzero", p.returncode != 0, True)
    f += not check("says FUTURE", "FUTURE" in (p.stdout + p.stderr), True)

    print()
    if f:
        print(f"{f} FAILED")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
