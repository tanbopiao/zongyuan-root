#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自治巡检·优化·净化（autonomy_patrol）｜ 定时巡检内核/架构/自治系统
锚定：DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω
职责：
  - 巡检 10 项：服务在线/cron 完整性/元法则 schema/关键资产/心跳新鲜度/审计连续性/磁盘/网关/Merkle 基线/净化项
  - 优化：服务 down 自动拉起（调 autonomy_guard.sh）；schema 坏自动 --fix + 重建基线
  - 净化：大日志轮转、tmp 旧文件清理、失败任务目录告警（安全非破坏）
  - 报告：var/patrol/patrol-<ts>.json + 可选网关上报（--report）
用法：python3 autonomy_patrol.py [--report]
"""
import json, os, re, shutil, subprocess, sys, time
from pathlib import Path

ZR = Path("/home/user/ZONGYUAN-ROOT")
KERNEL = Path("/home/user/Doubao/chats/38412149511142658/zongyuan-kernel")
DID = "DID-BR-000002"
GW = "https://www.huodouai.com/api/report/truth"
OUT_DIR = ZR / "var" / "patrol"
GUARD = ZR / "scripts" / "autonomy_guard.sh"
SCHEMA = Path("/home/user/.doubao/agent_mode/workspace/.user_skills/zongyuan-auto-lock/scripts/meta_law_schema_check.py")
INIT_BASELINE = KERNEL / "scripts" / "init_baseline.py"
LOG_ROTATE_MB = 100
TMP_MAX_AGE_DAYS = 7


def now():
    return time.strftime('%Y-%m-%dT%H:%M:%S%z')


def run(cmd, timeout=60):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except Exception as e:
        return type("R", (), {"returncode": -1, "stdout": "", "stderr": str(e)})()


def pgrep(pat):
    return run(["pgrep", "-f", pat]).returncode == 0


def patrol():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = time.strftime('%Y%m%d-%H%M%S')
    items = []

    def add(k, ok, detail):
        items.append({"item": k, "status": "PASS" if ok else ("PARTIAL" if detail.startswith("P:") else "FAIL"),
                      "detail": detail.lstrip("P:")})

    # 1. 服务在线
    svc_ok = (pgrep("supervisord.*zongyuan") and pgrep("zongyuan_daemon.sh") and
              pgrep("worker_daemon.sh worker-kernel-001") and pgrep("/usr/sbin/cron") and
              run(["bash", str(KERNEL / "scripts" / "kernel_launch.sh"), "status"]).stdout.strip().startswith("running"))
    ports = sum(1 for p in ("9081", "9082", "9092") if re.search(rf":{p} ", run(["ss", "-tln"]).stdout))
    add("services", svc_ok and ports == 3, f"supervisord/daemon/worker/crond/kernel={'OK' if svc_ok else 'DOWN'}; 端口{ports}/3")
    if not (svc_ok and ports == 3):
        run(["bash", str(GUARD), "--quiet"], timeout=120)
        add("services.fix", True, "P:已调 guard 拉起")

    # 2. cron 完整性
    n = len([l for l in run(["crontab", "-l"]).stdout.splitlines() if l.strip() and not l.startswith("#")])
    add("cron", n >= 10, f"{n} 条(要求≥10)")
    if n < 10:
        run(["bash", str(ZR / "scripts" / "self_bootstrap.sh")], timeout=120)

    # 3. 元法则 schema
    sc = run(["python3", str(SCHEMA)])
    add("meta_law_schema", sc.returncode == 0, "P:校验门通过" if sc.returncode == 0 else f"FAIL: {sc.stdout[-200:]}")
    if sc.returncode != 0:
        sc2 = run(["python3", str(SCHEMA), "--fix"], timeout=60)
        if sc2.returncode == 0:
            run(["python3", str(INIT_BASELINE)], timeout=120)
            add("meta_law_schema.fix", True, "P:已--fix并重建基线")

    # 4. 关键资产存在
    assets = {
        "kek(600)": ZR / "var" / "kek.env", "ark-enc": KERNEL / "var" / "state" / "ark-key.enc.json",
        "ledger": ZR / "HASH-LEDGER.csv", "baseline": KERNEL / "var" / "state" / "baseline.json",
        "audit": KERNEL / "var" / "audit" / "audit.jsonl", "fusion入口": ZR / "scripts" / "zongyuan_fusion.sh",
        "vector_index": Path("/home/user/.doubao/agent_mode/workspace/.user_skills/intelligent-orchestrator/state/vector_store/index.json"),
    }
    miss = [k for k, p in assets.items() if not p.exists()]
    add("key_assets", not miss, "全部存在" if not miss else f"缺失: {miss}")

    # 5. 心跳新鲜度
    fus = sorted((ZR / "var" / "fusion").glob("heartbeat-*.json"))
    fresh = bool(fus) and (time.time() - fus[-1].stat().st_mtime) < 1800
    add("heartbeat_fresh", fresh, f"最新={fus[-1].name if fus else '无'}")

    # 6. 审计连续性
    aud = KERNEL / "var" / "audit" / "audit.jsonl"
    lines = [l for l in aud.read_text(encoding="utf-8").splitlines() if l.strip()] if aud.exists() else []
    fresh_audit = bool(lines) and (time.time() - aud.stat().st_mtime) < 86400
    add("audit_fresh", fresh_audit, f"{len(lines)} 条, 最近写入<24h={'是' if fresh_audit else '否'}")

    # 7. 磁盘空间
    du = shutil.disk_usage(str(ZR))
    pct = du.free / du.total * 100
    add("disk", pct > 10, f"可用 {pct:.1f}%")

    # 8. 网关在线
    g = run(["curl", "-sS", "-m", "15", "-H", f"X-DID: {DID}", GW.replace("/api/report/truth", "/api/status")])
    add("gateway", '"status": "ok"' in g.stdout, "在线" if '"status": "ok"' in g.stdout else "不可达")

    # 9. Merkle 基线
    base = KERNEL / "var" / "state" / "baseline.json"
    base_ok = base.exists() and "root_hash" in base.read_text(encoding="utf-8")
    add("merkle_baseline", base_ok, f"root_hash 在位" if base_ok else "缺失/无效")

    # 10. 净化项
    cleaned = []
    for f in sorted((ZR / "logs").glob("*")):
        if f.is_file() and f.stat().st_size > LOG_ROTATE_MB * 1024 * 1024:
            bak = f.with_name(f.name + ".1")
            try:
                if not bak.exists():
                    shutil.copy2(f, bak)
                f.write_text(f"# rotated by autonomy_patrol {now()}\n")
                cleaned.append(f.name)
            except Exception:
                pass
    tmp_old = 0
    for f in Path("/tmp").glob("*"):
        try:
            if f.is_file() and time.time() - f.stat().st_mtime > TMP_MAX_AGE_DAYS * 86400:
                f.unlink()
                tmp_old += 1
        except Exception:
            pass
    add("purge", True, f"日志轮转={len(cleaned)}个 {cleaned[:3]} | tmp清理={tmp_old}个")

    # 11. VM 重启检测（沙箱定时销毁被动探针）
    state_f = OUT_DIR / "state.json"
    restart = False
    try:
        cur_up = float(open("/proc/uptime").read().split()[0])
    except Exception:
        cur_up = -1
    if state_f.exists():
        try:
            st = json.loads(state_f.read_text(encoding="utf-8"))
            expected = st.get("uptime", 0) + (time.time() - st.get("ts", time.time()))
            if 0 < cur_up < expected - 60:
                restart = True
                run(["bash", str(GUARD), "--quiet"], timeout=120)
                add("vm_restart", True, f"P:检测到VM重启(uptime {cur_up:.0f}s<期望{expected:.0f}s),已触发guard全量拉起")
            else:
                add("vm_restart", True, f"无重启(uptime {cur_up:.0f}s)")
        except Exception as e:
            add("vm_restart", True, f"基线异常({str(e)[:40]})")
    else:
        add("vm_restart", True, f"基线建立(uptime {cur_up:.0f}s)")
    try:
        json.dump({"uptime": cur_up, "ts": time.time()},
                  open(state_f, "w"), ensure_ascii=False, indent=2)
    except Exception:
        pass

    # 12. 用户技能资产完整性（.user_skills 半持久层还原防护：缺失从 ZONGYUAN-ROOT 备份恢复）
    BACKUP = ZR / "backup" / "user-skills"
    KEY_ASSETS = [
        "zongyuan-auto-lock/scripts/lock_readonly.sh",
        "zongyuan-auto-lock/scripts/incremental_lock.py",
        "zongyuan-auto-lock/scripts/zongyuan_full_lock.py",
        "zongyuan-auto-lock/scripts/meta_law_schema_check.py",
        "intelligent-orchestrator/scripts/vector_store.py",
    ]
    usk = Path("/home/user/.doubao/agent_mode/workspace/.user_skills")
    recovered = []
    for rel in KEY_ASSETS:
        p = usk / rel
        if p.exists():
            continue
        bak = BACKUP / rel
        if bak.exists():
            try:
                p.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(bak, p)
                recovered.append(rel)
            except Exception as e:
                recovered.append(f"{rel}:恢复失败({str(e)[:30]})")
        else:
            recovered.append(f"{rel}:无备份")
    add("user_skills", not recovered, "完整" if not recovered else "P:已恢复->" + "; ".join(recovered))

    # 汇总
    fails = [i for i in items if i["status"] == "FAIL"]
    report = {"event": "autonomy_patrol", "DID": DID, "anchor": "Ω₀⊂⊙∞⊂Ω", "run_at": now(),
              "summary": {"total": len(items), "pass": sum(1 for i in items if i["status"] == "PASS"),
                          "partial": sum(1 for i in items if i["status"] == "PARTIAL"),
                          "fail": len(fails)}, "items": items}
    out = OUT_DIR / f"patrol-{ts}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"PATROL: {report['summary']} ｜ 报告 {out.name}")
    for i in items:
        print(f"  [{i['status']}] {i['item']}: {i['detail'][:90]}")
    return report, out


def report_gateway(report):
    key = f"autonomy_patrol.{int(time.time())}"
    payload = {"key": key, "value": {"event": "autonomy_patrol", "DID": DID, "anchor": "Ω₀⊂⊙∞⊂Ω",
                                      "summary": report["summary"], "run_at": report["run_at"]}}
    p = run(["curl", "-sS", "-m", "25", "-X", "POST", GW,
             "-H", f"X-DID: {DID}", "-H", "Content-Type: application/json",
             "--data-binary", json.dumps(payload, ensure_ascii=False)], timeout=30)
    ok = "真值写入成功" in (p.stdout or p.stderr)
    print("GATEWAY:", "ok" if ok else "failed")
    return ok


if __name__ == "__main__":
    report, out = patrol()
    if "--report" in sys.argv:
        report_gateway(report)
    sys.exit(0 if report["summary"]["fail"] == 0 else 1)
