#!/usr/bin/env python3
"""Fleet context depth — the instrument behind TEAMLEAD §25 and the 90% friction report.

Reports every active agent session's context usage, so that "compact this agent"
and "collect this agent's friction report" are decisions made on a number rather
than on a proxy.

Why this exists: two roles independently inferred a context state from a proxy
(an empty input box; an unread percentage) and were wrong in the dangerous
direction — one re-tasked agents believed to have headroom, one recommended
compacting a session at 79%.

Exit status is meaningful:
    0  no session at or above --threshold
    1  at least one session at or above --threshold   (use this to gate an action)
    2  the scan itself failed to establish anything   (never read as "all clear")

⛔ THE DEPTH COLUMN IS A LEVEL, NOT A COUNTER — and this is the caveat that has
already been misread once.

Two samples reading the same value bound NOTHING about what happened between them.
Measured 2026-08-19: two panes were invoked 3 and 2 times respectively across an
interval in which their depth grew by +0.

    depth unchanged   does NOT mean "no work"
    depth unchanged   does NOT mean "not invoked"

⚠ And no sampling rate fixes it. Sampling faster narrows the window and leaves the
defect intact, because the reading was never about invocation: an invocation that
reads a cached prefix and adds little moves a level by ~0.

★ SAME SHAPE AS `exit 2` AND AS AN ABSENT `NFORMA-RUN` MARKER: a reading that
cannot distinguish DID-NOT-MOVE from WAS-NOT-OBSERVED. The value is well-formed,
plausible and stable, and what it contains is neither of the two things a reader
wants. (DEVOPS, connecting it to the other three.)

⇒ For "is this pane working", count RECORDS IN A WINDOW — events — not depth.
Same corpus, opposite selection: depth measures cumulative accumulation and
selects the loudest; records-in-window measures activity now and fires on exactly
the quiet panes depth cannot reach.

⛔ THE DEFECT WAS THE QUESTION, NOT THE ANSWER. This instrument answers "how much
has this pane accumulated". It was asked "is this pane working". It answered its
own question correctly every time. (#96)

⚠ Read the caveats in README before acting on a row.
"""
import argparse, glob, json, os, sys, time

LIMIT_DEFAULT = 1_000_000

# ⛔ The fleet is a DECLARED population, not whatever sessions exist on the machine.
#
# This scan sweeps every project directory — necessary, because an agent working in a
# git worktree gets its own and a single-directory scan silently omits it (measured: a
# pane at 97.7% was missed exactly that way). But the same sweep pulls in unrelated
# workstreams, and reporting them as "the fleet" is a wrong-population defect in the
# tool built to avoid them.
#
# Per the standard: a population that MIRRORS something living is derived; a population
# that IS the decision is declared, and every declared member must be asserted to still
# resolve. This roster is the decision — a reviewed choice about who is on this team —
# so it is declared here and checked on every run.
#
# A member that stops resolving is reported LOUDLY. A roster naming a role that has since
# gone silent reports "nothing due" with a cause that is false.
FLEET_ROLES = ("TEAMLEAD", "ARCHITECT", "DEVOPS", "DX",
               "DEV1", "DEV2", "DEV3", "DEV4", "DEV5")


def classify_series(window):
    """single | compaction-step | interleaved, from the ORDER of depth readings.

    ⛔ EXTRACTED SO IT CAN CARRY A CONTROL. The rule this implements was fixed
    against a real fleet transcript — `e4a7769d`, a window with 14 crossings between
    a ~350k and an ~850k series — and THAT TRANSCRIPT NO LONGER EXISTS. Not aged out
    of a scan window: the file is gone.

    ⇒ So "0 SHARED FILE flags" today establishes that the false positives stopped and
    establishes NOTHING about whether a genuine shared file would still be flagged.
    The comment at the call site warns that silencing a false positive by creating a
    false negative is the worse trade — and its own control evaporated with the
    session that produced it. A live-real fixture decaying, exactly as
    `stranded-branches.py` found when both its known-positives went to zero inside an
    hour.

    ⇒ The control is now CAPTURED-REAL and frozen in self_test(): both shapes come
    from the measured incident, cannot decay, and depend on no transcript surviving.

        compaction  H H H H l l l l l l      one crossing, and never back
        interleaved H H l H l l H H l H      many crossings, both series still live
    """
    if len(window) < 8:
        return "single"
    lo, hi = min(window), max(window)
    if hi - lo <= 100_000:
        return "single"
    mid = (lo + hi) / 2
    side = [v >= mid for v in window]
    if side.count(True) < 3 or side.count(False) < 3:
        return "single"
    crossings = sum(1 for i in range(1, len(side)) if side[i] != side[i - 1])
    # A step down taken once is a compaction: the last reading is then the CORRECT
    # post-compaction depth and must be reported, not suppressed. Returning to the
    # high cluster after leaving it is what no single session does.
    return "interleaved" if crossings >= 3 else "compaction-step"


def depth_bands(series, recent=60, min_gap=150_000):
    """The SET of depths in a shared transcript, when the assignment is not recoverable.

    ⛔ WHY A SET AND NOT AN ATTRIBUTION. A shared file was reported as one number —
    `85.5%` — which is wrong for at least one of its two writers. The obvious repair is to
    pair each usage reading with the nearest preceding name record and attribute it.

    **That was tested and REFUTED.** Measured on `e4a7769d`, last 60 readings in order:

        D423 D423 D423 D847 D847 D847 T425 T848 T426 T854 T854 T854 ...

    The readings are cleanly bimodal — 423-444k and 847-884k, no overlap — but **both
    names appear in BOTH bands.** ⇒ The name record does not identify which agent produced
    the adjacent reading, so nearest-name attribution assigns depth at chance.

    ★ The bands themselves are real and recoverable. So report *"two agents, one near 44%
    and one near 88%"* and refuse to say which. That is strictly better than one number
    that is wrong for somebody, and strictly more honest than a coin-flip attribution.

    ⛔ THREE OUTCOMES, NOT TWO — and the first version of this function had only two.

        None   CANNOT TELL. Fewer than `recent` readings to work with. No claim is possible.
        []     LOOKED, AND THERE IS ONE. Unimodal, or the split is a lone outlier.
        [lo,hi] two bands.

    ⇒ The first version returned `[]` for all three, so **a barely-started session rendered
    identically to a confirmed single-writer one** — and this function exists precisely because
    one depth number described two agents. **The instrument built to detect a two-states-one-output
    collapse contained one**, and its docstring mentioned only the unimodal case.

    ★ `None` vs `[]` is the same convention `exists-anywhere.py` uses for a failed search versus
    a genuine absence. One convention across the tools, so a caller that gets `None` anywhere
    knows it means *the question was not answered* rather than *the answer is nothing*.
    """
    vals = sorted(series[-recent:])
    if len(vals) < 8:
        return None                     # ⛔ cannot tell — NOT "one writer"
    gaps = [(vals[i + 1] - vals[i], i) for i in range(len(vals) - 1)]
    gap, at = max(gaps)
    if gap < min_gap:
        return []                       # unimodal: no separable bands
    lo, hi = vals[: at + 1], vals[at + 1:]
    if len(lo) < 3 or len(hi) < 3:
        return []                       # a lone outlier is not a band
    return [(min(lo), max(lo)), (min(hi), max(hi))]


def classify_names(seq):
    """A NAME HISTORY IS NOT A ROSTER. Which is this?

    ⛔ This function exists because its absence produced a chain of wrong conclusions in one
    session. `⚠name-ambiguous(IMPLEMENTER4/DEV4)` and `⚠name-ambiguous(TEAMLEAD/DEV2)` printed
    identically, and they are **opposite situations**:

        rename        A A A A B B B B        one agent, renamed. The last name is CURRENT.
        concurrent    A B A B A A B A        two agents interleaved. No name is current.

    Measured, and the two are cleanly separable by ORDER — the same insight `classify_series`
    applies to depths:

        b00d725a   IMPLEMENTER4 lines 5541..6795, then DEV4 from 6808 and never again -> RENAME
        e4a7769d   TEAMLEAD/DEV2 alternating for ~1800 records                    -> CONCURRENT

    ⇒ Reading the rename as ambiguity cost a full detour: I concluded a third, unaddressable
    writer existed, published that on a Blazing-Back issue, and only found it false by checking
    the roster — 78 live sessions, no IMPLEMENTER anywhere. **A name that appears in one
    contiguous early block and never returns is a rename, and the current name is knowable.**

    ⚠ Two states behind one warning string is the collapse this fleet catalogued five instances
    of in one toolchain the same day. This one was mine.

    ⛔ AND THIS ANSWERS A NAME QUESTION, NOT A WRITER QUESTION. Measured on `6150ffb2`: this
    returns **single** — only `ARCHITECT` ever wrote a name record — while the depth series is
    unmistakably interleaved, `428 → 77 → 431 → 82 → … → 433`, with the high series still live
    in the last two readings.

    ⇒ **Two writers, one name.** So `single` here does NOT mean one agent, and reading it that
    way is a mistake I made and nearly shipped a "fix" for: I inferred *one name ⇒ one writer ⇒
    the second band must be a compaction*, and went looking for a defect in `depth_bands` that
    was not there. The data refuted it in one look.

    ★ **A writer that never emits a name record is invisible to every name-based mechanism** —
    the roster, the obligation dedupe, ask-routing — while being fully visible in the depth
    series. That is the residual hole in fleet addressing, and it is not closable from here:
    nothing in the transcript gives it an address.
    """
    seen, order = set(), []
    for n in seq:
        if n not in seen:
            seen.add(n)
            order.append(n)
    if len(order) < 2:
        return "single"
    # A rename never returns to an earlier name. Any recurrence means interleaving.
    last_index = {}
    for i, n in enumerate(seq):
        last_index[n] = i
    first_index = {}
    for i, n in enumerate(seq):
        first_index.setdefault(n, i)
    for a, b in zip(order, order[1:]):
        if last_index[a] > first_index[b]:
            return "concurrent"
    return "rename"


def session_depth(path):
    """Context depth = the prompt size of the LAST COMPLETED assistant turn.

    A lower bound: a session mid-turn is already higher than this reports.

    ⚠ The returned name is SELF-REPORTED and is NOT an identity.

    Measured: one transcript carries TEAMLEAD, IMPLEMENTER2 and DEV2, and the
    records ALTERNATE — TEAMLEAD/DEV2/TEAMLEAD/DEV2 for a hundred cycles. A
    rename does not oscillate, so these records are not a rename history and
    last-wins is not "the current name": it is whichever record was written
    last. Reading it that way produced a confident false claim that TEAMLEAD had
    been renamed to DEV2, while both panes were in fact live and correctly named.

    `names` is therefore the DISTINCT set. More than one entry means the file
    cannot name its own session, not that the session was renamed.

    ⛔ There is no key joining a session to a Daintree pane: terminal.list gives
    id/title/worktreeId and no session id; the transcript gives a session id and
    a self-reported title. The only shared field is the title, which is stale on
    one side and duplicated on the other. Treat the depth as sound and the
    attribution as unverified.

    Returns (names, depth); names is an ordered list of every title seen.
    """
    # ⚠ `names` is the DISTINCT set (order of first appearance); `name_seq` is EVERY
    # record in order. classify_names needs the sequence — the distinct set cannot
    # tell a rename from an interleave, which is the whole distinction it draws.
    names, name_seq, last, recent = [], [], None, []
    with open(path, errors="replace") as fh:
        for line in fh:
            try:
                rec = json.loads(line)
            except Exception:
                continue                      # a partial trailing write is normal
            if rec.get("type") in ("custom-title", "agent-name"):
                n = rec.get("customTitle") or rec.get("agentName")
                if n and n not in names:      # distinct set: these records ALTERNATE
                    names.append(n)
                if n:
                    name_seq.append(n)
            msg = rec.get("message")
            if isinstance(msg, dict) and msg.get("role") == "assistant" and msg.get("usage"):
                u = msg["usage"]
                total = (u.get("input_tokens", 0) + u.get("cache_read_input_tokens", 0)
                         + u.get("cache_creation_input_tokens", 0) + u.get("output_tokens", 0))
                # ⛔ A zero is not a measurement of zero. Assistant records exist whose
                # usage block is present but entirely zero (an errored or cancelled turn).
                # Measured: one such record was a session's ONLY reading, and the session
                # rendered as "0 tokens, 0.0%" — the safest-looking row in the table, for
                # a session whose depth is in fact UNKNOWN. A second dragged a window's
                # minimum to 0, which moved the cluster midpoint by 46k and split one
                # compaction into what looked like two.
                if total <= 0:
                    continue
                last = total
                recent.append(total)
    if last is None:
        return names, None, "no-reading", [], "single"

    # ⛔ One transcript file is NOT one agent. Measured: two panes wrote to a single
    # .jsonl under one consistent sessionId, producing two interleaved depth series —
    # 856k and 690k, alternating within seconds. "The last assistant reading" is then
    # whichever agent wrote most recently, i.e. a coin flip, and every depth reported
    # for that file was unattributable. Nothing in the file declares the split; the
    # sessionId field is present, stable, and wrong to use as an identity.
    #
    # ⛔ THE TEST MUST BE TIME-AWARE. The previous rule was "both clusters hold >=3
    # readings", and its own comment claimed that excluded a compaction. It does not:
    # a compaction leaves the pre-compaction tail and the post-compaction head in the
    # same window, both populated, and the file is flagged. Measured on the live fleet:
    # 5 of 5 raised flags were compactions and 0 were shared files — a 100% false
    # positive rate, on the one event every long session eventually has. It fired on
    # ARCHITECT and on this tool's own session within minutes of each compacting.
    #
    # The two shapes are separable by ORDER, which the count throws away:
    #   compaction  H H H H l l l l l l      one crossing, and never back
    #   interleaved H H l H l l H H l H      many crossings, both series still live
    # Measured control, real and from this same population: e4a7769d carries a window
    # with 14 crossings between a ~350k and an ~850k series. Any replacement must keep
    # flagging that one — silencing a false positive by creating a false negative is
    # the worse trade, because an unattributable depth then reports as a fact.
    shape = classify_series(recent[-40:])

    return names, last, shape, depth_bands(recent), classify_names(name_seq)


def scan(active_within_s, limit):
    """Sweep EVERY project directory.

    Not the current one: an agent working in a git worktree gets its own project
    directory, and a single-directory scan silently omits it. Measured — a pane at
    97.7% was missed exactly this way.
    """
    rows, unreadable, no_reading = [], 0, 0
    roots = glob.glob(os.path.expanduser("~/.claude/projects/*"))
    if not roots:
        return None, 0, 0                      # nothing to scan is not "all clear"
    for root in roots:
        for path in glob.glob(os.path.join(root, "*.jsonl")):
            try:
                idle_s = time.time() - os.path.getmtime(path)
                if idle_s > active_within_s:
                    continue
                names, depth, shape, bands, name_kind = session_depth(path)
            except Exception:
                unreadable += 1
                continue
            if depth is None:
                # Active file, no usable reading. Not zero, not idle, not readable-and-low.
                no_reading += 1
                continue
            rows.append({"shared_file": shape == "interleaved",
                         "shape": shape,
                         "bands": bands,
                         "name_kind": name_kind,
                         "name": (names[-1] if names else "(unnamed)"),
                         "names": names,
                         "ambiguous": len(names) > 1,
                         "session": os.path.basename(path)[:8],
                         "depth": depth,
                         "pct": 100.0 * depth / limit,
                         "idle_min": int(idle_s // 60),
                         "project": os.path.basename(root)[-28:]})
    return sorted(rows, key=lambda r: -r["depth"]), unreadable, len(roots), no_reading


def self_test():
    """⛔ CAPTURED-REAL, because the live control evaporated.

    `e4a7769d` — the transcript this rule was fixed against — no longer exists, so a
    scan reporting zero flags cannot distinguish *the false positives stopped* from
    *the detector can no longer fire*. Those are opposite, and the second is the
    worse one: an unattributable depth then reports as a fact.

    Both series below are the measured shapes from that incident, frozen.
    """
    H, L = 850_000, 350_000
    compaction  = [H]*5 + [L]*5                      # one crossing, never back
    interleaved = [H, H, L, H, L, L, H, H, L, H]     # many crossings, both live
    flat        = [H - i*1000 for i in range(10)]    # one series, no cluster split
    short       = [H, L, H]                          # too few readings to claim anything

    got = {n: classify_series(w) for n, w in
           (("compaction", compaction), ("interleaved", interleaved),
            ("flat", flat), ("short", short))}
    want = {"compaction": "compaction-step", "interleaved": "interleaved",
            "flat": "single", "short": "single"}
    for n in want:
        mark = "ok  " if got[n] == want[n] else "FAIL"
        print(f"  {mark} {n:<12} -> {got[n]:<16} (want {want[n]})")
    ok = got == want
    print("  ⇒ the interleaved case is the one that matters: it is the FALSE-NEGATIVE\n"
          "    direction, and the live transcript that used to prove it is gone.",
          file=sys.stderr)
    print("\nselftest PASS" if ok else "\nselftest FAIL")
    return 0 if ok else 2


def main():
    if "--self-test" in sys.argv:
        # ⛔ A COMPANION FLAG MUST STILL BE REFUSED. Measured 2026-09-05:
        # `--self-test --zzz-not-a-flag` exited 0 here, so a self-test PASS could not
        # be told from a flag being silently ignored — the control's result
        # established nothing about the control. merge-guard.py exits 2 for both
        # forms and is the known-negative that makes this measurable.
        _extra = [a for a in sys.argv[1:] if a != "--self-test"]
        if _extra:
            print(f"\u26d4 unrecognised argument(s) alongside --self-test: {_extra}",
                  file=sys.stderr)
            return 2
        return self_test()
    ap = argparse.ArgumentParser()
    # ⛔⛔ A FLATLINE ROW IS ABOUT A FILE, NOT AN AGENT — measured the hard way.
    #
    # This scan's population is "transcripts on this machine". An agent that moves to
    # another session or another machine leaves its old transcript behind, and the
    # corpse keeps reporting as a live row at whatever depth it died at.
    #
    # Measured 2026-08-20: DEV1 was reported FLATLINE for six hours at an unchanged
    # 804,593 — and merged two pull requests during that window, from a session this
    # machine has no transcript for. Every "DEV1 dropped out / could not be asked /
    # consuming nothing" I published was about an abandoned file.
    #
    # ★ Same root as the SHARED FILE case, from the opposite side. There, one FILE held
    # two agents. Here, one AGENT held two files and the scan tracked the dead one.
    # ⇒ The agent↔transcript relation is neither injective nor surjective, and every
    # obligation this tool feeds assumed it was a bijection.
    #
    # ⚠ ABSENT FROM THIS SCAN IS NOT UNREACHABLE. The roster is a different population
    # and it had DEV1 the whole time. Check it before concluding anything about a
    # missing or flatlining row.
    #
    # ⛔ FLATLINE IS DERIVABLE, WHICH IS THE WHOLE POINT OF PUTTING IT HERE.
    # An agent that has run dry is supposed to send a message saying so. That
    # protocol reaches sessions started after it — and a prompt amendment does not
    # reach a running agent (measured: the STATE-line requirement landed 2026-08-19
    # 18:08 and every session predated it; 7 of 8 have never emitted one in up to
    # 2,884 turns). So the protocol needs a backstop that requires NO adoption.
    #
    # Transcript mtime and the usage series already exist on every pane. A session
    # consuming no tokens for N minutes is visible without anyone agreeing to
    # anything. Measured 2026-08-20: 3 of 14 sessions flat over 30 minutes, one at
    # 210 — the same session that had declared BLOCKED ~15 times in its own pane
    # while nothing aggregated it.
    #
    # ⚠ AND IT MUST NOT SAY WHY. Flat is finished, blocked, crashed, or waiting, and
    # this cannot tell them apart. A prior version of this class condemned a LIVE
    # session by defining `dead = (not alive) or idle > N`. FLATLINE is a prompt to
    # ASK, never a conclusion — the remedy is a message, not a verdict.
    ap.add_argument("--flatline", type=float, default=0.0, metavar="MINUTES",
                    help="flag sessions idle this long. 0 disables. A FLATLINE row is "
                         "UNEXPLAINED, not dead: ask the pane, do not conclude.")
    ap.add_argument("--threshold", type=float, default=80.0,
                    help="percent at which a session is reported as due (default 80). "
                         "80 rather than 90 because the binding cost of a friction report "
                         "is VERIFICATION, not composition — measured at ~2-2.5%% to write "
                         "and roughly two thirds of that re-deriving specifics.")
    ap.add_argument("--active-hours", type=float, default=6.0)
    ap.add_argument("--limit", type=int, default=LIMIT_DEFAULT)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--quiet", action="store_true", help="print only sessions at/over threshold")
    ap.add_argument("--fleet-only", action="store_true",
                    help="restrict to the DECLARED fleet roster. Without it, unrelated "
                         "workstreams on this machine are included and reported as such.")
    ap.add_argument("--snapshot", metavar="FILE", help="write the current reading, for a later --since")
    ap.add_argument("--since", metavar="FILE",
                    help="report the DELTA against a snapshot — what an event COST the fleet in "
                         "context. A broadcast that knocks seven agents off their in-flight work "
                         "is not free, and nothing else measures it.")
    args = ap.parse_args()

    rows, unreadable, roots, no_reading = scan(args.active_hours * 3600, args.limit)
    if rows is None:
        print("SCAN FAILED: no project directories found — this is not 'all clear'.\n"
              "   ADDABLE — FIXABLE HERE: ~/.claude/projects is created by the CLI on first\n"
              "   session. Zero directories means the path is wrong or no session has ever\n"
              "   run as this user — check the path before concluding anything about depth.",
              file=sys.stderr)
        return 2

    # Partition BEFORE thresholding: a stranger at 90% is not a fleet member due a report.
    def in_fleet(r):
        return any(n in FLEET_ROLES for n in r["names"])
    outside = [r for r in rows if not in_fleet(r)]
    all_rows = list(rows)          # the scanned population, before any filtering
    if args.fleet_only:
        rows = [r for r in rows if in_fleet(r)]

    # ⛔ Requiring only that the NAME appears is not enough, and this passed vacuously
    # on its first run. A transcript records every title a session has answered to, so one
    # session carrying TEAMLEAD/IMPLEMENTER2/DEV2 satisfied both the TEAMLEAD and DEV2
    # entries at once — while DEV2's real session was absent from the scan entirely, and
    # the roster reported all nine resolving.
    #
    # One session cannot be two roles. Demand a DISTINCT session per role.
    claims = {}
    for role in FLEET_ROLES:
        claims[role] = [r["session"] for r in rows if role in r["names"]]

    missing = [role for role in FLEET_ROLES if not claims[role]]
    if missing:
        print(f"⛔ DECLARED FLEET MEMBERS NOT RESOLVING: {', '.join(missing)} — absent from "
              f"the scan. A declared member that stops resolving makes every 'nothing due' "
              f"below true of a smaller fleet than the one declared.", file=sys.stderr)

    for i, role_a in enumerate(FLEET_ROLES):
        for role_b in FLEET_ROLES[i + 1:]:
            shared = set(claims[role_a]) & set(claims[role_b])
            if shared and len(claims[role_a]) == 1 and len(claims[role_b]) == 1:
                print(f"⛔ {role_a} and {role_b} are BOTH satisfied by session "
                      f"{sorted(shared)[0]}. One session cannot be two roles, so one of "
                      f"them is UNVERIFIED — its real session is not in this scan and the "
                      f"roster check would otherwise report it healthy.", file=sys.stderr)
    if outside and not args.fleet_only:
        print(f"⚠ {len(outside)} session(s) outside the declared fleet are included: "
              f"{', '.join(sorted({r['name'] for r in outside}))}. They are other workstreams "
              f"on this machine, not this team. Use --fleet-only to exclude them.",
              file=sys.stderr)

    due = [r for r in rows if r["pct"] >= args.threshold]

    if args.snapshot:
        with open(args.snapshot, "w") as fh:
            json.dump({r["session"]: r["depth"] for r in rows}, fh)
        print(f"snapshot: {len(rows)} sessions -> {args.snapshot}", file=sys.stderr)

    if args.since:
        try:
            before = json.load(open(args.since))
        except Exception as exc:
            # An unreadable snapshot is not "no change". Fail loudly.
            print(f"⛔ cannot read {args.since}: {exc}", file=sys.stderr)
            return 2
        total = 0
        print(f"{'session':<10}{'before':>10}{'after':>10}{'delta':>10}  name (self-reported)")
        for r in rows:
            prev = before.get(r["session"])
            if prev is None:
                print(f"{r['session']:<10}{'-':>10}{r['depth']:>10,}{'NEW':>10}  {r['name']}")
                continue
            d = r["depth"] - prev
            total += max(d, 0)              # a large drop is a compaction, not a cost
            note = "  <-- COMPACTED" if d < -300_000 else ""
            print(f"{r['session']:<10}{prev:>10,}{r['depth']:>10,}{d:>+10,}  {r['name']}{note}")
        # ⛔ Compare against the population actually scanned, not the filtered view.
        # With --fleet-only the filtered rows exclude every stranger, so iterating the
        # raw snapshot reported six live sessions as GONE. A filtering artifact that
        # renders as "vanished" is worse than no check: it manufactures alarms in the
        # exact field meant to catch real disappearances.
        present = {r["session"] for r in all_rows}
        for sess, prev in before.items():
            if sess not in present:
                print(f"{sess:<10}{prev:>10,}{'-':>10}{'GONE':>10}  "
                      f"⚠ vanished — not the same as idle")
        print(f"\nfleet-wide context consumed since snapshot: {total:,} tokens "
              f"({total / 1e6 * 100:.1f}% of one 1M window)", file=sys.stderr)

    if args.json:
        print(json.dumps({"rows": rows, "due": due, "unreadable": unreadable,
                          "roots_scanned": roots}, indent=2))
    else:
        for r in (due if args.quiet else rows):
            mark = "  <-- DUE" if r["pct"] >= args.threshold else ""
            # A name this session also answered to earlier. Printing only the last
            # one turns a guess into an assertion.
            # ⛔ A RENAME IS NOT AN AMBIGUITY. `IMPLEMENTER4/DEV4` and `TEAMLEAD/DEV2`
            # printed identically and are opposite: the first is one agent whose current
            # name is knowable, the second is two agents where no name is current.
            kind = r.get("name_kind")
            if r["ambiguous"] and kind == "rename":
                warn = f"  ↻renamed({'→'.join(r['names'])}) — current name is the last"
            elif r["ambiguous"]:
                warn = f"  ⚠name-ambiguous({'/'.join(r['names'])})"
            else:
                warn = ""
            if r.get("shared_file"):
                warn += "  ⛔SHARED FILE — two agents, depth UNATTRIBUTABLE"
                # ★ The assignment is unrecoverable; the SET is not. Printing both bands
                # turns "this number is wrong for somebody" into "one of these two agents
                # is deep, ask both" — which is an action a reader can take.
                b = r.get("bands")
                if b is None:
                    # ⛔ Not silence. Silence here would read as "one writer", which is the
                    # collapse this whole row exists to prevent.
                    warn += (" — and the depth series is TOO SHORT to separate: "
                             "ESTABLISHED NOTHING about how many agents, not 'one'.")
                    b = []
                if len(b) == 2:
                    warn += (f" — but the readings SEPARATE: one agent near "
                             f"{b[0][1] / 10000:.0f}%, one near {b[1][1] / 10000:.0f}%. "
                             f"ASK BOTH; do not attribute.")
            elif args.flatline and r["idle_min"] >= args.flatline:
                warn += (f"  ⛔FLATLINE {r['idle_min']}m — this FILE is consuming nothing. "
                         f"Finished, blocked, crashed, waiting, OR THE AGENT MOVED and left "
                         f"this transcript behind; this cannot tell which. ASK IT — and if it "
                         f"does not answer, check the ROSTER before concluding it is gone.")
            elif r.get("shape") == "compaction-step":
                warn += "  ↻compacted in-window — depth is the POST-compaction figure"
            print(f"{r['depth']:>9,} {r['pct']:>6.1f}%  {r['name']:<14} {r['session']}  "
                  f"{r['idle_min']:>4}m  {r['project']}{mark}{warn}")
        if not args.quiet:
            amb = sum(1 for r in rows if r["ambiguous"])
            print(f"\n{len(rows)} active session(s) across {roots} project dir(s); "
                  f"{len(due)} at/over {args.threshold:.0f}%", file=sys.stderr)
            shared = sum(1 for r in rows if r.get("shared_file"))
            stepped = sum(1 for r in rows if r.get("shape") == "compaction-step")
            print("⚠ names are SELF-REPORTED, not identities, and cannot be joined to a "
                  "Daintree pane. ⛔ Depth is per-FILE, and a file is not an agent: "
                  f"{shared} file(s) carry two interleaved agents, where no single depth "
                  "describes either."
                  + (f" {amb} session(s) answered to more than one name." if amb else "")
                  + (f" {stepped} compacted mid-window (NOT shared: a step down, taken "
                     "once, is one agent — their depth stands)." if stepped else ""),
                  file=sys.stderr)
        if args.flatline:
            flat = [r for r in rows if r["idle_min"] >= args.flatline]
            print(f"⛔ {len(flat)} of {len(rows)} session(s) flat for >={args.flatline:.0f}m. "
                  f"That is a prompt to ASK, not a verdict — one such session had declared "
                  f"BLOCKED ~15 times in its own pane while nothing aggregated it, and a "
                  f"declaration in a pane requires someone to be looking.", file=sys.stderr)
        if no_reading:
            print(f"⚠ {no_reading} active session(s) produced no usable reading — their "
                  "depth is UNKNOWN, and UNKNOWN is not 0%", file=sys.stderr)

    # An unreadable transcript is not a low-context transcript. Say so loudly.
    if unreadable:
        print(f"⚠ {unreadable} transcript(s) unreadable — their depth is UNKNOWN, not zero",
              file=sys.stderr)

    return 1 if due else 0


if __name__ == "__main__":
    sys.exit(main())
