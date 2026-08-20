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

## Applying this

**Authoring a check:**
1. Name the two states the decision depends on telling apart.
2. Name the value each produces **at the boundary the consumer reads**. If they are the same value,
   it is Class A — introduce a third.
3. Name an input that produces the third value (#26's known-negative). If none exists, the third
   value is decoration.
4. If the states do not genuinely differ, say so explicitly rather than manufacturing one (#73).

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
- **Class A's membership is a reading, not a measurement.** I placed seven issues into it by
  argument. Each issue's own evidence is measured; the *grouping* is not, and the grouping is what
  this file adds.
- **No claim the remedies are complete.** #2, #16, #26, #29 and #58 have DEV legs open. This
  reconciles the design; it does not report the execution.
- **Four of the nine issues carry no acceptance criteria** (#36, #39, #73, #80) — precisely the
  four with no DEV leg. Recorded rather than invented here.
