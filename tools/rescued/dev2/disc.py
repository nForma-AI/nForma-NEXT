"""For each sentinel-return site: was the discriminating value IN SCOPE and discarded?

Classification by the innermost enclosing construct:
  except-handler -> the exception object names the case (present, discarded)
  if/elif branch -> the condition just evaluated names the case (present, discarded)
  bare/fallthrough -> nothing local distinguishes it (genuinely absent at the site)
"""
import ast, sys, io

TARGETS = [
    ("control-plane/api/auth.py", "validate_api_key", (None,)),
    ("control-plane/api/services/firestore_queue_backend.py", "verify_receipt_handle", (None,)),
    ("control-plane/api/services/consul_peering.py", "establish_peering", (False,)),
]

def sentinel(node, vals):
    if not isinstance(node, ast.Return) or node.value is None:
        return False
    v = node.value
    return isinstance(v, ast.Constant) and any(v.value is t for t in vals)

for path, fname, vals in TARGETS:
    try:
        tree = ast.parse(io.open(path, encoding="utf-8").read())
    except OSError as e:
        print(f"{path}: {e}"); continue
    fn = next((n for n in ast.walk(tree)
               if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == fname), None)
    if fn is None:
        print(f"{path}::{fname}  NOT FOUND"); continue

    # innermost enclosing construct per return node
    parent = {}
    for n in ast.walk(fn):
        for c in ast.iter_child_nodes(n):
            parent[id(c)] = n
    rows = []
    for n in ast.walk(fn):
        if not sentinel(n, vals):
            continue
        kind, detail = "bare/fallthrough", ""
        cur = n
        while id(cur) in parent:
            p = parent[id(cur)]
            if isinstance(p, ast.ExceptHandler) and cur in p.body:
                kind = "except-handler"
                detail = ("as " + p.name) if p.name else "(exception NOT bound)"
                break
            if isinstance(p, ast.If) and (cur in p.body or cur in p.orelse):
                kind = "if-branch"
                try: detail = ast.unparse(p.test)[:56]
                except Exception: detail = ""
                break
            if isinstance(p, (ast.FunctionDef, ast.AsyncFunctionDef)):
                break
            cur = p
        rows.append((n.lineno, kind, detail))
    print(f"\n=== {path}::{fname}  — {len(rows)} sentinel returns ===")
    for ln, k, d in sorted(rows):
        print(f"  :{ln:<6} {k:<17} {d}")
    present = sum(1 for _, k, _ in rows if k != "bare/fallthrough")
    print(f"  ⇒ discriminator IN SCOPE at {present}/{len(rows)} sites")
