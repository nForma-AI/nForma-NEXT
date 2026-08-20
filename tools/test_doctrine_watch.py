#!/usr/bin/env python3
"""Pins that a role comes from the BOOTSTRAP — not a correction, not a quotation.

⛔ `doctrine-watch.py` had no suite at all, which is how this survived: `role_of`
promised *"the role a session was BOOTSTRAPPED as — a name can be changed, this
cannot"* and scanned the WHOLE FILE for `You are X.`, taking the first hit
anywhere. Measured over nine live fleet transcripts, it resolved 3 and **2 of the
3 were wrong**:

  e4a7769d -> "DEV2"   record 17155, a CORRECTION sent a day later — "your
                       identity was wrong ... You are DEV2". Bootstrap: MAINTAINER.
  c67ebcb4 -> "DEV2"   a session bootstrapped as DX, which had merely been
                       discussing DEV2 all day.
  6fc2dca8 -> "DEVOPS" record 3132, inside a QUOTATION of someone else's prompt.

⇒ It returned the mutable thing it promised immunity from, and a MENTION rather
than a USE. The other six returned `None`, which also meant "could not read it".

★ Every leg here carries the KNOWN-BAD control: `whole_file_scan` is the shipped
predicate, and it is asserted to give the WRONG answer on the same fixture. A
suite that only pins the right answer cannot show the wrong one was available.

⚠ Mutating this file: assert the replacement string's LENGTH, never eyeball it. A
one-byte mutation that does not apply reads as a clean SURVIVED on the very check
written to prevent clean SURVIVEDs.

Run: python3 tools/test_doctrine_watch.py
"""
import json, os, re, sys, tempfile, types

_here = os.path.dirname(os.path.abspath(__file__))


def load(path, name):
    """Execute the source read NOW — a positive reload proof, no cache to consult.

    ⛔ `spec_from_file_location` consults `__pycache__`, invalidated on mtime+SIZE,
    so a SIZE-PRESERVING mutation in the same second is served from cache and
    SURVIVES with the file verifiably changed and the target verifiably gone.
    """
    src = open(path).read()
    mod = types.ModuleType(name)
    mod.__file__ = path
    try:
        exec(compile(src, path, "exec"), mod.__dict__)
    except SystemExit:
        pass
    return mod


dw = load(os.path.join(_here, "doctrine-watch.py"), "dw")

fails = []


def check(name, got, want):
    ok = got == want
    print(f"{'✅' if ok else '❌'} {name}")
    if not ok:
        print(f"     got  {got!r}\n     want {want!r}")
        fails.append(name)


def whole_file_scan(path):
    """The predicate that shipped. Kept as the known-bad control, not as history."""
    try:
        with open(path, errors="replace") as fh:
            for line in fh:
                if '"type":"user"' not in line and '"type": "user"' not in line:
                    continue
                m = re.search(r"You are ([A-Z]+[0-9]*)\.", line)
                if m:
                    return m.group(1)
    except OSError:
        return None
    return None


def user(text):
    return {"type": "user", "message": {"content": [{"type": "text", "text": text}]}}


def write(tmp, records, name="t.jsonl"):
    p = os.path.join(tmp, name)
    with open(p, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    return p


with tempfile.TemporaryDirectory() as tmp:
    # ── the two forms, both MEASURED in live bootstraps ──────────────────────
    p = write(tmp, [user("You are DX, an IMPLEMENTER reporting to TEAMLEAD.")], "a.jsonl")
    check("comma form: the live majority, 5 of 9", dw.role_of(p), "DX")
    check("KNOWN-BAD control: the shipped period-regex reads it as no role at all",
          whole_file_scan(p), None)

    p = write(tmp, [user("You are taking over as MAINTAINER / engineering lead for:")], "b.jsonl")
    check("'taking over as' form: measured 1 of 9", dw.role_of(p), "MAINTAINER")

    # ── ⛔ THE REGRESSION: a correction is not a bootstrap ────────────────────
    p = write(tmp, [user("You are taking over as MAINTAINER / engineering lead for:")]
              + [user("filler") for _ in range(50)]
              + [user("your identity was wrong.\n\n## Standing state\n\nYou are DEV2. Panel `DEV2`")],
              "c.jsonl")
    check("a CORRECTION 50 records later does not become the bootstrap role",
          dw.role_of(p), "MAINTAINER")
    check("KNOWN-BAD control: the shipped scan takes the correction",
          whole_file_scan(p), "DEV2")

    # ── ⛔ THE OTHER REGRESSION: a quotation is a mention, not a use ──────────
    p = write(tmp, [user("You are DEVOPS, an IMPLEMENTER reporting to TEAMLEAD.")]
              + [user('3. "TEAMLEAD — ROLE ESTABLISHED. You are DEV5. FIRST TASK..."')],
              "d.jsonl")
    check("a QUOTATION of another prompt does not override the bootstrap",
          dw.role_of(p), "DEVOPS")
    check("KNOWN-BAD control: the shipped scan reaches past the bootstrap to it",
          whole_file_scan(p), "DEV5")

    # ── three states, never two ──────────────────────────────────────────────
    p = write(tmp, [user("[TEAMLEAD auto-wake] You are idle. Resume your loop.")], "e.jsonl")
    check("a wake at the head names no role: '' — READ IT, found none", dw.role_of(p), "")
    check("...which is NOT None", dw.role_of(p) is None, False)

    p = write(tmp, [{"type": "assistant", "message": {"content": []}}], "f.jsonl")
    check("no launch prompt in the file is None — ESTABLISHED NOTHING", dw.role_of(p), None)
    check("an unreadable path is None, not ''", dw.role_of(os.path.join(tmp, "nope.jsonl")), None)

    # ── the reminder that precedes the bootstrap in some transcripts ─────────
    p = write(tmp, [user("<system-reminder>\nnamed this session \"DX\"\n</system-reminder>"),
                    user("You are ARCHITECT, an IMPLEMENTER reporting to TEAMLEAD.")], "g.jsonl")
    check("a <system-reminder> before the bootstrap is skipped", dw.role_of(p), "ARCHITECT")

    # ── the window is bounded ON PURPOSE ─────────────────────────────────────
    p = write(tmp, [user("filler") for _ in range(60)] + [user("You are DX, an IMPLEMENTER.")],
              "h.jsonl")
    check("a role beyond the bootstrap window is not reachable — bounded on purpose",
          dw.role_of(p), "")

    # ── the caller's contract still holds ────────────────────────────────────
    check("both non-answers are falsy, so the single caller's `if r:` is unchanged",
          (bool(""), bool(None)), (False, False))

print(f"\n{len(fails)} failure(s)" if fails else "\nall checks passed")
sys.exit(1 if fails else 0)
