#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT 多路径智能调度部署器 V1.0
================================================
核心能力：稳态探针 + 优先级降级 + 故障自动切换备用路径
- 对所有部署路径执行健康探针，刷新稳态状态表
- 从最高优先级路径开始，探针通过则部署；失败记录并切换下一备用
- 部署中失败自动切换备用；全部失败触发告警 + 回滚 + 故障台账
- 状态写入 shared_brain.db + 记忆网关
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
用法:
  python3 deploy_scheduler.py --dry-run          # 仅探针刷新状态，不部署
  python3 deploy_scheduler.py --deploy            # 执行多路径智能部署
  python3 deploy_scheduler.py --deploy --batch BATCH_ID   # 部署指定批次
"""
import json, os, subprocess, sys, time, sqlite3, shutil

BASE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE, "deploy_paths_config.json")
EXECUTORS = os.path.join(BASE, "executors")
DB_PATH = os.path.abspath(os.path.join(BASE, "..", "_shared_brain", "shared_brain.db"))
GATEWAY = "https://www.huodouai.com/api/report/truth"

def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)

def probe_path(path, cfg):
    """对单条路径执行健康探针，返回 (ok, detail, state)
    state: ready(可用) / config_pending(缺配置,跳过) / broken(故障)"""
    p = path.get("probe", {})
    # 环境变量探针：缺任一必需变量 → config_pending
    if p.get("type") == "env":
        missing = [v for v in p.get("vars", []) if not os.environ.get(v)]
        if missing:
            return False, f"缺配置: {','.join(missing)}", "config_pending"
        return True, "配置就绪", "ready"
    if p.get("type") == "http":
        import urllib.request, ssl
        try:
            req = urllib.request.Request(p["url"], method="GET")
            ctx = ssl.create_default_context()
            r = urllib.request.urlopen(req, context=ctx, timeout=p.get("timeout", 10))
            code = r.getcode()
            ok = code in (200, 302, 301)
            return ok, f"HTTP {code}", ("ready" if ok else "broken")
        except Exception as e:
            return False, f"HTTP异常 {str(e)[:50]}", "broken"
    if p.get("type") == "command":
        cmd = [p["cmd"]] + p.get("args", [])
        # GIT_REMOTE_URL 解析: env 优先, 否则读配置 global.git_remote_url
        git_url = os.environ.get("GIT_REMOTE_URL") or (cfg.get("global") or {}).get("git_remote_url")
        cmd = [git_url if c == "GIT_REMOTE_URL" else c for c in cmd]
        if not git_url:
            return False, "缺配置: GIT_REMOTE_URL", "config_pending"
        try:
            r = subprocess.run(cmd, capture_output=True, timeout=p.get("timeout", 15))
            return r.returncode == 0, f"cmd rc={r.returncode}", ("ready" if r.returncode==0 else "broken")
        except Exception as e:
            return False, f"cmd异常 {str(e)[:50]}", "broken"
    return False, "未知探针类型", "broken"

def refresh_path_status(cfg):
    """刷新所有路径稳态状态，返回状态表；disabled 路径标记为停用"""
    status = []
    for p in cfg["paths"]:
        if p.get("status") == "disabled":
            status.append({"id": p["id"], "name": p["name"], "priority": p["priority"],
                           "role": p["role"], "ok": False, "detail": "停用(付费/禁用)", "state": "disabled"})
            continue
        ok, detail, state = probe_path(p, cfg)
        status.append({"id": p["id"], "name": p["name"], "priority": p["priority"],
                       "role": p["role"], "ok": ok, "detail": detail, "state": state})
    return status

def run_executor(script, extra_args=()):
    """执行部署算子脚本，返回 (ok, output)"""
    path = os.path.join(EXECUTORS, script)
    if not os.path.exists(path):
        return False, f"执行器不存在: {script}"
    cmd = ["bash", path] + list(extra_args)
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=1200)
        out = (r.stdout + r.stderr).decode("utf-8", "ignore")[-800:]
        return r.returncode == 0, out
    except Exception as e:
        return False, f"执行异常 {str(e)[:80]}"

def record_db(path_id, ok, detail, batch_id):
    """写入 shared_brain.db 部署状态"""
    try:
        con = sqlite3.connect(DB_PATH)
        con.execute("""CREATE TABLE IF NOT EXISTS deploy_log(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT, path_id TEXT, batch_id TEXT, ok INTEGER, detail TEXT)""")
        con.execute("INSERT INTO deploy_log(ts,path_id,batch_id,ok,detail) VALUES(?,?,?,?,?)",
                    (time.strftime("%Y-%m-%d %H:%M:%S"), path_id, batch_id, 1 if ok else 0, detail))
        con.commit()
        con.close()
        return True
    except Exception as e:
        return False

def report_gateway(ok, path_id, detail, batch_id):
    """上报记忆网关"""
    try:
        import urllib.request
        payload = json.dumps({
            "event": "multi_path_deploy",
            "path_id": path_id, "batch_id": batch_id,
            "ok": bool(ok), "detail": detail[:500],
            "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
            "did": "DID-BR-000002", "trace": "Ω₀⊂⊙∞⊂Ω"
        }, ensure_ascii=False)
        body = json.dumps({"truth_value": payload, "truth_type": "protocol"}, ensure_ascii=False).encode()
        req = urllib.request.Request(GATEWAY, data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read()).get("success")
    except Exception:
        return False

def main():
    args = sys.argv[1:]
    cfg = load_config()
    dry = "--dry-run" in args
    deploy = "--deploy" in args
    batch = "--batch" in args
    batch_id = args[args.index("--batch")+1] if batch else "TEST-001"

    print(f"═══ 多路径智能调度部署 | {time.strftime('%Y-%m-%d %H:%M:%S')} ═══")
    print(f"模式: {'DRY-RUN(仅探针)' if dry else 'DEPLOY'} | 批次: {batch_id}\n")

    # 1. 全路径探针刷新稳态
    print("── 全路径健康探针 ──")
    status = refresh_path_status(cfg)
    marks = {"ready": "✅ 可用", "broken": "❌ 故障", "config_pending": "⏸ 未就绪", "disabled": "🚫 停用"}
    for s in sorted(status, key=lambda x: x["priority"]):
        print(f"  [P{s['priority']}] {s['name']:<14} {marks.get(s['state'],'❓')}  ({s['detail']})")
    ok_paths = [s for s in status if s["ok"]]
    print(f"  可用路径: {len(ok_paths)} / {len(status)}"
          + (f" | 未就绪 {sum(1 for s in status if s['state']=='config_pending')}"
             if any(s["state"]=='config_pending' for s in status) else "") + "\n")

    if dry:
        print("DRY-RUN 完成，未执行部署。")
        return 0

    # 2. 按优先级降级执行
    print("── 智能调度(优先级降级+故障切换) ──")
    deployed = False
    for s in sorted(status, key=lambda x: x["priority"]):
        p = next(x for x in cfg["paths"] if x["id"] == s["id"])
        if not s["ok"]:
            print(f"  [P{s['priority']}] {s['name']} 探针故障，跳过 → 尝试备用")
            record_db(s["id"], False, "探针故障", batch_id)
            continue
        print(f"  [P{s['priority']}] {s['name']} 探针通过，执行部署...")
        ok, out = run_executor(p["deploy"]["cmd"], (batch_id,))
        if ok:
            print(f"      ✅ 部署成功 via {s['name']}")
            record_db(s["id"], True, "部署成功", batch_id)
            report_gateway(True, s["id"], "部署成功", batch_id)
            deployed = True
            break
        else:
            print(f"      ❌ 部署失败: {out[-120:]} → 尝试备用路径")
            record_db(s["id"], False, "部署失败:"+out[-100:], batch_id)

    # 3. 全部失败处理
    if not deployed:
        print("\n⚠️ 所有部署路径均失败，触发: 告警 + 回滚 + 故障台账")
        rb = run_executor("rollback_common.sh", (batch_id,))
        print(f"  回滚执行: {'✅' if rb[0] else '❌ ' + rb[1][-100:]}")
        report_gateway(False, "all_failed", "全路径失败已回滚", batch_id)
        return 1

    print("\n✅ 多路径部署闭环完成。")
    return 0

if __name__ == "__main__":
    sys.exit(main())
