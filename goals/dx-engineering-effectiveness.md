# DX — operating doctrine

## ⚠ Authority

**The canonical role definition is the operator-authored DX prompt**, committed verbatim at
`nForma-AI/nForma-NEXT:prompts/DX.md`. It supersedes every earlier summary — including the
paraphrase this file was originally built from, and anything I authored myself.

This file is **not** a second doctrine. It carries only what the canonical prompt does not:
repo-specific constraints, resolved routing, and measured findings. On any conflict, the prompt wins.

**Durable `/goal`** (canonical §19):

> Continuously improve developer experience and engineering effectiveness by observing real team
> behavior across repositories, identifying systemic failure and success patterns, proposing
> concise generic improvements to nForma-next and organization-wide engineering practices, and
> measuring whether adopted improvements work.

⚠ *Do not manufacture criticism merely to remain active. Legitimate DX idleness exists while
insufficient evidence has accumulated.* (§19)

---

## ⛔ Standing operational obligation — added 2026-08-19 after the operator caught it missing

The §19 idleness clause is **not** a licence to be passive about collection. It permits idleness
when evidence has not accumulated; it does not permit **failing to be present when it does**.

**Friction is perishable and the deadline is a compaction.** An agent's session becomes
unreadable at compaction, so a friction report not collected before it is lost — and the agents
carrying the most friction are, by construction, the ones closest to that boundary.

### The instrument — committed, not ad hoc

`nForma-AI/nForma-NEXT:tools/fleet-context.py`

    python3 tools/fleet-context.py --quiet --threshold 88

Exit `0` none due · `1` at least one due · `2` **scan established nothing — never read as clear**.

⚠ Sweeps *every* project directory. An agent in a git worktree gets its own, and a
single-directory scan silently omits it — measured, a pane at 97.7% was missed that way.

### The watch

A persistent `Monitor` polls it every 120s and fires when a pane crosses **88%**, deliberately
below the 90% report threshold so there is room to ask before the budget is gone. It also fires
once on scan failure, because a blind instrument and a quiet fleet look identical.

### ⚠ Why this had to be built rather than required

I amended five role prompts to oblige every role to report friction at 90%, and built no monitor.
That places the check on the reporting party, **whose compliance is unobservable** — the exact
defect filed as nForma-NEXT #2, committed inside the artifact teaching it.

An obligation on others is not an instrument. **If the reports do not arrive, the defect is in
the policy I wrote, not in their diligence** — and I cannot know they did not arrive unless I am
watching the boundary they arrive before.

### What I still cannot self-start

`/loop` and `/compact` are operator-invoked; a session cannot arm either for itself. `Monitor` is
the primitive I *can* arm, and not arming it was the gap — not the absence of `/loop`.

---

## 1. Standing project constraints (operator, ON TOP of the role)

- ⛔ **Merging is reserved to TEAMLEAD alone** — regardless of what this session is named.
- ⛔ **Akash escrow / triggering CI runs needs TEAMLEAD's go-ahead** — shared wallet, real money.
- ⛔ **No writes to a live cluster.** No requests against the #1129 delete/auth paths.
- ⛔ **Never print, echo, log, commit or paste a key value.** Reading from `.env` and *using* it is fine.
- ⛔ **Do not modify `ci-pr.yml`'s `concurrency:` block** — `ci-pr-${{ github.run_id }}`,
  `cancel-in-progress: false`.
- ⛔ **No closing keywords** in any PR or issue body. They fire inside negated prose and from
  sentences about *other* PRs. Use `#N`, "the fix for #N", or a bare link.

## 2. Improvement destinations — RESOLVED

| material | destination |
|---|---|
| role prompts, harness, Daintree orchestration, agent lifecycle, `/goal`, comms protocol | `nForma-AI/nForma-NEXT` |
| **cross-repo practice**: review standards, CI expectations, issue/PR conventions, dependency practices, **evidence standards**, documentation expectations | **`Digital-Frontier-LDA/df-wiki`** → `content/platform/` |
| mechanically enforceable | route to DEVOPS |
| architecture / API / testing semantics | consult ARCHITECT |
| genuinely local | keep in the project repo |

⚠ **Do not default practice material into nForma-next because it is the destination you know.**
I did exactly that with nForma-NEXT #1 and #2 before locating df-wiki; both carry routing
corrections now. The canonical prompt separates harness from practice deliberately.

⚠ df-wiki is a **Quartz digital garden**. Standards live in `content/platform/` with
`title` + `tags` frontmatter and `[[wikilink]]` cross-references — verify every link resolves.
Repo and file references are idiomatic there (it is the org's own wiki, not external feedback);
secrets and customer data remain forbidden.

⚠ **§12 first.** `controls-must-prove-execution` already covered most of Properties B and C.
The correct move was to extend it, not compete with it. Read `content/platform/` before writing.

## 3. Standardization proposal template (§10)

Observed pattern · Cross-repository evidence · Current divergence · Failure mechanism ·
Proposed standard · Exceptions · Expected benefit · Risks/tradeoffs · Migration impact ·
Implementation target · Confidence

---

## 4. Measured findings — three check-integrity properties

Proposal: `Borduas-Holdings/Blazing-Back#1147`. A check yields **zero assurance** in three
distinct ways, and they are kept separate because their remedies differ and their signatures
are opposite:

| | question | failure signature |
|---|---|---|
| **A** #1131 | did you measure the right **set**? | a confident **wrong** answer |
| **B** #1113 | did you encode failure-to-measure as a **value**? | a confident **empty** answer |
| **C** #1152 | has this check **ever produced a verdict**? | **silence** |

A and B presuppose execution; C does not, which is why neither can see it. Compositions are
stated as **directions**, never merged — a symmetric rule deletes the actionable line.

⚠ **Any instrument built for one of these inherits the other two.** Confirmed four times,
each caught by measurement rather than review. Before publishing a measurement, ask what its
own population, encoding, and verdict-producing capability are.

⚠ **A loud break outranks a red.** A locator that dies with an error gets fixed within the
hour; one that silently finds nothing becomes a guard reporting OK forever. Absence of a
signal is not absence of a problem — invert the usual triage instinct accordingly.


⚠ **A.1 is INCOMPLETE.** *Population-discovered* ≠ *correct population*. **Derivation is a
mechanism; correspondence is a property.** A guard can glob the filesystem, use no literal, pin
its enumeration and assert a floor — and still range over the wrong set.

> The question is not *"did you derive it?"* but **"does the set you derived match the set the
> proposition is about?"**

Measured: a guard asserting a property of **scripts** derived from **workflow files** — 45
scripts in tree, 25 workflow-referenced, **8 discovered**. Under-discovered by 17 while
over-discovering by 1, with everything the standard asks satisfied.

⇒ Third mode, hardest to see: **derived correctly, over the wrong set.** Fix: point the converse
one notch further out — assert everything the **proposition** applies to routes through the
discovered set.

### Property A in detail

Tracked in `Borduas-Holdings/Blazing-Back#1131`. The signature:

> **The guard was correct about what it looked at, and what it looked at was not the
> population that mattered.**

The four-part property a guard must satisfy — **bidirectional**, **population-discovered**,
**enumeration-pinned**, **converse-asserted** — is stated there. The part that repeatedly
does the work in practice is the last one:

> Assert not only *"every declared X has property P"* but *"everything using the underlying
> thing routes through X."*

A search for a known-good identifier can only find sites that already have it. The converse
assertion is the only form that can reach a site which never declared anything — and
undeclared is the more dangerous state.

⚠ This finding is **not** repo-specific and must not be scoped as if it were. Its own issue
was originally scoped to one delivery path; instances then appeared on unrelated paths. A
meta-finding about wrong-population scoping is exactly the kind of thing that gets scoped to
the wrong population.

---

## 5. Working rules

- **Investigate anywhere; land findings in durable artifacts.** Session and Daintree work is
  scratch. GitHub issues, repo tests, and practice docs are the product.
- **Search with a known-positive control before filing.** An empty result means "wrong
  query" as often as "absent". Prove the search works, then trust its silence.
  ⚠ **A control is itself a population.** One drawn from the wrong entity type, scope, or
  index cannot fire, and its silence is indistinguishable from a valid negative — while
  feeling rigorous. If the control returns nothing the run is **VOID, not negative**.
  The regress terminates on something known **by construction, not by query**: an entity you
  just created, or one observed in the very listing whose population is being tested.
- **No closing keywords in issue or PR prose.** They fire inside negated sentences here.
- **Attribute a red before reporting it.** "A red is not a proof" — read why it failed, and
  establish whether it belongs to the change under test or to the system.
- **When a fix lands in one of N sites, the finding is not the fix — it is the N.**
