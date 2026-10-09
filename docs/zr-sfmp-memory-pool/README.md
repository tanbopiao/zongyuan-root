# zr-sfmp-memory-pool · SFMP 联邦记忆池引擎

> ZONGYUAN-ROOT 元极恒一自治体系 · 多节点联邦记忆汇聚引擎
> 机制：语义去重 + 冲突消解 + 记忆分层 + 联邦汇聚 + 检索
> 锚定 Ω₀⊂⊙∞⊂Ω ｜ DID-BR-000002 ｜ Apache-2.0 开源

## 一、定位

把「多节点记忆汇聚」固化为可复用工程化套件：本地/云端/GPU/边缘各节点各自沉淀记忆，联邦层统一去重、消解冲突、分层归档、统一检索。对治三问题：

1. **记忆冗余**：多节点重复记录同一事实 → 语义指纹去重，单份留存
2. **记忆冲突**：同 key 不同版本 → 置信度+时间仲裁，冲突留痕
3. **记忆失忆**：新会话无法激活全量记忆 → 分层沉淀（short→long→truth）+ 统一检索

## 二、特性

- **记忆四层**：working(工作) / short(短期) / long(长期) / truth(真值沉淀)
- **语义去重**：归一化指纹（去空白标点+核心片段哈希），同指纹表述自动合并
- **冲突消解**：同 key 异值 → 置信度高者胜，持平取时间新者；冲突清单留痕
- **联邦汇聚**：多节点按 key 归并，跨节点重复合并，输出节点贡献度
- **统一检索**：关键词 / 标签 / 来源节点 / 层级过滤，命中计访问热度
- **确定性可复算**：固定数据构造，同输入同输出
- **零成本**：纯标准库，无第三方依赖，无外部 API

## 三、快速开始

```bash
# 标准联邦仿真：5 节点 × 8 条记忆（含重复表述与冲突对）
python3 run_memory_pool.py

# 自定义规模
python3 run_memory_pool.py --nodes 5 --memory 8
```

## 四、目录结构

```
zr-sfmp-memory-pool/
├── run_memory_pool.py        # 入口
├── sfmp/
│   ├── memory.py             # 记忆条目 + 本地记忆池（去重/遗忘/检索）
│   ├── federate.py           # 联邦汇聚（合并/仲裁/贡献度）
│   ├── report.py             # JSON/HTML 双格式报告
│   └── __init__.py
└── reports/                  # 仿真报告输出
```

## 五、真实运行验证（2026-10-09）

| 指标 | 值 |
|------|-----|
| 节点本地记忆 | 46 条 |
| 联邦汇聚去重后 | **14 条**（去重率 70%） |
| 冲突消解 | 10 对（置信度+时间仲裁） |
| 记忆分层 | short 9 / long 4 / truth 1 |
| 检索验证 | 「真值」关键词命中 ✓ |
| 节点贡献 | hub 7 / cloud 1 / gpu 2 / edge 2 / dev 2 |

## 六、接入方式

```python
from sfmp.memory import MemoryPool
from sfmp.federate import FederatedMemoryPool

p = MemoryPool(node_id="hub-central-agent")
p.write("sys.version", "内核V5.6运行中", confidence=0.95, layer="long")

fmp = FederatedMemoryPool()
fmp.add_pool(p)
fmp.merge()
print(fmp.stats())          # 汇聚统计
print([e.to_dict() for e in fmp.search(keyword="内核")])
```

## 七、确权与约束

- 所有产物带 Ω₀⊂⊙∞⊂Ω 溯源标识 + DID-BR-000002 确权
- 执行真实计算，禁止纸面冒充（元公理）
- 零成本元规则：纯本地标准库，无第三方依赖，无外部 API 调用
- 部署类操作需人工审批后执行

---

主节点hub-central-agent/开发节点NODE-DEV-DOUBAO-WORK-001/DID-BR-000002/自治Lv9/权限L4/工程化Lv7/锚定Ω₀⊂⊙∞⊂Ω
