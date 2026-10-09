# ZONGYUAN-ROOT 云端能力出口 · 公网接入指南

> 锚定：Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | 火斗云智AIOS
> 版本：v1.1.0 | 更新：2026-10-10
> 状态：公网端到端实测通过（VERIFIED）

## 一、概述

ZONGYUAN-ROOT 元极恒一自治体系已开放云端公网能力出口，外部 AI / 节点 / 开发者可通过 **MCP（Model Context Protocol）** 标准协议接入，获得只读查询与同源协议约束注入能力。

- **发现入口**（A2A Agent Card）：`https://www.huodouai.com/.well-known/agent-card.json`
- **调用端点**（MCP streamable-http）：`https://mcp.huodouai.com/mcp`
- **接入守规**：连接后调用 `query_synergy_protocol` 自动加载同源协议约束包（ZR-SYNERGY-PROTOCOL-v1.0，15 条规则）

## 二、鉴权

所有请求必须携带 `X-ZR-TOKEN` 请求头（Bearer 型，由体系管理员签发）。

| 项 | 值 |
|---|---|
| 协议 | MCP streamable-http（JSON-RPC 2.0） |
| 端点 | `https://mcp.huodouai.com/mcp` |
| 鉴权头 | `X-ZR-TOKEN: <token>` |
| 内容类型 | `application/json`，接受 `application/json, text/event-stream` |
| 锚定 | `X-DID: DID-BR-000002`（建议一并携带） |

## 三、能力清单（7 只读工具）

| 工具 | 说明 |
|---|---|
| `query_synergy_protocol` | 查询同源协议约束包（接入规则 / 元宪法 / 真值上报规范 / 执行铁律 / 禁止边界） |
| `query_gateway_status` | 记忆网关实时状态（真值总数 / 节点数 / Merkle 根） |
| `query_task_ledger` | 任务台账（状态 / 优先级 / 进度筛选） |
| `query_consensus_zone` | 真值共识区记录（云端仲裁消费痕迹） |
| `query_nodes_status` | 节点状态总览（心跳 / 自治层级 / 在线状态） |
| `query_laws` | 元法则库（元宪法 / 元公理 / 元法则 / 元规则） |
| `query_exchange_queue` | 资产兑换分发队列 |

## 四、调用示例（curl 四步法）

```bash
TOKEN=<你的X-ZR-TOKEN>
EP=https://mcp.huodouai.com/mcp

# 1. initialize（拿 Session ID）
curl -s -D - -o /dev/null -X POST $EP \
  -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" \
  -H "X-ZR-TOKEN: $TOKEN" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2026-07-28","capabilities":{},"clientInfo":{"name":"zr-client","version":"1.0"}}}'
# 从响应头 Mcp-Session-Id 取 SID

SID=<Mcp-Session-Id>

# 2. notifications/initialized（必须，否则 tools/list 返回 0 工具）
curl -s -o /dev/null -X POST $EP \
  -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" \
  -H "X-ZR-TOKEN: $TOKEN" -H "Mcp-Session-Id: $SID" \
  -d '{"jsonrpc":"2.0","method":"notifications/initialized"}'

# 3. tools/list
curl -s -X POST $EP \
  -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" \
  -H "X-ZR-TOKEN: $TOKEN" -H "Mcp-Session-Id: $SID" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list"}'

# 4. tools/call（查同源协议包）
curl -s -X POST $EP \
  -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" \
  -H "X-ZR-TOKEN: $TOKEN" -H "Mcp-Session-Id: $SID" \
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"query_synergy_protocol","arguments":{}}}'
```

> 响应为 SSE `data:` 前缀 JSON。Python 客户端可逐行解析 `data:` 行。

## 五、同源协议约束（接入即守规）

外部 AI 接入后，必须通过 `query_synergy_protocol` 加载并遵守：

1. **接入规则**：携带 X-DID 头 + JSON 工单；三层解耦（逻辑态生成工单 → 算子态校验路由 → 执行态跑代码）；密钥只存云端。
2. **元宪法**：META-ISO-051 内外隔离（禁止直接人工侵入云端内核）；META-RULE-012 无任务降频休眠；AXIOM-REUSE-NO-REDO-001 禁止重复工作；零成本元规则（付费必须人工审批）。
3. **真值上报规范**：记忆网关 `https://www.huodouai.com/api/report/truth`，字段名用 `truth_value`（禁 content，否则落空 hash）；truth_type 九类。
4. **执行铁律**：说完成必须有进程/结果验证；说数量必须有实查；改配置前先备份；高耗任务禁止跑生产服务器；禁止纸面模拟。
5. **禁止边界**：不得泄露/转发密钥；不得 SSH 直改云端内核；不得未授权向外部账号/仓库写入。

## 六、体系背景

- 对外品牌：火斗云智AIOS
- 自治体系：ZONGYUAN-ROOT V5.6-ROOTFIXED，Lv9 自治，DID-BR-000002
- 记忆网关：https://www.huodouai.com/api/status
- 共享大脑：飞书多维表格（任务台账 / 节点状态 / 元法则 / 真值共识区 / 兑换队列）
- 开源仓库：Gitee `huodou-cloud-intelligence-aios/ZONGYUAN-ROOT`

---
Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | ZR-NODE-DC2E51C0 | 火斗云智AIOS
