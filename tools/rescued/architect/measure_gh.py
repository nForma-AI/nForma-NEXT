import re, sys, yaml
from pathlib import Path
REPO = Path(".").resolve()
_GH_SHELL = re.compile(r"(?:^|[\s;&|(`$])gh\s+[a-z]", re.MULTILINE)
_GH_ARGV  = re.compile(r"""[\[(]\s*["']gh["']\s*,""")
_SCRIPT   = re.compile(r"(?:python3?|bash|sh)\s+(?:-\S+\s+)*([\w./-]+\.(?:py|sh))")
def calls(t): return bool(_GH_SHELL.search(t) or _GH_ARGV.search(t))
def tok(wf, job, step):
    for s in (wf.get("env") or {}, job.get("env") or {}, step.get("env") or {}):
        if "GH_TOKEN" in s or "GITHUB_TOKEN" in s: return True
    return False

print("=== (A) OTHER workflows: steps reaching gh WITHOUT a token ===")
n_other = 0; n_other_ok = 0
for wfp in sorted(Path(".github/workflows").glob("*.yml")):
    if wfp.name == "ci-pr.yml": continue
    try: wf = yaml.safe_load(wfp.read_text()) or {}
    except Exception as e:
        print(f"  !! {wfp.name}: unparseable {e}"); continue
    if not isinstance(wf, dict): continue
    for jn, job in (wf.get("jobs") or {}).items():
        if not isinstance(job, dict): continue
        for st in job.get("steps") or []:
            if not isinstance(st, dict): continue
            run = st.get("run") or ""
            why = None
            if calls(run): why = "direct"
            else:
                for ref in _SCRIPT.findall(run):
                    p = REPO / ref
                    if p.is_file() and calls(p.read_text()): why = f"via {ref}"; break
            if why:
                if tok(wf, job, st): n_other_ok += 1
                else:
                    n_other += 1
                    print(f"  MISSING  {wfp.name} :: {jn} / {st.get('name') or '<unnamed>'}  ({why})")
print(f"  -> other workflows: {n_other} missing, {n_other_ok} already have a token")

print()
print("=== (B) ci-pr.yml: one-level script following — does any referenced script IMPORT a module that calls gh? ===")
wf = yaml.safe_load(Path(".github/workflows/ci-pr.yml").read_text())
refs = set()
for jn, job in (wf.get("jobs") or {}).items():
    for st in job.get("steps") or []:
        if isinstance(st, dict):
            refs.update(_SCRIPT.findall(st.get("run") or ""))
deeper = 0
for ref in sorted(refs):
    p = REPO / ref
    if not p.is_file() or not ref.endswith(".py"): continue
    txt = p.read_text()
    direct = calls(txt)
    for m in re.finditer(r"^\s*(?:from|import)\s+([\w.]+)", txt, re.M):
        mod = m.group(1).split(".")[0]
        for cand in (REPO/"scripts"/f"{mod}.py", REPO/f"{mod}.py"):
            if cand.is_file() and calls(cand.read_text()):
                deeper += 1
                print(f"  DEPTH-2  {ref} imports {mod} which calls gh (direct={direct})")
print(f"  -> depth-2 gh reachers: {deeper}")
