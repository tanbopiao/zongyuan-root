#!/usr/bin/env python3
"""批量从真值库构建知识图谱 - 增强版"""
import sqlite3
import requests
import time
import json
import sys

DB_PATH = "/opt/ZONGYUAN-ROOT/data/memory_gateway.db"
KG_API = "http://127.0.0.1:8070/api/v1/kg/extract"

def get_truths_by_category(categories, limit=1000, offset=0):
    """按分类获取真值列表"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    placeholders = ",".join(["?"] * len(categories))
    cursor.execute(f"""
        SELECT id, truth_key, truth_value, category 
        FROM truths 
        WHERE category IN ({placeholders})
        ORDER BY id 
        LIMIT ? OFFSET ?
    """, (*categories, limit, offset))
    truths = cursor.fetchall()
    conn.close()
    return truths

def get_all_truths(limit=2000, offset=0):
    """获取所有真值"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, truth_key, truth_value, category 
        FROM truths 
        ORDER BY id 
        LIMIT ? OFFSET ?
    """, (limit, offset))
    truths = cursor.fetchall()
    conn.close()
    return truths

def build_kg_batch(truths, batch_name=""):
    """批量构建知识图谱"""
    print(f"\n{'='*60}")
    print(f"  批量构建: {batch_name}")
    print(f"  处理数量: {len(truths)}")
    print(f"{'='*60}")
    
    success = 0
    failed = 0
    total_entities = 0
    total_edges = 0
    start_time = time.time()
    
    for i, (tid, key, value, category) in enumerate(truths):
        try:
            text = f"{key}: {value}"
            # 跳过空文本
            if not text or len(text.strip()) < 5:
                continue
            resp = requests.post(
                KG_API,
                json={"text": text},
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                success += 1
                total_entities += len(data.get("entities", []))
                total_edges += len(data.get("edges", []))
            else:
                failed += 1
        except Exception as e:
            failed += 1
        
        if (i + 1) % 100 == 0:
            elapsed = time.time() - start_time
            rate = (i + 1) / elapsed if elapsed > 0 else 0
            print(f"  进度: {i+1}/{len(truths)} ({(i+1)/len(truths)*100:.1f}%), 成功: {success}, 失败: {failed}, 速度: {rate:.1f}条/秒")
        time.sleep(0.03)  # 避免请求过快
    
    elapsed = time.time() - start_time
    print(f"\n  完成: 成功 {success}, 失败 {failed}")
    print(f"  累计抽取实体: {total_entities}, 累计关系: {total_edges}")
    print(f"  耗时: {elapsed:.1f}秒, 平均速度: {len(truths)/elapsed:.1f}条/秒")
    
    return success, failed, total_entities, total_edges

def get_kg_stats():
    """获取知识图谱统计"""
    try:
        resp = requests.get("http://127.0.0.1:8070/api/v1/kg/stat", timeout=5)
        return resp.json()
    except:
        return {"nodes": 0, "edges": 0}

def main():
    print("=" * 60)
    print("  知识图谱批量构建 - 增强版")
    print("=" * 60)
    
    # 初始状态
    stats = get_kg_stats()
    print(f"\n初始状态: 节点 {stats.get('nodes',0)}, 边 {stats.get('edges',0)}")
    
    total_success = 0
    total_failed = 0
    total_entities = 0
    total_edges = 0
    
    # 第一批：高价值真值（axiom, theorem, method, meta_rule, protocol, decision, risk）
    high_value_cats = ["axiom", "theorem", "method", "meta_rule", "protocol", "decision", "risk", "creative", "case"]
    truths1 = get_truths_by_category(high_value_cats, limit=1500)
    if truths1:
        s, f, e, ed = build_kg_batch(truths1, "第一批-高价值真值")
        total_success += s
        total_failed += f
        total_entities += e
        total_edges += ed
    
    # 第二批：数据类真值（data, observation, stability_measure）
    data_cats = ["data", "observation", "stability_measure", "compute_injection", "classification", "guardian_report"]
    truths2 = get_truths_by_category(data_cats, limit=1500)
    if truths2:
        s, f, e, ed = build_kg_batch(truths2, "第二批-数据类真值")
        total_success += s
        total_failed += f
        total_entities += e
        total_edges += ed
    
    # 第三批：未分类和其他真值
    other_cats = ["unclassified", "", "lock"]
    truths3 = get_truths_by_category(other_cats, limit=1000)
    if truths3:
        s, f, e, ed = build_kg_batch(truths3, "第三批-未分类真值")
        total_success += s
        total_failed += f
        total_entities += e
        total_edges += ed
    
    # 最终状态
    stats = get_kg_stats()
    print(f"\n{'='*60}")
    print(f"  批量构建完成")
    print(f"{'='*60}")
    print(f"  总处理: {total_success + total_failed} 条")
    print(f"  成功: {total_success}")
    print(f"  失败: {total_failed}")
    print(f"  累计抽取实体: {total_entities}")
    print(f"  累计抽取关系: {total_edges}")
    print(f"  最终知识图谱: 节点 {stats.get('nodes',0)}, 边 {stats.get('edges',0)}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
