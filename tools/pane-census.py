#!/usr/bin/env python3
"""How many panes are in this fleet — and REFUSE a number when the sources disagree.

⛔ Why this exists, measured 2026-08-20 on the pane that fell out of it.

    terminal.list           9 panes, 9 DISTINCT titles
    tools/daintree-control  9 panes
    live transcripts <30m   8

A monitor keyed on transcripts named EIGHT panes for hours and never said it was
short. The ninth — TEAMLEAD's — was alive and `working` in terminal.list while its
transcript had been silent for 573 minutes.

★ THE PANE MISSING FROM THE CENSUS WAS THE PANE RUNNING THE CENSUS. It cannot appear
in its own blind spot, so from inside, 8 read as complete. It then attributed another
pane's session id to itself, which made 8 look like 9 — the roster was short by one AND
had mislabelled the survivor, so the arithmetic never looked wrong from either side.

⇒ THE DEFECT IS NOT THE WRONG NUMBER. It is that a number was returned at all.

    A census that silently returns 8 is the defect.
    One that returns 8 and declares UNESTABLISHED is the fix.

⚠ IDENTITY KEY IS THE PANE ID, NEVER THE DISPLAY NAME. `terminal.list` is the only
source carrying `id` + `worktreeId` on every row; ListAgents carries neither, over 51
rows. The recipe assigns titles at launch and `/rename` changes them at runtime, and
nothing reconciles the two layers — today's titles are unique by luck, not by property.
Keying on the name is what makes a collision able to collapse two panes into one.

⛔ NOT A REMEDY: renaming panes. That repairs today's collision and leaves the class.

Exit: 0 sources agree, count established · 1 a divergence is NAMED · 2 established nothing
"""
import json, os, subprocess, sys, time, glob, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
STALE_MIN = 30


def _daintree():
    """Reuse daintree-control.py's transport rather than re-implement it.

    ⚠ Deliberate: transition-report.py imports fleet-state.py's parser for the same
    reason — one home for the mechanism, so two readings cannot corroborate each other
    by both being wrong in the same way."""
    p = os.path.join(HERE, "daintree-control.py")
    if not os.path.isfile(p):
        return None, f"tools/daintree-control.py not found at {p}"
    spec = importlib.util.spec_from_file_location("dc", p)
    m = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(m)
    except SystemExit:
        pass
    except Exception as exc:
        return None, f"cannot load daintree-control.py: {exc}"
    return m, None


def panes_from_daintree():
    """(list_of_rows, error). A row is {id, title}. Never an empty list on failure —
    the caller must be able to tell 'zero panes' from 'could not ask'."""
    m, err = _daintree()
    if err:
        return None, err
    try:
        url, auth = m.endpoint()          # (url, auth) — the session id is handshaked below
    except SystemExit:
        return None, "daintree-control.py refused: no MCP config or unreadable ~/.claude.json"
    except Exception as exc:
        return None, f"endpoint(): {exc}"
    if not url:
        return None, "no daintree MCP endpoint configured"
    # ⚠ The session id comes from an `initialize` handshake, not from endpoint().
    # Replicated rather than imported because daintree-control.py keeps it inline in main().
    try:
        hs = subprocess.run(
            ["curl", "-sD", "-", "-o", "/dev/null", "--max-time", "10",
             "-H", f"Authorization: {auth}",
             "-H", "Accept: application/json, text/event-stream",
             "-H", "Content-Type: application/json", "-X", "POST", url,
             "-d", json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
                 "protocolVersion": "2024-11-05", "capabilities": {},
                 "clientInfo": {"name": "pane-census", "version": "1"}}})],
            capture_output=True, text=True).stdout
    except OSError as exc:
        return None, f"cannot run curl: {exc}"
    sid = next((l.split(":", 1)[1].strip() for l in hs.splitlines()
                if l.lower().startswith("mcp-session-id:")), None)
    if not sid:
        return None, "handshake returned no session id"
    try:
        m.rpc(url, auth, "notifications/initialized", sid=sid)
    except Exception:
        pass
    try:
        res = m.rpc(url, auth, "tools/call",
                    {"name": "terminal.list", "arguments": {}}, sid)
        body = m.payload(res)
    except Exception as exc:
        return None, f"terminal.list: {exc}"
    if isinstance(body, dict):
        body = body.get("terminals") or body.get("entries") or []
    if not isinstance(body, list):
        return None, f"terminal.list returned {type(body).__name__}, not a list"
    return [{"id": t.get("id"), "title": t.get("title")} for t in body], None


def live_transcripts(stale_min=STALE_MIN, base=None):
    base = base or os.path.expanduser("~/.claude/projects")
    now = time.time()
    out = []
    for f in glob.glob(os.path.join(base, "*", "*.jsonl")):
        if (now - os.path.getmtime(f)) / 60 <= stale_min:
            out.append(os.path.basename(f)[:8])
    return sorted(out)


def census(rows, transcripts):
    """(exit_code, lines). Pure, so the controls can drive it with fixtures."""
    out, diverged = [], False

    if rows is None:
        return 2, ["  VOID  could not enumerate panes — established nothing about the fleet"]
    if not rows:
        return 2, ["  VOID  terminal.list returned zero panes. A fleet with zero panes is a "
                   "broken query, not an empty fleet — established nothing"]

    ids = [r["id"] for r in rows]
    titles = [r["title"] for r in rows]
    out.append(f"  panes (by id, the identity key): {len(ids)}")

    # ⛔ Distinct-id is the real count. A duplicated TITLE does not reduce it — but any
    # consumer keyed on the name WILL collapse them, so it is named loudly here.
    if len(set(ids)) != len(ids):
        diverged = True
        out.append("  ⛔ DUPLICATE PANE ID — the identity key itself is not unique. "
                   "Nothing downstream can be trusted.")

    dupes = sorted({t for t in titles if titles.count(t) > 1})
    if dupes:
        diverged = True
        for d in dupes:
            who = [r["id"] for r in rows if r["title"] == d]
            out.append(f"  ⛔ DISPLAY-NAME COLLISION  {len(who)} panes titled {d!r}: "
                       f"{', '.join(str(w) for w in who)}")
        out.append("  ⇒ a census keyed on the NAME reports "
                   f"{len(set(titles))} where the id count is {len(ids)}. "
                   "That silent drop is this instrument's subject.")
    else:
        out.append(f"  ok    {len(set(titles))} distinct titles, no collision")

    n_tr = len(transcripts)
    if n_tr != len(ids):
        diverged = True
        out.append(f"  ⛔ SOURCE DISAGREEMENT  terminal.list={len(ids)} · live transcripts="
                   f"{n_tr} (<{STALE_MIN}m).")
        out.append("  ⇒ COUNT UNESTABLISHED — and NOT because one source lags the other.")
        out.append("     Measured: the transcript set is a DIFFERENT POPULATION, wrong in both")
        out.append("     directions at once. It INCLUDES sessions that are not panes (worktree-")
        out.append("     scoped agents under .claude-worktrees-*) and OMITS at least one pane")
        out.append("     that is (a live pane writing no transcript to the project dir).")
        out.append("     ⚠ The two errors partially cancel, which is why the total looked")
        out.append("     plausible at 8 and again at 9. A near-right total over the wrong set is")
        out.append("     harder to catch than an obviously wrong one.")
    else:
        out.append(f"  ok    transcripts agree at {n_tr}")

    if diverged:
        out.append("  ⛔ UNESTABLISHED — a divergence is named above. This is a REFUSED "
                   "verdict, not a count of zero and not an all-clear.")
        return 1, out
    out.append(f"  ✅ {len(ids)} of {len(ids)} — every source agrees, count established")
    return 0, out


def self_test():
    """⛔ Every control must fail on a REAL shape this instrument shipped against.
    The known-positive alone establishes nothing: an instrument that always returns
    'agree' passes it."""
    ok = True

    def chk(label, got, want):
        nonlocal ok
        good = got == want
        ok = ok and good
        print(f"  {'ok  ' if good else 'FAIL'}  {label} (got {got}, want {want})")

    nine = [{"id": f"terminal-{i}", "title": t} for i, t in enumerate(
        ["TEAMLEAD", "ARCHITECT", "DEVOPS", "DX", "DEV1", "DEV2", "DEV3", "DEV4", "DEV5"])]
    tr9 = [f"sess{i}" for i in range(9)]

    rc, _ = census(nine, tr9)
    chk("known-positive: 9 panes, 9 titles, 9 transcripts -> established", rc, 0)

    # ⛔ THE SHIPPED DEFECT, reproduced: one pane alive with no transcript.
    rc, lines = census(nine, tr9[:8])
    hit = rc == 1 and any("SOURCE DISAGREEMENT" in l for l in lines) \
                  and any("UNESTABLISHED" in l for l in lines)
    chk("known-negative: 8 transcripts vs 9 panes -> NAMED, not silently 8", hit, True)

    # ⛔ TEAMLEAD's hypothesis, which was not tonight's cause but is still reachable.
    dup = [dict(r) for r in nine]
    dup[0]["title"] = "DEV4"
    rc, lines = census(dup, tr9)
    hit = rc == 1 and any("DISPLAY-NAME COLLISION" in l for l in lines)
    chk("known-negative: two panes titled DEV4 -> collision NAMED", hit, True)

    # ⚠ and the count a name-keyed consumer would have reported, stated explicitly
    hit = any("reports 8 where the id count is 9" in l for l in lines)
    chk("collision output states the DROPPED count, not just the collision", hit, True)

    rc, lines = census(nine[:1] + nine[:1], tr9[:2])
    hit = rc == 1 and any("DUPLICATE PANE ID" in l for l in lines)
    chk("known-negative: duplicate pane ID -> the key itself is unsound", hit, True)

    rc, lines = census(None, [])
    chk("VOID: cannot enumerate -> 2, never 0", rc, 2)
    rc, lines = census([], [])
    chk("VOID: zero panes is a broken query, not an empty fleet -> 2", rc, 2)

    print("\nselftest PASS" if ok else "\nselftest FAIL")
    return 0 if ok else 3


def main():
    if "--self-test" in sys.argv or "--selftest" in sys.argv:
        return self_test()
    rows, err = panes_from_daintree()
    if err:
        print(f"  VOID  {err} — established nothing about the fleet", file=sys.stderr)
        return 2
    rc, lines = census(rows, live_transcripts())
    print("pane census — identity key is the pane id, never the display name")
    for l in lines:
        print(l)

    # ⛔ THE RULE (#353, docs/DEFECT-CLASSES.md): a probe must demonstrate, ON THIS RUN,
    # that it can return the answer it did NOT return.
    #
    # ⚠ It has NO class letter, and that is deliberate. An earlier revision of this comment
    # cited "CLASS A (#357)" — I relayed that from a PR TITLE without reading the merged
    # body, which WITHDRAWS it: "⛔ WITHDRAWN: I ruled this 'Class A' and DEV3 refuted it
    # before it merged." ⇒ A PR title states an intent; only the merged body is a record of
    # what landed. ★ ARCHITECT's reason for withdrawing is the part to carry: a class you
    # can only apply by being ALERT is worth less than a test you can RUN — which is why
    # DEV2 and DEV3 wrote it as a rule and claimed no letter, and why the withdrawal cost
    # nothing. tools/probe-validity.py (#371) is that test for corpus probes.
    #
    # ⚠ The half that is easy to miss is the one DEV2 found: a probe that always says
    # PRESENT is exactly as broken as one that wrongly says ABSENT, and HARDER to notice,
    # because its answer looks like a finding. tools/discriminates.py is the prior art —
    # it shipped with a known-DIFFERENT control and no known-SAME one, and
    # `--a 'date +%N' --b 'date +%N'` returned ✅ DISCRIMINATED. exit 4 exists because
    # of that. So both directions are exercised here, on real rows, every run.
    probe = [dict(r) for r in rows]
    probe[0] = dict(probe[0], title=probe[1]["title"])       # force a title collision
    neg_rc, _ = census(probe, live_transcripts())
    pos_rc, _ = census(rows, [f"s{i}" for i in range(len(rows))])
    print("\n  ⚠ this run's own controls, on these same rows:")
    print(f"       can report a GAP   : {'yes' if neg_rc == 1 else 'NO'} "
          f"(duplicated a title -> exit {neg_rc})")
    print(f"       can report AGREEMENT: {'yes' if pos_rc == 0 else 'NO'} "
          f"(sources forced to match -> exit {pos_rc})")
    if neg_rc != 1 or pos_rc != 0:
        print("  ⛔ VOID — this instrument did not demonstrate BOTH answers on this run, so "
              "the verdict above establishes nothing.", file=sys.stderr)
        return 2
    return rc


if __name__ == "__main__":
    sys.exit(main())
