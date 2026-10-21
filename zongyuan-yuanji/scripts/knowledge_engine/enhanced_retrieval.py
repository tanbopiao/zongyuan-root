"""
四维增强检索评分模块
用途：升级知识检索评分模型，从 0.6*余弦+0.4*文本 升级到四维评分
"""

import math
from datetime import datetime


def cosine_similarity(vec_a: list, vec_b: list) -> float:
    """计算余弦相似度"""
    if len(vec_a) != len(vec_b):
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    mag_a = math.sqrt(sum(a * a for a in vec_a))
    mag_b = math.sqrt(sum(b * b for b in vec_b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def compute_struct_match(query_text: str, doc_text: str, doc_metadata: dict) -> float:
    """计算结构匹配度"""
    score = 0.0
    
    # 1. 标题命中（权重 0.4）
    title = doc_metadata.get("title", "").lower()
    if title and title in query_text.lower():
        score += 0.4
    
    # 2. 关键词命中（权重 0.3）
    query_tokens = set(query_text.lower().split())
    doc_tokens = set(doc_text.lower().split())
    if query_tokens and doc_tokens:
        overlap = query_tokens & doc_tokens
        score += 0.3 * len(overlap) / max(len(query_tokens), 1)
    
    # 3. 层级匹配（权重 0.3）
    doc_level = doc_metadata.get("level", "L0")
    query_level_hint = "L0" if any(x in query_text for x in ["公理", "根本", "核心"]) else \
                       "L1" if any(x in query_text for x in ["能力", "基础"]) else \
                       "L2" if any(x in query_text for x in ["自治", "长期"]) else \
                       "L3" if any(x in query_text for x in ["闭环", "引擎", "协议"]) else "L4"
    if doc_level == query_level_hint:
        score += 0.3
    
    return min(score, 1.0)


def compute_time_decay(doc_metadata: dict) -> float:
    """计算时效衰减"""
    created_at = doc_metadata.get("created_at", doc_metadata.get("timestamp"))
    if not created_at:
        return 1.0
    
    try:
        if isinstance(created_at, str):
            created_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        else:
            created_dt = created_at
    except:
        return 1.0
    
    now = datetime.now()
    age_days = (now - created_dt).days
    
    # L0 公理永不衰减
    level = doc_metadata.get("level", "L0")
    if level == "L0":
        return 1.0
    
    # 半衰期 ~693 天
    return math.exp(-0.001 * age_days)


def compute_authority(doc_metadata: dict) -> float:
    """计算权威度"""
    source_type = doc_metadata.get("source_type", "anon")
    authority = {
        "homologous": 1.0,   # 同源节点
        "external": 0.7,     # 外源节点
        "anon": 0.4          # 匿名
    }
    return authority.get(source_type, 0.4)


def enhanced_score(query_embedding: list, doc_embedding: list, 
                   query_text: str, doc_text: str, 
                   doc_metadata: dict) -> float:
    """
    四维增强检索评分
    评分公式: 0.4 * 语义相似度 + 0.2 * 结构匹配 + 0.2 * 时效衰减 + 0.2 * 权威度
    """
    cos_sim = cosine_similarity(query_embedding, doc_embedding)
    struct_score = compute_struct_match(query_text, doc_text, doc_metadata)
    decay = compute_time_decay(doc_metadata)
    auth_score = compute_authority(doc_metadata)
    
    final = 0.4 * cos_sim + 0.2 * struct_score + 0.2 * decay + 0.2 * auth_score
    return round(final, 4)


def rank_documents(query_text: str, query_embedding: list, 
                   documents: list) -> list:
    """
    对文档列表进行排序
    documents: [{"text": "...", "metadata": {...}, "embedding": [...]}]
    """
    scored = []
    for doc in documents:
        score = enhanced_score(
            query_embedding,
            doc.get("embedding", []),
            query_text,
            doc.get("text", ""),
            doc.get("metadata", {})
        )
        scored.append((score, doc))
    
    scored.sort(key=lambda x: -x[0])
    return scored


def main():
    print("=" * 60)
    print("🔍 四维增强检索评分模块")
    print("=" * 60)
    
    # 测试用例
    query_text = "Ω⁴ 集群同步协议"
    query_embedding = [0.1] * 2048  # 模拟 embedding
    
    documents = [
        {
            "text": "Ω⁴集群同步：跨节点通信必经本地 L5 校验，Merkle-DAG 主链全量交互写存证",
            "metadata": {"title": "Ω⁴集群法典", "level": "L4", "source_type": "homologous", "created_at": "2026-10-15T12:00:00"},
            "embedding": [0.08] * 2048
        },
        {
            "text": "种子采集必须固定 seed=42, temperature=0.0",
            "metadata": {"title": "运维铁律", "level": "L0", "source_type": "homologous", "created_at": "2026-10-13T10:00:00"},
            "embedding": [0.05] * 2048
        },
        {
            "text": "A2A 工作流：注册→心跳→上报真值",
            "metadata": {"title": "A2A接入指南", "level": "L3", "source_type": "external", "created_at": "2026-10-14T15:00:00"},
            "embedding": [0.07] * 2048
        }
    ]
    
    print(f"\n查询: {query_text}")
    print("\n=== 排序结果 ===")
    results = rank_documents(query_text, query_embedding, documents)
    for i, (score, doc) in enumerate(results, 1):
        print(f"  #{i} 得分={score:.4f} | {doc['metadata']['title']} ({doc['metadata']['level']})")
        print(f"      {doc['text'][:60]}...")
    
    print("\n✅ 增强检索模块就绪")
    print("   评分维度: 语义(0.4) + 结构(0.2) + 时效(0.2) + 权威度(0.2)")
    
    return results


if __name__ == "__main__":
    main()