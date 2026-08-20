#!/usr/bin/env python3
"""The estate predicate, DERIVED from this tree — no list of names to keep current.

⛔ WHY THIS FILE EXISTS. `scripts/check-tools-index.py` and `tools/estate-provenance.py`
both carried the SAME closed list of five estate names. #348 proved by execution that a
SIXTH estate reads clean: a real path, in executable position, in an already-indexed and
already-passing tool, exit 0. The hard half — *mention vs. use*, decided by executable
position — was solved and is not touched here. Only the VOCABULARY moves.

⚠ The example above is written `<slug>` rather than spelled out: the literal form is the
very thing PROJ_SLUG_RE matches, so a worked example in this docstring made THIS MODULE
report itself. The regex on line ~38 is detection machinery and stays literal; prose does
not have to be. ⇒ The fixture needs the SHAPE, never the OWNER — and a doc example is a
fixture.

⇒ THE MOVE. Do not ask "is this name one of the estates I know?" Ask "does this string
name an estate that is NOT THIS ONE?" The comparand is read from the tree at run time, so
a fifth, sixth and seventh estate are caught without an edit:

    ~/code/<X>                        <X> != this repo's directory name
    ~/.claude/projects/<slug>         slug != this repo's own slug
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
    # ⛔ NOT --show-toplevel. In a worktree that returns the WORKTREE path, so this
    # repo's own name reads as a foreign estate — and nine panes here work in
    # worktrees, which is where the predicate would do the most damage. The common
    # git dir points at the ORIGINAL clone from every linked worktree.
    rc, out, _ = sh("git", "-C", root, "rev-parse", "--path-format=absolute",
                    "--git-common-dir")
    if rc == 0 and out.strip():
        top = os.path.realpath(os.path.dirname(out.strip().rstrip("/")))
    else:
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


FORGE_FLAG_TOKENS = {"-R", "--repo"}


def scan_strings(strings, ident):
    """Deduplicated hits across many code strings, ordered for a stable report.

    ⛔ TAKES THE WHOLE LIST, not one string, because one leg needs ADJACENCY.
    `code_strings()` returns literals individually, so an argv-list call arrives as
    ["gh", "issue", "list", "-R", "Owner/Repo"] — the flag and its value are never in
    the same string, and a per-string regex cannot see the pair. That is the form every
    tool in this repo uses to call gh, so the per-string version missed all of them.
    ⚠ Matching a BARE `owner/repo` in any string is not the alternative: `tools/README.md`
    is exactly that shape, and so is half the tree.
    """
    strings = list(strings)
    # ⛔ `-R` is ALSO grep/cp/ls's recursive flag. Without this gate, a future
    # ["grep", "-R", "docs/README.md"] reads as a foreign forge ref — `owner/repo` and
    # `dir/file` are the same shape. Zero such calls exist today, which is exactly when
    # a latent false positive is cheapest to close.
    is_gh_call = any(t.strip() == "gh" or t.strip().startswith("gh ") for t in strings)
    seen, out = set(), []

    def add(kind, matched, estate):
        if (kind, matched) not in seen:
            seen.add((kind, matched))
            out.append((kind, matched, estate))

    for i, s in enumerate(strings):
        for kind, matched, estate in foreign_in(s, ident):
            add(kind, matched, estate)
        # The adjacency leg: a lone flag token whose NEXT literal is the forge ref.
        if is_gh_call and s.strip() in FORGE_FLAG_TOKENS and i + 1 < len(strings):
            nxt = strings[i + 1].strip()
            m = re.fullmatch(r"([A-Za-z0-9._-]+)/([A-Za-z0-9._-]+)", nxt)
            if m and not _same(m.group(2), ident.forge_repo):
                add("forge-flag", nxt, m.group(2))
    return sorted(out)
