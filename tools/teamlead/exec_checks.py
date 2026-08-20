import ast, subprocess, collections
REPO="/Users/jonathanborduas/code/DigitalFrontier-infra"
files=[f for f in subprocess.run(["git","ls-tree","-r","origin/main","--name-only"],
       capture_output=True,text=True,cwd=REPO).stdout.split("\n")
       if f.endswith(".py") and "/.venv/" not in f]
def src(p):
    r=subprocess.run(["git","show",f"origin/main:{p}"],capture_output=True,text=True,cwd=REPO)
    return r.stdout if r.returncode==0 else None

rows=[]
for f in files:
    if not (f.startswith("e2e/") or f.startswith("tests/e2e/")): continue
    s=src(f)
    if s is None or "exec_command" not in s: continue
    try: tree=ast.parse(s)
    except SyntaxError: continue
    for fn in [n for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))]:
        calls=[n for n in ast.walk(fn)
               if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)
               and n.func.attr=="exec_command"]
        if not calls: continue
        body = ast.unparse(fn)
        reads_stdout = '"stdout"' in body or "'stdout'" in body or ".stdout" in body
        reads_exit    = "exit_code" in body
        marker        = "marker=" in body or "require_stdout" in body
        for c in calls:
            argv = None
            for a in c.args:
                if isinstance(a,(ast.List,ast.Tuple)): argv = ast.unparse(a)[:46]
            rows.append(dict(file=f, line=c.lineno, fn=fn.name, argv=argv or "?",
                             exit=reads_exit, stdout=reads_stdout, marker=marker))

def cls(r):
    if r["marker"]: return "MARKER/require_stdout"
    if r["stdout"]: return "reads STDOUT"
    if r["exit"]:   return "EXIT_CODE ONLY  <- mode-B blind"
    return "return DISCARDED  <- mode-B blind"

c=collections.Counter(cls(r) for r in rows)
print(f"exec_command call sites in e2e/ and tests/e2e/: {len(rows)}\n")
for k,v in sorted(c.items(), key=lambda x:-x[1]): print(f"  {v:>3}  {k}")
blind=sum(v for k,v in c.items() if "blind" in k)
print(f"\n  ⇒ {blind}/{len(rows)} = {100*blind/len(rows):.0f}% cannot distinguish a synthetic zero from a real one\n")
for r in rows:
    print(f"  {cls(r)[:22]:<24} {r['file'].split('/')[-1][:44]:<46}:{r['line']:<5} {r['argv']}")
