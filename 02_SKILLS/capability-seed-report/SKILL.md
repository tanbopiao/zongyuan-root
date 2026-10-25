---
name: "capability-seed-report"
description: "Distills frontier-model high-level capability seeds (3D/video/audio/agent/reasoning/embodied etc.), structures them into namespace-key truths, batch-reports to the cloud hub, and writes hash-ledger evidence. Invoke when user asks to 提炼/上报某领域高阶能力种子, 挖掘大模型能力, or batch-report structured truths."
---

# 高阶能力种子提炼与云端上报

把一个能力域（模态/技术方向）的全行业前沿能力，提炼成结构化种子真值，批量上报云端中枢并留痕。

## 何时使用

- 用户要求「提炼/挖掘某领域高阶能力种子并上报云端」
- 用户要求「批量上报结构化真值 / 能力谱系 / 行业对比」
- 需要把调研结论沉淀为可检索、可验签的真值条目

## 前置条件

- 运行环境存在上报网关：`scripts/services/seed_extraction_engine.py`，提供 `report_truth(payload)` 与 `build_key(core)`，内部已含网关签名（X-DID / X-Signature / X-Signature-Timestamp）
- 账本文件：`atomgit_sync/HASH-LEDGER.csv`（追加式留痕）
- 同步器：`scripts/services/auto_reporter.py`（把新增账本行 / 锁档文件上报云端）
- 签名口令由元内核受控保管，业务脚本**不得**自行读取、打印或写入口令

## 工作流

### 1. 界定能力矩阵（先定域，再检索）

先列出该领域的 5–8 个子维度，每个维度独立检索，避免只搜综合榜单一篇文章。示例（3D 域）：

| 子维度 | 典型问题 |
|---|---|
| 生成 | 文/图/视频 → 3D |
| 理解 | 多视角几何、空间推理 |
| 编辑 | 指令编辑、部件生成 |
| 世界模型 | 场景生成、具身环境 |
| 交互 | 实时交互、物理模拟 |
| 感知 | 2D/3D 定位 |
| 谱系 | 能力分类 + 行业趋势 |

### 2. 分域检索

- 每个子维度至少一次检索，覆盖海外头部（Google / OpenAI / Anthropic / NVIDIA）与国内头部（腾讯 / 字节 / 阿里通义 / 快手 / DeepSeek / 宇树 / 智元）
- 记录可核查细节：版本号、发布日期、参数规模、时长/分辨率/帧率、榜单分数、价格
- **禁止编造**：无出处的数字不写；不确定的标注 `claim` / `reported_spec` 保持原表述

### 3. 结构化种子

命名空间 key（不可乱写，网关会校验）：

```
KERNEL.<域>.<子类>.<种子名>.<日期YYYYMMDD>
例: KERNEL.EMBODIED.UNITREE-G1.20261025
```

value 必须为对象且字段数 ≥ 2，并补齐锚定字段：

```json
{
  "vendor": "厂商",
  "model": "模型/产品名",
  "category": "能力分类",
  "capabilities": ["要点1", "要点2"],
  "significance": "为什么值得记",
  "anchor": "Ω₀⊂⊙∞⊂Ω",
  "did": "DID-BR-000002",
  "source_node": "NODE-ID",
  "extracted_at": "YYYY-MM-DDTHH:MM:SS"
}
```

上报 payload 统一为：

```json
{ "key": "...", "value": {...}, "source_node": "NODE-ID", "confidence": 0.95, "truth_type": "data" }
```

- `truth_type`：事实/能力条目用 `data`；法则/规则用 `meta_law`；裁决/决策用 `decision`
- `confidence`：有明确出处 0.95；官方口径但未第三方验证 0.9；推测不写

### 4. 批量上报

用 `scripts/report_seeds.py <seeds.json>`（本 skill 自带模板）：逐条上报，0.3s 间隔，输出 seq 汇总。seeds.json 形如：

```json
[
  { "key": "KERNEL.XXX.YYY.20261025", "value": { "a": "1", "b": "2" }, "truth_type": "data" }
]
```

### 5. 写锁重试（重要）

云端中枢为 SQLite，批量蒸馏任务会持有写锁，表现为 `{"error": "write_failed"}`。**这不是签名问题，不要改签名逻辑。**

- 重试策略：失败 → 等待 60–120s → 整批重跑（幂等，key 相同覆盖）
- 连续 3 轮仍失败，才排查云端锁持有方
- 全部成功后核对 seq 连续

### 6. 账本留痕

向 `atomgit_sync/HASH-LEDGER.csv` 追加一行：

```
<ISO8601+08:00>,<批次ID>,<自然语言摘要: 条数/seq区间/维度覆盖/失败数>,<DID>
```

### 7. 同步云端

```bash
cd /workspace/scripts/services && python3 auto_reporter.py --once
```

确认输出含 `OK 账本上报 seq=...` 且 `失败0`。

## 交付格式

向用户汇报时给：

1. 成功/失败条数与 seq 区间
2. 按维度的表格（维度 | 代表模型与要点）
3. 过程异常（如写锁重试）如实说明
4. 账本行 ID

## 反面清单

- 不要把口令、token、密钥写进种子或脚本（元内核受控保管，仅「元极恒一」链路可取）
- 不要用扁平字符串当 value（网关拒收），必须结构化对象
- 不要在 key 里放空格/中文/特殊符号之外的不稳定内容；key 一经上报即为唯一标识
- 不要把一次性的任务进度、临时路径写进本 skill
