#!/usr/bin/env python3
"""Read the STATE line every agent is required to declare.

⛔ Why this exists, and it is a self-correction. The role prompts were amended to require
that every turn END with:

    STATE: WORKING — <what you are mid-way through>
    STATE: FREE — <nothing queued; what you would take next>
    STATE: BLOCKED — <the decision you need, and from whom>

**And nothing consumed it.** A signal was demanded with no reader built, which is the same
defect measured independently on a watchdog the same afternoon: it demanded "reply BLOCKED
and name the decision", nothing read the reply, and the agent that complied was re-woken
seven times — 88% to 93% context — with its named blockers unchanged and unchangeable by it.

> **A wake that cannot hear its own answer is a drain, not a nudge.**
> Demanding a signal you have not built a consumer for presents as the agent being
> unresponsive. It is the instrument being deaf.

★ Parsed POSITIONALLY — the final non-empty line of the last assistant turn — never by
searching for the token anywhere in the text. That distinction is the whole design. A
keyword scan is tripped by any turn *discussing* blockage, and this fleet produced five
instances of that inverse defect in one session, including a document about closing keywords
that contained a live one. **A quoted example is never the last line.**

Exit: 0 read cleanly · 2 the control failed — the parser established nothing.
"""
import argparse, glob, json, os, re, sys, time

STATE_RE = re.compile(r"^STATE:\s*(WORKING|FREE|BLOCKED)\b\s*[-—:]?\s*(.*)$", re.I)
FLEET_ROLES = ("TEAMLEAD", "ARCHITECT", "DEVOPS", "DX",
               "DEV1", "DEV2", "DEV3", "DEV4", "DEV5")


def _is_real_user_turn(rec):
    """Does this user RECORD end an agent turn?

    ⛔ In this harness a tool result is delivered as ``role="user"``. So the
    obvious boundary — "a record with role user" — fires once per TOOL CALL,
    which is exactly the unit that made this parser unsatisfiable.

    A record ends a turn only if it carries at least one block that is NOT a
    tool_result, or is a bare string.
    """
    msg = rec.get("message") or {}
    if msg.get("role") != "user":
        return False
    content = msg.get("content")
    if isinstance(content, str):
        return bool(content.strip())
    if isinstance(content, list):
        return any(isinstance(b, dict) and b.get("type") != "tool_result"
                   for b in content)
    return False


def assistant_texts(path):
    """EVERY non-empty assistant text turn, in order, and the names the file answers to.

    ⛔ This used to return only the LAST one, and that was a category error measured on the
    live fleet: one session had emitted **61** STATE lines, every one of them positionally
    last in its turn, and the tool reported the whole fleet as carrying none. Its most recent
    turn was mid-work — tool calls and narration — so the declaration from the turn before was
    invisible.

    **The STATE line is a per-TURN declaration. Reading only the newest turn turns it into a
    per-SESSION property that almost never holds**, because an agent that is working is, by
    definition, between reports. "Did not declare on its latest turn" and "has never declared"
    are different states and only the second is silence.
    """
    names, texts = [], []
    span = []                      # assistant texts since the last REAL user turn
    for line in open(path, errors="replace"):
        if '"custom-title"' in line or '"agent-name"' in line:
            try:
                rec = json.loads(line)
            except Exception:
                continue
            n = rec.get("customTitle") or rec.get("agentName")
            if n and n not in names:
                names.append(n)
            continue
        if '"user"' in line:
            # ⛔ A USER RECORD IS NOT A USER TURN. Tool results come back with
            # role="user", and treating them as boundaries reinstates the very
            # unit this function exists to stop counting.
            try:
                urec = json.loads(line)
            except Exception:
                continue
            if _is_real_user_turn(urec) and span:
                texts.append("\n".join(span))
                span = []
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
        blocks = [b.get("text", "") for b in content
                  if isinstance(b, dict) and b.get("type") == "text" and b.get("text", "").strip()]
        if blocks:
            span.append("\n".join(blocks))
    if span:
        texts.append("\n".join(span))
    return names, texts


def latest_declaration(texts):
    """The most recent turn that DECLARED, and how many turns back it was.

    Returns (state, detail, turns_ago); turns_ago == 0 means the latest turn declared.
    A declaration two turns old is stale, not absent — and an agent cannot be asked to
    re-declare if the instrument reports it as never having spoken.
    """
    for back, text in enumerate(reversed(texts)):
        state, detail = declared_state(text)
        if state:
            return state, detail, back
    return None, "", None


def declared_state(text):
    """Only the FINAL non-empty line counts. A mention anywhere else is prose."""
    if not text:
        return None, ""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return None, ""
    m = STATE_RE.match(lines[-1])
    if not m:
        return None, ""
    return m.group(1).upper(), m.group(2).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--active-hours", type=float, default=6.0)
    ap.add_argument("--blocked-only", action="store_true")
    args = ap.parse_args()

    rows = []
    for proj in glob.glob(os.path.expanduser("~/.claude/projects/*")):
        for path in glob.glob(os.path.join(proj, "*.jsonl")):
            if time.time() - os.path.getmtime(path) > args.active_hours * 3600:
                continue
            names, texts = assistant_texts(path)
            if not any(n in FLEET_ROLES for n in names):
                continue
            state, detail, back = latest_declaration(texts)
            rows.append({"session": os.path.basename(path)[:8],
                         "names": names, "state": state, "detail": detail,
                         "turns_ago": back, "turns": len(texts)})

    # ★ Known-positive control: this tool is invoked BY an agent required to declare, so at
    # least one session must carry a parseable STATE line. If none does, the parser is
    # broken or the prompts never landed — either way the run established nothing.
    if not any(r["state"] for r in rows):
        print("⛔ CONTROL FAILED — no session carries a parseable STATE line.\n"
              "   ADDABLE — FIXABLE BY THE PANES: the STATE line is a self-report; if none\n"
              "   parses, ask the roles to emit it rather than treating the fleet as silent.\n"
              "   Either the "
              "requirement has not reached any prompt, or this parser is broken. Both make "
              "every 'no declaration' below meaningless: VOID, not 'nobody is blocked'.",
              file=sys.stderr)
        return 2

    for r in sorted(rows, key=lambda r: (r["state"] or "zzz")):
        if args.blocked_only and r["state"] != "BLOCKED":
            continue
        label = r["state"] or "— never declared"
        mark = "  ⛔ SKIP WAKES until this state MOVES" if r["state"] == "BLOCKED" else ""
        # ⚠ Age the declaration. A BLOCKED from 40 turns ago is a claim about a
        # situation the agent has had 40 turns to change; presenting it identically to
        # one made this turn is how a stale blocker becomes a permanent one.
        if r["turns_ago"] == 0:
            age = "this turn"
        elif r["turns_ago"] is None:
            age = f"0 of {r['turns']} turns"
        else:
            age = f"{r['turns_ago']} turns ago"
        print(f"{r['session']:<10}{'/'.join(r['names'])[:26]:<27}{label:<18}"
              f"{age:<14}{r['detail'][:50]}{mark}")

    declared = sum(1 for r in rows if r["state"])
    current = sum(1 for r in rows if r["turns_ago"] == 0)
    print(f"\n{declared} of {len(rows)} fleet sessions have declared a state at all; "
          f"{current} declared on their latest turn. ⚠ Never-declared is UNKNOWN, not free — "
          f"and a declaration N turns old is a claim the agent has had N turns to invalidate.",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
