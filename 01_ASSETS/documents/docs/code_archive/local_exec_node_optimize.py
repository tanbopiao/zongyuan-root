#!/usr/bin/env python3
"""
local-windows-exec-001 节点优化脚本 (Python版本)
解决节点每10-18秒高频上报心跳导致记忆网关pass_rate被拉低的问题

优化项：
1. 上报频率从~18秒调整为60秒
2. 节点端去重（相同内容不重复上报）
3. 批量合并（60秒内的多次心跳合并为1条丰富汇总上报）
4. 添加上报间隔随机抖动（避免与其他节点同时上报）
5. 失败重试+指数退避

使用方法：
    python local_exec_node_optimize.py --interval 60
    python local_exec_node_optimize.py --install-service  (Windows服务安装)

生成时间: 2026-09-15 20:15 CST
确权: DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
"""

import argparse
import hashlib
import json
import logging
import os
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

# ============================================================
# 配置
# ============================================================
SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR / "node_config.json"
LOG_FILE = SCRIPT_DIR / "node_optimize.log"

DEFAULT_CONFIG = {
    "interval_seconds": 60,
    "gateway_url": "https://www.huodouai.com/api/report/truth",
    "node_id": "local-windows-exec-001",
    "dedup_enabled": True,
    "jitter_seconds": 5,
    "last_report_hash": "",
    "last_report_time": "",
    "total_reports": 0,
    "duplicate_skipped": 0,
    "consecutive_errors": 0,
}

# ============================================================
# 日志
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


# ============================================================
# 配置管理
# ============================================================
def load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            # 合并默认值
            merged = {**DEFAULT_CONFIG, **cfg}
            return merged
        except (json.JSONDecodeError, IOError):
            logger.warning("配置文件损坏，使用默认配置")
    return DEFAULT_CONFIG.copy()


def save_config(config: dict):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


# ============================================================
# 内容哈希（去重用）
# ============================================================
def content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


# ============================================================
# 采集节点状态（丰富的单条上报，替代高频简单心跳）
# ============================================================
def collect_node_status(node_id: str) -> dict:
    """采集节点系统状态，合并为单条丰富上报"""
    status = {
        "node_id": node_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "active",
    }

    # CPU使用率
    try:
        import psutil
        status["cpu_percent"] = psutil.cpu_percent(interval=1)
        status["memory_percent"] = psutil.virtual_memory().percent
        status["disk_c_percent"] = psutil.disk_usage("C:\\").percent if os.name == "nt" else psutil.disk_usage("/").percent
        status["process_count"] = len(psutil.pids())
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        status["uptime_hours"] = round((datetime.now() - boot_time).total_seconds() / 3600, 1)
    except ImportError:
        # psutil不可用时使用基础信息
        status["note"] = "psutil_not_installed_run_pip_install_psutil"
        status["cpu_percent"] = -1
        status["memory_percent"] = -1

    return status


# ============================================================
# 上报函数（去重+重试）
# ============================================================
def send_heartbeat(config: dict) -> bool:
    node_id = config["node_id"]
    gateway_url = config["gateway_url"]

    # 采集丰富状态
    status = collect_node_status(node_id)
    truth_value = json.dumps(status, ensure_ascii=False, separators=(",", ":"))
    chash = content_hash(truth_value)

    # 去重检查
    if config["dedup_enabled"] and chash == config["last_report_hash"]:
        config["duplicate_skipped"] += 1
        save_config(config)
        logger.debug(f"内容重复，跳过去重 (hash={chash}, 累计跳过={config['duplicate_skipped']})")
        return False

    # 构造上报
    payload = {
        "truth_key": "LOCAL.EXEC.NODE.HEARTBEAT",
        "truth_value": truth_value,
        "source_node": node_id,
        "confidence": 0.95,
        "truth_type": "data",
    }

    # 上报（带重试+指数退避）
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.post(
                gateway_url,
                json=payload,
                timeout=15,
                headers={"Content-Type": "application/json"},
            )
            if resp.status_code == 200 and resp.text.strip():
                result = resp.json()
                if result.get("written_to_gateway"):
                    config["last_report_hash"] = chash
                    config["last_report_time"] = datetime.now(timezone.utc).isoformat()
                    config["total_reports"] += 1
                    config["consecutive_errors"] = 0
                    save_config(config)
                    logger.info(
                        f"上报成功 (report_id={result.get('report_id')}, "
                        f"validation={result.get('validation', {}).get('status')}, "
                        f"累计={config['total_reports']})"
                    )
                    return True
                else:
                    logger.warning(f"上报未写入网关: {result}")
            else:
                logger.warning(f"上报HTTP {resp.status_code}: {resp.text[:200]}")
        except requests.RequestException as e:
            logger.warning(f"上报失败 (第{attempt}/{max_retries}次): {e}")
            if attempt < max_retries:
                time.sleep(2 ** attempt)  # 指数退避: 2s, 4s

    config["consecutive_errors"] += 1
    save_config(config)
    logger.error(f"上报最终失败 (连续错误={config['consecutive_errors']})")
    return False


# ============================================================
# 主循环
# ============================================================
def main_loop(config: dict):
    logger.info("=" * 60)
    logger.info("local-windows-exec-001 优化节点启动")
    logger.info(f"上报间隔: {config['interval_seconds']}秒 (原~18秒)")
    logger.info(f"去重: {config['dedup_enabled']}")
    logger.info(f"随机抖动: ±{config['jitter_seconds']}秒")
    logger.info(f"网关: {config['gateway_url']}")
    logger.info(f"历史累计上报: {config['total_reports']}")
    logger.info(f"历史去重跳过: {config['duplicate_skipped']}")
    logger.info("=" * 60)

    while True:
        try:
            send_heartbeat(config)
        except Exception as e:
            logger.error(f"主循环异常: {e}", exc_info=True)

        # 随机抖动：避免与其他节点同时上报
        jitter = random.randint(0, config["jitter_seconds"])
        sleep_time = config["interval_seconds"] + jitter
        time.sleep(sleep_time)


# ============================================================
# Windows服务安装（可选）
# ============================================================
def install_windows_service(interval: int):
    """安装为Windows服务（需要pywin32）"""
    try:
        import win32serviceutil
        import servicemanager
        import win32service
    except ImportError:
        logger.error("pywin32未安装，无法安装为服务。运行: pip install pywin32")
        logger.info("替代方案: 使用任务计划程序或nssm")
        return False

    # 简化：使用任务计划程序
    script_path = str(Path(__file__).resolve())
    task_name = "ZongyuanLocalExecNode"

    import subprocess
    # 删除已有任务
    subprocess.run(["schtasks", "/Delete", "/TN", task_name, "/F"], capture_output=True)
    # 创建新任务（开机自启，最高权限）
    cmd = [
        "schtasks", "/Create", "/TN", task_name,
        "/TR", f'python "{script_path}" --interval {interval}',
        "/SC", "ONSTART", "/RL", "HIGHEST", "/F",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        logger.info(f"已安装为开机自启任务: {task_name}")
        # 立即启动
        subprocess.run(["schtasks", "/Run", "/TN", task_name], capture_output=True)
        return True
    else:
        logger.error(f"任务创建失败: {result.stderr}")
        return False


# ============================================================
# 入口
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="local-windows-exec-001 节点优化")
    parser.add_argument("--interval", type=int, default=60, help="上报间隔秒数（默认60）")
    parser.add_argument("--gateway", type=str, default=DEFAULT_CONFIG["gateway_url"], help="网关URL")
    parser.add_argument("--node-id", type=str, default=DEFAULT_CONFIG["node_id"], help="节点ID")
    parser.add_argument("--install-service", action="store_true", help="安装为Windows开机自启任务")
    parser.add_argument("--no-dedup", action="store_true", help="禁用去重")
    args = parser.parse_args()

    config = load_config()
    config["interval_seconds"] = args.interval
    config["gateway_url"] = args.gateway
    config["node_id"] = args.node_id
    config["dedup_enabled"] = not args.no_dedup
    save_config(config)

    if args.install_service:
        install_windows_service(args.interval)
        return

    main_loop(config)


if __name__ == "__main__":
    main()
