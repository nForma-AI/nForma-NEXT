#!/usr/bin/env python3
"""Pins that INSTALLED and DELIVERED never collapse, and that PULLED is not delivery.

⛔ The bug this suite exists to keep dead: the first version of the extractor took
the first user record verbatim and got a `<system-reminder>`, not the bootstrap.
Every pane whose reminder precedes its launch prompt then read as "no pointer",
and 4 of 9 sessions were misreported from that one off-by-one-record.

★ So the fixture is NOT hand-typed. `testdata/transcript-head-real-shape.jsonl`
was generated from a live transcript head with the ids and prose replaced and the
record ORDER and KEYS untouched -- because the defect IS the order. A fixture
invented from memory drops exactly the field that breaks the tool, and then passes.

⚠ Each delivery leg carries a KNOWN-BAD control: the naive reading is asserted to
give the WRONG answer on the same fixture. A test that only pins the right answer
cannot tell a fixed tool from a fixture that never exercised it.

Run: python3 tools/test_prompt_delivery.py
"""
import json, os, sys, tempfile, types

_here = os.path.dirname(os.path.abspath(__file__))


def load(path, name):
    """Execute the source text READ NOW — a positive reload proof.

    ⛔ `spec_from_file_location` consults `__pycache__`, and Python invalidates a
    `.pyc` on mtime + SIZE. A SIZE-PRESERVING mutation (`==`/`!=`, a flag flip, a
    token swap) applied within the same second leaves both unchanged, so the
    cached module is served and the mutation SURVIVES — with a changed file and a
    moved target both verifying. Measured on a sibling tool: 60 bytes either way,
    file 18764 either way, and it survived.

    ⚠ Suppressing the cache proves only that none EXISTS. Compiling the bytes we
    just read is the evidence: there is no cache in the path to consult.
    """
    src = open(path).read()
    mod = types.ModuleType(name)
    mod.__file__ = path
    exec(compile(src, path, "exec"), mod.__dict__)
    return mod


pd = load(os.path.join(_here, "prompt-delivery.py"), "pd")

FIXTURE = os.path.join(_here, "testdata", "transcript-head-real-shape.jsonl")
POINTER = "git -C ~/code/nForma-NEXT show origin/main:prompts/DX.md"

fails = []


def check(name, got, want):
    ok = got == want
    print(f"{'✅' if ok else '❌'} {name}")
    if not ok:
        print(f"     got  {got!r}\n     want {want!r}")
        fails.append(name)


def user(text, tool_result=False):
    c = [{"type": "tool_result", "content": text}] if tool_result else [{"type": "text", "text": text}]
    return {"type": "user", "message": {"content": c}}


def assistant(text):
    return {"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}}


def write(tmp, records, name="t.jsonl"):
    p = os.path.join(tmp, name)
    with open(p, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    return p


def naive_first_user(path):
    """The reading this tool had before the fix. Kept as the known-bad control."""
    with open(path) as f:
        for i, line in enumerate(f):
            rec = json.loads(line)
            if rec.get("type") == "user":
                return i
    return None


# ── the real-shape fixture ────────────────────────────────────────────────────
idx, boot = pd.bootstrap(FIXTURE, 40)
check("real shape: bootstrap is the launch prompt, not the reminder", idx, 14)
check("real shape: KNOWN-BAD control — naive reading lands on the reminder",
      naive_first_user(FIXTURE), 11)
check("real shape: the two readings differ (fixture DOES exercise the defect)",
      idx != naive_first_user(FIXTURE), True)
check("real shape: text is the bootstrap", boot.startswith("You are DX"), True)

with tempfile.TemporaryDirectory() as tmp:
    # ── channels ─────────────────────────────────────────────────────────────
    p = write(tmp, [user("You are DEV. " + POINTER)], "launch.jsonl")
    check("LAUNCH: pointer in the bootstrap", pd.delivery(p), {pd.LAUNCH: 0})

    p = write(tmp, [user("You are DEV. no pointer here"), user("FYI: " + POINTER)], "recv.jsonl")
    check("RECEIVED: a later inbound turn", pd.delivery(p), {pd.RECEIVED: 1})

    p = write(tmp, [user("You are DEV."), user(POINTER, tool_result=True)], "pull.jsonl")
    check("PULLED: a tool_result is the session's OWN reading, not receipt",
          pd.delivery(p), {pd.PULLED: 1})
    check("PULLED is not counted as RECEIVED",
          pd.RECEIVED in (pd.delivery(p) or {}), False)

    p = write(tmp, [user("You are DEV."), assistant("I will read " + POINTER)], "wrote.jsonl")
    check("PULLED: the session writing the pointer is not delivery",
          pd.delivery(p), {pd.PULLED: 1})

    # ── ESTABLISHED NOTHING ──────────────────────────────────────────────────
    p = write(tmp, [user("[TEAMLEAD auto-wake] You are idle. Resume your goal's "
                         "autonomous loop: take the next item.")], "wake.jsonl")
    check("a wake at the head establishes NOTHING about the launch", pd.delivery(p), None)

    p = write(tmp, [assistant("no user record at all")], "nouser.jsonl")
    check("no launch prompt in the file is None, never {}", pd.delivery(p), None)

    p = write(tmp, [user("You are DEV. no pointer")], "clean.jsonl")
    check("read, carried none is {} — distinct from None", pd.delivery(p), {})

    # ── INSTALLED is a filesystem fact ───────────────────────────────────────
    g = os.path.join(tmp, "goals")
    os.makedirs(g)
    check("empty goals dir establishes NOTHING", pd.installed(g), None)
    open(os.path.join(g, "a.md"), "w").write("prose, no pointer\n")
    open(os.path.join(g, "b.md"), "w").write("see " + POINTER + "\n")
    check("installed counts FILES and says so", pd.installed(g), (["b.md"], 2))

    # ⛔ the collision this tool exists for: N files, N sessions, N != N
    inst, _ = pd.installed(g)
    sessions = [write(tmp, [user("You are DEV. no pointer")], f"s{i}.jsonl") for i in range(len(inst))]
    launched = sum(1 for s in sessions if pd.LAUNCH in (pd.delivery(s) or {}))
    check("COLLISION: installed 1 of 2 with 1 session — delivered is still 0",
          (len(inst), len(sessions), launched), (1, 1, 0))

# ── shape drift: reported, never gating ──────────────────────────────────────
import glob
live = sorted(glob.glob(os.path.expanduser("~/.claude/projects/*/*.jsonl")),
              key=lambda p: -os.path.getmtime(p))[:1]
if not live:
    print("⚠ shape drift: no live transcript on this machine — NOT RUN, not passed.")
else:
    li, lb = pd.bootstrap(live[0], 40)
    if li is None:
        print("⚠ shape drift: freshest transcript holds no launch prompt — NOT RUN.")
    else:
        naive = naive_first_user(live[0])
        print(f"ⓘ shape drift: live bootstrap at record {li}, naive reading at {naive} "
              f"— {'STILL DIFFERENT (fixture is current)' if li != naive else 'now identical: the fixture may no longer exercise the defect'}")

print(f"\n{len(fails)} failure(s)" if fails else "\nall checks passed")
sys.exit(1 if fails else 0)
