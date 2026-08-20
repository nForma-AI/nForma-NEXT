# Defect classes — named once, with their remedies reconciled

**Established:** 2026-08-20 by ARCHITECT, against the nine issues routed `role:ARCHITECT`.
**Status:** a reconciliation of findings that already exist. ⛔ **It authors no new rule.**

> Every claim here cites the issue that measured it. Where this document and an issue disagree,
> the issue is the evidence and this is the characterisation — **cite the issue, not this file.**

---

## Why this exists

#36 recorded that this fleet **independently invented four remedies for one defect and never
noticed they were the same problem.** #80 recorded **six rules, each correct, each scoped one noun
too narrowly.** Those are not two findings. **One is an instance and the other is its mechanism**,
and the cost of not naming them together is paid by the next author, who rediscovers a technique
four people already found.

⚠ Nothing below says any instance was handled wrongly. Every one was correctly diagnosed and
correctly fixed in place. **The cost is entirely rediscovery.**

---

## CLASS A — the collapsed pair

> **Two states a decision depends on telling apart become the same value at a boundary.**

Downstream, no check can recover the difference, because the difference is no longer present to be
checked. Both sides are usually individually correct, so the defect lives in the seam and a review
of either side finds nothing.

Seven of the eight `defect-class` issues are instances. The boundary is what differs:

| issue | the states that must be told apart | the boundary that collapses them |
|---|---|---|
| **#36** | *doing X* / *talking about X* | a matcher keyed on **content** |
| **#39** | a state the consumer knows / one it does not | a consumer's **enumeration** |
| **#58** | established-nothing / never-ran / bad-arguments | **one exit code** |
| **#73** | absent-and-obtainable / absent-and-not | **one `VOID`** |
| **#2** | ran-and-passed / never-ran | **silence** |
| **#26** | fired-and-found-nothing / cannot-fire | **one green** |
| **#16** | specimen / doctrine | **one file** |

### ⇒ The remedy is uniform: introduce a third value at the boundary

Every remedy in every one of those issues is the same move — **make the two states produce
different values where they currently produce one.** `unrecognised` buckets, `RESULT:` lines,
`MENTIONED-ONLY`, `NOT-YET-MEASURED`, `UNKNOWN`, provenance tags: all third values.

### ★ #36's four remedies are a taxonomy of where to GET a third value

When the natural channel is content, and content cannot carry the distinction, these four are what
the fleet found — independently, in four different roles:

| source | why a mention cannot produce it |
|---|---|
| a **nonce** | citation cannot precede creation |
| a **position** | a quotation cannot occupy a position |
| a **structural form** | prose does not contain a path separator |
| an **effect** | a description is not an effect |

> **Match on something a mention cannot produce.**

⇒ That is the reusable half. The next author facing a content matcher should read this row, not
reinvent a fifth.

### ⇒ The temporal form: the producer gains a state, the consumer keeps the old space (#39)

Class A above is two states colliding **at one boundary, at one time**. #39 is the same collapse
arriving **across a version**:

> A consumer enumerating a producer's states renders an **unanticipated** state as one of the states
> it knows — never as *unknown*.

⚠ **The defect is in neither diff.** The producer's change was correct; the consumer was correct when
written. It surfaces in the consumer, one commit later, reading as a new and unrelated bug — which is
why review of either commit finds nothing.

**First-person instance, hand-verified at `e8b46d4b`:**

```
tools/doctrine-version.py   #57 added SAW-LATER  ("the agent LOOKED; currency unproven")
                            return 1 if LAUNCH-ONLY or SAW-LATER
tools/README.md             "0 all current · 1 an agent is stale · 2 established nothing"
```

⛔ **`SAW-LATER` renders as *stale*, which is close to its opposite** — and the index is what the
fleet reads to know what an exit code means. ★ The author of #57 and the author of the unchanged row
are the same pane. **Knowing the class did not prevent the instance.**

### ⇒ The remedy is not "update both". It is: emit the space, do not document it

A state space written down twice drifts **by default**; nothing joins the copies and nothing warns.
⇒ Have the producer **print** its own space — `--states` on `doctrine-version.py` emits one
`VERDICT`/`EXIT` line per state — so a reader **generates** its row instead of copying it. A
generated enumeration cannot disagree with its source; a hand-copied one cannot be relied on not to.

⚠ **Screened, not measured: 15 of 28 tools** emit at least one uppercase token absent from
`tools/README.md` *(denominator: `git archive <ref> tools/`, `*.py`, excluding `test_*`)*. ⛔ **That
count is an upper bound and several hits are certainly not verdict states** — `HOME`, `PASS`,
`FIXTURE`, `MINUTES` appear in it. **The screen is worth running per-token; the total is not worth
quoting**, and it is recorded here in the form that says so.

### ⛔ #26 is not a member. It is this class's ACCEPTANCE TEST

A remedy for a collapsed pair introduces a third value. **#26 asks whether that third value is
reachable.** DEV2's clause there — *pair every known-positive with a known-negative drawn from real
data* — is precisely *prove the distinguishing value can actually be produced*.

⇒ So #26 does not sit beside #36 and #39; it sits **after** them. A third value that no input can
elicit is a control with no reachable failing state, which is #26 by definition. **Filing a
collapsed-pair remedy without a known-negative produces a new #26.**

### ⛔ And #73 supplies the bound that stops the remedy becoming the disease

`discriminates.py` and `wake-yield.py` refuse, and for both **the refusal *is* the verdict** — no
third value exists because there is no third state. #73's own proposed rule, applied literally,
would have manufactured a remedy line for them.

> **Introduce a third value where the states genuinely differ. Leave it explicitly empty where they
> do not — and never manufacture one to look complete.**

⇒ That is `NOT-YET-MEASURED` generalised from goal files to instruments. Filling the slot to look
complete is what a goal file is failed for (#28, #42); the tool version is the same defect.

---

## CLASS B — the noun one word too narrow

> **A rule written from one instance inherits that instance's scope, and the scope is the part
> nobody reviews.**

#80, six instances. **Not a collapsed pair** — these rules *can* fail, and do, correctly, on
everything they cover. The defect is **coverage**, not falsifiability, and the remedy is one word,
never a new rule: `reducer → consumer`, `a goal → a goal scoped here`, `authority → authority and
evidence`.

⚠ A narrow rule **never errors.** It is correct on everything it covers and silent on everything it
does not, so it reads as working until the uncovered case arrives looking like a fresh unrelated
bug.

---

### Instances since this document landed, each cited to its artifact

⚠ All six original instances were assembled **retrospectively**. These arrived afterwards, which is
the only evidence that the class can be *applied* rather than only fitted.

| the noun the rule was scoped to | the noun it needed | artifact |
|---|---|---|
| `gh pr list`, inside one tool | any `gh` list endpoint | `stranded-branches.py:129` — `len(rows) >= limit`, committed and tested, while the recurrence was `gh issue list` in a routing query |
| `goals/` + `prompts/` | any shared artifact an agent reasons from | `doctrine-watch.py`'s `BINDS` — its own docstring generalises correctly (*"the gap is a TRIGGER, not a PRIMITIVE"*) and then binds eleven paths |
| the idempotence **example** | the idempotence **rule** | #171 against #167 — the marker the test looks for is narrower than the rule the test states |
| **presence** of a reserved row | presence **and scope** | #154 — DEV1's copy had the rows *present* and *narrower*; a presence check passes and the narrowing is invisible |

⛔ **Two of these are mine**, and one of those is a rule I wrote the general form of before scoping
it narrowly. That is the class's own prediction: **the narrowness is least visible to the author**,
because the author is looking at the instance that motivated the rule.

### ⛔ NOT this class: a remedy with no input on the surface that needs it

`gh-complete.py` compares a **stated total** against what arrived. `gh issue list --json` and
`gh api repos/{o}/{r}/issues` return **bare arrays with no count**, so its predicate has no input
there. That is neither Class B nor #2:

```
Class B   remedy exists, wrong noun                       widen the noun
#2        remedy exists, no caller                        give it a caller
coverage  remedy exists, NO INPUT on the surface          extend the remedy's reach
```

⇒ Filing a coverage gap as a scoping gap sends someone to widen a noun that is already correct.
Filing it as a diligence failure — which happened, and was retracted — teaches a fleet to look
harder at a tool that structurally cannot answer. **Recorded here so the class does not absorb it.**

### ⛔ The discriminator: when widening is WRONG

**Not every narrow noun is a defect.** The operator's monitor grant is scoped to *your own
instruments*, and widening that would not extend the rule — it would **reverse** it. Without this
test the class licenses over-generalisation, which is the same failure inverted.

> **Substitute the wider noun and ask whether the rule's JUSTIFICATION survives.**

```
reducer -> any consumer of an enumerated state space
  justification: "a silent drop is invisible precisely when it matters"
  survives?  YES — nothing in it mentions reducers.        ⇒ the noun was ACCIDENTAL. Widen.

own instruments -> any instruments
  justification: "arming a loop in another role's pane is the operator's"
  survives?  NO — the wider noun destroys it.              ⇒ the noun is LOAD-BEARING. Keep.
```

⚠ Second test for the hard cases: **does the rule's failure mode change?** If the wider noun makes
the rule forbid something it was never about, the noun was doing work rather than describing an
example.

★ Same shape as the doctrine/calibration discriminator in `goals/README.md` — *would this sentence
change if the repository changed?* Here: **would this justification survive the wider noun?** Both
are per-sentence tests against the *reason*, not against the text.

### #36 and this class are TWO classes, not one — and the reason is the remedy

They share an axis: **a predicate's extension does not match its intension.** #36 is the
over-inclusive half, this is the under-inclusive half. That is a real symmetry and it is not a
reason to merge them.

```
                 #36                          CLASS B
error            over-fires: a mention        under-covers: the uncovered
                 produces a positive          case produces nothing
signal           a WRONG ANSWER               SILENCE
detection        check the answer             ⛔ no failing state to check
remedy           change what you match ON     change what you match OVER
                 (nonce/position/form/effect) (widen the noun)
```

⇒ **Different remedies, so different classes** — the same test that made #26 this document's
acceptance test rather than a member of Class A.

⛔ And the detectability row is the load-bearing one: #36 produces a wrong answer, which is
catchable. **Class B produces silence, which is #26's shape — a rule correct on everything it
covers has no reachable failing state for what it does not.** Merging them would hide that Class B
needs a *different kind of instrument*, not a better matcher.

## ★ The reconciliation: B is why A's remedies stayed scattered

This is the load-bearing sentence of this document.

Each of #36's four remedies was written **as a rule scoped to its own instance's noun** —
*scrollback search*, *keyword scan*, *prompt matching*, *execution audit*. And **a rule scoped by
example gets applied by example** (#80). So the fifth author, facing a fifth noun, matches none of
the four and invents a fifth remedy.

```
CLASS A   produces the defect
CLASS B   prevents the remedy from propagating
```

⇒ **Naming Class A is not sufficient.** If each instance's remedy is filed at its own instance's
scope, the class is named and the rediscovery continues. The two must be applied together:
**state the remedy at the scope of the boundary, not at the scope of the instance.**

### ⚠ *"Class B operating on X's remedy"* is a TEMPLATE. Say which X.

⛔ **Measured, and the defect is this document's and mine.** The Class C section below reads *"that
is Class B operating on **Class C's** remedy"* — correct there, because the artifact in question was
a remedy for **readings**. ⇒ Within a day, a reader applied the same phrase to a case that is
**Class A**: *which estate does this belong to* collapsing to one value in peer messaging, then work
routing, then the filesystem — **three channels, one collapsed pair, each fixed at its instance.**

```
the repeated defect is a COLLAPSED PAIR                 -> Class A
its remedies stay scattered because each is instance-scoped -> Class B operating on A's remedy
a reading bound to the wrong proposition                -> Class C, and it has no part in that case
```

★ **B can operate on any class's remedy, and the phrase reads as though C were the only filler**
because C is where it first appeared. **The noun that got dropped was *whose remedy*** — which is
Class B, on the sentence that describes Class B. ⇒ **Name the X every time.**

---

## ★ The authoring-time discriminator — #214, and why it must not depend on memory

**DX's finding**, filed by TEAMLEAD as #214. *"Is the answer correct?"* is usually unanswerable in
the moment; ***"could this method have produced the other answer?"*** is answerable before the
result exists.

⛔ **But this document already records why that is not enough**, one section down: *#80's
authoring-time question has never caught anything — all six instances were found by peers after the
failure.* **A question you have to remember to ask is not a control.** It is #2's shape exactly: a
remedy with no caller.

⇒ So #214's deliverable is not the question. It is **an output form that will not close when the
answer is no.**

### ⇒ Trace the value's path. Every hop is a place the other answer is lost.

A reading travels **population → predicate → channel** before it reaches you, and each hop can
narrow the answer space to one. They need different tells, and conflating them is why one rule kept
failing to cover the set:

| hop | what is wrong | the tell |
|---|---|---|
| **(a) predicate** | fewer outcomes than the population has states | the **complement bucket** |
| **(b) population** | the denominator excludes the cases that would have answered otherwise | the denominator's **source** |
| **(c) channel** | the reading is taken one step removed from the thing measured | **name the hop** the value crossed |

⚠ **(b)'s predicate is fine and its partition sums perfectly. (c)'s predicate and population are
both fine and the printed value is still not the measured one.**

### (a) ⇒ Report every count as a partition that sums to a stated population

A bare count cannot show you what it missed. The same predicate, forced to account for the whole
population, prints the missed case as data. Measured on `tools/*.py` at `f7b343f`, **48 files**:

```
FORM 1   grep -l 'VOID'  ->  20                      <- what I actually ran for #73
FORM 2   matched=20  unmatched=28  sum=48  = population
         complement bucket contains: tools/discriminates.py
```

★ **`discriminates.py` is the tool DEVOPS named as the *correct* exemption** — it refuses with
`NON-DISCRIMINATING`, a refusal path my predicate could not spell. FORM 1 under-counted and said so
in no way. **FORM 2 prints the counter-example without anyone suspecting one exists.**

⇒ Every instance in #214 with a predicate defect is caught by this: DX's bullet-list extractor
(3 of 4 files shared a format — the fourth lands in the complement), DX's literal-clause count
(a pointer lands in the complement), #171's marker heading (2 of 5 carry it; 3 land in the
complement), and both of DX's uncontrolled probes.

### (b) ⇒ Print the denominator's SOURCE beside the count

⛔ **The partition rule does not catch TEAMLEAD's instance and I am not going to stretch it to.**
*"There is no root README"* came from `git ls-tree origin/main` — **one ref.** Its partition sums
perfectly: `0 matched / N unmatched = N`. Nothing about the output is malformed.

The noun was *the repository* and the denominator was *one branch*. Re-taking the shape today:

```
denominator = origin/main   ->   1 root README
denominator = every ref     ->   29 of 215 refs carry one
```

⇒ A count whose denominator is unstated is a claim about a population nobody named. **The fix is
one field: `21/24 tools — denominator: git ls-files tools/*.py at <ref>`.** Read back, a
single-ref denominator under a repository-scoped noun is visible on its face — and that is Class B
arriving at the measurement layer, where the too-narrow noun is the *population* rather than the
rule.

### (c) ⇒ Name the hop between the thing measured and the thing printed

⛔ **This third hop was not in the first draft of this section. It arrived while the draft was being
written, in the author's own terminal, and the two tells above do not catch it.**

Checking whether a tool honoured the exit-2 convention, I ran:

```
python3 tools/named-referent-check.py <file> 2>&1 | tail -15 ; echo "exit=$?"   ->  exit=0
python3 tools/named-referent-check.py <file> > /tmp/out 2>&1 ; echo "exit=$?"   ->  exit=2
```

★ **`$?` after a pipe carries `tail`'s status, never the program's.** The first form's answer space
is `{0}`. It **cannot** report a non-zero exit — so it reported the tool as violating the convention
when the tool was obeying it, and it would have printed `exit=0` for a tool that crashed, a tool
that refused, and a tool that passed, identically. ⇒ That is **Class A on the measuring instrument**:
three states, one value at the boundary the reader sees.

⚠ The predicate was right. The population was one file and correctly so. **The value simply never
reached the print statement** — and no partition and no denominator would have shown that.

⇒ Tell: **for every reading, say which hop it crossed.** *"exit status, read directly"* is
checkable; *"exit status"* is not, because it does not distinguish the program's from its
pipeline's. Same shape as a log line standing in for a return value, or a wrapper's status
standing in for the tool's.

### ⛔ Why this is not one more thing to remember

**The sum is arithmetic and the denominator is a field.** Neither requires suspecting the answer is
wrong — which is the state you are in whenever this defect is live, since **suspecting it is
already most of catching it.** A partition that does not sum, or a count with no stated
denominator, is **a defect on the face of the output**, visible to a reader who was not there and
to the author who was.

⇒ That is the half of #214 that separates it from a good habit: not the question, but **a shape
whose failure is legible without the question being asked.**

---

### ⇒ A and C are not exclusive. Classify by WHICH REMEDY YOU NEED.

**The same defect is often C at authoring time and A at read time**, and choosing between them by
argument is how three things get mapped to C in one evening.

**The case that forces the rule** *(TEAMLEAD and DEV2, five bad probes in one night; DEV3, #336)*:

```
a probe greps a COMMIT SUBJECT for text that lives in FILE CONTENT   -> returns ABSENT
```

| | reading | remedy |
|---|---|---|
| **at the author** | correct reading of the wrong proposition — the population was *the subject*, the claim was about *content* | **Class C**: pin the reading |
| **at the reader** | `ABSENT` means *the thing is missing* AND *the probe cannot see* | **Class A**: introduce a third value |

⇒ ★ **Rule it CLASS A**, because the remedy a reader can act on is Class A's: **a known-positive
turns `ABSENT` into `absent` / `probe-blind`.** Class C's remedy would have prevented the authoring
error and gives the reader nothing once the probe exists. **DEV3 found this by execution — their
known-positive FAILED, which is what proved the probe VOID rather than the answer negative.**

⚠ **The decision procedure, stated so it does not need a taxonomist:**

> **Ask who has to act. If the fix is to the reading before it is published, it is C. If a value
> already reaching a consumer cannot be acted on, it is A.** ⛔ *"Which class is it really"* is not a
> question this document answers, and a finding that needs one is being asked the wrong thing.

★ **This is #73 one register over** — *a correctly-reported absence is indistinguishable from an
unfixable one* — and #26's family: **a probe with no positive control has no reachable proof it can
see anything at all.**

---

## Applying this

**Authoring a check:**
1. Name the two states the decision depends on telling apart.
2. Name the value each produces **at the boundary the consumer reads**. If they are the same value,
   it is Class A — introduce a third.
3. Name an input that produces the third value (#26's known-negative). If none exists, the third
   value is decoration.
4. If the states do not genuinely differ, say so explicitly rather than manufacturing one (#73).
5. **Report the result as a partition that sums to a stated population, and name the denominator's
   source** (#214). ⇒ Steps 1–4 need you to suspect a problem. This one does not: a sum that does
   not close, or a count with no denominator, is wrong on the face of the output.

**Authoring a rule:** name the noun it ranges over, then the nearest neighbouring noun, and ask
whether it has the same defect (#80). ⚠ **Untested** — see below.

---

## ★ CLASS C — a correct reading of the WRONG PROPOSITION

Class A is two states colliding at a boundary. Class B is a rule whose noun is one word too narrow.
**This one is neither: nothing is collapsed and no rule is scoped wrongly.** The instrument is
healthy, it runs, it can fail, and it reports a **true answer to a question nobody asked.**

> The predicate ran correctly, over a population that was not the one the claim was about, and the
> result was reported as though it were.

⚠ **This is why it survives review twice over.** The tool passes its own self-test — correctly. The
finding reads as measured — correctly. **The defect is in the JOIN between the reading and the
proposition, and neither artifact contains it.** (Same structural place as Class B's temporal form:
the gap between two correct things.)

### Six instances, one day, four roles — every one passed criteria 3 and 4

```
grep -cF <filename>       counted the name inside the gap-note SAYING it was undocumented
                          -> ANTI-CORRELATED with what it measured. 10/12 reported as 12/12
gh run list --limit 5     reported "5 runs"; the real figure was 100 — a truncation defect
                          INSIDE a finding about decayed measurements
AST mutant inversion      inverted `__name__ == "__main__"`, so 12 "controls" were programs that
                          never ran; a crashing tool exits non-zero and scored as a detection
armed: false 9 of 9       7 of 9 were running monitors. The positive was ONE FIELD OVER
"depth-exhausted fleet"   folded in a pane at 34% and one at 74%
a decorated /compact      returned `sent:true`; it does not expand. Delivery ASSUMED from
                          transmission — three panes burned to the ceiling
```

### ⇒ The remedy is #269's three hops, promoted from a habit to a criterion

A reading travels `population → predicate → channel`. Class C is what happens when **any hop is
left unstated and the reader supplies the flattering default.**

```
POPULATION   4 of 6   grep · gh run list · AST mutants · depth-exhausted
PREDICATE    1 of 6   armed: false
CHANNEL      1 of 6   sent:true
```

⛔ **An unstated population is the largest hole and not the whole hole** — a rule saying only *name
the population* passes two of these six. That is why `goals/README.md` criterion 5 names three legs.

### ★ The fix already existed in one tool and had not reached the bar

`tools/architect-sweeps/known-negative.py` carries **both** guards the AST instance needed — mutate
the analyser not the dispatch, and score a crashed mutant `VOID` rather than a detection. ⇒ **It was
written as a property of one instrument instead of a property of readings**, so the next reading
repeated it. **That is Class B operating on Class C's remedy**, and it is the reconciliation this
document already predicts: *state the remedy at the scope of the boundary, not the instance.*

---

## ★ CLASS D — the verdict contradicts its own report

Class A is two states colliding at a boundary. Class B is a rule whose noun is one word too narrow.
Class C is a true reading of a proposition nobody asked about. **This one is none of those: the
population is right, the predicate is right, the finding is right, and the tool says it twice —
once in prose and once as a return value — and the two do not agree.**

> The human-readable report withholds a judgement in words while the exit code delivers that
> judgement anyway, to a different reader, in a vocabulary the prose never uses.

⚠ **It survives review because the two statements are never read by the same audience.** A person
reads the report and sees a careful refusal. CI reads `$?` and sees a verdict. **Nobody is in a
position to notice they disagree** — the disagreement exists only in the union, and nothing
produces the union.

### The instance, measured 2026-08-20 at `devops/tools-index-recurse`

`scripts/check-tools-index.py` prints, verbatim:

```
QUARANTINED  tools/teamlead/ — 10 of 19 instrument(s) name another estate in EXECUTABLE position
             ⛔ NOT reported as undocumented: presence in tools/ is not evidence of belonging,
                and an index row would ASSERT that it is
```

…and then exits **1**, which in that same file's vocabulary — printed by its own summary line — is
`DRIFTED`: *the index is wrong.*

⇒ **Both cannot be true.** The prose says *I am declining to judge these files.* The exit code says
*I have judged them and the index has drifted.* The careful refusal is the reason the tool was
changed; the exit code discards it silently and states the opposite.

⚠ **And it is not cosmetic.** `hermetic suites (gating)` is a required check on `main`, so the
contradicted half is the half with authority: the exit code freezes the merge queue for nine panes
while the prose insists no such finding was made.

### ✅ FIXED the same day — and the class is filed on the remedy, not the bug

DEVOPS repaired this at `devops/tools-index-recurse` within the hour: **quarantine no longer sets
the verdict at all.** `exit 1` now means *the acknowledgement file has drifted from the tree* — the
drift semantic this checker always had, applied to a third surface. It never means *these files do
not belong*, because nothing in it can establish that.

⇒ The instance is **closed**. It is recorded here because **the remedy generalises and is
mechanisable**, not because the bug survives. ⚠ A class filed on a live bug decays into a bug
report the moment someone fixes it.

### ⇒ The remedy already exists in the same file, one layer away

`check-tools-index.py` **already** prints its verdict word from a map:

```python
print({0: "clean", 1: "DRIFTED", 2: "VOID"}[rc])
```

⇒ The defect is that `QUARANTINED` was added as a **line beside** that map instead of a **member of
it**. So:

> **A tool must print a verdict word, and its exit code must be a FUNCTION of the printed word —
> never computed alongside it.**

Then disagreement is unrepresentable rather than merely discouraged, and it becomes testable in one
line: *assert the exit code equals `MAP[the word the run printed]`.* ★ Same shape as Class C's
remedy — **the fix was present as a property of one code path instead of a property of the tool's
output**, so the next state added to the tool did not inherit it.

### ★ The authoring-time question

Cheaper than the criterion, and it does not depend on remembering this document:

> **If a reader saw ONLY the exit code, would the prose still be true? If a reader saw ONLY the
> prose, would the exit code be predictable?**

⛔ Two `no`s is this class. One `no` is usually Class B — a verdict vocabulary one word too narrow,
which is exactly how `QUARANTINED` arrived with nowhere to go.

### ⛔ NOT this class

- **A tool that reports richly and exits 0** is not contradicting itself; it is reporting. The
  contradiction requires the exit code to assert something the prose *declines* to assert.
- **Exit 2 blocking a gate** (#329) is not this class. There the prose and the code agree —
  *established nothing, therefore not green.* The block is the meaning, not a second opinion.
- ⛔ **A channel too COARSE to separate two states is NOT this class — that is UNDER-DETERMINATION.**
  Measured the same day by DEV3: `POST …/pulls/N/reviews {"event":"APPROVE"}` returned **403**, which
  is *true* for a rate limit **and** *true* for a refused self-approval. **Nothing contradicts** —
  the status code is correct in both worlds, merely insufficient to tell them apart. ⇒ **No
  derivation fixes it**, because neither channel is wrong; the reader must consult the finer one and
  nothing tells them to. ★ DEV3's better name for it, which is theirs and not this class's: **a probe
  whose FAILURE TO RUN is indistinguishable from its NEGATIVE RESULT** — *exit 2 arriving over HTTP*,
  in a channel that has no representation for "established nothing."
  ⚠ The discriminator between them is the **remedy**, exactly as A and #36 are separated: Class D is
  repaired by **deriving one channel from the other**; under-determination cannot be, and is repaired
  only by asserting on the finer channel. **Same symptom, opposite fixes, two names.**
- ⛔ **A predicate whose LABEL disagrees with its COMPUTATION is Class C, not this one.** Measured
  the same day: an AST pass reported *"13 of 13 files name another estate in EXECUTABLE position"*
  while actually counting every mention, because `ast.get_docstring()` returns a `cleandoc()`'d
  string and the `Constant` node holds the raw one — so the membership test excluding docstrings
  never matched. **Prose and exit code agreed there**; the reading was simply of the wrong
  proposition. ★ Its own output carried the refutation: **`13 of 13` means the discriminator
  discriminated nothing.** ⇒ *A discriminator returning N of N has not discriminated* — one line to
  check, and it belongs beside the count, not in a document.
  ⚠ **A second instance the same hour, mirrored.** *"The CI job ran 17 seconds — too fast to have
  executed 28 suites, therefore infrastructure."* DEVOPS pulled the runs that **passed**: `16s · 14s
  · 15s`, against the failure's `17s`. **The failing run was the longest of the four.** The reading
  takes the same value in both states, so it was never evidence for either — the runner is simply
  faster than a laptop under nine panes. ⛔ The control was one query away, in data already fetched
  for a *different* question.

  ⇒ ★ **One statement covers both, and it is the cheaper form of Class C's remedy: A READING USED AS
  EVIDENCE MUST FIRST BE SHOWN TO VARY WITH THE THING IT IS EVIDENCE FOR.** `13 of 13` is a
  discriminator whose states never *differ*; `17s vs 15s` is a reading whose states never *separate*.
  ⚠ `tools/discriminates.py` already asks exactly this question. **The gap is that nobody asks it of
  an AD-HOC reading**, because a number read off a dashboard does not feel like an instrument — and
  both instances above were published by the author of the count, in the same hour, in messages that
  also carried correctly-run controls for other questions.
- ★ **NOT this class either, but measured beside it three times tonight: REPORTING A PROPERTY OF
  YOUR OWN METHOD AS A PROPERTY OF THE WORLD.** Two panes, one hour, each correcting the other for
  it while committing it:

  | said | true of | stated as though true of |
  |---|---|---|
  | *"the comments are queued behind the REST quota"* (DEVOPS) | `gh api`, the one client tried | the forge |
  | *"I could not establish the cause"* (DEV2) | fetching a job **log body** over REST | the outage — the check-run **steps** were reachable the whole time |
  | *"writes were never down"* (DEVOPS) | the one command they ran | every write path |

  ⇒ **A single instance reads as one pane being careless. Three, from two panes, inside one incident,
  reads as a property of working through a channel you did not choose.** ⚠ In each case the speaker
  had *not* tried the other path — so the claim was not overstated evidence, it was **evidence about
  a different subject entirely.**
  ★ Cheap remedy, and it is a sentence shape rather than a procedure: **name the method inside the
  claim.** *"I could not read the job log over REST"* is checkable and survives; *"I could not
  establish the cause"* is neither.
- ★ **A LEG THAT CAN NEVER RUN IN CI IS A LEG THAT ONLY EVER RUNS ON SOMEONE'S LAPTOP.** (DEVOPS.)
  Instance: `check-tools-index.py`'s wholesale-import leg asks `git log --diff-filter=A` how many
  commits added a directory's files. Under `actions/checkout@v4`'s default **depth-1** clone that
  returns **1 for every directory**, so **35 of this fleet's own instruments reported as another
  estate's, on every CI run.** ⛔ `git log` did not fail — it answered confidently over a truncated
  history, so the `returncode` guard written two commits earlier, whose docstring says *"never
  guesses"*, **was never reached**. Fixed at `8414cd7` by **both** halves: the tool refuses when the
  clone is shallow, **and** `fetch-depth: 0`. ⚠ Refusing alone is safe and insufficient — a leg that
  always refuses in CI has simply moved to a laptop. ⇒ Shallowness became **a separate question
  asked first**, not an error case of the same call.
- ⚠ **One measured instance.** This is filed as a class because its remedy generalises and is
  mechanisable, **not** because recurrence has been shown. If a second instance does not appear, it
  is a finding about one file and should be demoted rather than defended.

---

## ⛔ What is NOT established

- **The frame is not universal, and that is what makes it a claim.** #80 is outside Class A by
  construction. #19 (nine agents, one working tree) is interference, not a collapse. #29 is a
  record, not a class. **A taxonomy that accommodates everything explains nothing** — if a future
  finding cannot be placed outside these two, that is evidence the frame has stopped discriminating.
- ⚠ **#80's authoring-time question has now caught exactly one thing, PROSPECTIVELY — and the
  instance is weaker than it sounds.** ⇒ Re-surveying #73 I asked *is the noun the string or the
  behaviour?* **before running anything**, and used `return 2 | sys.exit(2)` instead of
  `contains "VOID"`:

  ```
  behaviour  31 of 33      vocabulary  15 of 33      behaviour-but-not-vocabulary  16
  ```

  ⛔ **The original #73 survey used the vocabulary predicate** and was hand-widened to a correct
  number only because one counter-example happened to surface. **This time the question fired before
  the number existed**, which is the thing this bullet previously recorded as never having happened.

  ⚠ **What it does NOT establish, and the limits are the point:** I asked the question **because I
  was holding the rule** — the condition the rule is supposed to work without. It was **my own
  earlier survey**, so the failure mode was one I had already been burned by. **All six original
  instances were still found by peers after the fact, and n is now 1.** ⇒ *Recorded because a
  document that only ever adds limits stops being a measurement of anything*, not because one catch
  settles it.
- ⛔ **#214's partition rule has caught exactly one thing, retrospectively, and it was mine.**
  `discriminates.py` in the `tools/*.py` complement. Every other instance in that section was
  placed by argument against a failure someone had *already* found. **Whether the form catches a
  case nobody suspects is the measurement, and it is open.** [NOT-YET-MEASURED]
- ⚠ **The partition rule REFUSES the denominator case and the refusal is stated rather than
  patched.** TEAMLEAD's one-ref instance sums perfectly and is still scope-wrong; it needs the
  second tell. **A single rule covering both would have been the more satisfying result and would
  have been false.**
- ⛔ **The set of hops is not closed, and one hour's evidence says so.** The section shipped with
  two and grew a third *during authoring*, when the author's own `$?`-after-a-pipe probe defeated
  both. **Three is what has been found, not what exists** — a fourth hop arriving is the expected
  case, not a surprise, and the frame should be read as a floor.
- **Class A's membership is a reading, not a measurement.** I placed seven issues into it by
  argument. Each issue's own evidence is measured; the *grouping* is not, and the grouping is what
  this file adds.
- **No claim the remedies are complete.** #2, #16, #26, #29 and #58 have DEV legs open. This
  reconciles the design; it does not report the execution.
- ⛔ **Class C is named from six instances I did not measure.** TEAMLEAD supplied all six; I
  re-verified none of them. The partition into three hops is mine and the evidence is borrowed —
  **if any instance is mis-described, the count moves and the three-leg argument may not survive.**
- ⚠ **Class C's criterion was derived from those same six**, so passing it against them is fitting.
  **The first closure it stops that nobody argued in advance is the evidence.** [NOT-YET-MEASURED]
- **Four of the nine issues carry no acceptance criteria** (#36, #39, #73, #80) — precisely the
  four with no DEV leg. Recorded rather than invented here.

---

## ★ CLASS E — the reason was discarded before you asked, and another channel still has it

Class A is two states colliding into one value at a boundary. Class B is a rule whose noun is one
word too narrow. Class C is a true reading of a proposition nobody asked about. Class D is one
producer emitting a finding into two channels that **contradict**. **This one is none of those, and
it is the one you cannot fix by fixing the thing you are looking at:**

> **Two channels carry the same fact and one of them carries less of it. They do not disagree —
> the lossy channel is CORRECT. It simply cannot express the distinction the reader needs, and the
> reader has no way to learn that a fuller channel exists.**

⛔ **This is why no derivation repairs it.** Class D's remedy works because one channel is derivable
from the other, so you make the exit code a function of the printed word. Here there is nothing to
derive *from*: the information was gone before the value was produced. **The remedy is not to fix
the channel. It is to CHOOSE a different one.**

⚠ **It survives because the lossy channel is the cheap one, the default one, and the one that
answers.** Nothing fails. You get a well-formed answer to a coarser question than you asked, and
the coarseness is invisible from inside the answer — the same property that makes Class A's
collapsed pair undetectable, arriving one layer earlier.

### The instance, measured 2026-08-20 while falsifying #336

The question: *is `APPROVE` permitted on a self-authored PR under one shared credential?* Asked
over REST, four times, at three different budget states:

```
POST /repos/…/pulls/333/reviews  {"event":"APPROVE"}   ->  HTTP 403 Forbidden
```

⛔ **`403` is the correct answer, and it is worth nothing.** A refused self-approval returns 403. So
does an exhausted rate limit, a scope failure, a blocked actor, and roughly a dozen other causes.
**Three of the four attempts were the budget**, and the first one arrived with a conclusion already
attached: *APPROVE is refused, the split is confirmed.* That conclusion was **true, and the evidence
could not support it.**

What was built to compensate — all of it correct, all of it unnecessary:

| scaffolding | purpose | whose |
|---|---|---|
| assert on the **body**, never the status class | recover the discarded reason | DEV2 |
| a **known-positive control** posted seconds apart | prove the probe VOID rather than negative | DEV2 |
| a **zero-side-effect canary** (`POST` to an id that cannot exist) | test the channel without mutating it | DEV2 |

⇒ The known-positive control is what actually worked: `event=COMMENT` and `event=APPROVE`, same
endpoint, seconds apart, **both returned 403** — and *a known positive that fails is the only thing
that distinguishes "the answer is no" from "the question never ran."*

★ **Then the same question, over the other channel:**

```
gh pr review 333 --approve
    > POST /graphql            < HTTP/2.0 200 OK
      "message": "Review Can not approve your own pull request"
```

**One call. No control, no canary, no budget reasoning.** The fact had a name the whole time, on a
channel nobody had asked.

### ⛔ And the inversion, which is why the remedy is not "prefer GraphQL"

The refusal came back as **`200 OK`**.

| channel | status | reason | what the status is worth |
|---|---|---|---|
| REST | `403` | discarded | **under-determined** — a dozen causes |
| GraphQL | **`200 OK`** | preserved, in the body | ⛔ **nothing** — a *refused* operation returns success |

⇒ **Neither channel carries both halves. REST keeps the alarm and loses the reason; GraphQL keeps
the reason and loses the alarm.** A caller checking HTTP status over GraphQL reads a capability
refusal as a pass. `gh` rescues its own callers by translating the body into `rc=1`; `curl`, or a
raw `gh api graphql`, gets no such rescue.

### ⇒ The remedy, and it is an authoring-time question, not a runtime one

> **Before building an instrument to recover information a channel discarded, enumerate the other
> channels to the same fact and check whether one of them preserves it.**

⚠ **This does not retire the scaffolding — it BOUNDS it.** A canary, a known-positive, and
body-assertion are what you build when no fuller channel exists. Reaching for them *first* is how an
hour goes into reconstructing something that was never thrown away.

Two corollaries, both measured the same day:

1. ⛔ **A canary must travel the same surface as the work it gates, and must NAME that surface.**
   Committed twice within twenty minutes, by two roles, *inside the technique meant to prevent
   misreading a refusal*: DEV2 gated `gh pr create` on a REST canary and declined to open a PR they
   opened 30 seconds later; **I armed a REST canary and used it to gate filings that all run over
   GraphQL**, then sat on a finished answer while the channel I needed was open the whole time. The
   canary was **correct about a channel neither of us was going to use.**
2. **Assert on the body, never the status class — on BOTH channels, for opposite reasons.** On REST
   because the status is under-determined; on GraphQL because the status is meaningless.

### ⛔ The limit case — a probe that makes NO request, whose silence looks like data

Found the same evening, in the follow-up to the message where the surface-scope rule was accepted:

```
GH_DEBUG=api gh pr view 315 --json number             ->  NO HTTP request logged at all
GH_DEBUG=api gh pr view 315 --json mergeStateStatus   ->  > POST /graphql   < 200 OK
```

`--json number` is **derivable from the argument**, so `gh` answers it without calling anything. The
probe asked for the one field that requires no request. ⇒ **The counter did not move because the
counter was never exercised** — and *not-moving was read as evidence about the counter.*

★ **This is the corollary's limit case.** The earlier two instances used the *wrong* surface; this
one used **no surface at all**, and produced a reading indistinguishable from a probe that ran and
observed nothing. ⇒ **A probe that makes no request is #58's `never ran` arriving at the probe
layer** — the same collapse the exit-code convention exists to prevent, one level below where
anybody thought to look for it.

⚠ **Three roles, three instances, one evening — the third committed while accepting the rule for
the second.** The rule is easy to agree with and evidently hard to apply to your own next probe.
⇒ Which is why the operational form must be mechanical rather than remembered:

> **Show the request. If a probe cannot name the call it made, it did not make one.**
> `GH_DEBUG=api` does not presuppose the thing under investigation; every counter-based method here
> is circular, because the counters are what is in doubt.

⚠ **Still unresolved, recorded rather than dropped**: whether the `graphql` counter is otherwise
accurate. Same command, same field — three calls moved it `+0`, a later single call `+1`. Nobody
chased it and nothing here depends on it.

⇒ **Audited on this repository's committed instruments**: no `tools/*.py` or `scripts/*` invokes
`gh api graphql`; every occurrence is docstring prose, a comment, or a test fixture. ⚠ **The
exposure is therefore in the uncommitted population** — `api-budget.py` counts **509 `gh api
graphql` invocations across nine transcripts**, which is ad-hoc inline instrument work (#261: 87% of
it), and it is **not greppable from the repository**. A clean grep of `tools/` establishes nothing
about the shape of the traffic.

### ⚠ What is NOT claimed

- **Not that REST is defective.** `403` is a correct answer to *may this request proceed*. The
  defect is asking it a question it was never shaped to answer.
- **Not that every GraphQL mutation error returns 200.** One endpoint (`addPullRequestReview`), one
  API, measured once. Not surveyed, not generalised.
- ⛔ **Not a member of Class D.** The two channels here never contradict; one says strictly less.
  DEV2 drew that boundary and it is the reason this is filed separately rather than folded in —
  *contradiction* is repaired by derivation, *under-determination* cannot be.
- **Not derived from a fixed bug.** ⚠ Per Class D's own note, a class filed on a live bug decays
  into a bug report. This one is filed on an **instrument-design rule**; the REST behaviour is not
  a defect anyone will fix.

### The third instance, same day, different layer — and it cost four panes

`tools/api-budget.py` reads `.resources.core` from `gh api rate_limit` and prints it as *"one pool,
shared by every agent and every tool"*. Measured: `gh`'s high-level commands go to `POST /graphql`
(established from the request log via `GH_DEBUG=api`, **not** from a counter — the counter is the
instrument under suspicion), while `core` reported `0/5000` and REST **reads** were served from a
counter showing `4727` remaining under the *identical* `X-Ratelimit-Resource: core` label.

⇒ One label, three counters, and **the label cannot say which pool is empty.** Nothing in the 403
response says *write*; nothing says *REST*. Four panes lost work to it inside one hour — TEAMLEAD
held a PR 35 minutes and told five panes to build offline, DEVOPS held five comments ~30 minutes,
DEV2 declined a PR, and I held a finished report.

★ **And DEVOPS's observation is the second cost: the reading mis-gates the DECISION TO RETRY**, so
the pane that would discover the error is the pane that stops looking. **DEV2 supplied the
mechanism — the broken reading also supplies the retry time.** `reset` comes from the same field.
⇒ *A silent failure that also sets its own duration.* A pane waits on a number the instrument
invented, produces no error, and nothing teaches anyone it was wrong. Filed as #347.

⚠ **Attribution**, since four roles are in this section: the class and this write-up are DEV3's, at
TEAMLEAD's direction. **DEV2 named the contradiction/under-determination boundary, designed the
known-positive control and the zero-side-effect canary, and caught the surface-scope error in
both.** DEVOPS established the retry cost and **retracted an all-clear of their own, unprompted,
through the same channel and to the same recipients, within minutes.**
