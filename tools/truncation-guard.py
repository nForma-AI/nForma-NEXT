#!/usr/bin/env python3
"""Can we show this reading was NOT truncated by a client-side page bound?

⛔ THE DEFECT, measured twice in one day by one role, six hours apart.

    gh issue list --state open --json number --jq 'length'     -> 30    (real: 85)
    gh run list --limit 5                                      -> 5     (real: 100)

★ AND THE MECHANISM IS WHY A RULE DID NOT STOP THE SECOND ONE. `gh`'s default page
size is 30. When the population exceeds the page, **the cap and the returned count
are the same number** -- so a full page and a complete set are byte-identical in the
output. There is nothing to notice. The first instance was written into
DEFECT-CLASSES.md before the second occurred, and the catalogue did not prevent it.
⇒ A defect whose signature is "the output looks correct" cannot be remedied by a
reader who knows about it. It needs an instrument.

⛔⛔ THREE STATES, AND THE THIRD IS THE WHOLE POINT.

    SAFE       a bound is KNOWN and the count is strictly below it
    TRUNCATED  the count EXACTLY EQUALS the effective bound
    UNKNOWN    no bound could be determined  <- must NEVER collapse into SAFE

An unstated limit is the COMMON case, and the flattering default is to call it fine.
Refusing it is the same convention as tools/README.md's exit 2: established nothing
is never all clear (#58). ⇒ `UNKNOWN` is exit 2, not exit 0.

⚠⚠ WHAT THIS CANNOT DO, AND IT IS PRINTED ON EVERY RUN, NOT ONLY HERE.
A count below the bound is NOT proof of completeness. This rules out exactly ONE
truncation mechanism -- **the client-side page bound** -- and is silent on every
other. In particular the SERVER may filter before paging: a permission-scoped list,
a search index that has not caught up, an endpoint that drops what the caller cannot
see. Those return short and honest-looking readings that this guard calls SAFE.
⇒ SAFE means "not truncated by a page bound", never "complete".

★ IT ANALYSES A READING, NEVER PERFORMS ONE. Input is a command string and a count.
No network, no subprocess, no clock. That is deliberate: a guard that re-ran the
query would be spending the budget the truncation is hiding, and would be unusable
on the reading you already have in front of you.

Usage:
    python3 tools/truncation-guard.py --count 30 --command "gh issue list --state open"
    python3 tools/truncation-guard.py --self-test

Exit: 0 SAFE -- bound known, count strictly below it
      1 TRUNCATED -- count equals the effective bound
      2 UNKNOWN -- no bound determinable, or the reading contradicts itself
      3 the known-positive control failed
"""
import argparse
import re
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from runmarker import begin, result  # noqa: E402

# ⛔ Implicit defaults. A bound nobody typed is still a bound, and it is the one that
# produced BOTH measured instances -- neither command carried a --limit at all.
# Keyed on a normalised command prefix; only commands whose default we can name are
# listed, because guessing one would manufacture a SAFE verdict out of nothing.
IMPLICIT_DEFAULTS = {
    "gh issue list": 30,
    "gh pr list": 30,
    "gh run list": 20,
    "gh release list": 30,
    "gh repo list": 30,
    "gh gist list": 10,
    "gh workflow list": 50,
    "gh cache list": 30,
    "gh label list": 30,
    "gh api": 30,          # REST default per_page
    "gh search": 30,
}

# ⚠ Server-side hard caps that an explicit larger --limit CANNOT lift. `--limit 1000`
# on a search endpoint still stops at 1000, and per_page above 100 is clamped to 100.
HARD_CAPS = {
    "gh search": 1000,
    "gh api search/": 1000,
}

PER_PAGE_CLAMP = 100   # GitHub clamps per_page > 100 to 100, silently.

BOUND_PATTERNS = [
    (re.compile(r"--limit[=\s]+(\d+)"), "--limit"),
    (re.compile(r"(?<![\w-])-L[=\s]+(\d+)"), "-L"),
    (re.compile(r"per_page[=\s]+(\d+)"), "per_page"),
    (re.compile(r"\|\s*head\s+-n\s*(\d+)"), "| head -n"),
    (re.compile(r"\|\s*head\s+-(\d+)\b"), "| head -N"),
    (re.compile(r"\|\s*tail\s+-n\s*(\d+)"), "| tail -n"),
    (re.compile(r"--top[=\s]+(\d+)"), "--top"),
    (re.compile(r"-n\s+(\d+)\s*$"), "-n"),
]

PAGINATE = re.compile(r"--paginate\b")

# ⛔ A STATED TOTAL IS NOT A PAGE. `--jq .total_count` extracts the population size the
# API declares; `per_page` bounds the ARRAY beside it and does not govern that number.
# Found by dogfooding: `search/issues -F per_page=1 --jq .total_count` returns 85 with
# per_page=1, and the naive reading calls it TRUNCATED at every page size. ⚠ That call
# is close-condition-scan.py's own truncation cross-check, so shipping the false
# positive would have had two tools by one author contradicting each other — the exact
# outcome gh-complete.py was built after. ⇒ Refuse, and say why. A guard that cries
# wolf on the correct idiom teaches its reader to mute it.
STATED_TOTAL = re.compile(r"total_count|\.total\b|X-Total-Count", re.IGNORECASE)


class Reading:
    """A count, and how it was obtained. Both halves are required: a count with no
    provenance is exactly the object this guard cannot rule on."""

    def __init__(self, count, command):
        self.count = count
        self.command = " ".join((command or "").split())


def _normalised_prefix(cmd):
    """Longest IMPLICIT_DEFAULTS key that the command starts with.

    ⚠ Longest-match, not first-match: `gh api search/issues` must not resolve to the
    `gh api` default of 30 when the search cap is the operative one."""
    best = None
    for key in IMPLICIT_DEFAULTS:
        if cmd.startswith(key) and (best is None or len(key) > len(best)):
            best = key
    return best


def bounds(reading):
    """Every bound this command is subject to, as (value, source) pairs.

    ⇒ The EFFECTIVE bound is the minimum: a `--limit 1000` piped through `head -30`
    is bounded at 30, and reporting the 1000 would be reporting the bound that does
    not bind."""
    cmd = reading.command
    found = []

    for pat, label in BOUND_PATTERNS:
        for m in pat.finditer(cmd):
            v = int(m.group(1))
            if label == "per_page" and v > PER_PAGE_CLAMP:
                # ⛔ Not an error and not honoured. GitHub clamps it and says nothing,
                # which is this guard's own defect class one layer down.
                found.append((PER_PAGE_CLAMP,
                              f"per_page={v} silently CLAMPED to {PER_PAGE_CLAMP}"))
            else:
                found.append((v, f"{label} {v}"))

    explicit = bool(found)
    paginated = bool(PAGINATE.search(cmd))

    for key, cap in HARD_CAPS.items():
        if cmd.startswith(key):
            found.append((cap, f"server hard cap for `{key}` ({cap})"))

    # An implicit page default applies only when nothing explicit overrode it and the
    # caller did not ask gh to walk every page.
    if not explicit and not paginated:
        key = _normalised_prefix(cmd)
        if key:
            found.append((IMPLICIT_DEFAULTS[key],
                          f"IMPLICIT default page size for `{key}` "
                          f"({IMPLICIT_DEFAULTS[key]}) — nobody typed this"))
    return found, paginated


def verdict(reading):
    """(state, effective_bound, reasons). ⛔ Never returns SAFE without a bound."""
    if not reading.command:
        return "UNKNOWN", None, ["no command was supplied — a count with no "
                                 "provenance cannot be ruled on"]
    if reading.count is None or reading.count < 0:
        return "UNKNOWN", None, ["no usable count"]

    if STATED_TOTAL.search(reading.command):
        return "UNKNOWN", None, [
            "the count looks like a STATED TOTAL (`total_count`), not a list length",
            "a page bound governs the ARRAY, never the population size beside it — "
            "`per_page=1 --jq .total_count` is CORRECT and would read TRUNCATED here",
            "⇒ this guard rules on list lengths; it refuses rather than cry wolf on "
            "the very idiom that detects truncation properly"]

    found, paginated = bounds(reading)
    if not found:
        why = ["no --limit, per_page, head/tail bound, or known implicit default "
               "could be determined for this command"]
        if paginated:
            why.append("--paginate removes the page bound but this tool cannot "
                       "confirm the walk completed")
        return "UNKNOWN", None, why

    eff, src = min(found, key=lambda b: b[0])
    reasons = [s for _, s in sorted(found)]

    if reading.count > eff:
        # ⛔ The reading contradicts its own bound. Refuse rather than pick a side:
        # either the count or the command is wrong, and guessing which would be the
        # confident-wrong-measurement this exists to prevent.
        return "UNKNOWN", eff, reasons + [
            f"⛔ count {reading.count} EXCEEDS the effective bound {eff} — the count "
            f"and the command disagree; one of them is not describing the other"]
    if reading.count == eff:
        return "TRUNCATED", eff, reasons
    return "SAFE", eff, reasons


def render(reading, state, eff, reasons):
    out = [f"reading: count={reading.count}",
           f"command: {reading.command or '(none)'}", ""]
    verdicts = {
        "SAFE": f"✅ SAFE — count {reading.count} is strictly below the effective "
                f"bound {eff}",
        "TRUNCATED": f"⛔ TRUNCATED — count {reading.count} EXACTLY EQUALS the "
                     f"effective bound {eff}. A full page and a complete set are "
                     f"byte-identical here; this reading is a PREFIX until shown "
                     f"otherwise.",
        "UNKNOWN": "⛔ UNKNOWN — established nothing. This is NOT 'fine': an "
                   "unstated limit is the common case, and the flattering reading "
                   "of it is what produced both measured instances.",
    }
    out.append(verdicts[state])
    out.append("")
    out.append("bounds considered:")
    for r in reasons:
        out.append(f"  · {r}")
    out.append("")
    out.append("⚠ THIS RULES OUT ONE MECHANISM: the client-side page bound.")
    out.append("  It says NOTHING about server-side filtering before paging — a")
    out.append("  permission-scoped list, a lagging search index, or an endpoint")
    out.append("  dropping what the caller cannot see all return short, honest-")
    out.append("  looking readings that this guard calls SAFE.")
    out.append("  ⇒ SAFE means 'not truncated by a page bound', never 'complete'.")
    if state == "SAFE" and reading.count == 0:
        out.append("")
        out.append("⚠ COUNT IS ZERO. Not truncated — but zero has its own failure")
        out.append("  mode this guard does not cover: a filter that matches nothing")
        out.append("  because it names nothing (a mistyped label returns exit 0 with")
        out.append("  zero bytes). See #317. Verdict unchanged; conflating the two")
        out.append("  would overclaim.")
    return "\n".join(out)


CONTROLS = [
    # ⛔ CRITERION 4 — the two real specimens, verbatim. Both are strings plus a
    # number; neither costs an API call. If this tool cannot produce BOTH verdicts
    # from them it is not a guard, and the suite says so rather than passing.
    (30, "gh issue list --repo nForma-AI/nForma-NEXT --state open --json number "
         "--jq 'length'", "TRUNCATED",
     "the real reading that reported 30 against a population of 85"),
    (85, "gh issue list --repo nForma-AI/nForma-NEXT --state open --limit 1000 "
         "--json number", "SAFE",
     "the corrected reading of the same population"),
    (100, "gh run list --limit 100", "TRUNCATED",
     "count equals an EXPLICIT limit — the second measured instance's shape"),
    (5, "gh run list --limit 5", "TRUNCATED",
     "the second measured instance, verbatim"),
    # ⛔ The UNKNOWN control. A bare pipeline has no bound and MUST NOT read SAFE.
    (4213, "git log --oneline | wc -l", "UNKNOWN",
     "no bound exists — the flattering default is SAFE and it is refused"),
    (30, "curl -s https://example.invalid/things | jq length", "UNKNOWN",
     "an unrecognised producer: 30 is suspicious but nothing here BOUNDS it"),
    # Precedence and clamping.
    (30, "gh issue list --limit 1000 | head -30", "TRUNCATED",
     "min-of-bounds: head -30 binds, --limit 1000 does not"),
    (100, "gh api -X GET search/issues -F per_page=1000", "TRUNCATED",
     "per_page=1000 is silently clamped to 100, and the count equals the clamp"),
    (85, "gh api repos/o/r/issues --paginate", "UNKNOWN",
     "--paginate removes the page bound but completion is not thereby shown"),
    (200, "gh issue list --limit 30", "UNKNOWN",
     "count EXCEEDS its own bound — the reading contradicts itself; refuse"),
    (0, "gh issue list --label nonexistent --limit 100", "SAFE",
     "zero is not truncated — and the note names the failure mode it IS"),
    # ⛔ Found by dogfooding this guard on the OTHER tool's cross-check call.
    (1, "gh api -X GET search/issues -F per_page=1 --jq .total_count", "UNKNOWN",
     "a STATED TOTAL is not a page — the correct anti-truncation idiom must not "
     "be flagged by the truncation guard"),
]


def self_test():
    fails = []
    for count, cmd, expect, why in CONTROLS:
        got, _, _ = verdict(Reading(count, cmd))
        ok = got == expect
        if not ok:
            fails.append((why, expect, got))
        print(f"  {'ok  ' if ok else 'FAIL'} {expect:<9} got {got:<9} {why}")
    if fails:
        print("\n⛔ the guard is broken; no verdict it produces can be trusted:")
        for why, e, g in fails:
            print(f"     {why}: expected {e}, got {g}")
        return 3
    states = {e for _, _, e, _ in CONTROLS}
    print(f"\n  {len(CONTROLS)}/{len(CONTROLS)} controls passed, covering "
          f"{len(states)} of 3 states: {', '.join(sorted(states))}.")
    print("  ⇒ Both real specimens are present and produce OPPOSITE verdicts from "
          "the same\n    command family — which is the only evidence this "
          "discriminates rather than\n    always saying one thing.")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--count", type=int, help="the number the reading produced")
    ap.add_argument("--command", default="", help="the command that produced it")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--quiet", action="store_true",
                    help="print only the verdict word")
    a = ap.parse_args()

    if a.self_test:
        rc = self_test()
        result("SELF-TEST-PASS" if rc == 0 else "SELF-TEST-FAILED")
        return rc

    # The known-positive runs before every real verdict. A guard that only checks
    # itself when asked is one whose caller never asks.
    for count, cmd, expect in ((30, "gh issue list", "TRUNCATED"),
                               (1, "git log | wc -l", "UNKNOWN")):
        if verdict(Reading(count, cmd))[0] != expect:
            print("⛔ known-positive control failed — refusing to rule.",
                  file=sys.stderr)
            result("CONTROL-FAILED")
            return 3

    if a.count is None:
        print("⛔ --count is required. A command with no count is not a reading.",
              file=sys.stderr)
        result("ESTABLISHED-NOTHING")
        return 2

    r = Reading(a.count, a.command)
    state, eff, reasons = verdict(r)
    print(state if a.quiet else render(r, state, eff, reasons))
    result(state)
    return {"SAFE": 0, "TRUNCATED": 1, "UNKNOWN": 2}[state]


if __name__ == "__main__":
    begin("truncation-guard")
    sys.exit(main())
