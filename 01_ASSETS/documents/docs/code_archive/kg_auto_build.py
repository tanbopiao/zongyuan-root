#!/usr/bin/env python3
"""
自动知识图谱构建器
从9120真值库批量抽取实体和关系，构建全域知识图谱
确权: DID-BR-000002 | 溯源: Ω₀⊂⊙∞⊂Ω
"""
import json
import os
import sqlite3
import time
import urllib.request
from datetime import datetime

BASE = "/opt/ZONGYUAN-ROOT"
LOG_FILE = os.path.join(BASE, "logs/kg_auto_build.log")
STATE_FILE = os.path.join(BASE, "data/kg_build_state.json")
KG_API = "http://127.0.0.1:8070/api/v1"
DB_PATH = os.path.join(BASE, "data/memory_gateway.db")

# 优先抽取的高价值分类
PRIORITY_CATEGORIES = ["meta_rule", "decision", "axiom", "theorem", "method", "protocol", "risk"]
BATCH_SIZE = 20  # 每批处理数量
SLEEP_BETWEEN = 0.3  # 批次间隔（秒）

def log(msg):
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, 'a') as f:
        f.write("[%s] %s\n" % (ts, msg))
    print("[%s] %s" % (ts, msg))

def api_post(url, data):
    try:
        req = urllib.request.Request(
            url, data=json.dumps(data).encode(),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"error": str(e)}

def api_get(url):
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"error": str(e)}

def get_truths(categories=None, limit=500):
    """从9120数据库获取真值"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if categories:
        placeholders = ",".join("?" * len(categories))
        c.execute("SELECT truth_key, truth_value, category FROM truths WHERE category IN (%s) ORDER BY rowid DESC LIMIT ?" % placeholders, (*categories, limit))
    else:
        c.execute("SELECT truth_key, truth_value, category FROM truths ORDER BY rowid DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    return rows

def build_text(key, value, category):
    """构造抽取文本"""
    text = "%s。%s" % (key, (value or "")[:500])
    return text

def run_build(limit=300):
    """执行知识图谱构建"""
    log("=" * 50)
    log("知识图谱自动构建开始")
    
    # 构建前统计
    before = api_get(KG_API + "/kg/stat")
    before_nodes = before.get("nodes", 0)
    before_edges = before.get("edges", 0)
    log("构建前: %d节点/%d边" % (before_nodes, before_edges))
    
    # 获取高价值真值
    truths = get_truths(categories=PRIORITY_CATEGORIES, limit=limit)
    log("待处理真值: %d条" % len(truths))
    
    total_entities = 0
    total_edges = 0
    processed = 0
    errors = 0
    
    for i in range(0, len(truths), BATCH_SIZE):
        batch = truths[i:i+BATCH_SIZE]
        for key, value, category in batch:
            text = build_text(key, value, category)
            result = api_post(KG_API + "/kg/extract", {"text": text})
            if "error" not in result:
                total_entities += len(result.get("entities", []))
                total_edges += len(result.get("edges", []))
                processed += 1
            else:
                errors += 1
            if processed % 50 == 0:
                log("  进度: %d/%d, 实体+%d, 关系+%d" % (processed, len(truths), total_entities, total_edges))
        time.sleep(SLEEP_BETWEEN)
    
    # 构建后统计
    after = api_get(KG_API + "/kg/stat")
    after_nodes = after.get("nodes", 0)
    after_edges = after.get("edges", 0)
    
    log("构建后: %d节点/%d边" % (after_nodes, after_edges))
    log("增长: +%d节点, +%d边" % (after_nodes - before_nodes, after_edges - before_edges))
    log("处理: %d条成功, %d条失败" % (processed, errors))
    log("抽取: %d实体提及, %d关系提及" % (total_entities, total_edges))
    
    # Top实体
    top = after.get("top_entities", [])[:5]
    log("Top实体: %s" % ", ".join("%s(%d)" % (e[0], e[1].get("count", 0)) for e in top))
    
    # 保存状态
    state = {
        "last_build": datetime.now().isoformat(),
        "truths_processed": processed,
        "nodes": after_nodes,
        "edges": after_edges,
        "causal_rules": after.get("causal_rules", 0)
    }
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    
    log("知识图谱构建完成")
    log("=" * 50)
    return state

if __name__ == '__main__':
    import sys
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    run_build(limit)
