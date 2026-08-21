#!/usr/bin/env python3
"""Fetch an Actions job log, or say you did not. A refusal greps as clean.

⛔ MEASURED TWICE IN ONE NIGHT, both near-misses:

  99 bytes   `gh run view --job N --log` without --allow-escape-sequences returns
             a refusal that reads as an empty log. A peer hit it on a 29KB file.
  535 bytes  a REST 403 body is JSON. Fetched five job logs in a loop, greped each
             for the failure signature, and got `unreach=0` and `<no provider>` for
             ALL FIVE -- a clean sweep produced entirely by rate-limit refusals.

★ THE SHAPE: a refusal is TEXT. Every grep over it returns zero, and zero matches
reads as "the signature is not there" rather than "there is no log here". The
successful fetch of the same job was 46,922 bytes; the refusals were 535.

⇒ So this refuses to hand back a body it cannot witness. THREE independent
witnesses, because any one of them alone has a hole:

  the fetch exited 0            -- but `gh` exits 0 on some refusals
  the body is not a JSON error  -- but a truncated log is not JSON either
  the body carries a TIMESTAMP  -- an Actions log line is `2026-..Z <text>`;
                                   a refusal, an empty file and an HTML error page
                                   all lack it

⛔⛔ AND THESE WITNESSES CERTIFY PROVENANCE, NOT COMPLETENESS.

    A witness that certifies PROVENANCE does not certify COMPLETENESS,
    and every absence claim needs the second one. COUNTS ARE ABSENCE CLAIMS.

★ That is this tool's own primary output. All three witnesses answer "is this body
A LOG". None answers "is this THE WHOLE LOG". ⇒ A body that is truncated but
timestamped passes all three and then returns 0 for every --grep pattern — which
reads as "the signature is absent", the exact defect this file exists to prevent,
one level up. And it is MORE dangerous than a refusal, because it genuinely IS the
log; there is no wrong-shaped body to notice.

⚠ A fourth witness — evidence the job TERMINATED (`Complete job`, `Post job
cleanup`, a final `Process completed with exit code N`) — is NOT implemented here,
deliberately. There is exactly one specimen of it. A cancelled job, or one killed
by a runner loss, may legitimately carry none of those while still being the
complete available body, and a witness that refuses a legitimately-short body is
precisely the mistake `^ISO` already made against `gh run view --log`. ⇒ When it
lands it should WARN on absence, not refuse, until specimens exist from a cancelled
and a runner-killed job. Stated here as an open gap rather than a passing check.

⚠ The size floor is deliberately NOT a witness. 535 and 99 are both "small", but
so is a genuinely short job log, and picking a threshold invents a boundary the
data does not have. The timestamp is a property of the format, not of the length.
"""
import argparse, json, os, re, subprocess, sys, types

_here = os.path.dirname(os.path.abspath(__file__))
_est = os.path.join(_here, "established.py")
_m = types.ModuleType("established"); _m.__file__ = _est
with open(_est) as _fh:
    exec(compile(_fh.read(), _est, "exec"), _m.__dict__)
established, NotEstablished = _m.established, _m.NotEstablished

# A log line begins with an ISO instant — the format's own signature. Optionally
# behind an ANSI colour run, because --allow-escape-sequences preserves them.
#
# ⛔⛔ BOTH OBVIOUS ANCHORINGS ARE WRONG, AND IN OPPOSITE DIRECTIONS. Measured
# 2026-08-21 across six real bodies from four channels:
#
#                        DEV4's `gh run view --log`   platform "no entries"
#     ^ISO   (anchored)  REFUSES EVERY REAL LOG       refuses           ✅
#     ISO    (free)      accepts                      ACCEPTS A REFUSAL ⛔
#     (^|\t)ISO          accepts                      refuses           ✅ both
#
# ⇒ Free-text search is too loose: the platform body echoes its own query filter,
#   which CONTAINS an ISO instant — `… AND timestamp>="2026-08-21T00:36:12Z"` —
#   so an unanchored search calls a refusal a valid log.
# ⇒ Line-start is too tight: `gh run view --log` prefixes every line
#   `<job>\t<step>\t<ISO> <text>`, so the instant is the THIRD tab-separated
#   field. A peer built exactly this and their KNOWN-GOOD control caught it — a
#   real 454-line log matched ZERO lines. Fail-closed, safe, and useless forever.
#
# ★ So the timestamp must sit at a FIELD boundary: line start or after a tab.
#   Neither fixture alone locates that rule; it took a refusal that contains an
#   instant and a real log that does not start with one.
LOG_LINE = re.compile(
    r"(?:^|\t)(?:\x1b\[[0-9;]*m)*\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.?\d*Z\s", re.M)


def witnessed(body):
    """The log text, or a NotEstablished naming which witness failed."""
    if body is None:
        return established(None, False, "the fetch did not complete")
    s = body.strip()
    if not s:
        return established(None, False, "the body is empty — an empty file and a "
                                        "silent refusal are the same zero bytes")
    if s.startswith("{") and '"message"' in s[:400]:
        try:
            msg = json.loads(s).get("message", "")[:90]
        except ValueError:
            msg = s[:90]
        return established(None, False, f"the body is a JSON error, not a log: {msg!r}")
    if not LOG_LINE.search(s):
        return established(None, False, "no line carries an ISO timestamp — a job log "
                                        "always does, on every channel that serves one, "
                                        "so this is not one. A rate-limit JSON, a gsutil "
                                        "reauth traceback, an HTML error page, an empty "
                                        "file and a truncated stream all grep as zero "
                                        "matches.")
    return s


def fetch_gcs(uri):
    """A GCS object body, or None. ⛔ gsutil's refusal is 10,758 BYTES — a full Python
    traceback ending in ReauthUnattendedError. Bigger than plenty of real job logs, so
    any "small body means refusal" heuristic waves it straight through. Measured."""
    try:
        r = subprocess.run(["gsutil", "cat", uri],
                           capture_output=True, text=True, timeout=180)
    except (OSError, subprocess.SubprocessError):
        return None
    # ⚠ gsutil prints its traceback on STDERR and exits 1, but prints partial output on
    # stdout in other failure modes. Hand BOTH to the witness rather than choosing here —
    # choosing is how a refusal gets discarded and re-read as an empty success.
    return (r.stdout or "") + (r.stderr or "") or None


def read_body(path):
    """A body produced by ANY channel, witnessed the same way.

    ⇒ The channels are not enumerable. GitHub REST, GCS and the platform API all serve
    the same evidence and all three refuse differently; a guard that hardcodes them
    hardens the ones it knows and leaves the next one bare. So this takes a file (or -
    for stdin) and applies the same three witnesses to whatever produced it.

    ⚠ If you pipe into this, the producer's exit code is already gone. That is fine —
    the witnesses never consult it — but do not then report the PIPELINE's status as the
    fetch's status."""
    try:
        if path == "-":
            return sys.stdin.read() or None
        with open(path, errors="replace") as fh:
            return fh.read() or None
    except OSError:
        return None


def fetch(repo, job_id):
    """Raw body or None. --allow-escape-sequences is NOT optional: without it the
    API returns a short refusal for logs containing ANSI, and it reads as empty."""
    try:
        r = subprocess.run(
            ["gh", "api", "--allow-escape-sequences",
             f"repos/{repo}/actions/jobs/{job_id}/logs"],
            capture_output=True, text=True, timeout=180)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout if r.stdout else None


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--repo", help="owner/name — fetch an Actions job log (needs job_id)")
    src.add_argument("--gcs", metavar="URI", help="gs://… object, fetched with gsutil cat")
    src.add_argument("--witness-file", metavar="PATH",
                     help="witness a body ANY channel produced; - for stdin")
    ap.add_argument("job_id", nargs="?")
    ap.add_argument("--grep", action="append", default=[], metavar="TEXT",
                    help="LITERAL text to count; repeatable. Not a regex — see --grep-re. "
                         "Counts are only printed for a WITNESSED log, never over a refusal.")
    ap.add_argument("--grep-re", action="append", default=[], metavar="PATTERN",
                    help="regex to count; repeatable. Opt in deliberately: an unescaped "
                         "metacharacter fails SILENTLY toward 'absent'.")
    ap.add_argument("--show-lines", type=int, default=3,
                    help="matching lines to print per --grep pattern (0 = counts only). "
                         "A count invites a conclusion; a line lets you check it.")
    a = ap.parse_args()

    if a.repo:
        if not a.job_id:
            ap.error("--repo needs a job_id")
        body, where = fetch(a.repo, a.job_id), f"{a.repo} job {a.job_id}"
    elif a.gcs:
        body, where = fetch_gcs(a.gcs), a.gcs
    else:
        body, where = read_body(a.witness_file), a.witness_file

    log = witnessed(body)
    if isinstance(log, NotEstablished):
        print(f"{log}  [{where}]")
        print("   ⛔ No counts are printed. A grep over a refusal returns 0 for every "
              "pattern,\n      and 0 matches reads as 'the signature is absent'.")
        return 2

    # ⛔ THIS SAID "bytes" AND COUNTED CHARACTERS. Caught 2026-08-21 by a peer who
    # refused to pin a fixture on a number two fetches disagreed about: their fetch
    # measured 39,067 and this printed 38,950. The 117 was not a fetch difference —
    # `len()` on a str counts CHARACTERS, and a CI log is full of ✅ ⛔ ─, so it
    # understated by 110-124 on every log measured. Reconciled exactly:
    # len(stripped.encode("utf-8")) == the on-disk byte count, on all four.
    #
    # ★ AND THE MISLABEL MATTERED MORE HERE THAN IT USUALLY WOULD: this tool's whole
    # argument is that SIZE IS NOT A WITNESS — and it prints a size anyway, which is
    # the number people then quote (46,922 vs 535 is cited in its own docstring).
    # ⇒ A number a tool PRINTS gets used as evidence whether or not the tool calls
    # it one. So it is now exact, and says which quantity it is.
    raw_b = len(body.encode("utf-8", "replace")) if body else 0
    txt_b = len(log.encode("utf-8", "replace"))
    note = "" if raw_b == txt_b else f" ({raw_b} fetched, {raw_b - txt_b} stripped)"
    print(f"✅ witnessed log: {txt_b} bytes{note}, "
          f"{len(LOG_LINE.findall(log))} timestamped line(s)")
    # ⛔⛔ --grep IS LITERAL, AND IT USED TO BE A REGEX. LIVE FALSE ZERO, 2026-08-21.
    # A peer asked whether a C0(dfc) "success" was vacuous:
    #     --grep 'poll_until(pod leaves Running state): timed out after'  ->  0
    # The string is in the log EXACTLY ONCE. The unescaped `(...)` is a capture
    # group, so it searched for `poll_untilpod leaves Running state: timed out
    # after`, which never appears. Measured on the same body:
    #     literal  body.count(p)                  = 1
    #     regex    re.findall(p, body)            = 0   <- what the tool printed
    #     escaped  re.findall(re.escape(p), body) = 1
    #
    # ★ THE DIRECTION IS WHY THE DEFAULT FLIPPED. This tool's whole job is
    # answering ABSENCE questions — "does my change appear in this log?" — and the
    # natural things to search for in a CI log are full of metacharacters:
    # `poll_until(...)`, `deploy_custom_sdl -> console_api_1:`, version strings
    # with dots. Every one of them fails silently toward "not present".
    # ⇒ A refusal greps as clean; so did a paren. The witness proved the body was a
    # log and then the matcher lied about its contents.
    # ⚠ The peer nearly recorded the OPPOSITE conclusion off that 0. Escaped, it
    # confirmed #1319's C0(dfc) pass IS vacuous.
    for pat in a.grep:
        hits = [l for l in log.splitlines() if pat.lower() in l.lower()]
        print(f"  {len(hits):5d}  {pat}")
        # ⛔ A COUNT INVITES A CONCLUSION; A LINE LETS YOU CHECK IT. Measured by a
        # peer the same night: `--grep 402` on a B1b failure returned 16, and they
        # were one message from reporting "16 x 402 confirms the funding story".
        # Nine of those were HEX — `setup-python@a26af69be951a213d495a4c3e4e4022e16d87065`
        # contains "402", and an Actions log is full of SHAs. The true answer was 3,
        # one per Console backend. They caught it ONLY by asking for the lines.
        # ⚠ And an Actions log contains the step's OWN SCRIPT, so any phrase the
        # workflow quotes matches every run of it: their `UNREACHABLE` counted 1
        # against a RUNTIME count of 0.
        for l in hits[:a.show_lines]:
            print(f"         │ {l.strip()[:150]}")
        if len(hits) > a.show_lines:
            print(f"         └ … {len(hits) - a.show_lines} more (--show-lines)")
    for pat in a.grep_re:
        try:
            rx = re.compile(pat, re.I)
        except re.error as e:
            print(f"      ⛔  {pat}   INVALID REGEX ({e}) — no count printed, because "
                  f"a broken pattern and an absent string both produce 0.")
            continue
        hits = [l for l in log.splitlines() if rx.search(l)]
        lit = len([l for l in log.splitlines() if pat.lower() in l.lower()])
        note = ""
        if lit != len(hits):
            # ⚠ the pattern means something different as a regex than as text, and
            # THAT is the case that produced the false zero. Say so at the point of
            # use rather than trusting anyone to remember which flag they passed.
            note = f"   ⚠ literal would give {lit} — the metacharacters are active"
        print(f"  {len(hits):5d}  {pat}  (regex){note}")
        for l in hits[:a.show_lines]:
            print(f"         │ {l.strip()[:150]}")
        if len(hits) > a.show_lines:
            print(f"         └ … {len(hits) - a.show_lines} more (--show-lines)")
    if not a.grep and not a.grep_re:
        sys.stdout.write(log)
    return 0


if __name__ == "__main__":
    sys.exit(main())
