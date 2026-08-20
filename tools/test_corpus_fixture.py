#!/usr/bin/env python3
"""A synthetic ~/.claude corpus, so a test measures the TOOL and not this machine.

⛔ Why this exists. `.github/workflows/tools.yml` gated 12 of 19 suites because the other
7 passed on a developer machine and failed on a runner. Re-running them under an empty
HOME showed the cause: they assert on output that only appears when `~/.claude/projects`
holds a real fleet — *"names its scope"*, *"prints project dir count"*, *"warns when
unscoped"*.

★ The tools were right. The tests were asserting on **whatever this machine happened to
hold**, which is the "a working set is not a sample" defect wearing a green tick: they
would also have passed for the wrong reason on a machine with a different corpus, and
their failure on a clean one is not a regression but the first honest reading.

⇒ A fixture is strictly better than the live corpus here, because every one of those
assertions is about OUTPUT SHAPE, not about the fleet. Deterministic input, deterministic
claim.

⚠ WHAT THIS FIXTURE DELIBERATELY DOES NOT PROVIDE: a Daintree pane registry. Two suites
(`test_bootstrap_audit`, `test_runmarker` via `pane-binding`) need live pane rows, and
faking those would make a control pass without the thing it controls for. They stay
ungated and stay honest about why.

Run: python3 tools/test_corpus_fixture.py   (self-checks the fixture itself)
"""
import json
import os
import sys
import tempfile

SESSION_A = "aaaaaaaa-1111-2222-3333-444444444444"
SESSION_B = "bbbbbbbb-1111-2222-3333-444444444444"

# ⛔ TWO PROJECT DIRECTORIES, NOT ONE, AND THAT IS NOT DECORATION. Several tools warn only
# when a scan spans more than one project — "⚠ N session(s) outside the declared fleet are
# included". With a single directory that branch is unreachable, and the assertion for it
# fails while the tool is behaving correctly. Measured: adding the second directory took
# `test_pretooluse_guard` from 4 failures to 0.
PROJECT_FLEET = "-Users-x-code-DigitalFrontier-infra"
PROJECT_OTHER = "-Users-x-code-some-other-project"

# One command per rule the guards care about, so a corpus scan has something true to find.
COMMANDS = [
    'python3 t.py 2>&1 | tail -5; echo "exit=$?"',       # exit-after-pipe
    "git diff main..HEAD -- goals/",                      # two-dot-diff
    "grep -rn foo --include=*.py .",                      # unquoted-glob-arg
    "echo clean; git diff main...HEAD",                   # a clean command, deliberately
]


def _lines(title, commands):
    out = [json.dumps({"type": "custom-title", "customTitle": title}),
           json.dumps({"type": "user", "isSidechain": False, "message": {
               "role": "user", "content": [{"type": "text",
               "text": f"You are {title}, an IMPLEMENTER reporting to TEAMLEAD."}]}})]
    for c in commands:
        out.append(json.dumps({"type": "assistant", "message": {"role": "assistant",
            "content": [{"type": "tool_use", "name": "Bash", "input": {"command": c}}]}}))
    out.append(json.dumps({"type": "assistant", "message": {"role": "assistant",
        "content": [{"type": "text", "text": "Done.\nSTATE: FREE — nothing queued"}]}}))
    return "\n".join(out) + "\n"


def build(root=None):
    """Create the corpus and return its HOME path. Caller owns cleanup."""
    root = root or tempfile.mkdtemp(prefix="nforma-fixture-")
    projects = os.path.join(root, ".claude", "projects")
    os.makedirs(os.path.join(root, ".claude", "sessions"), exist_ok=True)
    for proj, sid, title, cmds in (
            (PROJECT_FLEET, SESSION_A, "DEVOPS", COMMANDS),
            (PROJECT_OTHER, SESSION_B, "DEV1", COMMANDS[:1])):
        d = os.path.join(projects, proj)
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, f"{sid}.jsonl"), "w").write(_lines(title, cmds))
    json.dump({"name": "DEVOPS"},
              open(os.path.join(root, ".claude", "sessions", "12345.json"), "w"))
    return root


def env(root=None):
    """An environment whose HOME is a fixture corpus."""
    return dict(os.environ, HOME=build(root))


def _check(name, got, want):
    ok = got == want
    print(("  PASS  " if ok else "  FAIL  ") + f"{name}: got {got!r}, want {want!r}")
    return ok


def main():
    """⛔ The fixture is itself an instrument and gets the same treatment. A malformed
    corpus would make every suite using it fail for a reason none of them names."""
    f = 0
    home = build()
    projects = os.path.join(home, ".claude", "projects")
    f += not _check("two project dirs", len(os.listdir(projects)), 2)
    f += not _check("fleet project present", os.path.isdir(os.path.join(projects, PROJECT_FLEET)), True)

    path = os.path.join(projects, PROJECT_FLEET, f"{SESSION_A}.jsonl")
    recs = [json.loads(l) for l in open(path)]
    f += not _check("every line parses as JSON", len(recs), len(COMMANDS) + 3)

    cmds = [b["input"]["command"] for r in recs
            for b in (r.get("message") or {}).get("content", [])
            if isinstance(b, dict) and b.get("type") == "tool_use"]
    f += not _check("commands recoverable", cmds, COMMANDS)

    # ⚠ A fixture with nothing to find would let a guard's "no hits" read as a pass.
    # Assert the corpus actually CONTAINS the defects the guards look for.
    f += not _check("corpus contains a piped exit read",
                    any("| tail" in c and "$?" in c for c in cmds), True)
    f += not _check("corpus contains a two-dot diff",
                    any(".." in c and "..." not in c for c in cmds), True)
    f += not _check("corpus contains a clean command too",
                    any("..." in c for c in cmds), True)

    last = recs[-1]["message"]["content"][0]["text"].splitlines()[-1]
    f += not _check("last line is a STATE declaration", last.startswith("STATE:"), True)

    print()
    if f:
        print(f"{f} FAILED")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
