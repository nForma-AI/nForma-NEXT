#!/usr/bin/env python3
"""Validate an in-repo Daintree recipe before trusting it.

Daintree's in-repo recipe loader is quietly lossy: its normalizer returns a
fixed field set, so several schema-valid fields are silently discarded and
several malformed ones silently drop the whole pane. A recipe can therefore be
100% valid JSON, load without a single error, and still not do what it says.

This script distinguishes the two failure modes that matter:

    ERR   the pane (or recipe) is rejected outright
    WARN  the field is accepted, then silently dropped

Rules transcribed from Daintree's bundled loader/normalizer, not from docs.

Usage:  python3 scripts/validate-recipe.py [path ...]
Exit:   0 clean, 1 errors found
"""
import glob
import json
import re
import shlex
import sys

AGENT_TYPES = {
    "claude", "opencode", "aider", "gemini", "antigravity", "codex", "grok",
    "cursor", "copilot", "goose", "amp", "crush", "qwen", "kimi", "interpreter",
    "mistral", "kiro", "daintree-assistant",
}
PANE_TYPES = {"terminal", "dev-preview"} | AGENT_TYPES
EXIT_BEHAVIORS = {"keep", "trash", "remove"}      # "restart" is schema-valid but rejected
MAX_TERMINALS = 10

SINGLE_LINE = re.compile(r"[\r\n\x00-\x1F]")                    # command / args / devCommand / env
PROMPT_BAD = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")    # initialPrompt (allows \t \n \r)

DROPPED_BY_NORMALIZER = ("agentModelId", "agentLaunchFlags", "location")


def validate(path):
    errs, warns = [], []
    try:
        recipe = json.load(open(path))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"{path}: unreadable or invalid JSON: {exc}"], [], None

    for field in ("id", "name"):
        if not isinstance(recipe.get(field), str) or not recipe[field]:
            errs.append(f"{field} must be a non-empty string")
    if not isinstance(recipe.get("createdAt"), (int, float)):
        warns.append("createdAt missing/non-numeric — loader coerces it to 0, sorting the recipe last")
    if recipe.get("scope") not in (None, "inrepo"):
        errs.append('scope must be "inrepo" for an in-repo recipe')

    panes = recipe.get("terminals")
    if not isinstance(panes, list) or not panes:
        errs.append("terminals must be a non-empty array")
        return errs, warns, recipe
    if len(panes) > MAX_TERMINALS:
        errs.append(f"{len(panes)} panes exceeds the cap of {MAX_TERMINALS} — the excess is truncated")

    for i, pane in enumerate(panes):
        tag = f"pane[{i}] {pane.get('title', '<untitled>')}"
        ptype = pane.get("type")
        if ptype not in PANE_TYPES:
            errs.append(f"{tag}: type {ptype!r} is not a known pane type")
            continue
        is_agent = ptype in AGENT_TYPES

        for field in ("command", "args", "devCommand"):
            if field in pane and (not isinstance(pane[field], str) or SINGLE_LINE.search(pane[field])):
                errs.append(f"{tag}: {field} must be a single-line string")

        if "command" in pane and ptype != "terminal":
            warns.append(f'{tag}: command DROPPED (kept only for type "terminal")')
        if "args" in pane and not is_agent:
            warns.append(f"{tag}: args DROPPED (kept only for agent types)")
        if "devCommand" in pane and ptype != "dev-preview":
            warns.append(f'{tag}: devCommand DROPPED (kept only for type "dev-preview")')

        if "initialPrompt" in pane:
            prompt = pane["initialPrompt"]
            if not isinstance(prompt, str) or PROMPT_BAD.search(prompt):
                errs.append(f"{tag}: initialPrompt contains forbidden control characters")
            elif not is_agent:
                warns.append(f"{tag}: initialPrompt DROPPED (kept only for agent types)")
            elif "\n" in prompt:
                warns.append(f"{tag}: initialPrompt is multi-line — newlines collapse to spaces "
                             f"before it is passed as argv; write it to read as one line")

        if "exitBehavior" in pane and pane["exitBehavior"] not in EXIT_BEHAVIORS:
            errs.append(f"{tag}: exitBehavior {pane['exitBehavior']!r} is rejected by the normalizer "
                        f"(valid: {', '.join(sorted(EXIT_BEHAVIORS))})")

        for key, value in (pane.get("env") or {}).items():
            if not isinstance(value, str) or SINGLE_LINE.search(key) or SINGLE_LINE.search(value):
                errs.append(f"{tag}: env[{key!r}] must be a single-line string — one bad entry "
                            f"drops the ENTIRE pane")

        for field in DROPPED_BY_NORMALIZER:
            if field in pane:
                warns.append(f"{tag}: {field} DROPPED by the normalizer (schema-valid, then discarded)")

    return errs, warns, recipe


def report(path):
    errs, warns, recipe = validate(path)
    print(f"\n\033[1m{path}\033[0m")
    if recipe and isinstance(recipe.get("terminals"), list):
        panes = recipe["terminals"]
        print(f"  {len(panes)}/{MAX_TERMINALS} panes: "
              f"{', '.join(p.get('title', '?') for p in panes)}")
        for pane in panes:
            if pane.get("type") in AGENT_TYPES and isinstance(pane.get("initialPrompt"), str):
                flat = pane["initialPrompt"].replace("\r\n", " ").replace("\n", " ")
                argv = f"{pane['type']} {shlex.quote(flat)}"
                print(f"    {pane.get('title', '?'):<12} argv {len(argv):>5} chars")
    for w in warns:
        print(f"  \033[33mWARN\033[0m  {w}")
    for e in errs:
        print(f"  \033[31mERR \033[0m  {e}")
    if not errs and not warns:
        print("  \033[32mclean\033[0m")
    return len(errs)


def main(argv):
    paths = argv[1:] or sorted(glob.glob(".daintree/recipes/*.json"))
    if not paths:
        print("no recipes found under .daintree/recipes/", file=sys.stderr)
        return 1
    return 1 if sum(report(p) for p in paths) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
