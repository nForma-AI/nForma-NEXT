"""DEV5's extension, measured: N distinct ARMS converging on ONE sentinel value.

My original test asked "is a NAME in scope at the site?" — it cannot see a discriminator
that is carried by WHICH BRANCH RAN, because there is no name to find. This counts arms
instead, and classifies the channel each arm's information travelled on.
"""
import ast, io, sys

TARGETS = [
    ("control-plane/api/auth.py", "validate_api_key"),
    ("control-plane/api/services/firestore_queue_backend.py", "verify_receipt_handle"),
    ("control-plane/api/services/consul_peering.py", "establish_peering"),
    ("control-plane/api/services/secret_injection_audit.py", "_check_presence_akash"),
    ("control-plane/api/services/secret_injection_audit.py", "_check_presence_console_api"),
]

def const_ret(n):
    return isinstance(n, ast.Return) and isinstance(n.value, ast.Constant)

for path, fname in TARGETS:
    try:
        tree = ast.parse(io.open(path, encoding="utf-8").read())
    except OSError as e:
        print(f"{path}: {e}"); continue
    fn = next((n for n in ast.walk(tree)
               if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == fname), None)
    if fn is None:
        print(f"!! {path}::{fname} NOT FOUND"); continue

    parent = {}
    for n in ast.walk(fn):
        for c in ast.iter_child_nodes(n):
            parent[id(c)] = n

    buckets = {}
    for n in ast.walk(fn):
        if not const_ret(n):
            continue
        chan, arm = "none (fallthrough)", ""
        cur = n
        while id(cur) in parent:
            p = parent[id(cur)]
            if isinstance(p, ast.ExceptHandler) and cur in p.body:
                try: exc = ast.unparse(p.type) if p.type else "BareExcept"
                except Exception: exc = "?"
                chan = "bound name" if p.name else "BRANCH IDENTITY ONLY"
                arm = f"except {exc}"
                break
            if isinstance(p, ast.If) and (cur in p.body or cur in p.orelse):
                chan = "bound name"
                try: arm = "if " + ast.unparse(p.test)[:44]
                except Exception: arm = "if ?"
                break
            if isinstance(p, (ast.FunctionDef, ast.AsyncFunctionDef)):
                break
            cur = p
        buckets.setdefault(repr(n.value.value), []).append((n.lineno, chan, arm))

    print(f"\n=== {fname}  ({path.split('/')[-1]}) ===")
    for val, arms in sorted(buckets.items()):
        unnamed = sum(1 for _, c, _ in arms if c != "bound name")
        print(f"  {len(arms)} arms -> {val}      ({unnamed} carry NO name)")
        for ln, c, a in sorted(arms):
            print(f"      :{ln:<6} {c:<22} {a}")
