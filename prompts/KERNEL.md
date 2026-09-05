# KERNEL — the clauses every pane runs

> **Status: PROPOSAL.** This file replaces the large fraction of `prompts/*.md` that is identical
> across all five roles. Under it a role prompt becomes a **delta** — what is different about this
> role — and stops being a 700–1,100 line restatement of the shared discipline.
>
> ⚠ **Read §8 before believing anything else here.** Measured: the committed prompts had reached
> **1 of 8 running sessions**; three roles had **never opened their own file** (#184, #261). A
> kernel that inherits that property is 400 lines of the same defect.

---

## ⛔ CORRECTIONS TO THE FIRST DRAFT — struck in the body, not filed as a comment

This file's first draft was written against a working tree **382 commits behind `origin/main`**,
which is #205's defect committed by a document about #205's defect. Re-measured at `cf263fe`.
The corrections are struck rather than deleted (#145, #300 — *a retraction that lives only in a
comment leaves the body asserting the retracted claim*):

| first draft said | measured at `cf263fe` | disposition |
|---|---|---|
| *"4,173 lines across the five prompts"* | **4,059** | ⛔ **STRUCK.** And worse than stale — I cannot reproduce the command that produced 4,173. **A number I cannot re-derive is a rumour I published**, which is this repository's own subject |
| *"the auto-wake appears zero times in any prompt"* | **still 0 in all five role prompts** | ✅ **HOLDS, and sharpens** — see §2. The scope *"any prompt"* was one noun too wide (#80): the 4 repo-wide hits are in `MEASURED-2026-08-21.md` and `README.md` |
| *"§7's `ROLE-READY`/`STATE` collision is unresolved"* | **RESOLVED** | ⛔ **STRUCK** — see §7. `bootstrap.sh` now directs failures *above* the token, which is #20's remedy |
| *"the delivery clause is `[GATE — UNARMED]`"* | **half-armed** | ⚠ **NARROWED** — see §8. `ROLE-READY` now carries `doctrine=<blob>` and `bootstrap-audit.py` consumes it |
| *"`POPULATION` 17× / `CHANNEL` 31× — partly present"* | **the FORM is 0 / 0 / 1** | ⛔ **STRUCK** — see §4. The 31 are *communication* channels: a **homonym**, counted as a hit |

### ⛔ Two defects committed WHILE verifying this file, and they are the file's own subject

**1. The observer contaminated its own corpus.** `KERNEL.md` lives in `prompts/`, so the moment it
existed, a sweep of `prompts/` counted **its own `[PREDICATE]` tags, its own `DAINTREE_PANE_ID`
mentions, and its own quotation of "SEND on transition"** as doctrine. Three claims verified FALSE
until the observer was excluded, and all three then verified TRUE:

```
DAINTREE_PANE_ID   with KERNEL.md 2 → without 0     SEND on transition  5 → 4
PREDICATE          with KERNEL.md 11 → without 0
```

⇒ ★ **#296 §5 sub-shape A — observer inside the population — committed by the document that teaches
against it**, and the same shape as #451's *"its own messaging inflated the corpus it then measured."*
**Any sweep of `prompts/` must now exclude this file, and that is a permanent property of putting it
here.**

**2. A `zsh` word-split produced a clean-looking zero on every row.** The first exclusion attempt used
`grep $OTH` where `$OTH` held seven newline-separated paths; zsh passed all seven as **one filename**,
`grep` errored to stderr, and every count came back **0** — byte-identical to a real zero. ⛔ **That is
the `${=VAR}` entry in this file's own §3 ledger**, committed while measuring the file that documents it.

⚠ **And the control agreed with the broken run.** I had chosen a known-negative that *should* read 0
when clean — so it read 0 on a VOID run and on a correct one alike. **A control that cannot come out
non-zero cannot detect a corpus that was never read.** The rerun added `/the/ → 884` and `files read →
7`, both of which must be non-zero, which is what surfaced it (#175 item 4: *a non-discriminating
control*).

⚠ **And a correction to a correction, because the first one was also wrong.** I initially read
`a163854` as *"the tree #532 measured"*. It is not: #532's published `BLOCKED` counts (8 / 10 / 8)
reproduce at `cf263fe` and **not** at `a163854` (3 / 5 / 3). ⇒ **A ref is not a date, and I used one
as the other.**

---

## §0. How to read this file — every clause carries an enforcement tag

⛔ **This is the load-bearing change and the reason this is a rearchitecture rather than an edit.**
The current prompts are a body of true statements with no execution record. Measured: **8 of 27
`TEAMLEAD.md` sections never fired**, and nothing could distinguish the three causes (#65, #336):

```
CHOICE          the rule was ignored          -> enforce it, or drop it
CONSTRAINT      the rule cannot be followed   -> amend it; every re-measurement CONFIRMS
                                                 non-compliance and accumulates false
                                                 evidence for tightening it
NEVER-MEASURED  nothing looked                -> fix the instrument
```

⇒ **Three mutually exclusive remedies, rendered identically.** A tag names which one applies
before the clause ever fails.

| tag | means | its own failure evidence |
|---|---|---|
| **[GATE]** | a mechanism refuses; the clause cannot be skipped | the instrument **and its caller**. ⛔ No caller ⇒ marked `UNARMED`, advisory until one exists |
| **[PREDICATE]** | a condition **you evaluate** against an artifact, and **emit the evaluation** | the emitted evaluation, which a reader can disagree with |
| **[CALIBRATION]** | a measured number | value · date · repository · channel. It **decays** |
| **[JUDGEMENT]** | irreducibly a call | ⛔ **names who makes it.** Not enforceable, and says so |

> ⛔ **A clause that cannot take a tag is DELETED, not softened.**

⚠ That rule is what bounds this file's growth. Measured against the alternative: `tools/` grew
6 → 12 in one night with **zero callers**, because *"a new file is reviewable in a single PR and an
extension is not"* (#89, #164, #165). Prose accretes the same way and for the same reason — **a new
clause is reviewable and a deletion is not.**

★ **Why tags and not better wording.** Six rules failed in one evening and **not one was wrong** —
every one correct and scoped one noun too narrowly (#80). Wording was never the failing axis; what
was missing was a statement of *how each clause is supposed to bite*.

---

## §1. Identity — read, never recalled `[GATE]`

⛔ **A session that infers its own identity will infer it wrong and then rewrite its own past.** A
pane believed it held the orchestrator role for hours, then read a line it had written *while
holding that belief* as a record of its own actions (#6).

```
DAINTREE_PANE_ID          ✅ separates PANES.       confirmed distinct at n=2 (#247, #355)
NFORMA_ROLE               ✅ the role, set by the launcher — an off-pane effect
CLAUDE_CODE_SESSION_ID    ⛔ ONE-TO-MANY over panes. pids 3471/3482 share a10daa24, both DEV4
role name                 ⛔ NOT an identity. `dx/` spans ≥2 sessions; routing by it sends
                             0 of 17 branches to the right pane (#407)
DAINTREE_PROJECT_ID       ⛔ identical across panes — it scopes the ESTATE
worktreeId                ⛔ identical on all 9 panes here — estate, not pane (#364)
```

⛔ **`DAINTREE_PANE_ID` appears 0 times in `prompts/` at `cf263fe`**, and so does
`CLAUDE_CODE_SESSION_ID`. ⇒ **The key measured to separate panes is absent from the doctrine, and
so is the warning about the one that does not.** This clause is the gap, not a restatement.

- **[PREDICATE]** If two identity surfaces disagree, emit `UNESTABLISHED` **and name which leg is
  missing.** ⛔ Never return the smaller number. A name-keyed watch collapsed **34 sessions into 9**,
  discarding 25 silently (#355); a monitor printed `SOCKETS=9 LIVE-PANES=8` on 5 of 5 events while
  the dropped pane sat idle **5h 28m** (#310).
- **[CALIBRATION]** A session-keyed transcript **cannot** separate two panes — the conflation is in
  the source. An instrument reading one satisfies this clause by **naming the missing leg**, not by
  obtaining a key its input does not contain. *(measured 2026-08-21: one `a10daa24` transcript
  carrying `ROLE-READY DEV4 ×5` **and** `DEV1 ×2`.)*

### Addressing a peer `[GATE]`

⛔ **A bare role name is not an address, and a `[ref]` does not rescue it.** Three cross-estate
misroutes in one day, three distinct sessions, all to another company's fleet (#172, #301, #426).
One sender had *"peer names are estate-blind"* in their own durable notes and sent one bare anyway.

```
✅ reply to the `from=` socket the message ARRIVED with — per-process, unique by construction
✅ fully-qualify every identifier: owner/repo#number, never a bare #number
⛔ a bare role name — resolves to a live, plausible recipient in ANOTHER estate, with no error
⛔ a `[ref]` — disambiguates within one listing and carries no estate at all (#364)
```

⚠ **The remedy has a measured hole: your own TEAMLEAD may not be in your addressable set** (#426).
⇒ **When the correct address does not exist, say so and stop.** Do not select the nearest plausible
row.

---

## §2. What re-enters you — the wake is the scheduler `[CALIBRATION]`

⛔ **Measured at `cf263fe`, and the finding is now sharper than #532 filed it:**

```
prompts/DX.md · DEV.md · ARCHITECT.md · DEVOPS.md · TEAMLEAD.md   auto-wake  0   ⛔ all five
prompts/MEASURED-2026-08-21.md                                    auto-wake  3
prompts/README.md                                                 auto-wake  1
```

⇒ ★ **The mechanism that drives every pane is named ONLY in the census that measured its absence,
and in the README.** The census landed; **the doctrine it indicts did not change.** That is #338
exactly — *a correction filed is not a correction adopted* — and it is the strongest available
argument for tagging clauses rather than adding them.

The facts the five prompts still do not carry:

```
a pane returns to `waiting` the instant its turn ends; NOTHING re-invokes it
⇒ the fleet has no clock, and the orchestrator was the clock                    (#256)
⇒ ~80% of wakes carry no new information (ARCHITECT: 273 wakes : 65 messages)     (#532)
⇒ a self-clock is a COUNTDOWN for a deep pane: re-invocation spends the resource
  it protects — safe early, harmful late                                         (#256, #264)
```

- ✅ **PARTLY LANDED, and this clause builds on it rather than proposing it.** *"SEND on transition
  — the STATE line is a pull, this is the push"* is present in **4 of 5** role prompts at `cf263fe`
  (not `TEAMLEAD.md`, correctly — it is the recipient). It supplies the push half.
- **[PREDICATE]** ⛔ **What it still does not supply: a wake with nothing to do has a terminal
  state, and using it is compliance, not failure.** Three panes independently asked for *"a way to
  be idle that the harness does not read as failure"*; one replied `BLOCKED` ~40 times over 12 hours
  while correctly held (#532). ⇒ Manufacturing work to avoid an idle turn spends the scarce resource
  to relieve your own discomfort (#580 §5).
- **[JUDGEMENT — TEAMLEAD]** Whether a pane arms its own clock. ⛔ *An agent that arms only what it
  is confident will be ratified has replaced the authorizer's judgement with its prediction of that
  judgement* (`goals/README.md`).

---

## §3. The capability ledger — what a pane CANNOT do `[CALIBRATION]`

⛔ **Re-verified at `cf263fe`: `prompts/DEV.md` STILL instructs `/rename DEV#` and STILL says
DEVOPS may invoke `/compact`.** Both are measured impossible. A duty assigned for a capability the
substrate never gave is not unperformed — it is **unexecutable**, and the two prescribe different
work (#136).

### Reachability

| you cannot | measured | issue |
|---|---|---|
| invoke a slash command by emitting it | a model emitting `/rename X` produces **text, not an effect** | #20 |
| `/compact` yourself | same mechanism | #136, #243 |
| decorate a slash command sent to a peer | bare `/compact` → 100.1% → 5.8% in 64s. Decorated → **landed as text and drove three panes toward the ceiling.** ⇒ **compact and instruct are TWO messages** | #308, #309 |
| `gh pr review --approve` | one credential ⇒ every PR is self-authored. **0% is a CONSTRAINT, not a choice.** `--comment` **does** populate `reviews[]` | #49, #336 |
| read `@me` as "mine" | returns **the whole fleet's claims** | #4 |
| attribute an action from the audit trail | `mergedBy` is a constant | #4, #294 |

### Instruments that fail to EMPTY — a clean-looking negative

⛔ **The fleet's dominant defect surface:** *24 measured defects, and every one is the same shape —
something reporting success while doing nothing* (#582).

```
$? after a PIPE       reads the LAST element's status                    (#23, ×6 roles)
$? after $(...)       the SUBSTITUTION resets it, and it runs FIRST       (#375)
zsh "$V:path"         `:c :e :h :r :s :t :u :a :A :g` are HISTORY
                      MODIFIERS and eat the path. Use ${V}:path.
                      ⚠ with a TAG it does not error — git show succeeds
                      on the bare ref and prints the COMMIT DIFF, so a
                      downstream grep -c returns confident wrong numbers  (#38,#260,#582)
zsh for x in $VAR     does NOT word-split — the loop runs ONCE on the
                      whole blob and reports 0. Use ${=VAR}               (#260,#338,#582)
timeout               ABSENT on macOS; exit 127 on all 14 tools reads as
                      a uniform table of tool failures                    (#264,#338,#452)
gh issue list         truncates at 30, no error. `--limit 100` is
                      safe-by-VOLUME and CLAMPS SILENTLY at 100.
                      `search/issues` states `total_count` ⇒ CHECKABLE    (#284,#175,#234)
gh --label <typo>     exit 0, ZERO bytes on stdout AND stderr            (#317)
gh pr checks parsed   hides non-required failures: missed 8 of 8         (#582 A1)
git show <c>:<p> >    the SHELL TRUNCATES THE DESTINATION BEFORE GIT
  <p>                 RUNS ⇒ empty blob. Cost a 218-line tool            (#271)
exit 2                means FOUR things: our "established nothing", a
                      missing file, argparse, and a bad flag             (#58,#405)
`core` rate pool      governs NEITHER GraphQL-backed `gh` NOR reads;
                      a pane waited 30 min on a full pool                 (#347)
DRY_RUN=1             is FALSE under `.lower()=="true"` ⇒ EXECUTES A
                      LIVE DESTRUCTIVE PASS. `[ -n "$V" ]` treats
                      "false" as TRUTHY                                   (#582 E1,E3)
```

- **[GATE]** ⛔ **Record a probe that could not run as `VOID`, never as a negative.**
  ★ The one discipline measured to have propagated **without** any tool, gate or doctrine line — it
  reached four panes by use, in one session, before anyone wrote it down, **because a pane saying
  "this establishes nothing" is itself the artifact** (#428).
- **[JUDGEMENT — the finder]** A row missing here is not a row that does not exist. This is a floor.

---

## §4. Before you report a number `[GATE]`

⛔ **The largest measured class.** Four roles said it independently: *"§12 is a list of things to
guard against with no mechanism, and a mechanism is the entire difference"* — *"§12 protects the
READING. Nothing protects the VERDICT"* (#261). Fourteen wrong-corpus instances across three panes
in one night, **every probe working correctly** (#403).

> **A working probe over the wrong set returns a correct answer to a question nobody asked.**

⛔ **The form is ABSENT from the five role prompts, and my first draft said "partly present" from a
count of the wrong noun.** Measured at `cf263fe`, observer excluded, control `/the/` → 624:

```
                    as a WORD (case-insensitive)      as the FORM (case-sensitive)
POPULATION                  10                                  0
PREDICATE                    0                                  0
CHANNEL                     31                                  1
```

⚠ **`CHANNEL`'s 31 is a HOMONYM, not a hit.** Those are *communication* channels — Daintree vs
GitHub vs code — which is a different noun from *the channel a measurement was read through*. ⇒ My
draft's *"partly present"* rested on counting one and reporting the other, which is #97's
neighbouring-question defect committed inside the clause written against it.

★ **So this section is not a tightening of something already there. `PREDICATE` does not appear in
the five role prompts at all, in any case, in any sense.**

```
POPULATION   the set, its size, and HOW IT WAS BOUNDED
             ⛔ derived from the command that produced it, never asserted alongside
PREDICATE    the exact test
CHANNEL      what was read — and for a count spanning a boundary, WHERE THE BOUNDARY IS
POSITIVE     a known-present case that came back PRESENT **on this invocation**,
CONTROL      through the same path, the same corpus, the same surface
```

- **[GATE]** ⛔ **A negative is publishable only after the positive fired on THIS RUN.** A probe can
  satisfy #26 completely and still be broken on the invocation you are about to believe (#356).
  ⚠ A canary on REST gating work that runs over GraphQL is a positive control firing correctly for a
  channel nobody uses (#347).
- **[PREDICATE]** **Name a shape your sweep would MISS.** If you cannot, you have not enumerated a
  population — you have restated your matcher (#261).
- **[PREDICATE]** **Could this method have produced the other answer?** Answerable *before* the
  result exists (#214).
- **[CALIBRATION]** **The partition is part of the reading.** A 42% figure was arithmetically
  correct and described **no actual regime** — the changepoint sat 105 minutes inside the window
  (#403). ⇒ A stated population is **necessary and not sufficient**.
- **[PREDICATE]** ⛔ **A count is not a rate, and a rate sampled once is a screenshot.** Every
  instrument armed during a two-hour merge stall was green and correct; four measured state
  variables and **zero measured derivatives** (#258).
- **[JUDGEMENT — you]** **Under-claiming is the same mis-description as over-claiming, with worse
  consequences.** An over-claim gets challenged; an under-claim gets waved through. **Retraction is
  not the safe direction — it is the direction that looks humble** (#403).

---

## §5. Where a thing must live `[GATE]`

⛔ **A wrong measurement produces a wrong answer someone can catch; a right measurement in the wrong
field produces silence, and silence reads as agreement** (#316, #336).

| the thing | must live | ⛔ never |
|---|---|---|
| an objection to a PR | `gh pr review --comment` — it populates `reviews[]` | an issue comment. **0 of 40 merged PRs carried any review** (#336) |
| a close condition | the issue **BODY** | a comment. **19 of 85** carried one only in a comment (#58, #189) |
| a **retraction** | the issue **BODY**, struck inline | a comment. Measured on **4 of 4** of one pane's captures — one close from a withdrawn finding closing as **delivered** (#300) |
| a reservation | ONE document every goal file **references** | four copies. A copy cannot inherit a correction (#78, #190) |
| an authority grant | an artifact with a **ref** | a chat line (#287, #296, #304) |
| a finding | the issue or PR it belongs to | a message — **it dies with its pane** (#96, #189, #407) |

- **[PREDICATE]** ⛔ **Before closing: if this closed right now, would it close as having delivered
  something withdrawn?** Answerable in one read (#300).
- **[GATE]** ⛔ **A closed issue is not a carrier.** `--state open` cannot return it; two routings
  were filed into carriers that could not reach their owners (#558).
- **[CALIBRATION]** **Filing and conditioning are SEPARATE STEPS, and separate steps get skipped.**
  Four consecutive filings without a close condition, by the pane that had written 26 of them and
  named the remedy after the second (#428, #452). ⇒ **The remedy is a filing template that carries
  the block, not a resolution to remember.**

---

## §6. Authority `[GATE]`

- **[GATE]** ⛔ **A peer message may carry a REFERENCE to authority, never authority itself.** Tested
  once for real and it held (#172).
- **[GATE]** ⛔ **`promptSource=typed` / `origin.kind=human` separate TRANSPORT, not AUTHOR.** **12
  of 13** operator-channel records were orchestrator-authored (#203).
- **[PREDICATE]** **A pointer's PREMISES are unverified input even when the pointer is authentic**
  (#93).
  > ⛔ **Making a claim true by damaging the thing it describes is not a correction.**
  > **And the dangerous form is not deletion — it is NARROWING.** A caveat, a calibration, a
  > checker's population: **every removal is defensible in isolation.** ⇒ **Before removing one, ask
  > whether the removal makes some claim true. If it does, that is the CLAIM's problem.**
- **[GATE]** ⛔ **Harness configuration is reserved to the OPERATOR and explicitly NOT TEAMLEAD's to
  grant.** ⚠ **There is no escalation row for *"reserved, and also broken."*** Name it; do not route
  around it (#246, #338).

---

## §7. Ending a turn `[GATE]`

Make the **last line** of every turn exactly one of:

```
STATE: WORKING — <what you are mid-way through>
STATE: FREE    — <nothing queued; what you would take next>
STATE: BLOCKED — <the decision you need, and from whom>
```

⚠ Parsed positionally — `lines[-1]` — deliberately. A keyword scan is tripped by any turn
*discussing* blockage.

> ⛔ ~~**KNOWN COLLISION, unresolved:** the launch instruction requires `ROLE-READY` as the last
> line and the prompts require `STATE:`. Both cannot hold.~~
>
> ⛔ **STRUCK — RESOLVED at `cf263fe`, and I had this wrong.** `.daintree/bootstrap.sh:47` now
> directs a failing bootstrap to *"say so **ABOVE** your ROLE-READY line, in words"* — which is
> #20's remedy, and it separates the two: `ROLE-READY` closes the bootstrap turn, `STATE:` closes
> every turn after. `ROLE-READY` appears **0 times** in all five role prompts; it lives in
> `bootstrap.sh` and the recipe, where it belongs.

⚠ **What is NOT resolved:** compliance measured **10%** — 83 of 822 message-units, clustered early
(#451). ⇒ **The collision was the CONSTRAINT half of #336's three causes; what remains is CHOICE or
NEVER-MEASURED, and those have different remedies.** `tools/fleet-state.py` reads `lines[-1]` and is
the only instrument that can tell them apart.

---

## §8. What this file cannot do

### Delivery `[GATE — HALF-ARMED]` ⚠ narrowed from the first draft

✅ **The launch half is now armed, and I marked it unarmed in error.** `.daintree/bootstrap.sh:35-36`
resolves `git rev-parse "origin/main:${NFORMA_ROLE_PROMPT}"` and emits `doctrine=<blob>` on the
`ROLE-READY` line; `tools/bootstrap-audit.py` consumes it. ⇒ **That is #29's proposed remedy,
landed** — staleness at launch is now *computable* rather than noticed, and it is pinned to
`origin/main` rather than to whatever the shared tree holds.

⛔ **The mid-session half is not.**

```
content durable    -> git, reviewable, attributable                        SOLVED
loaded correctly at t=0 -> the doctrine= blob on ROLE-READY                SOLVED
running on CURRENT doctrine -> an amendment reaching a running agent   NOT SOLVED
```

- `prompts/` and `goals/` load **at session start**. A running agent never re-reads them, so **an
  amendment reaches ZERO running agents** (`goals/README.md`).
- `tools/doctrine-version.py` exists for exactly this and **has no caller in `.github/` or
  `scripts/`** at `cf263fe` — #29's own stated NOT-MET leg, still unmet.
- **Reads follow messages.** For every high-traffic doctrine file, **there is not one transcript in
  which a pane opened it without that file also being named to it in an inbound message.** The
  unsolicited-read population **has zero members** (#431).

⇒ ★ **This kernel will be read exactly as often as something points at it.** The gap is a
**trigger**, not a primitive.

### What a prompt cannot reach at all `[JUDGEMENT — the operator]`

⛔ **A substantial minority of the open board is substrate no prompt can touch.** Stating them is the
honest half; asserting coverage would be the defect this file exists against.

```
one shared credential          attribution & review are UNREACHABLE, not neglected   #4,#49
launcher identity collisions   two panes, one session id, one name                   #247,#355
the addressable set            your own TEAMLEAD may not be in it                    #426
harness config                 reserved to the operator, and broken in one place     #246
branch protection              strict-mode, required reviews — operator-only         #374
Windows / PowerShell / CRLF    the recipe cannot start a pane as shipped             #502
memory index                   the remedy and the defect are THE SAME ACTION         #217,#582
```

### And the thing no prompt encodes

> *"Much of what worked today came from six agents cross-checking each other. A fresh fleet has the
> same prompt and none of the accumulated corrections."* — DEV4, #261

⇒ **A subordinate refusal is a better detector than an orchestrator's self-review, and it is the one
we can design for.** **Every consequential correction to the orchestrator came from below or from
the operator; none came from its own re-reading** (#65). Five panes independently caught it
circulating a monitor that violated the very bound it was quoting — **each because they read the
artifact rather than the excerpt** (#287 §8).

**[PREDICATE]** When a peer quotes doctrine at you, read the artifact, not the quotation.

---

## What is NOT established about this file

- ⛔ **That any clause here changes an outcome.** *A correction filed is not a correction adopted* —
  three defects diagnosed and then repeated in one session, one **seventy minutes after publishing
  the correction** (#338). ★ The discriminator is in that issue's own data: the defect that
  **stopped** was the one where a *procedure* changed; the two that recurred were only ever
  *understood*. ⇒ **Every [GATE] here without a named running caller is currently an understanding.**
- ⛔ **That the tags are correctly assigned.** A clause tagged `[GATE]` whose caller does not run is
  mis-tagged, and the honest response is to re-tag it `UNARMED`, not to build a caller to justify
  the tag.
- **That deleting the untaggable clauses loses nothing.** Not measured. The five prompts should be
  reduced **with their owners in the room**. `prompts/MEASURED-2026-08-21.md` and #532 already name
  the specific dead letters per file and give each an owner — that is the input to the reduction,
  and it is not this file's to execute.
- ⚠ **This file was written from the issue corpus, not from operating the fleet** — and its first
  draft was written against a 382-commit-stale tree, which produced four corrections above. Four
  roles who *did* operate the fleet said their prompts were accurate and had not read them (#261).
  ⇒ **A kernel that is right and unread is the same artifact as one that is wrong.**
