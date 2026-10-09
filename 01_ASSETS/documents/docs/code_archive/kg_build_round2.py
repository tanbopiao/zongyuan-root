#!/usr/bin/env python3
"""知识图谱批量构建 - 第二轮（处理剩余真值，目标覆盖率20%+）"""
import sqlite3
import requests
import time
import json

DB_PATH = "/opt/ZONGYUAN-ROOT/data/memory_gateway.db"
KG_API = "http://127.0.0.1:8070/api/v1/kg/extract"

def get_remaining_truths(limit=3000):
    """获取剩余未处理的真值（跳过已处理的高价值类型）"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # 获取所有真值，按ID排序，跳过前4000条（已处理）
    cursor.execute("""
        SELECT id, truth_key, truth_value, category 
        FROM truths 
        ORDER BY id 
        LIMIT ? OFFSET 4000
    """, (limit,))
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
        
        if (i + 1) % 200 == 0:
            elapsed = time.time() - start_time
            rate = (i + 1) / elapsed if elapsed > 0 else 0
            print(f"  进度: {i+1}/{len(truths)} ({(i+1)/len(truths)*100:.1f}%), 成功: {success}, 失败: {failed}, 速度: {rate:.1f}条/秒")
        time.sleep(0.02)  # 稍微加快速度
    
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
    print("  知识图谱批量构建 - 第二轮")
    print("  目标: 覆盖率20%+")
    print("=" * 60)
    
    # 初始状态
    stats = get_kg_stats()
    initial_nodes = stats.get("nodes", 0)
    initial_edges = stats.get("edges", 0)
    print(f"\n初始状态: 节点 {initial_nodes}, 边 {initial_edges}")
    
    # 获取真值总数
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM truths")
    total_truths = cursor.fetchone()[0]
    conn.close()
    print(f"真值库总量: {total_truths}")
    print(f"已处理: 4000条 (第一轮)")
    print(f"待处理: {total_truths - 4000}条")
    
    total_success = 0
    total_failed = 0
    total_entities = 0
    total_edges = 0
    
    # 分批处理剩余真值
    batch_size = 2000
    for batch_num in range(3):  # 处理3批，共6000条
        offset = 4000 + batch_num * batch_size
        if offset >= total_truths:
            break
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, truth_key, truth_value, category 
            FROM truths 
            ORDER BY id 
            LIMIT ? OFFSET ?
        """, (batch_size, offset))
        truths = cursor.fetchall()
        conn.close()
        
        if not truths:
            break
        
        s, f, e, ed = build_kg_batch(truths, f"第{batch_num+1}批 (offset={offset})")
        total_success += s
        total_failed += f
        total_entities += e
        total_edges += ed
        
        # 每批后检查状态
        stats = get_kg_stats()
        current_nodes = stats.get("nodes", 0)
        current_edges = stats.get("edges", 0)
        coverage = (current_nodes / total_truths) * 100 if total_truths > 0 else 0
        print(f"\n  当前知识图谱: 节点 {current_nodes}, 边 {current_edges}, 覆盖率 {coverage:.1f}%")
        
        # 如果覆盖率已经达到20%，提前结束
        if coverage >= 20:
            print(f"\n  目标达成！覆盖率已达到 {coverage:.1f}%")
            break
    
    # 最终状态
    stats = get_kg_stats()
    final_nodes = stats.get("nodes", 0)
    final_edges = stats.get("edges", 0)
    final_coverage = (final_nodes / total_truths) * 100 if total_truths > 0 else 0
    
    print(f"\n{'='*60}")
    print(f"  批量构建完成")
    print(f"{'='*60}")
    print(f"  总处理: {total_success + total_failed} 条")
    print(f"  成功: {total_success}")
    print(f"  失败: {total_failed}")
    print(f"  累计抽取实体: {total_entities}")
    print(f"  累计抽取关系: {total_edges}")
    print(f"  知识图谱节点: {initial_nodes} -> {final_nodes} (+{final_nodes-initial_nodes})")
    print(f"  知识图谱边: {initial_edges} -> {final_edges} (+{final_edges-initial_edges})")
    print(f"  覆盖率: {final_coverage:.1f}%")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
