# nForma-NEXT — founding thesis

> An autonomous delegation IDE. nForma becomes a Daintree plugin; the coupling is deliberate,
> because delegation without a substrate is just prompting.

Everything below is derived from a measured 8-hour session running the TEAMLEAD/IMPLEMENTER
pattern by hand — one orchestrator, five peer agents, one repo, one CI. Not from speculation
about what such a product might need.

---

## 1. The bottleneck is the orchestrator, not the agents

Measured: agents sat idle for 10–13 minutes at a time waiting for permission to **file an issue**
or **watch a CI run**. Across one hour, **six instructions** were never delivered at all, and the
fleet read as "idle, awaiting work" when it was "blocked on replies that never arrived."

The orchestrator's polling latency became the fleet's clock. Throughput was bounded by how often
one coordinator looked, not by how fast five agents worked.

**Consequence for the product:** the primary primitive is not better dispatch. It is
**durable delegated authority** — a standing grant of what an agent may do unattended, with an
explicit reserved list. "Ask before acting" is the default that kills autonomy.

```
granted   : file/close issues with evidence · push own branch · open PR · watch CI ·
            re-run a leg diagnosed as non-attributable
reserved  : merge · production/deploy · history rewrite · credential handling · goal replacement
```

## 2. Delivery must be verified by effect, never by acknowledgement

`sendCommand` returned `{"sent": true}` for messages that reached nobody, three distinct ways:
a pane whose agent had exited, a workspace that silently flipped to another project, and text
that landed in the input box and was never submitted. ⚠ The third **leaves the text in the box**,
so the intuitive repair — send it again — double-delivers.

`lastTransitionAt` advanced in **all three**, so the obvious verifier — compare a pre-send stamp —
passes on every false case.

**Measured since: five, and the fifth is not on this chain.** A mode is individuated by *which
arrow fails*, whether the loss is *terminal or transient*, and *what false signal accompanies it*
— never by which API produced the signal, or the list grows once per transport.

| # | mode | arrow | terminal? | false signal |
|---|---|---|---|---|
| 1 | pane's agent had exited | gen→del | terminal | `sent: true` |
| 2 | workspace silently flipped | gen→del *(wrong target)* | terminal | `sent: true` + `lastTransitionAt` |
| 3 | text in the box, never submitted | del→consumed | terminal | `sent: true` · also `terminal.inject` → `ok` |
| 4 | alive, delivered, queued, **not yet read** | del→consumed | ⚠ **transient** | `sent: true` + the pane reads *available* |
| 5 | a standing instruction edited into a file **the launch path never opens** | gen→del | terminal | ⛔ **none** |

⛔ **Mode 4 does not lose the message**, which is why nothing surfaces it: it is latency wearing
the appearance of availability. The remedy is a **content-free nudge** — never a re-send, because
the queued copies are still there.

⛔ **Mode 5 is a PULL failure; 1–4 are PUSH failures.** Nothing was sent, so nothing returned
true. ★ A wrong token eventually gets checked; **an absent signal gives nobody a reason to look**,
which is why this one persisted longest — measured, committed prompts had reached **one of eight**
live sessions. ★★ And its symptom is inverted: an undelivered *rule* does not look like a delivery
failure, **it looks like disobedience**. Seven roles were not emitting a `STATE:` line nobody had
ever asked them for. No other mode misattributes its failure to the recipient.

⚠ **The count is of modes OBSERVED.** Mode 5 was invisible for a day because it emits nothing, so
the absence of a sixth is the absence of a signal — not the absence of a mode.

**Consequence:** an instruction is a tracked object with a lifecycle
(`queued → delivered → acknowledged → acted-on`), and the terminal state is established by an
**off-pane effect** (branch pushed, file changed, issue transitioned), not by the substrate's
own report.

## 3. Instrument failure must be un-collidable with data

Nearly every wrong call was an instrument failure wearing the shape of a clean answer:

| reading | looked like | actually was |
|---|---|---|
| `gh api …/logs` empty | "no failures found" | stderr suppressed; gh refused escape sequences |
| unpaginated issue list | 77 open issues | 125 — one page |
| terminal tail at `lines=5` | "input box empty" | box renders above the window |
| `mergeable_state: clean` | ready to merge | **never checked** — 0 of 5 required contexts present |
| check-run `conclusion: ""` | falsy → treat as failure | still running |
| CI rollup mid-populate | "that job is absent" | not yet scheduled |

**Consequence:** every reading carries `{valid, value, error}`. A failed read can never be
mistaken for a legitimate domain value, and an invalid reading preserves enough diagnostics to
say *why*. "Absence read as success" and "ambiguity read as success" are the same defect and it
recurs at every layer.

## 4. Correction flows upward — design for subordinate refusal

Every consequential correction in the session came from an agent refuting the orchestrator with
evidence, or from interrogating an instrument. **None came from the orchestrator re-reading its
own reasoning.**

Two that mattered: an agent refused an instruction that would have buried a real defect behind a
38-minute timeout; another refuted a causal conclusion by pointing out that the field being used
as proof was the very field the check exists to cross-check.

**Consequence:** disagreement is a first-class transport, not an exception path. An agent must be
able to return `REFUSED(evidence)` and have that be a normal, recorded outcome. An IDE that only
models compliance loses its best error detector.

## 5. "Can it merge" silently substitutes for "should it merge"

The orchestrator spent multiple cycles determining whether a PR's red leg was clearable without
ever asking whether the PR was worth clearing. It rested on a refuted premise and inverted a
standing operator decision. Only a direct human question surfaced it.

CI triage *feels* like judgment: it produces findings, corrections, and evidence — everything
except the decision about whether the change should exist.

**Consequence:** admission and merit are a distinct, prompted phase. The IDE must not present a
board where green is the only rendered signal, or it will train its operator into the same
substitution.

## 6. Evidence is state-bound

CI tests the merge result, so a green describes a *tree*, not a branch. Readings must carry the
state they were taken against (commit, base, config generation, measured-at), and a base change
invalidates them rather than aging them.

Related: cross-agent comparison controls for **contention** but not for per-deployment causes.
"Only this one failed" is not attribution on its own — the tooling should state what a comparison
holds constant, in the output.

## 7. Autonomy needs a bound the bounded agent cannot raise

Cumulative consequence is separate from per-action authorization. The orchestrator merged 27 PRs
before any ceiling existed, then could not raise its own limit once one did — correctly.

**Consequence:** explicit-unit budgets (merges/24h, production mutations/session, spend), lowerable
by the agent, raisable only by the operator, and **non-inheritable** across sessions — carrying a
raised bound forward is self-renewal by another route.

---

## What this implies about the plugin boundary

Daintree owns the **substrate**: panes, sessions, workspaces, delivery, agent lifecycle.
nForma-NEXT owns the **discipline**: authority grants, instruction lifecycle, evidence validity,
admission/merit, budgets, and the correction channel.

The coupling is worth it precisely because §2 and §3 cannot be solved from outside the substrate.
A client-side helper can *detect* a workspace flip or an unsubmitted instruction; only the host can
prevent them.

## Open questions for the operator

1. Does `nForma-AI/nForma` PR #406 (Daintree fleet primitives) move here, or land there and get
   migrated?
2. Is the existing `bin/*.cjs` + `commands/nf/*.md` shape carried forward, or is the plugin surface
   a clean break?
3. Does nForma-NEXT keep the formal-verification lineage (TLA+/Alloy), or is that scope dropped
   with the pivot?
