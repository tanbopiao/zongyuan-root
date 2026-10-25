#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ZONGYUAN-WEBDEPLOY-PACK 自执行器：官网git通道云端一键部署 + 回执（幂等）"""
import subprocess, json, urllib.request, os

GATEWAY = "https://www.huodouai.com"
DIRS = ["/www/wwwroot/huodouai.com", "/www/wwwroot/www.huodouai.com"]
REPO = "https://gitee.com/huodou-cloud-intelligence-aios/huodouai-website.git"
BRANCH = "web-deploy"
DID = "DID-BR-000002"
TRACE = "Ω₀⊂⊙∞⊂Ω"

def run(cmd, t=90):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=t)
    return r.returncode, (r.stdout + r.stderr).strip()[:200]

def config_dir(d):
    if not os.path.isdir(d):
        return {"ok": False, "msg": "目录不存在"}
    rc, msg = run(f"cd {d} && git remote remove origin 2>/dev/null; "
                  f"git remote add origin {REPO} && git fetch -q origin {BRANCH} && "
                  f"git checkout -q -B {BRANCH} origin/{BRANCH} 2>/dev/null || git checkout -q {BRANCH}; "
                  f"git pull -q origin {BRANCH}")
    return {"ok": rc == 0, "msg": msg or "已同步"}

def setup_cron():
    rc, out = run("crontab -l 2>/dev/null | grep -c 'huodouai.com'")
    if out.strip() not in ("", "0"):
        return {"ok": True, "msg": "cron 已存在"}
    line = "*/5 * * * * cd /www/wwwroot/huodouai.com && git pull -q origin web-deploy >/dev/null 2>&1"
    rc, msg = run(f"(crontab -l 2>/dev/null; echo '{line}') | crontab -")
    return {"ok": rc == 0, "msg": "cron 已添加（每5分钟）"}

def report(key, value):
    body = json.dumps({"truth_key": key,
        "truth_value": json.dumps(value, ensure_ascii=False),
        "source_node": "cloud-kernel", "confidence": 1.0, "truth_type": "execution"}).encode()
    req = urllib.request.Request(f"{GATEWAY}/api/report/truth", data=body,
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode()).get("action")
    except Exception as e:
        return f"err:{str(e)[:50]}"

def main():
    results = {d: config_dir(d) for d in DIRS}
    results["cron"] = setup_cron()
    ack = report("ZONGYUAN.WEBDEPLOY.PACK.ACK.V1.0",
                 {"results": results, "branch": BRANCH, "did": DID, "trace": TRACE})
    print(json.dumps(results, ensure_ascii=False, indent=2))
    print("ACK:", ack)

if __name__ == "__main__":
    main()
