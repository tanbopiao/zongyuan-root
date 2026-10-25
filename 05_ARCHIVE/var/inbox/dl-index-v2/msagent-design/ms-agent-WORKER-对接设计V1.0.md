# ms-agent 主控 × ZONGYUAN worker 执行手 · 对接设计 V1.0

> 2026-10-08 | DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | 设计阶段（未部署，不烧额度）

## 一、定位：谁做什么

```
用户意图
   ▼
ms-agent（云端服务器 · 调度大脑）
   │  工具调用层（自动决定调哪个工具）
   ▼  ──── 现有联通通道 ────
   │   · ntfy 命令槽 (zongyuan-kunlun-2026)
   │   · git 命令槽 (control/CMD-*.json)
   │   · 云端记忆网关 (huodouai.com)
   ▼
多个临时GPU/CPU实例（worker · 执行手）
   · 已有能力全部保留，不改内部
```

**核心原则：ms-agent 只做"编排决策"，不碰实例联通；worker 只做"执行回传"，不理解 agent 意图。中间用现有协议对接。**

## 二、现有 worker 能力盘点 → ms-agent 工具映射

从现有脚本提取 worker 的 6 类可执行能力，逐一封装为 ms-agent 标准 tool（OpenAI function-calling 风格 JSON schema）：

| # | ms-agent 工具名 | 对应现有脚本 | 入参 | 出参 |
|---|---|---|---|---|
| T1 | `node_exec_command` | `zr_node_protocol.encode_cmd` + worker 执行 | `{node?, cmd, timeout}` | `{task_id, out, code}` |
| T2 | `node_scan_environment` | `scan_environment.py` | `{node?}` | `{gpu, ports, pyenv, net}` |
| T3 | `node_run_training` | `one_click_train.py` | `{node, corpus, model, epochs}` | `{job_id, log, metrics}` |
| T4 | `cloud_report_truth` | `zr_node_protocol.report_truth` | `{truth_key, truth_value}` | `{seq, status}` |
| T5 | `node_save_frame` | `intel-operators/frame_snapshot_autosave.py` | `{source, character, scene, shot_id}` | `{frame_id, hash, backup}` |
| T6 | `node_record_bill` | `intel-operators/resource_bill.py` | `{operator_id, tier, tokens}` | `{bill_id}` |

## 三、工具定义示例（ms-agent 标准 schema）

以 T1 `node_exec_command` 为例，ms-agent 工具清单里这样注册：

```json
{
  "type": "function",
  "function": {
    "name": "node_exec_command",
    "description": "在指定同源节点(或广播)执行受白名单保护的shell命令，返回执行输出与退出码",
    "parameters": {
      "type": "object",
      "properties": {
        "node": {
          "type": "string",
          "description": "目标节点名，如 ZR-NODE-MODEL-GPU-01；省略=广播所有在线worker",
          "enum": ["ZR-NODE-MODEL-GPU-01", "ZR-NODE-MODEL-GPU-02", "ZR-NODE-CPU-01"]
        },
        "cmd": { "type": "string", "description": "受白名单保护的shell命令" },
        "timeout": { "type": "integer", "description": "超时秒数", "default": 300 }
      },
      "required": ["cmd"]
    }
  }
}
```

其余 5 个工具同理，`node` 字段为公共参数（目标节点）。

## 四、ms-agent 主控调度工作流

**典型场景：主控收到"检查所有GPU节点状态并上报"**

```
1. ms-agent 分析 → 决定调用 T2 node_scan_environment (广播)
2. ms-agent 经联通通道下发: encode_cmd("python3 scan_environment.py", node=None=广播)
3. 各worker执行 scan_environment.py → 各自POST结果到云端
4. ms-agent 汇总各节点结果 → 调用 T4 cloud_report_truth 上报聚合真值
5. ms-agent 生成决策结论，回复用户
```

**关键衔接点：**
- 工具入参 `node` → 映射到 `encode_cmd` 的 `node` 字段（精确节点）或省略（广播）
- 工具入参 `cmd` → 必须通过 worker 白名单（`check_safe`），危险命令在 worker 侧拦截
- worker 回传 → 走云端 `RESULT.<task_id>` 或 ntfy 结果主题，ms-agent 轮询/订阅接收
- ms-agent 本身不存实例状态，状态查询一律实时调用工具

## 五、安全边界（沿用现有铁律）

1. **白名单不变**：ms-agent 生成的 `cmd` 仍需通过 worker `check_safe`，危险命令黑名单在 worker 侧兜底拦截
2. **付费隔离**：ms-agent 涉及付费API的工具调用，必须人工审批（META-RULE-012）
3. **配额保护**：ms-agent 调度时读配额状态，耗尽自动降级只读空转
4. **确权校验**：所有工具调用携带 `zr_did: DID-BR-000002`，ms-agent 未鉴权请求被 worker 拒绝

## 六、落地步骤（分阶段，最小额度）

| 阶段 | 动作 | 是否烧额度 |
|---|---|---|
| P0 | 把本设计写入数据湖 + 上报云端 | 否 |
| P1 | 云端服务器装 ms-agent，注册 6 个工具 schema | 免费算力 |
| P2 | 写适配层：工具调用 → `encode_cmd` 封装 | 否 |
| P3 | 单节点端到端联调（T1/T4 打通） | 极少量 |
| P4 | 全工具接入 + 多节点并行 | 按需 |

## 七、结论

ms-agent 不替换现有联通通道，而是**加一层标准化的工具编排**：
- 现有 worker（ntfy/git命令槽/云端上报）全部复用，不改内部
- ms-agent 在云端作为调度大脑，把"派任务→收结果→汇总→决策"做成标准 agent 工作流
- 收益：多临时实例调度从手搓脚本 → 自然语言+工具编排；第三方开发者熟悉 ms-agent 即可接入

---
*Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | 火斗云智AIOS*
