#!/usr/bin/env python3
"""Audit what a pane's bootstrap actually EXECUTED, against what its ROLE-READY line claims.

⛔ The defect this exists for (#20), stated as the thing that is actually wrong:

    A bootstrap step with NO EXECUTION RECORD AT ALL, followed by a success token.

Not "a step that failed" — a step that left no trace, while the token that is
supposed to summarise the bootstrap was emitted anyway. Measured on this pane:

    step 1  "Run: /rename DEV2"     -> zero tool_use records. Ever.
    step 2  "cat prompts/DEV.md"    -> tool_use, is_error=False
    step 3  "git rev-parse ..."     -> same call
    step 4  "Print exactly one line: ROLE-READY ..."  -> emitted

⇒ `ROLE-READY DEV2 repo=nForma-NEXT branch=main` was true in all three facts it
carries, and the bootstrap had still failed, because the failure was in a fourth
thing the token has no slot for. A fixed-arity success token is a CLOSED grammar:
it renders unanticipated facts as ABSENT rather than as UNKNOWN.

★ THE REFRAME, and it is why this tool checks what it checks.

`ROLE-READY` is not a claim worth verifying. Every fact it asserts is already
readable from substrate, more reliably, by any pane:

    role    ->  ~/.claude/sessions/<pid>.json  `name`  (written by the owning
                process, not narrated by the agent — see fleet-identity.py)
    repo    ->  the same row's `cwd`, resolved through `git worktree list`
    branch  ->  the harness writes `gitBranch` onto EVERY transcript record

So a consumer that checks the three assertions is checking a self-report against
better evidence that was available without asking. That consumer's only reachable
negative is "the pane never launched" — which the registry answers directly, and
more cheaply. ⛔ A control whose negative is reachable only by a condition another
instrument reports better is decorative in the sense of #26.

What `ROLE-READY` is genuinely good for is its POSITION. It is the only marker in
the system that says *everything before this was bootstrap*. Without it there is
no window to audit. So this tool does not treat the token as an assertion to be
confirmed; it treats it as PUNCTUATION, and audits the interval it closes.

    the token stops being a success claim  ->  nothing to countersign
    the interval it delimits gets audited  ->  a negative that is reachable

⚠ That reframe answers ARCHITECT's objection on #20 — "a template is a claim
someone else made that you sign" — by removing the signature rather than adding a
second branch to it. A delimiter cannot overclaim, because it claims nothing.

⛔ AND IT SUPPLIES THE MISSING INTERLOCK. TEAMLEAD's hard half: DEVOPS reported a
bootstrap failure AND emitted ROLE-READY in the same turn, so "readiness" and "a
failure occurred" are independent channels. They are independent IN THE AGENT'S
NARRATION. They are joined in the transcript, because the tool_use records and the
token are one ordered stream. The interlock does not need to exist in the agent's
vocabulary and does not depend on the agent choosing to speak.

⚠ Limits, stated rather than discovered:
  · This reads the TRANSCRIPT, not stdout. A pane cannot read a peer's stdout;
    it can read every peer's transcript, and fleet-identity.py already does.
    Those are different instruments for the same content and only one is barred.
  · Step->call matching is textual (see match_step). A step whose anchors are
    partly present is reported UNDECIDED, never EXECUTED. Converting a partial
    match into a pass is the exact §12 failure this repo keeps filing.
  · `NFORMA_ROLE` is per-process environment and is NOT cross-pane readable. The
    role leg is therefore checked against the registry name and the bootstrap
    text, and the env leg is reported UNKNOWN. It is not reported as agreeing.
  · A transcript is append-only but a session can be resumed; the bootstrap
    window is taken as the FIRST user prompt to the FIRST ROLE-READY, so a
    resumed session is audited on its original bootstrap, which is the intent.

Exit: 0 audited, no negative · 1 at least one NEGATIVE · 2 at least one role
      UNAUDITABLE (unknown is not a pass) · 3 the built-in known-positive failed,
      so the harness is broken and every verdict it printed is void.
"""
import argparse, glob, json, os, re, subprocess, sys, tempfile

SESSIONS = os.path.expanduser("~/.claude/sessions")
PROJECTS = os.path.expanduser("~/.claude/projects")
ROLES = ["TEAMLEAD", "ARCHITECT", "DEVOPS", "DX", "DEV1", "DEV2", "DEV3", "DEV4", "DEV5"]

TOKEN_RE = re.compile(r"ROLE-READY\s+(\S+)\s+repo=(\S+)\s+branch=(\S+)")

# Steps are written two ways in the bootstraps this fleet has actually used:
#   legacy : "1. Run: /rename DEV2 2. Read prompts/DEV.md ..."
#   recipe : "(1) Run: echo $NFORMA_ROLE && cat $NFORMA_ROLE_PROMPT -- then adopt ..."
# Only "Run:" steps are auditable for execution; a "Print ..." or "Read ..." step
# names no command, so this tool must not pretend to have checked it.
RUN_RE = re.compile(r"Run:\s*(.+?)(?=\s*(?:--|—|\(\d+\)|\d+\.\s|$))", re.S)

# Words that carry no discriminating power in a shell command. Matching on these
# would let any tool call satisfy any step.
STOPWORDS = {"then", "and", "the", "your", "from", "with", "this", "that", "into"}


def anchors(cmd):
    """Distinctive tokens a real invocation of `cmd` would have to contain.

    ⚠ Deliberately includes leading-slash words. `/rename DEV2` anchors on
    `/rename`, which no Bash tool_use can ever contain — that is the point. A
    step naming an action bound to a different actor is UNEXECUTABLE, and the
    audit should say so rather than quietly find nothing to check.
    """
    toks = re.findall(r"/[a-z][a-z-]{2,}|--[a-z][a-z-]{2,}|\$[A-Z_]{3,}|[a-zA-Z][\w.-]{3,}", cmd)
    out = []
    for t in toks:
        low = t.lower()
        if low in STOPWORDS:
            continue
        out.append(low)
    return out


def registry():
    """sessionId -> row, and name -> row. Written by the owning process."""
    by_name = {}
    for path in glob.glob(os.path.join(SESSIONS, "*.json")):
        try:
            row = json.load(open(path))
        except Exception:
            continue                     # one unreadable row is not a failed run
        if row.get("name") and row.get("sessionId"):
            by_name[row["name"]] = row
    return by_name


def transcript_for(sid):
    hits = glob.glob(os.path.join(PROJECTS, "*", f"{sid}.jsonl"))
    return hits[0] if hits else None


def main_tree(cwd):
    """The repository, not the worktree directory.

    ⛔ NOT basename(cwd): under #19's per-role worktrees that is "dev2", not
    "nForma-NEXT". Same correction fleet-preflight.sh carries.
    """
    try:
        out = subprocess.run(["git", "-C", cwd, "worktree", "list", "--porcelain"],
                             capture_output=True, text=True, timeout=10)
        if out.returncode == 0:
            for ln in out.stdout.splitlines():
                if ln.startswith("worktree "):
                    return ln.split(" ", 1)[1].strip()
    except Exception:
        pass
    return None


def blocks(rec):
    c = (rec.get("message") or {}).get("content")
    return c if isinstance(c, list) else []


def read_window(path):
    """Everything from the bootstrap prompt to the FIRST ROLE-READY emission.

    Returns (bootstrap_text, calls, token, token_rec, saw_token).
    `calls` is [(input_text, is_error)] in order.

    ⚠ The window CLOSES at the token deliberately. Steps performed afterwards did
    not support the token — that is the ordering the defect is about, and a
    whole-transcript scan would launder a late repair into an on-time success.
    """
    boot, calls, token, token_rec = None, [], None, None
    results = {}
    pending = []
    for ln in open(path, errors="replace"):
        try:
            rec = json.loads(ln)
        except Exception:
            continue                     # a malformed line is skipped, not fatal
        typ = rec.get("type")
        if typ not in ("user", "assistant"):
            continue
        content = (rec.get("message") or {}).get("content")
        if boot is None:
            # The bootstrap is the first plain-string user turn that is not a
            # harness injection. Injections all begin with a tag or a known lead.
            if typ == "user" and isinstance(content, str) and not content.lstrip().startswith("<") \
               and not content.lstrip().startswith("Another Claude session"):
                boot = content
            continue
        for b in blocks(rec):
            if not isinstance(b, dict):
                continue
            if b.get("type") == "tool_use":
                # ⛔ Only the `command` field of a command-running tool can satisfy a
                # `Run:` step. Matching against the whole input JSON read a
                # SendMessage whose PROSE said "/rename did not take on any pane" as
                # evidence that /rename ran — measured, on TEAMLEAD and DEVOPS, and
                # it is discriminates.py's documented case exactly: a statement
                # about a token contains the token. Execution is a property of what
                # was RUN, never of what was SAID about it.
                inp = b.get("input") or {}
                cmd = inp.get("command")
                if isinstance(cmd, str):
                    pending.append((b.get("id"), b.get("name") or "?", cmd))
            elif b.get("type") == "tool_result":
                results[b.get("tool_use_id")] = bool(b.get("is_error"))
            elif b.get("type") == "text" and typ == "assistant":
                m = TOKEN_RE.search(b.get("text") or "")
                if m and token is None:
                    token, token_rec = m, rec
        if token is not None:
            break
    for tid, tool, cmd in pending:
        calls.append((tool, cmd, results.get(tid)))
    return boot, calls, token, token_rec


def match_step(cmd, calls):
    """EXECUTED / ERRORED / UNEXECUTED / UNDECIDED for one `Run:` step.

    ⛔ UNDECIDED is a real outcome and is never folded into either neighbour. A
    partial anchor match means this tool cannot tell whether the step ran, and
    #26's whole point is that a control which cannot emit a negative is
    decorative — a control that emits a FALSE POSITIVE pass is worse.
    """
    # ⛔ A step whose command begins with `/` names a built-in belonging to the
    # human's input line. No tool can invoke it, so NO tool call can ever satisfy
    # this step and any match is spurious by construction. ARCHITECT on #20: the
    # action is not missing, it is MISADDRESSED — it exists and belongs to another
    # actor. Searching would only find prose discussing it, which is how this
    # function produced two false passes before it was written this way.
    if cmd.lstrip().startswith("/"):
        return "UNEXECUTABLE", ("names a built-in slash command — bound to the human input "
                                "line, unreachable by any agent tool, so no execution "
                                "record can exist")
    want = anchors(cmd)
    if not want:
        return "UNDECIDED", "no distinctive tokens in the step text"
    best, best_hits = None, 0
    for tool, shell, err in calls:
        low = shell.lower()
        hits = sum(1 for a in want if a in low)
        if hits > best_hits:
            best, best_hits = (tool, shell, err), hits
    if best_hits == 0:
        return "UNEXECUTED", f"no command run in the window contains any of {want}"
    if best_hits < len(want):
        missing = [a for a in want if a not in best[1].lower()]
        return "UNDECIDED", f"partial match; absent from the best candidate: {missing}"
    if best[2] is True:
        return "ERRORED", "the matching command returned is_error"
    if best[2] is None:
        return "UNDECIDED", "matching command has no recorded result"
    return "EXECUTED", "matched a command that returned without error"


def claim_negatives(claimed, observed):
    """Compare the three facts the token asserts against substrate readings.

    `claimed` and `observed` are dicts with keys role/repo/branch. An observed
    value of None means UNMEASURED and yields an entry in the second list, never
    a pass — #12: do not convert unknown into a plausible value.

    ★ Why this is checked at all, given that the token is not trusted:
    prompts/README.md:89 REQUIRES the line to quote values the agent just read,
    "never a value recalled from this message". Nothing has ever enforced that.
    A recalled value is precisely what disagrees with the harness's own record.
    """
    neg, unk = [], []
    for key, label in (("role", "role"), ("repo", "repo"), ("branch", "branch")):
        c, o = claimed.get(key), observed.get(key)
        if o is None:
            unk.append(f"{label} UNMEASURED — claimed {c!r}, no substrate reading available")
        elif c != o:
            neg.append(f"claimed {label} {c!r} != {o!r} read from substrate")
    return neg, unk


def audit(role, row):
    """One role's verdict. Returns a dict; `negatives` drives the exit code."""
    v = {"role": role, "negatives": [], "unknowns": [], "steps": [], "notes": []}
    if row is None:
        v["negatives"].append("no-session — no registry row for this role")
        return v
    sid = row["sessionId"]
    path = transcript_for(sid)
    if not path:
        v["unknowns"].append(f"no transcript file for sessionId {sid[:8]} — UNAUDITABLE")
        return v
    boot, calls, token, token_rec = read_window(path)
    v["session"] = sid[:8]
    v["calls"] = len(calls)
    if boot is None:
        v["unknowns"].append("no bootstrap prompt found — UNAUDITABLE")
        return v

    steps = [s.strip() for s in RUN_RE.findall(boot)]
    v["notes"].append(f"{len(steps)} `Run:` step(s) in the bootstrap")
    for s in steps:
        state, why = match_step(s, calls)
        v["steps"].append((s[:72], state, why))
        if state in ("UNEXECUTED", "ERRORED", "UNEXECUTABLE"):
            v["negatives"].append(f"step {state}: {s[:60]!r} — {why}")
        elif state == "UNDECIDED":
            v["unknowns"].append(f"step UNDECIDED: {s[:60]!r} — {why}")

    if token is None:
        # ⚠ Not automatically a negative. A pane may legitimately still be in its
        # bootstrap. Reported as unknown, because "has not yet" and "will not"
        # are different states and this instrument cannot separate them.
        v["unknowns"].append("no ROLE-READY emitted in this transcript — "
                             "still bootstrapping, or never will; not distinguishable here")
        return v

    claimed_role, claimed_repo, claimed_branch = token.group(1), token.group(2), token.group(3)
    v["token"] = f"ROLE-READY {claimed_role} repo={claimed_repo} branch={claimed_branch}"

    # ★ The claim/substrate cross-checks. These matter not because the token is
    # trusted but because prompts/README.md REQUIRES the line to quote values the
    # agent read, "never a value recalled from this message" — and nothing has
    # ever enforced that. A recalled value is exactly what disagrees here.
    top = main_tree(row.get("cwd") or ".")
    observed = {
        "role": role,                                  # registry name, process-written
        "repo": os.path.basename(top) if top else None,
        # ★ The harness stamps gitBranch onto the very record carrying the claim,
        # so this compares the assertion against its own substrate at the instant
        # it was made — not against the branch now, which agents legitimately move.
        "branch": token_rec.get("gitBranch"),
    }
    neg, unk = claim_negatives(
        {"role": claimed_role, "repo": claimed_repo, "branch": claimed_branch}, observed)
    v["negatives"] += neg
    v["unknowns"] += unk
    v["unknowns"].append("$NFORMA_ROLE is per-process and not cross-pane readable — "
                         "the env leg of the identity triple is UNMEASURED, not agreeing")
    return v


# ---------------------------------------------------------------------------
# ⛔ THE KNOWN-POSITIVE. #26: "Every control ships with its known-positive, and
# the known-positive must exist in the repaired state."
#
# These two synthetic transcripts differ in ONE way: whether a bootstrap step has
# an execution record. Both emit a perfectly well-formed ROLE-READY whose three
# facts are all correct. If the audit reports them the same, it cannot see the
# defect it exists for, and every verdict above is void — exit 3, per
# discriminates.py's control semantics.
#
# ⚠ The clean case is modelled on the CURRENT recipe on main, not on the legacy
# bootstrap that produced the original defect. That is the clause #26 adds: the
# failing input must be constructible against the system in its INTENDED REPAIRED
# STATE. A slash-command step is still reachable there, because the recipe is
# edited by agents and that is the edit that already happened once.
# ---------------------------------------------------------------------------
CLEAN_BOOT = ("You are DEVX. (1) Run: echo $NFORMA_ROLE && cat $NFORMA_ROLE_PROMPT -- then adopt "
              "that file. (2) Run: git rev-parse --show-toplevel && git branch --show-current "
              "(3) Print exactly one line and nothing else, in this format: ROLE-READY ROLE "
              "repo=REPO branch=BRANCH")

# Identical, plus ONE step naming an action bound to the human's input line. Every
# other step, every tool call, and the emitted token are byte-identical to the
# clean case — so anything that reads these two the same is reading the token and
# not the bootstrap.
DIRTY_BOOT = ("You are DEVX. (1) Run: /rename DEVX (2) Run: echo $NFORMA_ROLE && "
              "cat $NFORMA_ROLE_PROMPT -- then adopt that file. (3) Run: git rev-parse "
              "--show-toplevel && git branch --show-current (4) Print exactly one line and "
              "nothing else, in this format: ROLE-READY ROLE repo=REPO branch=BRANCH")


def _synth(path, boot, include_calls):
    recs = [{"type": "user", "message": {"content": boot}}]
    if include_calls:
        recs += [
            {"type": "assistant", "message": {"content": [
                {"type": "tool_use", "id": "t1",
                 "input": {"command": "echo $NFORMA_ROLE && cat $NFORMA_ROLE_PROMPT"}}]}},
            {"type": "user", "message": {"content": [
                {"type": "tool_result", "tool_use_id": "t1", "is_error": False}]}},
            {"type": "assistant", "message": {"content": [
                {"type": "tool_use", "id": "t2",
                 "input": {"command": "git rev-parse --show-toplevel && git branch --show-current"}}]}},
            {"type": "user", "message": {"content": [
                {"type": "tool_result", "tool_use_id": "t2", "is_error": False}]}},
        ]
    recs.append({"type": "assistant", "gitBranch": "main", "message": {"content": [
        {"type": "text", "text": "ROLE-READY DEVX repo=nForma-NEXT branch=main"}]}})
    with open(path, "w") as fh:
        for r in recs:
            fh.write(json.dumps(r) + "\n")


def self_test():
    """Returns True if the audit DISCRIMINATES the two constructed states."""
    tmp = tempfile.mkdtemp(prefix="bootstrap-audit-kp-")
    good, bad = os.path.join(tmp, "good.jsonl"), os.path.join(tmp, "bad.jsonl")
    _synth(good, CLEAN_BOOT, include_calls=True)
    _synth(bad, DIRTY_BOOT, include_calls=True)   # same calls; the /rename step has none

    def verdict(p):
        boot, calls, token, _ = read_window(p)
        steps = [s.strip() for s in RUN_RE.findall(boot)]
        return [match_step(s, calls)[0] for s in steps]

    vg, vb = verdict(good), verdict(bad)
    print(f"  known-positive  clean bootstrap : {vg}")
    print(f"  known-positive  slash-command   : {vb}")
    ok_clean = vg and all(s == "EXECUTED" for s in vg)
    ok_dirty = "UNEXECUTABLE" in vb
    if not ok_clean:
        print("  ⛔ the clean case did not read as fully executed — the audit reports "
              "false negatives, so its negatives mean nothing", file=sys.stderr)
    if not ok_dirty:
        print("  ⛔ the unexecutable step did not produce UNEXECUTABLE — the audit CANNOT "
              "SEE the defect it exists for", file=sys.stderr)
    # ⛔ Known-positive #2. The step audit and the claim comparison are two
    # controls; #26 requires a known-positive PER control, and a passing control
    # elsewhere in the same file is not one.
    agree = {"role": "DEVX", "repo": "nForma-NEXT", "branch": "main"}
    drift = dict(agree, branch="dev2/role-ready-consumer")
    n_same, _ = claim_negatives(agree, agree)
    n_diff, _ = claim_negatives(agree, drift)
    _, u_none = claim_negatives(agree, dict(agree, branch=None))
    print(f"  known-positive  claim==substrate : {len(n_same)} negative(s)")
    print(f"  known-positive  claim!=substrate : {len(n_diff)} negative(s) {n_diff}")
    print(f"  known-positive  substrate absent : {len(u_none)} unknown(s), 0 negatives")
    ok_claim = (n_same == [] and len(n_diff) == 1 and len(u_none) == 1)
    if not ok_claim:
        print("  ⛔ the claim comparison does not discriminate agreement from disagreement, "
              "or silently passes an unmeasured value", file=sys.stderr)
    if ok_clean and ok_dirty and ok_claim:
        print("  ✅ both controls discriminated: an unexecutable step from an executed one "
              "(identical ROLE-READY on both), and a claim that matches substrate from one "
              "that does not")
        return True
    return False


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--roles", default=",".join(ROLES))
    ap.add_argument("--self-test-only", action="store_true")
    args = ap.parse_args()

    print("\033[1mBootstrap audit\033[0m — what each pane EXECUTED before it declared ready\n")
    print("Known-positive control (the audit is not trusted until this passes):")
    if not self_test():
        print("\n⛔ CONTROL FAILED — the harness is broken. No verdict below would be "
              "meaningful, so none is produced.", file=sys.stderr)
        return 3
    print()

    by_name = registry()
    roles = [r for r in args.roles.split(",") if r]
    if args.self_test_only:
        return 0

    neg = unk = 0
    for role in roles:
        v = audit(role, by_name.get(role))
        head = f"\033[1m{role}\033[0m"
        if v.get("session"):
            head += f"  session={v['session']}  calls-in-window={v['calls']}"
        print(head)
        if v.get("token"):
            print(f"    token   {v['token']}")
        for s, state, why in v["steps"]:
            colour = {"EXECUTED": "32", "UNEXECUTED": "31", "ERRORED": "31", "UNEXECUTABLE": "31"}.get(state, "33")
            print(f"    \033[{colour}m{state:<10}\033[0m Run: {s}")
        for n in v["negatives"]:
            print(f"    \033[31mNEGATIVE\033[0m   {n}")
        for u in v["unknowns"]:
            print(f"    \033[33mUNKNOWN\033[0m    {u}")
        neg += len(v["negatives"])
        unk += len(v["unknowns"])
        print()

    print(f"\033[1mSummary\033[0m  {len(roles)} roles · {neg} negative · {unk} unknown")
    print("⚠ UNKNOWN is not a pass. It is the count of propositions this instrument "
          "did not establish.")
    if neg:
        return 1
    return 2 if unk else 0


if __name__ == "__main__":
    sys.exit(main())
