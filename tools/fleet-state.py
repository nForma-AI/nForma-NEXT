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


def last_assistant_text(path):
    """The final text emitted by the assistant, and the names the file answers to."""
    names, text = [], None
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
            text = "\n".join(blocks)
    return names, text


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
            names, text = last_assistant_text(path)
            if not any(n in FLEET_ROLES for n in names):
                continue
            state, detail = declared_state(text)
            rows.append({"session": os.path.basename(path)[:8],
                         "names": names, "state": state, "detail": detail})

    # ★ Known-positive control: this tool is invoked BY an agent required to declare, so at
    # least one session must carry a parseable STATE line. If none does, the parser is
    # broken or the prompts never landed — either way the run established nothing.
    if not any(r["state"] for r in rows):
        print("⛔ CONTROL FAILED — no session carries a parseable STATE line. Either the "
              "requirement has not reached any prompt, or this parser is broken. Both make "
              "every 'no declaration' below meaningless: VOID, not 'nobody is blocked'.",
              file=sys.stderr)
        return 2

    for r in sorted(rows, key=lambda r: (r["state"] or "zzz")):
        if args.blocked_only and r["state"] != "BLOCKED":
            continue
        label = r["state"] or "— none declared"
        mark = "  ⛔ SKIP WAKES until this state MOVES" if r["state"] == "BLOCKED" else ""
        print(f"{r['session']:<10}{'/'.join(r['names'])[:26]:<26}{label:<16}"
              f"{r['detail'][:60]}{mark}")

    declared = sum(1 for r in rows if r["state"])
    print(f"\n{declared} of {len(rows)} fleet sessions declared a state. "
          f"⚠ Undeclared is UNKNOWN, not free.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
