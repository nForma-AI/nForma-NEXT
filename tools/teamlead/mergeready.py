import json, os, subprocess, sys, time
SP = os.path.dirname(os.path.abspath(__file__))
TL = os.path.join(SP, "nforma-contrib", "tl.py")
STATE = "/tmp/mergeready-seen.txt"
env = dict(os.environ, TL_WORKSPACE=os.environ.get("TL_WORKSPACE", ""))

def emit(s):
    print(s, flush=True)

seen = set(open(STATE).read().split("\n")) if os.path.exists(STATE) else set()
while True:
    p = subprocess.run([sys.executable, TL, "board"], capture_output=True, text=True, env=env, timeout=300)
    if p.returncode != 0:
        emit("BOARD UNREADABLE :: %s" % (p.stderr.strip()[:140] or "unknown"))
        time.sleep(180); continue
    try:
        prs = json.loads(p.stdout)["prs"]
    except Exception as e:
        emit("BOARD PARSE FAILED :: %s: %s" % (type(e).__name__, e)); time.sleep(180); continue
    for r in prs:
        if not r.get("valid"):
            continue
        # MERGE-READY: all required contexts green, nothing failed, no unresolved
        # threads (branch protection requires resolution), not a draft.
        # Non-required failures do not block (GitHub calls that `unstable`).
        # Only required-context failures do. See tl.py::required_failures.
        ready = (r["req_ok"] == r["req_of"] and r["req_of"] > 0
                 and not r.get("required_failures") and r["unresolved"] == 0 and not r["draft"])
        # GUARD: a required context that SKIPPED counts as PASSING in branch protection.
        # `Merge Gate: C/D-Tier Honesty` skips whenever G0 has not yet succeeded, i.e.
        # exactly when the pipeline is unhealthy -- so the honesty gate is bypassed by the
        # condition it exists to catch. req_ok requires `success` so this does not read as
        # ready here, but GitHub WILL show it mergeable. Surface it loudly.
        for sk in r.get("skipped_required", []):
            k = "skipreq:%s:%s:%s" % (r["pr"], r["head"], sk)
            if k not in seen:
                seen.add(k)
                emit("⛔ #%s %s — REQUIRED CONTEXT SKIPPED: %r. GitHub counts a skip as a PASS, "
                     "so this may present as mergeable with that gate never having run. "
                     "DO NOT merge on it." % (r["pr"], r["head"], sk))
        if ready:
            k = "ready:%s:%s" % (r["pr"], r["head"])
            if k not in seen:
                seen.add(k)
                emit("MERGE-READY #%s %s — %s/%s required, 0 failures, 0 threads, %s checks"
                     % (r["pr"], r["head"], r["req_ok"], r["req_of"], r["checks_total"]))
        # clean-but-unchecked is a trap, not a pass — surface it distinctly
        if r["clean_but_unchecked"]:
            k = "unchk:%s:%s" % (r["pr"], r["head"])
            if k not in seen:
                seen.add(k)
                emit("⚠ #%s reports clean with only %s checks — NEVER CHECKED, not a pass"
                     % (r["pr"], r["checks_total"]))
    open(STATE, "w").write("\n".join(sorted(x for x in seen if x)))
    time.sleep(180)
