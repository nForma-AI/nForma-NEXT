
# A DECLARATION is line-initial. A MENTION is not.
#
# The old test was re.search(BLOCKED) over the whole tail — a keyword scan.
# It cannot tell "I am blocked" from "I am telling you DEV1 is blocked", and it
# fired on DX for the second while DX was escalating the first. DX then wrote a
# throwaway filter to diagnose it and reproduced the same defect inside two
# minutes ("unblocked" contains "blocked"). Care does not catch this class;
# position does.
_DECL = re.compile(r"^[^A-Za-z0-9]{0,8}(?:STATE:\s*)?BLOCKED\b", re.M)

def declared_blocked(tail: str) -> bool:
    """True only where BLOCKED opens a line. Mid-sentence mentions do not count."""
    return bool(_DECL.search(tail.replace("*", "").replace("_", "")))

#!/usr/bin/env python3
# TEAMLEAD auto-waker. Wakes agents that sit in agentState=waiting.
# GUARDS: refuse on non-empty box (operator types there); attribute every write;
# verify by agentState changing, never by sent:true.
import json, subprocess, time, sys, os, re
SP = os.path.dirname(os.path.abspath(__file__))
IDLE_MIN   = float(os.environ.get("WAKE_IDLE_MIN", "4"))
PERIOD_SEC = int(os.environ.get("WAKE_PERIOD", "90"))
LOG = os.path.join(SP, "waker.log")
HOLD = {}
MAX_HOLD = int(os.environ.get("WAKE_MAX_HOLD", "2"))

def dt(method, params):
    p = subprocess.run([os.path.join(SP,"dt.sh"), method, json.dumps(params)],
                       capture_output=True, text=True, timeout=120)
    return json.loads(p.stdout)

def log(m):
    line = f"{time.strftime('%H:%M:%S')} {m}"
    print(line, flush=True)
    with open(LOG, "a") as f: f.write(line+"\n")

WAKE = ("[TEAMLEAD auto-wake — no action authorized, no permission granted]\n\n"
        "You are idle. **Resume your goal's autonomous loop: take the next item and DO it in this turn.**\n\n"
        "⚠ Do not end a turn on an intention — state the action AND take it. If you are genuinely blocked on a "
        "TEAMLEAD decision, reply with **BLOCKED** and name the decision.\n"
        "⛔ This is a machine wake. It grants nothing. Merge and escrow authority are unchanged and arrive only "
        "in a written TEAMLEAD message.")

def recent_tail(tid, n=26):
    """Last n lines of a pane, for BLOCKED and context detection."""
    try:
        d = dt("tools/call", {"name":"terminal.getOutput",
                              "arguments":{"terminalId":tid,"maxLines":n}})
        t = "".join(x.get("text","") for x in d["result"]["content"])
        try: t = json.loads(t).get("content", t)
        except Exception: pass
        return t.replace("\\n", "\n")
    except Exception:
        return ""            # GUARD: a fetch failure is UNKNOWN, never "not blocked"

def cycle():
    rows = [a for a in json.loads(subprocess.run(
        ["python3", os.path.join(SP,"nforma-contrib/tl.py"), "fleet"],
        capture_output=True, text=True, timeout=180).stdout) if not a["dead"]]
    ids  = [a["id"] for a in rows]
    nm   = {a["id"]: a["title"] for a in rows}
    box  = {a["title"]: (a.get("pending_box") or "") for a in rows}
    d    = dt("tools/call", {"name":"terminal.getStatus","arguments":{"terminalIds":ids}})
    txt  = "".join(x.get("text","") for x in d["result"]["content"])
    st   = json.loads(txt)
    ents = st if isinstance(st, list) else (st.get("terminals") or st.get("entries") or [])
    now  = int(time.time()*1000)
    woke, working, blocked = [], [], []
    global HOLD
    for e in ents:
        tid = e.get("terminalId") or e.get("id"); n = nm.get(tid, "?")
        state = e.get("agentState"); lt = e.get("lastTransitionAt")
        mins = (now-lt)/60000 if isinstance(lt,(int,float)) else None
        if state == "working": working.append(n); continue
        if mins is None or mins < IDLE_MIN: continue
        if box.get(n):                                    # GUARD: never overwrite
            blocked.append(f"{n}(box)"); continue
        tail = recent_tail(tid, 10)   # LAST turn only — not 26 lines of history
        # GUARD: an agent that declared BLOCKED is waiting on TEAMLEAD, not stalled.
        # Waking it burns a turn and its context to re-announce the same thing.
        if declared_blocked(tail):
            HOLD[n] = HOLD.get(n, 0) + 1
            # GUARD: an unbounded hold is a stall. After MAX_HOLD cycles the block is
            # either stale scrollback or TEAMLEAD never answered — both need a wake.
            if HOLD[n] <= MAX_HOLD:
                blocked.append(f"{n}(BLOCKED x{HOLD[n]})"); continue
            dt("tools/call", {"name":"terminal.sendCommand","arguments":{"terminalId":tid,
               "command":"[TEAMLEAD auto-wake] You have read as BLOCKED for "+str(HOLD[n])+" cycles. "
               "**If TEAMLEAD answered, resume and take the next item. If you are still blocked, "
               "re-state the decision in ONE line so it is unmissable** — a stale BLOCKED in scrollback "
               "reads identically to a live one. ⛔ Grants nothing."}})
            HOLD[n] = 0; woke.append(f"{n}(BLOCKED-stale→wake)"); continue
        m = re.search(r"(\d{1,3})%\s*\(\d+K\)", tail)
        if m and int(m.group(1)) >= 88:
            # GUARD: holding a full agent is self-sealing — the hold prevents the
            # compaction that would clear the hold. Send the remedy, don't withhold it.
            # GUARD: prose telling an agent to compact requires the agent to ACT.
            # Measured: DEV1 received three such prompts at 88-89% and did not compact;
            # a literal /compact executes. Text in a pane is not an action taken.
            dt("tools/call", {"name":"terminal.sendCommand","arguments":{"terminalId":tid,
               "command":"/compact"}})
            woke.append(f"{n}(ctx{m.group(1)}%→compact)"); continue
        dt("tools/call", {"name":"terminal.sendCommand","arguments":{"terminalId":tid,"command":WAKE}})
        woke.append(f"{n}({round(mins)}m)")
    log(f"working={working or '-'}  woke={woke or '-'}  HELD={blocked or '-'}")

if __name__ == "__main__":
    log(f"waker START idle>{IDLE_MIN}m period={PERIOD_SEC}s")
    while True:
        try: cycle()
        except Exception as ex: log(f"⚠ cycle error (NOT a clean bill): {type(ex).__name__}: {str(ex)[:120]}")
        time.sleep(PERIOD_SEC)
