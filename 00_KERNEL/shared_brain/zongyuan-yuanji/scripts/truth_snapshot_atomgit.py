#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN 真值快照脱敏入库脚本 v1.0
锚定 DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
- 从 truth.db 导出【公开安全层】：统计型快照 + 白名单事件key列表（不含value内容）
- 脱敏原则：key/secret/token/password/ssh/私钥/内部指令 一律不导出内容
- 每日 push 至 AtomGit zongyuan-core-truths/data/snapshots/（append-only）
- 凭证：云端 ~/.git-credentials（零明文落脚本）
"""
import json, time, subprocess, sqlite3, hashlib, os, shutil, sys

DB = "/www/wwwroot/huodouai.com/zhongshu/data/truth/truth.db"
REPO = "/root/zongyuan-yuanji/var/atomgit-core-truths"
GIT_URL = "https://atomgit.com/zongyuangen/zongyuan-core-truths.git"
# 白名单命名空间（公开安全层）；其余 key 一律只计数量不列明细
WHITELIST = ("REPORT.", "SEED_", "EVOLUTION.", "HEARTBEAT", "STATUS", "SFMP.node",
             "GOV.POLICY.", "ARCH-", "SCAN", "QUOTA", "TEST.")
# 敏感子串：命中即跳过（即使在白名单内也不列明细）
SENSITIVE = ("key", "token", "secret", "password", "passwd", "ssh", "ed25519",
             "rsa", "authorized_keys", "INSTRUCTION", "TASK.", "DID-BR-000001",
             "kek", "api_key", "apikey", "bearer", "私钥", "密钥")

def sh(cmd, timeout=30):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout).stdout.strip()

def main():
    ts = time.strftime("%Y%m%d-%H%M%S")
    day = ts[:10]
    try:
        con = sqlite3.connect(DB)
        con.text_factory = str
        cur = con.cursor()
        total = cur.execute("SELECT COUNT(*) FROM truth").fetchone()[0]
        # 各命名空间计数（公开安全层，不含value）
        ns = {}
        for row in cur.execute("SELECT key FROM truth"):
            k = row[0] or ""
            prefix = k.split(".")[0][:20]
            ns[prefix] = ns.get(prefix, 0) + 1
        # 白名单事件明细（key + ts，无value）
        events = []
        for row in cur.execute("SELECT key, ts FROM truth ORDER BY seq DESC LIMIT 2000"):
            k, t = row[0] or "", row[1] or ""
            low = k.lower()
            if any(s in low for s in SENSITIVE):
                continue
            if k.startswith(WHITELIST):
                events.append({"key": k, "ts": str(t)[:19]})
        con.close()
    except Exception as e:
        print("DB_ERROR:", e); sys.exit(1)

    snap = {
        "meta": {"name": "truth-snapshot", "anchor": "Ω₀⊂⊙∞⊂Ω", "did": "DID-BR-000002",
                 "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "scope": "public-safe-layer"},
        "stats": {"total_truth": total, "namespace_count": len(ns), "whitelist_events": len(events)},
        "namespace_histogram": {k: v for k, v in sorted(ns.items(), key=lambda x: -x[1])[:20]},
        "events": events,
        "note": "统计型快照: 仅key与计数, 不含value/密钥/内部指令内容",
    }
    payload = json.dumps(snap, ensure_ascii=False, indent=1)
    sha = hashlib.sha256(payload.encode()).hexdigest()[:16]
    snap["meta"]["sha256_prefix"] = sha
    payload = json.dumps(snap, ensure_ascii=False, indent=1)

    # 更新本地镜像仓
    if not os.path.isdir(REPO):
        os.makedirs(os.path.dirname(REPO), exist_ok=True)
        if sh(f"git clone --depth 1 {GIT_URL} {REPO}") == "" and not os.path.isdir(REPO):
            print("CLONE_FAIL"); sys.exit(1)
    os.makedirs(f"{REPO}/data/snapshots", exist_ok=True)
    fname = f"{REPO}/data/snapshots/truth-snapshot-{day}.json"
    # append-only：同一天存在则并入同文件（新事件追加）
    old = []
    if os.path.exists(fname):
        try:
            old = json.load(open(fname)).get("events", [])
        except Exception:
            pass
    snap["events"] = old + events
    payload = json.dumps(snap, ensure_ascii=False, indent=1)
    with open(fname, "w", encoding="utf-8") as f:
        f.write(payload)
    # manifest
    with open(f"{REPO}/data/snapshots/MANIFEST.md", "a", encoding="utf-8") as f:
        f.write(f"- {day} {time.strftime('%H:%M')} | sha256:{sha} | total:{total} | events:{len(events)}\n")

    # push
    cmds = [
        f"cd {REPO} && git add data/snapshots/",
        f"cd {REPO} && git -c user.name=zongyuanroot -c user.email=zongyuangen@atomgit.com commit -m 'truth snapshot {day} sha:{sha}'",
        f"cd {REPO} && git push origin main",
    ]
    for c in cmds:
        r = sh(c)
        if "fatal" in r or "error" in r.lower():
            print("PUSH_WARN:", r[:120])
    print(f"OK {fname} sha={sha} total={total} events={len(events)}")

if __name__ == "__main__":
    main()
