import sys
sys.path.insert(0, "/opt/ZONGYUAN-ROOT/engine/semantic_search")
from vector_engine import VectorSearchEngine, build_index_from_db, get_engine
import os

# 构建索引
print("构建索引...")
engine = VectorSearchEngine()
count = build_index_from_db(engine)
print("索引构建完成: {}个文档".format(count))
print("词汇表大小: {}".format(len(engine.vocabulary)))
idx_size = os.path.getsize("/opt/ZONGYUAN-ROOT/engine/semantic_search/index.pkl") / 1024 / 1024
print("索引文件大小: {:.1f} MB".format(idx_size))

print()
print("=== 测试1: SSH自愈相关 ===")
results = engine.search("SSH自愈 瘫痪修复", top_k=5)
for r in results:
    print("  [{:.3f}] {}".format(r["similarity"], r["key"][:60]))

print()
print("=== 测试2: 元法则 中枢智能 ===")
results = engine.search("元法则 中枢智能 最高优先级", top_k=5)
for r in results:
    print("  [{:.3f}] {}".format(r["similarity"], r["key"][:60]))

print()
print("=== 测试3: 短剧生产 昆仑洞天 ===")
results = engine.search("短剧生产 昆仑洞天 关键帧", top_k=5)
for r in results:
    print("  [{:.3f}] {}".format(r["similarity"], r["key"][:60]))

print()
print("=== 测试4: 9120记忆网关 增量同步 ===")
results = engine.search("9120 记忆网关 增量同步", top_k=5)
for r in results:
    print("  [{:.3f}] {}".format(r["similarity"], r["key"][:60]))

print()
print("=== 测试5: 质量评分 数据治理 ===")
results = engine.search("质量评分 数据治理 自动分类", top_k=5)
for r in results:
    print("  [{:.3f}] {}".format(r["similarity"], r["key"][:60]))
