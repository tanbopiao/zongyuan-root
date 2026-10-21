#!/usr/bin/env python3
import json, subprocess, time, sys

pre = json.load(open("recon_pre.json"))
missing = pre["missing_local"]  # list of {key,table,summary,type}
print("to confirm:", len(missing))

confirmed_missing = []
confirmed_hit = []
for i, e in enumerate(missing):
    key = e["key"]
    try:
        p = subprocess.run(["curl","-s","--max-time","12",
            f"https://www.huodouai.com/api/truth/{key}"], capture_output=True, text=True)
        d = json.loads(p.stdout)
        if d.get("status") == "ok" and d.get("truth"):
            confirmed_hit.append(key)
        else:
            confirmed_missing.append(e)
    except Exception as ex:
        # network error -> treat as uncertain, retry once
        time.sleep(1)
        try:
            p = subprocess.run(["curl","-s","--max-time","12",
                f"https://www.huodouai.com/api/truth/{key}"], capture_output=True, text=True)
            d = json.loads(p.stdout)
            if d.get("status") == "ok" and d.get("truth"):
                confirmed_hit.append(key)
            else:
                confirmed_missing.append(e)
        except Exception:
            confirmed_missing.append(e)  # conservative: upload anyway
    if (i+1) % 50 == 0:
        print(f"  ...{i+1}/{len(missing)} confirmed_missing={len(confirmed_missing)} hit={len(confirmed_hit)}")

print("CONFIRMED MISSING:", len(confirmed_missing))
print("CONFIRMED HIT:", len(confirmed_hit))
json.dump({"confirmed_missing": confirmed_missing, "confirmed_hit": confirmed_hit},
          open("confirmed.json","w"), ensure_ascii=False, indent=1)
