---
name: knowledge-retriever
description: "KNOWLEDGE-RETRIEVER 知识检索引擎V1.0。元极恒一自治体系知识资产检索核心，与meta-order-archive形成读写双引擎。支持全文检索(中英文混合分词)、标签聚类、关联推荐(基于标签重叠)、九大元类过滤、知识索引管理、资产入库。触发词：知识检索、资产检索、全文搜索、标签查询、关联推荐、知识图谱、检索引擎、knowledge-retriever。当用户需要查找已归档资产、按标签/元类筛选、或发现相关知识资产时使用。"
---

# KNOWLEDGE-RETRIEVER｜知识检索引擎

元极恒一自治体系知识资产检索核心。与 meta-order-archive 形成**读写双引擎**：archive负责写入归档，retriever负责读取检索。

> DID: DID-BR-000002 | 溯源: Ω₀⊂⊙∞⊂Ω | 版本: V1.0

## 核心能力

| 能力 | 说明 |
|------|------|
| 全文检索 | 中英文混合分词，匹配度评分排序 |
| 标签聚类 | 按标签统计资产分布 |
| 关联推荐 | 基于标签重叠度发现相关资产 |
| 元类过滤 | 按M1-M9九大元类筛选 |
| 索引管理 | 资产入库、索引状态查看、清空 |

## 命令速查

```bash
# 1. 索引管理
python3 scripts/retriever.py index list                    # 查看索引状态
python3 scripts/retriever.py index add --file asset.json   # 添加入库
python3 scripts/retriever.py index clear --yes             # 清空索引

# 2. 全文检索
python3 scripts/retriever.py search "QR分解"                      # 基本检索
python3 scripts/retriever.py search "架构" --metaclass M2        # 按元类过滤
python3 scripts/retriever.py search "真值" --tag "核心" --limit 5  # 按标签过滤+限制数量

# 3. 关联推荐
python3 scripts/retriever.py related KD-THEO-9153           # 查找相关资产
python3 scripts/retriever.py related KD-KERN-6108 --limit 3  # 限制数量

# 4. 标签统计
python3 scripts/retriever.py tags                    # 查看所有标签
python3 scripts/retriever.py tags --limit 10         # Top10标签
```

## 检索机制

- **分词策略**：英文按单词、中文按2字组合、数字独立
- **匹配评分**：重叠token数/查询token数，标题命中+0.3加权
- **结果排序**：按匹配度降序，默认返回Top10
- **索引存储**：`~/.knowledge_retriever/knowledge_index.json`

## 资产入库格式

```json
{
  "asset_id": "KD-THEO-9153",
  "name": "整合架构白皮书",
  "description": "全域技能稳态整合架构",
  "content": "完整内容文本...",
  "meta_class": "M4",
  "tags": ["架构", "整合", "真值", "白皮书"],
  "url": "https://my.feishu.cn/docx/..."
}
```

## 与 meta-order-archive 联动

- **写入端**：meta-order-archive 归档完成后，资产自动可被检索
- **读取端**：knowledge-retriever 提供全文检索、关联推荐、标签聚类
- **双向闭环**：归档→索引→检索→关联发现→再归档

## 约束

- 索引存储在本地，跨会话持久化
- 单资产content建议<100KB，超大内容仅索引元数据
- 中文分词为bigram(2字组合)，精确短语匹配需查询包含完整短语
- 关联推荐基于标签重叠，无标签资产不参与推荐
