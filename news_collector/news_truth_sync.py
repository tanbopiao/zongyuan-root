#!/usr/bin/env python3
"""
资讯真值 → Ω-Brainμ 向量库同步脚本
从news.db提取的真值自动写入Ω-Brainμ truth_index.json，实现自进化闭环
"""
import json, sqlite3, hashlib, time, os, sys
from datetime import datetime

NEWS_DB = "/opt/ZONGYUAN-ROOT/news_collector/news.db"
TRUTH_INDEX = "/opt/ZONGYUAN-ROOT/Ω-Brainμ/truth_index.json"

def load_truth_index():
    if os.path.exists(TRUTH_INDEX):
        with open(TRUTH_INDEX) as f:
            return json.load(f)
    return {"version": "μ-1.0", "truth_count": 0, "truths": [], "merkle_root": "", "updated_at": ""}

def save_truth_index(data):
    data["truth_count"] = len(data["truths"])
    # 重新计算merkle_root
    all_hashes = "".join(t.get("sha256", "") for t in data["truths"])
    data["merkle_root"] = hashlib.sha256(all_hashes.encode()).hexdigest()
    data["updated_at"] = datetime.now().isoformat()
    with open(TRUTH_INDEX, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return data

def sync_news_truths():
    # 读取资讯真值
    conn = sqlite3.connect(NEWS_DB)
    c = conn.cursor()
    c.execute("SELECT truth_id, category, content, source_news, confidence FROM extracted_truths")
    news_truths = c.fetchall()
    conn.close()
    
    # 加载现有真值索引
    index = load_truth_index()
    existing_ids = {t["id"] for t in index["truths"]}
    
    added = 0
    for truth_id, category, content, source, confidence in news_truths:
        if truth_id not in existing_ids:
            sha = hashlib.sha256(f"{truth_id}{content}".encode()).hexdigest()
            index["truths"].append({
                "id": truth_id,
                "type": "news_evolution",
                "category": category,
                "content": content,
                "source": source,
                "confidence": confidence,
                "sha256": sha,
                "origin": "news_collector"
            })
            added += 1
    
    if added > 0:
        index = save_truth_index(index)
        print(f"[同步完成] 新增{added}条资讯真值 → Ω-Brainμ")
        print(f"  Ω-Brainμ真值总数: {index['truth_count']}")
        print(f"  Merkle根: {index['merkle_root'][:16]}...")
    else:
        print(f"[无新增] 资讯真值已全部在Ω-Brainμ中（共{len(news_truths)}条）")
    
    return added

if __name__ == "__main__":
    added = sync_news_truths()
    # 重启omega服务加载新真值
    if added > 0:
        os.system("systemctl restart zongyuan-omega > /dev/null 2>&1")
        time.sleep(2)
        print("  omega服务已重启，新真值已加载")
    sys.exit(0)
