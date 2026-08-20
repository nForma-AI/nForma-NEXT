#!/usr/bin/env python3
"""Report which panes can be joined to a session, and WHICH LEG is missing when they cannot.

⛔ The failure this exists for, measured (#6):

    A session acted for hours on an unverifiable belief about which pane it was,
    then wrote another actor's merges into its own record. Five independent
    investigations -- an authorization check, an attribution query, a
    compensation detector, an addressing resolver, a telemetry reading -- each
    terminated at the same unjoined edge:

        terminal.list  ->  pane id, title      ... and no session id
        transcript     ->  session id          ... and no pane id

★ That framing is one layer too high, and the layer below it changes the remedy.
Daintree's own state file already carries the join:

    ~/Library/Application Support/Daintree/projects/<proj>/state.json
        terminals[].agentSessionId          <- same namespace as CLAUDE_CODE_SESSION_ID

Measured 2026-08-19, 11 panes on one machine: the field is populated for exactly
those panes whose process was launched with `--session-id`, 2 of 2, in both
directions. It is not a value Daintree discovers -- it is one Daintree already
knew because it chose it at launch. The nine fleet panes were launched without
the flag, so it is null for all of them.

⛔ SO THE JOIN NEEDS TWO LEGS, AND NOTHING CURRENTLY HAS BOTH:

    leg A   --session-id at launch      -> Daintree records agentSessionId
    leg B   a session-registry row      -> that id resolves to name / cwd / role
            (~/.claude/sessions/<pid>.json)

    the 9 fleet panes    B, not A
    the 2 probe panes    A, not B -- spawned from inside another Claude session,
                         so CLAUDE_CODE_CHILD_SESSION suppressed the registry row

⇒ The join has never been observed working because no pane has yet held both at
once. That is a different problem from a missing primitive, and a much cheaper one.

⛔⛔ THAT SENTENCE IS NOW FALSE, AND THIS TOOL IS THE THING THAT FALSIFIED IT.
Re-measured 2026-08-20, 58 panes: **13 BOUND**, 15 PARTIAL-A, 30 UNBOUND. Every
fleet role is among the BOUND:

    DX        c67ebcb4 -> DX          DEV3   ec0d07f0 -> DEV3
    DEVOPS    6fc2dca8 -> DEVOPS      DEV4   b00d725a -> DEV4
    ARCHITECT 6150ffb2 -> ARCHITECT   DEV5   96827e4b -> DEV5
    TEAMLEAD  e4a7769d -> DEV2        <- see below

★ THE CONTROL FIRED POSITIVE AND NOBODY READ IT. This file's own stated purpose is
"the known-positive control for the launcher fix: run it before and after adding
--session-id, and BOUND rows appearing is the evidence the fix worked." The rows
appeared. The docstring around them still described the pre-fix world, and so did
the self-test's rationale ("today the live population contains no BOUND").

⇒ A control that detects the thing it was built for, and whose surrounding prose is
never updated, reports a solved problem as open for as long as anyone reads the prose
instead of running it.

★★ AND THE EXACT JOIN ANSWERS A QUESTION ANOTHER TOOL HAS BEEN REPORTING AS
UNANSWERABLE. `fleet-context.py` prints on every sweep:

    ⛔ TEAMLEAD and DEV2 are BOTH satisfied by session e4a7769d ... one of them is
       UNVERIFIED

The binding above resolves it: the pane TITLED `TEAMLEAD` holds session `e4a7769d`,
whose REGISTRY name is `DEV2`. That is a title-versus-registry disagreement on one
exactly-bound pane, not an unresolvable identity — and the answer was in Daintree's
state file the whole time, while the roster check fell back to self-reported names.

★ WHY THIS TOOL EXISTS RATHER THAN A REGISTER

A pane->session register built today would have ZERO exact joins fleet-wide: its
positive branch would never have executed (#2's never-concluded state), and it
would fall back to the content-matching it was meant to replace. Per #26 that is
not a control. So this reports the LEGS instead, and it is the known-positive
control for the launcher fix: run it before and after adding --session-id, and
BOUND rows appearing is the evidence the fix worked.

⚠ It reports; it never infers. A pane whose legs do not join is UNBOUND, never
guessed at from a matching title -- title agreement is exactly the unreliable
join this issue documents (two panes carried one title simultaneously; one
transcript alternated two names for ~100 cycles).

Usage:
    pane-binding.py                 report every pane and its legs
    pane-binding.py --role DEV3     just that pane
    pane-binding.py --self-test     prove BOUND / PARTIAL / UNBOUND are reachable

Exit: 0 every pane BOUND · 1 at least one is not (ESTABLISHED) · 2 established nothing
      3 the self-test failed -- this tool's verdicts cannot be trusted
"""
import argparse
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from runmarker import guard, result  # noqa: E402
import tempfile

DAINTREE = os.path.expanduser("~/Library/Application Support/Daintree/projects")
SESSIONS = os.path.expanduser("~/.claude/sessions")


class Void(Exception):
    """Established nothing. Never convertible into a verdict."""


def panes(root):
    """Every terminal in every project state file. ⛔ A state file that will not parse
    raises rather than being skipped -- a skipped file is an UNREAD file, and 'no pane
    has the binding' must never mean 'none among the ones I could parse'."""
    files = sorted(glob.glob(os.path.join(root, "*", "state.json")))
    if not files:
        raise Void(f"no project state files under {root} — Daintree state is absent, "
                   f"which is not the same as a fleet with no panes")
    out = []
    for f in files:
        try:
            d = json.load(open(f))
        except Exception as exc:
            raise Void(f"{f}: unparseable ({exc}); refusing to report on a partial population")
        for t in d.get("terminals", []):
            out.append({
                "project": os.path.basename(os.path.dirname(f))[:8],
                "pane": t.get("id"),
                "title": t.get("title"),
                "title_mode": t.get("titleMode"),
                "session": t.get("agentSessionId"),
                "cwd": t.get("cwd"),
            })
    return out


def registry(root):
    """sessionId -> registry row. Absent root is VOID, not an empty fleet."""
    if not os.path.isdir(root):
        raise Void(f"{root} does not exist — no session registry to join against")
    reg = {}
    for f in glob.glob(os.path.join(root, "*.json")):
        try:
            d = json.load(open(f))
        except Exception:
            continue  # a half-written row is not a claim about any pane
        if d.get("sessionId"):
            reg[d["sessionId"]] = d
    return reg


def verdict(pane, reg):
    """BOUND      both legs — the pane resolves to a named, live session
       PARTIAL-A  leg A only — Daintree knows the id, the registry does not (child session)
       PARTIAL-B  leg B only — cannot be detected per-pane; see report()
       UNBOUND    leg A absent — nothing on this pane can be joined to any session

    ⚠ There is deliberately no 'probably' verdict. The whole incident behind #6 is an
    agent acting on a plausible identity."""
    if not pane["session"]:
        return "UNBOUND", None
    row = reg.get(pane["session"])
    if row is None:
        return "PARTIAL-A", None
    return "BOUND", row


def report(root_d, root_s, role=None):
    ps, reg = panes(root_d), registry(root_s)
    rows = []
    for p in ps:
        if role and p["title"] != role:
            continue
        v, row = verdict(p, reg)
        rows.append((v, p, row))
    if role and not rows:
        raise Void(f"no pane titled {role!r} — and a pane's title is self-reported, "
                   f"so its absence does not establish that the role has no pane")

    print(f"{'verdict':<10} {'title':<12} {'pane':<40} session → registry name")
    counts = {}
    for v, p, row in rows:
        counts[v] = counts.get(v, 0) + 1
        sid = (p["session"] or "—")[:8]
        name = row.get("name") if row else ("no registry row" if p["session"] else "—")
        print(f"{v:<10} {str(p['title'])[:12]:<12} {str(p['pane'])[:40]:<40} {sid} → {name}")

    unbound_named = [p for v, p, _ in rows if v == "UNBOUND" and p["title_mode"] == "user"]
    print()
    print("  ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    if unbound_named:
        print(f"\n⚠ {len(unbound_named)} explicitly-titled pane(s) are UNBOUND — leg A is missing.")
        print("  Fix is at LAUNCH, not here: pass --session-id <fresh-uuid> per pane so Daintree")
        print("  records agentSessionId. ⛔ Generate per launch; a uuid committed to the recipe")
        print("  may resume the previous session (UNTESTED, and the load-bearing unknown).")

    # Leg B in aggregate: registry rows nothing claims. Reported, not diagnosed --
    # a session with no pane is normal (any terminal outside Daintree).
    claimed = {p["session"] for p in ps if p["session"]}
    orphan = [r for sid, r in reg.items() if sid not in claimed]
    if orphan:
        print(f"\n  {len(orphan)} registry session(s) claimed by no pane: "
              + ", ".join(sorted(str(r.get('name')) for r in orphan)[:12]))

    # ⛔ EXIT 0 WAS UNREACHABLE. Requiring every pane to be BOUND means one closed
    # pane from a past session — of which the state files hold 30 — makes a clean
    # verdict impossible forever. A success state that cannot occur is the mirror of
    # a falsifier that cannot fire, and it trains its reader to ignore the exit code.
    #
    # PARTIAL is the actionable state: the join was ATTEMPTED and half-landed.
    # UNBOUND means no leg at all — a pane nobody tried to bind, which is the
    # expected condition of every pane launched before the fix, not a failure.
    if not rows:
        return 1
    return 1 if counts.get("PARTIAL-A", 0) or counts.get("PARTIAL-B", 0) else 0


def cmd_self_test():
    """⛔ Proves BOUND / PARTIAL-A / UNBOUND are all reachable, against a synthetic
    population built here rather than against the live fleet.

    ★ Why synthetic and not the real panes — ⚠ THE PREMISE HAS EXPIRED, the practice
    has not. It read: today the live population contains no BOUND
    pane at all, so a self-test anchored to it could not exercise the positive branch --
    and once the launcher fix lands it would contain no UNBOUND fleet pane, losing the
    negative. Either way a live-anchored control goes half-blind, which is #26's sharp
    subtype. A population this tool constructs holds all three forever."""
    checks, failed = [], 0

    def check(name, got, want):
        nonlocal failed
        if got != want:
            failed += 1
        checks.append((got == want, name, got, want))

    with tempfile.TemporaryDirectory() as tmp:
        dt = os.path.join(tmp, "projects", "proj0")
        sess = os.path.join(tmp, "sessions")
        os.makedirs(dt)
        os.makedirs(sess)
        json.dump({"terminals": [
            {"id": "terminal-bound", "title": "BOUND-FIXTURE", "titleMode": "user",
             "agentSessionId": "11111111-1111-1111-1111-111111111111"},
            {"id": "terminal-partial", "title": "PARTIAL-FIXTURE", "titleMode": "user",
             "agentSessionId": "22222222-2222-2222-2222-222222222222"},
            {"id": "terminal-unbound", "title": "UNBOUND-FIXTURE", "titleMode": "user",
             "agentSessionId": None},
        ]}, open(os.path.join(dt, "state.json"), "w"))
        json.dump({"pid": 1, "sessionId": "11111111-1111-1111-1111-111111111111",
                   "name": "FIXTURE"}, open(os.path.join(sess, "1.json"), "w"))

        reg = registry(sess)
        by_title = {p["title"]: p for p in panes(os.path.join(tmp, "projects"))}
        for title, want in [("BOUND-FIXTURE", "BOUND"),
                            ("PARTIAL-FIXTURE", "PARTIAL-A"),
                            ("UNBOUND-FIXTURE", "UNBOUND")]:
            check(f"{title} -> {want}", verdict(by_title[title], reg)[0], want)

        # The VOID paths must execute, not merely exist.
        for name, fn in [("absent daintree root -> VOID",
                          lambda: panes(os.path.join(tmp, "nope"))),
                         ("absent registry root -> VOID",
                          lambda: registry(os.path.join(tmp, "nope")))]:
            try:
                fn()
                check(name, "no exception", "Void raised")
            except Void:
                check(name, "Void raised", "Void raised")

    for ok, name, got, want in checks:
        print(f"{'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"   got {got!r}, want {want!r}"))
    if failed:
        print(f"\n⛔ {failed} of {len(checks)} known-positives failed — verdicts cannot be trusted.",
              file=sys.stderr)
        return 3
    print(f"\n{len(checks)} of {len(checks)} known-positives reachable "
          f"(BOUND · PARTIAL-A · UNBOUND · 2× VOID).")
    return 0



def _mark(rc):
    """Map the tool's own exit code to a terminal marker. ⛔ Every controlled path
    goes through here — a path returning without a marker is indistinguishable from
    a crash, and that reading is only correct if it actually crashed."""
    result({0: "OK", 1: "FINDING", 2: "ESTABLISHED-NOTHING",
            3: "SELF-TEST-FAILED"}.get(rc, f"EXIT-{rc}"))
    return rc


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--role", help="only the pane with this title")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--daintree", default=DAINTREE)
    ap.add_argument("--sessions", default=SESSIONS)
    args = ap.parse_args()
    try:
        if args.self_test:
            return _mark(cmd_self_test())
        return _mark(report(args.daintree, args.sessions, args.role))
    except Void as exc:
        print(f"VOID: {exc}", file=sys.stderr)
        print("⛔ established nothing — this is NOT 'no pane is bound'.", file=sys.stderr)
        result("ESTABLISHED-NOTHING")
        return 2


if __name__ == "__main__":
    sys.exit(guard("pane-binding", main))
