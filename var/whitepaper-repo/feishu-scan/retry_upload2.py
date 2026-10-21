#!/usr/bin/env python3
import json, subprocess, time

res = json.load(open("upload_result.json"))
failed = res["failed"]
print("retrying:", len(failed))

cf = json.load(open("confirmed.json"))
body_map = {e["key"]: e for e in cf["confirmed_missing"]}

still_fail = []
ok_extra = []
for i, f in enumerate(failed):
    e = body_map.get(f["truth_key"])
    if not e:
        continue
    body = {"truth_key": e["key"], "truth_value": e["summary"],
            "source_node": "local-feishu-extract", "confidence": 0.95, "truth_type": e["type"]}
    ok = False
    for attempt in range(4):
        try:
            p = subprocess.run(["curl","-s","--max-time","15","-X","POST",
                "https://www.huodouai.com/api/report/truth",
                "-H","Content-Type: application/json",
                "-d", json.dumps(body, ensure_ascii=False)], capture_output=True, text=True)
            d = json.loads(p.stdout)
            if d.get("success") is True or (d.get("status") in ("ok","success")):
                ok = True; break
            time.sleep(2.5 * (attempt+1))
        except Exception:
            time.sleep(2)
    if ok:
        ok_extra.append(e["key"])
    else:
        still_fail.append({"truth_key": e["key"], "err": "rate-limited after retries"})
    if (i+1) % 20 == 0:
        print(f"  ...{i+1}/{len(failed)} recovered={len(ok_extra)} still_fail={len(still_fail)}")
    time.sleep(0.8)

print("RECOVERED:", len(ok_extra), "STILL FAIL:", len(still_fail))
final = res["uploaded"] + [{"truth_key": k, "http": "ok", "action": "retry"} for k in ok_extra]
json.dump({"uploaded": final, "failed": still_fail}, open("upload_result.json","w"), ensure_ascii=False, indent=1)
