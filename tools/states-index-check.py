#!/usr/bin/env python3
"""Does a tool's README row agree with the exit codes the tool ITSELF emits?

⛔ #39: a producer gains a state, its consumers keep asserting the old one, and the new state
renders as one of the OLD ones rather than as unknown. Measured on this repository:
`doctrine-version.py` gained SAW-LATER in #57 and `tools/README.md` still read "1 an agent is
stale" -- so "the agent LOOKED, currency unproven" rendered as its near-opposite.

⇒ #292 gave that tool `--states`, so the space is EMITTED. This is the missing half: a
CONSUMER THAT INVOKES THE PRODUCER instead of trusting a transcription.

⚠ WHAT THIS IS NOT. It does not GENERATE the row. #39's close condition asks for a consumer
whose list is *produced by invoking the producer*; this one *verifies* a hand-written row
against the producer. ⇒ That is drift DETECTION, not drift IMPOSSIBILITY, and the difference
is the whole of #39. Stated here rather than claimed away.

Exit codes:
    0  every tool exposing --states has a row agreeing with it
    1  a row disagrees with its tool's emitted exit codes
    2  ESTABLISHED NOTHING -- no tool exposes --states, or the index is unreadable
       ⚠ never "all clear"
    3  CONTROL FAILED
"""
import argparse, os, re, subprocess, sys

EXIT_LINE = re.compile(r"^EXIT\t(\d+)\t", re.M)


def emitted_exits(path):
    """⚠ Exit status read directly; `$?` after a pipe is the pipe's."""
    p = subprocess.run([sys.executable, path, "--states"], capture_output=True, text=True,
                       timeout=60)
    if p.returncode != 0:
        return None
    codes = {int(m) for m in EXIT_LINE.findall(p.stdout)}
    return codes or None


def row_exits(readme_text, toolname):
    """The exit codes a README row CLAIMS. ⚠ Matched only inside that tool's own row --
    a code elsewhere in the file is a different tool's and counting it would be the
    wrong-population defect."""
    for line in readme_text.splitlines():
        if line.startswith("|") and f"`{toolname}`" in line:
            return {int(n) for n in re.findall(r"(?<![\w.])([0-9])(?=\s)", line)} or set(), line
    return None, None



def emit_row(path, question):
    """⇒ #39's other half: PRODUCE the row from the tool rather than transcribe it.

    ⛔ A verified transcription is not a generated row. `states-index-check` (as first written)
    DETECTED drift; this makes the committed text an OUTPUT of the producer, so the two cannot
    disagree without the generator being re-run and the diff showing it.
    """
    p = subprocess.run([sys.executable, path, "--states"], capture_output=True, text=True,
                       timeout=60)
    if p.returncode != 0:
        return None
    exits = []
    for line in p.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) == 3 and parts[0] == "EXIT":
            exits.append(f"{parts[1]} {parts[2]}")
    if not exits:
        return None
    name = os.path.basename(path)
    return (f"| `{name}` | {question} | " + " · ".join(exits)
            + " | ⚙ GENERATED-FROM: --states |")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__)
    ap.add_argument("--repo", default=".")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--emit", metavar="TOOL",
                    help="print the canonical README row for TOOL, generated from its --states")
    ap.add_argument("--verify", action="store_true",
                    help="regenerate every row marked GENERATED-FROM and compare byte-for-byte")
    a = ap.parse_args()
    print("NFORMA-RUN states-index-check", file=sys.stderr)
    if a.self_test:
        return self_test()
    if a.verify:
        # ⛔ THE MARKER IS A CLAIM. Without this, `⚙ GENERATED-FROM: --states` asserts the row was
        #    produced by the generator and NOTHING re-runs it — a name carrying its method only
        #    because someone typed it (#437). This regenerates and compares byte-for-byte.
        text = open(os.path.join(a.repo, "tools", "README.md")).read()
        marked = [l for l in text.splitlines() if "GENERATED-FROM: --states" in l]
        if not marked:
            print("⛔ VOID  no row claims to be generated — ESTABLISHED NOTHING.", file=sys.stderr)
            return 2
        bad = 0
        for line in marked:
            m = re.match(r"\| `([a-z0-9-]+\.py)` \| (.*?) \|", line)
            if not m:
                print(f"  ⛔ UNPARSEABLE  {line[:60]}"); bad += 1; continue
            fresh = emit_row(os.path.join(a.repo, "tools", m.group(1)), m.group(2))
            if fresh is None:
                print(f"  ⛔ VOID        {m.group(1)}: --states emitted nothing"); bad += 1
            elif fresh.strip() != line.strip():
                print(f"  ⛔ NOT GENERATED  {m.group(1)}: committed row differs from regenerated")
                bad += 1
            else:
                print(f"  ✅ GENERATED   {m.group(1)}: byte-identical to its regeneration")
        print(f"\n  rows claiming generation: {len(marked)} · verified: {len(marked)-bad}")
        return 1 if bad else 0
    if a.emit:
        row = emit_row(a.emit, "which version of its role prompt is each agent running?"
                       if "doctrine-version" in a.emit else "<question>")
        if row is None:
            print("⛔ VOID  that tool emitted no EXIT lines — ESTABLISHED NOTHING.", file=sys.stderr)
            return 2
        print(row)
        return 0

    tools_dir = os.path.join(a.repo, "tools")
    readme = os.path.join(tools_dir, "README.md")
    if not os.path.isfile(readme):
        print("⛔ VOID  tools/README.md unreadable — ESTABLISHED NOTHING.", file=sys.stderr)
        return 2
    text = open(readme).read()

    checked = disagreed = 0
    for fn in sorted(os.listdir(tools_dir)):
        if not fn.endswith(".py") or fn.startswith("test_"):
            continue
        path = os.path.join(tools_dir, fn)
        # ⛔ USE, NOT MENTION (#36). The first version matched the STRING "--states" and
        #    therefore flagged close-condition-scan.py and THIS FILE, both of which only
        #    DISCUSS the flag in prose. Match the argparse registration instead.
        src = open(path, errors="ignore").read()
        if not re.search(r'add_argument\(\s*["\']--states["\']', src):
            continue
        codes = emitted_exits(path)
        if codes is None:
            print(f"  ⛔ VOID        {fn:<28} --states did not emit EXIT lines")
            continue
        claimed, line = row_exits(text, fn)
        if claimed is None:
            print(f"  ⛔ NO ROW      {fn:<28} emits {sorted(codes)}, indexed nowhere")
            disagreed += 1
            continue
        checked += 1
        if codes <= claimed:
            print(f"  ok            {fn:<28} emits {sorted(codes)} ⊆ row {sorted(claimed)}")
        else:
            disagreed += 1
            print(f"  ⛔ DISAGREES  {fn:<28} emits {sorted(codes)}, row claims {sorted(claimed)}"
                  f"\n                missing from the row: {sorted(codes - claimed)}")

    if checked == 0 and disagreed == 0:
        print("⛔ VOID  no tool exposes --states — ESTABLISHED NOTHING, not 'all agree'.",
              file=sys.stderr)
        return 2
    print(f"\n  tools exposing --states: {checked + disagreed} · rows agreeing: {checked}"
          f" · disagreeing: {disagreed}")
    _total = checked + disagreed
    if _total >= 3 and (checked == 0 or disagreed == 0):
        _w = "agreeing" if disagreed == 0 else "disagreeing"
        print(f"⛔ NON-DISCRIMINATING — all {_total} subjects scored {_w}. Establishes nothing"
              "\n   about any of them; a per-invocation control cannot see this.")
    print("⚠ This DETECTS drift; it does not make drift impossible. #39's condition asks for a row"
          "\n   GENERATED from the emitter, and a verified transcription is not one.")
    return 1 if disagreed else 0


def self_test():
    ok = True

    def check(name, got, want):
        nonlocal ok
        if got != want:
            print(f"⛔ FAIL  {name}: got {got!r}, want {want!r}"); ok = False
        else:
            print(f"  PASS  {name}: {got!r}")

    row = "| `x.py` | what? | 0 fine · 1 a finding · **2 established nothing** |\n"
    check("codes are read from the tool's own row", row_exits(row, "x.py")[0], {0, 1, 2})
    # ⛔ population: another tool's row must not contribute
    other = "| `y.py` | q | 0 · 1 · 2 · 3 |\n| `x.py` | q | 0 · 2 |\n"
    check("a different tool's row does not leak in", row_exits(other, "x.py")[0], {0, 2})
    check("a tool with no row is None, not an empty set", row_exits(other, "z.py")[0], None)
    # ⛔ the known-negative: a row MISSING a code the tool emits must be caught
    claimed, _ = row_exits("| `x.py` | q | 0 · 1 |\n", "x.py")
    check("a row missing an emitted code is detected", {0, 1, 2} <= claimed, False)
    check("a row covering every emitted code passes", {0, 1} <= claimed, True)
    print("all checks passed" if ok else "⛔ self-test FAILED")
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(main())
