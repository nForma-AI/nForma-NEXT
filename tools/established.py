#!/usr/bin/env python3
"""A zero means nothing until something witnesses that the reading happened.

⛔ FOUR INSTRUMENTS NEEDED THIS IN ONE DAY, each rediscovering it, each shipping
without it first:

  api-budget.py     0 API calls across nine panes -> "restraint"?  No: the meter
                    was EXHAUSTED and every request was refused.
  check-freshness   0 current red checks -> "the board is clean"?  No: NOTHING had
                    re-run since the boundary.
  issue-coverage    0 untouched issues -> "full coverage"?  No: the query failed,
                    or the transcript glob matched nothing.
  pr-stack.py       0 conflicts -> "nothing collides"?  No: PR heads were not
                    fetched, so most pairs were never compared.

★ THE SHAPE, once instead of four times: an observation is `OUTCOME AND
EXECUTION`. When the execution did not happen, the outcome is not a reading — and
crucially, **the outcome looks IDENTICAL in both cases**. Zero findings and zero
looking are the same number.

⚠ AND THE FAILURE IS ALWAYS TOWARD REASSURANCE. Every one of the four reads as
good news: no spend, no reds, full coverage, no conflicts. That asymmetry is why
it must be structural rather than remembered — nobody double-checks a clean
result, which is exactly when this fires.

⇒ So: state the WITNESS alongside the value. A witness is the thing that must be
true for the number to mean what it appears to mean, and it is named in prose so
the refusal can say what was missing.
"""


class NotEstablished:
    """A refused reading. Falsy, so `if result:` cannot mistake it for a value.

    ⛔ It is NOT an exception and NOT None. An exception forces a caller to handle
    it at the wrong moment; None invites `or 0`, which is how a refusal becomes a
    zero one line later. This is falsy, prints its reason, and compares unequal to
    every real value.
    """

    __slots__ = ("why",)

    def __init__(self, why):
        self.why = why

    def __bool__(self):
        return False

    def __eq__(self, other):
        return isinstance(other, NotEstablished) and other.why == self.why

    def __repr__(self):
        return f"NotEstablished({self.why!r})"

    def __str__(self):
        return f"⛔ ESTABLISHED NOTHING — {self.why}"


def established(value, witness, why):
    """`value` if the witness holds, else a NotEstablished carrying `why`.

    ⚠ `witness` is deliberately the SECOND argument and mandatory. A default of
    True would make the guard opt-in, and an opt-in guard against a reassuring
    zero is one that is skipped exactly when it matters.

    ⛔ The witness is about EXECUTION, never about the value. "Did the reader run"
    is a different question from "did the reader find anything", and conflating
    them is the defect: `established(0, count == 0, ...)` is always-true nonsense.
    """
    if witness:
        return value
    return NotEstablished(why)


def zero_is_a_finding(value, witness, subject):
    """A zero specifically — the case that reads as good news.

    ⇒ A non-zero value carries its own evidence that something ran. A ZERO does
    not, so only a zero needs the witness. Passing a non-zero through unchanged
    keeps the guard cheap enough that nobody routes around it.
    """
    if value:
        return value
    return established(value, witness,
                       f"{subject}: the count is 0, and nothing establishes that the "
                       "reading happened at all. Zero findings and zero looking are "
                       "the same number.")
