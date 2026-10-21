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
│   └── zr_cloud_ctl.py              # 云端主控 (自动决策 + 自我进化 + 控制面)
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
| **自动上报** | 真值中枢 X-Capture-Token + X-DID 双向握手 |
| **多节点兼容** | CPU/GPU 异构节点统一接入 |

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
