# ARCHITECT sweeps — the inline measurements, made reproducible

⛔ **Why these are files.** Every figure below was produced by an **inline heredoc** during
session `c83ecf77` and quoted into a durable artifact. The artifact survived; the code did not.
A number in a durable artifact whose instrument lives only in a transcript is **a citation to a
pane that may be gone** — which is `goals/README.md`'s rule about instruments outside version
control, applied to a measurement rather than to a tool.

⚠ **These are sweeps, not instruments.** They answer a question once and print what they did not
establish. None is a control, none has a known-negative, and they are deliberately **not** in
`tools/` — that directory's rows carry the incident that produced them and a proven failure path.
These carry neither. `scripts/check-tools-index.py` indexes `tools/*.py`; this directory is
outside its population by construction and should stay there.

## Provenance — which figure came from which script

| figure I reported | where I quoted it | script |
|---|---|---|
| *"7 distinct versions of `prompts/ARCHITECT.md`, 0 mutually-contained pairs"* | #29, and `tools/doctrine-version.py`'s docstring | `doctrine-discriminability.py` |
| *"`per_page=150` → 100 returned, silently capped"* | #142 | `list-truncation-probe.py` |
| *"`gh pr list --limit 200` → 131, true total 131 — does NOT cap"* | #186 | `list-truncation-probe.py` |
| *"118 PRs"* / *"131 PRs"* | #142, #186 | `list-truncation-probe.py` |

⛔ **Re-run before citing any of them.** Both moved between authoring and committing, in one hour:

```
prompts/ARCHITECT.md versions    7  ->  9
PRs                            118  -> 131 -> 135
```

★ That is the reason to commit a sweep rather than its output. **A number decays; the thing that
regenerates it does not** — and four observers produced four different PR counts in one hour
because each held a number and none held the query.

## What is NOT here

- ⛔ **The activity-burst analysis** (5 bursts, gaps of 49/4/72/72 minutes — the evidence that a
  depth monitor measures *invocation*, not idleness) reads a session transcript by path. It is
  omitted deliberately: a committed script that walks `~/.claude/projects` invites being pointed
  at another pane's transcript, and *whether one role may read another's transcript* is not mine
  to settle by committing a convenience. The finding is in #177; the code is not.
- **The `Held by:` census and the queue-criteria census** were three-line loops over files already
  in this repo. Anyone can rewrite them from the finding; committing them adds nothing but a row.
