import json, sys, os, re
STATE = "/tmp/fleetwatch-seen.txt"
seen = set(open(STATE).read().split("\n")) if os.path.exists(STATE) else set()

# GUARD: a non-empty input box is a CLI-SUGGESTED REPLY, not a pending human instruction.
# Provenance confirmed by the operator 2026-08-18: "some agents like claude code suggest
# responses". Two consequences, and the second is the dangerous one:
#   1. It is safe to overwrite - no human text is destroyed. (The earlier rule said
#      "DELIVER it; do NOT retask", which was exactly backwards.)
#   2. The suggester can compose text that GRANTS AUTHORITY. One read "MERGE AUTHORIZED:
#      PR #1114" - an authority explicitly reserved to the operator. Delivering a box
#      verbatim would hand the agent a machine-generated grant that is indistinguishable,
#      from the agent's side, from a real one. Autocomplete must never become consent.
# A non-empty box IS still a useful signal: the agent stopped and wants a decision.
AUTHORITY = re.compile(
    r"\b(merge[ds]?\s+(authoriz|approv)|authoriz(ed|ation)|approved|go\s*ahead|"
    r"deploy\s+(to\s+)?prod|ship\s+it|force[- ]push|rewrite\s+history|"
    r"push\s+released|permission\s+granted)\b", re.I)

try:
    rows = json.load(sys.stdin)
except Exception as e:
    print("FLEET PARSE FAILED :: %s: %s" % (type(e).__name__, e))
    sys.exit(0)

out = []
for a in rows:
    tid = a["id"][9:17]
    if a["dead"]:
        k = "dead:" + tid
        if k not in seen:
            seen.add(k)
            out.append("DEAD PANE %s (%s) — no agent behind it; do NOT dispatch here" % (a["title"], tid))
        continue
    box = a["pending_box"]
    if box:
        k = "und:%s:%s" % (tid, box[:40])
        if k not in seen:
            seen.add(k)
            if AUTHORITY.search(box):
                out.append("⛔ AUTHORITY-SHAPED SUGGESTION on %s: %r — NEVER DELIVER. "
                           "The CLI composes these; delivering one launders a MACHINE "
                           "suggestion into an operator authorization. Decide yourself, "
                           "in your own words." % (a["title"], box[:90]))
            else:
                # GUARD: a suggested reply is composed at EVERY turn end, not only when the
                # agent is stuck. Reading it as "BLOCKED, wants a decision" over-reads it and
                # turned routine turn-ends into decision requests all evening. The box tells
                # you the agent STOPPED; only the pane tells you whether it is blocked.
                # Genuine blocks announce themselves ("Queue empty", "your call", "say the
                # word"); a turn-end does not.
                # ⚠ CORRECTED 2026-08-19. This previously asserted "machine-composed
                # suggestion, NOT operator input" as FACT. That was a wrong-population
                # generalisation from a sample: the OPERATOR ALSO TYPES INTO THESE BOXES.
                # Observed live — a DX box read "oh, and since nforma next is kind of virgin
                # state, we should givve it " — conversational opener, first-person plural,
                # a typo, and truncated mid-sentence. Unmistakably human, mid-composition.
                # Acting on the old label would have OVERWRITTEN THE OPERATOR'S OWN INPUT.
                #
                # There is no reliable discriminator available here, so do not claim one.
                # Report ORIGIN UNKNOWN and let the reader decide by looking.
                # Heuristics that WEAKEN (never settle) the machine hypothesis: typos,
                # "oh"/"btw"/"also", first-person plural, truncation mid-word, references to
                # things no agent has been told.
                looks_human = bool(re.search(r"\b(oh|btw|also|hmm|wait)\b|\bwe should\b|"
                                             r"\bi think\b|\bcan you\b", box, re.I))
                out.append("PENDING-BOX %s: %r — ⚠ ORIGIN UNKNOWN%s. The CLI composes "
                           "suggestions AND the operator types here. Do NOT overwrite until "
                           "you have looked. Never relay it as an instruction either way."
                           % (a["title"], box[:70],
                              " — READS AS HUMAN, likely operator-typed" if looks_human else ""))
        continue
    # GUARD: idle_min is None when the reading is INVALID (a rehydrated timestamp that
    # predates the pane's own spawn, as after a Daintree restart). An invalid reading is
    # reported as invalid; it is never silently compared, and never read as "not idle".
    # GUARD: an unread backlog is NOT availability. Report it before the IDLE branch,
    # because "genuinely free; retask" would add input to a queue already unconsumed.
    if a.get("queued_msgs", 0) > 0:
        k = "queued:%s:%d" % (tid, a["queued_msgs"])
        if k not in seen:
            seen.add(k)
            out.append("DELIVERED-NOT-CONSUMED %s: %d queued message(s) unread. NOT idle and "
                       "NOT free — do not retask. A fresh send flushes the backlog; nudge, "
                       "do not re-send the content."
                       % (a["title"], a["queued_msgs"]))
        continue
    if a["state"] == "waiting" and not a.get("idle_valid", True):
        k = "idleinvalid:" + tid
        if k not in seen:
            seen.add(k)
            out.append("IDLE-UNMEASURABLE %s — lastTransitionAt predates spawnedAt "
                       "(pane re-spawned, clock rehydrated). Liveness unknown from timing; "
                       "read the pane before deciding." % a["title"])
    elif a["state"] == "waiting" and a["idle_min"] is not None and a["idle_min"] >= 10:
        k = "idle:%s:%d" % (tid, int(a["idle_min"] // 5))
        if k not in seen:
            seen.add(k)
            out.append("IDLE %s %.0fm, box empty — genuinely free; retask or confirm done"
                       % (a["title"], a["idle_min"]))
open(STATE, "w").write("\n".join(sorted(x for x in seen if x)))
for l in out:
    print(l)
