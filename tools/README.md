# Fleet instruments

Six tools, each built because a reading was believed and turned out to be wrong. Every one
carries the incident that produced it in its own docstring — the measurement is the
justification, not the description.

⚠ **Exit codes are load-bearing.** Every tool distinguishes *the answer is no* from *I
established nothing*. A run that establishes nothing exits **2** and must never be read as
"all clear". This is the single convention worth carrying to any other tool here.

| tool | question | exit codes |
|---|---|---|
| `fleet-context.py` | how much context does each agent have left? | 0 none due · 1 due · **2 scan established nothing** |
| `fleet-identity.py` | which role is this session, and which pane runs it? | 0 resolved · **2 population too small** · **2 own-session control failed** |
| `discriminates.py` | can this check tell the two states apart at all? | 0 discriminated · **2 non-discriminating, verdict refused** |
| `daintree-control.py` | is the fleet-status instrument answering, or blind? | 0 control passes · **2 VOID** |
| `wake-yield.py` | did that interruption produce work, or churn? | 0 |
| `bootstrap-audit.py` | did the pane EXECUTE its bootstrap, or only declare it? | 0 clean · 1 negative · **2 unauditable** · **3 known-positive failed** |
| `doctrine-version.py` | which version of its role prompt is each agent running? | 0 all current · 1 an agent is stale · **2 established nothing** |

## What each one is for

**`fleet-context.py`** — reports per-session context depth so "compact this agent" and
"collect its friction report" are decisions made on a number rather than a proxy. Two roles
independently inferred a context state from a proxy and were wrong in the dangerous
direction: one read an empty input box as a completed compaction and re-tasked agents it
believed had headroom; one recommended compacting a session at 79% it had never measured.

⚠ Carries three hard-won behaviours: it sweeps **every** project directory (an agent in a
worktree gets its own, and a pane at 97.7% was missed by a single-directory scan); it treats
the fleet as a **declared** roster and demands a *distinct session per role*; and it flags
**`SHARED FILE`** when one transcript carries two interleaved agents, because a file is not
an agent.

**`fleet-identity.py`** — answers two joins, and they are not equally hard.

*Session → name and role* is **exact**: `~/.claude/sessions/<pid>.json` carries `sessionId`, which
IS the transcript filename. ⚠ This file previously said "there is no shared key" flatly. That is
true of `terminal.list` and false of the registry, and the over-broad claim was read as a property
of the system — one role rebuilt the name join by hand because this paragraph said it was
impossible. The registry also carries `nameSource`, the only field that separates a renamed session
from an auto-named one; ⛔ the predicate is **key absence**, never `== "user"`, and a checker
written against the value never fires.

*Session → pane* genuinely has no shared key and still joins on **content** — rare tokens from
recent output matched against pane scrollback. That path needs the Daintree MCP; without it the tool
falls back to the registry report and says `UNAVAILABLE` on stderr rather than printing an empty
table. ★ Its known-positive is by construction: the process runs inside a session, so that session
must appear in the join. Proven to discriminate — break the join and it exits **2** with zero rows,
rather than printing a clean-looking table of nothing.

**`discriminates.py`** — refuses a verdict when two states produce identical readings.
Built after `grep -c "46.6%"` returned `1` on both a worktree and `origin/main` and was read
as *"the states agree"*: the worktree was 163 commits behind and the figure had been
retracted, and **a retraction quotes the number it retracts.**

> Identical readings from a discriminator are an instrument failure, not evidence of sameness.

**`daintree-control.py`** — a known-positive control for the fleet-status instrument, so a
blind poller cannot log a quiet cycle that reads as a healthy fleet. ★ It terminates the
regress on something known **by construction**: at least one pane must report `working`,
because the agent running the check is one.

**`wake-yield.py`** — pairs an interruption's cost with its yield. Cost alone is
uninterpretable: an agent woken into useful work and one woken into churn consume context
identically.

**`bootstrap-audit.py`** — audits the interval a `ROLE-READY` line closes, rather than the
three facts it asserts. ⛔ Measured on the live nine-pane fleet: **every token was true in all
three facts it carries, and every bootstrap had a step with no execution record** — so a
consumer that verified the assertions would have passed all nine. The token is treated as
punctuation delimiting the bootstrap window, never as a claim; the audit is of what ran inside
that window. See #20.

## Conventions worth copying

- **Exit 2 for "established nothing."** Absence of a finding and absence of a measurement are
  different states and must not share an exit code.
- **State the caveat on every run, not in the docs.** Each tool prints what its numbers do
  *not* establish, because a caveat that lives only in a README is read once.
- **Prove the failure path.** `daintree-control.py` takes a `DAINTREE_CFG` override purely so
  its VOID path can be exercised — a control that has only ever passed is not a control.
- **Roll the baseline forward.** A `--since` diff against a *fixed* snapshot re-reports the
  same event on every run. Measured: one compaction was reported as news four sweeps in a
  row, against a baseline 172 minutes old. **An alarm that fires forever on one event trains
  its reader to ignore it** — which is worse than not firing, because the reader also stops
  seeing the next one. Snapshot *after* reporting, so each run measures one interval.
- **A duplicate alarm and a broken alarm are indistinguishable to the reader.** Both produce
  output that is safe to skip. Treat repeat-firing as a defect with the same severity as
  silence.
- **Never read an exit code through a pipe.** `cmd | head; echo $?` reports *head's* status, and
  `${PIPESTATUS[0]}` expands to empty in zsh — both print something that looks like a measurement and
  is not one. Redirect to a file and check `$?` on the bare command. ⚠ Two independent instances in one
  session, ten minutes apart, in two different roles, *both while verifying instrument integrity*: one
  reading `tail`'s status and nearly filing a working validator as an entrypoint that cannot fail, one
  reading an empty `PIPESTATUS` and printing `exit=` having measured nothing. That it caught two
  careful readers in the act of being careful is why it is a convention and not a note.
- ⛔ **A known-positive proves a control CAN fire. It does not prove the control fires
  CORRECTLY.** Measured, inside the tool built for #26: `bootstrap-audit.py`'s known-positive
  passed — it genuinely discriminated a defective bootstrap from a clean one — and the same run
  reported two **false passes** against live data, because a step was matched against any tool
  input containing its text, and two panes had *messaged each other that the step did not
  execute*. A report of non-execution quotes the thing that did not execute. ⇒ #26's test
  (*name the input that makes this emit a negative*) is **necessary and not sufficient**; it
  says nothing about the false-positive direction, and a control that passes it can still be
  wrong in the direction that reads as healthy. Pair every known-positive with a known-negative
  drawn from **real** data, not from a fixture.
- **Match execution against what was RUN, never against what was SAID about it.** The false
  passes above came from searching a tool call's whole input. Prose that discusses a command
  contains the command; only the `command` field is evidence that it ran. This is
  `discriminates.py`'s retraction case — *a retraction quotes the claim it retracts* — one
  layer up, in a different instrument, found the same day.
- **Always brace a ref variable — `${REF}:path`, never `$REF:path`.** zsh applies its history
  modifiers to an unbraced `$VAR:`, so `$P:tools/README.md` expands to `c29aa60ools/README.md`
  (`:t` = tail) and `$B:scripts/…` expands with `:s` consumed. ⛔ **The failure mimics a domain
  answer:** git replies `unknown revision or path not in the working tree`, which reads as *the
  file is not there*. Measured twice in one session — one produced two empty fixtures and four
  exit codes nearly filed as a broken checker; the other was one step from reporting
  `tools/README.md` missing from `main` and inverting a closure verdict about that very file.
  ★ **It is data-dependent, which is the part that makes it dangerous:** in the same script
  `$P:goals/`, `$P:scripts/` and `$P:.daintree/` were all correct, because only the letters that
  happen to be modifiers bite. A script can be right nine times and wrong on the tenth path.
  Same family as the exit-code rule above — an idiom that answers a different question while
  looking like it answers yours.
- **Pin a sweep to an immutable SHA, not to a ref.** `git rev-parse origin/main` once, then read
  everything at that SHA. ⛔ A worktree gets its own `HEAD`, index and logs, but `refs/remotes`
  lives in the **common** `.git` — so `git show origin/main:<path>` resolves the ref *at read
  time* and follows every peer's fetch. Measured: `origin/main` advanced mid-audit under a
  pinned-*looking* read; two `git ls-tree origin/main scripts/` calls twenty minutes apart
  returned 2 files and then 3. **Only an immutable SHA pins**, and worktree isolation does not
  change this — it isolates the working tree, not the refs.
  ⚠ **Pinning protects the READ, not the WRITE.** The two are different propositions and the
  rule covers only the first. A branch cut from a pinned SHA still has to land on a moving
  target, so a peer editing the same file mid-flight produces a merge conflict that no amount of
  pinning prevents — measured, on the very PR that added this rule. Re-pin and rebase before
  pushing; expect the conflict rather than being surprised by it.
- **Whitespace-normalise before matching a rendered body.** `#23`'s rule is *verify by content,
  never by position* — this is the failure mode one step inside it. A content predicate is still
  positional if its unit is the LINE: `"no reachable passing state"` returned **False** against a
  PR body that contains exactly that phrase, wrapped. ⇒ The artifact was correct and the check was
  not, which is indistinguishable from the artifact being wrong. Collapse runs of whitespace on
  both sides first. ⚠ Measured twice the same day, at two altitudes: once against a rendered PR
  body, once against a wrapped Markdown bullet where a `grep` reported *"not there"* for
  *"not looked at"*.
- ⛔ **Restricting to the `command` field was NOT enough, and the gap was measured rather than
  imagined.** `echo "git rev-parse --show-toplevel"` and `grep -n "git rev-parse …" f` both read
  **EXECUTED**: they are command fields, and they contain every anchor. ⇒ **Match on POSITION,
  not on presence.** Strip quoted spans, split on shell separators, take the first bare word of
  each segment — that is what was *invoked*. A command named inside a quoted argument occupies
  no command position, whatever quoted it. ★ Not a blocklist of `echo`/`grep`/`cat`: a blocklist
  enumerates the mentions you thought of. This is #36's rule — **match on something a mention
  cannot produce** — and the fourth independent rediscovery of it in this repo, alongside
  `DX.md` §19's positional last-line parse and matching `goals/` rather than the word `goal`.
- ⛔ **A limit you have MEASURED is a limit. A limit you have only DESCRIBED is a defect you
  have not looked at** — and it has no input that could contradict it, which makes it a control
  with no reachable failing state (#26) sitting in the section whose whole purpose is honesty.
  Measured: `bootstrap-audit.py` printed *"$NFORMA_ROLE is per-process and not cross-pane
  readable — UNMEASURED, not agreeing"* on every pane of every run. It was never run. `ps eww`
  reads any same-user process's environment; 37 variables came back from each of the nine live
  panes. ⇒ The tool emitted a **false UNKNOWN nine times per run and called it honesty.** The
  test transfers unchanged: *name the input that would falsify this limit.*
- ⚠ **Control the instrument on the population it is USED on, not on a convenient stand-in.**
  The env reader's known-positive was first built against `/bin/sleep` and failed: macOS returns
  **no environment at all** for SIP-protected system binaries. Had it happened to pass, it would
  have certified the reader on a process class it is never pointed at — #1's wrong-population
  defect, inside a control. It now runs against a live agent pane.
- ⛔ **An unresolvable input must not share a verdict with a clean negative** — the exit-2
  convention applied *inside* a function rather than at a process boundary. Measured by
  ARCHITECT against the position rule above: `sudo git push`, `xargs -I{} git push`,
  `echo $(git push)` and `if git push; then` all RUN the command and all read as *not found*.
  Every miss landed in the unknown bucket, which is safe for *"did this pane comply?"* and
  **unsafe for *"how widespread is non-compliance?"*** — it inflates the rate, and #20's content
  **is** a rate. ⇒ Same defect as the false positive above, pointed the other way, and invisible
  because it produces the finding you were already expecting. Split three ways: *only inside
  quotes* → `MENTIONED-ONLY` (text cannot run); *unquoted but not in a command position, or a
  command substitution* → `INDETERMINATE` (it may be wrapped, substituted, or an argument, and
  the parser cannot say). ★ Still not a blocklist: enumerating wrapper names would be one,
  **noticing that a segment has a shape you do not resolve is not.**
- **A mention is a third state, not a negative.** `MENTIONED-ONLY` means *no execution evidence*,
  which is not *evidence of no execution*. It counts as unknown and never as a pass.
- **No secrets in source.** Tools needing the Daintree token read it from the user's own MCP
  config at runtime; it appears in none of these files.
