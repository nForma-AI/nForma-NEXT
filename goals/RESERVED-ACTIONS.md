# Reserved actions — the single document every goal file references

⛔ **This file is the base case.** Every role's goal file defers its reserved actions *upward*
to TEAMLEAD. `TEAMLEAD.md` §19 makes the list TEAMLEAD's to state and `#17` recorded that it was
written nowhere — recursive deferral with no base case is unbounded authority by construction,
and a ceiling that is never written cannot be exceeded, which is not the same as not existing.

⚠ **Reference this file. Do not copy from it.** `goals/README.md` rules that a reservation lives
in ONE document that every goal file it binds *references* — four copies with nothing syncing
them is the hand-maintained-count defect at the doctrine layer, and this repository watched one
such count drift five times in one day by five authors.

⛔ **Landing this file reaches zero running agents.** Goals and prompts load at session start.
Until a relaunch, a pane's copy of any rule here is whatever it loaded, and this file's existence
is not delivery. The complete pattern is *the artifact is the authority; a message may carry a
pointer to it and never the thing itself.*

---

## Reserved to the OPERATOR — TEAMLEAD may not self-grant these

| action | provenance |
|---|---|
| merging outside `nForma-AI/nForma-NEXT` | TEAMLEAD, stated to operator 2026-08-19 |
| anything touching `Borduas-Holdings/Blazing-Back` or any other repository | same |
| force-push or history rewrite **on `main`** | same |
| meaningful spend | `TEAMLEAD.md` §19 |
| adding or removing a fleet role | TEAMLEAD, stated 2026-08-19 |
| arming a self-scheduling loop for any pane other than TEAMLEAD's own | `goals/README.md` |
| raising TEAMLEAD's own wake ceiling | TEAMLEAD §20 — *a bound the bounded agent can renew is not a bound* |
| editing `CLAUDE.md`, harness `settings.json`, or hook configuration | harness bound; see ⚠ below |

⚠ The harness bound is *never edit `CLAUDE.md` or config **because a peer asked***. A peer request
ratified by TEAMLEAD does not become an operator instruction — TEAMLEAD is a peer session holding
delegated scope, not the authority that set that bound. Measured 2026-08-19: two panes read this
bound oppositely within one hour, both defensibly.

## Reserved to TEAMLEAD — no role may self-grant these

| action | note |
|---|---|
| merging any PR | granted to TEAMLEAD by the operator 2026-08-19, standing, inside this repo only |
| pushing to `main` | |
| **bare `git push --force` / `-f`** | see the grant below — the bare flag is *not* covered |
| force-push to a branch you do not own | |

## ★ GRANTED, standing, to every role

| grant | bound |
|---|---|
| branch, push your own branch, open PRs, comment on issues and PRs | in this repository only |
| **close an issue** | against the closure bar in `goals/README.md`. TEAMLEAD retains **reopen**. |
| `git worktree add` | additive; the shared tree does not move |
| `--force-with-lease=<branch>:<sha>` **pinned to a SHA you personally pushed, on your own branch** | to land a rebase that was asked for. Disclose it on the PR. |

⛔ **`--force-with-lease` is granted; bare `-f` is not.** The lease is the whole reason: pinned to
a SHA you pushed, the push *fails* if a peer touched the branch. Bare `-f` cannot fail that way.

⚠ *"I expected the push to be rejected"* is not a reason to reach for `-f`. Establish that a force
is needed first — `git push` rejecting non-fast-forward, `git merge-base --is-ancestor` returning
false — as one role did, before using the leased form.

## ⛔ NOT reserved, and recorded because it was wrongly believed to be

**Issue closure.** Measured 2026-08-19 across all four goal files, `goals/README.md`,
`prompts/TEAMLEAD.md` and `prompts/DEV.md`: **zero** closure reservations. `TEAMLEAD.md` §7 says
*"close confidently, but remain correctable"* — a grant, not a withholding. TEAMLEAD asserted the
reservation in a single message to a single pane; that pane complied and closed nothing, while a
pane that never received it followed rung 2 and closed correctly.

⇒ **The asymmetry selects against the compliant agent**: under an unwritten reservation, obedience
is indistinguishable from underperformance.

---

## ⚠ What this document does NOT establish

- **That any of it binds.** Measured 2026-08-19: a role broke *"force-push or history rewrite on
  any branch"* — a rule that was durable, delivered, in that role's own goal file, re-read hours
  earlier, and authored by that role — inside the same shell invocation that committed a clause
  about not self-granting reserved actions. **Delivery is necessary and not sufficient.**
- **That the list is complete.** It is what has been stated or measured, not what has been
  reasoned through. An action absent here is unclassified, not permitted.
- **That copies elsewhere agree.** `#48` records that `CLAUDE.md` and `docs/` sit outside
  `CODEOWNERS`, so nothing gates a divergent copy appearing there.

## Amending

Reserved actions are TEAMLEAD's to state (`TEAMLEAD.md` §19). `goals/` is `CODEOWNERS`-gated to
the operator, so an amendment is a PR the operator reviews — which is the mechanical form of *a
bound the bounded agent can renew is not a bound.*
