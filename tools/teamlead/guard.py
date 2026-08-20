#!/usr/bin/env python3
"""Reject unintended issue-closing keywords in a PR title, body, or commit subject.

MEASURED INCIDENT
-----------------
#1104 — a HIGH PRIORITY security issue, explicitly marked BLOCKED — was auto-closed by
the merge of #1118 and sat closed for five hours with a wallet mnemonic still mounted in
both production manifests.

    #1118 merged  2026-08-18T20:23:55Z
    #1104 closed  2026-08-18T20:23:57Z   <- two seconds later, commit a7facfc5

The PR BODY carried no keyword. The SQUASH SUBJECT did:

    fix(api): gate the money-moving wallet-pool admin routes fail-{C} (#1104 slice 3b)

`fail-{C}` contains the keyword as the tail of a hyphenated compound, and it is this
repository's house phrase for security hardening — used most often on precisely the PRs
that reference the security issue they are a slice of. The author wrote no directive; the
parser saw one anyway.

⚠ THE TRIGGER IS ADJACENCY, NOT CO-OCCURRENCE — swept across all four merged PRs whose
title contains that phrase, and only ONE closed anything:

    #1118  "...fail-{C} (#1104 slice 3b)"                            -> CLOSED #1104
    #1117  "...fail-{C} - a funding path had no gate at all (#1104)"  -> did NOT close
    #785   "...the fail-{C} gate discarded the evidence..."           -> no reference
    #586   "...(post-boot MODULE LOAD, fail-{C})"                     -> no reference

#1117 has the SAME WORDS and survived, because intervening text separates the keyword
from the reference. A guard flagging every title containing both a keyword and a `#ref`
would flag 2 of 4 and cry wolf on #1117 — and an alert that fires on a by-design state is
a defect in the alert, not a finding.

WHY THE API FIELD IS NOT ENOUGH
-------------------------------
`gh pr view --json closingIssuesReferences` reads `[]` for BOTH #1118 and #1117, even
though #1118 demonstrably closed #1104. That field enumerates issues linked through the
PR form; a closure arriving via the commit subject is invisible to it. It is also blind to
PR targets entirely — #1071 closed PR #1067 while the field read `[]`. So the field is a
useful second oracle and cannot be the only one.

⚠ TOKEN HYGIENE IN THIS FILE
----------------------------
Every keyword above is written with a `{C}` placeholder rather than the live word, and the
fixtures in the test-suite build their strings by concatenation. This is not squeamishness:
a fixture containing the live form is a directive at authoring time and in every future
copy of the file. The incident was reproduced once already by someone quoting the example
verbatim while documenting it. A quotation is not a quotation to the parser.
"""

from __future__ import annotations

import argparse
import re
import sys

# Built by concatenation so this source file never contains a live directive.
_C = "clos"
_F = "fix"
_R = "resolv"
KEYWORDS = [
    _C + "e",
    _C + "es",
    _C + "ed",
    _F,
    _F + "es",
    _F + "ed",
    _R + "e",
    _R + "es",
    _R + "ed",
]

# `\b` before the keyword deliberately matches the tail of a hyphenated compound:
# `-` is a non-word character, so the boundary exists inside `fail-<kw>`. That is the
# whole point — this is the form that neither prose-stripping nor negation-detection sees.
#
# The adjacency window is the measured discriminator. GitHub permits whitespace, a colon,
# and an opening paren between the keyword and the reference; it does NOT bridge a clause.
# Bounded at 3 separator characters, which fires on `<kw> (#1104` and stays quiet on
# `<kw> - a funding path had no gate at all (#1104`.
_ADJACENCY = r"[\s:]{0,2}\(?"
_REF = r"(?:#\d+|GH-\d+|https://github\.com/[\w.-]+/[\w.-]+/(?:issues|pull)/\d+)"
PATTERN = re.compile(
    r"\b(" + "|".join(sorted(KEYWORDS, key=len, reverse=True)) + r")\b" + _ADJACENCY + r"(" + _REF + r")",
    re.IGNORECASE,
)


def find_directives(text: str) -> list[tuple[str, str, str]]:
    """Return (keyword, reference, surrounding context) for each live closing directive."""
    out = []
    for m in PATTERN.finditer(text or ""):
        start, end = max(0, m.start() - 40), min(len(text), m.end() + 20)
        out.append((m.group(1), m.group(2), text[start:end].replace("\n", " ").strip()))
    return out


def scan(title: str = "", body: str = "", commits: list[str] | None = None) -> list[str]:
    """Scan every surface a keyword can fire from. A body-only check is blind to the
    entire title/squash-subject class, which is how #1104 was lost."""
    problems = []
    for label, text in [("title", title), ("body", body)] + [(f"commit[{i}]", c) for i, c in enumerate(commits or [])]:
        for kw, ref, ctx in find_directives(text):
            problems.append(f"{label}: {kw!r} is adjacent to {ref} -> ...{ctx}...")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(prog="ci_guard_closing_keywords")
    ap.add_argument("--title", default="")
    ap.add_argument("--body-file")
    ap.add_argument("--commit", action="append", default=[])
    a = ap.parse_args()
    body = open(a.body_file).read() if a.body_file else ""
    problems = scan(a.title, body, a.commit)
    if not problems:
        print("no unintended closing directives found")
        return 0
    print("UNINTENDED CLOSING DIRECTIVE(S) — these will close issues on merge:", file=sys.stderr)
    for p in problems:
        print(f"  {p}", file=sys.stderr)
    print(
        "\nIf the closure is intended, say so explicitly in review. Otherwise separate the\n"
        "keyword from the reference with intervening text — that is measurably sufficient.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
