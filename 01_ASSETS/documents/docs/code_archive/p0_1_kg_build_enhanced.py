#!/usr/bin/env python3
"""
P0-1增强版：知识图谱全量构建
处理所有类型真值，最多5000条，提升覆盖率
确权: DID-BR-000002 | 溯源: Ω₀⊂⊙∞⊂Ω
"""
import sys
import json
import sqlite3
import requests
import time
from datetime import datetime

DB_PATH = "/opt/ZONGYUAN-ROOT/data/memory_gateway.db"
KG_API = "http://127.0.0.1:8070"
MAX_TRUTHS = 5000
BATCH_SIZE = 50

def get_kg_stat():
    """获取知识图谱状态"""
    try:
        resp = requests.get(f"{KG_API}/api/v1/kg/stat", timeout=10)
        return resp.json()
    except Exception as e:
        return {"error": str(e)}

def get_all_truths(limit=5000):
    """从数据库获取所有真值"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT truth_key, truth_value, category, created_at 
            FROM truths 
            ORDER BY created_at DESC 
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        conn.close()
        
        truths = []
        for row in rows:
            truths.append({
                "key": row[0],
                "value": row[1],
                "type": row[2] or "unknown",
                "created_at": row[3]
            })
        return truths
    except Exception as e:
        print(f"  数据库查询错误: {e}")
        return []

def extract_to_kg(truth):
    """将单条真值抽取到知识图谱"""
    try:
        # 构建文本
        text = f"{truth['key']}: {truth['value']}"
        if len(text) > 2000:
            text = text[:2000]
        
        resp = requests.post(
            f"{KG_API}/api/v1/kg/extract",
            json={"text": text, "source": truth["key"], "type": truth["type"]},
            timeout=30
        )
        return resp.json()
    except Exception as e:
        return {"error": str(e)}

def main():
    print("=" * 60)
    print("  P0-1增强版：知识图谱全量构建")
    print("=" * 60)
    print()
    
    # 构建前状态
    print("【1】构建前状态")
    before = get_kg_stat()
    print(f"  节点数: {before.get('nodes', 0)}")
    print(f"  边数: {before.get('edges', 0)}")
    print(f"  因果规则: {before.get('causal_rules', 0)}")
    print()
    
    # 获取所有真值
    print("【2】获取所有真值")
    truths = get_all_truths(MAX_TRUTHS)
    print(f"  获取到 {len(truths)} 条真值")
    print()
    
    # 按类型统计
    type_count = {}
    for t in truths:
        ttype = t.get("type", "unknown")
        type_count[ttype] = type_count.get(ttype, 0) + 1
    print("  按类型统计:")
    for ttype, count in sorted(type_count.items(), key=lambda x: -x[1])[:10]:
        print(f"    {ttype}: {count}条")
    print()
    
    # 批量抽取到知识图谱
    print("【3】批量抽取到知识图谱")
    print(f"  每批 {BATCH_SIZE} 条，共 {len(truths)} 条")
    print()
    
    success = 0
    failed = 0
    start_time = time.time()
    
    for i in range(0, len(truths), BATCH_SIZE):
        batch = truths[i:i+BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        total_batches = (len(truths) + BATCH_SIZE - 1) // BATCH_SIZE
        
        print(f"  批次 {batch_num}/{total_batches}: 处理 {len(batch)} 条...", end=" ", flush=True)
        
        batch_success = 0
        for truth in batch:
            try:
                result = extract_to_kg(truth)
                if "error" not in result:
                    batch_success += 1
                else:
                    failed += 1
            except Exception:
                failed += 1
        
        success += batch_success
        elapsed = time.time() - start_time
        print(f"成功{batch_success}条, 累计成功{success}条, 耗时{elapsed:.1f}s")
        
        # 每10批打印一次当前状态
        if batch_num % 10 == 0:
            current = get_kg_stat()
            print(f"    当前状态: {current.get('nodes', 0)}节点 / {current.get('edges', 0)}边")
    
    print()
    
    # 构建后状态
    print("【4】构建后状态")
    after = get_kg_stat()
    print(f"  节点数: {after.get('nodes', 0)}")
    print(f"  边数: {after.get('edges', 0)}")
    print(f"  因果规则: {after.get('causal_rules', 0)}")
    print()
    
    # 增长统计
    before_nodes = before.get("nodes", 0)
    after_nodes = after.get("nodes", 0)
    before_edges = before.get("edges", 0)
    after_edges = after.get("edges", 0)
    
    print("【5】增长统计")
    print(f"  节点增长: +{after_nodes - before_nodes} ({before_nodes} -> {after_nodes})")
    print(f"  边数增长: +{after_edges - before_edges} ({before_edges} -> {after_edges})")
    print(f"  处理真值: {len(truths)}条")
    print(f"  成功抽取: {success}条")
    print(f"  失败: {failed}条")
    print(f"  总耗时: {time.time() - start_time:.1f}s")
    print()
    
    # 覆盖率
    truth_count = len(truths)
    coverage = min(after_nodes / truth_count * 100, 100) if truth_count > 0 else 0
    print(f"  覆盖率估算: {coverage:.1f}% (基于{truth_count}条真值)")
    print()
    
    # Top实体
    print("【6】Top10实体")
    top = after.get("top_entities", [])[:10]
    for i, item in enumerate(top, 1):
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            name = item[0]
            info = item[1] if isinstance(item[1], dict) else {}
            cnt = info.get("count", 0)
            print(f"  {i}. {name}: {cnt}次")
    print()
    
    print("=" * 60)
    print("  P0-1增强版 完成")
    print("=" * 60)

if __name__ == "__main__":
    main()
