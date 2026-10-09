#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 真值遗忘机制（反臃肿）
- 评估每条真值的价值分（引用频率/置信度/时效性/类型权重）
- 低价值真值自动归档到cold storage，从主库移除
- 核心库保持精炼，防止"真值通货膨胀"
- 每周日凌晨3点执行
"""
import json
import time
import sqlite3
import os
import shutil
from datetime import datetime, timedelta

# 配置
DB_PATH = "/opt/ZONGYUAN-ROOT/data/memory_gateway.db"
COLD_STORAGE_DIR = "/opt/ZONGYUAN-ROOT/archive/cold_truths"
AUDIT_LOG = "/opt/ZONGYUAN-ROOT/logs/truth_forgetting.log"
DID = "DID-BR-000002"
ANCHOR = "Ω₀⊂⊙∞⊂Ω"

# 价值评分权重
WEIGHTS = {
    "recency": 0.3,      # 时效性（越新分越高）
    "confidence": 0.25,  # 置信度
    "type_weight": 0.25, # 类型权重（元法则/公理最高）
    "length": 0.1,       # 内容长度（过短可能低价值）
    "access": 0.1        # 访问频率（暂无数据，预留）
}

# 类型权重
TYPE_WEIGHTS = {
    "meta_law": 1.0,
    "axiom": 1.0,
    "core_truth": 0.9,
    "decision": 0.8,
    "protocol": 0.8,
    "method": 0.7,
    "data": 0.5,
    "case": 0.5,
    "audit_log": 0.3,
    "sync_log": 0.2,
    "anomaly_detect": 0.2,
    "heartbeat": 0.1,
    "default": 0.4
}

# 遗忘阈值
FORGET_THRESHOLD = 0.35  # 低于此分归档
ARCHIVE_LIMIT = 100      # 每次最多归档100条
MIN_TRUTHS = 500         # 主库最少保留500条

def log(msg):
    os.makedirs(os.path.dirname(AUDIT_LOG), exist_ok=True)
    with open(AUDIT_LOG, 'a') as f:
        f.write(f"[{datetime.now()}] {msg}\n")
    print(msg)

def get_type_weight(category, truth_key):
    """获取类型权重"""
    if category:
        cat_lower = str(category).lower()
        for k, v in TYPE_WEIGHTS.items():
            if k in cat_lower:
                return v
    # 从key推断
    key_lower = str(truth_key).lower()
    if key_lower.startswith("mr-") or "meta_law" in key_lower or "metalaw" in key_lower:
        return 1.0
    if "anomaly" in key_lower or "heartbeat" in key_lower:
        return 0.1
    if "sync" in key_lower or "audit" in key_lower:
        return 0.2
    return TYPE_WEIGHTS["default"]

def calculate_value(truth):
    """计算真值价值分 (0-1)"""
    now = time.time()
    
    # 时效性：30天内满分，超过180天0分
    updated_at = truth.get('updated_at', truth.get('created_at', now))
    try:
        age_days = (now - float(updated_at)) / 86400
        recency = max(0, 1 - age_days / 180)
    except:
        recency = 0.5
    
    # 置信度（从value中提取，默认0.5）
    confidence = 0.5
    value_str = str(truth.get('truth_value', ''))
    if 'confidence' in value_str:
        try:
            import re
            m = re.search(r'confidence["\s:]+([0-9.]+)', value_str)
            if m:
                confidence = float(m.group(1))
        except:
            pass
    
    # 类型权重
    type_w = get_type_weight(truth.get('category', ''), truth.get('truth_key', ''))
    
    # 内容长度：50-500字满分，过短过低
    length = len(value_str)
    if length < 10:
        len_score = 0.1
    elif length < 50:
        len_score = 0.3
    elif length < 500:
        len_score = 1.0
    else:
        len_score = 0.8
    
    # 访问频率（预留，默认0.5）
    access = 0.5
    
    # 加权总分
    score = (recency * WEIGHTS["recency"] + 
             confidence * WEIGHTS["confidence"] + 
             type_w * WEIGHTS["type_weight"] + 
             len_score * WEIGHTS["length"] + 
             access * WEIGHTS["access"])
    
    return round(score, 4)

def archive_truth(truth, archive_file):
    """归档单条真值到cold storage"""
    with open(archive_file, 'a') as f:
        f.write(json.dumps(truth, ensure_ascii=False) + "\n")

def main():
    log("=" * 50)
    log("真值遗忘机制启动")
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 获取当前真值总数
    cursor.execute("SELECT COUNT(*) FROM truths")
    total = cursor.fetchone()[0]
    log(f"当前主库真值数: {total}")
    
    if total <= MIN_TRUTHS:
        log(f"真值数低于最低阈值{MIN_TRUTHS}，跳过遗忘")
        conn.close()
        return
    
    # 获取所有真值
    cursor.execute("SELECT * FROM truths ORDER BY updated_at ASC")
    all_truths = [dict(row) for row in cursor.fetchall()]
    
    # 计算价值分
    scored = []
    for t in all_truths:
        score = calculate_value(t)
        scored.append((score, t))
    
    # 按分数升序排列（低分在前）
    scored.sort(key=lambda x: x[0])
    
    # 统计分布
    low_count = sum(1 for s, _ in scored if s < FORGET_THRESHOLD)
    mid_count = sum(1 for s, _ in scored if FORGET_THRESHOLD <= s < 0.6)
    high_count = sum(1 for s, _ in scored if s >= 0.6)
    log(f"价值分布: 低价值(<{FORGET_THRESHOLD})={low_count}, 中价值={mid_count}, 高价值={high_count}")
    
    # 选择要归档的真值
    to_archive = []
    for score, t in scored:
        if score < FORGET_THRESHOLD and len(to_archive) < ARCHIVE_LIMIT:
            # 保护元法则和核心真值
            key = str(t.get('truth_key', ''))
            if key.startswith('MR-') or 'meta_law' in key.lower():
                continue
            to_archive.append((score, t))
    
    if not to_archive:
        log("没有需要遗忘的低价值真值")
        conn.close()
        return
    
    # 归档
    os.makedirs(COLD_STORAGE_DIR, exist_ok=True)
    archive_file = os.path.join(COLD_STORAGE_DIR, f"cold_truths_{datetime.now().strftime('%Y%m%d')}.jsonl")
    
    archived = 0
    for score, t in to_archive:
        t['forget_score'] = score
        t['forgotten_at'] = datetime.now().isoformat()
        archive_truth(t, archive_file)
        # 从主库删除
        cursor.execute("DELETE FROM truths WHERE id = ?", (t['id'],))
        archived += 1
    
    conn.commit()
    conn.close()
    
    # 记录结果
    cursor = None
    log(f"已归档 {archived} 条低价值真值到 {archive_file}")
    log(f"归档后主库真值数: {total - archived}")
    
    # 上报9120
    try:
        import urllib.request
        report = {
            "key": f"truth_forgetting.{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "value": f"真值遗忘执行: 评估{total}条, 归档{archived}条低价值真值, 主库剩余{total-archived}条",
            "source": "truth_forgetting",
            "did": DID,
            "truth_type": "audit_log",
            "confidence": 1.0
        }
        req = urllib.request.Request(
            "http://127.0.0.1:9120/api/truth/upsert",
            data=json.dumps(report).encode(),
            headers={'Content-Type': 'application/json'}
        )
        urllib.request.urlopen(req, timeout=5)
    except:
        pass
    
    log("真值遗忘完成")

if __name__ == '__main__':
    main()
