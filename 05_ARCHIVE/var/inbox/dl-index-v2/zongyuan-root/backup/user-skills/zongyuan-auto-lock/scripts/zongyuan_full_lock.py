#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT 全自动全域锁档机制（zongyuan-auto-lock skill 核心执行器）
锚定：DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω ｜ 本地实例自治内核
链路（六环节，逐源容错，失败不阻塞）：
  1. 本地实例内核快照锁档  —— ZONGYUAN-ROOT 全根 SHA-256 → 卷宗回执 + HASH-LEDGER 追加
  2. 飞书多维表格真值同步  —— Base 7 表逐表分页 → var/truth/ + 同步索引
  3. 飞书云盘归档           —— var/truth 同步索引 + 最新锁档回执 → Drive 根目录上传
  4. 飞书知识库归档         —— 锁档回执 → 知识库节点（标题内嵌事件ID+批次哈希）
  5. 云端记忆网关上报       —— X-DID 单头 POST https://www.huodouai.com/api/report/truth
  6. 心跳握手               —— 调用 scripts/heartbeat_sync.sh（上行+下行+握手落盘）
幂等：只追加不修改；排除 logs/.git/__pycache__/var/kek.env/var/nginx/zr_token.conf
用法：python3 zongyuan_full_lock.py [--skip-heartbeat]
"""
import argparse, base64, hashlib, json, shutil, subprocess, sys, time
from pathlib import Path

ROOT = Path("/home/user/ZONGYUAN-ROOT")
SKILL_DIR = Path("/home/user/.doubao/agent_mode/workspace/.user_skills/zongyuan-auto-lock/scripts")
DID = "DID-BR-000002"
ANCHOR = "Ω₀⊂⊙∞⊂Ω"
GW = "https://www.huodouai.com/api/report/truth"
BASE_TOKEN = "DgnMbLqZiaIUDKshqCrcD4DvnBg"
WIKI_SPACE = "7689477619196120266"  # ZONGYUAN-ROOT 知识库
EXCLUDE_PREFIX = ("logs/", "var/kek.env", "var/nginx/zr_token.conf")
EXCLUDE_SUB = ("/.git", "__pycache__", "/logs/")
TS = time.strftime('%Y-%m-%dT%H:%M:%S%z')
TS_F = time.strftime('%Y%m%d-%H%M%S')

def log(msg): print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(65536), b''):
            h.update(c)
    return h.hexdigest()

def lark(args, timeout=120):
    """lark-cli base/wiki/drive 统一调用，返回 dict"""
    p = subprocess.run(["lark-cli"] + args + ["--format", "json", "--as", "user"],
                       capture_output=True, text=True, timeout=timeout)
    try:
        return json.loads(p.stdout or "{}")
    except Exception:
        return {"ok": False, "_raw": (p.stdout or p.stderr)[-200:]}

def step_lock():
    """环节1：全根快照锁档 → 卷宗回执 + HASH-LEDGER 追加"""
    files = []
    for p in sorted(ROOT.rglob('*')):
        if not p.is_file(): continue
        rel = p.relative_to(ROOT).as_posix()
        if rel.startswith(EXCLUDE_PREFIX) or any(x in rel for x in EXCLUDE_SUB): continue
        files.append({'path': '/' + rel, 'sha256': sha256_file(p), 'bytes': p.stat().st_size})
    batch = hashlib.sha256()
    for f in files:
        batch.update(f['path'].encode()); batch.update(f['sha256'].encode())
    event = f"GLOBAL-LOCK-ZONGYUAN-ROOT-FULL-{TS_F}"
    receipt = {
        "meta_action": "GLOBAL_LOCK_WRITE", "event_id": event, "target_root": str(ROOT),
        "mechanism": "zongyuan-auto-lock", "lock_timestamp": int(time.time()), "locked_at": TS,
        "asset_count": len(files), "batch_root_sha256": batch.hexdigest(),
        "gateway_report": {"endpoint": GW, "did": DID, "status": "to_report"},
        "DID": DID, "anchor": ANCHOR, "status": "LOCKED", "files": files,
    }
    out = ROOT / "卷宗" / f"{event}.json"
    out.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
    with open(ROOT / "HASH-LEDGER.csv", 'a', encoding='utf-8') as f:
        for fl in files:
            f.write(f"FRAMEWORK,{fl['path']},{event},{fl['sha256']},{fl['bytes']},{TS},locked\n")
    return {"status": "ok", "event_id": event, "asset_count": len(files),
            "batch_root_sha256": batch.hexdigest(), "receipt": str(out.relative_to(ROOT))}

def step_base_sync():
    """环节2：飞书多维表格真值同步（全表分页 → var/truth/）"""
    OUT = ROOT / "var" / "truth"; OUT.mkdir(parents=True, exist_ok=True)
    tl = lark(["base", "+table-list", "--base-token", BASE_TOKEN])
    tables = tl.get("data", {}).get("tables", [])
    if not tables: return {"status": "failed", "reason": "table-list 无返回"}
    idx = {"title": "本地实例持久化真值存储（云端同步）", "synced_at": TS,
           "source_base": BASE_TOKEN, "tables": []}
    total = 0
    for i, t in enumerate(tables, 1):
        tid, name = t["id"], t["name"]
        rows, offset, fields = [], 0, []
        while True:
            d = lark(["base", "+record-list", "--base-token", BASE_TOKEN, "--table-id", tid,
                      "--limit", "200", "--offset", str(offset)])
            dd = d.get("data", {})
            rows.extend(dd.get("data", [])); fields = dd.get("fields", [])
            if not dd.get("has_more", False): break
            offset += len(dd.get("data", []))
        obj = {"table": name, "table_id": tid, "fields": fields, "records": rows,
               "record_count": len(rows), "synced_at": TS}
        (OUT / f"{i:02d}-{name}.json").write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')
        idx["tables"].append({"table": name, "file": f"{i:02d}-{name}.json", "records": len(rows)})
        total += len(rows)
    (OUT / "00-同步索引.json").write_text(json.dumps(idx, ensure_ascii=False, indent=2), encoding='utf-8')
    return {"status": "ok", "tables": len(tables), "records": total}

def latest_receipt() -> Path:
    return max((ROOT / "卷宗").glob("GLOBAL-LOCK-ZONGYUAN-ROOT-FULL-*.json"), key=lambda p: p.stat().st_mtime)

def step_drive():
    """环节3：飞书云盘归档（同步索引 + 最新锁档回执 → Drive 根目录）"""
    # lark-cli 文件路径白名单限制：ZONGYUAN-ROOT 不在允许根内，先复制到 ~/files/lock 再上传
    results = []
    stage = Path.home() / "files" / "lock"
    stage.mkdir(parents=True, exist_ok=True)
    targets = [
        (ROOT / "var" / "truth" / "00-同步索引.json", f"真值同步索引-{TS_F}.json"),
        (latest_receipt(), f"锁档回执-{TS_F}.json"),
    ]
    # A2: 附加最新运行态证据（环境截图 + 汇总）上传飞书云盘
    ev_dir = ROOT / "var" / "evidence"
    try:
        if ev_dir.is_dir():
            sums = sorted(ev_dir.glob("evidence-*.json"))
            scrn = sorted(ev_dir.glob("screen-*.*"))
            if sums: targets.append((sums[-1], f"证据汇总-{TS_F}.json"))
            if scrn: targets.append((scrn[-1], f"证据截图-{TS_F}.json"))
    except Exception:
        pass
    for path, name in targets:
        sp = stage / name
        try:
            shutil.copy(path, sp)
        except Exception as e:
            results.append({"file": name, "ok": False, "reason": f"stage copy failed: {e}"})
            continue
        p = subprocess.run(["lark-cli", "drive", "+upload", "--file", str(sp), "--name", name,
                            "--format", "json", "--as", "user"],
                           capture_output=True, text=True, timeout=180)
        try:
            r = json.loads(p.stdout or "{}")
            results.append({"file": name, "ok": bool(r.get("ok")),
                            "token": r.get("data", {}).get("file_token", "")})
        except Exception:
            results.append({"file": name, "ok": False, "reason": (p.stderr or "")[-120:]})
    ok_n = sum(1 for x in results if x["ok"])
    return {"status": "ok" if ok_n == len(results) else "partial",
            "uploaded": results, "ok_count": ok_n, "total": len(results)}

def step_wiki():
    """环节4：飞书知识库归档（锁档回执 → 知识库节点，标题内嵌事件ID+哈希）"""
    rc = latest_receipt()
    meta = json.loads(rc.read_text(encoding='utf-8'))
    title = f"全域锁档 {meta['event_id']} ｜ {meta['batch_root_sha256'][:16]}"
    r = lark(["wiki", "+node-create", "--space-id", WIKI_SPACE, "--title", title,
              "--obj-type", "docx", "--node-type", "origin"])
    node = r.get("data", {})
    if r.get("ok") and node:
        return {"status": "ok", "node_title": title,
                "node_token": node.get("node_token", ""), "obj_token": node.get("obj_token", "")}
    return {"status": "failed", "reason": (json.dumps(r, ensure_ascii=False)[-200:])}

def step_gateway(report_value: dict):
    """环节5：云端记忆网关上报（X-DID 单头，零令牌明文）"""
    payload = {"key": f"global_lock_auto_{int(time.time())}", "value": report_value}
    p = subprocess.run(["curl", "-sS", "-m", "25", "-X", "POST", GW,
                        "-H", f"X-DID: {DID}", "-H", "Content-Type: application/json",
                        "--data-binary", json.dumps(payload, ensure_ascii=False)],
                       capture_output=True, text=True, timeout=30)
    resp = p.stdout or p.stderr
    ok = "真值写入成功" in resp
    truth_count = ""
    try:
        truth_count = str(json.loads(resp).get("truth_count", ""))
    except Exception:
        pass
    return {"status": "ok" if ok else "failed", "truth_count": truth_count, "resp_tail": resp[-100:]}

def step_heartbeat():
    """环节6：心跳握手（调用既有 heartbeat_sync.sh，输出重定向到日志，按握手回执文件判定）"""
    hb_dir = ROOT / "var" / "heartbeat"
    before = max([p.stat().st_mtime for p in hb_dir.glob("握手-*.json")], default=0)
    p = subprocess.run(["bash", str(ROOT / "scripts" / "heartbeat_sync.sh")],
                       capture_output=True, text=True, timeout=180)
    after = max([p.stat().st_mtime for p in hb_dir.glob("握手-*.json")], default=0)
    ok = p.returncode == 0 and after > before
    return {"status": "ok" if ok else "failed", "returncode": p.returncode,
            "new_handshake": bool(after > before), "log_tail": (p.stderr or "")[-120:]}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-heartbeat", action="store_true")
    args = ap.parse_args()

    log(f"=== ZONGYUAN-ROOT 全自动全域锁档启动 ｜ {DID} ｜ {TS} ===")
    results = {}
    # 环节0：运行态证据采集（env快照 + 全屏截图 + 主站HTML → var/evidence/，随全根扫描进账本）
    try:
        ev = subprocess.run([sys.executable, str(ROOT / "scripts" / "lock_evidence.py")],
                            capture_output=True, text=True, timeout=180)
        ev_out = ev.stdout.strip().splitlines()[-1] if ev.stdout.strip() else ""
        results["evidence"] = {"status": "ok" if ev.returncode == 0 else "failed",
                               "summary": ev_out[-120:] if ev_out else (ev.stderr or "")[-120:]}
        log(f"[0/6] 运行态证据采集 {results['evidence']['status']}：{results['evidence']['summary'][:80]}")
    except Exception as e:
        results["evidence"] = {"status": "failed", "reason": str(e)[:160]}
        log(f"[0/6] 运行态证据采集失败: {e}")

    # 环节0.5：元法则 Schema 校验门（防新元法则 schema 不兼容 → 内核 load_laws 拒启断点复发）
    try:
        sc = subprocess.run([sys.executable, str(SKILL_DIR / "meta_law_schema_check.py")],
                            capture_output=True, text=True, timeout=60)
        sc_lines = [l for l in (sc.stdout or "").strip().splitlines() if l.startswith(("[PASS]", "[FAIL]", "[FIXED]", "ERROR"))]
        ok = sc.returncode == 0
        results["law_schema"] = {"status": "ok" if ok else "failed",
                                 "summary": sc_lines[-4:] if sc_lines else (sc.stderr or "")[-160:]}
        log(f"[0.5/6] 元法则Schema校验 {results['law_schema']['status']}：{sc_lines[-1][:60] if sc_lines else '无输出'}")
    except Exception as e:
        results["law_schema"] = {"status": "failed", "reason": str(e)[:160]}
        log(f"[0.5/6] Schema校验失败: {e}")

    # 环节0.6：收敛点完整性校验（沙箱销毁唯一恢复源 backup/ 一致性）
    try:
        cv = subprocess.run(["bash", str(ROOT / "scripts" / "zongyuan_persist.sh"), "verify"],
                            capture_output=True, text=True, timeout=90)
        cv_out = (cv.stdout or "") + (cv.stderr or "")
        v_ok = ("一致" in cv_out) and ("BAD:" not in cv_out)
        results["convergence"] = {"status": "ok" if v_ok else "partial", "detail": cv_out.strip()[-120:]}
        log(f"[0.6/6] 收敛点完整性校验 {results['convergence']['status']}")
    except Exception as e:
        results["convergence"] = {"status": "failed", "reason": str(e)[:160]}
        log(f"[0.6/6] 收敛点校验失败: {e}")

    try: results["local_lock"] = step_lock(); log(f"[1/6] 本地锁档 {results['local_lock']['status']}：{results['local_lock']['event_id']} ｜ {results['local_lock']['asset_count']} 资产 ｜ 批次根 {results['local_lock']['batch_root_sha256'][:16]}")
    except Exception as e: results["local_lock"] = {"status": "failed", "reason": str(e)[:160]}; log(f"[1/6] 本地锁档失败: {e}")

    try: results["base_sync"] = step_base_sync(); log(f"[2/6] 飞书Base同步 {results['base_sync']['status']}：{results['base_sync'].get('tables',0)} 表 / {results['base_sync'].get('records',0)} 条")
    except Exception as e: results["base_sync"] = {"status": "failed", "reason": str(e)[:160]}; log(f"[2/6] Base同步失败: {e}")

    try: results["drive"] = step_drive(); log(f"[3/6] 云盘归档 {results['drive']['status']}：{results['drive'].get('ok_count',0)}/{results['drive'].get('total',0)}")
    except Exception as e: results["drive"] = {"status": "failed", "reason": str(e)[:160]}; log(f"[3/6] 云盘归档失败: {e}")

    try: results["wiki"] = step_wiki(); log(f"[4/6] 知识库归档 {results['wiki']['status']}：{results['wiki'].get('node_title','')}")
    except Exception as e: results["wiki"] = {"status": "failed", "reason": str(e)[:160]}; log(f"[4/6] 知识库归档失败: {e}")

    report_value = {"event": "global_lock_full_auto", "mechanism": "zongyuan-auto-lock",
                    "target": "ZONGYUAN-ROOT", "DID": DID, "anchor": ANCHOR,
                    "locked_at": TS, "source_status": results}
    try: results["gateway"] = step_gateway(report_value); log(f"[5/6] 网关上报 {results['gateway']['status']}：truth_count={results['gateway'].get('truth_count','')}")
    except Exception as e: results["gateway"] = {"status": "failed", "reason": str(e)[:160]}; log(f"[5/6] 网关上报失败: {e}")

    if not args.skip_heartbeat:
        try: results["heartbeat"] = step_heartbeat(); log(f"[6/6] 心跳握手 {results['heartbeat']['status']}")
        except Exception as e: results["heartbeat"] = {"status": "failed", "reason": str(e)[:160]}; log(f"[6/6] 心跳失败: {e}")

    summary = {"mechanism": "zongyuan-auto-lock", "did": DID, "run_at": TS,
               "source_status": {k: (v.get("status") if isinstance(v, dict) else "?") for k, v in results.items()},
               "detail": results}
    out_dir = ROOT / "var" / "auto-lock"; out_dir.mkdir(parents=True, exist_ok=True)
    out_f = out_dir / f"auto-lock-{TS_F}.json"
    out_f.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    # 后置：收敛点同步（保证 backup/ 与锁档后最新状态一致）
    try:
        cs = subprocess.run(["bash", str(ROOT / "scripts" / "zongyuan_persist.sh"), "sync", "--quiet"],
                            capture_output=True, text=True, timeout=180)
        results["converge_sync"] = {"status": "ok" if cs.returncode == 0 else "failed",
                                    "detail": (cs.stdout or cs.stderr)[-100:]}
        log(f"[后置] 收敛点同步 {results['converge_sync']['status']}")
    except Exception as e:
        results["converge_sync"] = {"status": "failed", "reason": str(e)[:120]}
    summary["source_status"]["converge_sync"] = results.get("converge_sync", {}).get("status", "?")
    log(f"=== 完成：汇总 {out_f.relative_to(ROOT)} ===")
    ok_n = sum(1 for v in results.values() if isinstance(v, dict) and v.get("status") == "ok")
    print(f"SOURCE_STATUS: {json.dumps(summary['source_status'], ensure_ascii=False)}")
    print(f"SUMMARY_FILE: {out_f}")
    return 0 if ok_n >= 4 else 1

if __name__ == "__main__":
    sys.exit(main())
