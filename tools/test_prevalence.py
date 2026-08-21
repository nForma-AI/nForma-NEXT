#!/usr/bin/env python3
"""Pins that a token present in EVERY record is format, not evidence — and that a
population of one cannot say so.

⛔ The mistake this exists for, made twice four months apart and once by the author
of this file an hour before writing it: a token sitting next to the subject you are
reading, which is a CONSTANT of the line format. `detail=<free text>, attempts=1,
elapsed=247s` — the suffix is on 7 of 7 poll lines, including lines whose `detail=`
is EMPTY — was read as circuit-breaker state and reported to a decision-maker. The
breaker's own message contains neither field.

Run: python3 tools/test_prevalence.py
"""
import contextlib, io, os, sys, tempfile, types

sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
_here = os.path.dirname(os.path.abspath(__file__))


def load(path, name):
    mod = types.ModuleType(name); mod.__file__ = path
    exec(compile(open(path).read(), path, "exec"), mod.__dict__)
    return mod


pv = load(os.path.join(_here, "prevalence.py"), "pv")
fails = []


def check(name, got, want):
    ok = got == want
    print(f"{'✅' if ok else '❌'} {name}")
    if not ok:
        print(f"     got  {got!r}\n     want {want!r}")
        fails.append(name)


def run(path, *extra):
    argv = sys.argv[:]
    sys.argv = ["prevalence.py", path, *extra]
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            rc = pv.main()
    finally:
        sys.argv = argv
    return rc, buf.getvalue()


# ── ⛔ THE REAL ARTIFACT — 7 poll lines captured from a CI log, not typed ─────
REAL = os.path.join(_here, "testdata", "poll-lines-real.txt")
rc, out = run(REAL, "--token", "attempts=", "--like", r"\[POLL #")
check("the suffix is on EVERY real poll line", "7 of 7" in out, True)
check("...so it is NON-DISCRIMINATING", "NON-DISCRIMINATING" in out, True)
check("...named as the FORMAT, not a property of one record",
      "this is the FORMAT" in out, True)
check("...and it tells the reader not to conclude from it",
      "Do NOT record a conclusion" in out, True)
check("...exit 1, never 0", rc, 1)

# ⛔ THE PROOF THAT MAKES IT A FINDING: lines whose `detail=` is EMPTY still carry
# the suffix. A constant that survives an empty subject is unambiguously format.
_lines = open(REAL).read().splitlines()
_empty_detail = [l for l in _lines if "detail=, " in l]
check("real lines exist whose detail= is EMPTY", len(_empty_detail) >= 3, True)
check("...and every one of them still carries the suffix",
      all("attempts=" in l for l in _empty_detail), True)

# ── ✅ KNOWN-NEGATIVE: a token that genuinely varies must DISCRIMINATE ────────
# Without this the checks above would pass against a tool that always says
# NON-DISCRIMINATING.
rc, out = run(REAL, "--token", "status=FAILED", "--like", r"\[POLL #")
check("KNOWN-NEGATIVE: a varying token DISCRIMINATES", "✅ DISCRIMINATES" in out, True)
check("...with its real rate, 1 of 7", "1 of 7" in out, True)
check("...and exits 0", rc, 0)

# ── ⛔ A POPULATION OF ONE ESTABLISHES NOTHING ────────────────────────────────
# With n=1, "every record carries it" and "the only record carries it" are the
# same sentence. A tool that answered would manufacture the confidence it exists
# to remove.
with tempfile.TemporaryDirectory() as tmp:
    def write(name, text):
        p = os.path.join(tmp, name)
        open(p, "w").write(text)
        return p

    one = write("one.txt", "the only line, attempts=1\n")
    rc, out = run(one, "--token", "attempts=")
    check("⛔ n=1 is VOID, not 100%", rc, 2)
    check("...and says why the two readings are the same sentence",
          "the only record carries it" in out, True)
    check("...and does NOT print a percentage", "100%" in out, False)

    # a --like that selects too few must say the SELECTOR is the problem
    many = write("many.txt", "\n".join(f"[POLL #{i}] status=X, attempts={i}" for i in range(5)))
    rc, out = run(many, "--token", "attempts=", "--like", "POLL #3")
    check("⛔ a too-narrow --like is VOID and blames the selector", rc, 2)
    check("...naming the selector that produced it", "selected 1" in out, True)

    # absent from all is equally uninformative — the OTHER half of the same rule
    rc, out = run(many, "--token", "nowhere-token")
    check("a token absent from ALL records is also NON-DISCRIMINATING",
          "NON-DISCRIMINATING" in out, True)
    check("...for the stated reason", "says nothing about any of them" in out, True)
    check("...and exits 1, not 0", rc, 1)

    # ⚠ literal by default — a token lifted from a log is full of metacharacters
    meta = write("meta.txt", "a poll_until(x) here\nb plain\nc poll_until(x) here\n")
    rc, out = run(meta, "--token", "poll_until(x)")
    check("--token is LITERAL: parentheses are not a capture group", "2 of 3" in out, True)
    rc, out = run(meta, "--token", "poll_until(x)", "--token-re")
    check("KNOWN-BAD control: as a REGEX the same token finds NOTHING",
          "0 of 3" in out, True)

    rc, out = run(write("empty.txt", "\n\n  \n"), "--token", "x")
    check("⛔ an empty input is VOID, not 'absent from all'", rc, 2)

rc, out = run(os.path.join(tmp, "gone.txt"), "--token", "x")
check("⛔ an unreadable path is VOID", rc, 2)


# ── ⛔ THE CONTROL MUST BE REACHABLE WITHOUT THE THING UNDER TEST ─────────────
# CI failed this PR for exactly this: the repo's gate-selftests counts a tool whose
# `--self-test` cannot be invoked BARE as UNESTABLISHED — "that is not 'has no
# self-test'; it is a limit of the invocation." `--token` was required=True, so
# argparse rejected `--self-test` alone BEFORE main() ran.
# ★ A control you cannot invoke without supplying the subject is not a control the
# gate can run, and the gate is right to refuse to count it.
import subprocess
_tool = os.path.join(_here, "prevalence.py")
r = subprocess.run([sys.executable, _tool, "--self-test"], capture_output=True, text=True)
check("`--self-test` alone is REACHABLE (exit 0, no argparse error)", r.returncode, 0)
check("...and it actually ran controls", "all checks passed" in r.stdout, True)
check("...including a KNOWN-NEGATIVE, or a always-refusing tool would pass",
      "KNOWN-NEGATIVE" in r.stdout, True)
check("...and it asserts the two verdicts DIFFER — a constant function is vacuous",
      "the function is not constant" in r.stdout, True)

# ⛔ and dropping the subject must still refuse clearly rather than crash
r = subprocess.run([sys.executable, _tool], capture_output=True, text=True)
check("bare, with no args at all: exit 2 and a named reason", r.returncode, 2)
check("...naming BOTH missing things, not just the first",
      "a path and --token" in r.stdout, True)
r = subprocess.run([sys.executable, _tool, REAL], capture_output=True, text=True)
check("a path with no --token also exits 2", r.returncode, 2)

print(f"\n{len(fails)} failure(s)" if fails else "\nall checks passed")
sys.exit(1 if fails else 0)
