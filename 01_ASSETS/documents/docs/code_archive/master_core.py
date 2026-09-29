#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
元极恒一｜主中枢核心 (MASTER CORE)
职责：全局裁决、Merkle根管理、次中枢节点管理、指令调度、结果收集、全域广播
溯源：Ω₀⊂⊙∞⊂Ω｜DID-BR-000002
"""
import sys
import json
import time
import sqlite3
import requests
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(BASE_DIR / "comm" / "protocol"))
sys.path.insert(0, str(BASE_DIR / "config"))
sys.path.insert(0, str(BASE_DIR))
from comm_protocol import (
    ensure_queue_dirs, build_message, write_message, read_messages,
    write_broadcast, read_broadcast, sha256_str,
    MSG_TYPE_HANDSHAKE, MSG_TYPE_HEARTBEAT, MSG_TYPE_COMMAND,
    MSG_TYPE_RESULT, MSG_TYPE_BROADCAST, MSG_TYPE_APPROVAL,
    ACTION_SCAN_ASSET, ACTION_RUN_PIPELINE, ACTION_CROSS_VERIFY,
    ACTION_SYNC_LEDGER, ACTION_RELOAD_RULE, ACTION_STOP
)
# 统一数据库连接模块（自动设置PRAGMA: WAL/NORMAL/20MB缓存）
from comm.db_utils import get_connection

# 配置加载器（支持热加载，失败时降级为默认值）
try:
    from config_loader import config as _config
    _CONFIG_AVAILABLE = True
except ImportError:
    _CONFIG_AVAILABLE = False

def _cfg(key, default):
    """从配置加载器读取，失败返回默认值"""
    if _CONFIG_AVAILABLE:
        return _config.get(key, default)
    return default

MASTER_DB = BASE_DIR / "master" / "core" / "master_state.db"
MASTER_PID = BASE_DIR / "master" / "master.pid"
LOG_DIR = BASE_DIR / "logs"
GATEWAY_URL = _cfg("gateway.base_url", "https://www.huodouai.com") + _cfg("gateway.truth_report_endpoint", "/api/report/truth")
DID = _cfg("system.did", "DID-BR-000002")
TRACE = _cfg("system.trace", "Ω₀⊂⊙∞⊂Ω")
LOOP_INTERVAL = _cfg("master.loop_interval", 15)
HEARTBEAT_TIMEOUT = _cfg("master.heartbeat_timeout", 120)


def log(msg, level="INFO"):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [MASTER] [{level}] {msg}"
    print(line, flush=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOG_DIR / f"master_{time.strftime('%Y%m%d')}.log", "a") as f:
        f.write(line + "\n")


def init_master_db():
    """初始化主中枢状态数据库"""
    MASTER_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection(MASTER_DB)
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS nodes (
        node_id TEXT PRIMARY KEY,
        node_type TEXT DEFAULT 'slave',
        status TEXT DEFAULT 'offline',
        last_heartbeat REAL,
        register_time REAL,
        cpu_usage REAL,
        mem_usage REAL,
        disk_usage REAL,
        asset_count INTEGER DEFAULT 0
    )''')
    cur.execute('''CREATE TABLE IF NOT EXISTS commands (
        cmd_id TEXT PRIMARY KEY,
        action TEXT,
        target_node TEXT,
        payload TEXT,
        status TEXT DEFAULT 'pending',
        create_time REAL,
        result TEXT
    )''')
    cur.execute('''CREATE TABLE IF NOT EXISTS merkle_roots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        root_hash TEXT,
        leaf_count INTEGER,
        create_time REAL,
        source TEXT
    )''')
    cur.execute('''CREATE TABLE IF NOT EXISTS approvals (
        approval_id TEXT PRIMARY KEY,
        title TEXT,
        status TEXT DEFAULT 'pending',
        payload TEXT,
        create_time REAL,
        approve_time REAL
    )''')
    conn.commit()
    conn.close()
    log("主中枢状态数据库初始化完成")


def register_node(node_id, node_type="slave"):
    """注册次中枢节点"""
    conn = get_connection(MASTER_DB)
    cur = conn.cursor()
    cur.execute('''INSERT OR REPLACE INTO nodes
    (node_id, node_type, status, last_heartbeat, register_time)
    VALUES (?, ?, 'online', ?, ?)''',
    (node_id, node_type, time.time(), time.time()))
    conn.commit()
    conn.close()
    log(f"节点注册: {node_id} ({node_type})")


def update_heartbeat(node_id, energy_snapshot=None):
    """更新节点心跳"""
    conn = get_connection(MASTER_DB)
    cur = conn.cursor()
    if energy_snapshot:
        cur.execute('''UPDATE nodes SET status='online', last_heartbeat=?,
        cpu_usage=?, mem_usage=?, disk_usage=? WHERE node_id=?''',
        (time.time(), energy_snapshot.get("cpu_usage"),
         energy_snapshot.get("mem_usage_pct"), energy_snapshot.get("disk_usage_pct"), node_id))
    else:
        cur.execute('''UPDATE nodes SET status='online', last_heartbeat=? WHERE node_id=?''',
        (time.time(), node_id))
    conn.commit()
    conn.close()


def check_offline_nodes():
    """检查超时离线节点"""
    conn = get_connection(MASTER_DB)
    cur = conn.cursor()
    cutoff = time.time() - HEARTBEAT_TIMEOUT
    cur.execute("UPDATE nodes SET status='offline' WHERE last_heartbeat < ? AND status='online'", (cutoff,))
    cur.execute("SELECT node_id FROM nodes WHERE status='offline'")
    offline = [r[0] for r in cur.fetchall()]
    conn.commit()
    conn.close()
    if offline:
        log(f"⚠️ 节点离线: {offline}", "WARN")


def get_online_nodes():
    """获取在线节点列表"""
    conn = get_connection(MASTER_DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM nodes WHERE status='online'")
    nodes = [dict(r) for r in cur.fetchall()]
    conn.close()
    return nodes


def dispatch_command(action, target_node="ALL", payload=None):
    """主中枢裁决并下发指令"""
    # 逻辑态裁决：校验指令合法性
    allowed_actions = [ACTION_SCAN_ASSET, ACTION_RUN_PIPELINE, ACTION_CROSS_VERIFY,
                       ACTION_SYNC_LEDGER, ACTION_RELOAD_RULE, ACTION_STOP]
    if action not in allowed_actions:
        log(f"指令被裁决拒绝: 未知动作 {action}", "WARN")
        return {"status": "deny", "reason": f"未知动作: {action}"}

    cmd_id = f"CMD-{int(time.time())}-{sha256_str(action+target_node)[:8]}"
    msg = build_message(MSG_TYPE_COMMAND, "MASTER", target_node, {
        "cmd_id": cmd_id,
        "action": action,
        "payload": payload or {}
    }, priority=5)

    # 写入消息队列
    if target_node == "ALL":
        write_message("master_out", msg)
        log(f"全域指令下发: {action} -> ALL")
    else:
        write_message("master_out", msg)
        log(f"指令下发: {action} -> {target_node}")

    # 记录到数据库
    conn = get_connection(MASTER_DB)
    cur = conn.cursor()
    cur.execute('''INSERT INTO commands (cmd_id, action, target_node, payload, status, create_time)
    VALUES (?,?,?,?, 'dispatched', ?)''',
    (cmd_id, action, target_node, json.dumps(payload or {}, ensure_ascii=False), time.time()))
    conn.commit()
    conn.close()

    return {"status": "dispatched", "cmd_id": cmd_id, "action": action, "target": target_node}


def collect_results():
    """收集次中枢执行结果"""
    results = read_messages("master_in")
    for msg in results:
        payload = msg.get("payload", {})
        cmd_id = payload.get("cmd_id", "")
        result = payload.get("result", {})
        conn = get_connection(MASTER_DB)
        cur = conn.cursor()
        cur.execute("UPDATE commands SET status='completed', result=? WHERE cmd_id=?",
                    (json.dumps(result, ensure_ascii=False), cmd_id))
        conn.commit()
        conn.close()
        log(f"结果回收: {cmd_id} from {msg['source']} | {result.get('ok', 'N/A')}")
    return results


def process_handshakes():
    """处理次中枢握手注册"""
    msgs = read_messages("master_in")
    for msg in msgs:
        if msg["msg_type"] == MSG_TYPE_HANDSHAKE:
            node_id = msg["source"]
            register_node(node_id)
            # 回复握手确认
            ack = build_message(MSG_TYPE_HANDSHAKE, "MASTER", node_id, {
                "status": "registered",
                "master_time": time.time(),
                "did": DID
            })
            write_message("master_out", ack)
        elif msg["msg_type"] == MSG_TYPE_HEARTBEAT:
            node_id = msg["source"]
            energy = msg["payload"].get("energy_snapshot")
            update_heartbeat(node_id, energy)


def update_merkle_root(root_hash, leaf_count, source="pipeline"):
    """更新全域Merkle根"""
    conn = get_connection(MASTER_DB)
    cur = conn.cursor()
    cur.execute('''INSERT INTO merkle_roots (root_hash, leaf_count, create_time, source)
    VALUES (?,?,?,?)''', (root_hash, leaf_count, time.time(), source))
    conn.commit()
    conn.close()
    log(f"全域Merkle根更新: {root_hash[:16]}... ({leaf_count}叶子)")


def get_latest_merkle_root():
    """获取最新Merkle根"""
    conn = get_connection(MASTER_DB)
    cur = conn.cursor()
    cur.execute("SELECT root_hash, leaf_count FROM merkle_roots ORDER BY create_time DESC LIMIT 1")
    row = cur.fetchone()
    conn.close()
    return row if row else ("", 0)


def broadcast_to_all(payload):
    """全域广播（审批通过后触发）"""
    msg = build_message(MSG_TYPE_BROADCAST, "MASTER", "ALL", payload, priority=10)
    write_broadcast(msg)
    log(f"全域广播: {payload.get('action', 'N/A')}")
    return msg


def report_to_gateway(truth_key, truth_value, truth_type="protocol", confidence=0.98):
    """上报真值到记忆网关"""
    try:
        resp = requests.post(GATEWAY_URL, json={
            "truth_key": truth_key,
            "truth_value": truth_value,
            "source_node": DID,
            "confidence": confidence,
            "truth_type": truth_type
        }, timeout=15)
        data = resp.json()
        success = data.get("written_to_gateway", False) or data.get("success", False)
        if success:
            log(f"网关真值上报成功: {truth_key}")
        return data
    except Exception as e:
        log(f"网关上报异常: {e}", "ERROR")
        return {"error": str(e)}


class MasterCore:
    def __init__(self):
        self.running = True
        self.loop_count = 0

    def main_loop(self):
        log("=" * 60)
        log("元极恒一主中枢 (MASTER CORE) 启动")
        log(f"PID: {__import__('os').getpid()}")
        log(f"溯源: {TRACE} | {DID}")
        log("=" * 60)

        ensure_queue_dirs()
        init_master_db()

        # 主中枢自注册
        register_node("MASTER", "master")

        # 上报主中枢启动真值
        report_to_gateway("MASTER.CORE.STARTED",
            json.dumps({"status": "active", "pid": __import__('os').getpid(), "time": time.time()}, ensure_ascii=False),
            "meta_law", 1.0)

        while self.running:
            self.loop_count += 1
            log(f"--- 主中枢循环第 {self.loop_count} 轮 ---")

            # 0. 主中枢自更新心跳（防止自己被标记离线）
            update_heartbeat("MASTER")

            # 1. 处理握手和心跳
            process_handshakes()

            # 2. 收集执行结果
            collect_results()

            # 3. 检查离线节点
            check_offline_nodes()

            # 4. 处理广播
            broadcasts = read_broadcast()
            for b in broadcasts:
                log(f"处理广播: {b['msg_id']}")

            # 5. 每10轮上报主中枢心跳到网关
            if self.loop_count % 10 == 0:
                online = get_online_nodes()
                report_to_gateway("MASTER.CORE.HEARTBEAT",
                    json.dumps({"online_nodes": len(online), "loop": self.loop_count}, ensure_ascii=False),
                    "protocol", 0.98)

            time.sleep(LOOP_INTERVAL)

        log("主中枢已停止")


def main():
    MASTER_PID.write_text(str(__import__('os').getpid()))
    core = MasterCore()
    try:
        core.main_loop()
    except KeyboardInterrupt:
        core.running = False
        log("收到中断信号，主中枢优雅退出")
    finally:
        if MASTER_PID.exists():
            MASTER_PID.unlink()


if __name__ == "__main__":
    main()
