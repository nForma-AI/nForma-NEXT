#!/usr/bin/env python3
"""Pins pipe-exit-scan.py's use/mention discriminators and the population it reports over.

Written from the DOCSTRING. Its stated discriminators, in its own order of strength:

    1. FILE KIND     prose lives in .md; markdown is scanned ONLY inside ```bash/```sh fences
    2. COMMENT STRIP a `#` comment in a shell script is a mention, not a use
    3. SHAPE         the finding is a PIPELINE whose status is read, not the bare identifier

and: "Matched on `tool_use`.`command` ONLY — never assistant prose."

⛔ What this file found. `scan_transcripts` globs `~/.claude/projects/*` — EVERY repository
this machine has worked on — while the docstring above it called that "this fleet's
transcripts" and quoted 32 invocations across 7 of 9 sessions. Re-measured 2026-08-20:

    every project on the machine   1,317 hits   82 sessions   27 project dirs
    this fleet's project dir         251 hits   15 sessions    4 project dirs

The same file also carried a citation of a sibling tool's fire rate — "1.5% fleet-wide
(25 of 1720)" — that the sibling has since retracted for exactly this reason.

★ A rate is not wrong because it is small or large. It is wrong when the set it was taken
over is not the set the sentence names.

Run: python3 tools/test_pipe_exit_scan.py
"""
import importlib.util
import os
import subprocess
import sys
import tempfile

_here = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(_here, "pipe-exit-scan.py")
_spec = importlib.util.spec_from_file_location("pes", TOOL)
pes = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pes)


def hits(line):
    # ⚠ getattr, not a direct call. A version without the segment-aware refinement has
    # no such function, and an AttributeError would abort this suite BEFORE the
    # assertions — producing an empty run that reads exactly like a clean pass. The
    # fallback is the OLD behaviour (regex alone), so the break fails on the assertion
    # instead of crashing. Measured: it crashed first, and the empty output nearly
    # counted as a pass for the third time tonight.
    refine = getattr(pes, "pipeline_status_read", lambda _l: True)
    code = pes.strip_comment(line)
    return bool((pes.AFTER_PIPE.search(code) and refine(code))
                or pes.PIPESTATUS.search(code))


import importlib.util as _ilu
_fx_spec = _ilu.spec_from_file_location(
    "corpus_fixture", os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "test_corpus_fixture.py"))
_fx = _ilu.module_from_spec(_fx_spec)
_fx_spec.loader.exec_module(_fx)
FIXTURE_ENV = _fx.env()


def run(*args):
    # ⚠ cwd is the REPO ROOT, not tools/. The tool resolves `git ls-files` paths and
    # its own fixture relative to the root; running it from tools/ made the self-test
    # exit 2 and read as a defect. Harness, not code — the second time in this suite
    # family that a portability bug in the test presented as a finding.
    # ⛔ AND a fixture HOME, for the same reason as the cwd note above: the "warns when
    # unscoped" assertion needs a corpus spanning two project dirs, and reading the
    # developer's real one made this suite pass here and fail on a clean runner.
    p = subprocess.run([sys.executable, TOOL, *args], capture_output=True, text=True,
                       cwd=os.path.dirname(_here), env=FIXTURE_ENV)
    return p.returncode, p.stdout + p.stderr


def check(name, got, want):
    ok = got == want
    print(("  PASS  " if ok else "  FAIL  ") + f"{name}: got {got!r}, want {want!r}")
    return ok


def main():
    f = 0

    print("SHAPE — a pipeline whose status is read:")
    f += not check("classic", hits('python3 v.py | tail -6; echo "exit=$?"'), True)
    f += not check("PIPESTATUS", hits('cmd | grep x; echo "${PIPESTATUS[0]}"'), True)

    print("★ the CORRECT idiom must stay silent — firing on it is the worst outcome:")
    f += not check("re-run redirected",
                   hits('python3 t.py | tail -4; python3 t.py >/dev/null 2>&1; echo $?'), False)
    f += not check("bare $? with no pipe", hits('python3 t.py; echo "exit=$?"'), False)
    f += not check("bare identifier alone", hits('PIPESTATUS is a bash builtin'), False)

    print("COMMENT STRIP — a mention inside a script is not a use:")
    f += not check("commented out", hits('# python3 v.py | tail -6; echo "exit=$?"'), False)
    f += not check("trailing comment prose",
                   hits('ls   # never write: cmd | tail; echo $?'), False)

    print("★ FILE KIND — the known-negative is the file that documents the trap:")
    rc, out = run()          # scan tracked files of this repo
    f += not check("no finding in tools/README.md", "README.md" in out, False)

    print("the self-test proves its own known-positive fires:")
    rc, out = run("--self-test")
    f += not check("exit", rc, 0)
    f += not check("says PASS", "selftest PASS" in out, True)

    print("★ --transcripts must PRINT the population it measured:")
    rc, out = run("--transcripts")
    f += not check("names its scope", "scope " in out, True)
    f += not check("counts project dirs", "project dirs with hits" in out, True)
    f += not check("names the largest contributor", "largest contributor" in out, True)
    f += not check("warns when unscoped", "UNSCOPED" in out, True)

    print("--project scopes it; a scope matching nothing is exit 2, not a clean scan:")
    rc, out = run("--transcripts", "--project", "zzz-no-such-project-zzz")
    f += not check("exit", rc, 2)
    f += not check("says established nothing", "ESTABLISHED NOTHING" in out, True)
    rc, out = run("--transcripts", "--project")
    f += not check("--project with no value exits 2", rc, 2)

    print("★ the docstring must not emit a SyntaxWarning — it contains \\$?:")
    p = subprocess.run([sys.executable, "-W", "error::SyntaxWarning", "-c",
                        f"import importlib.util;s=importlib.util.spec_from_file_location('x',{TOOL!r});"
                        f"m=importlib.util.module_from_spec(s);s.loader.exec_module(m)"],
                       capture_output=True, text=True)
    f += not check("imports cleanly", p.returncode, 0)

    print("the retracted sibling citation is not quoted as live:")
    rc, out = run("--transcripts", "--project", "code-DigitalFrontier-infra")
    f += not check("1.5% is marked retracted",
                   ("1.5%" not in out) or ("RETRACTED" in out), True)

    print()
    if f:
        print(f"{f} FAILED")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
