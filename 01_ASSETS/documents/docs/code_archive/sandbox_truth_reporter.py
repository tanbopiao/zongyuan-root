#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT 新沙盒真值上报标准模板
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | Ω-TAN-7-001

功能：
  1. 节点注册（可选，用于心跳管理）
  2. 心跳上报（30秒间隔，2分钟超时标记离线）
  3. 单条真值上报（无需同源验证，最简单）
  4. 批量真值同步（需同源验证）
  5. 真值查询（列表/单条/历史）
  6. 审计日志查询

使用方法：
  - 修改 CONFIG 部分的配置
  - 调用对应函数即可
  - 可作为模块导入，也可直接运行测试
"""

import json
import time
import hashlib
import requests
from datetime import datetime
from typing import Dict, List, Optional, Any

# ============================================================
# 配置部分（根据实际情况修改）
# ============================================================
CONFIG = {
    # 记忆网关地址
    "gateway_url": "http://123.207.202.158:9120",

    # 同源身份凭证（批量同步/节点注册时需要）
    "DID": "DID-BR-000002",
    "ROOT_OMEGA": "Ω-TAN-7-001",
    "TRACE_MARK": "Ω₀⊂⊙∞⊂Ω",

    # 本沙盒节点标识（自定义，建议唯一）
    "node_id": "sandbox-new-001",
    "node_type": "sandbox",
    "capabilities": ["truth_upsert", "truth_sync", "audit"],

    # 心跳配置
    "heartbeat_interval": 30,  # 秒
    "heartbeat_timeout": 120,   # 秒（2分钟无心跳标记离线）

    # 请求超时
    "request_timeout": 10,
}


# ============================================================
# 工具函数
# ============================================================
def _post(endpoint: str, data: Dict) -> Dict:
    """发送POST请求"""
    url = f"{CONFIG['gateway_url']}{endpoint}"
    try:
        resp = requests.post(url, json=data, timeout=CONFIG["request_timeout"])
        return resp.json()
    except requests.exceptions.RequestException as e:
        return {"status": "error", "msg": f"请求失败: {str(e)}"}


def _get(endpoint: str) -> Dict:
    """发送GET请求"""
    url = f"{CONFIG['gateway_url']}{endpoint}"
    try:
        resp = requests.get(url, timeout=CONFIG["request_timeout"])
        return resp.json()
    except requests.exceptions.RequestException as e:
        return {"status": "error", "msg": f"请求失败: {str(e)}"}


def calc_truth_hash(value: Any) -> str:
    """计算真值内容的SHA256哈希"""
    value_str = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
    return hashlib.sha256(value_str.encode()).hexdigest()


def ts_iso() -> str:
    """当前时间ISO格式"""
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


# ============================================================
# 一、节点管理
# ============================================================
def register_node() -> Dict:
    """
    注册节点（需同源验证）
    返回：节点ID、心跳间隔、超时时间、同步端点
    """
    data = {
        "DID": CONFIG["DID"],
        "ROOT_OMEGA": CONFIG["ROOT_OMEGA"],
        "node_id": CONFIG["node_id"],
        "node_type": CONFIG["node_type"],
        "capabilities": CONFIG["capabilities"],
    }
    result = _post("/api/node/register", data)
    if result.get("status") == "registered":
        print(f"[OK] 节点注册成功: {result['node_id']}")
        print(f"     心跳间隔: {result['heartbeat_interval']}秒")
        print(f"     超时阈值: {result['heartbeat_timeout']}秒")
        print(f"     同步端点: {result['sync_endpoint']}")
    else:
        print(f"[FAIL] 节点注册失败: {result.get('msg', '未知错误')}")
    return result


def send_heartbeat() -> Dict:
    """
    发送心跳（无需同源验证）
    建议每30秒调用一次
    """
    data = {"node_id": CONFIG["node_id"]}
    result = _post("/api/node/heartbeat", data)
    return result


def start_heartbeat_loop():
    """
    启动心跳循环（阻塞模式，建议在独立线程运行）
    """
    print(f"[INFO] 启动心跳循环，间隔 {CONFIG['heartbeat_interval']} 秒")
    while True:
        result = send_heartbeat()
        status = result.get("status", "unknown")
        print(f"[{ts_iso()}] 心跳: {status}")
        time.sleep(CONFIG["heartbeat_interval"])


def list_nodes() -> Dict:
    """获取所有节点列表（含在线状态）"""
    return _get("/api/nodes")


# ============================================================
# 二、真值上报（核心功能）
# ============================================================
def upsert_truth(
    key: str,
    value: Any,
    category: str = "",
    node_id: Optional[str] = None,
) -> Dict:
    """
    单条真值上报（无需同源验证，推荐使用）

    参数：
      key:       真值唯一键，建议点分命名法，如 "SANDBOX.001.STATUS"
      value:     真值内容，字符串或字典（会自动JSON序列化）
      category:  分类标签（可选）
      node_id:   上报节点ID（可选，默认用配置中的node_id）

    返回：
      {
        "success": true,
        "action": "inserted" | "updated",
        "key": "...",
        "truth_count": 1839,
        "validation": {...}
      }

    说明：
      - 自动进行语义前置校验（内容过短会跳过）
      - 自动计算SHA256哈希、版本号、时间戳
      - 相同key重复上报会更新版本号（version+1）
      - 所有操作自动写入审计日志
    """
    if not key:
        return {"status": "error", "msg": "key不能为空"}

    # value如果是字典，序列化为JSON字符串
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False)

    data = {
        "key": key,
        "value": value,
        "category": category,
        "node_id": node_id or CONFIG["node_id"],
    }
    result = _post("/api/truth/upsert", data)

    if result.get("success") or result.get("status") == "ok":
        action = result.get("action", "unknown")
        count = result.get("truth_count", "?")
        print(f"[OK] 真值上报成功 [{action}]: {key} (总量: {count})")
    else:
        print(f"[FAIL] 真值上报失败: {key} - {result.get('msg', '未知错误')}")

    return result


def sync_truths(truths: Dict[str, Any]) -> Dict:
    """
    批量真值同步（需同源验证）

    参数：
      truths: 真值字典，{key: value, ...}

    返回：
      {"status": "ok", "synced": 3, "total": 1841}

    说明：
      - 必须携带正确的DID和ROOT_OMEGA，否则返回403
      - 适合批量上报多条真值
      - value会自动JSON序列化
    """
    # 序列化字典/列表类型的value
    serialized = {}
    for k, v in truths.items():
        if isinstance(v, (dict, list)):
            serialized[k] = json.dumps(v, ensure_ascii=False)
        else:
            serialized[k] = v

    data = {
        "DID": CONFIG["DID"],
        "ROOT_OMEGA": CONFIG["ROOT_OMEGA"],
        "node_id": CONFIG["node_id"],
        "truths": serialized,
    }
    result = _post("/api/truth/sync", data)

    if result.get("status") == "ok":
        print(f"[OK] 批量同步成功: {result.get('synced', 0)}条 (总量: {result.get('total', '?')})")
    else:
        print(f"[FAIL] 批量同步失败: {result.get('msg', '未知错误')}")

    return result


# ============================================================
# 三、真值查询
# ============================================================
def get_truth(key: str) -> Dict:
    """获取单条真值"""
    return _get(f"/api/truth/{key}")


def list_truths() -> Dict:
    """获取所有真值列表"""
    return _get("/api/truths")


def get_truth_history(key: str) -> Dict:
    """获取真值变更历史"""
    return _get(f"/api/history/{key}")


def get_gateway_status() -> Dict:
    """获取网关状态（真值数、节点数、审计数）"""
    return _get("/api/status")


def get_audit_logs() -> Dict:
    """获取审计日志"""
    return _get("/api/audit")


# ============================================================
# 四、快捷上报模板（常用场景）
# ============================================================
def report_status(status: str, detail: Dict = None):
    """快捷上报：沙盒状态"""
    key = f"{CONFIG['node_id'].upper()}.STATUS"
    value = {
        "status": status,
        "timestamp": ts_iso(),
        "detail": detail or {},
    }
    return upsert_truth(key, value, category="sandbox_status")


def report_metric(metric_name: str, value: Any):
    """快捷上报：监控指标"""
    key = f"{CONFIG['node_id'].upper()}.METRIC.{metric_name.upper()}"
    data = {
        "metric": metric_name,
        "value": value,
        "timestamp": ts_iso(),
    }
    return upsert_truth(key, data, category="sandbox_metric")


def report_event(event_type: str, detail: Dict = None):
    """快捷上报：事件记录"""
    key = f"{CONFIG['node_id'].upper()}.EVENT.{event_type.upper()}.{int(time.time())}"
    data = {
        "event_type": event_type,
        "timestamp": ts_iso(),
        "detail": detail or {},
    }
    return upsert_truth(key, data, category="sandbox_event")


def report_config(config_key: str, config_value: Any):
    """快捷上报：配置项"""
    key = f"{CONFIG['node_id'].upper()}.CONFIG.{config_key.upper()}"
    return upsert_truth(key, config_value, category="sandbox_config")


# ============================================================
# 五、测试与示例
# ============================================================
def run_self_test():
    """运行自测：验证连接和基本功能"""
    print("=" * 60)
    print("ZONGYUAN-ROOT 新沙盒真值上报模板 - 自测")
    print("=" * 60)

    # 1. 网关状态
    print("\n[1/5] 检查网关状态...")
    status = get_gateway_status()
    if status.get("status") == "ok":
        stats = status.get("stats", {})
        print(f"  ✅ 网关在线 | 真值: {stats.get('truths')} | 节点: {stats.get('nodes')} | 审计: {stats.get('audit_logs')}")
    else:
        print(f"  ❌ 网关连接失败: {status}")
        return False

    # 2. 单条真值上报
    print("\n[2/5] 测试单条真值上报...")
    test_key = f"{CONFIG['node_id'].upper()}.SELFTEST"
    result = upsert_truth(
        key=test_key,
        value={"test": "ok", "timestamp": ts_iso()},
        category="selftest",
    )
    if not (result.get("success") or result.get("status") == "ok"):
        print(f"  ❌ 上报失败: {result}")
        return False

    # 3. 查询真值
    print("\n[3/5] 测试真值查询...")
    truth = get_truth(test_key)
    if truth.get("status") == "ok" or "truth_key" in str(truth):
        print(f"  ✅ 查询成功: {test_key}")
    else:
        print(f"  ⚠️  查询结果: {truth}")

    # 4. 批量同步
    print("\n[4/5] 测试批量真值同步...")
    batch = {
        f"{CONFIG['node_id'].upper()}.BATCH.1": "value1",
        f"{CONFIG['node_id'].upper()}.BATCH.2": {"nested": "data"},
    }
    sync_result = sync_truths(batch)
    if sync_result.get("status") != "ok":
        print(f"  ⚠️  批量同步需同源验证，如失败请检查DID/ROOT_OMEGA配置")

    # 5. 节点列表
    print("\n[5/5] 获取节点列表...")
    nodes = list_nodes()
    count = nodes.get("count", "?")
    print(f"  ✅ 当前注册节点数: {count}")

    print("\n" + "=" * 60)
    print("自测完成！模板可正常使用。")
    print("=" * 60)
    return True


# ============================================================
# 主入口
# ============================================================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="ZONGYUAN-ROOT 新沙盒真值上报模板")
    parser.add_argument("--selftest", action="store_true", help="运行自测")
    parser.add_argument("--register", action="store_true", help="注册节点")
    parser.add_argument("--heartbeat", action="store_true", help="启动心跳循环")
    parser.add_argument("--status", type=str, help="快捷上报状态")
    parser.add_argument("--key", type=str, help="上报真值的key")
    parser.add_argument("--value", type=str, help="上报真值的value")

    args = parser.parse_args()

    if args.selftest:
        run_self_test()
    elif args.register:
        register_node()
    elif args.heartbeat:
        start_heartbeat_loop()
    elif args.key and args.value:
        upsert_truth(args.key, args.value)
    elif args.status:
        report_status(args.status)
    else:
        print("ZONGYUAN-ROOT 新沙盒真值上报模板")
        print(f"节点ID: {CONFIG['node_id']}")
        print(f"网关地址: {CONFIG['gateway_url']}")
        print("")
        print("使用方法:")
        print("  python sandbox_truth_reporter.py --selftest    # 运行自测")
        print("  python sandbox_truth_reporter.py --register     # 注册节点")
        print("  python sandbox_truth_reporter.py --heartbeat    # 启动心跳循环")
        print("  python sandbox_truth_reporter.py --key KEY --value VALUE  # 上报单条真值")
        print("  python sandbox_truth_reporter.py --status running  # 快捷上报状态")
        print("")
        print("作为模块导入:")
        print("  from sandbox_truth_reporter import upsert_truth, sync_truths, register_node")
        print("  upsert_truth('MY.KEY', {'data': 'value'})")
