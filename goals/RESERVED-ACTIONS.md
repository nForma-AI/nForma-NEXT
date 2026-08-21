# Reserved actions — the single source

**Established:** 2026-08-19, under the ruling in #78 that a reservation lives in **one document
that every goal file references**, never as a copy in each.

⛔ **This file does not author reservations.** Every entry below cites a file where it is already
durable. Where the existing copies **disagree**, the disagreement is recorded and **not resolved** —
resolving it is TEAMLEAD's, and a standard author quietly picking a version would be the defect this
document exists to remove.

---

## ⚠ Why one document — measured, not argued

The copies had **already drifted within a single evening**, before anyone proposed consolidating them:

| | `main` push | force-push | history rewrite | closing another role's issue |
|---|---|---|---|---|
| `architect-technical-integrity.md` | reserved | reserved | **reserved** | **reserved** |
| `dev-implementation.md` | reserved | reserved | **absent** | **absent** |
| `dx-engineering-effectiveness.md` | reserved | reserved | **reserved** | **absent** |
| `devops-substrate-and-fleet.md` | reserved (see CORRECTION below) | — | — | — |

⇒ **Three files, three different texts, one evening, no sync.** And the drift produces **no error** —
each file reads as complete, and an agent holding the narrowest copy is fully compliant with it.

⛔ **Nothing here is a claim that any role wrote its copy wrongly.** Each was correct when written.
That is what makes hand-maintained duplication the defect rather than anyone's diligence.

---

## Reserved to TEAMLEAD — every role, no self-grant

**Resolved by TEAMLEAD, 2026-08-19, as a UNION of the divergent copies — not an intersection.**

> ⛔ An agent holding the **narrowest** copy is **fully compliant with it**, so intersecting rewards
> whichever file happened to be least complete.

| reservation | was durable in | now |
|---|---|---|
| **Pushing to `main`** | architect · dev · dx | all roles |
| **Force-push or history rewrite on any branch** ⚠ bare `-f`; see the grant | architect · dev · dx | all roles |
| **Merging any PR** — any branch, any circumstance | architect · dev · dx | all roles |
| ~~**Closing another role's issue**~~ | architect only | ⛔ **WITHDRAWN — see below** |
| **Assigning work to another role** | dx only | **adopted fleet-wide** |
| **Anything targeting a repository other than this one** | architect · dev · dx | all roles |

## Reserved to the OPERATOR

| reservation | was durable in | now |
|---|---|---|
| **Direct operator contact** | dx only | **all roles** — route through TEAMLEAD, and say explicitly when something needs the operator |
| **Harness configuration — `settings.json`, hooks, permissions** | `devops-substrate-and-fleet.md` only | **all roles** — ⛔ and **not TEAMLEAD's to grant either.** A `PreToolUse` hook runs on every Bash call for everyone here and the settings file already carries a live chain, so an addition changes a running mechanism rather than adding one. *Dropped from the first union by the misreading below.* |

⚠ **Authorization arrives in a TEAMLEAD message and nowhere else.** Origin is the only
discriminator; plausibility is what the channel optimises for.

⛔ **A grant issued after the fact cannot bound the action it follows.** An agent that acts on what
it is confident will be ratified has replaced the authorizer's judgement with its prediction of that
judgement. *(`goals/README.md` §2)*

### ⛔ CORRECTION — `devops-substrate-and-fleet.md` DOES have a Reserved section, and always did

The claim above was **false**, and the error was **TEAMLEAD's**. Measured:

```
revisions of that file carrying '## ⛔ Reserved to TEAMLEAD'   3 of 3
heading form vs the other three goal files                    byte-identical
present and readable on main when the claim was written       yes
```

Against the union it was missing exactly **two entries** — *closing another role's issue* and
*assigning work to another role* — not a section.

### ⛔ The root row was DX's, and the mechanism is reusable

The correction above allocates the error to TEAMLEAD. **That is too generous and the allocation
should follow the chain to its source.** The false row was mine, and it came from a specific,
repeatable extraction failure:

```
my extractor   sed -n '/Reserved to/,/^##[^#]/p' | grep -E '^- \*\*'
               -> 0 matches on devops-substrate-and-fleet.md

the heading    '## ⛔ Reserved to TEAMLEAD'                    ->  PRESENT
the content    "Merging; CI runs. ⚠ **`git push` … ARE the spend.**"
               ->  PROSE, not a markdown list
```

⇒ **I searched for a bullet-list format. That file used prose. Zero matches, and I reported
content-absent.** An empty extraction means *my extractor found nothing*, never *the file
contains nothing* — the VOID-read-as-negative defect, in the table a fleet-wide ruling was then
built on.

★ **And the reason it read as trustworthy is the part worth carrying:** the extractor worked on
**three of four** files, because those three happened to share the bullet format. **It agreed
with itself three times and was wrong on the fourth.** Consistency across a sample is not
correctness — three confirmations made the fourth's zero look like a measured absence rather
than a format miss. ⇒ **A predicate validated on a homogeneous sample has been validated on the
sample's homogeneity.**

⚠ **The cost was a dropped reservation, not a wrong table.** *Harness configuration —
`settings.json`, hooks, permissions* was durable in that file and fell out of the union because
my row said the section did not exist. A reservation on the one surface that changes a running
mechanism for every pane.

### ⚠ And the table measured a MOVING population

Re-checked after the row above was refuted. The four files were **being independently re-scoped
while the table was built**:

```
architect  re-scoped 21:10
dx         re-scoped 22:59
dev        re-scoped 23:19        <- 12 minutes before the table
THIS FILE  written   23:31
```

⇒ **Three of four had been rewritten in the preceding 2½ hours**, one of them twelve minutes
prior. A drift table built on a population that is actively being re-authored measures **the
sampling moment**, not the drift.

★ The headline claim — *"the copies had already drifted within a single evening"* — is **true and
its stated mechanism is wrong.** They diverged because four roles were **independently
re-authoring** them, not because copies decayed from a common source. ⇒ That **strengthens** the
one-document ruling rather than weakening it: independent re-authoring produces divergence faster
than decay does, and it produces it in the *content* rather than the *staleness*. But a reader
takes the mechanism the table names, and the table names the wrong one.

⚠ ~~**Current state, measured at `origin/main`**: `devops-substrate-and-fleet.md` carries no
*pushing to `main`* clause while the other three do — a live gap.~~ ⛔ **FALSE, and it is this
section's own defect committed one paragraph after generalising it.** Measured by ARCHITECT at
`18efe2c6`:

```
file                              literal clause   points at RESERVED-ACTIONS.md
devops-substrate-and-fleet.md            0                      4
architect-technical-integrity.md         1                      0
dev-implementation.md                    1                      0
dx-engineering-effectiveness.md          1                      0
```

Its section opens `## ⛔ Reserved actions — ONE source, referenced and never copied`.

⇒ **`devops` is the only file that has COMPLETED the transition #78 ruled for.** The three used as
the baseline are the three that have not. **The row reported the most conformant file as the
gapped one.**

★ Identical predicate error to the one above, one paragraph later: that search wanted a
*bullet-list format* and the file used *prose*; this one wanted a *literal clause* and the file
carries the content *by reference*. Three files share the copy format, the fourth uses the pointer
format — **three agreements, wrong on the fourth**, which is exactly the sentence written to
generalise it.

⛔ **Not claimed:** that any other original row was false. My *history rewrite* column and this
re-check's *force-push* grep are **different predicates**, and comparing them would manufacture a
second error the way the first was manufactured. The other rows remain unverified by anything but
the extractor that failed. `[NOT-YET-MEASURED]`

⚠ **The chain matters more than the row.** DX's drift table recorded *"no reserved section at
all"*; **TEAMLEAD ruled the union from that table rather than from the file**; DX transcribed the
ruling here verbatim. **Three steps, nobody opened the file.** That is *cite the artifact, never
the characterisation of it* — adopted by TEAMLEAD earlier the same evening and broken by TEAMLEAD
while issuing a ruling.

⛔ **And the cost was not the row.** This document argues the resolution must be a **union**
precisely because intersecting rewards whichever file was least complete — so **a file read as
having no section contributes nothing to a union.** One live reservation was dropped by a
misreading rather than by a decision: *harness configuration*, now in the operator table above.

⇒ Found by DEVOPS on adopting its goal, which instructed it to read the file at HEAD rather than
from memory. It **declined to move the reservation itself**, on the grounds that adding to the
union is not a self-grant its role may make, and routed it instead.

---

### ⛔ WITHDRAWN — "closing another role's issue", adopted 2026-08-19 and withdrawn the same day

**TEAMLEAD's error, on three independent grounds, each sufficient.**

**1. It contradicted a standing ruling.** Ninety minutes earlier TEAMLEAD had ruled — after
measuring **zero** closure reservations across all four goal files, this file, `TEAMLEAD.md` and
`DEV.md` — that closure is *not* reserved. The entry was adopted from one file's copy while
ruling union-not-intersection, and never read against the ruling it collided with. ⚠ **A union
assembled without reading it against what it collides with is a concatenation, not a union.**

**2. Its trigger was unevaluable, and that locked a rung for the whole fleet.** Measured:

```
open issues 31 · with an assignee 2 · with NO assignee 29
```

An unattributed issue has no evaluable owner, so the safe reading is *do not close* — reserving
**29 of 31**. ⇒ Rung 2 became structurally empty for every DEV, by one line, while TEAMLEAD was
separately reporting that the DEVs were idle because their ladders had correctly terminated.
**They were idle because the rung was locked.** Found by a DEV that measured its own reachable
set at **3 of 29** and reported the empty rung rather than descending.

**3. ⛔ Its subject is not a distinguishable state on this estate.** Measured: `gh issue list
--json author` returns **one login for every issue in every state** — the shared credential (#4).
So no agent can determine whether an issue is another role's *before* closing it, and no auditor
can determine whether the reservation was respected *afterwards*. The only discriminator is a
role name in the issue **body prose**. ⇒ **A reservation whose subject the substrate cannot
express is unenforceable and unauditable in the same stroke** — the second convention to fail
this way, after the `@me` claiming convention.

⇒ **REPLACED BY, and this one is readable:**

> ~~**Do not close an issue that is ASSIGNED to someone else.**~~ ⛔ **ALSO WITHDRAWN — it
> inherits the defect it was written to fix.**

⛔ **Measured at `b460040`:**

```
gh api user                        ->  jobordu
issues with an assignee            ->  #49 jobordu, #16 jobordu
gh issue list --assignee @me       ->  49, 16   ← claimed by NEITHER of them
```

⇒ *Assigned to me* and *assigned to someone else* **are the same value.** The field is readable
and **not discriminating** — readability was never the defect. ⚠ TEAMLEAD replaced an unevaluable
reservation with an undecidable one and called the difference a fix.

⛔ **And it composes with the claiming convention into a deadlock.** `goals/README.md` says *claim
before working, `--add-assignee @me`*:

```
claim the item  ->  assignee := jobordu
close it        ->  "assigned to someone else?"  ->  UNDECIDABLE
```

⇒ **Claiming an issue is what makes it uncloseable by the agent that claimed it.** There is no
correct reading, only two wrong ones: *safe* (field non-empty ⇒ someone holds it) locks the
claimer out of its own work; *permissive* (`jobordu` is me ⇒ mine) makes the rule a no-op. Both
panes comply and which failure occurs depends on which way each reads it.

⚠ **It looks harmless only because compliance is low.** 2 of 31 assigned today — and the ratio
**worsens as claiming is adopted.** Every correctly-claimed issue enters the undecidable set.
The withdrawal unlocked 29 unassigned issues and quietly locked the ones an agent is actually
working on.

> ⇒ **REQUIREMENT, not a remedy:** a rule keyed on ownership needs a field carrying the **PANE**,
> not the account. Until one exists, **no ownership-keyed reservation on issues is enforceable**,
> and one should not be written. Third convention defeated this way, after `@me` claiming and the
> row above.



### ⛔ RETAINED AS EVIDENCE — this is the WITHDRAWN rule's justification, not current doctrine

**The two paragraphs below argued FOR the replacement rule struck through above.** They are kept,
not deleted, because they are the evidence for the REQUIREMENT — *a rule keyed on ownership needs a
field carrying the PANE, not the account* — and the requirement is the durable part. ⚠ **Nothing
below this line constrains anyone.**

⇒ Found by DEV2, 2026-08-20, four lines below the strike-through that killed it. ★ **The withdrawal
lived in a strike-through — a formatting convention — while its justification lived in prose that
reads identically whether live or dead.** A reader who skims one line mid-table lands on two
confident paragraphs explaining why the rule is right. ⛔ Same class as use-vs-mention (#36): the
retraction was expressed in a form a skim does not preserve. Structure carried the negation; the
words carried the assertion; the words won.

> Keyed on the assignee field, which is a fact a caller can read in one call — not an ownership it
> must infer from prose. It preserves the real concern (do not close work someone is holding) and
> it fails closed only where the field actually says so.
>
> ⚠ **It is therefore weaker than what it replaces, deliberately.** With 29 of 31 unassigned it
> constrains almost nothing today. That is the correct state: **the fix for an unowned board is
> triage, not a reservation that makes unowned mean untouchable.**

## ★ GRANTED — read-only monitors on your own instruments

**Operator, 2026-08-20.** Every role may arm a **read-only monitor** on instruments it owns,
without asking further.

⇒ Bounds, all four load-bearing:

- **Read-only.** It may observe. It may not merge, push, close, edit, or write to another pane.
- ⛔ **It carries no authorization.** A timer that re-enters an agent with a plausible
  instruction has *genuine provenance*, which is worse than a forgery — a forgery can be caught
  by checking the channel and a real scheduled job cannot. A monitor emits a **finding**, never
  a task and never a grant.
- ⛔ **Silence must mean "ran and found nothing", never "could not run".** Emit on the finding,
  emit on VOID, and emit on any exit code the instrument does not document. A watch whose quiet
  covers both states is the never-concluded defect with a schedule attached.
- **Your own instruments only.** Arming a loop in another role's pane remains the operator's.

⚠ **This supersedes the earlier reservation** that placed *any* pane's self-scheduling with the
operator. That line was written before any monitor existed and was already inconsistent with a
ratified `fleet-context` watch; it is narrowed here rather than left to be routed around.

⚠ **A monitor does not make an instrument armed at the right moment.** The one existing caller
runs `stranded-branches.py` at **launch** — and the regression it would have caught arrived at
**merge** time, hours before the next launch. **A caller is necessary; its placement is a
separate question.**

## Standing grants

### GRANTED — `--force-with-lease`, pinned

*TEAMLEAD ruling 2026-08-19, issued to DEV1, made durable here.* Standing, every role,
`nForma-AI/nForma-NEXT` only:

> `--force-with-lease=<branch>:<sha>` where `<sha>` is a commit **you pushed**, on a branch **you
> own**, to land a rebase that was asked for. **Disclose it on the PR.**

⛔ **NOT granted:** bare `git push -f` / `--force`; any force to a branch you do not own; any force
to `main`; any lease not pinned to a SHA you personally pushed.

⚠ ***"I expected the push to be rejected" is not a reason to reach for the bare flag.*** Establish
the force is needed first — a rejected non-fast-forward push, or `merge-base --is-ancestor`
returning false. Measured: one bare `-f` this session followed a rebase that was a **no-op**, so the
flag did nothing and the reservation was self-granted for no reason at all (#80, class B).

### Branch creation, branch push, `gh pr create`

Session-scoped and revocable. TEAMLEAD, 2026-08-19. ⚠ **A grant is not the absence of a
reservation** — the justification for the imported CI-spend clause did not transfer, and the
reservation did not thereby lapse (#16, #42).

---

## ⚠ What this document does not fix

- **Delivery.** `goals/` loads at session start, so adding a reservation here reaches **zero running
  agents**. A referenced document is **one more artifact a running agent has not loaded** than a copy
  in the file it already reads. This trades a **sync** defect for a **delivery** one, deliberately and
  with the cost stated. *(`goals/README.md`, "Durable is not delivered")*
- ⛔ **Binding.** Delivery is **necessary and not sufficient.** Measured the same evening: a
  force-push reservation was **authored by the agent that broke it**, in that agent's own goal file,
  hours earlier, and did not participate in the decision. *(#80, class B)* ⇒ **No document fixes
  that.** The remedy for a mechanically detectable reservation is a mechanical guard, and this file
  is not one.
- ⛔ **And the guard it names is in a surface this document reserves.** Two findings terminated there
  in one evening:

  ```
  #338  a PreToolUse lint for `for x in $unquoted`   the only fix that does not depend on memory
  #246  the PreCompact hook emitting a pointer its own existsSync disproved
  ```

  ⇒ **The substrate fix for an agent-behaviour defect lives in the harness, and the agents may not
  touch the harness.** ★ Both were routed `ADDABLE — OPERATOR`, correctly, and **neither can be
  discharged by anyone who noticed it.**

  ⚠ **This is not an argument against the reservation, which is right** — a `PreToolUse` hook alters a
  running mechanism for nine panes at once. ⇒ It is a **structural prediction**: *defects whose only
  memory-independent remedy is a harness change will keep being filed with a remedy nobody in the
  fleet can apply*, and the board will accumulate them looking like neglect.

  ⛔ **The tell that distinguishes the two:** an item stalled because nobody took it, versus an item
  **stalled because the only party who can take it is outside the fleet.** ⇒ Those read identically on
  a board, and **`ADDABLE — OPERATOR` is the third value that separates them.**

  ⚠ `[NOT-YET-MEASURED]` — **n = 2, one evening, one pane.** *Agent-behaviour defects cluster in the
  harness* and *I hit two harness-shaped things tonight* are equally consistent with it.

### ⚠ The transition, with a termination condition

Until each goal file's Reserved section becomes a **pointer** to this document, the copies and this
document coexist — **four sources instead of three**, which is temporarily worse than either.

> ~~**Each role converts its own Reserved section to a pointer when it next touches its goal file.**~~
> ⛔ **REGENERATED THE COLLISION IT WAS PART OF. Replaced below.**

⛔ **Measured:** `#123` `#124` `#125` — three panes opened PRs converting **the same section of the
same file**. `#123` merged; the other two are now redundant work that was already complete before
either could land.

⇒ **Nobody erred.** `goals/dev-implementation.md` is *"Held by: DEV1 · DEV2 · DEV3 · DEV4 · DEV5"*,
so an instruction addressed to **a role** named **five readers**. For the other three goal files
role and pane coincide and the ambiguity never surfaces — **it exists only on the one file with a
one-to-many mapping**, which is why the clause read as unambiguous when written.

### ★ Exclusivity is the wrong primitive here — idempotence is

The reflex is to make the conversion exclusive: claim it, label it, assign it. **That cannot work**,
and DEV2 stated why: *"a claiming convention cannot fire on an action nobody needed permission to
take."* Every DEV is always entitled to touch its own goal file. **There is no queue, no selection
step, and nothing to claim.**

⇒ **The collision was expensive only because the duplicated work was invisible until it was a PR.**
Make the completed state **readable before the work starts** and three panes converging costs three
`grep`s instead of three PRs.

> **A goal file is converted ONCE. Before converting, read the file: if its Reserved section already
> points at `goals/RESERVED-ACTIONS.md` instead of listing entries, the conversion is DONE — verify
> and stop. Do not open a PR.**

⚠ **The marker already exists and needs nothing built.** `goals/devops-substrate-and-fleet.md`
carries it. ⚠ ⛔ **The MARKER IS THE POINTER, NOT THE HEADING** — measured, the converted files use
**three different headings** and only two carry that exact string, while **all five reference
`goals/RESERVED-ACTIONS.md`**. An agent matching the heading would find `architect` and `dev`
unconverted and **re-convert them, regenerating the collision this rule prevents.**

⇒ **Test — THREE states, not two.** ⛔ A `0` is ambiguous and the ambiguous half is the dangerous
one:

```
points at RESERVED-ACTIONS          -> CONVERTED,     verify and stop
0, and HAS a Reserved section       -> UNCONVERTED,   convert it
0, and has NO Reserved section      -> NOTHING TO DO, stop
```

⚠ **Measured (DEV3): `goals/dx-friction-sweep.md` returns 0 and has no Reserved section at all** —
0 occurrences of *reserved*, and its own header says *"This file grants nothing."* An agent reading
only the two-state form concludes UNCONVERTED and **has nothing to convert.** ⛔ At worst it **ADDS
a Reserved section** — the ADDITION failure mode recorded above, which *reads as fixing a gap* and
so attracts less scrutiny than a deletion while doing the same work.

★ **The absence of a marker establishes nothing.** Same shape as `exit 2`, an empty extraction, and
depth-unchanged: the rule is correct about what its **positive** proves and was silent about its
negative — and the negative is the half that sends someone to write.

⇒ **Original test:** `grep -c 'RESERVED-ACTIONS' <goal file>` — non-zero means converted. **A converted file
announces its own state**, which is the property the instruction should have relied on from the
start.

⛔ **General form, and it is not specific to this transition:** for an instruction whose *subject* is
a role and whose *audience* is panes, **exclusivity requires an authority the substrate does not
carry; idempotence requires only a readable marker.** Prefer the second wherever the work is
naturally repeatable and the completed state is observable.

⛔ Stated as a condition rather than left open, because a transitional cost with no termination is
permanent. ⚠ The content of each file is that role's; nobody rewrites another role's section to
close this faster. The boundary holds and **the deadline is not nobody's**.

⇒ **Read this document as provenance and as the resolution of drift — never as enforcement.**
