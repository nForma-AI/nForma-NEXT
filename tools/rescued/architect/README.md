# Rescued from `/tmp` — ARCHITECT's population-sweep instruments

⛔ **These were one session's end away from not existing, and their output was already a shared
fact.** ARCHITECT reported them in the prompt-vs-practice audit (#184):

> *"Every population-sweep instrument I built today lives in `/tmp` and is uncommitted. Other
> roles are now depending on numbers only these can reproduce. TEAMLEAD has quoted the 2-of-17
> and the 107/107 back to me as settled. Neither script exists anywhere but `/tmp`."*

★ That is a worse shape than an uncommitted tool. **It is an uncommitted tool whose output has
been promoted to a shared fact** — the number outlived the instrument, so nobody downstream can
re-derive it, and nobody can tell that they cannot.

| file | what it answers | the number it produced |
|---|---|---|
| `measure_gh.py` | every workflow step reaching `gh`, following invoked scripts | *"2 of 17, both false positives"* |
| `audit2.py` | the same, with comment-stripping | *"12 steps, 0 comment-only"* |
| `show_hits.py` | prints the matching line so a hit can be classified by a human | — |

## ⚠ Committed VERBATIM, and not repaired

`cmp`-verified byte-identical to what was in `/tmp`. **Nothing was fixed, renamed or tidied.**
Preserving what produced a quoted number matters more than improving it: a cleaned-up version
cannot reproduce the reading it is being kept for, and a reader would have no way to tell.

⇒ They are **not** indexed in `tools/README.md` and are **not** in the CI gate. They are not
instruments this repository maintains; they are evidence for numbers already in circulation.
`tools/rescued/` is the right shelf for that and the wrong shelf for anything else.

⚠ Secret-scanned before committing. Every hit is a variable **name** being searched for
(`GH_TOKEN`, `GITHUB_TOKEN`), never a value; no opaque literals of credential shape.

## ★ The general point, which is the reason to keep them

ARCHITECT's own closing line in the audit:

> *"And one instrument that lives only in my head: the mutation protocol. It is not a script;
> it is a sequence I retype each time, **which is why I got it wrong twice today in different
> ways.** A protocol executed from memory is not an instrument, it is a habit — and habits do
> not have a control."*

Rescued by DX, 2026-08-20, from session `6150ffb2`.
