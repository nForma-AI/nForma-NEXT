import re, yaml, sys
from pathlib import Path
REPO=Path(".").resolve()
_GH_SHELL = re.compile(r"(?:^|[\s;&|(`$])gh\s+[a-z]", re.MULTILINE)
_GH_ARGV  = re.compile(r"""[\[(]\s*["']gh["']\s*,""")
_SCRIPT   = re.compile(r"(?:python3?|bash|sh)\s+(?:-\S+\s+)*([\w./-]+\.(?:py|sh))")
def calls(t): return bool(_GH_SHELL.search(t) or _GH_ARGV.search(t))
def strip_comments(t):
    return "\n".join("" if l.lstrip().startswith("#") else l for l in t.splitlines())
def scan(path, label):
    try: wf=yaml.safe_load(Path(path).read_text()) or {}
    except Exception as e: print(f"  !! {path}: {e}"); return
    if not isinstance(wf,dict): return
    raw=code=0; missing=[]
    for jn,job in (wf.get("jobs") or {}).items():
        if not isinstance(job,dict): continue
        for st in job.get("steps") or []:
            if not isinstance(st,dict): continue
            run=st.get("run") or ""
            texts=[run]+[ (REPO/r).read_text() for r in _SCRIPT.findall(run) if (REPO/r).is_file() ]
            if not any(calls(t) for t in texts): continue
            raw+=1
            iscode=any(calls(strip_comments(t)) for t in texts)
            if iscode: code+=1
            tok=any("GH_TOKEN" in s or "GITHUB_TOKEN" in s
                    for s in ((wf.get("env") or {}),(job.get("env") or {}),(st.get("env") or {})))
            if not tok: missing.append((jn, st.get("name") or "<unnamed>", "CODE" if iscode else "COMMENT-ONLY"))
    print(f"{label:34s} raw={raw:3d} code={code:3d} comment-only-FP={raw-code:2d} missing-token={len(missing)}")
    for m in missing: print(f"     MISSING [{m[2]}] {m[0]} / {m[1]}")
scan(".github/workflows/ci-pr.yml","ci-pr.yml (WITH fix applied)")
print()
for p in sorted(Path(".github/workflows").glob("*.yml")):
    if p.name!="ci-pr.yml": scan(str(p), p.name)
