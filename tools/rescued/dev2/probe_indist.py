"""EXECUTE the #1238 claim: are :272 (ConnectionClosed) and :279 (no RESULT) distinguishable?"""
import asyncio, logging, io, sys, contextlib
sys.path.insert(0, "control-plane"); sys.path.insert(0, "control-plane/api")
import websockets, websockets.exceptions
from api.services import provider_shell_client as psc

class FakeWS:
    def __init__(self, behaviour): self.b = behaviour; self.n = 0
    async def send(self, *a, **k): pass
    async def recv(self):
        self.n += 1
        if self.b == "closed":
            raise websockets.exceptions.ConnectionClosed(None, None)
        if self.b == "no_result":
            # stream ends cleanly: STDOUT frame then a graceful generator stop
            raise StopAsyncIteration
        raise AssertionError(self.b)

class FakeConnect:
    def __init__(self, behaviour): self.b = behaviour
    def __call__(self, *a, **k): return self
    async def __aenter__(self): return FakeWS(self.b)
    async def __aexit__(self, *a): return False

async def run(behaviour):
    orig = psc.websockets.connect
    psc.websockets.connect = FakeConnect(behaviour)
    buf = io.StringIO(); h = logging.StreamHandler(buf)
    lg = logging.getLogger(psc.__name__); lg.addHandler(h); lg.setLevel(logging.DEBUG)
    try:
        c = psc.ProviderShellClient("provider.example:8443")
        r = await c.exec_command(dseq="1", service_name="app", command="kill -9 1", timeout=30)
    finally:
        psc.websockets.connect = orig; lg.removeHandler(h)
    logs = [l for l in buf.getvalue().split("\n") if l.strip() and "Connecting to provider" not in l]
    return r, logs

async def main():
    out = {}
    for b in ("closed", "no_result"):
        try:
            r, logs = await run(b)
            out[b] = (r.exit_code, repr(r.stderr), repr(r.stdout), r.success, logs)
        except Exception as e:
            out[b] = ("RAISED", type(e).__name__, str(e)[:80], None, [])
    for b, v in out.items():
        print(f"{b:<10} exit_code={v[0]}  stderr={v[1]}  stdout={v[2]}  success={v[3]}")
        print(f"           logs beyond 'Connecting': {v[4]}")
    a, c = out["closed"], out["no_result"]
    same = a[:4] == c[:4] and a[4] == c[4]
    print(f"\n⇒ INDISTINGUISHABLE in return value + logs? {same}")

asyncio.run(main())
