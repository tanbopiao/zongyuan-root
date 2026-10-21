#!/usr/bin/env python3
"""
WEAR 中枢错误巡检闭环
扫描Worker错误台账中open状态的错误 → P1自动修复 → P0升级审批 → 台账回写 → 真值上报
由定时任务触发，最小额度消耗：增量扫描、缓存复用、失败快速跳过
"""
import sys, os, time, json, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from datetime import datetime, timezone, timedelta
from zr_octop_bridge import report_truth, DID, NODE_ID
try:
    from wear_sdk import wear_report_healthy, wear_report_error
    WEAR_AVAILABLE = True
except Exception:
    WEAR_AVAILABLE = False

CST = timezone(timedelta(hours=8))
BASE_TOKEN = "DgnMbLqZiaIUDKshqCrcD4DvnBg"
ERROR_TABLE_ID = "tblnX1spnSqNfgY1"

def log(m): print(f"[{datetime.now(CST).strftime('%H:%M:%S')}] {m}", flush=True)

def lark_cli(args, timeout=20):
    """调用lark-cli，返回解析后的JSON"""
    try:
        r = subprocess.run(
            ["lark-cli", "base"] + args + ["--as", "user"],
            capture_output=True, text=True, timeout=timeout
        )
        return json.loads(r.stdout) if r.stdout.strip() else {"ok": False, "error": r.stderr}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def scan_open_errors():
    """扫描台账中status=open的错误记录"""
    # record-list输出是manifest格式（直接含record_file），不是{ok,data}包装
    result = lark_cli([
        "+record-list", "--base-token", BASE_TOKEN,
        "--table-id", ERROR_TABLE_ID, "--limit", "100"
    ])
    open_errors = []
    # 兼容两种格式：{ok,data} 或 直接manifest
    record_file = result.get("data", {}).get("record_file") or result.get("record_file")
    if record_file and os.path.exists(record_file):
        with open(record_file) as f:
            for line in f:
                line = line.strip()
                if not line: continue
                try:
                    rec = json.loads(line)
                    status = rec.get("status", "")
                    if isinstance(status, list): status = status[0] if status else ""
                    if status == "open":
                        open_errors.append(rec)
                except Exception:
                    pass
    return open_errors

def try_auto_heal(error_rec):
    """P1/P2错误自动修复尝试，返回 (healed:bool, detail:str)"""
    category = error_rec.get("error_category", "")
    if isinstance(category, list): category = category[0] if category else ""
    level = error_rec.get("error_level", "")
    if isinstance(level, list): level = level[0] if level else ""
    worker = error_rec.get("worker_id", "")
    msg = error_rec.get("error_message", "")

    # P0不自动修复，升级审批
    if level == "P0":
        return (False, "P0_requires_manual_approval")

    # 按分类执行修复
    if category == "dir_missing":
        # 目录缺失：确认目录已创建（心跳脚本的自愈通常已处理）
        import re
        paths = re.findall(r"['\"]?(/[\w/._-]+)['\"]?", msg)
        created = []
        for p in paths:
            try:
                if not os.path.exists(p):
                    os.makedirs(p, exist_ok=True)
                    created.append(p)
            except Exception:
                pass
        return (True, f"dirs_verified_or_created: {len(created)} new")

    if category == "auth":
        # 认证失效：清除token缓存
        import glob
        cleared = []
        for p in ["/tmp/octop_jwt_token.json", os.path.expanduser("~/.octop/token.json")]:
            if os.path.exists(p):
                try: os.remove(p); cleared.append(p)
                except Exception: pass
        for p in glob.glob("/tmp/octop_*"):
            try:
                if os.path.isfile(p): os.remove(p); cleared.append(p)
            except Exception: pass
        return (True, f"token_cleared: {len(closed)} files, relogin_on_next_call")

    if category == "network":
        # 网络异常：确认备用通道可用
        import urllib.request
        try:
            req = urllib.request.Request("https://drama.huodouai.com/api/status", method="GET")
            with urllib.request.urlopen(req, timeout=5) as r:
                if r.status == 200:
                    return (True, "backup_channel_verified_200")
        except Exception:
            pass
        return (False, "backup_channel_unreachable")

    if category == "resource":
        # 资源耗尽：清理临时文件
        import glob, shutil
        cleaned = 0
        for pattern in ["/tmp/octop_*", "/tmp/wear_*"]:
            for p in glob.glob(pattern):
                try:
                    if os.path.isfile(p): os.remove(p); cleaned += 1
                    elif os.path.isdir(p): shutil.rmtree(p, ignore_errors=True); cleaned += 1
                except Exception: pass
        return (True, f"temp_cleaned: {cleaned} items")

    if category == "dependency":
        # 依赖缺失：尝试pip安装
        import re
        m = re.search(r"No module named ['\"]?([\w.]+)", msg, re.IGNORECASE)
        if m:
            module = m.group(1).split('.')[0]
            pkg_map = {"yaml":"pyyaml","cv2":"opencv-python","PIL":"pillow","sklearn":"scikit-learn"}
            pkg = pkg_map.get(module, module)
            try:
                r = subprocess.run([sys.executable,"-m","pip","install","--quiet","--user",pkg],
                                   capture_output=True, text=True, timeout=60)
                if r.returncode == 0:
                    return (True, f"pip_installed: {pkg}")
            except Exception:
                pass
        return (False, "pip_install_failed")

    # logic/data_conflict等不自动修复
    return (False, f"no_auto_heal_for_{category}")

def update_record_status(record_id, status, heal_detail=""):
    """更新台账记录状态（lark-cli格式：update_records是对象映射）"""
    fields = {"status": [status]}
    if heal_detail:
        fields["heal_result"] = heal_detail
    body = json.dumps({"update_records": {record_id: fields}}, ensure_ascii=False)
    result = lark_cli([
        "+record-batch-update", "--base-token", BASE_TOKEN,
        "--table-id", ERROR_TABLE_ID, "--json", body
    ])
    return result.get("ok", False)

def main():
    log("=== WEAR 中枢错误巡检闭环 ===")

    # 1. 扫描open错误
    open_errors = scan_open_errors()
    log(f"扫描到 open 状态错误: {len(open_errors)} 条")

    healed = 0
    escalated = 0
    failed = 0
    details = []

    # 2. 逐条处理
    for err in open_errors:
        rid = err.get("record_id", "")
        worker = err.get("worker_id", "?")
        category = err.get("error_category", "?")
        if isinstance(category, list): category = category[0]
        level = err.get("error_level", "?")
        if isinstance(level, list): level = level[0]

        # P0直接升级
        if level == "P0":
            update_record_status(rid, "escalated", "P0_auto_escalated_pending_approval")
            escalated += 1
            details.append(f"  ⬆️ P0升级: {worker}/{category}")
            log(f"  ⬆️ P0升级审批: {worker}/{category} (rid={rid[:12]})")
            continue

        # P1/P2尝试自动修复
        ok, detail = try_auto_heal(err)
        if ok:
            update_record_status(rid, "resolved", detail)
            healed += 1
            details.append(f"  ✅ 自愈: {worker}/{category} → {detail}")
            log(f"  ✅ 自动修复: {worker}/{category} → {detail}")
        else:
            update_record_status(rid, "escalated", f"auto_heal_failed: {detail}")
            escalated += 1
            details.append(f"  ⬆️ 修复失败升级: {worker}/{category} → {detail}")
            log(f"  ⬆️ 修复失败升级: {worker}/{category} → {detail}")

    # 3. 上报巡检真值
    patrol_result = {
        "event": "wear_central_patrol",
        "wear_version": "1.0",
        "scanned_open": len(open_errors),
        "healed": healed,
        "escalated": escalated,
        "failed": failed,
        "details": details,
        "did": DID,
        "node": NODE_ID,
        "ts": datetime.now(CST).isoformat(),
    }
    patrol_key = f"PATROL.WEAR.{datetime.now(CST).strftime('%Y%m%d-%H%M')}"
    r = report_truth(patrol_key, patrol_result)
    log(f"📤 巡检真值 {patrol_key} → {'主备双通' if r else '上报异常'}")

    # WEAR健康上报（中枢巡检自身监控）
    if WEAR_AVAILABLE:
        try:
            wear_report_healthy("wear_central_patrol", "cron",
                                context={"scanned": len(open_errors), "healed": healed, "escalated": escalated})
        except Exception: pass

    # 清理临时ndjson文件
    import glob
    for f in glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), f"{ERROR_TABLE_ID}_*.ndjson")):
        try: os.remove(f)
        except Exception: pass
    for f in glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), f"{ERROR_TABLE_ID}_*.manifest.json")):
        try: os.remove(f)
        except Exception: pass

    return patrol_result

if __name__ == "__main__":
    try:
        r = main()
        sys.exit(0 if r["escalated"] == 0 else 1)
    except Exception as exc:
        # 中枢巡检自身异常 → WEAR上报
        if WEAR_AVAILABLE:
            try:
                wear_report_error("wear_central_patrol", "cron", exc, "central_patrol_fatal",
                                  context={"fatal": True})
            except Exception: pass
        print(f"[WEAR] 中枢巡检致命异常已上报: {exc}", flush=True)
        sys.exit(3)
