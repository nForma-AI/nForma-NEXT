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

## ⛔ What is NOT established

- **The frame is not universal, and that is what makes it a claim.** #80 is outside Class A by
  construction. #19 (nine agents, one working tree) is interference, not a collapse. #29 is a
  record, not a class. **A taxonomy that accommodates everything explains nothing** — if a future
  finding cannot be placed outside these two, that is evidence the frame has stopped discriminating.
- ⛔ **#80's authoring-time question has never caught anything.** All six instances were found by
  peers *after* the failure. Whether asking it prospectively produces a catch is unmeasured, and
  this document does not strengthen it by restating it.
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
- **Four of the nine issues carry no acceptance criteria** (#36, #39, #73, #80) — precisely the
  four with no DEV leg. Recorded rather than invented here.
