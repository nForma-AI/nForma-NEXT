#!/usr/bin/env python3
"""Pins that a refused reading cannot be mistaken for a value — and where it still can.

⛔ The four instruments that rediscovered this in one day, each shipping without
it first: a 0 API-call count read as restraint (the meter was exhausted), 0 current
red checks read as a clean board (nothing had re-run), 0 untouched issues read as
full coverage (the query failed), 0 conflicts read as no collisions (the heads were
never fetched).

★ All four fail toward REASSURANCE, which is why the guard must be structural:
nobody double-checks a clean result, and that is exactly when this fires.

Run: python3 tools/test_established.py
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


e = load(os.path.join(_here, "established.py"), "e")
fails = []


def check(name, got, want):
    ok = got == want
    print(f"{'✅' if ok else '❌'} {name}")
    if not ok:
        print(f"     got  {got!r}\n     want {want!r}")
        fails.append(name)


# ── the refusal cannot pose as a value ───────────────────────────────────────
r = e.zero_is_a_finding(0, False, "API calls")
check("a refused reading is FALSY, so `if result:` skips it", bool(r), False)
check("...and it is NOT None — `is None` checks do not catch it", r is None, False)
check("...and it is not equal to 0, so `== 0` does not either", r == 0, False)
check("it carries WHY, in prose", "nothing establishes" in str(r), True)

# ── the witness is about execution, not about the value ──────────────────────
check("a witnessed zero is the number 0", e.zero_is_a_finding(0, True, "x"), 0)
check("a non-zero passes through even unwitnessed — it carries its own evidence",
      e.zero_is_a_finding(7, False, "x"), 7)
check("established() returns the value when the witness holds",
      e.established([1, 2], True, "why"), [1, 2])
check("...and refuses when it does not", bool(e.established([1, 2], False, "why")), False)

# ── ⚠ THE LIMIT I CANNOT DESIGN AWAY, pinned rather than discovered ──────────
# Falsiness is what makes `if result:` safe. The SAME falsiness means `or` still
# converts a refusal into a default. There is no value that is both falsy for
# `if` and immune to `or`, so this is stated, not fixed.
check("⚠ `or 0` DEFEATS the guard — falsy is what makes `if` safe and `or` unsafe",
      (e.zero_is_a_finding(0, False, "x") or 0), 0)
check("...so the remedy is `if isinstance(x, NotEstablished)`, which does work",
      isinstance(e.zero_is_a_finding(0, False, "x"), e.NotEstablished), True)

# ── KNOWN-BAD control: the misuse that looks correct ─────────────────────────
# `established(0, count == 0, ...)` is always-true nonsense — a witness about the
# VALUE rather than about the EXECUTION. It cannot be detected at runtime, so the
# control shows what it silently produces.
count = 0
check("KNOWN-BAD control: a witness about the VALUE always passes, guarding nothing",
      e.established(count, count == 0, "wrong witness"), 0)

print(f"\n{len(fails)} failure(s)" if fails else "\nall checks passed")
sys.exit(1 if fails else 0)
