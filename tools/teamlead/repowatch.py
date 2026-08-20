import json, os, subprocess, sys, time
REPO = "Borduas-Holdings/Blazing-Back"
STATE = "/tmp/repowatch-state.json"

def gh(path, paginate=False):
    """GUARD: never suppress stderr; a failed read must be reportable, not empty."""
    cmd = ["gh", "api"] + (["--paginate"] if paginate else []) + [path]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if p.returncode != 0:
        return None, (p.stderr or p.stdout).strip()[:160]
    try:
        return json.loads(p.stdout), None
    except Exception as e:
        return None, "unparseable: %s" % e

def snap():
    out = {}
    m, err = gh("repos/%s/commits/main" % REPO)
    if err: return None, "main: " + err
    out["main"] = m["sha"][:9]
    prs, err = gh("repos/%s/pulls?state=open&per_page=100" % REPO)
    if err: return None, "pulls: " + err
    out["prs"] = {str(p["number"]): p["head"]["sha"][:9] for p in prs}
    iss, err = gh("repos/%s/issues?state=open&per_page=100&sort=created&direction=desc" % REPO)
    if err: return None, "issues: " + err
    nums = [i["number"] for i in iss if not i.get("pull_request")]
    out["maxissue"] = max(nums) if nums else 0
    return out, None

prev = None
if os.path.exists(STATE):
    try: prev = json.load(open(STATE))
    except Exception: prev = None
last_err = None
while True:
    cur, err = snap()
    if err:
        # GUARD: report the failure once per episode; silence must not read as "no change".
        if err != last_err:
            print("REPO UNREADABLE :: %s" % err, flush=True); last_err = err
        time.sleep(90); continue
    if last_err:
        print("REPO READABLE again", flush=True); last_err = None
    if prev:
        ev = []
        if cur["main"] != prev.get("main"):
            ev.append("MERGED TO MAIN: %s -> %s" % (prev.get("main"), cur["main"]))
        for n, sha in cur["prs"].items():
            if n not in prev.get("prs", {}):
                ev.append("NEW PR #%s %s" % (n, sha))
            elif prev["prs"][n] != sha:
                ev.append("PR #%s head %s -> %s" % (n, prev["prs"][n], sha))
        for n in prev.get("prs", {}):
            if n not in cur["prs"]:
                ev.append("PR #%s closed/merged" % n)
        if cur["maxissue"] > prev.get("maxissue", 0):
            ev.append("NEW ISSUE(S) up to #%s" % cur["maxissue"])
        for e in ev:
            print(e, flush=True)
    json.dump(cur, open(STATE, "w"))
    prev = cur
    time.sleep(90)
