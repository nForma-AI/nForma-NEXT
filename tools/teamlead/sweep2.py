import ast, subprocess, collections
REPO="/Users/jonathanborduas/code/DigitalFrontier-infra"
files=[f for f in subprocess.run(["git","ls-tree","-r","origin/main","--name-only"],
       capture_output=True,text=True,cwd=REPO).stdout.split("\n")
       if f.endswith(".py") and "/.venv/" not in f and "node_modules" not in f]
def src(p):
    r=subprocess.run(["git","show",f"origin/main:{p}"],capture_output=True,text=True,cwd=REPO)
    return r.stdout if r.returncode==0 else None

def window_kind(node):
    """Return ('literal'|'name'|'attr'|'call', desc) for X[i : i + N]; None otherwise."""
    if not isinstance(node, ast.Subscript) or not isinstance(node.slice, ast.Slice): return None
    up = node.slice.upper
    if not (isinstance(up, ast.BinOp) and isinstance(up.op, ast.Add)): return None
    r = up.right
    if isinstance(r, ast.Constant) and isinstance(r.value,int): return ("literal", str(r.value))
    if isinstance(r, ast.Name):      return ("name", r.id)
    if isinstance(r, ast.Attribute): return ("attr", ast.unparse(r))
    if isinstance(r, ast.Call):      return ("call", ast.unparse(r)[:40])
    return ("other", ast.unparse(r)[:40])

# ---- bound A: window sizes that are NOT int literals ----
nonlit=[]; lit=0
# ---- bound B: helpers that RETURN a window (consumed elsewhere) ----
helpers=[]
for f in files:
    s=src(f)
    if s is None or "[" not in s: continue
    try: tree=ast.parse(s)
    except SyntaxError: continue
    for fn in [n for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))]:
        returns_window=False
        for n in ast.walk(fn):
            k=window_kind(n)
            if k is None: continue
            if k[0]=="literal": lit+=1
            else: nonlit.append((f,getattr(n,'lineno',0),fn.name,k))
        for n in ast.walk(fn):
            if isinstance(n, ast.Return) and n.value is not None:
                if window_kind(n.value) is not None: returns_window=True
                # also: return <name> where <name> was assigned a window in this fn
                if isinstance(n.value, ast.Name):
                    for a in ast.walk(fn):
                        if isinstance(a, ast.Assign) and window_kind(a.value) is not None:
                            for t in a.targets:
                                if isinstance(t,ast.Name) and t.id==n.value.id: returns_window=True
        if returns_window:
            helpers.append((f, fn.lineno, fn.name))

print("── BOUND A: window sizes that are NOT int literals ──")
print(f"  int-literal windows found : {lit}")
print(f"  NON-literal windows found : {len(nonlit)}")
for f,l,fn,k in nonlit[:20]:
    print(f"    {f}:{l}  {fn[:44]:<46} size={k[0]}:{k[1]}")
if len(nonlit)>20: print(f"    … +{len(nonlit)-20} more")

print("\n── BOUND B: helpers that RETURN a window (invisible to same-function matchers) ──")
print(f"  count: {len(helpers)}")
for f,l,fn in helpers[:20]:
    print(f"    {f}:{l}  {fn}")
