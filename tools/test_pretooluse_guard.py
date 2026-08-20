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



# ⛔ HERMETIC CORPUS. This suite used to read the developer's real ~/.claude/projects, so
# its assertions ("names its scope", "warns when unscoped") passed or failed according to
# what this machine happened to hold — and failed on a clean runner, where they were
# classified as "fleet-dependent". They are not: they are assertions about OUTPUT SHAPE,
# and a fixture states the input they were always implicitly assuming.
import importlib.util as _ilu
_fx_spec = _ilu.spec_from_file_location(
    "corpus_fixture", os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "test_corpus_fixture.py"))
_fx = _ilu.module_from_spec(_fx_spec)
_fx_spec.loader.exec_module(_fx)
FIXTURE_ENV = _fx.env()


def run(*args, stdin=""):
    p = subprocess.run([sys.executable, TOOL, *args], input=stdin,
                       capture_output=True, text=True, env=FIXTURE_ENV)
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
