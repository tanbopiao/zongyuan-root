#!/usr/bin/env python3
"""ZONGYUAN-ROOT 本地内核权威清单定期复核
对比 ROOT-MANIFEST.json 权威清单，识别新增/删除/变更，上报云端变更。
DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω
"""
import os,hashlib,json,time,subprocess
ROOT="/home/user/ZONGYUAN-ROOT"
CORE_DIRS=["config","meta-rules","core/config","scripts","locks"]
MANIFEST=os.path.join(ROOT,"ROOT-MANIFEST.json")
def sha256(p):
    h=hashlib.sha256()
    try:
        with open(p,'rb') as f:
            for c in iter(lambda:f.read(65536),b''): h.update(c)
    except: return None
    return h.hexdigest()
def scan():
    assets={}
    for d in CORE_DIRS:
        base=os.path.join(ROOT,d)
        if not os.path.isdir(base): continue
        for dp,dn,fn in os.walk(base):
            if ".git" in dp or "__pycache__" in dp: continue
            for f in fn:
                if f.endswith(".pyc"): continue
                p=os.path.join(dp,f); rel=os.path.relpath(p,ROOT)
                h=sha256(p)
                if h: assets[rel]=h
    return assets
def main():
    if not os.path.exists(MANIFEST):
        print("MANIFEST缺失"); return 2
    m=json.load(open(MANIFEST,encoding="utf-8"))
    baseline=m.get("assets",{})
    cur=scan()
    added=[r for r in cur if r not in baseline]
    removed=[r for r in baseline if r not in cur]
    changed=[r for r in baseline if r in cur and baseline[r]["sha"]!=cur[r]]
    drift=len(added)+len(removed)+len(changed)
    report={"ts":time.strftime("%Y-%m-%dT%H:%M:%S+0800"),"manifest_sha":m.get("_sha",""),
        "baseline_total":len(baseline),"current_total":len(cur),
        "drift":drift,"added":added,"removed":removed,"changed":changed,
        "status":"CONVERGED" if drift==0 else "DRIFT"}
    print(f"复核[{report['ts']}] baseline={report['baseline_total']} cur={report['current_total']} drift={drift} status={report['status']}")
    if added: print("  新增:",added)
    if removed: print("  删除:",removed)
    if changed: print("  变更:",changed)
    # 有漂移才上报云端
    if drift>0:
        payload={"key":"root.reconcile.20261010","value":report}
        try:
            r=subprocess.run(["curl","-s","--noproxy","*","--max-time","15","-X","POST",
                "https://www.huodouai.com/api/report/truth","-H","X-DID: DID-BR-000002",
                "-H","Content-Type: application/json","-d",json.dumps(payload,ensure_ascii=False)],
                capture_output=True,text=True,timeout=20)
            print("  上报:",r.stdout.strip()[:120])
        except Exception as e:
            print("  上报失败:",e)
    return 0 if drift==0 else 1
if __name__=="__main__":
    exit(main())
