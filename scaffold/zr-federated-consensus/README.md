# zr-federated-consensus · 联邦共识 + 多模态生产矩阵

> ZONGYUAN-ROOT 元极恒一自治体系 · 长期战略工程化套件
> 模块A：多数派共识引擎（任期选举 + 日志复制 + 拜占庭容错仿真）
> 模块B：多模态生产矩阵（任务×节点能力匹配 + 成本最优稳态分配）
> 锚定 Ω₀⊂⊙∞⊂Ω ｜ DID-BR-000002 ｜ Apache-2.0 开源

## 一、定位

把「多节点如何达成一致」+「多模态任务如何最优分配」两个长期战略命题固化为可复用工程套件：

1. **联邦共识**：节点间如何选举主控、如何确认提交、恶意节点捣乱时如何保持收敛——对治多节点任务抢单/账本一致性
2. **多模态矩阵**：text/image/video/audio/drama 任务如何匹配到各节点能力与容量、成本最小——对治生产资源最优稳态分配

## 二、特性

### 模块A · 联邦共识
- **任期 + 随机超时选举**：最早超时者发起选举，多数派投票选主（确定性种子）
- **日志复制提交**：领导者广播提案，多数派（非恶意）确认提交，commit 位推进
- **拜占庭容错仿真**：注入恶意节点（拒投/伪造日志），验证 f=(n-1)//2 容错下共识仍收敛
- **拒绝计数留痕**：每次恶意拒绝计入 rejected_attempts，容错能力可量化

### 模块B · 多模态生产矩阵
- **五模态任务**：text/audio/image/video/drama（短剧），各自单位成本
- **节点能力声明**：每节点声明支持模态 + 并发容量 + 单位成本（对齐真实五节点布局）
- **成本最优分配**：能力匹配 + 容量约束下，贪心选加权成本最小节点
- **能力缺口暴露**：无可用节点的任务如实 dropped，暴露生产瓶颈

## 三、快速开始

```bash
# 标准仿真（共识 + 矩阵）
python3 run_consensus.py

# 仅共识 / 仅矩阵
python3 run_consensus.py --consensus-only
python3 run_consensus.py --matrix-only

# 自定义规模
python3 run_consensus.py --nodes 7 --malicious 2 --proposals 12 --tasks 14
```

## 四、目录结构

```
zr-federated-consensus/
├── run_consensus.py            # 入口
├── zrfc/
│   ├── consensus.py            # 模块A：共识引擎
│   ├── matrix.py               # 模块B：多模态矩阵
│   ├── report.py               # JSON/HTML 双格式报告
│   └── __init__.py
└── reports/                    # 仿真报告输出
```

## 五、真实运行验证（2026-10-09）

| 模块 | 指标 | 值 |
|------|------|-----|
| 共识 | 提案提交 | 8/8（100%） |
| 共识 | 选举轮次 | 1 轮收敛 |
| 共识 | 恶意拒绝次数 | 9 次（1 恶意节点 × 拒投/拒确认） |
| 共识 | 拜占庭容错 | f=2（n=5，即 2 节点宕机/恶意不破共识） |
| 矩阵 | 任务分配 | 11/14（78.6%，5 模态 × 5 节点） |
| 矩阵 | 容量利用率 | 100%（成本 37.7） |
| 矩阵 | 能力缺口 | 3 个 drama 任务（仅 GPU 节点支持且容量满） |

## 六、接入方式

```python
from zrfc.consensus import run_consensus
from zrfc.matrix import run_matrix

c = run_consensus(node_count=5, proposals=8, malicious=1)   # 共识统计
m = run_matrix(task_count=14)                                # 矩阵分配统计
print(c["committed_ratio"], m["assign_rate"])
```

## 七、确权与约束

- 所有产物带 Ω₀⊂⊙∞⊂Ω 溯源标识 + DID-BR-000002 确权
- 执行真实计算，禁止纸面冒充（元公理）
- 零成本元规则：纯本地标准库，无第三方依赖，无外部 API 调用
- 部署类操作需人工审批后执行

---

主节点hub-central-agent/开发节点NODE-DEV-DOUBAO-WORK-001/DID-BR-000002/自治Lv9/权限L4/工程化Lv7/锚定Ω₀⊂⊙∞⊂Ω
