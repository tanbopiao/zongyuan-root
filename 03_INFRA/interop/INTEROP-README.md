# 元极恒一自治内核 · MCP / A2A 互操作层

> DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω ｜ INTEROP-V1.0 ｜ 2026-10-09
> 位置：`03_INFRA/interop/`（7 大类收敛：03_INFRA=基础设施+配置+网关）

## 组成

| 文件 | 协议 | 形态 | 说明 |
|---|---|---|---|
| `omega_mcp_server.py` | MCP (Model Context Protocol) | stdio JSON-RPC 2.0，零依赖 | 把内核能力暴露为 MCP tools，供任意 MCP client（Claude/CodeArts/Cursor 等）调用 |
| `omega_a2a_server.py` | A2A (Agent2Agent) | HTTP + JSON-RPC 2.0，零依赖 | 把内核暴露为可发现的 A2A agent，支持 agent card 与任务交互 |
| `agent-card.json` | A2A | 静态声明 | Agent Card（技能清单/身份元数据），A2A server 与静态发现共用同一份 |

## MCP 接入

```json
{
  "mcpServers": {
    "omega-zongyuan-kernel": {
      "command": "python3",
      "args": ["/path/to/zongyuan-root-sync/03_INFRA/interop/omega_mcp_server.py"]
    }
  }
}
```

工具清单：`omega_status` / `truth_report(key,value,...)` / `truth_recall(key)` / `truth_list(limit)` / `memory_anchor(anchor_type,...)` / `node_heartbeat(note)`

## A2A 接入

```bash
python3 03_INFRA/interop/omega_a2a_server.py --port 8099
curl http://127.0.0.1:8099/.well-known/agent-card.json     # 发现
curl -X POST http://127.0.0.1:8099/ -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"message/send","params":{"message":{"role":"user","parts":[{"kind":"text","text":"status"}]}}}'
```

指令技能：`status` / `recall <key>` / `report <key>=<value>` / `anchor <keyword>` / `heartbeat`

## 设计约定

1. **单一身份**：MCP 与 A2A 共用同一节点身份 `NODE-DEV-CODEARTS-001`（DID-BR-000002），心跳复用已注册节点，不重复注册（METALAW.011）。
2. **真值规范**：上报一律 `key`/`value` + `anchor=Ω₀⊂⊙∞⊂Ω`，禁用 `content` 字段。
3. **零依赖**：两协议均为手写 JSON-RPC 2.0，无 fastapi/mcp 包依赖（当前实例 fastapi/mcp 不可用，uvicorn 亦未使用）。
4. **鉴权**：中枢访问头 `X-DID` + `X-Capture-Token`（可用环境变量 `ZR_CAPTURE_TOKEN` 覆盖）。
5. A2A capabilities 声明 `streaming=false`（未实现 SSE 的 message/stream），`stateTransitionHistory=true`（TASKS 内存表）。