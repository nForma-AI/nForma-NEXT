import json,subprocess,time,os,sys
SP=os.path.dirname(os.path.abspath(__file__))
IDS=["terminal-da3db0b6-8277-4979-847e-da94eaaddbef","terminal-bf43c03c-5be4-4819-8b6a-d0cb4136cf7c",
     "terminal-4fbc5a7d-3c48-481c-95e7-0d7879899e74","terminal-74df2764-5a9a-4a08-8c90-4f877a3bcba0"]
NAME={"da3db0b6":"IMPLEMENTER","bf43c03c":"IMPLEMENTER2","4fbc5a7d":"IMPLEMENTER5","74df2764":"IMPLEMENTER4"}
LOG=open(os.path.join(SP,"boxwatch.log"),"a",buffering=1)
arg=json.dumps({"name":"terminal.getStatus","arguments":{"terminalIds":IDS,
    "includeOutput":{"lines":14,"stripAnsi":True}}})
last={}
WANT="f0aa822b0ba19b148e91b70cea17a11fa22d6a2eaa3b941db9eded67049ef215"
def ts(): return time.strftime("%H:%M:%SZ",time.gmtime())
for _ in range(400):
    try:
        r=subprocess.run([os.path.join(SP,"dt.sh"),"tools/call",arg],capture_output=True,text=True,timeout=90)
        d=json.loads(r.stdout)
        ws=(d.get("result",{}).get("_meta",{}) or {}).get("org.daintree/resolved-workspace",{})
        wid=ws.get("workspaceId","")
        if wid!=WANT:
            LOG.write(f"{ts()} INVALID workspace-flip -> {ws.get('workspacePath','?')} ({wid[:12]})\n")
            time.sleep(20); continue
        body=d["result"]["content"][0]["text"]
        if '"code"' in body and "EXECUTION_ERROR" in body:
            LOG.write(f"{ts()} INVALID exec-error :: {body[:90]}\n"); time.sleep(20); continue
        rows=json.loads(body)
    except Exception as e:
        LOG.write(f"{ts()} INVALID probe-failed {type(e).__name__}: {str(e)[:80]}\n"); time.sleep(20); continue
    for t in (rows.get("terminals") or rows):
        tid=t["terminalId"]; short=tid[9:17]; nm=NAME.get(short,short)
        ro=t.get("recentOutput") or ""
        if isinstance(ro,list): ro="\n".join(ro)
        box=[l.strip() for l in ro.split("\n") if l.strip().startswith("❯")]
        txt=box[-1][1:].strip() if box else ""
        if txt and last.get(nm)!=txt:
            LOG.write(f"{ts()} APPEARED {nm} state={t.get('agentState')} :: {txt[:80]}\n")
        last[nm]=txt
    time.sleep(20)
