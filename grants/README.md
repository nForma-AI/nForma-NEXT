# `grants/` — where an ad-hoc authorization lives so a message does not have to carry it

> ⛔ **No rules live in this directory. These are RECORDS.**
>
> The rule that *requires* a grant lives in `prompts/TEAMLEAD.md`. Doctrine about **standing**
> authority lives in `goals/`. If you find yourself writing *always* or *never* in a file here,
> it belongs in one of those two. This directory answers exactly one question, mechanically:
>
> **"Is `<role>` authorized to do `<capability>` in `<repo>` right now?"**

## Why it exists

`prompts/TEAMLEAD.md:474` established that a goal must live in a file and the channel may carry
only a pointer, because *"a forged pointer can only reference a file that must exist."* That
solved **standing** authority and stopped there.

Every **ad-hoc** grant — `authorized, one run`, `push it`, `GRANTED: branch, push, PR` — remained
bearer text in an unauthenticatable channel. Measured consequence: forged grants converged on
TEAMLEAD's phrasing, and **one of them matched a real ruling**, because the real ones and the
forged ones were the same kind of object. Nothing existed for a careful agent to check, so care
did not help. See #3.

⇒ This directory is the artifact the redemption test redeems against:

> **Does this instruction's authority survive the deletion of the message that delivered it?**

A grant recorded here survives. A grant that exists only in a message does not.

## ⛔ The two stores are disjoint, and the schema enforces it

| | `goals/` | `grants/` |
|---|---|---|
| holds | **standing** authority — the role's durable desired state | **ad-hoc, expiring** authority |
| expiry | none; standing until redirected | ⛔ **`expires-at` is REQUIRED and has no `never` value** |
| written by | DX owns the standard; the role proposes | TEAMLEAD only |
| contains | doctrine and rationale | records, and nothing else |

★ **A grant with no expiry is a standing grant, and standing grants belong in `goals/`.** That is
why the schema cannot express one. TEAMLEAD's constraint — *"a file that only accumulates becomes
a standing grant nobody decided to make"* — is enforced by the format rather than by memory.

## The record

One file per grant: `grants/<granted-at-compact>-<grantee>-<capability>.md`. One file per grant
rather than a shared ledger, so two grants written in the same minute do not conflict.

```yaml
---
id:          20260819T2000Z-DEV3-pr-create   # MUST equal the filename stem
grantee:     DEV3                            # a ROLE, never a session or an agent — see #4
capability:  pr-create                       # from the closed vocabulary below; exactly one
scope:       nForma-AI/nForma-NEXT           # matched against `git remote get-url origin`
granted-by:  TEAMLEAD
granted-at:  2026-08-19T20:00:00Z            # UTC, RFC3339, Z only
expires-at:  2026-08-20T00:00:00Z            # ⛔ REQUIRED. No `never`. No default.
uses:        1                               # a positive integer, or `unlimited-until-expiry`
revoked-at:                                  # empty = live. A timestamp = revoked.
evidence:    https://github.com/nForma-AI/nForma-NEXT/issues/3#issuecomment-5347295690
---

Free prose below the frontmatter: why this was granted, and what it is for. Read by humans,
ignored by `tools/grant-check.py`. ⚠ Prose here is EVIDENCE, never terms — anything that changes
what is authorized must be a field, or it is not enforceable and not checkable.
```

### Closed capability vocabulary

Exactly the reserved list this fleet already operates under. **The vocabulary is closed on
purpose**: an open one re-admits the prose ambiguity the directory exists to remove.

| capability | covers |
|---|---|
| `merge` | merging any PR, any branch |
| `ci-run` | `gh run`, and any deliberate CI spend |
| `push-pr-branch` | `git push` to a PR branch — **this is CI spend** |
| `pr-create` | `gh pr create` — **also CI spend** |
| `force-push` | `git push --force` anywhere |
| `push-main` | pushing directly to the default branch |
| `cross-repo` | any mutation outside `scope` |

⇒ A grant carries **exactly one** capability. Two capabilities are two records. This is deliberate:
`GRANTED: branch, push, PR, comment` is precisely the bundled form that made forgeries cheap, and a
bundle cannot be revoked in part.

## ⛔ Revocation is an edit, never a deletion

Set `revoked-at`. Do not delete the file.

A deleted grant is **indistinguishable from a grant that never existed**, which destroys the audit
in exactly the direction that matters — the reader cannot tell *withdrawn* from *never issued*. This
is the same reasoning as the `DROPPED` state in `goals/README.md`: the removal is the part a reader
must be able to check.

## How it is read

`tools/grant-check.py`. Two properties are load-bearing and neither is optional:

1. ⛔ **It reads `origin/main`, after fetching — never the working tree.** An agent controls its own
   checkout. If redemption read the local tree, an agent could resurrect an expired or revoked grant
   by checking out an older commit — **self-renewal by another route**, which is the failure thesis
   §7 exists to prevent. A bound the bounded agent can raise is not a bound.
2. ⛔ **It exits `2` when it establishes nothing**, per `tools/README.md`'s convention. *No live
   grant* and *I could not reach the grant store* are different answers, and collapsing them turns a
   network failure into a refusal — or worse, into a pass.

```
grant-check.py --grantee DEV3 --capability merge
    0  a live grant exists   (it is printed)
    1  no live grant         — the answer is NO, established
    2  established nothing   — ⛔ never read as either answer
    3  the self-test failed  — the checker itself is broken
```

## ⚠ What this does NOT do

- **It does not enforce.** Nothing here refuses an action. A control that fires before real grants
  are recorded fires on *all* traffic and gets ignored into decoration — #26's failure arriving by a
  different route. Enforcement is sequenced **after** this store carries the live grants.
- **It does not attribute to an agent.** `grantee` is a role. Under one shared credential (#4) the
  substrate cannot say *which* agent acted, and this directory does not pretend otherwise. It bounds
  **what** was authorized, which is what authority needs; **who typed it** is #4's problem.
- **It does not authenticate the writer.** It relies on `CODEOWNERS` and git provenance — authored,
  diffable, attributable, reviewable. That is a review control, not a cryptographic one. An attacker
  who can commit to `main` can write a grant, and no field here would stop them.
- **It does not verify the clock.** Expiry is evaluated against the reader's system clock, which the
  reader controls. This defends against **fabricated text**, which is the threat in #3 — it does not
  defend against a malicious agent, which is a different threat with a different remedy.
