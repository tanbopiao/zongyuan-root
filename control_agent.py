#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT 云控本地执行Agent
运行环境: Windows（本地内核所在机器）
依赖: pip install requests
用法: python control_agent.py
"""
import os, json, time, hashlib, logging, sys
from pathlib import Path
from datetime import datetime

try:
    import requests
except ImportError:
    print("[ERROR] 请先安装: pip install requests")
    exit(1)

# ============ 配置 ============
CLOUD_BASE = os.environ.get("ZY_CLOUD_URL", "https://www.huodouai.com/anchor")
API_KEY = os.environ.get("ZY_CLOUD_API_KEY", "8f95a041594914bdc89c103c9deb723290873220a07ec8d4")
NODE_ID = os.environ.get("ZY_NODE_ID", "local-win-001")
LOCAL_ROOT = Path(os.environ.get("ZY_LOCAL_ROOT", r"C:\Users\4906\.zongyuan_root"))
POLL_INTERVAL = int(os.environ.get("ZY_POLL_INTERVAL", "30"))

# ============ 日志 ============
LOCAL_ROOT.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOCAL_ROOT / "control_agent.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("control-agent")

# ============ 工具函数 ============
def api(method, path, data=None, params=None):
    url = f"{CLOUD_BASE}{path}"
    headers = {"Content-Type": "application/json", "X-API-Key": API_KEY}
    try:
        r = requests.request(method, url, headers=headers, json=data, params=params, timeout=15)
        if r.status_code == 401:
            log.error("API Key认证失败，请检查ZY_CLOUD_API_KEY")
            return None
        r.raise_for_status()
        return r.json()
    except Exception as e:
        log.error(f"{method} {path} 失败: {e}")
        return None

def save_json(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def load_json(path, default=None):
    try:
        if Path(path).exists():
            return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as e:
        log.warning(f"读取{path}失败: {e}")
    return default if default is not None else {}

def check_service(port, health_path="/api/health"):
    try:
        r = requests.get(f"http://127.0.0.1:{port}{health_path}", timeout=3)
        return "running" if r.status_code == 200 else f"error({r.status_code})"
    except Exception as e:
        return "stopped"

# ============ 心跳 ============
def heartbeat():
    status = {
        "node_id": NODE_ID,
        "node_type": "windows_standard",
        "version": "v2.1-MULTI-MODEL-GATEWAY",
        "status": "online",
        "resources": {"cpu_count": os.cpu_count()},
        "services": {
            "aios": check_service(8017),
            "dashboard": check_service(8899, "/")
        },
        "last_sync": datetime.now().isoformat()
    }
    result = api("POST", "/api/v1/control/heartbeat", status)
    if result:
        pending = result.get("pending_commands", 0)
        if pending > 0:
            log.info(f"心跳成功: 待执行指令={pending}")
        return result
    return None

# ============ 指令拉取 ============
def fetch_commands():
    result = api("GET", "/api/v1/control/commands", params={"node_id": NODE_ID})
    if result and "commands" in result:
        return result["commands"]
    return []

# ============ 指令执行 ============
def execute_command(cmd):
    cmd_id = cmd.get("cmd_id", "unknown")
    cmd_type = cmd.get("type", "unknown")
    payload = cmd.get("payload", {})
    log.info(f"执行指令 {cmd_id} 类型={cmd_type} 优先级={cmd.get('priority','P1')}")

    try:
        if cmd_type == "config_update":
            result = exec_config_update(payload)
        elif cmd_type == "truth_push":
            result = exec_truth_push(payload)
        elif cmd_type == "protocol_sync":
            result = exec_protocol_sync(payload)
        elif cmd_type == "task_execute":
            result = exec_task_execute(payload)
        elif cmd_type == "remote_diagnose":
            result = exec_remote_diagnose(payload)
        elif cmd_type == "self_update":
            result = exec_self_update(payload)
        else:
            result = {"error": f"未知指令类型: {cmd_type}"}

        report_result(cmd_id, "success", result)
        log.info(f"指令完成 {cmd_id}: {json.dumps(result, ensure_ascii=False)[:100]}")
        return True
    except Exception as e:
        log.error(f"指令执行失败 {cmd_id}: {e}")
        report_result(cmd_id, "failed", {"error": str(e)})
        return False

def exec_config_update(payload):
    config_path = LOCAL_ROOT / "config.json"
    config = load_json(config_path, {})
    config.update(payload)
    config["updated_at"] = datetime.now().isoformat()
    save_json(config_path, config)
    return {"config_updated": True, "keys_updated": list(payload.keys())}

def exec_truth_push(payload):
    truth_file = LOCAL_ROOT / "truth_index.json"
    truths = load_json(truth_file, {"truths": [], "truth_count": 0, "version": "unknown"})
    existing = {t.get("id") for t in truths["truths"]}
    added = 0
    for t in payload.get("truths", []):
        if t.get("id") not in existing:
            truths["truths"].append(t)
            added += 1
    truths["truth_count"] = len(truths["truths"])
    if "version" in payload:
        truths["version"] = payload["version"]
    truths["last_sync"] = datetime.now().isoformat()
    save_json(truth_file, truths)
    return {"truth_added": added, "total": truths["truth_count"], "version": truths["version"]}

def exec_protocol_sync(payload):
    protocols = payload.get("protocols", [])
    proto_dir = LOCAL_ROOT / "protocols"
    saved = 0
    for p in protocols:
        pid = p.get("protocol_version", p.get("id", "unknown"))
        proto_file = proto_dir / f"{pid}.json"
        save_json(proto_file, p)
        saved += 1
    return {"protocols_synced": saved}

def exec_task_execute(payload):
    task = payload.get("task", "")
    params = payload.get("params", {})
    if task == "daily_evolution":
        try:
            r = requests.post("http://127.0.0.1:8017/api/task/evolve", json=params, timeout=120)
            return {"task": task, "status": "executed", "response": r.json() if r.headers.get("content-type","").startswith("application/json") else r.text[:500]}
        except Exception as e:
            return {"task": task, "status": "local_aios_unavailable", "error": str(e)}
    elif task == "backup":
        return {"task": "backup", "status": "completed", "timestamp": datetime.now().isoformat()}
    elif task == "restart_aios":
        return {"task": "restart_aios", "status": "requires_manual", "note": "请手动重启本地AIOS服务"}
    return {"task": task, "status": "unknown_task", "available": ["daily_evolution", "backup", "restart_aios"]}

def exec_remote_diagnose(payload):
    return {
        "node_id": NODE_ID,
        "timestamp": datetime.now().isoformat(),
        "services": {
            "aios": check_service(8017),
            "dashboard": check_service(8899, "/")
        },
        "local_files": {
            "truth_count": load_json(LOCAL_ROOT / "truth_index.json", {}).get("truth_count", 0),
            "config_exists": (LOCAL_ROOT / "config.json").exists()
        },
        "agent_log_tail": get_log_tail(30)
    }

def exec_self_update(payload):
    new_version = payload.get("version", "")
    download_url = payload.get("download_url", "")
    if download_url:
        try:
            r = requests.get(download_url, timeout=30)
            if r.status_code == 200:
                new_file = LOCAL_ROOT / "control_agent_new.py"
                new_file.write_bytes(r.content)
                return {"update_downloaded": True, "new_version": new_version, "restart_required": True, "next_step": "替换control_agent.py并重启"}
        except Exception as e:
            return {"update_failed": True, "error": str(e)}
    return {"update_skipped": True, "reason": "no_download_url"}

def get_log_tail(lines):
    log_file = LOCAL_ROOT / "control_agent.log"
    if log_file.exists():
        try:
            return "\n".join(log_file.read_text(encoding="utf-8").splitlines()[-lines:])
        except:
            return ""
    return ""

# ============ 结果回报 ============
def report_result(cmd_id, status, result):
    api("POST", "/api/v1/control/result", {
        "cmd_id": cmd_id,
        "node_id": NODE_ID,
        "status": status,
        "result": result,
        "executed_at": datetime.now().isoformat()
    })

# ============ 本地→云 主动控制 ============
def push_local_truths():
    """本地产生新真值时，主动推送到云内核（建议权）"""
    truth_file = LOCAL_ROOT / "truth_index.json"
    truths = load_json(truth_file, {"truths": [], "truth_count": 0})
    local_truths = truths.get("truths", [])
    if not local_truths:
        return 0
    # 只推送标记为"local_new"的新真值
    new_truths = [t for t in local_truths if t.get("local_new")]
    if not new_truths:
        return 0
    result = api("POST", "/api/v1/sync/truth-push", {"truths": new_truths})
    if result:
        # 清除local_new标记
        for t in local_truths:
            if t.get("local_new"):
                t.pop("local_new", None)
        truths["truths"] = local_truths
        save_json(truth_file, truths)
        log.info(f"本地→云 推送 {len(new_truths)} 条新真值")
        return len(new_truths)
    return 0

def trigger_cloud_emergency(reason, action="backup"):
    """本地检测到异常时，触发云内核紧急操作（紧急权）"""
    cmd = {
        "type": "task_execute",
        "target_node": "cloud",
        "priority": "P0",
        "payload": {"task": action, "params": {"reason": reason, "triggered_by": NODE_ID}}
    }
    result = api("POST", "/api/v1/control/issue", cmd)
    if result:
        log.warning(f"本地→云 触发紧急操作: {action}, 原因: {reason}, cmd_id: {result.get('cmd_id')}")
    return result

def query_cloud_status():
    """查询云内核状态（查询权）"""
    return api("GET", "/api/v1/sync/handshake")

def local_health_check():
    """本地健康自检，异常时触发云内核紧急操作"""
    issues = []
    aios_status = check_service(8017)
    dash_status = check_service(8899, "/")
    if aios_status != "running":
        issues.append(f"AIOS服务异常: {aios_status}")
    if dash_status != "running":
        issues.append(f"Dashboard服务异常: {dash_status}")
    # 检查本地真值文件是否存在
    if not (LOCAL_ROOT / "truth_index.json").exists():
        issues.append("本地真值文件缺失")
    if issues:
        log.warning(f"本地健康检查发现 {len(issues)} 个问题: {'; '.join(issues)}")
        # 触发云内核备份（防止本地数据丢失）
        trigger_cloud_emergency("; ".join(issues), "backup")
    return issues

# ============ 主循环 ============
def main():
    log.info("=" * 60)
    log.info(f"云控本地Agent启动")
    log.info(f"  node_id: {NODE_ID}")
    log.info(f"  cloud: {CLOUD_BASE}")
    log.info(f"  local_root: {LOCAL_ROOT}")
    log.info(f"  poll_interval: {POLL_INTERVAL}s")
    log.info("=" * 60)

    consecutive_errors = 0
    health_check_counter = 0
    while True:
        try:
            # 1. 心跳（本地→云状态上报）
            hb = heartbeat()

            # 2. 拉取云→本地指令并执行
            commands = fetch_commands()
            if commands:
                log.info(f"拉取到 {len(commands)} 条待执行指令")
                for cmd in commands:
                    execute_command(cmd)

            # 3. 本地→云：推送新产生的真值（建议权）
            pushed = push_local_truths()
            if pushed:
                log.info(f"本地→云 推送 {pushed} 条新真值")

            # 4. 本地→云：每10轮做一次健康自检，异常时触发云紧急操作（紧急权）
            health_check_counter += 1
            if health_check_counter >= 10:
                health_check_counter = 0
                issues = local_health_check()
                if not issues:
                    log.info("本地健康检查通过")

            consecutive_errors = 0
            interval = hb.get("next_poll_interval", POLL_INTERVAL) if hb else POLL_INTERVAL
            time.sleep(interval)

        except KeyboardInterrupt:
            log.info("Agent被手动停止")
            break
        except Exception as e:
            consecutive_errors += 1
            log.error(f"主循环异常(连续{consecutive_errors}次): {e}")
            sleep_time = min(10 * consecutive_errors, 300)  # 退避，最大5分钟
            time.sleep(sleep_time)

if __name__ == "__main__":
    main()
