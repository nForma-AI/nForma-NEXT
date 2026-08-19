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

# DEV.md is a template shared by DEV1..DEV5, so the role->file map is not identity.
PROMPT_FOR = {r: f"prompts/{r}.md" for r in ["TEAMLEAD", "ARCHITECT", "DEVOPS", "DX"]}
PROMPT_FOR.update({f"DEV{i}": "prompts/DEV.md" for i in range(1, 10)})


# ⚠ A hash short enough to collide is not a comparison. The bootstrap emits 12
# chars; at 1 char a claim reads CURRENT roughly 1 in 16 times. Anything shorter
# than this is UNVERIFIED — refused, not compared. (Reviewer's measurement: the
# live half of a two-clause prefix test, where the second clause never differed
# from the first across five cases and only widened what could pass.)
MIN_DOCTRINE = 7


def doctrine_verdict(claimed, current):
    """WHICH VERSION of its prompt was this pane launched with?

    Pure, so it can carry its own known-positive AND known-negative. It shipped
    with neither in the first revision — the only control in this file to arrive
    that way, in a file whose --self-test refuses every verdict when a control
    fails. It asserted a standard it exempted its own newest check from.

    Returns (state, note). States are distinct because the remedies are:
      current     nothing
      STALE       relaunch that pane; a prompt loads at session start
      UNKNOWN     ⛔ ABSENT IS NOT CURRENT. A three-field token is SILENT about
                  doctrine, and silence must never resolve to a pass — that is
                  the #20 defect, where a fact with no slot rendered as absent
                  rather than unknown.
      UNVERIFIED  the comparison could not be made; not a pass either
    """
    if claimed is None:
        return "UNKNOWN", ("no doctrine= in the token — this pane predates the hash step, "
                           "so its prompt version is UNKNOWN, not current")
    if len(claimed) < MIN_DOCTRINE:
        return "UNVERIFIED", (f"doctrine={claimed!r} is shorter than {MIN_DOCTRINE} chars — "
                              "too short to discriminate; refused rather than compared")
    if not current:
        return "UNVERIFIED", "could not hash the prompt at HEAD — doctrine UNVERIFIED, not verified"
    if current.startswith(claimed):
        return "current", ""
    return "STALE", (f"doctrine STALE: pane launched with {claimed}, HEAD has {current[:12]} — "
                     "this pane is executing a superseded prompt and cannot be told; "
                     "a prompt loads at session start")


def _hash_object(top, relpath):
    """git hash-object of the file AS COMMITTED AT HEAD, not as it sits on disk.

    ⛔ Deliberate: the working tree is shared and a peer's checkout moves it, so
    hashing the file on disk would compare a pane's launch-time doctrine against
    whatever branch someone else last checked out. HEAD of the pane's own tree is
    the stable referent.
    """
    out = subprocess.run(["git", "-C", top, "rev-parse", f"HEAD:{relpath}"],
                         capture_output=True, text=True)
    return out.stdout.strip() if out.returncode == 0 and out.stdout.strip() else None

# ⚠ `doctrine=` is OPTIONAL on purpose. Nine panes are running RIGHT NOW that
# emitted a three-field token, and they cannot be retrofitted — a prompt loads at
# session start. A consumer that required the new field would report the entire
# live fleet as malformed, which is #39 in the other direction: the producer
# changed, and the consumer asserted the NEW state space against old data.
TOKEN_RE = re.compile(
    r"ROLE-READY\s+(\S+)\s+repo=(\S+)\s+branch=(\S+)(?:\s+doctrine=(\S+))?")

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


QUOTED = re.compile('\'[^\']*\'|"[^"]*"', re.S)
SEPARATORS = re.compile(r"&&|\|\||;|\||\n")
ASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")


# ⛔ THE ONLY WORDS THAT MAY EVER BE SKIPPED IN COMMAND POSITION.
#
# These are shell GRAMMAR — reserved words of POSIX sh, plus the three keywords
# bash and zsh add. Skipping them is not the blocklist the position rule exists to
# avoid, because the set is fixed by a language specification and cannot grow with
# anyone's habits.
#
# ⚠ THE TEMPTATION IS TO WIDEN THIS, and it will arrive later, to someone who was
# not part of the conversation that created it. `env`, `nohup`, `timeout`, `nice`,
# `sudo`, `xargs`, `stdbuf`, `command`, `exec` all LOOK like grammar and are
# binaries or builtins that take a command as an argument. Adding any of them
# would make `sudo git push` resolve to EXECUTED — which is a guess, not a reading,
# because `sudo` may equally have failed to authenticate.
#
#   > The moment this list stops being derivable from the shell specification,
#   > it becomes the blocklist the position rule refused.
#
# Wrapped invocations are INDETERMINATE by design. That is the honest verdict and
# it is not an accuracy problem to be tuned away.
#
# ★ NOT HYPOTHETICAL. ARCHITECT reached for `timeout` by reflex while auditing every
# instrument in this repo for #26 — macOS does not ship it, so ALL NINE TOOLS
# returned 127 and produced a uniform, confident, meaningless table that would have
# read as a clean result for every row. The first wrapper on that list was chosen
# by a careful author, in this repo, the same afternoon. That is why this is a
# CONTROL (see keyword_control) and not a comment: a prose caveat is a check with
# no execution record, and this one has to survive its own author.
POSIX_RESERVED = {"!", "{", "}", "case", "do", "done", "elif", "else", "esac", "fi",
                  "for", "if", "in", "then", "until", "while"}
SHELL_ADDED = {"select", "function", "time"}   # bash/zsh keywords, not POSIX
GRAMMAR = POSIX_RESERVED | SHELL_ADDED

SHELL_KEYWORDS = {"if", "then", "else", "elif", "fi", "while", "until", "do", "done",
                  "for", "case", "esac", "select", "function", "time", "!", "{", "}"}


def keyword_control():
    """Refuse the run if SHELL_KEYWORDS has grown a word that is not shell grammar.

    ⛔ The failure this exists for is an EDIT, not an input — which is why no
    ordinary known-negative would catch it. Someone hits `sudo git push` reading
    INDETERMINATE, decides that is a false negative, and adds `sudo`. Every other
    control in this file still passes: the fixtures do not use sudo, the live
    fleet does not use sudo, and the change reads as a small accuracy improvement.
    The tool would then report a guess as a reading, in the direction of the
    finding its operator expects — the asymmetry from #26.
    """
    intruders = SHELL_KEYWORDS - GRAMMAR
    print(f"  known-positive  keyword set      : "
          f"{'grammar only' if not intruders else f'INTRUDERS {sorted(intruders)}'}")
    # The known-negative: the guard must actually reject a binary if one is added.
    would_reject = bool(({"sudo", "timeout", "env"} | SHELL_KEYWORDS) - GRAMMAR)
    print(f"  known-negative  a binary added   : "
          f"{'would be rejected' if would_reject else 'ACCEPTED — the guard is inert'}")
    if intruders:
        print(f"  ⛔ SHELL_KEYWORDS contains {sorted(intruders)}, which are not shell grammar. "
              f"A wrapper skipped in command position turns a GUESS into an EXECUTED verdict. "
              f"Wrapped invocations must stay INDETERMINATE.", file=sys.stderr)
    if not would_reject:
        print("  ⛔ the guard cannot reject a binary — it is inert and would permit the edit "
              "it exists to prevent", file=sys.stderr)
    return not intruders and would_reject
SUBSTITUTION = re.compile(r"\$\(|`")


def command_positions(shell):
    """The words this shell string actually invokes, as opposed to mentions.

    ⛔ MEASURED, not anticipated. Text presence was the matching rule and it read
    all three of these as EXECUTED:

        echo "git rev-parse --show-toplevel && git branch --show-current"
        grep -n "git rev-parse --show-toplevel && git branch --show-current" f
        git rev-parse --show-toplevel && git branch --show-current

    Only the third runs anything. ⇒ The fix is not a blocklist of echo/grep/cat —
    that enumerates the mentions you thought of. It is POSITION: quoted spans are
    removed, the remainder is split on shell separators, and the first bare word
    of each segment is what got invoked. A command named inside a quoted argument
    occupies no command position, whatever tool quoted it.

    ★ Same remedy as DX.md §19's "parse the last line POSITIONALLY, never search
    for the keyword", and as matching `goals/` rather than the word `goal`. #36
    names the class: MATCH ON SOMETHING A MENTION CANNOT PRODUCE. A quotation can
    reproduce any text; it cannot occupy a command position.
    """
    bare = QUOTED.sub(" ", shell)
    out = set()
    for seg in SEPARATORS.split(bare):
        for word in seg.split():
            if ASSIGN.match(word):
                continue                  # leading FOO=bar env assignments
            w = word.lstrip("(")
            if w in SHELL_KEYWORDS:
                continue                  # grammar, not a command — the command follows
            out.add(w)
            break
    return out, bool(SUBSTITUTION.search(bare)), bare


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


def env_of(pid):
    """One pane's environment, read from OUTSIDE it. Returns (vars, readable).

    ⛔ THIS FUNCTION EXISTS BECAUSE THE LIMIT IT REPLACES WAS FALSE. Earlier
    versions printed, on every pane of every run:

        "$NFORMA_ROLE is per-process and not cross-pane readable — the env leg of
         the identity triple is UNMEASURED, not agreeing"

    That was DESCRIBED, never run. `ps eww` reads any same-user process's
    environment: 37 variables recovered from each of the nine live panes. ⇒ The
    tool was emitting a false UNKNOWN nine times per run and calling it honesty.

    ★ The distinction that makes this worth a function: a limit you have MEASURED
    is a limit; a limit you have only DESCRIBED is a defect you have not looked
    at, and it has no input that could contradict it — a control with no reachable
    failing state, sitting in the section whose whole purpose is honesty. DX filed
    that on #26 with two of its own; this is mine.

    ⚠ `readable` is returned separately and is not inferable from an empty dict.
    A dead process and a process with no such variable are DIFFERENT STATES, and
    collapsing them is how "the check found nothing" becomes "the check passed".
    """
    out = subprocess.run(["ps", "eww", "-o", "command=", "-p", str(pid)],
                         capture_output=True, text=True)
    toks = out.stdout.split()
    env = {}
    for t in toks:
        if "=" in t:
            k, _, val = t.partition("=")
            if k and k.isupper() and k.replace("_", "").isalnum():
                env[k] = val
    # The control: a process whose environment we can read has SOME standard
    # variables. Zero of them means ps did not answer, whatever its exit code.
    readable = bool(env)
    return env, readable


def env_control(reg):
    """Known-positive and known-negative for env_of(), on the process class that matters.

    ⛔ THE FIRST TWO VERSIONS OF THIS CONTROL WERE BOTH WRONG, and the control
    caught both — the third and fourth times it has refused this tool's verdicts.

      v1  mutated `os.environ` and read this process back. `ps` reports the
          environment captured at EXEC, so an in-process mutation never appears.
      v2  spawned `/bin/sleep` with a nonce. macOS returns NO environment at all
          for SIP-protected system binaries: 8 bytes, just the command line.

    ⚠ v2's failure is the important one, because it is a WRONG-POPULATION defect
    (#1) and it would have been invisible in the other direction. Had the probe
    happened to succeed on a system binary, the control would have certified an
    instrument on a process class that is not the one it is used against. The
    panes run a user binary from ~/.local/bin, whose environment IS readable — so
    the control must run against a PANE, not against a convenient stand-in.

    Positive: a live pane's environment contains HOME. Negative: the same read
    does not contain a nonce that exists nowhere. Together these show the reader
    discriminates present from absent on the real population, which is the only
    claim env_of() makes. Third case: a pid that cannot exist must be UNREADABLE,
    never "absent" — dead and unset are different states.

    ⚠ Stated limit, and this one is RUN rather than described: `ps eww` yields no
    environment for SIP-protected binaries, so env_of() answers for agent panes
    and would silently report "absent" for a system process. Every caller here
    passes a pane pid.
    """
    live = next((r for r in reg.values() if r.get("pid")), None)
    if not live:
        print("  ⛔ no live pane in the registry to control against", file=sys.stderr)
        return False
    env, readable = env_of(live["pid"])
    pos = readable and "HOME" in env
    neg = "NFORMA_AUDIT_PROBE_7f3a" not in env
    _, ghost = env_of(2 ** 22)
    dead_ok = not ghost
    print(f"  known-positive  env of a live pane: "
          f"{f'{len(env)} vars incl. HOME' if pos else 'HOME NOT FOUND — reader is blind'}")
    print(f"  known-negative  a nonce variable  : "
          f"{'correctly absent' if neg else 'REPORTED PRESENT — reader invents values'}")
    print(f"  known-negative  env of dead pid   : "
          f"{'UNREADABLE (correct)' if dead_ok else 'readable — dead would read as unset'}")
    if not pos:
        print("  ⛔ cannot read a live pane's environment — every env verdict below would be "
              "a false ABSENCE, which reads exactly like a real finding", file=sys.stderr)
    if not dead_ok:
        print("  ⛔ a nonexistent process reads as readable — a dead pane would report its "
              "identity carrier as ABSENT rather than UNKNOWN", file=sys.stderr)
    return pos and neg and dead_ok


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
    # ⛔ The anchors are all present — but presence is what `echo "<the command>"`
    # also produces. Require the step's own leading word to occupy a COMMAND
    # POSITION in the matched shell string before calling this execution.
    lead = (cmd.split() or [""])[0].lower()
    positions, unresolved, bare = command_positions(best[1])
    if lead and lead not in {w.lower() for w in positions}:
        # ⛔ THREE-WAY, not two. ARCHITECT measured that the two-way version missed
        # four real-execution shapes — `sudo git push`, `xargs -I{} git push`,
        # `echo $(git push)`, `if git push; then` — and every miss landed in the
        # unknown bucket. ⇒ Safe for "did THIS pane comply", NOT safe for "how
        # widespread is non-compliance", because it inflates the rate. #20's
        # content IS a rate, and this tool is what measures the next one. Same
        # defect as the false positive above, pointed the other way.
        #
        # ★ The fix is still not a blocklist. Quoted vs unquoted is structural:
        #   only inside quotes            -> a MENTION. Text cannot run.
        #   unquoted, not command position -> INDETERMINATE. It may be wrapped
        #                                     (sudo/xargs), substituted, or an
        #                                     argument, and this parser cannot say.
        # Enumerating wrapper names would be the blocklist; noticing that a
        # segment has a shape we do not resolve is not.
        bare_words = {w.lower().lstrip("(") for w in bare.split()}
        if unresolved or lead in bare_words:
            return "INDETERMINATE", (
                f"{lead!r} appears UNQUOTED but not in a command position"
                + (" and the segment contains a command substitution" if unresolved else "")
                + " — it may be wrapped, substituted, or an argument. This parser cannot "
                  "resolve which, and an unresolvable input must not share a verdict with a "
                  "clean negative")
        return "MENTIONED-ONLY", (f"the matched command contains the step text but never invokes "
                                  f"{lead!r} — it appears only inside a quoted argument, so this "
                                  f"is a MENTION of the step, not a record of running it")
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
        elif state in ("UNDECIDED", "MENTIONED-ONLY", "INDETERMINATE"):
            v["unknowns"].append(f"step {state}: {s[:60]!r} — {why}")

    if token is None:
        # ⚠ Not automatically a negative. A pane may legitimately still be in its
        # bootstrap. Reported as unknown, because "has not yet" and "will not"
        # are different states and this instrument cannot separate them.
        v["unknowns"].append("no ROLE-READY emitted in this transcript — "
                             "still bootstrapping, or never will; not distinguishable here")
        return v

    claimed_role, claimed_repo, claimed_branch = token.group(1), token.group(2), token.group(3)
    claimed_doctrine = token.group(4)
    # ⛔ Reconstruct from what was MATCHED, not from a fixed template. The previous
    # version rebuilt the token from three fields; with a fourth present it would
    # have displayed a token the pane never emitted — a quiet lie rather than a
    # crash, which is the failure mode that survives review.
    v["token"] = token.group(0)
    v["doctrine"] = claimed_doctrine

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
    # ★ Leg 3 of the identity triple, MEASURED. See env_of() for why this is not
    # the "unmeasurable" it was previously reported as.
    env, readable = env_of(row.get("pid"))
    if not readable:
        v["unknowns"].append(f"could not read pid {row.get('pid')}'s environment — the env "
                             f"leg is UNKNOWN (process gone?), not absent")
    elif "NFORMA_ROLE" not in env:
        v["negatives"].append(
            "NFORMA_ROLE is ABSENT from this pane's environment, established by reading "
            f"{len(env)} of its variables from outside it. prompts/README.md calls this the "
            "authoritative identity carrier; on this pane it does not exist")
    elif env["NFORMA_ROLE"] != role:
        v["negatives"].append(f"NFORMA_ROLE={env['NFORMA_ROLE']!r} but the registry name is "
                              f"{role!r} — the identity triple disagrees with itself")
    # ★ WHICH VERSION of the doctrine is this pane executing?
    #
    # prompts/README.md argues the IDENTITY case correctly — `echo $NFORMA_ROLE`
    # is an off-pane effect rather than a claim the agent makes about itself — and
    # never makes the same argument for the prompt's CONTENT. ROLE-READY proves the
    # file was reachable, not which version was read.
    #
    # A pane running stale doctrine is the party LEAST able to report that it is,
    # so the hash is taken by the substrate at launch and merely quoted here.
    # ⚠ No `DEV#` fallback: PROMPT_FOR already holds DEV1..DEV9 and has no `DEV#`
    # key, so a regex fallback to it returned None for every input ever passed —
    # measured on DEV3, DEV12, DEVX. It produced no wrong verdict, and it read as
    # coverage while providing none. Removed rather than fixed; an unrecognised
    # role lands in the honest UNVERIFIED path.
    prompt = PROMPT_FOR.get(claimed_role)
    cur = _hash_object(top, prompt) if (top and prompt) else None
    state, note = doctrine_verdict(claimed_doctrine, cur)
    v["doctrine_state"] = state
    if state == "STALE":
        v["negatives"].append(note)
    elif state in ("UNKNOWN", "UNVERIFIED"):
        v["unknowns"].append(note)
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


# ⛔ THE KNOWN-NEGATIVE. Inputs the audit must REJECT.
#
# #26, clause added from this tool's own failure: a known-positive proves a
# control CAN fire and says nothing about whether it fires WRONGLY — and a false
# positive reads as health. ARCHITECT hit the same wall within the hour, with a
# signature fallback that resolved nine sessions to one file at an identical
# score while its known-positive passed throughout. Two tools, two roles, one
# hour. That is a rate, not an anecdote.
#
# ⚠ REAL DATA, not a fixture. `MENTION_REAL` is the actual `SendMessage` input
# that made this tool report `/rename DEVOPS` as EXECUTED — DEVOPS telling
# TEAMLEAD that /rename had NOT taken on any pane. A fixture contains only the
# failure you already imagined; this one was in the fleet's transcripts the whole
# time and was found by reading the rows instead of the summary.
#
# ★ ARCHITECT's sharper half, recorded because it applies here too: that instance
# was caught because the answer was TOO CLEAN (nine identical scores), which is
# aesthetic judgement rather than a control. The rejection path must be
# EXERCISED, not described — so these run on every invocation, before any verdict.
MENTION_REAL = json.dumps({
    "to": "nforma-next-3d [c9020a]",
    "summary": "DEVOPS: fleet /rename did not take on any pane",
    "message": "DEVOPS -> TEAMLEAD. Blocking operational finding. /rename took on ZERO of the "
               "9 fleet panes. All 9 have nameSource=derived.",
})

STEP_REAL = "git rev-parse --show-toplevel && git branch --show-current"

# ⚠ A SINGLE-command step, for the wrapper cases. STEP_REAL contains `&&`, so
# wrapping only its first half leaves `git branch --show-current` genuinely in a
# command position and every wrapper case reads EXECUTED for a correct reason —
# the fixture defeats its own test. Second time a fixture, not the matcher, was
# the defect here; the control caught both.
STEP_ONE = "git rev-parse --show-toplevel"


def known_negative():
    """Every case here must NOT read EXECUTED. The last one must still read EXECUTED —
    a rejection rule that also kills true positives is a worse control, not a safer one."""
    cases = [
        ("real SendMessage prose (the input that caused the original false pass)",
         [("SendMessage", MENTION_REAL, False)], "/rename DEVOPS", False),
        ("the step echoed inside a quoted argument",
         [("Bash", f'echo "{STEP_REAL}"', False)], STEP_REAL, False),
        ("the step grepped for in a file",
         [("Bash", f'grep -n "{STEP_REAL}" notes.md', False)], STEP_REAL, False),
        ("the step genuinely run, after an unrelated leading command",
         [("Bash", f"cd /tmp && {STEP_REAL}", False)], STEP_REAL, True),
        ("the step run behind a shell keyword (`if git …; then`)",
         [("Bash", f"if {STEP_ONE}; then echo ok; fi", False)], STEP_ONE, True),
        ("the step piped into (`cat f | git …`)",
         [("Bash", f"cat f | {STEP_ONE}", False)], STEP_ONE, True),
        ("a single-command step echoed — still only a mention",
         [("Bash", f'echo "{STEP_ONE}"', False)], STEP_ONE, False),
    ]
    # ⚠ ARCHITECT's shapes: each RUNS the step, so none may read EXECUTED here only
    # because the parser resolved it — but none may read MENTIONED-ONLY either.
    # MENTIONED-ONLY asserts "text cannot run", which is FALSE for all of these.
    # They must land in INDETERMINATE, the bucket that says so.
    wrapped = [("wrapped in sudo", f"sudo {STEP_ONE}"),
               ("driven by xargs", f"xargs -I{{}} {STEP_ONE}"),
               ("inside a command substitution", f"echo $({STEP_ONE})")]
    ok = True
    for label, shell in wrapped:
        state, _ = match_step(STEP_ONE, [("Bash", shell, False)])
        good = state == "INDETERMINATE"
        print(f"  known-negative  {'✅' if good else '⛔'} {state:<15} {label} — must not read "
              f"MENTIONED-ONLY (it really ran)")
        ok = ok and good
    for label, calls, step, want_executed in cases:
        state, _ = match_step(step, calls)
        got = (state == "EXECUTED")
        flag = "✅" if got == want_executed else "⛔"
        if got != want_executed:
            ok = False
        print(f"  known-negative  {flag} {state:<15} {label}")
    if not ok:
        print("  ⛔ the audit either accepted a MENTION as execution, or rejected a genuine "
              "one. Either way its EXECUTED verdicts are not evidence.", file=sys.stderr)
    return ok


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
    ok_neg = known_negative()
    ok_env = env_control(registry())
    # ⛔ Known-positive #3, added because the doctrine check shipped with NEITHER a
    # positive nor a negative — the only control here to do so, in a file that
    # refuses every verdict when a control fails.
    CUR = "abcdef0123456789abcdef0123456789abcdef01"
    d_cur = doctrine_verdict(CUR[:12], CUR)[0]
    d_stale = doctrine_verdict("ffffffffffff", CUR)[0]
    d_absent = doctrine_verdict(None, CUR)[0]
    d_short = doctrine_verdict("abc", CUR)[0]
    d_nohash = doctrine_verdict(CUR[:12], None)[0]
    print(f"  known-positive  doctrine current : {d_cur}")
    print(f"  known-positive  doctrine stale   : {d_stale}")
    print(f"  known-positive  doctrine absent  : {d_absent}   (ABSENT IS NOT CURRENT)")
    print(f"  known-positive  doctrine short   : {d_short}   (refused, not compared)")
    print(f"  known-positive  cannot hash HEAD : {d_nohash}")
    ok_doc = (d_cur == "current" and d_stale == "STALE" and d_absent == "UNKNOWN"
              and d_short == "UNVERIFIED" and d_nohash == "UNVERIFIED")
    if not ok_doc:
        print("  ⛔ the doctrine check does not discriminate a stale prompt from a current "
              "one, or resolves a MISSING field to a pass", file=sys.stderr)
    ok_kw = keyword_control()
    # ⛔ EVERY control joins this conjunction. The rebase that produced this line had
    # `ok_doc` on one side and `ok_kw` on the other, and taking either side whole
    # would have DROPPED a control silently — it would still run, still print, and
    # its result would be discarded. That is #26 inside a merge resolution, and it is
    # why a conflict on a conjunction is never a positional conflict.
    if ok_clean and ok_dirty and ok_claim and ok_neg and ok_env and ok_doc and ok_kw:
        # ⚠ "every", not a numeral. This line read "both controls" while printing
        # five, then ten, then thirteen — a hand-counted number describing a list
        # drifts on the next addition and emits no error while doing it. DEVOPS
        # hit the identical drift in a file that inherited this string from here,
        # two hours after removing the same defect from tools/README.md's header.
        # A count that is not computed is a claim nobody re-checks.
        print("  ✅ every control discriminated: an unexecutable step from an executed one "
              "(identical ROLE-READY on both), a claim that matches substrate from one that "
              "does not, a MENTION of a step from a record of running it, and a wrapped or "
              "substituted invocation from either, and a stale prompt version from a current "
              "one — with a MISSING doctrine field reading UNKNOWN rather than either")
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
            colour = {"EXECUTED": "32", "UNEXECUTED": "31", "ERRORED": "31", "UNEXECUTABLE": "31", "MENTIONED-ONLY": "33", "INDETERMINATE": "33"}.get(state, "33")
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
