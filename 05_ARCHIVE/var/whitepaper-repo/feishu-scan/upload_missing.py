#!/usr/bin/env python3
import json, subprocess, time

cf = json.load(open("confirmed.json"))
todo = cf["confirmed_missing"]
print("to upload:", len(todo))

uploaded = []
failed = []
for i, e in enumerate(todo):
    body = {
        "truth_key": e["key"],
        "truth_value": e["summary"],
        "source_node": "local-feishu-extract",
        "confidence": 0.95,
        "truth_type": e["type"],
    }
    try:
        p = subprocess.run(["curl","-s","--max-time","15","-X","POST",
            "https://www.huodouai.com/api/report/truth",
            "-H","Content-Type: application/json",
            "-d", json.dumps(body, ensure_ascii=False)],
            capture_output=True, text=True)
        d = json.loads(p.stdout)
        st = d.get("status") or d.get("code") or ("ok" if d.get("success") else "fail")
        act = d.get("action")
        if (d.get("success") is True) or st in ("ok","success",200) or d.get("truth") or d.get("id"):
            uploaded.append({"truth_key": e["key"], "http": st, "action": act})
        else:
            failed.append({"truth_key": e["key"], "resp": p.stdout[:200]})
    except Exception as ex:
        failed.append({"truth_key": e["key"], "err": str(ex)[:150]})
    if (i+1) % 50 == 0:
        print(f"  ...{i+1}/{len(todo)} ok={len(uploaded)} fail={len(failed)}")
    time.sleep(0.1)

print("UPLOADED OK:", len(uploaded))
print("FAILED:", len(failed))
if failed:
    for f in failed[:5]: print("  FAIL", f)
json.dump({"uploaded": uploaded, "failed": failed}, open("upload_result.json","w"), ensure_ascii=False, indent=1)
