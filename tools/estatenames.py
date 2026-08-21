#!/usr/bin/env python3
# NOT-EXECUTABLE: a shared predicate module (#348), imported by check-tools-index.py and estate-provenance.py. No __main__, no argv surface.
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
# ⛔ `-R` IS ALSO grep/cp/ls's RECURSIVE FLAG, and `owner/repo` is the same shape as
# `dir/file`. Without this, `grep -R docs/README.md` reads as a foreign forge ref.
# ⚠ The guard used to live on the adjacency leg only; removing that leg removed the guard
# while the single-string form kept firing — caught by this module's own known-negative.
GH_CMD_RE = re.compile(r"(?:^|[\s;|&(])gh\s")


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
    flag_pairs = FORGE_FLAG_RE.findall(text) if GH_CMD_RE.search(text) else []
    for owner, repo in FORGE_URL_RE.findall(text) + flag_pairs:
        if not _same(repo, ident.forge_repo):
            hits.append(("forge-repo", f"{owner}/{repo}", repo))
    return hits


def scan_strings(strings, ident):
    """Deduplicated hits across many code strings, ordered for a stable report.

    ⛔ THERE IS NO ADJACENCY LEG, AND ITS ABSENCE IS A STATED GAP RATHER THAN AN OVERSIGHT.
    An earlier version paired a lone `-R` with the NEXT literal to catch
    `gh -R owner/repo` in argv form. It was unsound over anything but one call's argv:
    `code_strings()` collects via `ast.walk`, which is BREADTH-FIRST, so literals from
    unrelated statements sort before a call's own arguments. Measured:

        a = "FIRST"; subprocess.run(["gh","pr","list","-R","owner/repo"]); b = "LAST"
        walk order -> ['FIRST', 'LAST', 'gh', 'pr', 'list', '-R', 'owner/repo']

    ⚠ Adjacency SURVIVES inside one list literal and is scrambled ACROSS statements, which
    is why no window rescues it — the failure is between statements, where no window is
    small enough. (DEVOPS's measurement.)

    ⇒ REMOVED RATHER THAN GATED. DEVOPS measured every estate hit in this repository —
    12 of 12 matched a SINGLE literal — so the leg has never fired for a real detection,
    and a leg that passes by luck is worse than an absent one BECAUSE IT READS AS COVERAGE.
    ⛔ The sound version is not a parameter on this function; it is a different POPULATION —
    the string arguments of one `ast.Call`, collected per call site — and it should be built
    when something needs the argv shape, with its own known-negative.

    ⛔ SO THIS IS AN UNCOVERED SHAPE: a `gh -R foreign/repo` written as an argv LIST is not
    detected. The shell-string form still matches via FORGE_URL_RE. This narrows a claim
    made in #354, where the shape was demonstrated and reported covered; it passed because
    that plant's literals happened to survive walk order.
    """
    seen, out = set(), []
    for s in strings:
        for kind, matched, estate in foreign_in(s, ident):
            if (kind, matched) not in seen:
                seen.add((kind, matched))
                out.append((kind, matched, estate))
    return sorted(out)


def _self_test():
    """Controls for the derived predicate. ⛔ Two-sided, and the negatives are the point."""
    est = "-".join(("fixture", "estate", "not", "an", "owner"))
    pre = "-Users" + "-o" + "-code-"
    ident = Identity("nForma-NEXT", pre + "nForma-NEXT", "nForma-NEXT")
    k = lambda t: sorted({a for a, _, _ in foreign_in(t, ident)})       # noqa: E731
    checks = {
        "code-dir fires": k("p = '/Users/o/code/%s/x'" % est) == ["code-dir"],
        "project-slug fires": k("'~/.claude/projects/%s%s/a'" % (pre, est)) == ["project-slug"],
        "forge-url fires": k("'https://github.com/%s/%s.git'" % (est, est)) == ["forge-repo"],
        # ⛔ THE FLOOD CONTROL. Our own names are the SAME SHAPE; a predicate that reds here
        # matches every path in the tree and is worthless.
        "our code dir is not foreign": k("p = '/Users/o/code/nForma-NEXT/x'") == [],
        "our slug is not foreign": k("'~/.claude/projects/%snForma-NEXT/a'" % pre) == [],
        "case differs, same estate": k("p = '~/code/nforma-next/x'") == [],
        # `tools/README.md` is exactly `X/Y`; matching that shape anywhere floods the tree.
        "bare dir/file is not a repo": k("'tools/README.md'") == [],
        # ⛔ -R is also grep's recursive flag.
        "grep -R is not a forge ref": k("grep -R docs/README.md") == [],
        "gh -R IS a forge ref": k("gh pr list -R %s/%s" % (est, est)) == ["forge-repo"],
        # ⛔ No comparand means ESTABLISHED NOTHING, and the caller must treat it as VOID.
        # ⛔ ASSEMBLED like the rest. A bare literal here felt inert — the identity is
        # incomplete, so no comparison happens — but the SCANNER reading this file is a
        # different reader, and it flagged `~/code/x`. The fixture needs the SHAPE, never
        # the OWNER (docs/ESTATE-BOUNDARY.md), and that holds even where the value is unused.
        "no identity -> no claim": foreign_in("p='/Users/o/code/%s/y'" % est,
                                              Identity(None, None, None)) == [],
        "incomplete is not complete": Identity("a", "b", None).complete() is False,
    }
    for name, ok in checks.items():
        print("  %-4s %s" % ("PASS" if ok else "FAIL", name))
    return 0 if all(checks.values()) else 2


if __name__ == "__main__":
    import sys as _sys
    _args = [a for a in _sys.argv[1:] if a.startswith("-")]
    _unknown = [a for a in _args if a != "--self-test"]
    if _unknown:
        print("⛔ VOID: unrecognised flag(s): %s. Known: --self-test" % ", ".join(_unknown),
              file=_sys.stderr)
        _sys.exit(2)
    if "--self-test" in _args:
        _sys.exit(_self_test())
    # ⚠ Bare run stays silent, exit 0, matching tools/runmarker.py — see codestrings.py.
