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
import json, os, sys, tempfile, types

# ⛔ A STALE __pycache__ SILENTLY SERVES THE PRE-MUTATION MODULE. Measured with a
# 4-cell table: {clean,mutant} x {cache cleared,stale} -> the mutant PASSED on a stale
# cache and failed 3 checks once cleared. Every suite here loads its tool through
# spec_from_file_location, so a false SURVIVED sends you rewriting a correct test.
# CI is safe (fresh checkout, no cache); local mutation testing was not.
sys.dont_write_bytecode = True
# ⚠ and the env var too: a SUBPROCESS does not inherit sys.dont_write_bytecode,
# which is why three suites still produced a cache after the first fix.
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

_here = os.path.dirname(os.path.abspath(__file__))


def load(path, name):
    """Execute the source text READ NOW — a positive reload proof.

    ⛔ `spec_from_file_location` consults `__pycache__`, and Python invalidates a
    `.pyc` on mtime + size. A SIZE-PRESERVING mutation applied within the same
    second leaves both unchanged, so the cached module is served and the mutation
    SURVIVES. Measured: `GH_PUBLISH.search(cmd)` -> `"gh pr comment" in cmd` is
    60 bytes either way, file 18764 either way, and it survived with all three of
    the usual safeguards passing.

    ⚠ `sys.dont_write_bytecode` prevents the cache; that is an ABSENCE of the
    mechanism, not evidence of the load. Compiling the bytes we just read is the
    evidence — there is no cache in the path to consult.
    """
    src = open(path).read()
    mod = types.ModuleType(name)
    mod.__file__ = path
    exec(compile(src, path, "exec"), mod.__dict__)
    return mod


tp = load(os.path.join(_here, "text-provenance.py"), "tp")

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


# ── INSTRUMENT: a command carrying the string is not an assertion of it ───────
# ⛔ Found by a PEER after this tool shipped: two of my three AUTHORED hits were a
# search script with the needle as a literal argument. A confident false positive.
def tool_use(name, inp, ts="2026-08-20T13:00:00Z"):
    return {"type": "assistant", "timestamp": ts,
            "message": {"content": [{"type": "tool_use", "name": name, "input": inp}]}}


search = tool_use("Bash", {"command": f"python3 -c \"if '{NEEDLE}' in line: pass\""})
check("a search command is INSTRUMENT, not AUTHORED",
      tp.channel(search, [NEEDLE]), tp.INSTRUMENT)
check("KNOWN-BAD control: a type-only classifier calls that same record AUTHORED",
      search["type"] == "assistant", True)
check("⚠ and the verb is NOT the discriminator — this one contains no grep/rg",
      "grep" not in search["message"]["content"][0]["input"]["command"], True)

check("SendMessage IS publishing: AUTHORED",
      tp.channel(tool_use("SendMessage", {"to": "X", "message": NEEDLE}), [NEEDLE]), tp.AUTHORED)
check("gh pr comment IS publishing: AUTHORED",
      tp.channel(tool_use("Bash", {"command": f"gh pr comment 1 --body '{NEEDLE}'"}), [NEEDLE]),
      tp.AUTHORED)
check("prose in an assistant text block stays AUTHORED",
      tp.channel(rec(tp.AUTHORED, NEEDLE), [NEEDLE]), tp.AUTHORED)

# ── POST-DATES: you cannot be the origin of what you saw after me ─────────────
early = [("2026-08-20T13:45:00Z", "aaaaaaaa", 1, tp.FETCHED)]
late = [("2026-08-20T14:09:00Z", "bbbbbbbb", 2, tp.AUTHORED)]
code, why = tp.verdict(early + late, "aaaaaaaa")
check("a session that first saw it AFTER you is not the author", code, 1)
# ⚠ asserted "POST-DATES" here first and it failed: the message reads "POST-DATE".
# A substring assertion that is one character off reports a working feature broken —
# the same matcher defect this repo has filed twice. Match the STEM.
check("...and it is named as post-dating", ("bbbbbbbb" in why, "POST-DATE" in why), (True, True))
check("KNOWN-BAD control: without the check it reads as attributed",
      tp.verdict(early + late, None)[0], 0)

earlier = [("2026-08-20T12:00:00Z", "bbbbbbbb", 2, tp.AUTHORED)]
code, why = tp.verdict(early + earlier, "aaaaaaaa")
check("a session that had it BEFORE you is attributed", (code, "bbbbbbbb" in why), (0, True))
check("postdates with no self is None — NOT RUN, not an empty set",
      tp.postdates(early + late, None), None)

# ── the control cannot be omitted silently ───────────────────────────────────
import subprocess
tool = os.path.join(_here, "text-provenance.py")
r = subprocess.run([sys.executable, tool, "x"], capture_output=True, text=True)
check("omitting --self is an ERROR, not a quiet unchecked run", r.returncode != 0, True)
check("...and the error names the escape hatch", "--no-self" in r.stderr, True)


# ── the allowlist drifts, and that is measurable ─────────────────────────────
# ⛔ A peer measured the FIRST version of this table on its own transcript:
# `commit -F` 61 uses, `commit -m` 13; `gh issue create` 24; `gh issue comment` 55.
# Only `commit -m` and `gh pr comment` were listed. Nothing failed — the numerator
# just quietly shrank. These pin the forms that were missing.
for cmd, want, why in [
    ("git commit -q -F /tmp/msg.txt", tp.AUTHORED, "commit -F is how heredoc messages are written"),
    ("git commit -m 'x'",             tp.AUTHORED, "commit -m still publishes"),
    ("gh issue create --body-file b",  tp.AUTHORED, "gh issue create publishes"),
    ("gh issue comment 1 --body x",    tp.AUTHORED, "gh issue comment publishes"),
    ("gh pr view 1 --json body",       tp.INSTRUMENT, "gh pr view READS — gh is not one tool"),
    ("gh api repos/x/y",               tp.INSTRUMENT, "gh api reads"),
    ("cat > tools/new.py <<'EOF'",     tp.AUTHORED, "a heredoc landing in a file IS authoring"),
]:
    check(f"bash: {why}", tp.classify_use({"name": "Bash", "input": {"command": cmd}}), want)

check("an unknown tool is UNCLASSIFIED, never silently INSTRUMENT",
      tp.classify_use({"name": "SomeNewSender", "input": {"x": 1}}), tp.UNCLASSIFIED)
check("an unrecognised bash path is UNCLASSIFIED too",
      tp.classify_use({"name": "Bash", "input": {"command": "newpublisher --send x"}}),
      tp.UNCLASSIFIED)
check("KNOWN-BAD control: the old rule would have called that INSTRUMENT",
      tp.classify_use({"name": "Bash", "input": {"command": "newpublisher --send x"}})
      != tp.INSTRUMENT, True)

# an UNCLASSIFIED hit blocks a verdict rather than being absorbed
mine = [("2026-08-20T13:00:00Z", "aaaaaaaa", 1, tp.FETCHED)]
uncl = [("2026-08-20T12:00:00Z", "dddddddd", 2, tp.UNCLASSIFIED)]
code, why = tp.verdict(mine + uncl, "aaaaaaaa")
check("an UNCLASSIFIED path is a DECISION (exit 4), not an answer", code, 4)
check("...and the undecided session is named", "dddddddd" in why, True)

# ⚠ but it must not mask a real author
both = uncl + [("2026-08-20T11:00:00Z", "eeeeeeee", 3, tp.AUTHORED)] + mine
code, why = tp.verdict(both, "aaaaaaaa")
check("a real author still attributes, with the gap flagged",
      (code, "eeeeeeee" in why, "UNCLASSIFIED" in why), (0, True, True))


# ── flag ORDER is unbounded, so it must not be enumerated ────────────────────
# ⛔ The first version listed "commit -m", "commit -F", "commit -q -F" and fell
# through on -a -F, --amend -m and -am. Same drift as the tool-level allowlist,
# one level down, found while a peer was correcting its own count of these forms.
for cmd, want in [
    ("git commit -q -F /tmp/m.txt",        tp.AUTHORED),
    ("git commit -a -F /tmp/m",            tp.AUTHORED),
    ("git commit -am 'x'",                 tp.AUTHORED),
    ("git commit --amend -m x",            tp.AUTHORED),
    ("git commit --message=x",             tp.AUTHORED),
    ("git -c user.name=X commit -F /tmp/m", tp.AUTHORED),
]:
    check(f"commit form: {cmd[:34]}", tp.classify_use({"name": "Bash", "input": {"command": cmd}}), want)

# ⚠ NEGATIVE CONTROLS. `git` is required before `commit` for two reasons, and the
# second was only found by measuring: grep's `-m` is max-count, and — measured on
# a peer's transcript — ALL 10 bare `commit -m` occurrences were QUOTATIONS of the
# allowlist itself, in messages and commit bodies discussing it. Requiring `git`
# excludes mention and keeps use.
check("grep's -m is max-count, not a message", 
      tp.classify_use({"name": "Bash", "input": {"command": "grep commit -m 3 f.txt"}}), tp.INSTRUMENT)
check("a quotation of the allowlist is not an invocation of it",
      tp.classify_use({"name": "Bash", "input": {"command": "echo \"listed: commit -m and gh pr comment\""}}),
      tp.INSTRUMENT)
check("git log is reading",
      tp.classify_use({"name": "Bash", "input": {"command": "git log --oneline -5"}}), tp.INSTRUMENT)

print(f"\n{len(fails)} failure(s)" if fails else "\nall checks passed")
sys.exit(1 if fails else 0)
