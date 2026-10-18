#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
轻量知识图谱构建器V2：优化关系抽取规则
"""
import sqlite3, json, re

TRUTH_DB = "/www/wwwroot/huodouai.com/zhongshu/data/truth/truth.db"
KG_DB = "/opt/ZONGYUAN-ROOT/data/knowledge_graph.db"

def init_kg():
    conn = sqlite3.connect(KG_DB)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS entities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        type TEXT,
        mention_count INTEGER DEFAULT 1
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS relations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_id INTEGER,
        target_id INTEGER,
        relation TEXT,
        count INTEGER DEFAULT 1,
        UNIQUE(source_id, target_id, relation)
    )""")
    conn.commit()
    conn.close()

def get_prefix(name):
    """取实体前缀分类"""
    parts = name.split(".")
    return parts[0] if parts else "OTHER"

def build():
    init_kg()
    conn_truth = sqlite3.connect(TRUTH_DB)
    c_truth = conn_truth.cursor()
    c_truth.execute("SELECT key, value FROM truth ORDER BY seq DESC LIMIT 3000")
    rows = c_truth.fetchall()
    
    conn_kg = sqlite3.connect(KG_DB)
    c_kg = conn_kg.cursor()
    
    # 清空重建
    c_kg.execute("DELETE FROM entities")
    c_kg.execute("DELETE FROM relations")
    
    entity_map = {}
    all_keys = [r[0] for r in rows]
    
    # 1. 所有key作为实体入库
    for key in all_keys:
        c_kg.execute("INSERT OR IGNORE INTO entities (name, type) VALUES (?, ?)", (key, get_prefix(key)))
        c_kg.execute("SELECT id FROM entities WHERE name=?", (key,))
        entity_map[key] = c_kg.fetchone()[0]
    
    # 2. 同前缀自动建边：同大类的实体之间自动关联
    prefix_groups = {}
    for key in all_keys:
        prefix = key.split(".")[0]
        prefix_groups.setdefault(prefix, []).append(key)
    
    edge_count = 0
    for prefix, keys in prefix_groups.items():
        # 同大类内的实体两两连边（只连前10个，避免爆炸）
        for i, k1 in enumerate(keys[:10]):
            for k2 in keys[:10]:
                if k1 >= k2: continue
                sid, tid = entity_map[k1], entity_map[k2]
                c_kg.execute("""INSERT INTO relations (source_id, target_id, relation) VALUES (?, ?, ?)
                                ON CONFLICT(source_id, target_id, relation) DO UPDATE SET count = count + 1""",
                                (sid, tid, "同属"+prefix))
                edge_count += 1
    
    conn_kg.commit()
    
    # 统计
    c_kg.execute("SELECT COUNT(*) FROM entities")
    ent_count = c_kg.fetchone()[0]
    c_kg.execute("SELECT COUNT(*) FROM relations")
    rel_count = c_kg.fetchone()[0]
    
    conn_kg.close()
    conn_truth.close()
    
    print(f"✅ 知识图谱V2构建完成")
    print(f"  实体数: {ent_count}")
    print(f"  关系边数: {rel_count}")

if __name__ == "__main__":
    build()
