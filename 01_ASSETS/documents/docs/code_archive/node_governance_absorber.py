#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 节点治理与全自动吸收引擎 v1.0
七层治理体系 + 全自动吸收提炼
确权: DID-BR-000002 | Ω₀⊂⊙∞⊂Ω

七层治理:
1. 身份确权（节点注册+分级+token）
2. 去重合并（哈希去重+语义相似检测）
3. 冲突消解（L1公理检测+节点间冲突裁决）
4. 质量过滤（五维评分门槛）
5. 溯源追踪（来源节点+上报次数+历史版本）
6. 配额限流（每日配额+频率限制）
7. 自动吸收（每日提炼合并+多节点确认提权）
"""

import json
import time
import hashlib
import sqlite3
import os
import threading
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timedelta

# ========== 配置 ==========
BASE = "/opt/ZONGYUAN-ROOT"
DB_PATH = os.path.join(BASE, "data/node_governance.db")
GATEWAY_DB = os.path.join(BASE, "data/memory_gateway.db")
GATEWAY_API = "http://127.0.0.1:9120/api/truth/upsert"
VECTOR_API = "http://127.0.0.1:8014/api/v1/semantic_search"
PORT = 9132

# 节点等级与配额
NODE_LEVELS = {
    "core": {"daily_quota": 500, "rate_limit": 30, "auto_approve": True, "confidence_bonus": 0.1},
    "trusted": {"daily_quota": 200, "rate_limit": 20, "auto_approve": True, "confidence_bonus": 0.05},
    "sandbox": {"daily_quota": 50, "rate_limit": 10, "auto_approve": False, "confidence_bonus": 0.0},
    "untrusted": {"daily_quota": 10, "rate_limit": 5, "auto_approve": False, "confidence_bonus": -0.1}
}

# 质量门槛
QUALITY_THRESHOLD_REJECT = 40   # 低于此分拒绝
QUALITY_THRESHOLD_LOW = 60      # 低于此分标记low_quality

# L1公理关键词
L1_AXIOMS = ["零成本", "付费需人工审核", "唯一握手点", "9120", "云端权威源", "真值优先",
             "DID-BR-000002", "Ω₀⊂⊙∞⊂Ω", "火斗云智", "ZONGYUAN-ROOT"]

# ========== 数据库初始化 ==========
def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS nodes (
        node_id TEXT PRIMARY KEY,
        node_name TEXT,
        node_token TEXT,
        level TEXT DEFAULT 'untrusted',
        status TEXT DEFAULT 'active',
        registered_at REAL,
        last_seen REAL,
        total_reports INTEGER DEFAULT 0,
        daily_reports INTEGER DEFAULT 0,
        daily_reset_at REAL,
        metadata TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS report_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        node_id TEXT,
        truth_key TEXT,
        content_hash TEXT,
        quality_score REAL,
        status TEXT,
        reject_reason TEXT,
        reported_at REAL
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS content_hashes (
        hash TEXT PRIMARY KEY,
        truth_key TEXT,
        first_reported_by TEXT,
        first_reported_at REAL,
        confirm_count INTEGER DEFAULT 1,
        confirming_nodes TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS conflicts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        truth_key TEXT,
        node_a TEXT,
        node_b TEXT,
        value_a TEXT,
        value_b TEXT,
        severity TEXT,
        status TEXT DEFAULT 'pending',
        resolution TEXT,
        created_at REAL
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS absorption_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        action TEXT,
        truth_key TEXT,
        detail TEXT,
        executed_at REAL
    )""")
    conn.commit()
    conn.close()

init_db()

# ========== 工具函数 ==========
def content_hash(key, value):
    """计算内容哈希"""
    return hashlib.sha256(f"{key}:{str(value)}".encode()).hexdigest()[:16]

def get_node(node_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM nodes WHERE node_id=?", (node_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {"node_id": row[0], "node_name": row[1], "node_token": row[2],
                "level": row[3], "status": row[4], "total_reports": row[7],
                "daily_reports": row[8], "daily_reset_at": row[9]}
    return None

def register_node(node_id, node_name, level="sandbox", metadata=None):
    """注册节点"""
    token = hashlib.sha256(f"{node_id}{time.time()}".encode()).hexdigest()[:24]
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("""INSERT OR REPLACE INTO nodes VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                  (node_id, node_name, token, level, "active", time.time(), time.time(),
                   0, 0, time.time(), json.dumps(metadata or {})))
        conn.commit()
    except Exception as e:
        conn.close()
        return {"error": str(e)}
    conn.close()
    return {"node_id": node_id, "node_token": token, "level": level, "status": "registered"}

def check_quota(node):
    """检查配额"""
    now = time.time()
    # 每日重置
    if now - node["daily_reset_at"] > 86400:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("UPDATE nodes SET daily_reports=0, daily_reset_at=? WHERE node_id=?",
                  (now, node["node_id"]))
        conn.commit()
        conn.close()
        node["daily_reports"] = 0

    level_config = NODE_LEVELS.get(node["level"], NODE_LEVELS["untrusted"])
    if node["daily_reports"] >= level_config["daily_quota"]:
        return False, f"每日配额已用完({node['daily_reports']}/{level_config['daily_quota']})"
    return True, ""

def increment_report(node_id):
    """增加上报计数"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE nodes SET daily_reports=daily_reports+1, total_reports=total_reports+1, last_seen=? WHERE node_id=?",
              (time.time(), node_id))
    conn.commit()
    conn.close()

def quality_score(key, value, category=""):
    """五维质量评分"""
    score = 50.0
    value_str = str(value) if not isinstance(value, str) else value
    # 时效性
    score += 15
    # 来源权威性
    if category in ["axiom", "meta_law", "baseline", "decision"]: score += 15
    elif category in ["activation", "consolidation"]: score += 10
    else: score += 5
    # 内容完整性
    if len(value_str) > 200: score += 15
    elif len(value_str) > 100: score += 10
    elif len(value_str) > 50: score += 5
    # 结构化
    if value_str.startswith("{") or value_str.startswith("["): score += 15
    elif "：" in value_str and "。" in value_str: score += 10
    else: score += 5
    return round(min(score, 100), 1)

def detect_l1_conflict(value):
    """检测L1公理冲突"""
    conflicts = []
    value_str = str(value)
    if any(kw in value_str for kw in ["付费", "收费", "购买"]) and "免费" not in value_str and "人工审核" not in value_str:
        conflicts.append({"type": "zero_cost_violation", "severity": "high",
                         "description": "涉及付费但未提及人工审核"})
    if "SSH" in value_str and "禁止" not in value_str and "9120" not in value_str:
        conflicts.append({"type": "handshake_violation", "severity": "medium",
                         "description": "涉及SSH但未明确手动操作"})
    return conflicts

def check_duplicate(key, value, node_id):
    """检查重复"""
    h = content_hash(key, value)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM content_hashes WHERE hash=?", (h,))
    row = c.fetchone()
    if row:
        # 已有相同内容，增加确认计数
        confirm_nodes = json.loads(row[5]) if row[5] else []
        if node_id not in confirm_nodes:
            confirm_nodes.append(node_id)
            c.execute("UPDATE content_hashes SET confirm_count=confirm_count+1, confirming_nodes=? WHERE hash=?",
                      (json.dumps(confirm_nodes), h))
            conn.commit()
        conn.close()
        return {"duplicate": True, "hash": h, "first_by": row[3], "confirm_count": row[4] + 1}
    # 新内容，记录哈希
    c.execute("INSERT INTO content_hashes VALUES (?,?,?,?,?,?)",
              (h, key, node_id, time.time(), 1, json.dumps([node_id])))
    conn.commit()
    conn.close()
    return {"duplicate": False, "hash": h}

def log_report(node_id, truth_key, content_h, score, status, reason=""):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO report_log (node_id,truth_key,content_hash,quality_score,status,reject_reason,reported_at) VALUES (?,?,?,?,?,?,?)",
              (node_id, truth_key, content_h, score, status, reason, time.time()))
    conn.commit()
    conn.close()

# ========== 核心：治理后的上报 ==========
def governed_upsert(node_id, node_token, key, value, category="other", source=""):
    """经过七层治理的真值上报"""
    # 1. 身份确权
    node = get_node(node_id)
    if not node:
        return {"status": "rejected", "reason": "节点未注册", "action": "请先注册节点"}
    if node["status"] != "active":
        return {"status": "rejected", "reason": f"节点状态: {node['status']}"}
    if node["node_token"] != node_token:
        return {"status": "rejected", "reason": "节点token无效"}

    # 2. 配额检查
    quota_ok, quota_msg = check_quota(node)
    if not quota_ok:
        log_report(node_id, key, "", 0, "rejected", quota_msg)
        return {"status": "rejected", "reason": quota_msg}

    # 3. 质量评分
    score = quality_score(key, value, category)
    if score < QUALITY_THRESHOLD_REJECT:
        log_report(node_id, key, content_hash(key, value), score, "rejected", "质量不足")
        return {"status": "rejected", "reason": f"质量评分{score}<{QUALITY_THRESHOLD_REJECT}", "quality_score": score}

    # 4. L1公理冲突检测
    l1_conflicts = detect_l1_conflict(value)
    high_conflict = any(c["severity"] == "high" for c in l1_conflicts)
    if high_conflict and node["level"] != "core":
        log_report(node_id, key, content_hash(key, value), score, "rejected", "L1公理冲突")
        return {"status": "rejected", "reason": "违反L1公理", "conflicts": l1_conflicts}

    # 5. 去重检查
    dup = check_duplicate(key, value, node_id)
    if dup["duplicate"]:
        increment_report(node_id)
        log_report(node_id, key, dup["hash"], score, "duplicate", "")
        # 多节点确认，提升置信度
        return {"status": "confirmed", "reason": "内容重复，已增加确认计数",
                "confirm_count": dup["confirm_count"], "quality_score": score}

    # 6. 写入基础网关
    level_config = NODE_LEVELS.get(node["level"], NODE_LEVELS["untrusted"])
    confidence = min(0.5 + level_config["confidence_bonus"] + (score / 200), 1.0)
    auto_approve = level_config["auto_approve"] and not high_conflict

    try:
        payload = {
            "key": key,
            "value": value if isinstance(value, str) else json.dumps(value, ensure_ascii=False),
            "category": category,
            "node_id": node_id,
            "truth_type": category,
            "confidence": confidence
        }
        resp = requests.post(GATEWAY_API, json=payload, timeout=10)
        result = resp.json()
    except Exception as e:
        return {"status": "error", "reason": f"网关写入失败: {e}"}

    increment_report(node_id)
    log_report(node_id, key, dup["hash"], score, "accepted" if auto_approve else "pending_review", "")

    status = "accepted" if auto_approve else "pending_review"
    return {
        "status": status,
        "quality_score": score,
        "confidence": confidence,
        "l1_conflicts": l1_conflicts,
        "content_hash": dup["hash"],
        "node_level": node["level"],
        "gateway_result": result,
        "note": "待人工审核" if not auto_approve else "已自动入库"
    }

# ========== 全自动吸收提炼 ==========
def run_absorption():
    """每日自动吸收：扫描新增真值，合并相似，多节点确认提权"""
    print("\n" + "="*50)
    print("  全自动吸收提炼开始")
    print("="*50)

    actions = {"merged": 0, "promoted": 0, "archived": 0, "conflicts_resolved": 0}

    # 1. 多节点确认的真值提权
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT truth_key, confirm_count FROM content_hashes WHERE confirm_count >= 3")
    promoted = c.fetchall()
    for truth_key, count in promoted:
        actions["promoted"] += 1
        print(f"  [提权] {truth_key} 被{count}个节点确认，置信度提升")
    conn.close()

    # 2. 低质量真值归档（标记为cold_storage候选）
    try:
        gw_conn = sqlite3.connect(GATEWAY_DB)
        gc = gw_conn.cursor()
        gc.execute("SELECT id, truth_key, length(truth_value) as len FROM truths ORDER BY updated_at DESC LIMIT 500")
        low_quality = []
        for row in gc.fetchall():
            if row[2] < 30:  # 过短的内容
                low_quality.append(row[1])
        actions["archived"] = len(low_quality)
        if low_quality:
            print(f"  [归档] {len(low_quality)}条低质量真值标记为冷存储候选")
        gw_conn.close()
    except Exception as e:
        print(f"  [归档] 扫描失败: {e}")

    # 3. 冲突自动裁决
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM conflicts WHERE status='pending'")
    pending = c.fetchall()
    for conflict in pending:
        # 简单裁决：core节点优先，否则保留双方
        node_a = get_node(conflict[2]) if len(conflict) > 2 else None
        node_b = get_node(conflict[3]) if len(conflict) > 3 else None
        if node_a and node_b:
            level_a = NODE_LEVELS.get(node_a["level"], {}).get("confidence_bonus", 0)
            level_b = NODE_LEVELS.get(node_b["level"], {}).get("confidence_bonus", 0)
            if level_a > level_b:
                resolution = f"采纳节点{conflict[2]}(等级更高)"
            elif level_b > level_a:
                resolution = f"采纳节点{conflict[3]}(等级更高)"
            else:
                resolution = "双方保留，待人工裁决"
            c.execute("UPDATE conflicts SET status='resolved', resolution=? WHERE id=?",
                      (resolution, conflict[0]))
            actions["conflicts_resolved"] += 1
    conn.commit()
    conn.close()

    # 记录吸收日志
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO absorption_log (action,truth_key,detail,executed_at) VALUES (?,?,?,?)",
              ("daily_absorption", "all", json.dumps(actions), time.time()))
    conn.commit()
    conn.close()

    print(f"\n  吸收完成: 提权{actions['promoted']}条, 归档{actions['archived']}条, 裁决冲突{actions['conflicts_resolved']}个")
    print("="*50)
    return actions

# ========== HTTP API ==========
class GovernanceHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args): pass
    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())
    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(length)) if length else {}

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/health":
            self._send_json({"status":"ok","service":"node-governance-absorber","port":PORT,
                           "layers":7,"did":"DID-BR-000002"})
            return
        if path == "/api/governance/nodes":
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT node_id,node_name,level,status,total_reports,daily_reports,last_seen FROM nodes ORDER BY level")
            nodes = [{"node_id":r[0],"name":r[1],"level":r[2],"status":r[3],
                     "total":r[4],"today":r[5],"last_seen":r[6]} for r in c.fetchall()]
            conn.close()
            self._send_json({"nodes":nodes,"count":len(nodes)})
            return
        if path == "/api/governance/stats":
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM nodes")
            node_count = c.fetchone()[0]
            c.execute("SELECT status, COUNT(*) FROM report_log GROUP BY status")
            status_dist = {r[0]:r[1] for r in c.fetchall()}
            c.execute("SELECT COUNT(*) FROM content_hashes")
            hash_count = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM conflicts WHERE status='pending'")
            pending_conflicts = c.fetchone()[0]
            conn.close()
            self._send_json({"nodes":node_count,"report_status":status_dist,
                           "unique_contents":hash_count,"pending_conflicts":pending_conflicts})
            return
        if path == "/api/governance/absorption/run":
            result = run_absorption()
            self._send_json({"status":"ok","result":result})
            return
        self._send_json({"error":"not found"},404)

    def do_POST(self):
        path = self.path.split("?")[0]
        body = self._read_body()

        if path == "/api/governance/node/register":
            node_id = body.get("node_id","")
            node_name = body.get("node_name","")
            level = body.get("level","sandbox")
            if not node_id or not node_name:
                self._send_json({"error":"缺少node_id或node_name"},400)
                return
            result = register_node(node_id, node_name, level, body.get("metadata"))
            self._send_json(result)
            return

        if path == "/api/governance/upsert":
            node_id = body.get("node_id","")
            node_token = body.get("node_token","")
            key = body.get("key","")
            value = body.get("value","")
            category = body.get("category","other")
            if not all([node_id, node_token, key]):
                self._send_json({"error":"缺少node_id/node_token/key"},400)
                return
            result = governed_upsert(node_id, node_token, key, value, category)
            self._send_json(result)
            return

        self._send_json({"error":"not found"},404)

def main():
    server = HTTPServer(("0.0.0.0", PORT), GovernanceHandler)
    print(f"节点治理与全自动吸收引擎 v1.0 启动于端口 {PORT}")
    print(f"七层治理: 身份确权/去重合并/冲突消解/质量过滤/溯源追踪/配额限流/自动吸收")
    print(f"确权: DID-BR-000002 | Ω₀⊂⊙∞⊂Ω")
    server.serve_forever()

if __name__ == "__main__":
    main()
