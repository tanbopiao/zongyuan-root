#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT 本地内核 ↔ 云内核 双向同步Agent
运行环境: Windows (本地AIOS所在机器)
依赖: requests (pip install requests)
用法: python sync_agent.py [--interval 300]
"""
import os, json, time, hashlib, logging, argparse
from pathlib import Path
from datetime import datetime

try:
    import requests
except ImportError:
    print("[ERROR] 请先安装: pip install requests")
    exit(1)

# ============ 配置 ============
# 云内核地址 (通过frp隧道或直连)
CLOUD_BASE = os.environ.get("ZY_CLOUD_URL", "https://www.huodouai.com/anchor")
# 如果通过Nginx域名访问(带Basic Auth),使用:
# CLOUD_BASE = "https://www.huodouai.com/anchor"
CLOUD_AUTH = os.environ.get("ZY_CLOUD_AUTH", "")  # 格式: "user:password"
CLOUD_API_KEY = os.environ.get("ZY_CLOUD_API_KEY", "8f95a041594914bdc89c103c9deb723290873220a07ec8d4")

# 本地内核路径 (Windows)
LOCAL_ROOT = Path(os.environ.get("ZY_LOCAL_ROOT", r"C:\Users\4906\.zongyuan_root"))
LOCAL_TRUTH_FILE = LOCAL_ROOT / "truth_index.json"
LOCAL_STATE_FILE = LOCAL_ROOT / "sync_state.json"
LOCAL_LOG_FILE = LOCAL_ROOT / "sync_agent.log"

# 同步间隔(秒)
DEFAULT_INTERVAL = 300  # 5分钟

# ============ 日志 ============
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOCAL_LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("sync-agent")

# ============ 工具函数 ============
def sha256(data):
    if isinstance(data, str):
        data = data.encode()
    return hashlib.sha256(data).hexdigest()

def load_json(path, default=None):
    try:
        if Path(path).exists():
            return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as e:
        log.warning(f"读取{path}失败: {e}")
    return default if default is not None else {}

def save_json(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def cloud_get(path, **kwargs):
    url = f"{CLOUD_BASE}{path}"
    headers = {"Content-Type": "application/json", "X-API-Key": CLOUD_API_KEY}
    auth = tuple(CLOUD_AUTH.split(":")) if CLOUD_AUTH else None
    try:
        r = requests.get(url, headers=headers, auth=auth, timeout=10, **kwargs)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        log.error(f"GET {url} 失败: {e}")
        return None

def cloud_post(path, data):
    url = f"{CLOUD_BASE}{path}"
    headers = {"Content-Type": "application/json"}
    auth = tuple(CLOUD_AUTH.split(":")) if CLOUD_AUTH else None
    try:
        r = requests.post(url, json=data, headers=headers, auth=auth, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        log.error(f"POST {url} 失败: {e}")
        return None

# ============ 核心同步逻辑 ============
def handshake():
    """与云内核握手,获取当前状态"""
    data = cloud_get("/api/v1/sync/handshake")
    if data:
        log.info(f"握手成功: 云内核={data.get('kernel_id')}, "
                 f"真值={data.get('truth_count')}条, "
                 f"版本={data.get('truth_version')}, "
                 f"记忆链={data.get('memory_chain_seeds')}种子")
    return data

def pull_truths(cloud_version, local_ids):
    """从云内核拉取本地缺失的真值"""
    # 全量拉取后本地比对(简单可靠)
    data = cloud_post("/api/v1/sync/truth-pull", {"ids": []})
    if not data:
        return 0
    cloud_truths = data.get("truths", [])
    new_truths = [t for t in cloud_truths if t.get("id") not in local_ids]
    if new_truths:
        log.info(f"拉取到 {len(new_truths)} 条云端新真值")
        for t in new_truths:
            log.info(f"  + {t.get('id')}: {str(t.get('content',''))[:50]}")
    return new_truths

def push_truths(local_truths, cloud_ids):
    """推送本地新真值到云内核"""
    new_truths = [t for t in local_truths if t.get("id") not in cloud_ids]
    if not new_truths:
        return 0
    log.info(f"推送 {len(new_truths)} 条本地新真值到云内核")
    result = cloud_post("/api/v1/sync/truth-push", {
        "truths": new_truths,
        "source": "local_kernel"
    })
    if result and result.get("status") == "ok":
        log.info(f"推送成功: 添加{result.get('added')}条, 云端总数{result.get('total_after')}")
        return result.get("added", 0)
    return 0

def sync_once():
    """执行一次完整同步"""
    log.info("=" * 50)
    log.info("开始同步循环")

    # 1. 握手
    cloud_state = handshake()
    if not cloud_state:
        log.error("握手失败,跳过本次同步")
        return False

    # 2. 加载本地状态
    local_state = load_json(LOCAL_STATE_FILE, {
        "last_sync": None, "last_cloud_version": None,
        "truth_count": 0, "sync_count": 0
    })

    # 3. 加载本地真值
    local_data = load_json(LOCAL_TRUTH_FILE, {"truths": [], "truth_count": 0})
    local_truths = local_data.get("truths", [])
    local_ids = {t.get("id") for t in local_truths}

    # 4. 获取云端真值ID列表(通过pull全量)
    cloud_data = cloud_post("/api/v1/sync/truth-pull", {"ids": []})
    if not cloud_data:
        log.error("获取云端真值失败")
        return False
    cloud_ids = {t.get("id") for t in cloud_data.get("truths", [])}

    # 5. 拉取云端新真值 → 本地
    new_from_cloud = pull_truths(cloud_state.get("truth_version"), local_ids)
    if new_from_cloud:
        local_truths.extend(new_from_cloud)
        local_data["truths"] = local_truths
        local_data["truth_count"] = len(local_truths)
        local_data["version"] = cloud_data.get("version", local_data.get("version", "unknown"))
        save_json(LOCAL_TRUTH_FILE, local_data)
        log.info(f"本地真值更新: {len(local_truths)}条")

    # 6. 推送本地新真值 → 云端
    pushed = push_truths(local_truths, cloud_ids)

    # 7. 更新同步状态
    local_state["last_sync"] = datetime.now().isoformat()
    local_state["last_cloud_version"] = cloud_state.get("truth_version")
    local_state["truth_count"] = len(local_truths)
    local_state["sync_count"] = local_state.get("sync_count", 0) + 1
    local_state["last_result"] = {
        "pulled": len(new_from_cloud),
        "pushed": pushed,
        "cloud_truths": cloud_state.get("truth_count"),
        "local_truths": len(local_truths)
    }
    save_json(LOCAL_STATE_FILE, local_state)

    log.info(f"同步完成: 拉取{len(new_from_cloud)}条, 推送{pushed}条, "
             f"本地{len(local_truths)}条, 云端{cloud_state.get('truth_count')}条")
    return True

# ============ 主循环 ============
def main():
    parser = argparse.ArgumentParser(description="ZONGYUAN-ROOT 双向同步Agent")
    parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL, help="同步间隔(秒)")
    parser.add_argument("--once", action="store_true", help="只执行一次")
    args = parser.parse_args()

    log.info("ZONGYUAN-ROOT 双向同步Agent启动")
    log.info(f"云内核: {CLOUD_BASE}")
    log.info(f"本地路径: {LOCAL_ROOT}")
    log.info(f"同步间隔: {args.interval}秒")

    if args.once:
        sync_once()
        return

    while True:
        try:
            sync_once()
        except Exception as e:
            log.error(f"同步异常: {e}", exc_info=True)
        time.sleep(args.interval)

if __name__ == "__main__":
    main()
