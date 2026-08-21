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

# an Actions log line begins with an ISO instant — the format's own signature
LOG_LINE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.?\d*Z\s", re.M)


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
        return established(None, False, "no line carries an ISO timestamp — an Actions "
                                        "log always does, so this is not one. A refusal, "
                                        "an HTML error page and a truncated stream all "
                                        "grep as zero matches.")
    return s


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
    ap.add_argument("--repo", required=True)
    ap.add_argument("job_id")
    ap.add_argument("--grep", action="append", default=[],
                    help="pattern to count; repeatable. Counts are only printed for "
                         "a WITNESSED log — never over a refusal.")
    a = ap.parse_args()

    log = witnessed(fetch(a.repo, a.job_id))
    if isinstance(log, NotEstablished):
        print(str(log))
        print("   ⛔ No counts are printed. A grep over a refusal returns 0 for every "
              "pattern,\n      and 0 matches reads as 'the signature is absent'.")
        return 2

    print(f"✅ witnessed log: {len(log)} bytes, "
          f"{len(LOG_LINE.findall(log))} timestamped line(s)")
    for pat in a.grep:
        print(f"  {len(re.findall(pat, log, re.I)):5d}  {pat}")
    if not a.grep:
        sys.stdout.write(log)
    return 0


if __name__ == "__main__":
    sys.exit(main())
