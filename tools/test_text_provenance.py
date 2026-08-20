#!/usr/bin/env python3
"""Pins that a count of hits is never an attribution, and that own-reads refuse a verdict.

⛔ The defect: `grep -c` on a distinctive string was read as "this reached N
sessions" twice in one day, when every hit was the asking session's own tool
record. A count cannot tell AUTHORED from FETCHED, and the wrong one was the
whole answer.

⚠ Every leg carries the KNOWN-BAD control explicitly: the naive count is asserted
to be NON-ZERO on the same fixture where the verdict is REFUSED. A suite that only
pins the right answer cannot show the wrong one was ever available.

Run: python3 tools/test_text_provenance.py
"""
import importlib.util, json, os, sys, tempfile

_here = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("tp", os.path.join(_here, "text-provenance.py"))
tp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tp)

NEEDLE = "9 of 9, not 1 of 8"
fails = []


def check(name, got, want):
    ok = got == want
    print(f"{'✅' if ok else '❌'} {name}")
    if not ok:
        print(f"     got  {got!r}\n     want {want!r}")
        fails.append(name)


def rec(kind, text, ts="2026-08-20T13:00:00Z"):
    if kind == tp.AUTHORED:
        return {"type": "assistant", "timestamp": ts,
                "message": {"content": [{"type": "text", "text": text}]}}
    if kind == tp.FETCHED:
        return {"type": "user", "timestamp": ts,
                "message": {"content": [{"type": "tool_result", "content": text}]}}
    if kind == tp.RECEIVED:
        return {"type": "user", "timestamp": ts,
                "message": {"content": [{"type": "text", "text": text}]}}
    return {"type": "attachment", "timestamp": ts, "message": {"content": text}}


# ── channel classification ────────────────────────────────────────────────────
for kind in (tp.AUTHORED, tp.FETCHED, tp.RECEIVED, tp.OTHER):
    check(f"channel: {kind}", tp.channel(rec(kind, NEEDLE)), kind)

with tempfile.TemporaryDirectory() as tmp:
    def session(sid, kinds):
        d = os.path.join(tmp, "proj")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, sid + "-rest.jsonl"), "w") as f:
            for k in kinds:
                f.write(json.dumps(rec(k, NEEDLE)) + "\n")
    root = os.path.join(tmp, "proj", "*.jsonl")

    # ── the live case: every hit is the asker's ──────────────────────────────
    session("aaaaaaaa", [tp.FETCHED, tp.AUTHORED, tp.AUTHORED])
    hits, files, _ = tp.scan([NEEDLE], root)
    code, why = tp.verdict(hits, "aaaaaaaa")
    check("own-reads only: VERDICT REFUSED (exit 3)", code, 3)
    check("KNOWN-BAD control: the naive count is non-zero on that same fixture",
          len(hits) > 0, True)
    check("KNOWN-BAD control: naive count would have said 3", len(hits), 3)
    check("...and one of them is genuinely AUTHORED — refusal is not 'no authors'",
          sum(1 for h in hits if h[3] == tp.AUTHORED), 2)

    # ⚠ the caveat is load-bearing: no --self disables the control
    code_nc, _ = tp.verdict(hits, None)
    check("without --self the own-reading control does NOT fire", code_nc, 0)
    check("...which is a DIFFERENT verdict from the same data", code_nc != code, True)

    # ── a real author elsewhere ──────────────────────────────────────────────
    session("bbbbbbbb", [tp.AUTHORED])
    hits, _, _ = tp.scan([NEEDLE], root)
    code, why = tp.verdict(hits, "aaaaaaaa")
    check("another session AUTHORED it: attributed (exit 0)", code, 0)
    check("...and it is named", "bbbbbbbb" in why, True)

    # ── present but unauthored ───────────────────────────────────────────────
    with tempfile.TemporaryDirectory() as t2:
        d = os.path.join(t2, "proj"); os.makedirs(d)
        with open(os.path.join(d, "cccccccc-x.jsonl"), "w") as f:
            f.write(json.dumps(rec(tp.RECEIVED, NEEDLE)) + "\n")
        h2, _, _ = tp.scan([NEEDLE], os.path.join(d, "*.jsonl"))
        code, _ = tp.verdict(h2, "aaaaaaaa")
        check("received but never authored here: exit 1, not 0", code, 1)

    # ── absence is not absence ───────────────────────────────────────────────
    h3, _, _ = tp.scan(["a string nobody ever wrote xyzzy"], root)
    code, why = tp.verdict(h3, "aaaaaaaa")
    check("no hits anywhere: ESTABLISHED NOTHING (exit 2)", code, 2)
    check("...and it does not say nobody wrote it", "ELSEWHERE" in why, True)

    # ── stated limit: a needle spanning records is not found ─────────────────
    h4, _, _ = tp.scan(["9 of 9, not 1 of 8 AND MORE TEXT"], root)
    check("a needle longer than any single record is simply absent", h4, [])

print(f"\n{len(fails)} failure(s)" if fails else "\nall checks passed")
sys.exit(1 if fails else 0)
