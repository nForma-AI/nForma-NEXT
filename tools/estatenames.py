#!/usr/bin/env python3
"""The estate predicate, DERIVED from this tree — no list of names to keep current.

⛔ WHY THIS FILE EXISTS. `scripts/check-tools-index.py` and `tools/estate-provenance.py`
both carried the SAME closed list of five estate names. #348 proved by execution that a
SIXTH estate reads clean: a real path, in executable position, in an already-indexed and
already-passing tool, exit 0. The hard half — *mention vs. use*, decided by executable
position — was solved and is not touched here. Only the VOCABULARY moves.

⇒ THE MOVE. Do not ask "is this name one of the estates I know?" Ask "does this string
name an estate that is NOT THIS ONE?" The comparand is read from the tree at run time, so
a fifth, sixth and seventh estate are caught without an edit:

    ~/code/<X>                        <X> != this repo's directory name
    ~/.claude/projects/-Users-…-<X>   slug != this repo's own slug
    github.com/<owner>/<repo>         <repo> != this repo's forge name
    gh -R <owner>/<repo>              same, for the flag form

⚠ WHAT IT CANNOT DO, and this is the proxy test #348 asks. A path-shaped predicate catches
estates that leave PATHS. An estate present only as vendored source — no path, no issue
number, no name — still reads clean here. `w1226.py` was nearly exactly that, identifiable
only because its first line kept a foreign file header. ⇒ Nothing in this module may be
read as "no foreign estate present." It reports what it FOUND, never what is absent, and
the caller's UNCLAIMED state must never collapse into LOCAL on its silence.

⛔ THIS MODULE DOES NOT EXTRACT STRINGS. It takes strings the caller already decided are in
executable position. Feeding it raw file text reintroduces the docstring flood that
`code_strings()` exists to prevent — and this very file would be its loudest false positive,
because it contains estate-shaped examples BECAUSE IT DETECTS THEM.
"""
import os
import re
import subprocess

# ⚠ `~/code/<X>` and `/Users/<who>/code/<X>`. The user segment is a wildcard on purpose:
# hardcoding one operator's home is the same closed-list defect one level down.
CODE_DIR_RE = re.compile(r"(?:~|/Users/[^/\s\"']+|/home/[^/\s\"']+)/code/([A-Za-z0-9._-]+)")
PROJ_SLUG_RE = re.compile(r"\.claude/projects/(-[A-Za-z0-9._-]+)")
FORGE_URL_RE = re.compile(r"github\.com[:/]([A-Za-z0-9._-]+)/([A-Za-z0-9._-]+?)(?:\.git)?(?=[/\s\"']|$)")
# ⚠ The bare `owner/repo` form is accepted ONLY behind an explicit gh flag. Matching it
# anywhere would flag every `control-plane/api`-shaped path fragment in the tree.
FORGE_FLAG_RE = re.compile(r"(?:-R|--repo)[=\s]+([A-Za-z0-9._-]+)/([A-Za-z0-9._-]+)")


def sh(*args):
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=60)
        return p.returncode, p.stdout, p.stderr
    except Exception:                                       # noqa: BLE001
        return 1, "", ""


class Identity:
    """This repository's own names, read from the tree. Never typed in."""

    def __init__(self, repo_dir, slug, forge_repo):
        self.repo_dir = repo_dir
        self.slug = slug
        self.forge_repo = forge_repo

    def complete(self):
        # ⛔ An incomplete identity is ESTABLISHED NOTHING, not "nothing foreign". Without a
        # comparand every string is trivially "not equal to it" — a predicate that would
        # flag the entire tree, or, if written the other way round, clear all of it.
        return all([self.repo_dir, self.slug, self.forge_repo])

    def __repr__(self):
        return f"Identity(repo_dir={self.repo_dir!r}, slug={self.slug!r}, forge_repo={self.forge_repo!r})"


def local_identity(root):
    """Identity for `root`, or an incomplete one. DERIVED — nothing here is a literal."""
    try:
        top = os.path.realpath(root)
    except OSError:
        return Identity(None, None, None)
    rc, out, _ = sh("git", "-C", root, "rev-parse", "--show-toplevel")
    if rc == 0 and out.strip():
        top = os.path.realpath(out.strip())
    repo_dir = os.path.basename(top) or None
    slug = top.replace("/", "-") if top else None
    forge_repo = None
    rc, url, _ = sh("git", "-C", root, "remote", "get-url", "origin")
    if rc == 0:
        m = re.search(r"[:/]([A-Za-z0-9._-]+)/([A-Za-z0-9._-]+?)(?:\.git)?/?\s*$", url.strip())
        if m:
            forge_repo = m.group(2)
    return Identity(repo_dir, slug, forge_repo)


def _same(a, b):
    # macOS is case-insensitive; `nforma-next` and `nForma-NEXT` are one estate, not two.
    return a is not None and b is not None and a.casefold() == b.casefold()


def foreign_in(text, ident):
    """[(kind, matched, estate)] for every foreign-estate reference in ONE code string.

    Empty list means "found none in this string" — NEVER "this string is local".
    """
    if not ident.complete():
        return []
    hits = []
    for name in CODE_DIR_RE.findall(text):
        if not _same(name, ident.repo_dir):
            hits.append(("code-dir", f"~/code/{name}", name))
    for slug in PROJ_SLUG_RE.findall(text):
        if not _same(slug, ident.slug):
            hits.append(("project-slug", slug, slug.rsplit("-", 1)[-1]))
    for owner, repo in FORGE_URL_RE.findall(text) + FORGE_FLAG_RE.findall(text):
        if not _same(repo, ident.forge_repo):
            hits.append(("forge-repo", f"{owner}/{repo}", repo))
    return hits


def scan_strings(strings, ident):
    """Deduplicated hits across many code strings, ordered for a stable report."""
    seen, out = set(), []
    for s in strings:
        for kind, matched, estate in foreign_in(s, ident):
            if (kind, matched) not in seen:
                seen.add((kind, matched))
                out.append((kind, matched, estate))
    return sorted(out)
