# GUARD: context% lives ONLY in the rendered status line. A pane whose status line
# is not in the captured viewport yields NO number — that is "unknown", never "safe".
import json,re,subprocess,sys
sp="/private/tmp/claude-501/-Users-jonathanborduas-code-DigitalFrontier-infra/e4a7769d-4905-49e7-b80d-1c3df6c7f71f/scratchpad"
rows=[a for a in json.load(open(sp+"/.gb.json")) if not a["dead"]]
out=[]
for a in rows:
    m={"name":"terminal.getOutput","arguments":{"terminalId":a["id"],"maxLines":14}}
    p=subprocess.run([sp+"/dt.sh","tools/call",json.dumps(m)],capture_output=True,text=True)
    txt=""
    try:
        d=json.loads(p.stdout); t="".join(x.get("text","") for x in d["result"]["content"])
        try: t=json.loads(t).get("content",t)
        except Exception: pass
        txt=t.replace("\\n","\n")
    except Exception: pass
    mm=re.search(r"(\d{1,3})%\s*\((\d+)K\)", txt)
    pct=int(mm.group(1)) if mm else None
    out.append((a["title"], pct, mm.group(2)+"K" if mm else "-"))
out.sort(key=lambda r:-(r[1] if r[1] is not None else -1))
print(f"{'agent':<11}{'ctx%':>6}{'tokens':>9}  state")
for name,pct,tok in out:
    if pct is None: st="⚠ UNKNOWN — status line not in viewport; NOT a clean bill"
    elif pct>=90: st="⛔ CRITICAL — prompt to preserve state NOW"
    elif pct>=80: st="⚠ HIGH — prompt before assigning new work"
    else: st="ok"
    print(f"{name:<11}{(str(pct)+'%' if pct is not None else '?'):>6}{tok:>9}  {st}")
