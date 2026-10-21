#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AtomGit 资产层每日巡检 v1.0 | Ω₀⊂⊙∞⊂Ω DID-BR-000002
- 7仓库 ls-remote 可达性
- 云端 /opt/ZONGYUAN-ROOT 未推送commit自动push(锁档联动兜底)
- boot-memory 敏感红线扫描(本地镜像)
- 真值快照 cron 新鲜度
- 结果上报网关 STATUS.atomgit.patrol
"""
import json, subprocess, time, os, re, urllib.request

REPOS = ["huodouai","zongyuan-root-sync","zongyuan-core-truths","zongyuan-truth-corpus",
         "zongyuan-root-achievements","zongyuan-character-keyframes","zongyuan-qwen-gguf"]
SYNC_DIR = "/opt/ZONGYUAN-ROOT"
SENS_PAT = [r'QXFobQpMToTGYFxUCTxcA6TjnPf', r'rn9iRxnd7tXz64mFBWzMx92Y',
            r'ag-74c256c3b2024d748517fa2253eb4d78', r'sk-[0-9a-f]{20,}', r'ssh-ed25519 AAAAC']

def sh(cmd, timeout=60):
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout).stdout.strip()
    except Exception as e:
        return f"ERR:{e}"

def main():
    ts = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    repos = {}
    for r in REPOS:
        out = sh(f"git ls-remote https://atomgit.com/zongyuangen/{r}.git HEAD 2>/dev/null | head -1")
        repos[r] = {"reachable": bool(out), "head": out.split("\t")[0][:10] if out else None}
    # 锁档联动兜底：云端未推送 commit → push
    sync = sh(f"cd {SYNC_DIR} && git rev-list HEAD..atomgit/main --count 2>/dev/null")
    unpushed = int(sync) if sync.isdigit() else -1
    pushed = False
    if unpushed > 0:
        sh(f"cd {SYNC_DIR} && git pull --rebase atomgit main 2>&1 && git push atomgit main 2>&1")
        pushed = True
    elif unpushed < 0:
        sh(f"cd {SYNC_DIR} && git fetch atomgit 2>&1")
    # 敏感红线（云端本地 boot-memory 镜像）
    sensitive = []
    if os.path.isdir(f"{SYNC_DIR}/boot-memory"):
        for root, dirs, fs in os.walk(f"{SYNC_DIR}/boot-memory"):
            dirs[:] = [d for d in dirs if d != ".git"]
            for f in fs:
                p = os.path.join(root, f)
                try: s = open(p, encoding="utf-8", errors="ignore").read()
                except: continue
                for pat in SENS_PAT:
                    if re.search(pat, s): sensitive.append(f"{os.path.relpath(p, SYNC_DIR)}:{pat[:12]}")
    # 真值快照新鲜度
    log = sh("ls -la /tmp/truth_snapshot.log 2>/dev/null | head -1")
    log_age = sh("test -f /tmp/truth_snapshot.log && echo $(( $(date +%s) - $(stat -c %Y /tmp/truth_snapshot.log) )) || echo -1")
    report = {
        "meta": {"name": "atomgit-patrol", "anchor": "Ω₀⊂⊙∞⊂Ω", "did": "DID-BR-000002", "ts": ts},
        "repos": repos,
        "sync": {"unpushed_before": unpushed, "auto_pushed": pushed, "head": sh(f"cd {SYNC_DIR} && git rev-parse --short HEAD")},
        "sensitive_hits": sensitive,
        "truth_snapshot": {"log": log[:80], "age_sec": log_age},
        "status": "OK" if (all(v["reachable"] for v in repos.values()) and not sensitive) else "WARN"
    }
    # 上报网关
    try:
        req = urllib.request.Request("https://www.huodouai.com/api/report/truth",
            data=json.dumps({"key": f"STATUS.atomgit.patrol.{int(time.time())}", "value": {
                "status": report["status"], "repos_ok": sum(1 for v in repos.values() if v["reachable"]),
                "repos_total": len(repos), "sensitive_hits": len(sensitive), "auto_pushed": pushed}}).encode(),
            headers={"Content-Type": "application/json", "X-DID": "DID-BR-000002"})
        resp = json.loads(urllib.request.urlopen(req, timeout=10).read().decode())
        gw = resp.get("truth_count", "?")
    except Exception as e:
        gw = f"ERR:{e}"
    print(json.dumps(report, ensure_ascii=False, indent=1))
    print("gateway:", gw)

if __name__ == "__main__":
    main()
