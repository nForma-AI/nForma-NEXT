#!/usr/bin/env python3
# SUITE-DEPENDS: one GraphQL query per population — network plus auth. Without a token
# it reports ESTABLISHED NOTHING (exit 2) rather than an empty fleet, which is the
# distinction the whole tool exists to preserve.
"""Which roles have SHIPPED something, when the STATE line cannot tell you.

⛔ THE GAP, named by an existing instrument in its own words. `tools/fleet-state.py`
exits 2 today and says exactly why:

    ⛔ NO ROLE-NAMED SESSION DECLARED — but 1 ROLELESS session(s) DID: 15b69750.
       ⛔ What is NOT established: anything about the role-named panes. They may
          be silent, unlaunched, or never given the prompt — this cannot tell

That is honest, and it is a dead end for a standup: "cannot tell" is precisely where
dispatch needs an answer, and policy differs completely between a pane that is running
and quiet and a pane that was never launched.

★ THE POINT IS THAT THE TWO MECHANISMS FAIL FOR UNRELATED REASONS, which is what makes
one a control on the other and not a second opinion from the same witness:

    fleet-state.py   reads TRANSCRIPTS   local · session-side · blind to a pane that
                                         never writes a STATE line
    this tool        reads ARTIFACTS     remote · output-side · blind to work that was
                                         done and never signed

⚠ COMMIT AUTHORSHIP CANNOT CARRY THIS. One git credential serves every pane (#4), so
git says "Jonathan Borduas" for all nine roles. The only author signal in this estate is
the body self-naming convention, and that is what is read here.

⛔ USE VS MENTION DECIDES THE ANSWER, it does not season it. Measured 2026-09-07 over the
24h window: ARCHITECT is MENTIONED in 13 comments and has SIGNED 0. A tool counting the
role name would have reported ARCHITECT the second-most-active role on a day it produced
nothing. So authorship is decided by POSITION — a role token in the last few non-empty
lines, or an explicit `Filed/Written/Posted by <ROLE>` byline — never by occurrence.

⛔ WHAT `SILENT` MUST NOT BE READ AS. Measured the same day: 280 of 432 comments carry no
signature at all, so the convention is followed about a third of the time. SILENT here
means ONLY "produced no SIGNED artifact in this window". A role that worked and did not
sign is invisible to this, and the unsigned count is printed on every run so the reading
cannot be taken further than it goes. ⇒ An unmeasured role must never read as an accused
one.

Exit: 0 every role produced something · 1 at least one role is SILENT (a finding, and the
usual state) · 2 established nothing (no token, no comments read) · 3 a control failed.
"""
import argparse
import collections
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from runmarker import guard, result  # noqa: E402

ROLES = ("TEAMLEAD", "ARCHITECT", "DEVOPS", "DX", "DEV1", "DEV2", "DEV3", "DEV4", "DEV5")
ROLE_RE = r"(TEAMLEAD|ARCHITECT|DEVOPS|DX|DEV[1-5])"
# ⇒ Three signature FORMS, all positional or explicitly performative. The bare-token form
# is anchored to the start of a line in the TAIL only; the byline form may appear anywhere
# because "Filed by X" is a claim of authorship wherever it sits.
# ⛔ ALL THREE ARE ANCHORED TO A LINE, IN THE TAIL. None of them was, before review.
# The un-anchored forms converted a MENTION into authorship, the one thing this tool
# exists to avoid: `ARCHITECT, session \`x\`, measured this` matched mid-sentence, and
# `measured by DEVOPS last week` — a statement about who took a reading — read as a
# byline.
#
# ⛔⛔ AND THE FIRST FIX WAS WRONG IN THE OTHER DIRECTION, caught by RUNNING it rather
# than re-reading it. Narrowing the verb list to filed|written|posted|appended dropped
# three real signatures in one 75-comment window — `Replicated by TEAMLEAD, session …`,
# `Withdrawn by TEAMLEAD, session …`, `Verified by TEAMLEAD, session …` — every one of
# them as performative as `Filed by`.
#
# ★ SO THE DISCRIMINATOR IS POSITION, NOT VOCABULARY, which is what the docstring said
# before I reached for a word list anyway. `Replicated by TEAMLEAD` STARTS a line in the
# tail; `This was measured by DEVOPS last week` does not. Anchor the line and the verb
# list can stay broad, because the sentence a mention lives in almost never begins with
# the verb.
# ⚠ The bound that remains, stated: a report that DOES start a tail line — `Measured by
# DEVOPS on 2026-09-01.` — is indistinguishable from a byline here, and is read as one.
SIG_TAIL = re.compile(rf"^\s*[*_>\s]*{ROLE_RE}\b", re.M)
SIG_SESSION = re.compile(rf"^\s*[*_>\s]*{ROLE_RE}\s*,\s*session", re.M)
SIG_BYLINE = re.compile(
    rf"^\s*[*_>\s]*(?:filed|written|posted|appended|replicated|withdrawn|verified|"
    rf"measured|answered|reported|raised|corrected)\s+by\s+[*_]{{0,2}}{ROLE_RE}",
    re.I | re.M)
MENTION = re.compile(rf"\b{ROLE_RE}\b")
TAIL_LINES = 3

QUERY = """
{ repository(owner:"%s", name:"%s") {
    issues(first:%d, states:OPEN, orderBy:{field:UPDATED_AT,direction:DESC}) {
      nodes { number comments(last:20){ nodes { createdAt body } } } }
    pullRequests(first:%d, orderBy:{field:UPDATED_AT,direction:DESC}) {
      nodes { number comments(last:20){ nodes { createdAt body } } } } } }
"""


def author(body):
    """The role that SIGNED this comment, or None.

    ⛔ The tail is read first and separately. A comment that DISCUSSES DEVOPS at length
    and is signed TEAMLEAD must return TEAMLEAD, and the only thing that guarantees it
    is looking at position before looking at content."""
    lines = [l for l in body.strip().splitlines() if l.strip()]
    tail = "\n".join(lines[-TAIL_LINES:])
    m = SIG_SESSION.search(tail) or SIG_BYLINE.search(tail) or SIG_TAIL.search(tail)
    return m.group(1) if m else None


def mentions(body):
    return set(MENTION.findall(body))


def fetch(repo, first):
    owner, name = repo.split("/", 1)
    q = QUERY % (owner, name, first, first)
    p = subprocess.run(["gh", "api", "graphql", "-f", f"query={q}"],
                       capture_output=True, text=True, timeout=180)
    if p.returncode != 0:
        return None, p.stderr.strip().splitlines()[0][:160] if p.stderr.strip() else "gh failed"
    try:
        d = json.loads(p.stdout)["data"]["repository"]
    except Exception as exc:  # noqa: BLE001
        return None, f"unparseable response: {exc}"
    rows = []
    for key, kind in (("issues", "issue"), ("pullRequests", "PR")):
        for node in d[key]["nodes"]:
            for c in node["comments"]["nodes"]:
                rows.append((c["createdAt"], kind, node["number"], c["body"]))
    return rows, None


def tally(rows, since):
    """(signed-per-role, mentioned-per-role, unsigned, window-size) — mentions are
    carried ONLY so the report can show the gap that a mention-counter would fall into."""
    sub = [r for r in rows if r[0] > since]
    signed = collections.Counter()
    mentioned = collections.Counter()
    unsigned = 0
    for _, _, _, body in sub:
        a = author(body)
        if a:
            signed[a] += 1
        else:
            unsigned += 1
        for m in mentions(body):
            mentioned[m] += 1
    return signed, mentioned, unsigned, len(sub)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default="nForma-AI/nForma-NEXT")
    ap.add_argument("--since", default=None,
                    help="ISO instant; default: 24h before the newest comment READ, so the "
                         "window is anchored to the data and not to the reader's clock")
    ap.add_argument("--first", type=int, default=100)
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()

    if a.self_test:
        rc = self_test()
        result("SELF-TEST-PASS" if rc == 0 else "SELF-TEST-FAILED")
        return rc

    rows, err = fetch(a.repo, a.first)
    if rows is None:
        print(f"⛔ ESTABLISHED NOTHING — could not read {a.repo}: {err}")
        print("⚠ This is NOT an empty fleet. It is an unread one.")
        result("ESTABLISHED-NOTHING")
        return 2
    if not rows:
        print(f"⛔ ESTABLISHED NOTHING — zero comments read from {a.repo}. A silent fleet "
              f"and an unread repository print the same table, so no table is printed.")
        result("ESTABLISHED-NOTHING")
        return 2

    # ⇒ ANCHORED TO THE DATA. A window measured from `now` drifts against a snapshot taken
    # minutes earlier and makes two runs incomparable for reasons that have nothing to do
    # with the fleet.
    newest = max(r[0] for r in rows)
    if a.since:
        since = normalise(a.since)
        if since is None:
            print(f"⛔ ESTABLISHED NOTHING — --since {a.since!r} is not an ISO instant.")
            result("ESTABLISHED-NOTHING")
            return 2
    else:
        since = _minus_24h(newest)
    signed, mentioned, unsigned, n = tally(rows, since)

    # ⛔ AN EMPTY WINDOW IS VOID, NOT A SILENT FLEET, and the role loop below cannot say
    # so — it would print nine SILENT lines and exit 1, which is a finding about the
    # fleet drawn from a reading that contains no fleet. The self-test asserted this
    # about tally(); nothing asserted it about the path a caller actually takes.
    if n == 0:
        print(f"⛔ ESTABLISHED NOTHING — zero comments fall in the window "
              f"{since} → {newest}, out of {len(rows)} read.")
        print("⚠ This is NOT a silent fleet. Widen --since, or check the clock that produced it.")
        result("ESTABLISHED-NOTHING")
        return 2

    print(f"── FLEET OUTPUT ── {len(rows)} comment(s) read from {a.repo}")
    print(f"   POPULATION  the {a.first} most-recently-updated OPEN issues and PRs, "
          f"last 20 comments of each")
    print(f"   WINDOW      {since} → {newest}   ({n} comment(s) fall inside)")
    print(f"   AUTHORSHIP  signature POSITION — tail of the body, or an explicit byline. "
          f"Never a mention.\n")
    silent = []
    for role in ROLES:
        s, m = signed[role], mentioned[role]
        if s:
            print(f"  ✅ PRODUCED {s:3}  {role:10} (mentioned in {m})")
        else:
            silent.append(role)
            gap = f"  ⛔ and MENTIONED in {m} — a mention-counter would call this active" if m else ""
            print(f"  ⚠ SILENT       {role:10} (mentioned in {m}){gap}")
    print(f"\n  unsigned in window: {unsigned} of {n}")
    print(f"⚠ SILENT MEANS ONLY 'no SIGNED artifact in this window'. With {unsigned} of {n} "
          f"comments carrying\n   no signature at all, a role that worked and did not sign is "
          f"invisible here. It is NOT evidence\n   of doing nothing, and must never be quoted as "
          f"such.")
    print("⚠ Complementary to tools/fleet-state.py, not a replacement: that reads TRANSCRIPTS "
          "and is blind\n   to a running pane that writes no STATE line; this reads ARTIFACTS "
          "and is blind to unsigned work.")
    if not silent:
        result("CLEAN")
        return 0
    result("FINDINGS")
    return 1


def _minus_24h(iso):
    import datetime
    t = datetime.datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ") - datetime.timedelta(hours=24)
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def normalise(iso):
    """Any ISO instant -> the exact `...Z` form the comparison needs, or None.

    ⛔ tally() compares timestamps as STRINGS, which is correct only when every string
    is in one form. `--since 2026-09-07T11:00:00+01:00` IS 10:00Z, but lexically it sorts
    after `2026-09-07T10:30:00Z` and would silently drop a comment inside the window.
    ⇒ An offset is not a formatting variation here; it is a different number."""
    import datetime
    txt = iso.strip()
    try:
        t = datetime.datetime.fromisoformat(txt.replace("Z", "+00:00"))
    except ValueError:
        return None
    if t.tzinfo is None:
        t = t.replace(tzinfo=datetime.timezone.utc)
    return t.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def self_test():
    """⛔ Two-sided, and the known-NEGATIVE is the real 2026-09-07 ARCHITECT case:
    13 mentions, 0 signatures. A mention-counter passes a suite of authors; only a
    comment that MENTIONS a role it did not write separates the two."""
    if not __debug__:
        print("⛔ ESTABLISHED NOTHING — run without -O. Assertions are this suite.")
        return 2

    cases = [
        ("✅ KNOWN-POSITIVE  a session byline in the tail",
         "Some finding.\n\nTEAMLEAD, session `15b69750`, nForma-NEXT, 2026-09-07", "TEAMLEAD"),

        ("⛔ KNOWN-NEGATIVE  the real ARCHITECT case: mentioned throughout, signed by another",
         "ARCHITECT's §1 table is right about downstream and too kind about here. ARCHITECT\n"
         "measured this on 2026-09-06 and ARCHITECT is the estate it describes.\n\n"
         "TEAMLEAD, session `15b69750`, nForma-NEXT, 2026-09-07", "TEAMLEAD"),

        ("✅ an explicit byline STARTING A TAIL LINE",
         "more text\n\n---\n*Filed by DX. The retraction-legibility half is the second read.*",
         "DX"),

        ("✅ REAL CASE (#580): `Replicated by` is as performative as `Filed by`",
         "body\n\n---\nReplicated by TEAMLEAD, session `15b69750`, nForma-NEXT, 2026-09-06",
         "TEAMLEAD"),

        ("✅ REAL CASE (#287): `Verified by`, and the role is NOT the first token",
         "body\n\n---\nVerified by TEAMLEAD, session `15b69750` — the successor named at `:180`",
         "TEAMLEAD"),

        ("✅ a bare role token starting the last line",
         "a measurement\n\nDEVOPS", "DEVOPS"),

        ("⚠ no signature at all — must be None, never guessed from content",
         "This concerns DEVOPS and DEV3 and the DX prompt. No byline anywhere.", None),

        ("⛔ CONTROL a role named ONLY in the first line does not sign the comment",
         "DEV4 raised this last week.\n\nbody\n\nbody\n\nbody\n\nbody", None),

        ("✅ a blockquoted signature still counts — the tail regex allows `>` and emphasis",
         "text\n\n> *TEAMLEAD, session `abc`*", "TEAMLEAD"),
        ("⛔ CONTROL an un-anchored `ROLE, session` mid-tail is a MENTION, not a signature",
         "text\n\nAs ARCHITECT, session `abc`, measured it — but I am not ARCHITECT.\n"
         "TEAMLEAD, session `15b69750`", "TEAMLEAD"),

        ("⛔ CONTROL `measured by DEVOPS` reports an action; it does not claim authorship",
         "This was measured by DEVOPS last week.\n\nplain body line", None),

        ("✅ `Appended by DEV2` IS a performative byline and still counts",
         "Appended by DEV2, session `abc`, 2026-09-07.\n\nbody", "DEV2"),
    ]
    ok = True
    for label, body, want in cases:
        got = author(body)
        good = got == want
        ok &= good
        print(f"{'✅' if good else '❌'} {label}\n     want {want!r} got {got!r}")

    _extra = 0
    # ⛔ The whole point, as one assertion: mentions and signatures must DISAGREE on the
    # real case. A tool where they agree has not separated them.
    _extra += 1
    body = cases[1][1]
    good = author(body) == "TEAMLEAD" and "ARCHITECT" in mentions(body)
    ok &= good
    print(f"{'✅' if good else '❌'} ⛔ CONTROL mention and signature DISAGREE on the same "
          f"comment — signed={author(body)!r}, mentions ARCHITECT={'ARCHITECT' in mentions(body)}")

    _extra += 1
    rows = [("2026-09-07T10:00:00Z", "issue", 1, cases[1][1]),
            ("2026-09-05T10:00:00Z", "issue", 2, cases[0][1])]
    s, m, u, n = tally(rows, "2026-09-06T00:00:00Z")
    good = (n == 1 and s["TEAMLEAD"] == 1 and m["ARCHITECT"] == 1 and u == 0)
    ok &= good
    print(f"{'✅' if good else '❌'} ✅ CONTROL the window EXCLUDES an older comment — "
          f"n={n} (want 1), signed TEAMLEAD={s['TEAMLEAD']}, mentioned ARCHITECT={m['ARCHITECT']}")

    _extra += 1
    s2, _, u2, n2 = tally(rows, "2030-01-01T00:00:00Z")
    good = (n2 == 0 and u2 == 0 and sum(s2.values()) == 0)
    ok &= good
    print(f"{'✅' if good else '❌'} ⛔ CONTROL an EMPTY window yields zero of everything, so "
          f"the caller reports VOID rather than a silent fleet — n={n2}")

    _extra += 1
    good = _minus_24h("2026-09-07T16:00:00Z") == "2026-09-06T16:00:00Z"
    ok &= good
    print(f"{'✅' if good else '❌'} ✅ CONTROL the window is anchored to the DATA, not the "
          f"clock — got {_minus_24h('2026-09-07T16:00:00Z')}")

    _extra += 1
    good = (normalise("2026-09-07T11:00:00+01:00") == "2026-09-07T10:00:00Z"
            and normalise("2026-09-07T10:00:00Z") == "2026-09-07T10:00:00Z"
            and normalise("not a date") is None)
    ok &= good
    print(f"{'✅' if good else '❌'} ⛔ CONTROL an OFFSET instant normalises to Z before the "
          f"string compare — +01:00 11:00 → {normalise('2026-09-07T11:00:00+01:00')}, "
          f"junk → {normalise('not a date')}")

    n = len(cases) + _extra
    print(f"\n{'all ' + str(n) + ' checks passed' if ok else 'FAILED'}")
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(guard("fleet-output", main))
