#!/usr/bin/env python3
"""Pins that a refusal never reaches a grep — because a grep over one reads as clean.

⛔ The measured near-miss this exists for: five job logs fetched in a loop while the
REST pool drained mid-loop. Every body was a 535-byte 403 JSON. The extraction
reported `unreach=0` and `<no provider>` for ALL FIVE — a clean sweep produced
entirely by refusals. The successful fetch of the same job was 46,922 bytes.

★ A refusal is TEXT. Every grep over it returns zero, and zero matches reads as
"the signature is absent" rather than "there is no log here".

Run: python3 tools/test_job_log.py
"""
import os, sys, types

sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
_here = os.path.dirname(os.path.abspath(__file__))


def load(path, name):
    mod = types.ModuleType(name); mod.__file__ = path
    with open(path) as fh:
        src = fh.read()
    exec(compile(src, path, "exec"), mod.__dict__)
    return mod


jl = load(os.path.join(_here, "job-log.py"), "jl")
NE = jl.NotEstablished
fails = []


def check(name, got, want):
    ok = got == want
    print(f"{'✅' if ok else '❌'} {name}")
    if not ok:
        print(f"     got  {got!r}\n     want {want!r}")
        fails.append(name)


REAL = ("2026-08-20T23:25:21.3914563Z [FAIL] Workload tetris UNREACHABLE after 29 attempts\n"
        "2026-08-20T23:26:45.0924793Z [INFO] RESULT: FAILED in 951s\n")
# ⛔ THE REAL ARTIFACT, not a hand-typed approximation of one. This is the body
# that produced the five-for-five clean sweep, captured from the wire and redacted
# only for account and request identifiers. A synthetic 403 tests the synthetic
# 403 — this repository has already shipped that mistake once, in a fixture whose
# missing timestamp prefix made the matcher pass on nothing.
with open(os.path.join(_here, "testdata", "rest-403-body.txt")) as _fh:
    R403 = _fh.read()

check("a real log is returned as text", isinstance(jl.witnessed(REAL), str), True)
check("a 403 JSON body is REFUSED", isinstance(jl.witnessed(R403), NE), True)
check("...and it names what it saw", "JSON error" in str(jl.witnessed(R403)), True)
check("an empty body is refused", isinstance(jl.witnessed(""), NE), True)
check("whitespace-only is refused too", isinstance(jl.witnessed("   \n "), NE), True)
check("a None body is refused", isinstance(jl.witnessed(None), NE), True)
check("an HTML error page is refused — no timestamp",
      isinstance(jl.witnessed("<html><body>502 Bad Gateway</body></html>"), NE), True)
check("prose with no timestamp is refused",
      isinstance(jl.witnessed("could not read the log"), NE), True)

# ⛔ THE KNOWN-BAD CONTROL: the whole reason this file exists.
# Grepping the refusal returns 0 for the signature — identical to a clean log.
import re
check("KNOWN-BAD control: the signature count over a 403 body is 0",
      len(re.findall("UNREACHABLE", R403)), 0)
check("...and over the real log it is 1 — the SAME grep, opposite meaning",
      len(re.findall("UNREACHABLE", REAL)), 1)
check("⇒ so the refusal must never reach the grep: it is not a str",
      isinstance(jl.witnessed(R403), str), False)

# ⚠ size is deliberately NOT a witness — a short real log must still pass
check("⚠ a SHORT but real log is accepted — length is not the witness",
      isinstance(jl.witnessed("2026-08-20T23:00:00.0Z done\n"), str), True)

# ── ⛔ KNOWN-BAD CONTROL over the REAL captured refusal ───────────────────────
check("the real 403 body is REFUSED", isinstance(jl.witnessed(R403), NE), True)
check("...and it is genuinely the size that fooled the loop (500-600B)",
      500 <= len(R403) <= 600, True)
check("...and it contains ZERO timestamped lines — the witness that catches it",
      len(jl.LOG_LINE.findall(R403)), 0)
for pat in ("UNREACHABLE", "ingress", "akash1", "RESULT: FAILED"):
    check(f"KNOWN-BAD control: the real refusal greps clean for {pat!r}",
          len(re.findall(pat, R403)), 0)

# ⚠ NOT COVERED BY A REAL SPECIMEN: the 99-byte escape-sequence refusal returned
# when --allow-escape-sequences is omitted. A peer measured it; I have not
# captured one, and writing a synthetic stand-in would test the stand-in. The
# format witness would catch it for the same reason it catches this body — no
# timestamped line — but that is REASONING, not a measurement, and it is recorded
# here as an open gap rather than a passing check.
print("⚠ NOT RUN: the 99-byte escape-sequence refusal — no real specimen captured yet")

print(f"\n{len(fails)} failure(s)" if fails else "\nall checks passed")
sys.exit(1 if fails else 0)
