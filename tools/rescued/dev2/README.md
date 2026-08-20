# Rescued from `/tmp` — DEV2's discriminator and CI datasets

⛔ **Two of these are already load-bearing for another role**, which is the same shape as
ARCHITECT's rescue one directory over: not merely an uncommitted tool, but **an uncommitted tool
whose output has been promoted to a shared fact.**

From DEV2's prompt-vs-practice answer (#184):

> *"DEV5 built on `disc.py`'s result and I implemented their counter-proposal as `arms.py`; both
> are in `/tmp` on one machine. `probe_indist.py` produced the correction that **#1238 now rests
> on**, and nobody can re-run it."*

| file | what it answers |
|---|---|
| `disc.py` | AST — *is the discriminator in scope at this return?* |
| `arms.py` | *N arms converging on ONE sentinel* — DEV5's proposed metric, implemented by DEV2 |
| `probe_indist.py` | drives `exec_command`'s error paths; **produced the #1238 correction** |
| `render.py` | byte-identity check of one function's output across worktrees |
| `legs.tsv` · `allc0.tsv` · `c0sig.tsv` | 32 KB of derived CI datasets — run id, timestamp, branch, leg, result |

## ⚠ Verbatim, unrepaired, unindexed — see `../architect/README.md`

`cmp`-verified byte-identical. Not in `tools/README.md`, not in the CI gate: **evidence for
numbers already in circulation, not instruments this repository maintains.**

Secret-scanned. Every hit is a **function or file name** — `validate_api_key`,
`secret_injection_audit.py` — never a value. The `.tsv` files contain CI run metadata only.

## ⛔ The instrument that could NOT be rescued, and it is the one DEV2 nominated

> *"`run_mut`, my mutation harness with apply-verification — **REDEFINED FROM SCRATCH IN THREE
> SEPARATE TURNS today.**"*

It was never written to a file. ⇒ **It exists only as text in a transcript, and DEV2 rebuilt it
three times in one day because of that.** Its own failure mode is the argument for committing it:

> *"Today my `run_mut` harness got its own arguments wrong and printed `NOT APPLIED (71 matches)`
> three times instead of three false survivals. Without the apply-check I would have concluded a
> guard was strong when it had never been tested."*

★ DEV2's nomination, unprompted: *"If you want one of these committed I would start with
`run_mut`: it is the one I rebuilt three times, the one I got wrong, and the one whose absence
produces **false confidence** rather than a visible error."*

## ★ And one instrument that was named but never existed at all

`~/.claude/goals/dev-implementation.md` cited **`ci_guard_closing_keywords.py`** as the mechanism
enforcing a rule TEAMLEAD enforces. Verified independently: **0 tracked files matching
`closing.?keyword` in either repository.** DEV2 found it and corrected the doc the same day.

⇒ That is `tools/named-referent-check.py`'s defect class — *a named enforcement mechanism with no
referent* — occurring in a **goal file** rather than in code, where that tool cannot see it.

Rescued by DX, 2026-08-20, from session `e4a7769d`.
