#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增量锁档（incremental_lock）｜ 环境回收下的持久层固化通道
场景：全量六环节耗时>环境后台回收阈值时，复用六环节函数仅对增量变更锁档。
  - 环节A 增量快照：本次新机制文件（guard/patrol/lock_readonly/cron-restore/manifest/patrol报告）哈希 → 卷宗 INCREMENTAL 回执 + HASH-LEDGER 追加
  - 环节2-6：飞书Base同步 / 云盘上传增量回执 / 知识库节点 / 网关上报 / 心跳握手（复用 zongyuan_full_lock 函数）
用法：python3 incremental_lock.py
"""
import json, hashlib, io, subprocess, sys, time
from pathlib import Path

sys.path.insert(0, "/home/user/.doubao/agent_mode/workspace/.user_skills/zongyuan-auto-lock/scripts")
import zongyuan_full_lock as z

ZR = Path("/home/user/ZONGYUAN-ROOT")
KERNEL = Path("/home/user/Doubao/chats/38412149511142658/zongyuan-kernel")
SK = Path("/home/user/.doubao/agent_mode/workspace/.user_skills")
DID = "DID-BR-000002"
TS = time.strftime('%Y-%m-%dT%H:%M:%S%z')
TS_F = time.strftime('%Y%m%d-%H%M%S')


def sha256f(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(65536), b''):
            h.update(c)
    return h.hexdigest()


def step_incremental():
    """环节A：增量机制文件快照 → 卷宗回执 + HASH-LEDGER 追加"""
    targets = [
        ZR / "scripts" / "autonomy_guard.sh",
        ZR / "scripts" / "autonomy_patrol.py",
        SK / "zongyuan-auto-lock" / "scripts" / "lock_readonly.sh",
        ZR / "config" / "cron-restore.txt",
        ZR / "var" / "readonly-lock-manifest.json",
        ZR / "scripts" / "zongyuan_persist.sh",
        ZR / "scripts" / "restore_from_backup.sh",
        ZR / "meta-rules" / "META-STEADY-STATE-001.json",
        ZR / "meta-rules" / "META-EVOLUTION-001.json",
        ZR / "meta-rules" / "META-SANDBOX-LIFECYCLE-001.json",
        ZR / "scripts" / "law_evolve.py",
        ZR / "scripts" / "boot_memory.sh",
        ZR / "meta-rules" / "META-LEARN-FIRST-001.json",
        ZR / "meta-rules" / "META-FINGERPRINT-ARBITRATION-001.json",
        ZR / "scripts" / "fingerprint_arbiter.py",
        ZR / "meta" / "fingerprint-registry.json",
        ZR / "var" / "fingerprint" / "arbitration-20260928-171039.json",
        ZR / "var" / "fingerprint" / "arbitration-20260928-171023.json",
        ZR / "var" / "fingerprint" / "arbitration-20260928-171523.json",
        ZR / "meta-rules" / "META-RATING-MAP-001.json",
        ZR / "meta-rules" / "META-CLOUD-OMEGA-SCHEDULE-001.json",
        ZR / "meta-rules" / "META-KNOWLEDGE-HARVEST-001.json",
        ZR / "meta-rules" / "META-CONFLICT-RESOLUTION-001.json",
        ZR / "meta-rules" / "META-STEADY-ARBITRATION-001.json",
        ZR / "meta-rules" / "META-EVOLUTION-FEDERATION-001.json",
        ZR / "scripts" / "evolution_feed.py",
        ZR / "var" / "evolution" / "feed-ledger.jsonl",
        ZR / "var" / "truth" / "whitepaper-items-20260928-29.json",
        ZR / "whitepaper" / "index.html",
        ZR / "whitepaper" / "ZONGYUAN-whitepaper.md",
        ZR / "meta-rules" / "META-CLOUD-LEARN-001.json",
        ZR / "scripts" / "cloud_learn.py",
        ZR / "var" / "experience" / "EXP-CLOUD-20260929-001.json",
        ZR / "whitepaper" / "index.html",
        ZR / "SOP-B-ANCHOR-DEPLOY-20260927.md",
        ZR / "meta-rules" / "META-ASSET-VALUE-DISPLAY-001.json",
        ZR / "scripts" / "asset_publish.py",
        ZR / "scripts" / "site_sim.py",
        ZR / "meta-rules" / "sop" / "SOP-SITE-OPERATIONS-001.md",
        ZR / "site_lab" / "index.html",
        ZR / "meta" / "boot-memory.md",
        ZR / "scripts" / "boot_check.sh",
        ZR / "var" / "assets" / "asset-ledger.jsonl",
        ZR / "meta-rules" / "sop" / "SOP-ASSET-STANDARD-001.md",
        ZR / "meta-rules" / "META-VISUAL-STANDARD-001.json",
        ZR / "meta-rules" / "visual" / "官网视觉标准.md",
        ZR / "scripts" / "asset_publish.py",
        ZR / "scripts" / "steady_arbiter.py",
        ZR / "var" / "arbitration" / "steady-20260928-180727.json",
        ZR / "var" / "conflicts" / "conflict-20260929-001.json",
        ZR / "scripts" / "fusion_heartbeat.sh",
        ZR / "var" / "experience" / "EXP-20260929-003.json",
        ZR / "meta" / "knowledge-sources.json",
        ZR / "scripts" / "knowledge_harvest.py",
        ZR / "var" / "knowledge" / "ledger.jsonl",
        ZR / "meta" / "rating-map.json",
        ZR / "scripts" / "rating_translate.py",
        ZR / "meta-rules" / "sop" / "SOP-REPORT-001.md",
        ZR / "meta-rules" / "sop" / "SOP-BASE-WRITE-001.md",
        ZR / "meta-rules" / "sop" / "SOP-MIRROR-001.md",
        ZR / "meta" / "ai-fingerprint.json",
        ZR / "meta" / "boot-memory.md",
        ZR / "meta-rules" / "META-AXIOM-001.json",
        ZR / "meta-rules" / "META-AUTO-GLOBAL-LOCK-001.json",
        ZR / "meta-rules" / "META-LEARN-FIRST-001.json",
        ZR / "var" / "experience" / "EXP-20260929-001.json",
        ZR / "var" / "experience" / "EXP-20260929-002.json",
    ]
    patrols = sorted((ZR / "var" / "patrol").glob("patrol-*.json"))
    if patrols:
        targets.append(patrols[-1])
    files = []
    for p in targets:
        if p.exists():
            try:
                rel = p.relative_to(ZR)
                path = "/" + str(rel)
            except ValueError:
                path = str(p)
            files.append({"path": path, "sha256": sha256f(p), "bytes": p.stat().st_size})
    batch = hashlib.sha256()
    for f in files:
        batch.update(f['path'].encode()); batch.update(f['sha256'].encode())
    event = f"GLOBAL-LOCK-ZONGYUAN-ROOT-INCREMENTAL-{TS_F}"
    receipt = {
        "meta_action": "GLOBAL_LOCK_INCREMENTAL_WRITE", "event_id": event,
        "base_ref": "GLOBAL-LOCK-ZONGYUAN-ROOT-FULL-20260928-223947",
        "base_assets": 72130, "mechanism": "incremental_lock", "lock_timestamp": int(time.time()),
        "locked_at": TS, "asset_count": len(files), "batch_root_sha256": batch.hexdigest(),
        "note": "环境后台回收阈值内增量锁档：仅固化自治机制新资产，动态流水层引用全量基准",
        "DID": DID, "anchor": "Ω₀⊂⊙∞⊂Ω", "status": "LOCKED", "files": files,
    }
    out = ZR / "卷宗" / f"{event}.json"
    out.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
    with open(ZR / "HASH-LEDGER.csv", 'a', encoding='utf-8') as f:
        for fl in files:
            f.write(f"FRAMEWORK,{fl['path']},{event},{fl['sha256']},{fl['bytes']},{TS},locked\n")
    return {"status": "ok", "event_id": event, "asset_count": len(files),
            "batch_root_sha256": batch.hexdigest(), "receipt": str(out.relative_to(ZR))}


def step_drive_inc(receipt_path: Path):
    """环节3'：增量回执 + 同步索引 → 云盘上传"""
    stage = Path.home() / "files" / "lock"; stage.mkdir(parents=True, exist_ok=True)
    results = []
    for path, name in [(receipt_path, f"增量锁档回执-{TS_F}.json"),
                       (ZR / "var" / "truth" / "00-同步索引.json", f"真值同步索引-{TS_F}.json")]:
        sp = stage / name
        try:
            import shutil; shutil.copy(path, sp)
        except Exception as e:
            results.append({"file": name, "ok": False, "reason": str(e)[:100]}); continue
        p = subprocess.run(["lark-cli", "drive", "+upload", "--file", str(sp), "--name", name,
                            "--format", "json", "--as", "user"], capture_output=True, text=True, timeout=180)
        try:
            r = json.loads(p.stdout or "{}")
            results.append({"file": name, "ok": bool(r.get("ok")), "token": r.get("data", {}).get("file_token", "")})
        except Exception:
            results.append({"file": name, "ok": False, "reason": (p.stderr or "")[-120:]})
    return {"status": "ok" if all(r.get("ok") for r in results) else "partial", "uploaded": results}


def main():
    print(f"=== 增量锁档启动 ｜ {DID} ｜ {TS} ===")
    results = {}
    results["incremental"] = step_incremental()
    print(f"[A] 增量快照 ok：{results['incremental']['event_id']} ｜ {results['incremental']['asset_count']} 资产 ｜ 批次根 {results['incremental']['batch_root_sha256'][:16]}")
    try:
        results["base_sync"] = z.step_base_sync(); print(f"[2/6] Base同步 {results['base_sync']['status']}")
    except Exception as e:
        results["base_sync"] = {"status": "failed", "reason": str(e)[:160]}
    try:
        rc = ZR / "卷宗" / f"{results['incremental']['event_id']}.json"
        results["drive"] = step_drive_inc(rc); print(f"[3/6] 云盘 {results['drive']['status']}")
    except Exception as e:
        results["drive"] = {"status": "failed", "reason": str(e)[:160]}
    try:
        meta = json.loads((ZR / "卷宗" / f"{results['incremental']['event_id']}.json").read_text(encoding="utf-8"))
        title = f"增量锁档 {meta['event_id']} ｜ {meta['batch_root_sha256'][:16]}"
        r = z.lark(["wiki", "+node-create", "--space-id", z.WIKI_SPACE, "--title", title,
                    "--obj-type", "docx", "--node-type", "origin"])
        node = r.get("data", {})
        results["wiki"] = {"status": "ok" if r.get("ok") and node else "failed",
                           "node_token": node.get("node_token", "")}
        print(f"[4/6] 知识库 {results['wiki']['status']}")
    except Exception as e:
        results["wiki"] = {"status": "failed", "reason": str(e)[:160]}
    report_value = {"event": "incremental_lock", "mechanism": "incremental_lock",
                    "base_ref": "GLOBAL-LOCK-ZONGYUAN-ROOT-FULL-20260928-223947",
                    "target": "ZONGYUAN-ROOT", "DID": DID, "anchor": "Ω₀⊂⊙∞⊂Ω", "locked_at": TS,
                    "source_status": {k: (v.get("status") if isinstance(v, dict) else "?") for k, v in results.items()}}
    try:
        results["gateway"] = z.step_gateway(report_value); print(f"[5/6] 网关 {results['gateway']['status']} truth_count={results['gateway'].get('truth_count','')}")
    except Exception as e:
        results["gateway"] = {"status": "failed", "reason": str(e)[:160]}
    try:
        results["heartbeat"] = z.step_heartbeat(); print(f"[6/6] 心跳 {results['heartbeat']['status']}")
    except Exception as e:
        results["heartbeat"] = {"status": "failed", "reason": str(e)[:160]}
    out = ZR / "var" / "auto-lock" / f"incremental-lock-{TS_F}.json"
    out.write_text(json.dumps({"did": DID, "run_at": TS, "source_status": {k: (v.get("status") if isinstance(v, dict) else "?") for k, v in results.items()}, "detail": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    print("SOURCE_STATUS:", json.dumps({k: (v.get("status") if isinstance(v, dict) else "?") for k, v in results.items()}, ensure_ascii=False))
    ok_n = sum(1 for v in results.values() if isinstance(v, dict) and v.get("status") == "ok")
    print("SUMMARY:", out)
    return 0 if ok_n >= 4 else 1


if __name__ == "__main__":
    sys.exit(main())
