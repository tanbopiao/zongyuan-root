#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""官网↔AtomGit 联动发布 v1.0 | Ω₀⊂⊙∞⊂Ω DID-BR-000002
AtomGit huodouai 仓库 docs/ + portal.html 变更 → 自动发布到官网 www.huodouai.com
单向(仓库为源, 官网为发布端), 幂等, 每次全量对拍。
"""
import os, re, subprocess, json, time, hashlib, urllib.request

REPO_URL = "https://zongyuangen:rn9iRxnd7tXz64mFBWzMx92Y@atomgit.com/zongyuangen/huodouai.git"
LOCAL = "/root/zongyuan-yuanji/var/docs-sync"
WEB = "/www/wwwroot/huodouai.com"
SYNC_DIRS = ["docs", "articles"]

def sh(cmd, timeout=120):
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout).stdout.strip()
    except Exception as e:
        return f"ERR:{e}"

def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(65536), b''): h.update(c)
    return h.hexdigest()

def main():
    ts = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    # 拉取仓库最新
    if not os.path.isdir(f"{LOCAL}/.git"):
        sh(f"git clone -q --depth 1 {REPO_URL} {LOCAL}")
    else:
        sh(f"cd {LOCAL} && git fetch -q origin && git reset -q --hard origin/main && git clean -qfd")
    # 对拍同步
    synced, changed = [], []
    for d in SYNC_DIRS:
        src, dst = f"{LOCAL}/{d}", f"{WEB}/{d}"
        os.makedirs(dst, exist_ok=True)
        for f in os.listdir(src):
            if f.startswith('.'): continue
            sp, dp = os.path.join(src, f), os.path.join(dst, f)
            if not os.path.exists(dp) or sha256(sp) != sha256(dp):
                with open(sp, 'rb') as a, open(dp, 'wb') as b: b.write(a.read())
                changed.append(f"{d}/{f}")
                synced.append(f"{d}/{f}")
    # portal.html 联动
    sp, dp = f"{LOCAL}/portal.html", f"{WEB}/portal.html"
    if os.path.exists(sp) and (not os.path.exists(dp) or sha256(sp) != sha256(dp)):
        with open(sp, 'rb') as a, open(dp, 'wb') as b: b.write(a.read())
        synced.append("portal.html")
    # 上报网关
    try:
        req = urllib.request.Request("https://www.huodouai.com/api/report/truth",
            data=json.dumps({"key": f"REPORT.docs.sync.{int(time.time())}", "value": {
                "synced": len(synced), "changed": changed[:5], "ts": ts}}).encode(),
            headers={"Content-Type": "application/json", "X-DID": "DID-BR-000002"})
        gw = json.loads(urllib.request.urlopen(req, timeout=10).read().decode()).get("truth_count", "?")
    except Exception as e:
        gw = f"ERR:{e}"
    print(json.dumps({"ts": ts, "synced": synced, "gw": gw}, ensure_ascii=False))

if __name__ == "__main__":
    main()
