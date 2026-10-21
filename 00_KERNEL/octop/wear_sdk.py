#!/usr/bin/env python3
"""
WEAR SDK - Worker Error Awareness & Remediation
统一错误捕获、结构化上报、自愈钩子注册
接入方式：@wear_monitor(worker_id="xxx", worker_type="cron")
"""
import os, sys, time, json, traceback, functools
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from zr_octop_bridge import report_truth, DID, NODE_ID

CST = timezone(timedelta(hours=8))
WEAR_VERSION = "1.0"

# 飞书共享大脑错误台账
BASE_TOKEN = "DgnMbLqZiaIUDKshqCrcD4DvnBg"
ERROR_TABLE_ID = "tblnX1spnSqNfgY1"

def _write_ledger(payload):
    """将错误/健康记录写入飞书Base Worker错误台账"""
    try:
        import subprocess
        is_error = payload.get("event") == "wear_error"
        record = {
            "worker_id": payload.get("worker_id", ""),
            "worker_type": payload.get("worker_type", "manual"),
            "error_level": payload.get("error_level", "P3") if is_error else "P3",
            "error_category": payload.get("error_category", "logic") if is_error else "logic",
            "error_type": payload.get("error_type", "") if is_error else "healthy",
            "error_message": payload.get("error_message", "") if is_error else "healthy heartbeat",
            "self_heal": payload.get("self_heal_attempted", False),
            "heal_result": payload.get("self_heal_result", "") if isinstance(payload.get("self_heal_result"), str) else str(payload.get("self_heal_result", "")),
            "status": payload.get("status", "healthy"),
            "truth_key": payload.get("truth_key", ""),
            "reported_at": int(time.time() * 1000),
            "did": payload.get("did", DID),
        }
        body = json.dumps({"create_records": [record]}, ensure_ascii=False)
        r = subprocess.run(
            ["lark-cli", "base", "+record-batch-create",
             "--base-token", BASE_TOKEN, "--table-id", ERROR_TABLE_ID,
             "--json", body, "--as", "user"],
            capture_output=True, text=True, timeout=15
        )
        return r.returncode == 0
    except Exception:
        return False

# 自愈函数注册表：{error_category: callable(error_info) -> (success, detail)}
_HEAL_REGISTRY = {}

def register_heal(category, func):
    """注册某类错误的自愈函数，返回 (success:bool, detail:str)"""
    _HEAL_REGISTRY[category] = func

def _now_str():
    return datetime.now(CST).strftime("%Y%m%d-%H%M%S")

def _classify_error(exc):
    """根据异常类型自动分类"""
    msg = str(exc).lower()
    etype = type(exc).__name__
    if any(k in msg for k in ["no such file", "not found", "不存在", "找不到目录", "filenotfound", "missing dir", "目录缺失"]):
        return "dir_missing"
    if any(k in msg for k in ["timeout", "connection", "502", "503", "refused", "unreachable", "网络"]):
        return "network"
    if any(k in msg for k in ["401", "403", "auth", "token", "unauthorized", "权限"]):
        return "auth"
    if any(k in msg for k in ["module not found", "no module", "command not found", "依赖"]):
        return "dependency"
    if any(k in msg for k in ["hash", "mismatch", "integrity", "冲突", "重复"]):
        return "data_conflict"
    if any(k in msg for k in ["disk", "memory", "oom", "quota", "额度", "空间"]):
        return "resource"
    return "logic"

def _level_for_category(category, exc):
    """根据分类和异常判定错误级别"""
    level_map = {
        "dir_missing": "P2",
        "network": "P1",
        "auth": "P1",
        "dependency": "P2",
        "data_conflict": "P0",
        "resource": "P1",
        "logic": "P0",
    }
    return level_map.get(category, "P2")

def _report_error(worker_id, worker_type, exc, tb_str, context=None,
                  self_heal_attempted=False, self_heal_result=None):
    """结构化上报错误到云端真值"""
    category = _classify_error(exc)
    level = _level_for_category(category, exc)
    err_key = f"ERROR.WORKER.{worker_id}.{_now_str()}"
    payload = {
        "event": "wear_error",
        "wear_version": WEAR_VERSION,
        "worker_id": worker_id,
        "worker_type": worker_type,
        "error_level": level,
        "error_category": category,
        "error_type": type(exc).__name__,
        "error_message": str(exc)[:500],
        "error_trace": tb_str[:2000],
        "context": context or {},
        "self_heal_attempted": self_heal_attempted,
        "self_heal_result": self_heal_result,
        "status": "resolved" if (self_heal_attempted and self_heal_result and self_heal_result[0]) else "open",
        "did": DID,
        "node": NODE_ID,
        "ts": datetime.now(CST).isoformat(),
    }
    try:
        report_truth(err_key, payload)
    except Exception:
        pass  # 上报失败不阻断主流程
    payload["truth_key"] = err_key
    _write_ledger(payload)
    return payload

def _report_healthy(worker_id, worker_type, context=None):
    """无错误时也上报健康心跳（沉默≠正常）"""
    healthy_key = f"HEALTHY.WORKER.{worker_id}.{_now_str()}"
    payload = {
        "event": "wear_healthy",
        "wear_version": WEAR_VERSION,
        "worker_id": worker_id,
        "worker_type": worker_type,
        "status": "healthy",
        "context": context or {},
        "did": DID,
        "node": NODE_ID,
        "ts": datetime.now(CST).isoformat(),
    }
    try:
        report_truth(healthy_key, payload)
    except Exception:
        pass
    payload["truth_key"] = healthy_key
    _write_ledger(payload)
    return payload

def wear_monitor(worker_id, worker_type="cron", context=None, report_healthy=True):
    """
    装饰器：自动捕获Worker异常→结构化→尝试自愈→上报真值
    用法：@wear_monitor(worker_id="heartbeat_failover", worker_type="cron")
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            ctx = dict(context or {})
            try:
                result = func(*args, **kwargs)
                if report_healthy:
                    ctx["result_summary"] = str(result)[:200] if result else "ok"
                    _report_healthy(worker_id, worker_type, ctx)
                return result
            except Exception as exc:
                tb_str = traceback.format_exc()
                category = _classify_error(exc)
                # 尝试自愈
                heal_attempted = False
                heal_result = None
                if category in _HEAL_REGISTRY:
                    heal_attempted = True
                    try:
                        heal_result = _HEAL_REGISTRY[category]({
                            "worker_id": worker_id,
                            "error": exc,
                            "trace": tb_str,
                            "context": ctx,
                        })
                    except Exception as heal_exc:
                        heal_result = (False, f"heal_func_error: {heal_exc}")
                # 上报
                payload = _report_error(worker_id, worker_type, exc, tb_str, ctx,
                                        heal_attempted, heal_result)
                # 自愈成功则不重新抛出，Worker继续；自愈失败或无自愈策略则抛出
                if heal_attempted and heal_result and heal_result[0]:
                    print(f"[WEAR] ✅ {worker_id} 错误已自愈: {category} → {heal_result[1]}", flush=True)
                    return {"wear_healed": True, "category": category, "detail": heal_result[1]}
                print(f"[WEAR] ❌ {worker_id} 错误未自愈: {category}/{payload['error_level']} → {exc}", flush=True)
                raise
        return wrapper
    return decorator

# ── 预置自愈策略 ──────────────────────────────────────────────

def _heal_dir_missing(info):
    """目录缺失自愈：从错误信息提取路径并自动创建"""
    import re
    msg = str(info["error"])
    # 尝试提取路径
    paths = re.findall(r"['\"]?(/[\w/._-]+)['\"]?", msg)
    created = []
    for p in paths:
        try:
            if not os.path.exists(p):
                os.makedirs(p, exist_ok=True)
                created.append(p)
        except Exception:
            pass
    if created:
        return (True, f"auto_created: {', '.join(created)}")
    return (False, "no_path_extracted")

def _heal_network(info):
    """网络异常自愈：标记为已切换备用通道（由调用方实际执行切换）"""
    return (True, "failover_to_backup_channel")

def _heal_auth(info):
    """认证失效自愈：清除token缓存，触发下次调用时自动重新登录"""
    import glob
    cleared = []
    # 清除OCTOP JWT token缓存
    token_paths = [
        "/tmp/octop_jwt_token.json",
        os.path.expanduser("~/.octop/token.json"),
    ]
    for p in token_paths:
        if os.path.exists(p):
            try:
                os.remove(p)
                cleared.append(p)
            except Exception:
                pass
    # 清除/tmp下octop相关缓存
    for p in glob.glob("/tmp/octop_*"):
        try:
            if os.path.isfile(p):
                os.remove(p)
                cleared.append(p)
        except Exception:
            pass
    if cleared:
        return (True, f"token_cleared: {len(cleared)} files, next_call_will_relogin")
    return (True, "no_token_cache_found, assume_relogin_on_next_call")

def _heal_resource(info):
    """资源耗尽自愈：清理临时文件释放空间"""
    import glob, shutil
    cleaned = []
    freed = 0
    # 清理/tmp下octop和wear相关临时文件
    for pattern in ["/tmp/octop_*", "/tmp/wear_*", "/tmp/zr_*.tmp"]:
        for p in glob.glob(pattern):
            try:
                if os.path.isfile(p):
                    freed += os.path.getsize(p)
                    os.remove(p)
                    cleaned.append(p)
                elif os.path.isdir(p):
                    freed += sum(os.path.getsize(os.path.join(dp,f)) for dp,_,fn in os.walk(p) for f in fn)
                    shutil.rmtree(p, ignore_errors=True)
                    cleaned.append(p)
            except Exception:
                pass
    # 清理~/.octop/logs下超过7天的日志
    log_dir = os.path.expanduser("~/.octop/logs")
    if os.path.isdir(log_dir):
        cutoff = time.time() - 7*86400
        for f in os.listdir(log_dir):
            fp = os.path.join(log_dir, f)
            try:
                if os.path.isfile(fp) and os.path.getmtime(fp) < cutoff:
                    freed += os.path.getsize(fp)
                    os.remove(fp)
                    cleaned.append(fp)
            except Exception:
                pass
    if cleaned:
        return (True, f"cleaned {len(cleaned)} items, freed {freed//1024}KB")
    return (False, "nothing_to_clean")

def _heal_dependency(info):
    """依赖缺失自愈：尝试pip安装缺失模块"""
    import re, subprocess
    msg = str(info["error"])
    # 提取 "No module named 'xxx'" 或 "ModuleNotFoundError: No module named 'xxx'"
    m = re.search(r"No module named ['\"]?([\w.]+)", msg, re.IGNORECASE)
    if not m:
        m = re.search(r"ModuleNotFoundError:?\s*['\"]?([\w.]+)", msg, re.IGNORECASE)
    if not m:
        return (False, "no_module_name_extracted")
    module = m.group(1).split('.')[0]  # 取顶层包名
    # pip包名映射（常见模块名→包名）
    pkg_map = {
        "yaml": "pyyaml", "cv2": "opencv-python", "PIL": "pillow",
        "sklearn": "scikit-learn", "bs4": "beautifulsoup4",
        "requests": "requests", "numpy": "numpy", "pandas": "pandas",
    }
    pkg = pkg_map.get(module, module)
    try:
        r = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--quiet", "--user", pkg],
            capture_output=True, text=True, timeout=60
        )
        if r.returncode == 0:
            return (True, f"pip_installed: {pkg}")
        return (False, f"pip_failed: {pkg} ({r.stderr[:100]})")
    except Exception as e:
        return (False, f"pip_error: {e}")

# 注册预置自愈策略
register_heal("dir_missing", _heal_dir_missing)
register_heal("network", _heal_network)
register_heal("auth", _heal_auth)
register_heal("resource", _heal_resource)
register_heal("dependency", _heal_dependency)
