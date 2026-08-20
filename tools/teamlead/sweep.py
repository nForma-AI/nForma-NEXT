import ast, subprocess, json, sys, collections
REPO="/Users/jonathanborduas/code/DigitalFrontier-infra"

files = subprocess.run(["git","ls-tree","-r","origin/main","--name-only"],
                       capture_output=True,text=True,cwd=REPO).stdout.split("\n")
files = [f for f in files if f.endswith(".py") and "/.venv/" not in f and "node_modules" not in f]

def src(p):
    r=subprocess.run(["git","show",f"origin/main:{p}"],capture_output=True,text=True,cwd=REPO)
    return r.stdout if r.returncode==0 else None

def is_window(node):
    """X[i : i + N] with N an int literal — the fixed-window shape, assigned OR inline."""
    if not isinstance(node, ast.Subscript) or not isinstance(node.slice, ast.Slice):
        return None
    up = node.slice.upper
    if not (isinstance(up, ast.BinOp) and isinstance(up.op, ast.Add)
            and isinstance(up.right, ast.Constant) and isinstance(up.right.value, int)):
        return None
    return up.right.value

rows=[]
for f in files:
    s = src(f)
    if s is None or "[" not in s: continue
    try: tree = ast.parse(s)
    except SyntaxError: continue
    # map: function node -> its windows and its membership asserts
    for fn in [n for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))]:
        wins=[]; neg=[]; pos=[]
        for n in ast.walk(fn):
            w = is_window(n)
            if w is not None:
                wins.append((w, getattr(n,'lineno',0), ast.unparse(n)[:60]))
            if isinstance(n, ast.Assert):
                t=n.test
                if isinstance(t, ast.Compare) and len(t.ops)==1:
                    if isinstance(t.ops[0], ast.NotIn): neg.append(ast.unparse(t)[:80])
                    elif isinstance(t.ops[0], ast.In):  pos.append(ast.unparse(t)[:80])
                # `assert not (x in y)`
                if isinstance(t, ast.UnaryOp) and isinstance(t.op, ast.Not) \
                   and isinstance(t.operand, ast.Compare) and t.operand.ops and isinstance(t.operand.ops[0], ast.In):
                    neg.append(ast.unparse(t)[:80])
        if wins and (neg or pos):
            rows.append(dict(file=f, fn=fn.name, line=fn.lineno, col=fn.col_offset,
                             windows=wins, neg=neg, pos=pos))
json.dump(rows, open("sweep.json","w"), indent=1)

def area(f):
    if f.startswith("e2e/"): return "e2e/  (UNSWEPT by #1243)"
    if f.startswith("compiler/"): return "compiler/  (UNSWEPT by #1243)"
    if f.startswith("control-plane/api/tests/") or f.startswith("tests/"): return "#1243's swept area"
    return "other  (UNSWEPT by #1243)"

by=collections.Counter(area(r["file"]) for r in rows)
print("WINDOW+MEMBERSHIP FUNCTIONS BY AREA")
for k,v in sorted(by.items(), key=lambda x:-x[1]): print(f"  {v:>4}  {k}")
print(f"  {len(rows):>4}  TOTAL\n")

negs=[r for r in rows if r["neg"]]
print(f"WITH >=1 NEGATIVE assertion (the silent-failure shape): {len(negs)}")
print(f"  of those, ZERO-POSITIVE (worst config): {sum(1 for r in negs if not r['pos'])}\n")
for r in negs:
    zp = "  ⛔ ZERO-POSITIVE" if not r["pos"] else ""
    print(f"  {r['file']}:{r['line']}  {r['fn'][:52]}  col={r['col']}  win={[w[0] for w in r['windows']]}{zp}")
    for a in r["neg"][:2]: print(f"        NEG: {a}")
