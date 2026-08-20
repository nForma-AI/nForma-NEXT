#!/usr/bin/env python3
"""Pins pretooluse-guard.py's matcher and the population its rate is taken over.

Written from the DOCSTRING. Its stated contract:

    Exit: 0 clean · 1 would warn · 2 established nothing.
    heredoc BODIES are stripped — a command writing documentation ABOUT the idiom
    was the dominant false positive
    `$?` after a pipe is LOST; the re-run idiom (`cmd | look; cmd > /dev/null; echo $?`)
    is CORRECT and must stay silent
    LOST vs INVERTED is the severity split

⛔ And the finding that produced this file. The docstring corrected a rate that had been
quoted without its denominator ("2.5% was ONE ROLE'S SESSION") — and its replacement,
labelled "the fleet", was mis-denominated in the other direction. `--measure` scanned
EVERY project directory on the machine. Measured 2026-08-20: 50 project dirs, 179,216
commands, of which the fleet's own directory held **14.3%** and the largest single
contributor was an unrelated project at **19.6%**.

⚠ The cited corpus of 1,720 does not reproduce. A number a docstring attributes to its
own tool, which the tool no longer produces, is the exact thing this file was committed
to prevent.

Run: python3 tools/test_pretooluse_guard.py
"""
import importlib.util
import os
import subprocess
import sys

_here = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(_here, "pretooluse-guard.py")
_spec = importlib.util.spec_from_file_location("guard", TOOL)
guard = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(guard)


def names(cmd):
    return sorted(n for n, _ in guard.check(cmd))


def sevs(cmd):
    return sorted(s for _, s in guard.check(cmd))


def run(*args, stdin=""):
    p = subprocess.run([sys.executable, TOOL, *args], input=stdin,
                       capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def check(name, got, want):
    ok = got == want
    print(("  PASS  " if ok else "  FAIL  ") + f"{name}: got {got!r}, want {want!r}")
    return ok


def main():
    f = 0

    print("the founding incident fires:")
    f += not check("pipe then $?", names('python3 v.py 2>&1 | tail -6; echo "exit=$?"'),
                   ["exit-after-pipe"])

    print("★ the CORRECT re-run idiom must stay silent — firing on it is the worst case:")
    f += not check("re-run redirected", guard.check(
        'python3 t.py 2>&1 | tail -4; python3 t.py >/dev/null 2>&1; echo "exit=$?"'), [])

    print("severities are split:")
    f += not check("PIPESTATUS is LOST", sevs('echo "${PIPESTATUS[0]}"'), ["LOST"])
    f += not check("zsh var modifier is INVERTED", sevs('git show $P:tools/README.md'),
                   ["INVERTED"])
    f += not check("a plain colon is not the defect", guard.check('echo $HOME:/bin'), [])

    print("★ ground truth from zsh — the rule must follow the shell, not the other way:")
    # Verified by running each through zsh. The first two are silently corrupted;
    # the second two are the deliberate modifier and must not be interrupted.
    f += not check("$P:tools/... is MANGLED -> fires",
                   bool(guard.check('git show $P:tools/README.md')), True)
    f += not check("$IMAGE:tag is MANGLED -> fires",
                   bool(guard.check('docker run $IMAGE:tag')), True)
    f += not check("$file:t is INTENDED -> silent", guard.check('echo $file:t'), [])
    f += not check("$V:h/sub is INTENDED -> silent", guard.check('echo $V:h/sub'), [])
    f += not check("braces prevent it -> silent", guard.check('echo ${P}:tools/x'), [])

    print("★ heredoc bodies are content, not code:")
    f += not check("doc about the idiom", guard.check(
        "cat > d.md <<'EOF'\nnever use ${PIPESTATUS[0]} here\nEOF"), [])
    f += not check("...but the shell around it still counts", bool(guard.check(
        "cat > d.md <<'EOF'\nharmless prose\nEOF\necho \"${PIPESTATUS[0]}\"")), True)

    print("exit contract, over stdin:")
    rc, _ = run(stdin='python3 v.py | tail -1; echo $?')
    f += not check("a hit exits 1", rc, 1)
    rc, _ = run(stdin="ls -la")
    f += not check("clean exits 0", rc, 0)

    print("★ --measure must PRINT the population it measured:")
    rc, out = run("--measure")
    f += not check("names its scope", "scope" in out, True)
    f += not check("prints project dir count", "project dirs included" in out, True)
    f += not check("warns when unscoped", "UNSCOPED" in out, True)
    f += not check("names the largest contributor", "largest single contributor" in out, True)

    print("--project scopes it, and a scope that matches nothing is exit 2:")
    rc, out = run("--measure", "--project", "code-DigitalFrontier-infra")
    f += not check("scoped run does not warn UNSCOPED", "UNSCOPED" in out, False)
    rc, out = run("--measure", "--project", "zzz-no-such-project-zzz")
    f += not check("empty scope exit", rc, 2)
    f += not check("says established nothing", "ESTABLISHED NOTHING" in out, True)
    rc, out = run("--measure", "--project")
    f += not check("--project with no value exits 2", rc, 2)

    # ── converted rules: the NEGATIVE direction is the one that matters ──────────
    # Every rule here fires on a defect three agents paid for. The risk a new rule
    # adds is the opposite one — interrupting correct work — and this file already
    # shipped a rule (`zsh-var-modifier`) that fired ONLY on correct usage while its
    # zero hit-count was read as "the defect is rare".
    print("converted rules, both directions:")
    for rule, pos, neg in [
        ("two-dot-diff", "git diff main..HEAD", "git diff main...HEAD"),
        ("gh-logs-no-escape",
         "gh api repos/o/r/actions/jobs/1/logs > x.log",
         "gh api --allow-escape-sequences repos/o/r/actions/jobs/1/logs > x.log"),
        ("unquoted-glob-arg", "grep -rn x --include=*.py .", "grep -rn x --include='*.py' ."),
        ("zsh-for-unsplit", "for b in $BR; do :; done", 'for b in "${BR[@]}"; do :; done'),
        ("git-grep-word-boundary", r"git grep -E '\bfoo\b'", "git grep -E 'foo'"),
        ("git-archive-tree", "git archive HEAD | tar -x -C /tmp/i", "git worktree add /tmp/i HEAD"),
    ]:
        f += not check(f"{rule} fires", rule in names(pos), True)
        f += not check(f"{rule} silent on the correct form", rule in names(neg), False)

    # ⛔ The exact near-miss that shipped and was caught by the negative above: `.` was
    # inside the left character class, so the pattern matched from the FIRST dot of
    # `...` and the (?!\.) lookahead never saw a dot. Pinned with the awkward forms
    # too, because a path containing dots is where it would come back.
    f += not check("three-dot with a dotted path stays silent",
                   "two-dot-diff" in names("git diff a.b...c.d -- x/y.py"), False)
    f += not check("two-dot with a dotted path still fires",
                   "two-dot-diff" in names("git diff a.b..c.d -- x/y.py"), True)

    # ── the guard's standing, which is separate from whether its rules discriminate ──
    print("enforcement self-check:")
    rc, out = run("--enforcement")
    f += not check("reports a definite standing", rc in (0, 1), True)
    # ⛔ THIS ASSERTION PASSED FOR THE WRONG REASON AND A MUTATION EXPOSED IT.
    # It read `... or "WIRED —" in out`, and the unwired banner says "NOT WIRED — ",
    # which CONTAINS that substring. So the wired-branch clause was satisfied by the
    # negation, and gutting the consequence sentence left the test green.
    # ⇒ Discriminate on a token that cannot appear inside the other state's text.
    # This is ARCHITECT's #1269 §3 corollary — the matcher finds its token inside the
    # prose about the token — committed in the test for the guard that catches it.
    wired = out.startswith("✓ WIRED")
    unwired = out.startswith("⛔ NOT WIRED")
    f += not check("banner picks exactly one state", wired ^ unwired, True)
    f += not check("names the consequence, not just the state",
                   "evidence that the guard ran" in out if wired
                   else "evidence of nothing" in out, True)
    f += not check("refuses to wire itself",
                   True if wired else "operator decision" in out, True)
    rc, out = run("--self-test")
    f += not check("self-test states standing BEFORE passing", "WIRED" in out, True)

    print("the self-test still passes:")
    rc, out = run("--self-test")
    f += not check("exit", rc, 0)
    f += not check("says PASS", "selftest PASS" in out, True)

    print()
    if f:
        print(f"{f} FAILED")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
