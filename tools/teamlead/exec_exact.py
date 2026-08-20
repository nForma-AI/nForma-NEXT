import ast, subprocess, collections, os
REPO="/Users/jonathanborduas/code/DigitalFrontier-infra"
SNAP="snap"; os.makedirs(SNAP, exist_ok=True)

files=[f for f in subprocess.run(["git","ls-tree","-r","origin/main","--name-only"],
       capture_output=True,text=True,cwd=REPO).stdout.split("\n")
       if f.endswith(".py") and (f.startswith("e2e/") or f.startswith("tests/e2e/"))]

def snapshot(p):
    """Write origin/main:<p> to a temp file and read ONLY from that."""
    out=os.path.join(SNAP,p.replace("/","__"))
    r=subprocess.run(["git","show",f"origin/main:{p}"],capture_output=True,text=True,cwd=REPO)
    if r.returncode: return None
    open(out,"w").write(r.stdout); return r.stdout

def enclosing_fn(tree, node):
    best=None
    for n in ast.walk(tree):
        if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.Lambda)):
            lo=n.lineno; hi=getattr(n,'end_lineno',lo)
            if lo<=node.lineno<=hi and (best is None or lo>best.lineno): best=n
    return best

rows=[]
for f in files:
    s=snapshot(f)
    if s is None or "exec_command" not in s: continue
    try: tree=ast.parse(s)
    except SyntaxError: continue
    parent={}
    for n in ast.walk(tree):
        for c in ast.iter_child_nodes(n): parent[c]=n
    for call in [n for n in ast.walk(tree)
                 if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)
                 and n.func.attr=="exec_command"]:
        # 1. direct chain:  exec_command(...).get("exit_code" | "stdout")
        p=parent.get(call)
        verdict=None
        if isinstance(p,ast.Attribute) and p.attr=="get":
            gp=parent.get(p)
            if isinstance(gp,ast.Call) and gp.args and isinstance(gp.args[0],ast.Constant):
                key=gp.args[0].value
                verdict = "EXIT_CODE ONLY" if key=="exit_code" else ("reads "+str(key))
        # 2. assigned to a name -> what is read off that name in the same scope
        if verdict is None and isinstance(p,ast.Assign):
            names=[t.id for t in p.targets if isinstance(t,ast.Name)]
            tup  =[e.id for t in p.targets if isinstance(t,ast.Tuple) for e in t.elts if isinstance(e,ast.Name)]
            fn=enclosing_fn(tree,call); scope=ast.unparse(fn) if fn else s
            keys=set()
            for nm in names:
                for n2 in ast.walk(ast.parse(scope)):
                    if isinstance(n2,ast.Call) and isinstance(n2.func,ast.Attribute) \
                       and n2.func.attr=="get" and isinstance(n2.func.value,ast.Name) \
                       and n2.func.value.id==nm and n2.args and isinstance(n2.args[0],ast.Constant):
                        keys.add(n2.args[0].value)
                    if isinstance(n2,ast.Subscript) and isinstance(n2.value,ast.Name) \
                       and n2.value.id==nm and isinstance(n2.slice,ast.Constant):
                        keys.add(n2.slice.value)
            if tup: keys.add("tuple-unpack")
            verdict = ("reads " + ",".join(sorted(map(str,keys)))) if keys else "return DISCARDED"
        if verdict is None:
            verdict = "return DISCARDED" if isinstance(p,ast.Expr) else f"other({type(p).__name__})"
        rows.append((f, call.lineno, verdict))

# dedupe by (file,line) — the double-count that inflated the previous pass
seen={}
for f,l,v in rows:
    key=(f,l)
    if key not in seen or len(v)>len(seen[key]): seen[key]=v
print(f"raw call nodes: {len(rows)}   distinct (file,line): {len(seen)}\n")
blind=0
for (f,l),v in sorted(seen.items()):
    mark=""
    if v=="EXIT_CODE ONLY" or v=="return DISCARDED": blind+=1; mark="  <- cannot see a synthetic zero"
    print(f"  {f.split('/')[-1][:46]:<48}:{l:<6} {v}{mark}")
print(f"\n  ⇒ {blind}/{len(seen)} distinct sites are blind to a synthetic exit-0")
