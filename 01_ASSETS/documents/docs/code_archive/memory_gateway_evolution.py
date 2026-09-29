#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 记忆网关进化引擎 v1.0
端口: 9121 (进化版，代理9120基础功能)
确权: DID-BR-000002 | Ω₀⊂⊙∞⊂Ω

进化功能:
P0: 结构化真值对象 + 类型体系 + 冲突检测
P1: 语义检索聚合 + 订阅推送 + 批量API
P2: 质量评分 + 版本管理 + 审计查询 + 内存缓存
"""

import json
import time
import hashlib
import sqlite3
import threading
import urllib.request
from http.server import HTTPServer, BaseHTTPRequestHandler
from collections import OrderedDict

# ========== 配置 ==========
BASE_PORT = 9120          # 基础网关
EVOLUTION_PORT = 9121     # 进化网关
VECTOR_PORT = 8014        # 向量库
DB_PATH = "/opt/ZONGYUAN-ROOT/data/memory_gateway.db"
CACHE_SIZE = 500          # 内存缓存条数
SUBSCRIBERS_FILE = "/opt/ZONGYUAN-ROOT/config/gateway_subscribers.json"

# 真值类型体系
TRUTH_TYPES = [
    "axiom",           # 公理类 (L0/L1)
    "meta_law",        # 元法则
    "service_status",  # 服务状态
    "config",          # 配置
    "decision",        # 决策记录
    "alert",           # 告警
    "distillation",    # 蒸馏样本
    "baseline",        # 基准
    "activation",      # 激活记录
    "integration",     # 整合记录
    "cleanup",         # 清理记录
    "consolidation",   # 固化记录
    "security",        # 安全事件
    "drama",           # 短剧相关
    "knowledge",       # 知识
    "other"            # 其他
]

# L1公理关键词（用于冲突检测）
L1_AXIOM_KEYWORDS = ["零成本", "付费需人工审核", "唯一握手点", "9120", "云端权威源",
                     "真值优先", "DID-BR-000002", "Ω₀⊂⊙∞⊂Ω", "火斗云智", "ZONGYUAN-ROOT"]

# ========== 内存缓存 (LRU) ==========
class LRUCache:
    def __init__(self, capacity=500):
        self.cache = OrderedDict()
        self.capacity = capacity
        self.lock = threading.Lock()
        self.hits = 0
        self.misses = 0

    def get(self, key):
        with self.lock:
            if key in self.cache:
                self.cache.move_to_end(key)
                self.hits += 1
                return self.cache[key]
            self.misses += 1
            return None

    def set(self, key, value):
        with self.lock:
            if key in self.cache:
                self.cache.move_to_end(key)
            self.cache[key] = value
            if len(self.cache) > self.capacity:
                self.cache.popitem(last=False)

    def stats(self):
        with self.lock:
            total = self.hits + self.misses
            return {
                "size": len(self.cache),
                "capacity": self.capacity,
                "hits": self.hits,
                "misses": self.misses,
                "hit_rate": round(self.hits / total * 100, 1) if total > 0 else 0
            }

cache = LRUCache(CACHE_SIZE)

# ========== 订阅者管理 ==========
def load_subscribers():
    try:
        with open(SUBSCRIBERS_FILE) as f:
            return json.load(f)
    except:
        return {"subscribers": []}

def save_subscribers(subs):
    with open(SUBSCRIBERS_FILE, "w") as f:
        json.dump(subs, f, ensure_ascii=False, indent=2)

def notify_subscribers(event_type, truth_data):
    """真值变更时推送给订阅者"""
    subs = load_subscribers()
    notified = 0
    for sub in subs.get("subscribers", []):
        if not sub.get("active", True):
            continue
        # 过滤事件类型
        if sub.get("event_types") and event_type not in sub["event_types"]:
            continue
        try:
            req = urllib.request.Request(
                sub["webhook_url"],
                data=json.dumps({"event": event_type, "truth": truth_data, "timestamp": time.time()}).encode(),
                headers={"Content-Type": "application/json"}
            )
            urllib.request.urlopen(req, timeout=5)
            notified += 1
        except Exception as e:
            print(f"[订阅推送失败] {sub.get('name','?')}: {e}")
    return notified

# ========== 冲突检测 ==========
def detect_conflict(key, value, category=""):
    """检测新真值与L1公理/元法则的冲突"""
    conflicts = []
    value_str = str(value) if not isinstance(value, str) else value

    # 1. 检查是否与零成本公理冲突
    if any(kw in value_str for kw in ["付费", "收费", "购买", "充值"]) and "免费" not in value_str:
        if "零成本" not in value_str and "人工审核" not in value_str:
            conflicts.append({
                "type": "axiom_conflict",
                "axiom": "零成本运行（付费需人工审核）",
                "severity": "high",
                "description": "内容涉及付费但未提及人工审核机制"
            })

    # 2. 检查是否与唯一握手点公理冲突
    if "SSH" in value_str and "禁止" not in value_str and "9120" not in value_str:
        conflicts.append({
            "type": "axiom_conflict",
            "axiom": "唯一握手点9120（禁止SSH自动同步）",
            "severity": "medium",
            "description": "内容涉及SSH但未明确是手动操作"
        })

    # 3. 检查key是否与已有元法则重复但内容不同
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT truth_value FROM truths WHERE truth_key=? AND truth_key LIKE 'MR-%'", (key,))
        existing = c.fetchone()
        if existing and existing[0] != value_str:
            conflicts.append({
                "type": "version_change",
                "severity": "low",
                "description": f"元法则{key}内容已变更，旧版本已归档"
            })
        conn.close()
    except:
        pass

    return conflicts

# ========== 真值质量评分 ==========
def score_truth(key, value, category="", truth_id=None):
    """五维质量评分: 引用频率/置信度/时效性/来源权威性/逻辑一致性"""
    score = 50.0  # 基础分
    value_str = str(value) if not isinstance(value, str) else value

    # 1. 时效性 (0-20分)
    if truth_id:
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT updated_at FROM truths WHERE id=?", (truth_id,))
            row = c.fetchone()
            if row:
                age_days = (time.time() - row[0]) / 86400
                if age_days < 1:
                    score += 20
                elif age_days < 7:
                    score += 15
                elif age_days < 30:
                    score += 10
                else:
                    score += 5
            conn.close()
        except:
            score += 10
    else:
        score += 15  # 新真值

    # 2. 来源权威性 (0-15分)
    if category in ["axiom", "meta_law", "baseline"]:
        score += 15
    elif category in ["decision", "activation", "consolidation"]:
        score += 10
    elif category in ["service_status", "config"]:
        score += 8
    else:
        score += 5

    # 3. 内容完整性 (0-15分)
    if len(value_str) > 200:
        score += 15
    elif len(value_str) > 100:
        score += 10
    elif len(value_str) > 50:
        score += 5

    # 4. 结构化程度 (0-15分)
    if value_str.startswith("{") or value_str.startswith("["):
        score += 15
    elif "：" in value_str and "。" in value_str:
        score += 10
    else:
        score += 5

    # 5. 引用频率 (0-15分) - 简化：key被其他真值引用的次数
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM truths WHERE truth_value LIKE ?", (f"%{key}%",))
        ref_count = c.fetchone()[0]
        score += min(ref_count * 3, 15)
        conn.close()
    except:
        score += 5

    return round(min(score, 100), 1)

# ========== 语义检索聚合 ==========
def semantic_search(query, top_k=5):
    """聚合关键词检索 + 向量语义检索"""
    results = {"keyword": [], "semantic": [], "merged": []}

    # 1. 关键词检索 (从9120基础网关)
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        # 拆分关键词OR匹配
        keywords = query.split()
        if len(keywords) == 1:
            c.execute("SELECT id, truth_key, truth_value, category FROM truths WHERE truth_key LIKE ? OR truth_value LIKE ? ORDER BY updated_at DESC LIMIT 10",
                     (f"%{query}%", f"%{query}%"))
        else:
            where = " OR ".join(["truth_key LIKE ? OR truth_value LIKE ?"] * len(keywords))
            params = []
            for kw in keywords:
                params.extend([f"%{kw}%", f"%{kw}%"])
            c.execute(f"SELECT id, truth_key, truth_value, category FROM truths WHERE {where} ORDER BY updated_at DESC LIMIT 10", params)
        for row in c.fetchall():
            results["keyword"].append({
                "id": row[0], "key": row[1], "value": str(row[2])[:200],
                "category": row[3], "source": "keyword"
            })
        conn.close()
    except Exception as e:
        print(f"关键词检索失败: {e}")

    # 2. 向量语义检索
    try:
        req = urllib.request.Request(
            f"http://127.0.0.1:{VECTOR_PORT}/api/v1/semantic_search",
            data=json.dumps({"query": query, "top_k": top_k}).encode(),
            headers={"Content-Type": "application/json"}
        )
        resp = urllib.request.urlopen(req, timeout=10)
        vec_data = json.loads(resp.read().decode())
        for doc in vec_data.get("results", vec_data.get("documents", [])):
            if isinstance(doc, dict):
                results["semantic"].append({
                    "content": doc.get("content", doc.get("text", ""))[:200],
                    "score": doc.get("score", doc.get("distance", 0)),
                    "source": "semantic"
                })
    except Exception as e:
        print(f"语义检索失败: {e}")

    # 3. 合并去重
    seen_keys = set()
    for item in results["keyword"][:top_k]:
        if item["key"] not in seen_keys:
            seen_keys.add(item["key"])
            results["merged"].append(item)
    for item in results["semantic"][:top_k]:
        results["merged"].append(item)

    return results

# ========== HTTP处理 ==========
class EvolutionHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

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
            self._send_json({
                "status": "ok",
                "service": "memory-gateway-evolution",
                "port": EVOLUTION_PORT,
                "version": "v1.0",
                "cache": cache.stats(),
                "did": "DID-BR-000002",
                "anchor": "Ω₀⊂⊙∞⊂Ω"
            })
            return

        if path == "/api/evolution/stats":
            # 进化引擎统计
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM truths")
            total = c.fetchone()[0]
            c.execute("SELECT category, COUNT(*) FROM truths GROUP BY category ORDER BY COUNT(*) DESC LIMIT 10")
            by_type = {r[0] or "unclassified": r[1] for r in c.fetchall()}
            c.execute("SELECT COUNT(*) FROM audit_logs")
            audit_count = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM truth_history")
            history_count = c.fetchone()[0]
            conn.close()
            self._send_json({
                "total_truths": total,
                "by_type": by_type,
                "audit_logs": audit_count,
                "truth_history": history_count,
                "cache": cache.stats(),
                "subscribers": len(load_subscribers().get("subscribers", []))
            })
            return

        if path == "/api/evolution/search":
            # 聚合检索
            query = self.path.split("q=")[-1] if "q=" in self.path else ""
            if not query:
                self._send_json({"error": "缺少q参数"}, 400)
                return
            results = semantic_search(query)
            self._send_json({
                "query": query,
                "keyword_count": len(results["keyword"]),
                "semantic_count": len(results["semantic"]),
                "results": results["merged"][:10]
            })
            return

        if path == "/api/evolution/history":
            # 真值版本历史
            key = self.path.split("key=")[-1] if "key=" in self.path else ""
            if not key:
                self._send_json({"error": "缺少key参数"}, 400)
                return
            try:
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("SELECT * FROM truth_history WHERE truth_key=? ORDER BY version DESC LIMIT 20", (key,))
                history = []
                for row in c.fetchall():
                    history.append({"version": row[0] if len(row) > 0 else None,
                                   "value": str(row[2])[:200] if len(row) > 2 else "",
                                   "timestamp": row[-1] if row[-1] else None})
                conn.close()
                self._send_json({"key": key, "history": history})
            except Exception as e:
                self._send_json({"error": str(e)}, 500)
            return

        if path == "/api/evolution/audit":
            # 审计日志查询
            try:
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT 50")
                logs = []
                for row in c.fetchall():
                    logs.append({"id": row[0], "action": row[1] if len(row) > 1 else "",
                                "truth_key": row[2] if len(row) > 2 else "",
                                "timestamp": row[-1] if row[-1] else None})
                conn.close()
                self._send_json({"logs": logs, "count": len(logs)})
            except Exception as e:
                self._send_json({"error": str(e)}, 500)
            return

        if path == "/api/evolution/subscribers":
            self._send_json(load_subscribers())
            return

        if path == "/api/evolution/cache":
            self._send_json(cache.stats())
            return

        # 其他路径代理到基础网关9120
        self._proxy_to_base("GET")

    def do_POST(self):
        path = self.path.split("?")[0]
        body = self._read_body()

        if path == "/api/evolution/upsert":
            # 进化版写入: 结构化 + 冲突检测 + 质量评分 + 订阅推送
            key = body.get("key", "")
            value = body.get("value", "")
            category = body.get("category", body.get("truth_type", "other"))
            source = body.get("source", "unknown")
            confidence = body.get("confidence", 0.8)

            if not key:
                self._send_json({"error": "缺少key"}, 400)
                return

            # 1. 冲突检测
            conflicts = detect_conflict(key, value, category)
            has_high_conflict = any(c["severity"] == "high" for c in conflicts)

            # 2. 计算质量评分
            quality_score = score_truth(key, value, category)

            # 3. 构造结构化真值对象
            truth_obj = {
                "key": key,
                "value": value,
                "category": category,
                "source": source,
                "confidence": confidence,
                "quality_score": quality_score,
                "conflicts": conflicts,
                "created_at": time.time(),
                "did": "DID-BR-000002"
            }

            # 4. 写入基础网关 (高冲突需标记但不阻断)
            try:
                payload = {
                    "key": key,
                    "value": json.dumps(truth_obj, ensure_ascii=False) if isinstance(value, (dict, list)) else value,
                    "category": category,
                    "node_id": source,
                    "truth_type": category
                }
                req = urllib.request.Request(
                    f"http://127.0.0.1:{BASE_PORT}/api/truth/upsert",
                    data=json.dumps(payload).encode(),
                    headers={"Content-Type": "application/json"}
                )
                resp = urllib.request.urlopen(req, timeout=10)
                base_result = json.loads(resp.read().decode())
            except Exception as e:
                base_result = {"error": str(e)}

            # 5. 缓存更新
            cache.set(f"truth:{key}", truth_obj)

            # 6. 订阅推送
            notified = notify_subscribers("truth_upsert", truth_obj)

            self._send_json({
                "status": "ok" if "error" not in base_result else "partial",
                "truth": truth_obj,
                "conflict_warning": has_high_conflict,
                "subscribers_notified": notified,
                "base_result": base_result
            })
            return

        if path == "/api/evolution/batch_upsert":
            # 批量写入
            items = body.get("items", [])
            if not items:
                self._send_json({"error": "缺少items"}, 400)
                return
            results = []
            for item in items:
                try:
                    payload = {
                        "key": item.get("key", ""),
                        "value": item.get("value", ""),
                        "category": item.get("category", "other"),
                        "node_id": item.get("source", "batch")
                    }
                    req = urllib.request.Request(
                        f"http://127.0.0.1:{BASE_PORT}/api/truth/upsert",
                        data=json.dumps(payload).encode(),
                        headers={"Content-Type": "application/json"}
                    )
                    resp = urllib.request.urlopen(req, timeout=10)
                    results.append({"key": item["key"], "status": "ok"})
                except Exception as e:
                    results.append({"key": item.get("key", "?"), "status": "error", "error": str(e)})
            self._send_json({"total": len(items), "success": sum(1 for r in results if r["status"] == "ok"), "results": results})
            return

        if path == "/api/evolution/subscribe":
            # 注册订阅者
            name = body.get("name", "")
            webhook_url = body.get("webhook_url", "")
            event_types = body.get("event_types", ["truth_upsert"])
            if not name or not webhook_url:
                self._send_json({"error": "缺少name或webhook_url"}, 400)
                return
            subs = load_subscribers()
            subs["subscribers"].append({
                "name": name,
                "webhook_url": webhook_url,
                "event_types": event_types,
                "active": True,
                "created_at": time.time()
            })
            save_subscribers(subs)
            self._send_json({"status": "ok", "subscriber": name, "total": len(subs["subscribers"])})
            return

        if path == "/api/evolution/score":
            # 真值质量评分查询
            key = body.get("key", "")
            if not key:
                self._send_json({"error": "缺少key"}, 400)
                return
            cached = cache.get(f"truth:{key}")
            if cached:
                self._send_json({"key": key, "quality_score": cached.get("quality_score"), "cached": True})
                return
            try:
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("SELECT id, truth_value, category FROM truths WHERE truth_key=? LIMIT 1", (key,))
                row = c.fetchone()
                conn.close()
                if row:
                    score = score_truth(key, row[1], row[2], row[0])
                    self._send_json({"key": key, "quality_score": score, "cached": False})
                else:
                    self._send_json({"error": "真值不存在"}, 404)
            except Exception as e:
                self._send_json({"error": str(e)}, 500)
            return

        # 其他路径代理到基础网关
        self._proxy_to_base("POST", body)

    def _proxy_to_base(self, method, body=None):
        """代理请求到基础网关9120"""
        try:
            url = f"http://127.0.0.1:{BASE_PORT}{self.path}"
            data = json.dumps(body).encode() if body else None
            req = urllib.request.Request(url, data=data, method=method,
                                        headers={"Content-Type": "application/json"})
            resp = urllib.request.urlopen(req, timeout=30)
            self.send_response(resp.status)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(resp.read())
        except Exception as e:
            self._send_json({"error": f"代理失败: {e}"}, 502)

def main():
    server = HTTPServer(("0.0.0.0", EVOLUTION_PORT), EvolutionHandler)
    print(f"记忆网关进化引擎 v1.0 启动于端口 {EVOLUTION_PORT}")
    print(f"确权: DID-BR-000002 | Ω₀⊂⊙∞⊂Ω")
    print(f"代理基础网关: {BASE_PORT}")
    print(f"进化功能: 结构化真值/冲突检测/语义聚合/订阅推送/批量API/质量评分/版本审计/内存缓存")
    server.serve_forever()

if __name__ == "__main__":
    main()
