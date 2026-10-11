#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
火斗云智 AIOS 云端中枢握手与节点注册引擎

握手流程（状态机，来自经验 572401）：
  DISCOVER → CONNECT → HANDSHAKE → REGISTER → VERIFY

1. DISCOVER: 探测云端中枢可达性（DNS + HTTP）
2. CONNECT: 连接中枢状态端点 /api/status
3. HANDSHAKE: 身份核验（DID 匹配 + 锚点校验）
4. REGISTER: 节点注册（通过 /api/report/truth 上报注册声明）
5. VERIFY: 验证注册结果（truth_count 递增）

同源节点：来源为 huodouai.com 的节点
"""
import os
import sys
import json
import time
import hashlib
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List

# ============ 配置 ============

WORKSPACE = Path("/workspace")
NODE_REGISTRY_DIR = WORKSPACE / "node_registry"
NODE_REGISTRY_DIR.mkdir(parents=True, exist_ok=True)

REGISTRY_FILE = NODE_REGISTRY_DIR / "registry.json"
HANDSHAKE_LOG = NODE_REGISTRY_DIR / "handshake.log"

# 云端中枢端点
HUB_PRIMARY = "https://www.huodouai.com"
HUB_BACKUP = "https://drama.huodouai.com"
STATUS_ENDPOINT = "/api/status"
TRUTH_ENDPOINT = "/api/report/truth"

# 本节点身份
DID_TAG = "DID-BR-000002"
ARCHIVE_NODE = "ZONGYUAN-ROOT"
ANCHOR = "Ω₀⊂⊙∞⊂Ω"
NODE_ID = "NODE-DEV-DOUBAO-WORK-001"


def log(message: str):
    """握手日志。"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] [HANDSHAKE] {message}"
    print(line)
    with open(HANDSHAKE_LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def run_curl(url: str, method: str = "GET", data: Optional[Dict] = None, timeout: int = 10) -> Dict[str, Any]:
    """执行 curl 请求（兼容无 requests 库的环境）。"""
    cmd = ["/usr/bin/curl", "-s", "-X", method, url,
           "-H", "Content-Type: application/json",
           "-H", f"X-DID: {DID_TAG}",
           "--max-time", str(timeout)]
    if data:
        cmd.extend(["-d", json.dumps(data, ensure_ascii=False)])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5)
        body = result.stdout.strip()
        try:
            return {"success": True, "data": json.loads(body), "raw": body}
        except json.JSONDecodeError:
            return {"success": True, "data": None, "raw": body}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============ 握手状态机 ============

def discover_hub() -> Dict[str, Any]:
    """
    DISCOVER: 探测云端中枢可达性。
    返回各端点的可达性状态。
    """
    log("状态: DISCOVER - 探测云端中枢可达性")
    results = {}

    for name, base in [("primary", HUB_PRIMARY), ("backup", HUB_BACKUP)]:
        # HTTP 可达性
        resp = run_curl(base + "/", timeout=8)
        results[name] = {
            "base_url": base,
            "reachable": resp["success"],
            "response": resp.get("raw", "")[:200],
        }

    primary_ok = results["primary"]["reachable"]
    backup_ok = results["backup"]["reachable"]
    log(f"主端点可达: {primary_ok}, 备用端点可达: {backup_ok}")

    return results


def connect_hub() -> Dict[str, Any]:
    """
    CONNECT: 连接中枢状态端点。
    """
    log("状态: CONNECT - 连接中枢状态端点")
    resp = run_curl(HUB_PRIMARY + STATUS_ENDPOINT, timeout=10)
    if not resp["success"] or not resp["data"]:
        log("连接失败，尝试备用端点")
        resp = run_curl(HUB_BACKUP + STATUS_ENDPOINT, timeout=10)

    if resp["success"] and resp["data"]:
        log(f"连接成功: service={resp['data'].get('service')}, version={resp['data'].get('version')}")
        return resp["data"]
    else:
        log("连接失败: 无有效响应")
        return {}


def handshake_identity(hub_status: Dict[str, Any]) -> Dict[str, Any]:
    """
    HANDSHAKE: 身份核验。
    校验 DID 匹配 + 锚点一致。
    """
    log("状态: HANDSHAKE - 身份核验")
    result = {"success": False, "checks": {}}

    # DID 匹配
    hub_did = hub_status.get("did", "")
    did_match = hub_did == DID_TAG
    result["checks"]["did_match"] = did_match
    log(f"DID 校验: 本地={DID_TAG}, 中枢={hub_did}, 匹配={did_match}")

    # 锚点校验
    hub_anchor = hub_status.get("anchor", "")
    anchor_match = hub_anchor == ANCHOR
    result["checks"]["anchor_match"] = anchor_match
    log(f"锚点校验: 本地={ANCHOR}, 中枢={hub_anchor}, 匹配={anchor_match}")

    # 中枢状态
    hub_ok = hub_status.get("status") == "ok"
    result["checks"]["hub_ok"] = hub_ok

    result["success"] = did_match and anchor_match and hub_ok
    log(f"身份核验结果: {'通过' if result['success'] else '失败'}")

    return result


def register_node() -> Dict[str, Any]:
    """
    REGISTER: 节点注册。
    通过真值上报通道提交节点注册声明。
    """
    log("状态: REGISTER - 节点注册")

    truth_id = f"HZ-NODE-REG-{NODE_ID}"
    payload = {
        "truth_id": truth_id,
        "name": "同源节点注册声明",
        "content": (
            f"节点 {NODE_ID} 向云端中枢 zhongshu-meta-core 注册。"
            f"节点类型：开发节点。来源：同源(huodouai.com)。"
            f"自治等级：Lv4。权限等级：L4。工程化等级：Lv7。锚定：{ANCHOR}。"
        ),
        "source": "node-self-registration",
        "risk_level": "低风险",
        "did_tag": DID_TAG,
        "archive_node": ARCHIVE_NODE,
        "node_id": NODE_ID,
        "node_type": "dev",
        "origin": "huodouai",
        "reported_at": datetime.now().isoformat(),
    }

    resp = run_curl(HUB_PRIMARY + TRUTH_ENDPOINT, method="POST", data=payload, timeout=15)
    if not resp["success"] or not resp["data"]:
        # 尝试备用端点
        resp = run_curl(HUB_BACKUP + TRUTH_ENDPOINT, method="POST", data=payload, timeout=15)

    if resp["success"] and resp["data"] and resp["data"].get("ok"):
        truth_count = resp["data"].get("truth_count", 0)
        log(f"注册成功: truth_count={truth_count}, seq={resp['data'].get('seq')}")
        return {"success": True, "truth_count": truth_count, "response": resp["data"]}
    else:
        log(f"注册失败: {resp}")
        return {"success": False, "error": resp}


def verify_registration(before_count: int) -> Dict[str, Any]:
    """
    VERIFY: 验证注册结果。
    检查 truth_count 是否递增。
    """
    log("状态: VERIFY - 验证注册结果")
    resp = run_curl(HUB_PRIMARY + STATUS_ENDPOINT, timeout=10)
    if resp["success"] and resp["data"]:
        current_count = resp["data"].get("truth_count", 0)
        verified = current_count > before_count
        log(f"验证: 注册前={before_count}, 当前={current_count}, 递增={verified}")
        return {
            "success": verified,
            "before_count": before_count,
            "current_count": current_count,
            "merkle_root": resp["data"].get("merkle_root", ""),
        }
    return {"success": False, "error": "无法获取中枢状态"}


# ============ 节点注册表 ============

def load_registry() -> Dict[str, Any]:
    """加载节点注册表。"""
    if REGISTRY_FILE.exists():
        return json.loads(REGISTRY_FILE.read_text(encoding="utf-8"))
    return {"nodes": {}, "last_handshake": None}


def save_registry(registry: Dict[str, Any]):
    """保存节点注册表。"""
    REGISTRY_FILE.write_text(
        json.dumps(registry, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def update_node_registry(node_info: Dict[str, Any], handshake_result: Dict[str, Any]):
    """更新节点注册表。"""
    registry = load_registry()

    registry["nodes"][NODE_ID] = {
        "node_id": NODE_ID,
        "did": DID_TAG,
        "origin": "huodouai",
        "node_type": "dev",
        "status": "registered",
        "registered_at": datetime.now().isoformat(),
        "last_handshake": datetime.now().isoformat(),
        "handshake_success": handshake_result.get("success", False),
        "hub_truth_count": handshake_result.get("truth_count", 0),
        "merkle_root": handshake_result.get("merkle_root", ""),
        "archive_node": ARCHIVE_NODE,
        "anchor": ANCHOR,
    }

    registry["last_handshake"] = {
        "timestamp": datetime.now().isoformat(),
        "success": handshake_result.get("success", False),
        "hub_service": handshake_result.get("hub_service", ""),
        "hub_version": handshake_result.get("hub_version", ""),
    }

    save_registry(registry)
    log(f"节点注册表已更新: {NODE_ID}")


# ============ 主握手流程 ============

def run_handshake() -> Dict[str, Any]:
    """
    执行完整的云端中枢握手流程。
    """
    log("=" * 60)
    log("云端中枢握手流程开始")
    log("=" * 60)

    result = {
        "success": False,
        "steps": {},
        "registered_node": None,
    }

    # Step 1: DISCOVER
    discover = discover_hub()
    result["steps"]["discover"] = discover
    if not any(d["reachable"] for d in discover.values()):
        log("握手终止: 中枢不可达")
        return result

    # Step 2: CONNECT
    hub_status = connect_hub()
    result["steps"]["connect"] = hub_status
    if not hub_status:
        log("握手终止: 无法连接中枢")
        return result

    # 记录注册前的 truth_count
    before_count = hub_status.get("truth_count", 0)

    # Step 3: HANDSHAKE
    handshake = handshake_identity(hub_status)
    result["steps"]["handshake"] = handshake
    if not handshake["success"]:
        log("握手终止: 身份核验失败")
        return result

    # Step 4: REGISTER
    register = register_node()
    result["steps"]["register"] = register
    if not register["success"]:
        log("握手终止: 节点注册失败")
        return result

    # Step 5: VERIFY
    verify = verify_registration(before_count)
    result["steps"]["verify"] = verify

    # 汇总
    result["success"] = handshake["success"] and register["success"]
    result["registered_node"] = {
        "node_id": NODE_ID,
        "did": DID_TAG,
        "origin": "huodouai",
        "hub_service": hub_status.get("service", ""),
        "hub_version": hub_status.get("version", ""),
        "truth_count_after": verify.get("current_count", register.get("truth_count", 0)),
    }

    # 更新注册表
    update_node_registry(result["registered_node"], {
        "success": result["success"],
        "truth_count": verify.get("current_count", 0),
        "merkle_root": verify.get("merkle_root", ""),
        "hub_service": hub_status.get("service", ""),
        "hub_version": hub_status.get("version", ""),
    })

    log("=" * 60)
    log(f"握手流程完成: {'成功' if result['success'] else '失败'}")
    log("=" * 60)

    return result


# ============ 命令行入口 ============

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "status":
        registry = load_registry()
        print(json.dumps(registry, ensure_ascii=False, indent=2))
    else:
        result = run_handshake()
        print("\n" + json.dumps(result, ensure_ascii=False, indent=2))
