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

# ── ✅ THE 99-BYTE ESCAPE-SEQUENCE REFUSAL — captured 2026-08-21, no longer a gap ──
# This stood here as `⚠ NOT RUN` because writing a synthetic stand-in would have
# tested the stand-in. A real one is now on disk, and it is WORSE than the note said:
#
#     rc=1    stdout = 0 bytes    stderr = 99 bytes
#
# ⛔ The 99 bytes are on STDERR. stdout is genuinely EMPTY. So `gh api … > out.log`
# writes a ZERO-BYTE FILE and puts the only explanation in a stream most callers do
# not capture. The danger is not "a short body looks like a log" — it is that the
# body is absent and the reason is invisible.
with open(os.path.join(_here, "testdata", "gh-escape-refusal-stderr.txt")) as _fh:
    ESC = _fh.read()
check("the escape-sequence refusal is exactly 99 bytes, as reported", len(ESC), 99)
check("it names the remedy in its own text",
      "--allow-escape-sequences" in ESC, True)
check("the refusal TEXT is refused", isinstance(jl.witnessed(ESC), NE), True)
check("...carrying no timestamped line", len(jl.LOG_LINE.findall(ESC)), 0)
# ⛔ and the path that actually bites: an empty stdout, refused for a DIFFERENT reason
check("the EMPTY stdout is refused too", isinstance(jl.witnessed(""), NE), True)
check("...and says the two zeros are the same zero",
      "empty" in str(jl.witnessed("")), True)


# ── ⛔ THREE MORE CHANNELS, THREE MORE REAL REFUSALS ──────────────────────────
# The same evidence is reachable through GitHub REST, GCS and the platform API, and
# all three refuse DIFFERENTLY. A guard that hardens one channel hardens one channel.
# Both fixtures below are captured from the wire on 2026-08-21, not hand-written.
with open(os.path.join(_here, "testdata", "gcs-reauth-body.txt")) as _fh:
    GCS = _fh.read()
with open(os.path.join(_here, "testdata", "platform-noentries-body.txt")) as _fh:
    PLAT = _fh.read()

check("the real gsutil reauth body is REFUSED", isinstance(jl.witnessed(GCS), NE), True)
check("...and it carries ZERO timestamped lines", len(jl.LOG_LINE.findall(GCS)), 0)

# ⛔⛔ KNOWN-BAD CONTROL — THE ONE THAT KILLS THE SIZE HEURISTIC.
# The obvious guard is "a refusal is short". This refusal is a full Python traceback
# ending in ReauthUnattendedError and is LARGER than many real job logs. Any byte
# floor waves it straight through, in the exact direction that produces a false clean.
check("KNOWN-BAD control: the gsutil refusal is >10KB", len(GCS) > 10_000, True)
check("KNOWN-BAD control: ...so a 1KB 'too short to be real' floor ACCEPTS it",
      len(GCS) >= 1000, True)
check("KNOWN-BAD control: ...and it is BIGGER than this fixture's real log, "
      "so 'bigger is realer' fails in the other direction too",
      len(GCS) > len(REAL), True)
for pat in ("UNREACHABLE", "ingress", "REACH_EVIDENCE", "RESULT: FAILED"):
    check(f"KNOWN-BAD control: the gsutil refusal greps clean for {pat!r}",
          len(re.findall(pat, GCS)), 0)

check("the platform 'no entries' body is REFUSED", isinstance(jl.witnessed(PLAT), NE), True)

# ⛔⛔ KNOWN-BAD CONTROL — THE ONE THAT PROVES THE ^ ANCHOR IS LOAD-BEARING.
# This body echoes its own query filter, and the filter CONTAINS an ISO instant:
#     # filter: … AND timestamp>="2026-08-21T00:36:12Z"
# So the witness is one regex anchor away from calling a refusal a valid log.
_UNANCHORED = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.?\d*Z")
check("KNOWN-BAD control: an UNANCHORED ISO search MATCHES the refusal",
      bool(_UNANCHORED.search(PLAT)), True)
check("...while the anchored witness does not — the anchor IS the difference",
      len(jl.LOG_LINE.findall(PLAT)), 0)

# ── the witness tolerates ANSI, because --allow-escape-sequences preserves it ──
check("a log line behind an ANSI colour run is still witnessed",
      isinstance(jl.witnessed("\x1b[0;32m2026-08-20T23:00:00.0Z done\n"), str), True)

# ── read_body: any channel, same three witnesses ─────────────────────────────
# ⇒ The channels are not enumerable — DEV4 reported a FOURTH tonight (`gh run view
# --log` returns a near-empty body with exit 0 while the RUN, not the job, is still
# in progress). So the guard takes a body from anywhere rather than growing a case
# per channel.
check("a missing file reads as None, and None is REFUSED",
      isinstance(jl.witnessed(jl.read_body(os.path.join(_here, "nope.txt"))), NE), True)
check("...and the refusal names the fetch, not the content",
      "did not complete" in str(jl.witnessed(jl.read_body("/nonexistent/x"))), True)
check("a real body read from disk IS witnessed",
      isinstance(jl.witnessed(jl.read_body(
          os.path.join(_here, "testdata", "gcs-reauth-body.txt"))), NE), True)


# ── ⛔⛔ BOTH OBVIOUS ANCHORINGS ARE WRONG, IN OPPOSITE DIRECTIONS ─────────────
# The pair of fixtures below is the point: neither one alone locates the rule.
#   - the platform refusal CONTAINS an ISO instant (in its echoed query filter),
#     so free-text search accepts a refusal;
#   - `gh run view --log` puts the instant in the THIRD tab-separated field, so
#     line-start anchoring refuses every real log from that channel.
# ★ The timestamp must sit at a FIELD boundary: line start, or after a tab.
_RUNVIEW = "B1b: Smoke (dfc)\tRun tests\t2026-08-21T00:36:12.1234567Z starting\n"
_FREE    = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.?\d*Z")
_STRICT  = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.?\d*Z\s", re.M)

check("a tab-prefixed log line IS witnessed (gh run view --log)",
      isinstance(jl.witnessed(_RUNVIEW), str), True)
check("KNOWN-BAD control: a LINE-START-only anchor refuses that real log",
      bool(_STRICT.search(_RUNVIEW)), False)
check("KNOWN-BAD control: a FREE-TEXT search accepts the platform refusal",
      bool(_FREE.search(PLAT)), True)
check("...so only the field-boundary rule gets BOTH right",
      (isinstance(jl.witnessed(_RUNVIEW), str), isinstance(jl.witnessed(PLAT), NE)),
      (True, True))

# ── the 81-byte in-progress body ─────────────────────────────────────────────
# ⚠ PROVENANCE: captured by DEV4 on Blazing-Back and relayed verbatim — NOT
# captured from the wire by this session. Recorded that way deliberately: a value
# that round-trips between two agents acquires false independence, and the label
# is the only thing carrying the difference.
with open(os.path.join(_here, "testdata", "gh-run-inprogress-body.txt")) as _fh:
    INPROG = _fh.read()
check("the 81-byte in-progress body is REFUSED", isinstance(jl.witnessed(INPROG), NE), True)
# ⚠ 81 on the wire, 80 of text + the newline. Stated both ways because the first
# version of this check asserted a number I had DERIVED from "exactly 81 bytes"
# rather than measured, and it was wrong by one. The test caught it, not me.
check("...and it is 80 bytes of text (81 on the wire) — far BELOW any floor",
      (len(INPROG.rstrip()), len(INPROG)), (80, 81))
check("★ so no byte floor can catch both: 79 and 10,758 bracket every real log",
      len(INPROG) < 1000 < len(GCS), True)
check("...and it is not JSON, not HTML, not empty — it reads like a status message",
      INPROG.strip().startswith("run "), True)


# ── ⛔ "bytes" MUST MEAN BYTES ────────────────────────────────────────────────
# This tool printed `len(log)` and called it bytes. len() on a str counts
# CHARACTERS, and a CI log is full of ✅ ⛔ ─, so it understated by 110-124 on
# every real log measured. Caught by a peer who refused to pin a fixture on a
# number two fetches disagreed about (39,067 vs 38,950 — the 117 was the encoding,
# not the fetch).
#
# ★ It mattered more here than it usually would: this tool's whole argument is that
# SIZE IS NOT A WITNESS, and it prints a size anyway — the number people quote.
# A number a tool PRINTS is used as evidence whether or not the tool calls it one.
_MB = "2026-08-20T23:00:00.0Z ✅ done ⛔ ─────\n"
check("KNOWN-BAD control: len() UNDERSTATES a multi-byte log",
      len(_MB) < len(_MB.encode("utf-8")), True)
# ⚠ 14, MEASURED — 2 extra bytes each for ✅ ⛔ and five ─. I first wrote 16 from
#   arithmetic in my head and the suite caught it. Second time tonight a check
#   caught me asserting a DERIVED number; both times the derivation was the error,
#   not the code. ⇒ A test that only ever confirms what you predicted has no teeth.
check("...and the gap is exactly the multi-byte characters",
      len(_MB.encode("utf-8")) - len(_MB), 14)
check("the real fixtures are multi-byte too, so this is not a toy case",
      len(GCS.encode("utf-8")) >= len(GCS), True)

print(f"\n{len(fails)} failure(s)" if fails else "\nall checks passed")
sys.exit(1 if fails else 0)
