#!/usr/bin/env python3
"""Did the fleet ANNOUNCE its transitions, or only declare them?

The STATE line (`tools/fleet-state.py`) is the **pull** leg: every turn ends with one, and a
monitor reads it. It works exactly as well as the monitor's polling — an agent that goes FREE
one second after a sweep is invisible until the next one.

The role prompts now also require a **push**: on TRANSITION into FREE or BLOCKED, send TEAMLEAD
one message. This tool is that rule's execution record.

⛔ Built at the same time as the rule, deliberately. `prompts/README.md` names the defect this
avoids: "a rule here asks a reader to check something mechanical, [so] the rule is a **check
with no execution record**: its compliance is unobservable, so its violation rate is
unmeasurable." Nine of nine bootstraps carried such a step. A tenth was not worth adding.

★ THE TWO DIRECTIONS ARE NOT EQUALLY STRONG, and reading a column as though they were is the
way to misuse this.

  MISSED    strong.  The window from your previous declaration to this one contains no
                     SendMessage at all. You cannot have announced this transition through
                     this channel, because you sent nothing through it.
  notified  WEAK.    A message exists in the window. It may have been about something else
                     entirely. This tool cannot read intent, and does not pretend to.

⇒ Use it to find OMISSIONS. Do not quote the notified count as a compliance rate.

⚠ SendMessage is not the only way to reach TEAMLEAD — a pane can be spoken to directly, and
the operator relays. A MISSED row is therefore a CANDIDATE, not a finding: it says this
channel was silent, not that TEAMLEAD was uninformed. Verify one before reporting many.

Exit: 0 audited · 2 the control failed — the run established nothing.
"""
import argparse, glob, importlib.util, json, os, sys, time

# ⛔ IMPORTED, not re-implemented. `fleet-state.py` owns the positional STATE parser and the
# roster it recognises. A second copy of a rule this fleet has already got wrong once — the
# keyword-vs-positional distinction — would drift, and the two readings would then be used
# as corroboration of each other. One parser, one place to fix.
_TOOLS = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("fleet_state", os.path.join(_TOOLS, "fleet-state.py"))
fleet_state = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fleet_state)

sys.path.insert(0, _TOOLS)
from runmarker import guard, result  # noqa: E402

STATE_RE = fleet_state.STATE_RE
declared_state = fleet_state.declared_state
FLEET_ROLES = fleet_state.FLEET_ROLES

ANNOUNCE = ("FREE", "BLOCKED")


def scan(path):
    """Walk one transcript ONCE, keeping line numbers so declarations and sends are ordered.

    Returns (names, decls, sends) where
      decls = [(line_no, state, detail)]  — positional STATE lines, in order
      sends = [(line_no, recipient)]      — SendMessage tool calls, in order

    ⚠ Both lists are keyed by LINE NUMBER, not by turn index. A turn is several records and a
    tool call is not in the same record as the text that follows it, so "same turn" is not a
    thing this file can answer. Line order is, and it is what the window below is built on.
    """
    names, decls, sends = [], [], []
    for ln, line in enumerate(open(path, errors="replace")):
        if '"custom-title"' in line or '"agent-name"' in line:
            try:
                rec = json.loads(line)
            except Exception:
                continue
            n = rec.get("customTitle") or rec.get("agentName")
            if n and n not in names:
                names.append(n)
            continue
        if '"assistant"' not in line:
            continue
        try:
            rec = json.loads(line)
        except Exception:
            continue
        msg = rec.get("message") or {}
        if msg.get("role") != "assistant":
            continue
        content = msg.get("content")
        if not isinstance(content, list):
            continue
        for b in content:
            if not isinstance(b, dict):
                continue
            if b.get("type") == "tool_use" and b.get("name") == "SendMessage":
                inp = b.get("input") or {}
                sends.append((ln, str(inp.get("to") or inp.get("recipient") or "?")))
        blocks = [b.get("text", "") for b in content
                  if isinstance(b, dict) and b.get("type") == "text" and b.get("text", "").strip()]
        if blocks:
            state, detail = declared_state("\n".join(blocks))
            if state:
                decls.append((ln, state, detail))
    return names, decls, sends


def transitions(decls):
    """Declarations whose state DIFFERS from the previous declaration.

    ⛔ The prompt rule is "send on TRANSITION", and the reason is a measured one: an agent that
    messages on every FREE turn sends one per wake, and a channel that carries a message per
    wake is a channel TEAMLEAD stops reading. Repeats are therefore not violations — they are
    the rule working, and they must not appear as rows.

    The FIRST declaration in a file is a transition (from unknown). It is marked, because a
    session's opening state is not something the agent chose to move to.
    """
    out, prev = [], None
    for i, (ln, state, detail) in enumerate(decls):
        if state != prev:
            out.append({"line": ln, "state": state, "detail": detail,
                        "first": i == 0, "prev": prev,
                        "since": decls[i - 1][0] if i else -1})
        prev = state
    return out


def audit(decls, sends):
    """Pair each announceable transition with the sends in (previous declaration, this one].

    The window opens at the PREVIOUS declaration rather than at the file start, so a message
    sent long ago cannot excuse a transition made now.
    """
    rows = []
    for t in transitions(decls):
        if t["state"] not in ANNOUNCE:
            continue
        hit = [(ln, to) for ln, to in sends if t["since"] < ln <= t["line"]]
        rows.append({**t, "sends": hit})
    return rows


def main():
    # ⛔ The asymmetry belongs in --help, not only in the docstring and the PR. The person
    # who quotes the notified count as a compliance rate is, by construction, someone who
    # did not read either of those. Ratified by TEAMLEAD 2026-08-20.
    ap = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        epilog=(
            "MISSED is strong (nothing was sent, so this channel cannot have carried it); "
            "notified is WEAK (a message exists; intent is unreadable). "
            "It finds omissions. It is not a compliance rate and must not be quoted as one. "
            "A MISSED row is a CANDIDATE: a pane can also be spoken to directly."),
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--active-hours", type=float, default=6.0)
    ap.add_argument("--missed-only", action="store_true",
                    help="print only transitions this channel carried nothing for")
    args = ap.parse_args()

    sessions = []
    for proj in glob.glob(os.path.expanduser("~/.claude/projects/*")):
        for path in glob.glob(os.path.join(proj, "*.jsonl")):
            try:
                if time.time() - os.path.getmtime(path) > args.active_hours * 3600:
                    continue
            except OSError:
                continue
            names, decls, sends = scan(path)
            if not any(n in FLEET_ROLES for n in names):
                continue
            sessions.append({"session": os.path.basename(path)[:8], "names": names,
                             "decls": decls, "sends": sends,
                             "rows": audit(decls, sends)})

    if not sessions:
        print("⛔ CONTROL FAILED — no fleet session matched. This is a reading about the "
              "SEARCH, not about the fleet: VOID, not 'nobody transitioned'.", file=sys.stderr)
        result("ESTABLISHED-NOTHING")
        return 2

    # ★ Control 1 — the declaration parser. Borrowed from fleet-state.py, for the same reason:
    # this tool is run BY an agent required to declare, so a fleet-wide zero is the parser.
    if not any(s["decls"] for s in sessions):
        print("⛔ CONTROL FAILED — not one session carries a parseable STATE line. Every "
              "'no transition' below is then a fact about this parser. VOID.", file=sys.stderr)
        result("ESTABLISHED-NOTHING")
        return 2

    # ★ Control 2 — the notification DETECTOR, which has its own way of reading zero. If no
    # session in the population ever called SendMessage, "0 notified" is indistinguishable
    # from a detector that cannot fire, and a clean zero is the signature of exactly that.
    total_sends = sum(len(s["sends"]) for s in sessions)
    detector_live = total_sends > 0

    for s in sorted(sessions, key=lambda s: -len(s["rows"])):
        who = "/".join(s["names"])[:24] or "(unnamed)"
        if not s["decls"]:
            print(f"{s['session']:<10}{who:<25}UNDECIDED — declares no STATE; not auditable")
            continue
        if not s["rows"]:
            print(f"{s['session']:<10}{who:<25}no FREE/BLOCKED transition in "
                  f"{len(s['decls'])} declarations")
            continue
        for r in s["rows"]:
            if r["sends"]:
                if args.missed_only:
                    continue
                to = ",".join(sorted({t for _, t in r["sends"]}))[:18]
                mark = f"notified? {len(r['sends'])} msg → {to}"
            else:
                mark = "⛔ MISSED — this channel carried nothing"
            frm = r["prev"] or "start"
            print(f"{s['session']:<10}{who:<25}{frm} → {r['state']:<8}{mark}")

    n_rows = sum(len(s["rows"]) for s in sessions)
    n_missed = sum(1 for s in sessions for r in s["rows"] if not r["sends"])
    undecided = sum(1 for s in sessions if not s["decls"])

    print(f"\n{len(sessions)} fleet sessions · {n_rows} announceable transitions · "
          f"{n_missed} carried nothing · {undecided} undecided (no STATE at all).",
          file=sys.stderr)
    if not detector_live:
        print("⚠ DETECTOR NOT PROVEN — zero SendMessage calls anywhere in this population, so "
              "the MISSED column cannot be distinguished from a detector that never fires. "
              "Read the count as VOID, not as total non-compliance.", file=sys.stderr)
    else:
        print(f"✓ detector live — {total_sends} SendMessage calls seen, so a MISSED row means "
              "silence in the window and not a blind instrument.", file=sys.stderr)
    print("⚠ MISSED rows are CANDIDATES: this channel was silent, which is not the same as "
          "TEAMLEAD being uninformed. Verify one before reporting many.", file=sys.stderr)
    # ⚠ OK even when rows are MISSED. This tool reports; the exit code says the audit RAN,
    # not that the fleet complied. Overloading it would make a real omission look like a
    # broken instrument, which is the collision `runmarker` exists to prevent.
    result("OK")
    return 0


if __name__ == "__main__":
    sys.exit(guard("transition-report", main))
