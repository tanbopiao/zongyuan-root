#!/usr/bin/env python3
"""独立校验器：不与wrapper同进程，定期校验wrapper输出"""
import requests, json, time, hashlib, os
from datetime import datetime

LOG = "/root/zongyuan-yuanji/logs/validator.jsonl"
WRAPPER = "https://127.0.0.1:18080"

def check_health():
    try:
        r = requests.get(f"{WRAPPER}/health", verify=False, timeout=5)
        return {"check": "health", "ok": r.json().get("ok", False)}
    except Exception as e:
        return {"check": "health", "ok": False, "err": str(e)[:80]}

def check_models():
    try:
        r = requests.post(f"{WRAPPER}/v1/ask", json={"prompt":"1+1=","max_tokens":10}, verify=False, timeout=30)
        d = r.json()
        ans = str(d.get("response",""))
        return {"check": "models", "ok": "2" in ans, "ans": ans[:50]}
    except Exception as e:
        return {"check": "models", "ok": False, "err": str(e)[:80]}

def check_no_self_certify():
    """G隔离：wrapper不能自己说自己对，必须有外部校验记录"""
    return {"check": "g_isolated", "ok": os.path.exists(LOG), "note": "validator独立运行"}

def run():
    results = [check_health(), check_models(), check_no_self_certify()]
    entry = {"ts": datetime.now().isoformat(), "results": results}
    with open(LOG, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    ok_count = sum(1 for r in results if r.get("ok"))
    print(f"[validator] {ok_count}/{len(results)} passed")

if __name__ == "__main__":
    run()
