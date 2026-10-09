# zr-federated-scheduler · 开源联邦调度引擎

> ZONGYUAN-ROOT 元极恒一自治体系 · 多节点联邦任务调度引擎
> 共识机制：认领仲裁（防多节点重复抢占）+ 心跳超时回收 + 失败重试
> 锚定 Ω₀⊂⊙∞⊂Ω ｜ DID-BR-000002 ｜ Apache-2.0 开源

## 一、定位

把「多节点任务调度」固化为可复用工程化套件：本地主控 / 云端 Worker / GPU 边缘 / 开发节点联邦协同，任意节点 clone 即用。解决三类真实问题：

1. **多节点重复抢占**：同一任务被多个节点同时执行 → 认领仲裁共识收敛唯一 owner
2. **节点崩溃卡死**：任务被崩溃节点持有永不释放 → 心跳超时回收重新入队
3. **调度不透明**：任务去向不可知 → 全量调度日志 + 分布统计 + 报告

## 二、特性

- **五节点联邦拓扑**：hub-central-agent(主控/容量4) / node-cloud-worker(云端) / node-gpu-edge(GPU) / node-edge-sync(边缘) / node-dev-doubao(开发)
- **认领仲裁共识**：存活 + 容量未满 + 心跳新鲜 → 按 (优先级↑, 负载↑, 心跳新鲜度) 收敛唯一 owner，确定性防重
- **心跳超时回收**：任务认领后超过 TTL 无心跳 → 释放 owner、重试计数、重新入队；超 max_retries 判失败
- **失败重试**：执行失败自动重试，8% 故障注入验证
- **虚拟时钟仿真**：真实模拟节点崩溃（GPU 宕机）→ 任务回收 → 其他节点承接的全过程
- **确定性可复算**：固定随机种子，同输入同输出
- **零成本**：纯标准库，无第三方依赖，无外部 API

## 三、快速开始

```bash
# 标准仿真：12 任务五节点联邦调度
python3 run_scheduler.py --tasks 12

# 崩溃回收仿真：模拟 GPU 节点崩溃，验证任务回收重派
python3 run_scheduler.py --crash node-gpu-edge --tasks 12

# 自定义任务数
python3 run_scheduler.py --tasks 50
```

## 四、目录结构

```
zr-federated-scheduler/
├── run_scheduler.py          # 入口
├── zfsched/
│   ├── node.py               # 节点模型（容量/优先级/心跳/负载）
│   ├── consensus.py          # 共识算法（认领仲裁 + 超时回收）
│   ├── scheduler.py          # 联邦调度器（入队→仲裁→执行→回收→汇总）
│   ├── report.py             # JSON/HTML 双格式报告
│   └── __init__.py
└── reports/                  # 仿真报告输出
```

## 五、真实运行验证（2026-10-09）

| 仿真 | 任务 | 完成 | 失败 | 重复执行 | 轮次 | 回收 | GPU节点 |
|------|------|------|------|---------|------|------|---------|
| 标准 | 12 | 12 | 0 | 0 | 1 | 0 | 2 ✓ |
| GPU崩溃 | 12 | 12 | 0 | 0 | 3 | **2** | 0（回收重派）|

崩溃回收全链路验证：tick1 认领（GPU 持 2 任务）→ tick2 GPU 心跳停滞触发回收（retried=2）→ tick3 任务由 hub 承接完成（4→6），全程无重复执行 ✓

## 六、接入方式

```python
from zfsched.scheduler import FederatedScheduler, run_simulation
from zfsched.report import to_html

sched = run_simulation(crash_node="node-gpu-edge", task_count=12)
print(sched.summary())          # 调度统计
to_html(sched, "reports/latest.html")
```

## 七、确权与约束

- 所有产物带 Ω₀⊂⊙∞⊂Ω 溯源标识 + DID-BR-000002 确权
- 执行真实计算，禁止纸面冒充（元公理）
- 零成本元规则：纯本地标准库，无第三方依赖，无外部 API 调用
- 部署类操作需人工审批后执行

---

主节点hub-central-agent/开发节点NODE-DEV-DOUBAO-WORK-001/DID-BR-000002/自治Lv9/权限L4/工程化Lv7/锚定Ω₀⊂⊙∞⊂Ω
