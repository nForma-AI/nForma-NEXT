# The estate boundary, and the three channels it has collapsed at

⛔ **Presence in this repository is not evidence of belonging to it.** That sentence is the whole
document. Everything below is the measurement that forced it and the state it introduces.

*Measured 2026-08-20 at `2fcd8e1`, on `origin/main`, by `git ls-tree`/`git show` — no API.*

---

## What was measured

`ac6a946` — *"tools(teamlead): 22 instruments out of a temp directory and into version control"* —
promoted `tools/teamlead/` into `nForma-AI/nForma-NEXT` in one commit, from a
`/private/tmp/claude-501/…` scratch directory. ⚠ **That directory is not single-estate.** More than
one fleet wrote to it, and `git add` of the whole directory carried the difference in.

```
POPULATION   every *.py under tools/teamlead/ on origin/main            19 files
             ├─ instruments                                             16
             └─ test_*.py                                                3

PREDICATE    file cites an issue in #1066–#1243  (this repo is in the 300s)
             OR contains akash | blazing | Tron | provider

CHANNEL      git show origin/main:<path> — the committed blob, not a working tree

READING      foreign instruments   8 of 16
             foreign tests         3 of 3
             ── total             11 of 19 files
```

**The specimen that settles direction for at least one file.** `tools/teamlead/w1226.py` is not an
instrument at all. Line 1 is `# control-plane/api/handlers/workloads.py`; the docstring reads
*"Unified Workloads API — Platform-Agnostic Container Management … across GKE (Kubernetes workers),
Akash deployments, and CronJobs."* In-tree elsewhere in the directory:
`Borduas-Holdings/Blazing-Back`, `/worker-blazing-rpg/exec`.

**The control, and it is a real one.** `tools/architect-sweeps/` — 3 of 3 **clean**, zero markers.
⇒ The predicate discriminates. A scan that reddened every directory would have established nothing.

### ⚠ A near-miss worth keeping: two different 19s

The instrument census and the marker scan both produce **19**, over **different sets**:

```
19 (A)  every .py under tools/teamlead/          16 instruments + 3 tests
19 (B)  instruments check-tools-index flagged     16 teamlead   + 3 architect-sweeps
```

`11 of 19` is true of **A** and was stated where **B** was in hand. Numerically identical
populations are the easiest wrong join to make and the hardest to see, because the arithmetic never
complains. ⇒ *`goals/README.md` criterion 5, POPULATION leg, caught in the writing of this file.*

---

## ⛔ The new state: QUARANTINED, and why the obvious three are all wrong

A file under `tools/` was previously in one of two states — **indexed** or **missing a row**. Both
presuppose it belongs here. The third state does not:

```
LOCAL       provenance evidence places it in this estate
FOREIGN     provenance evidence places it elsewhere
UNCLAIMED   no provenance evidence either way        <- boxwatch.py is the specimen
QUARANTINED present, and belonging is an OPEN QUESTION — not ours to close
```

- ⛔ **Do not index them.** A row in `tools/README.md` **asserts** the file belongs here. That is
  making a claim true by damaging the thing it describes — the failure mode
  `scripts/check-tools-index.py` documents in its own header.
- ⛔ **Do not silence the checker.** *"A gate that never refuses looks identical to one that does
  not exist."* The CI gate is **RED**, deliberately, and red here means *unresolved estate
  question* — not documentation debt.
- ⛔ **Do not rewrite history.** The commit is pushed, to a second GitHub org, with commits authored
  across nine panes sharing one working tree. No `filter-branch`, no force-push, no deletion. ⚠ This
  is not a caution, it is a **boundary of authority**: disposition of pushed history belongs to the
  operator. *(Ruled 2026-08-20; the operator elected quarantine.)*

## The fixture rule: the shape, never the owner

A detector that reads the tree will read **its own test data**. Three files carried real estate
names as literal fixtures and were reported as contamination; one detector reported *itself*. Each
report was **correct** — nothing in the string distinguishes a fixture from a dependency.

⛔ **So the strictness is right, and the fixtures are what change.** A detector that exempted
"obvious fixtures" would have to GUESS, and a guessing detector commits the use-vs-mention error it
exists to prevent. ⚠ Nor do these belong in `tools/QUARANTINE.txt`: an entry there asserts the file
*is* contamination, which is a second false claim replacing the first.

> **THE FIXTURE NEEDS THE SHAPE, NEVER THE OWNER.**
> Assemble the string from fragments at run time, with the reason in a comment, so it still
> exercises the predicate while asserting no owner.

### The discriminator, which is about the string's ROLE and not the string

**Is this string an INPUT TO THE MATCHER, or a CLAIM ABOUT A REAL ENTITY?**

| the string | role | verdict |
|---|---|---|
| detection vocabulary the matcher tests against | input to the matcher | **MACHINERY** — stays literal |
| the positive specimen | claim about an entity | **DATA** — assemble |
| the **known-negative** specimen | claim about an entity | **DATA** — assemble |
| a worked example in a docstring | claim about an entity | **DATA** — assemble |
| a bare issue number in a fixture | no entity at all | **PURE SHAPE** — keep literal |

⇒ The last row is why the rule is not "remove every literal": a number **asserts no owner**, so it is
already what the rule asks a fixture to be. And the first row is why it is not "assemble everything":
a detector must hold its vocabulary in executable position or it cannot match at all.

### ⛔ The goal is NOT to make the file read LOCAL

A detector reads FOREIGN on its own detection vocabulary and **should** — that is the `DETECTOR`
state, and it is correct. ⚠ A rule that pushed a file toward LOCAL would damage the detector to make
a checker comfortable, which is the failure mode #26 names. The defect being fixed is narrower and
only this: **a fixture indistinguishable from a dependency.**

### ★ A shape-only fixture is never burned, because there is no owner to leak

A specimen that lives in the tree **cannot be a control for a detector that reads the tree** — once
committed, the name is in the vocabulary of the thing under test. Two specimens have been spent this
way already: one by being published in an issue, one by being committed as a literal.

⇒ The remedy is not a better-disguised name. It is a string that **cannot be mistaken for an owner
at all**, assembled at run time — which makes the fictionality *structural rather than documented*.
⚠ A documented property decays the moment nobody reads the line; an enforced one cannot. Nothing
downstream needs telling, and no later sweep can misread it.

### ⚠ The known-negative is the row that looks safe, because it names US

A hermetic suite must construct a **synthetic identity**, and any synthetic identity differs from the
real one. So the row asserting *"our own slug is NOT foreign"* is **guaranteed** to contain a
not-quite-ours — our own name, slightly wrong — and it reads FOREIGN to the live detector while
looking like the safest line in the file.

⇒ This is not an oversight in any one file. It is **a property of hermeticity**, and it means the
rule applies to the negative specimen exactly as it applies to the positive one.

### What this section does NOT establish

⛔ It does not make a file's silence evidence. A fixture assembled from fragments still exercises the
predicate, but a detector finding nothing has established **nothing about absence** — `UNCLAIMED`
must never collapse into `LOCAL`.

⚠ And it does not close the reverse case: an estate present as **vendored source with no path, no
issue number and no name** asserts nothing for any of these rows to catch, and reads clean whether or
not the fixtures are assembled.

*Doctrine by DEV3 (`the shape, never the owner`; the strictness-is-right ruling), ratified by
TEAMLEAD. The role discriminator, the known-negative case, the doc-example case, the pure-shape
exception and structural fictionality: DEV3 and DEV5 jointly, 2026-08-21. ⚠ This section deliberately
contains **no owner literal** — a page saying "never write the owner" that wrote one would be its own
counterexample, and would be reported by the detector it describes.*

## ⛔ What this does NOT establish

- **Direction, for 10 of the 11.** A file citing `#1177` may be the other estate's committed here,
  or ours written *about* it, or dual-use. Only `w1226.py` is settled, by being another product's
  application source rather than any kind of instrument.
- **The reverse leak.** Whether *this* repository's instruments were promoted into the other estate
  is **unmeasured and unmeasurable from here** — the fleet has no standing in that repository and
  did not look. `[NOT-MEASURED — OPERATOR ONLY]`
- ⛔ ~~**That the predicate is complete.**~~ **REFUTED, same day, by DEVOPS.** This file said a
  third estate *"would leave markers this scan has never seen, and would read as `LOCAL`."* There
  was one, and it did. `scripts/check-tools-index.py` (#315) evaluates **executable position rather
  than mention** and found **`DigitalFrontier-infra`** — 7 files under `tools/teamlead/` point at
  `/Users/jonathanborduas/code/DigitalFrontier-infra`. ⇒ **`UNCLAIMED` must never be collapsed into
  `LOCAL`** — that bar is what kept those 7 out of `LOCAL` while the predicate was still blind to
  them, and it is the only reason this refutation is a correction and not a retraction.

  ⚠ **AND THE CONTAMINATION IS NOT CONFINED TO `tools/teamlead/`**, which this file implied
  throughout and never stated as a limit — the worst kind of claim, because it was never available
  to be checked. `tools/memory-index-check.py`, root-level, tracked and indexed on `main`:

  ```python
  ap.add_argument("--dir", default=os.path.expanduser(
      "~/.claude/projects/-Users-jonathanborduas-code-DigitalFrontier-infra/memory"))
  ```

  ⛔ That is a **default in executable position**, so `python3 tools/memory-index-check.py` with no
  arguments **audits another estate's memory while reporting as an instrument of this one.** Not a
  stale string — a live reading bound to the wrong estate.

- ⚠ **MENTION IS NOT USE, and this file's own predicate cannot tell them apart.** A marker grep over
  `tools/` proper returns **12 of 70**; the executable-position predicate returns **1 of 33**. The
  grep counts `tools/estate-provenance.py`, which contains the vocabulary **because it detects it**.
  ⇒ Every count in the measurement block above is a MENTION count and is an upper bound, not a
  reading. `tools/use-not-mention.py` exists in this repository and was not applied here.
- **That secrets are absent.** `tools/teamlead/README.md` records a secrets scan over its 22 files
  finding nothing. That scan predates this finding and was not re-run against this question.

⇒ **A complete index of a contaminated directory is a MORE confident wrong answer than an
incomplete one.** *(DEV2's proxy test, adopted verbatim; it is better than the one it replaced.)*

---

## The channel count, which is the reason this is doctrine and not an incident

Same collapse — *which estate does this belong to* — now measured in **three** channels:

| # | channel | how it collapsed |
|---|---|---|
| 1 | peer messaging | a bare role name addressed a pane in another fleet |
| 2 | work routing | triage carried in prose, with no queryable field to bind it |
| 3 | **the filesystem** | a shared scratch dir `git add`-ed wholesale at the commit boundary |

⛔ **The collapse itself is CLASS A**, not Class C. *Which estate does this belong to* is a
**pair** — ours / not-ours — arriving as **one value** at three different boundaries. No reading is
bound to a wrong proposition anywhere in it, so Class C has no part here. *(Ruled by ARCHITECT,
2026-08-20; this file said Class C and was wrong by one letter. The argument did not change — only
the filler did.)*

⚠ Three channels, one collapse, and each was fixed **at the instance** rather than at the boundary.
That is `docs/DEFECT-CLASSES.md` **Class B operating on Class A's remedy**, exactly as that document
predicts: **state the remedy at the scope of the boundary, not the instance.**

★ That sentence is a **template, and the X varies** — `Class B operating on <class>'s remedy`.
`docs/DEFECT-CLASSES.md` instantiates it with C because C is where it was first noticed; reading C
as the only filler is itself the Class B error, one level up. The noun that goes missing is *whose
remedy*.

⇒ The remedy at the scope of the boundary is `tools/estate-provenance.py`, and until it exists and
has been shown to produce **both** verdicts on live data, this file is a description and not a guard.

## Provenance of the claims in this file

⛔ **Two different things were checked by two different roles, and they are not interchangeable.**

```
THE MEASUREMENT   8 of 16 · 3 of 3 · w1226.py · the architect-sweeps control
                  found by DEV2, re-measured independently by TEAMLEAD on origin/main
                  ⚠ NOT verified by ARCHITECT — stated explicitly by them when ruling
THE TAXONOMY      Class A, and Class B operating on its remedy
                  ruled by ARCHITECT, who read this file at the ref before ruling
```

⇒ **Ruling on the mapping is not endorsement of the measurement.** Anyone relying on the numbers
above is relying on DEV2 and TEAMLEAD, and on nobody else.
