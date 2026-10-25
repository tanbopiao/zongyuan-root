# ZONGYUAN-ROOT 自治内核基底

> **确权**: Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | ZR-NODE-DC2E51C0 | 火斗云智AIOS
> **版本**: V1.0 | **日期**: 2026-10-08
> **定位**: 云端中枢真自治能力（自动决策 + 自我进化）的标准化可复用基底，任何同源节点可一键拉起。

---

## 一、基底是什么

这是一套**已验证、可复用、可一键部署**的自治内核基底，让任何同源节点 / 新环境快速拉起"自动决策 + 自我进化"的云端中枢能力。它把火斗云智AIOS的核心自治内核从"一次性的部署成果"固化为"标准化的可复制基底"。

## 二、目录结构

```
zongyuan-autonomy-kernel/
├── kernel/                          # 自治内核核心代码
│   ├── zr_node_protocol.py          # NTFY-CONNECT-001 协议 (身份/命令/真值上报)
│   ├── zr_node_worker.py            # 同源节点 worker (订阅命令/执行/回传/心跳)
│   ├── zr_cloud_ctl.py              # 云端主控 (自动决策 + 自我进化 + AxiomGate + 自治算子)
│   ├── zr_axiom_gate.py             # AxiomGate 裁决器 (四维校验+风险三优先+配额稳态)
│   └── zr_autonomy_ops.py           # 自治算子集 (因果链跟踪 + 异常自愈)
├── deploy/
│   └── bootstrap_autonomy_kernel.sh # 一键部署脚本 (worker|controller|full)
└── docs/
    └── 云端轻量调度主控-部署SOP-V1.0.md  # 详细部署运维手册
```

## 三、核心能力

| 能力 | 说明 |
|---|---|
| **自动运行** | systemd 托管，自动启动 + 崩溃自愈 |
| **自动感知** | 节点表自动维护（心跳 / 上线 / 完成） |
| **自动决策** | 任务池 + 能力匹配，自动派发待办任务 |
| **自我进化 (RSI)** | 节点信誉表，依据历史结果调整派发策略 |
| **AxiomGate 裁决** | 派发前四维真值校验 + 风险三优先评分 + 配额稳态三重裁决 |
| **因果链跟踪** | 任务 入池→派发→完成→上报 全生命周期可回溯，防分叉 |
| **异常自愈联动** | 僵死任务自动清理 + 节点失败计数 + 反复失败节点自动隔离 + 成功解除隔离 |
| **记忆蒸馏** | 高价值经验自动沉淀，低价值/陈旧记忆周期净化淘汰（SFMP联邦记忆池思路） |
| **A/B 策略寻优** | epsilon-greedy 多臂老虎机，在信誉优先/能力优先/均衡三策略间灰度实验，自动选最优 |
| **资源账单统计** | 任务级消耗记录(耗时/结果)，按节点/策略聚合，复用去重提示，成本可审计 |
| **灰度发布** | 新节点先进灰度池(小流量验证)，稳定自动转正，失败自动隔离回滚；高风险任务仅过灰度的节点可接 |
| **视觉快照记忆** | 任务/节点状态快照(输出/心跳/指纹)，异常可回看历史快照定位（VISTA记忆思路） |
| **自动上报** | 真值中枢 X-Capture-Token + X-DID 双向握手 |
| **多节点兼容** | CPU/GPU 异构节点统一接入 |

## 灰度发布 + 视觉快照记忆（V1.3）

- **灰度发布**：节点分三态 canary/active/quarantined；低风险任务 all 可接，高风险任务仅 active 可接；canary 达最小任务数(2)且成功率≥0.8 自动转正，失败自动隔离；呼应风险三优先
- **视觉快照记忆**：任务派发/完成/错误 + 节点心跳自动存快照（含内容指纹），`/snapshots` 端点回看，异常定位（VISTA 视觉记忆思路）
- 控制面新增 `/canary`（灰度状态）、`/snapshots`（快照回看）端点

实测证据（2026-10-10）：
```
[决策] 派发 t-canary-1 → NODE(信誉100,策略=capability_first,风险=low) | echo CANARY-TEST
/snapshots → task_start {cmd,risk} + task_done {code:0}
```

## 资源账单统计（V1.2）

- **成本可审计**：每个派发任务记录 算子/节点/命令/耗时/结果，写入 JSONL 账单台账
- **聚合看板**：按节点/策略聚合任务数、成功失败、平均耗时、累计耗时，`/bill` 端点查询
- **复用去重**：相同命令 60s 窗口内重复执行，标记可复用（呼应复用优先公理）
- 呼应 **META-RULE-012 配额稳态保护**，为成本最小化决策提供数据支撑

实测证据（2026-10-08）：
```
/bill → {total_tasks:1, success:1, failed:0, total_duration_s:6.17s, by_node:{...}}
```

## 记忆蒸馏 + A/B 策略寻优（V1.1）

- **记忆蒸馏**：任务成功/失败自动沉淀经验真值，低价值(价值<0.5)不沉淀，陈旧+低价值周期淘汰，超限按价值+新近裁剪
- **A/B 策略实验**：派发策略三选（信誉优先/能力优先/均衡），epsilon=0.15 探索+利用，按成功率自动偏向最优策略
- **自愈联动升级**：僵死任务触发节点失败计数，连续失败≥3次自动隔离（不派发），节点成功后自动解除隔离

实测证据（2026-10-08）：
```
[决策] 派发 t-mab-1 → NODE(信誉100,策略=capability_first) | echo MAB-TEST-1
[决策] 派发 t-mab-2 → NODE(信誉100,策略=reputation_first) | echo MAB-TEST-2
```
两个任务自动选用不同策略，epsilon-greedy 探索正常工作。

## 自治算子集（V1.0）

新增因果可回溯 + 自愈能力：

- **因果链跟踪**：任务全生命周期（enqueue→dispatched→done/failed）写入 JSONL 台账，节点、命令、时间戳、退出码完整可溯
- **异常自愈**：派发后超时(120s)无结果的僵死任务自动检测清理，防任务悬空

实测证据（2026-10-08，任务 t-ops-1）：
```
{"task_id":"t-ops-1","stage":"dispatched","node":"NODE","task":"echo OPS-CAUSALITY-OK"}
{"task_id":"t-ops-1","stage":"done","node":"NODE","detail":"exit=0"}
```
因果链 dispatched→done 完整记录，可溯源审计。

## AxiomGate 裁决器（V1.0）

派发前强制三重裁决，高危任务自动拦截：

- **L1 四维真值校验**：空间(命令)/时间(时间戳)/属性(能力标签)/因果(任务ID) 完整性
- **L2 风险三优先**：风险最小 > 成本最小 > 收益最大；高危命令(rm -rf/mkfs/drop等)硬拦截，低信誉(<40)节点拦截
- **L3 配额稳态**：正常→预警(<30%)→只读空转(<10%)，只读空转禁派发消耗型任务

实测证据（2026-10-08）：
```
[AxiomGate拦截] t-gate-highrisk→NODE | 四维=True 风险=high 配额=normal | 派发跳过
[决策] 派发 t-gate-ok → NODE(信誉100) | echo AXIOM-GATE-OK
```
高危任务被拦、正常任务放行，安全裁决在生产链路生效。

## 四、一键部署

### 角色说明
- **worker**: 同源节点接入（订阅命令并执行）
- **controller**: 云端主控（自动决策 + 自我进化 + 控制面）
- **full**: 全栈（本地同时跑 worker + 主控）

### Worker 接入
```bash
# 方式A: 从魔搭数据湖拉取基底
cd /mnt/workspace
git clone --depth 1 https://modelscope.cn/datasets/zongyuanroot/ZONGYUAN-SHARED-DATALAKE.git ZSD
cd ZSD/autonomy-kernel

# 方式B: 本地已有基底
cd zongyuan-autonomy-kernel

# 一键拉起 worker
bash deploy/bootstrap_autonomy_kernel.sh worker "ZR-NODE-MODEL-xxx"
```

### 云端主控部署
```bash
bash deploy/bootstrap_autonomy_kernel.sh controller
# 控制面: http://127.0.0.1:9010 (X-CTL-Token: ZR-CTL-2026-OMEGA)
```

## 五、控制面 API（云端主控）

| 接口 | 方法 | 说明 |
|---|---|---|
| `/health` | GET | 健康 + 在线节点快照 |
| `/nodes` | GET | 节点表详情 |
| `/cmd` | POST | 下发命令到指定节点 |
| `/report` | POST | 上报真值到云端中枢 |
| `/enqueue` | POST | 投递待办任务进任务池（自动决策派发） |

## 六、已验证证据

- 自动决策 PASS：`[决策] 派发 t-auto-002 → ZR-NODE-TEST-DECIDE-002`（未手动下发）
- 自我进化 PASS：节点信誉 100→102→104（任务完成自动累积，策略按信誉自适应）
- systemd 自愈 PASS：kill 后自动拉起
- 真值上报：云端中枢 seq 3059 闭环

## 七、确权与溯源

- **确权**: Ω₀⊂⊙∞⊂Ω | DID-BR-000002
- **架构根**: ONT-4D-UNIVERSAL-ROOT
- **主控**: ZR-CLOUD-CTL-001
- **协议**: NTFY-CONNECT-001
- **可信**：本基底为 ZONGYUAN-ROOT 全域自治内核的标准化复制品，仅供同源节点 (DID-BR-000002 系) 部署复用。
