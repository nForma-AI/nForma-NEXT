import ast, subprocess, os, collections
REPO="/Users/jonathanborduas/code/DigitalFrontier-infra"
SNAP="snap2"; os.makedirs(SNAP, exist_ok=True)
files=[f for f in subprocess.run(["git","ls-tree","-r","origin/main","--name-only"],
       capture_output=True,text=True,cwd=REPO).stdout.split("\n")
       if f.endswith(".py") and (f.startswith("e2e/") or f.startswith("tests/"))]
def snap(p):
    o=os.path.join(SNAP,p.replace("/","__"))
    if not os.path.exists(o):
        r=subprocess.run(["git","show",f"origin/main:{p}"],capture_output=True,text=True,cwd=REPO)
        if r.returncode: return None
        open(o,"w").write(r.stdout)
    return open(o).read()

rows=[]
for f in files:
    s=snap(f)
    if s is None or "poll_until" not in s: continue
    try: tree=ast.parse(s)
    except SyntaxError: continue
    parent={}
    for n in ast.walk(tree):
        for c in ast.iter_child_nodes(n): parent[c]=n
    for call in [n for n in ast.walk(tree)
                 if isinstance(n,ast.Call) and (
                    (isinstance(n.func,ast.Name) and n.func.id=="poll_until") or
                    (isinstance(n.func,ast.Attribute) and n.func.attr=="poll_until"))]:
        p=parent.get(call)
        desc=""
        for kw in call.keywords:
            if kw.arg=="description" and isinstance(kw.value,ast.Constant):
                desc=str(kw.value.value)[:52]
        if isinstance(p, ast.Expr):
            rows.append((f, call.lineno, "RETURN DISCARDED", desc))
        elif isinstance(p, ast.Assign):
            names=[t.id for t in p.targets if isinstance(t,ast.Name)]
            # is the assigned name ever READ afterwards in this file?
            read=False
            for n2 in ast.walk(tree):
                if isinstance(n2,ast.Name) and n2.id in names and isinstance(n2.ctx,ast.Load):
                    read=True; break
            rows.append((f, call.lineno, "assigned+read" if read else "ASSIGNED NEVER READ", desc))
        elif isinstance(p,(ast.Assert,ast.If,ast.UnaryOp,ast.BoolOp,ast.Compare,ast.Return)):
            rows.append((f, call.lineno, "used inline", desc))
        else:
            rows.append((f, call.lineno, f"other({type(p).__name__})", desc))

c=collections.Counter(r[2] for r in rows)
print(f"poll_until call sites on origin/main (e2e/ + tests/): {len(rows)}\n")
for k,v in sorted(c.items(), key=lambda x:-x[1]): print(f"  {v:>3}  {k}")
print("\n── sites whose result nobody reads ──")
for f,l,v,d in rows:
    if v in ("RETURN DISCARDED","ASSIGNED NEVER READ"):
        print(f"  {f}:{l}\n        {v}   description={d!r}")
