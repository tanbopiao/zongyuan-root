#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 同源节点部署Agent V2.0
轻量部署代理，轮询部署调度中心任务队列，认领并自主执行部署，上报回执
支持多窗口并发提交、FIFO+优先级队列、原子性任务认领
"""
import os
import sys
import json
import time
import hashlib
import subprocess
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

# ============ 配置 ============
CONFIG = {
    "gateway_url": "http://127.0.0.1:9120",
    "node_id": "tencent-cloud-main-01",
    "node_name": "腾讯云主服务器",
    "node_type": "cloud_server",
    "agent_version": "2.0.0",
    "poll_interval": 30,  # 轮询间隔（秒）
    "heartbeat_interval": 60,  # 心跳间隔（秒）
    "work_dir": "/opt/ZONGYUAN-ROOT/deploy_agent",
    "log_file": "/opt/ZONGYUAN-ROOT/logs/deploy_agent.log",
    "max_concurrent_tasks": 1,  # 单节点同时只能运行1个任务（互斥）
    "task_timeout": 1800,  # 任务超时（秒）
}

# ============ 工具函数 ============
def log(message, level="INFO"):
    """记录日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] [{level}] {message}"
    print(log_line)
    try:
        os.makedirs(os.path.dirname(CONFIG["log_file"]), exist_ok=True)
        with open(CONFIG["log_file"], "a", encoding="utf-8") as f:
            f.write(log_line + "\n")
    except Exception as e:
        print(f"[日志写入失败] {e}")

def http_request(url, method="GET", data=None, timeout=30):
    """HTTP请求封装"""
    try:
        headers = {"Content-Type": "application/json"}
        if data:
            data_bytes = json.dumps(data, ensure_ascii=False).encode()
        else:
            data_bytes = None
        req = urllib.request.Request(url, data=data_bytes, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}", "detail": str(e)}
    except Exception as e:
        return {"error": "request_failed", "detail": str(e)}

def calculate_sha256(file_path):
    """计算文件SHA256"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()

def run_command(command, timeout=300):
    """执行Shell命令"""
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return {
            "returncode": result.returncode,
            "stdout": result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout,
            "stderr": result.stderr[-2000:] if len(result.stderr) > 2000 else result.stderr,
        }
    except subprocess.TimeoutExpired:
        return {"returncode": -1, "stdout": "", "stderr": "命令执行超时"}
    except Exception as e:
        return {"returncode": -1, "stdout": "", "stderr": str(e)}

# ============ 核心功能 ============
def send_heartbeat():
    """发送心跳到记忆网关"""
    try:
        # 获取系统信息
        import platform
        os_info = f"{platform.system()} {platform.release()}"
        
        # 通过API上报节点状态（使用truth upsert作为临时通道）
        heartbeat_data = {
            "key": f"NODE.HEARTBEAT.{CONFIG['node_id']}",
            "value": json.dumps({
                "node_id": CONFIG["node_id"],
                "node_name": CONFIG["node_name"],
                "node_type": CONFIG["node_type"],
                "agent_version": CONFIG["agent_version"],
                "status": "online",
                "os_info": os_info,
                "timestamp": datetime.now().isoformat()
            }, ensure_ascii=False),
            "category": "node_heartbeat",
            "node_id": CONFIG["node_id"]
        }
        result = http_request(
            f"{CONFIG['gateway_url']}/api/truth/upsert",
            method="POST",
            data=heartbeat_data,
            timeout=15
        )
        if result.get("success"):
            log(f"心跳上报成功")
            return True
        else:
            log(f"心跳上报失败: {result}", "WARN")
            return False
    except Exception as e:
        log(f"心跳异常: {e}", "ERROR")
        return False

def fetch_pending_tasks():
    """从部署调度中心API获取并认领待执行任务"""
    try:
        # 1. 查询属于本节点的pending任务队列（按优先级排序）
        result = http_request(
            f"{CONFIG['gateway_url']}/api/deploy/tasks?node_id={CONFIG['node_id']}&status=pending&order_by=priority,created_at&limit=5",
            method="GET",
            timeout=15
        )

        if not result.get("success"):
            return None

        tasks = result.get("data", [])
        if not tasks:
            return None

        # 2. 取队列中第一个任务，尝试认领（原子性pending→running）
        first_task = tasks[0]
        task_id = first_task["task_id"]

        claim_result = http_request(
            f"{CONFIG['gateway_url']}/api/deploy/tasks/{task_id}/claim",
            method="POST",
            data={
                "node_id": CONFIG["node_id"],
                "agent_version": CONFIG["agent_version"]
            },
            timeout=15
        )

        if claim_result.get("success"):
            log(f"获取到待执行任务并认领成功: {task_id}")
            # 返回认领后的任务数据（状态已变为running）
            return claim_result.get("data", first_task)
        else:
            # 认领失败（可能被其他Agent抢先），记录并返回None
            log(f"任务认领失败: {task_id}, {claim_result.get('error')}", "WARN")
            return None

    except Exception as e:
        log(f"获取任务异常: {e}", "ERROR")
        return None

def execute_deploy_task(task):
    """执行部署任务"""
    task_id = task.get("task_id", "unknown")
    log(f"开始执行部署任务: {task_id}")
    
    # 更新任务状态为running
    update_task_status(task_id, "running")
    
    try:
        work_dir = os.path.join(CONFIG["work_dir"], task_id)
        os.makedirs(work_dir, exist_ok=True)
        
        # 1. 下载部署包（如果有package_url）
        package_path = None
        if task.get("package_url"):
            log(f"下载部署包: {task['package_url']}")
            package_path = os.path.join(work_dir, "package.tar.gz")
            download_result = run_command(f"curl -sL -o {package_path} '{task['package_url']}'", timeout=300)
            if download_result["returncode"] != 0:
                raise Exception(f"部署包下载失败: {download_result['stderr']}")
            
            # 2. 校验SHA256
            if task.get("package_sha256"):
                actual_sha256 = calculate_sha256(package_path)
                if actual_sha256 != task["package_sha256"]:
                    raise Exception(f"SHA256校验失败: 期望{task['package_sha256']}, 实际{actual_sha256}")
                log(f"SHA256校验通过")
        
        # 3. 执行部署脚本
        deploy_result = None
        if task.get("deploy_script"):
            script_path = os.path.join(work_dir, "deploy.sh")
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(task["deploy_script"])
            os.chmod(script_path, 0o755)
            
            log(f"执行部署脚本...")
            deploy_result = run_command(f"bash {script_path}", timeout=CONFIG["task_timeout"])
            log(f"部署脚本返回码: {deploy_result['returncode']}")
            
            if deploy_result["returncode"] != 0:
                raise Exception(f"部署脚本执行失败: {deploy_result['stderr'][:500]}")
        
        # 4. 执行校验脚本
        check_result = None
        if task.get("check_script"):
            check_path = os.path.join(work_dir, "check.sh")
            with open(check_path, "w", encoding="utf-8") as f:
                f.write(task["check_script"])
            os.chmod(check_path, 0o755)
            
            log(f"执行校验脚本...")
            check_result = run_command(f"bash {check_path}", timeout=120)
            log(f"校验脚本返回码: {check_result['returncode']}")
            
            if check_result["returncode"] != 0:
                raise Exception(f"校验脚本执行失败: {check_result['stderr'][:500]}")
        
        # 5. 任务成功
        result_log = json.dumps({
            "deploy_stdout": deploy_result["stdout"] if deploy_result else "",
            "check_stdout": check_result["stdout"] if check_result else "",
            "completed_at": datetime.now().isoformat()
        }, ensure_ascii=False)
        
        update_task_status(task_id, "success", result_log=result_log)
        report_task_result(task, "success", result_log)
        log(f"部署任务执行成功: {task_id}")
        return True
        
    except Exception as e:
        error_msg = str(e)
        log(f"部署任务执行失败: {task_id}, 错误: {error_msg}", "ERROR")
        update_task_status(task_id, "failed", error_message=error_msg)
        report_task_result(task, "failed", error_msg)
        return False

def update_task_status(task_id, status, result_log=None, error_message=None):
    """更新任务状态（通过部署调度中心API）"""
    try:
        data = {"status": status}
        if result_log:
            data["result_log"] = result_log
        if error_message:
            data["error_message"] = error_message

        result = http_request(
            f"{CONFIG['gateway_url']}/api/deploy/tasks/{task_id}/status",
            method="PUT",
            data=data,
            timeout=15
        )

        if result.get("success"):
            log(f"任务状态已更新: {task_id} -> {status}")
        else:
            log(f"任务状态更新失败: {task_id}, {result.get('error')}", "WARN")
    except Exception as e:
        log(f"更新任务状态失败: {e}", "WARN")

def report_task_result(task, status, result_data):
    """上报任务结果到记忆网关（作为真值）"""
    try:
        task_id = task.get("task_id", "unknown")
        callback_key = task.get("callback_truth_key", f"DEPLOY.RESULT.{task_id}")
        
        result = {
            "task_id": task_id,
            "task_name": task.get("task_name", ""),
            "target_node": CONFIG["node_id"],
            "status": status,
            "result": result_data,
            "agent_version": CONFIG["agent_version"],
            "completed_at": datetime.now().isoformat(),
            "trace_mark": "Ω₀⊂⊙∞⊂Ω",
            "did": "DID-BR-000002"
        }
        
        http_request(
            f"{CONFIG['gateway_url']}/api/truth/upsert",
            method="POST",
            data={
                "key": callback_key,
                "value": json.dumps(result, ensure_ascii=False),
                "category": "deploy_result",
                "node_id": CONFIG["node_id"]
            },
            timeout=15
        )
        log(f"任务结果已上报: {callback_key}")
    except Exception as e:
        log(f"上报任务结果失败: {e}", "WARN")

# ============ 主循环 ============
def main():
    log("=" * 60)
    log(f"ZONGYUAN-ROOT 部署Agent V{CONFIG['agent_version']} 启动")
    log(f"节点ID: {CONFIG['node_id']}")
    log(f"网关地址: {CONFIG['gateway_url']}")
    log(f"轮询间隔: {CONFIG['poll_interval']}秒")
    log("=" * 60)
    
    # 确保工作目录存在
    os.makedirs(CONFIG["work_dir"], exist_ok=True)
    
    last_heartbeat = 0
    current_task = None
    
    while True:
        try:
            now = time.time()
            
            # 发送心跳
            if now - last_heartbeat >= CONFIG["heartbeat_interval"]:
                send_heartbeat()
                last_heartbeat = now
            
            # 如果当前没有正在执行的任务，获取新任务
            if current_task is None:
                task = fetch_pending_tasks()
                if task:
                    current_task = task
                    # 异步执行任务（在主线程执行，因为单节点互斥）
                    success = execute_deploy_task(task)
                    current_task = None
            else:
                log(f"任务执行中: {current_task.get('task_id')}")
            
            # 等待下一轮
            time.sleep(CONFIG["poll_interval"])
            
        except KeyboardInterrupt:
            log("收到中断信号，Agent停止")
            break
        except Exception as e:
            log(f"主循环异常: {e}", "ERROR")
            time.sleep(CONFIG["poll_interval"])

if __name__ == "__main__":
    main()
