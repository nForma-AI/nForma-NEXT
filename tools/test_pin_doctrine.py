#!/usr/bin/env python3
"""Pins check_pin_doctrine's two refuted defects — with a caller that still runs them.

⛔ WHY THIS FILE EXISTS, and it is #381. The pin-doctrine control shipped with two
defects (#316): it FIRED on a repaired state, and it PASSED on a reversed one. Both were
demonstrated before #303 merged, both were fixed in #323, and the demonstration was a
MANUAL run in a scratch worktree that nothing re-executes.

    criterion 4: shown to FAIL on real data — BY A CALLER THAT STILL RUNS IT.
    A demonstration that happened once and cannot happen again is a SCREENSHOT.

⇒ My evidence for #316 was a screenshot. This is the caller.

★ The two defects are opposite, and a suite that only pins one leaves the control able
to regress into the other:
  · ATTACK A — delete one endorsed ✅ pin form, keep the other. The doctrine is INTACT.
    The pre-#323 control exited 1, firing on a repaired state — the failure mode the
    control's own docstring says to prefer AGAINST.
  · ATTACK B — remove both ✅ forms and reintroduce the string inside a line reading
    "⛔ Never use: git archive …". The doctrine is REVERSED. The pre-#323 control
    exited 0, because bare presence cannot see polarity.

⚠ T4 is the known-positive and is not optional: a suite that only proves the false
alarms stopped would pass a control that can no longer fail at all. Removing a false
positive is half a fix — tools/test_fleet_context.py records that same lesson.

Hermetic: builds a fixture tree in a temp dir and points the control's ROOT at it. No
network, no repository state, so it carries no `# SUITE-DEPENDS:` and the CI glob gates it.
"""
import importlib.util, io, os, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
CTRL = HERE.parent / "scripts" / "check-orientation.py"
FAILED = 0


def check(label, got, want):
    global FAILED
    ok = got == want
    print(f"  {'PASS' if ok else 'FAIL'}  {label}: got {got!r}, want {want!r}")
    if not ok:
        FAILED += 1


def load_with_root(root):
    """Load the control with ROOT pointed at a fixture tree."""
    spec = importlib.util.spec_from_file_location(f"co_{os.path.basename(root)}", CTRL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.ROOT = Path(root)
    return mod


BOTH_FORMS = """# Fleet instruments

⛔ **A MARKER-CARRYING TOOL CANNOT BE PINNED AS A SINGLE FILE.**

```
git show <ref>:tools/x.py > /tmp/x.py && python3 /tmp/x.py                        ⛔ zero markers
git archive <ref> tools/ | tar -x -C /tmp/pin  &&  python3 /tmp/pin/tools/x.py    ✅ markers emit
git show <ref>:tools/x.py + tools/runmarker.py &&  python3 /tmp/pin2/x.py         ✅ markers emit
```

Every marker-carrying tool does `import runmarker` at the top.
"""


def fixture(tmp, readme):
    root = Path(tmp) / "r"
    (root / "tools").mkdir(parents=True)
    (root / "tools" / "README.md").write_text(readme, encoding="utf-8")
    return root


def verdict(root):
    """True == the control reports the doctrine LOST (i.e. it fires)."""
    mod = load_with_root(root)
    buf, err = io.StringIO(), io.StringIO()
    out, oerr = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = buf, err
    try:
        return mod.check_pin_doctrine()
    finally:
        sys.stdout, sys.stderr = out, oerr


def main():
    with tempfile.TemporaryDirectory() as tmp:
        print("baseline — both endorsed forms present:")
        check("does not fire", verdict(fixture(tmp + "/a", BOTH_FORMS)), False)

        print("\n★ ATTACK A — one ✅ form deleted, the OTHER endorsed one kept:")
        a = "\n".join(l for l in BOTH_FORMS.splitlines() if "git archive" not in l) + "\n"
        assert "runmarker.py" in a and "✅" in a, "fixture must keep the other ✅ form"
        check("doctrine intact, so it must NOT fire", verdict(fixture(tmp + "/b", a)), False)

        print("\n★ ATTACK B — both ✅ forms gone, string survives in a ⛔ 'Never use' line:")
        b = "\n".join(l for l in BOTH_FORMS.splitlines() if "✅" not in l)
        b = b.replace("# Fleet instruments",
                      "# Fleet instruments\n\n⛔ Never use: `git archive <ref> tools/ | tar -x -C /tmp/pin` — superseded.")
        check("doctrine reversed, so it MUST fire", verdict(fixture(tmp + "/c", b)), True)

        print("\n⛔ T4 known-positive — genuine loss, both forms simply removed:")
        d = "\n".join(l for l in BOTH_FORMS.splitlines() if "✅" not in l)
        check("must fire", verdict(fixture(tmp + "/d", d)), True)

        print("\nthe unreadable case is UNCHECKED, never absent:")
        empty = Path(tmp) / "e" / "tools"
        empty.mkdir(parents=True)
        check("no README -> does not claim the doctrine is lost",
              verdict(Path(tmp) / "e"), False)

    print(f"\n{FAILED} FAILED" if FAILED else "\nall PASS")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
