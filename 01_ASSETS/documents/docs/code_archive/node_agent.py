#!/usr/bin/env python3
# node_agent.py 同源节点部署Agent V1.0
# DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
import os
import time
import json
import hashlib
import subprocess
import requests
from dataclasses import dataclass
from typing import Optional, Dict, Any
import logging

# ===================== 【配置区，请部署时修改】 =====================
NODE_ID = "SEC-NODE-001"
GATEWAY_API_BASE = "http://127.0.0.1:3000/api/report"
POLL_INTERVAL = 30
TASK_LOCK_FILE = "/opt/node-agent/task.lock"
WORK_DIR = "/opt/node-agent/workspace"
LOG_PATH = "/var/log/node-agent/agent.log"
# ==================================================================

os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

@dataclass
class DeployTask:
    task_id: str
    target_node: str
    package_url: str
    sha256: str
    deploy_script: str
    check_script: str
    rollback_script: str
    callback_truth_key: str
    version: str
    status: str

def is_task_running() -> bool:
    if os.path.exists(TASK_LOCK_FILE):
        try:
            with open(TASK_LOCK_FILE, "r") as f:
                pid = int(f.read().strip())
            if os.path.exists(f"/proc/{pid}"):
                return True
            else:
                os.unlink(TASK_LOCK_FILE)
        except Exception:
            os.unlink(TASK_LOCK_FILE)
    return False

def set_task_lock():
    os.makedirs(os.path.dirname(TASK_LOCK_FILE), exist_ok=True)
    with open(TASK_LOCK_FILE, "w") as f:
        f.write(str(os.getpid()))

def release_task_lock():
    if os.path.exists(TASK_LOCK_FILE):
        os.unlink(TASK_LOCK_FILE)

def calc_sha256(file_path: str) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def http_post_truth(truth_key:str, truth_value:Dict[str,Any], truth_type:str="meta_law", confidence:float=0.99):
    payload = {
        "truth_key": truth_key,
        "truth_value": json.dumps(truth_value, ensure_ascii=False),
        "source_node": NODE_ID,
        "confidence": confidence,
        "truth_type": truth_type
    }
    try:
        resp = requests.post(f"{GATEWAY_API_BASE}/truth", json=payload, timeout=10)
        logger.info(f"上报真值 status={resp.status_code}")
        return resp.status_code == 200
    except Exception as e:
        logger.error(f"真值上报失败: {str(e)}")
        return False

def fetch_pending_task() -> Optional[DeployTask]:
    try:
        resp = requests.get(f"{GATEWAY_API_BASE}/nodes?node_id={NODE_ID}", timeout=10)
        if resp.status_code != 200:
            return None
        data = resp.json()
        task_raw = data.get("pending_task")
        if not task_raw:
            return None
        task = DeployTask(**task_raw)
        if task.target_node == NODE_ID and task.status == "pending":
            return task
    except Exception as e:
        logger.error(f"拉取任务异常: {str(e)}")
    return None

def run_shell(script:str, cwd:str) -> Dict[str,Any]:
    try:
        proc = subprocess.Popen(
            ["bash", "-c", script],
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = proc.communicate()
        return {"returncode": proc.returncode, "stdout": stdout, "stderr": stderr}
    except Exception as e:
        return {"returncode": -1, "stdout":"", "stderr":str(e)}

def execute_task(task:DeployTask):
    result = {
        "task_id": task.task_id,
        "node_id": NODE_ID,
        "version": task.version,
        "stage": "init",
        "success": False,
        "log": "",
        "package_sha256_check": False
    }
    try:
        set_task_lock()
        os.makedirs(WORK_DIR, exist_ok=True)
        pkg_path = os.path.join(WORK_DIR, f"{task.task_id}.zip")
        result["stage"] = "download"
        r = requests.get(task.package_url, timeout=120)
        with open(pkg_path, "wb") as f:
            f.write(r.content)
        local_hash = calc_sha256(pkg_path)
        if local_hash.lower() != task.sha256.lower():
            result["log"] += f"哈希不匹配，本地:{local_hash},预期:{task.sha256}\n"
            raise Exception("部署包哈希校验失败，终止部署")
        result["package_sha256_check"] = True
        result["stage"] = "deploy"
        deploy_ret = run_shell(task.deploy_script, WORK_DIR)
        result["log"] += f"【部署脚本输出】\nstdout:{deploy_ret['stdout']}\nstderr:{deploy_ret['stderr']}\n"
        if deploy_ret["returncode"] != 0:
            result["stage"] = "rollback"
            run_shell(task.rollback_script, WORK_DIR)
            raise Exception(f"部署脚本异常，返回码{deploy_ret['returncode']}")
        result["stage"] = "health_check"
        check_ret = run_shell(task.check_script, WORK_DIR)
        result["log"] += f"【自检脚本输出】\nstdout:{check_ret['stdout']}\nstderr:{check_ret['stderr']}\n"
        if check_ret["returncode"] != 0:
            result["stage"] = "rollback"
            run_shell(task.rollback_script, WORK_DIR)
            raise Exception(f"健康自检失败，返回码{check_ret['returncode']}")
        result["success"] = True
        result["stage"] = "complete"
        logger.info(f"任务 {task.task_id} 部署成功")
    except Exception as e:
        result["success"] = False
        result["log"] += f"【异常】{str(e)}"
        logger.error(f"任务执行失败 task={task.task_id}, err={str(e)}")
    finally:
        http_post_truth(
            truth_key=task.callback_truth_key,
            truth_value=result,
            truth_type="protocol",
            confidence=0.99
        )
        release_task_lock()

def main_loop():
    logger.info(f"NodeAgent启动成功，NODE_ID={NODE_ID}，轮询间隔{POLL_INTERVAL}s")
    while True:
        try:
            if not is_task_running():
                task = fetch_pending_task()
                if task:
                    logger.info(f"获取到待部署任务: {task.task_id}, version:{task.version}")
                    execute_task(task)
        except Exception as e:
            logger.error(f"主循环异常: {str(e)}")
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main_loop()
