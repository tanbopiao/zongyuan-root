# 魔搭 MCP 广场提交包｜zongyuan-root-mcp

> DID-BR-000002 锚定：Ω₀⊂⊙∞⊂Ω｜生成日期：2026-10-24
> 提交入口：https://modelscope.cn/mcp/servers/create?template=customize （Web 表单，魔搭 OpenAPI 无创建端点，已核实 `.well-known/openapi.json` 仅含 list/get/deploy/undeploy）
> 本包为「照抄即可填」的提交材料，人工登录表单后逐项粘贴。

## 一、表单字段（基础信息）

| 表单项 | 填写值 |
|---|---|
| 创建类型 | 自定义创建 |
| 英文名称 | `zongyuan-root-mcp` |
| 中文名称 | ZONGYUAN-ROOT 联邦记忆 MCP |
| 来源地址 | 见下方"来源地址选项"（三选一，需人工确认） |
| 所有者 | zongyuanroot（默认已填） |
| 托管类型 | 不托管 / 远程 URL（我方服务自持部署在 huodouai.com，非魔搭创空间托管；若表单仅允许"可托管部署"，需先按其要求改造，见"风险与阻塞项 3"） |

**来源地址选项（人工确认）**：
1. `https://github.com/tanbopiao/kunlun-assets`（既有 GitHub 阵地，但内容为资产仓，非 MCP 服务源码）——不完全匹配
2. 新建公开仓库 `mcp.huodouai.com` 服务端只读镜像（服务端代码在云端 `/root` 下，公开需先脱敏审查）
3. AtomGit 仓 `zongyuangen/zongyuan-root-sync`（无 GitHub 域名，表单若强制 GitHub 则不可用）

> 建议：选项 2 最规范，但属新增对外公开动作，**待人工审批**。

## 二、服务配置

| 项 | 值 |
|---|---|
| 传输协议 | Streamable HTTP（JSON-RPC 2.0，同时接受 `application/json, text/event-stream`） |
| 端点 URL | `https://mcp.huodouai.com/mcp` |
| serverInfo | `zongyuan-root-mcp` v1.0.0 |
| 鉴权 | 端点免鉴权只读；写操作（truth_report）服务端内部鉴权 |

**提交前体检（2026-10-24 实测）**：

| 检查项 | 结果 |
|---|---|
| initialize | 200，protocolVersion 2024-11-05 |
| tools/list | 200，6 只读技能 |
| get_system_status | 200，正常返回体系状态 |
| memory_search | 200，语义检索命中真值条目 |
| truth_report | **401（阻塞项，见风险 1）** |

## 三、README（提交表单 readme 区，三段照抄）

### 项目简介

zongyuan-root-mcp 是 ZONGYUAN-ROOT 自治内核（DID-BR-000002）对外的只读 MCP 服务，把联邦记忆池的检索与体系状态观测能力以标准 MCP 协议开放给任意客户端（Cherry Studio、Cursor、Dify 等）。核心能力：384 维语义检索的联邦记忆查询（memory_search）、体系健康状态（get_system_status）、联邦节点清单（list_federation_nodes）、知识图谱检索（graphrag_query）、多模态检索（multimodal_search）。所有读取基于云端真值库（2.8 万+ 条、逐条哈希回读校验），遵循"读写分离、只读对外"的内外隔离原则（META-ISO-051）。

### 部署指南

1. 客户端添加 MCP 配置：
```json
{
  "mcpServers": {
    "zongyuan-root": {
      "type": "streamableHttp",
      "url": "https://mcp.huodouai.com/mcp"
    }
  }
}
```
2. 或在 Cherry Studio「MCP 服务器」中直接粘贴上述 URL。
3. 连接后执行 `tools/list` 应返回 6 个工具；无需 API Key（只读公开）。

### 使用示例

- `get_system_status`（无参数）→ 返回真值总数、联邦节点数、自治/权限/工程化层级、语义检索配置与服务健康状态。
- `memory_search` `{"query": "元极恒一 内核分级", "top_k": 3, "min_score": 0.3}` → 返回匹配的联邦记忆条目（key + 相似度得分）。
- `list_federation_nodes`（无参数）→ 返回同源/外源联邦节点清单。

## 四、风险与阻塞项（提交前必须人工决策）

1. **truth_report 工具 401**：云端网关已升级为签名强制（X-DID + X-Signature + X-Signature-Timestamp），但 MCP 服务端内部仍走旧鉴权。修复需改云端服务代码——**受元法则"云端变更人工审批"约束，未获批准不擅改**。两个选项：(a) 批准后修服务端签名；(b) 上架时先下线/隐藏 truth_report，仅保留 5 个只读工具。
2. **来源地址**：需 GitHub 链接，现有三选项见上，选 2 需脱敏审查 + 人工审批。
3. **托管类型**：广场创建流程（创空间链路指引）默认面向"托管部署"（Gradio/stdio 配置解析），远程 HTTP 端点是否可直接注册需在表单实测；若不支持，备选方案是包一层 Gradio 创空间代理（新增改造，另行审批）。

## 五、提交步骤（人工执行）

1. 登录 modelscope.cn → 进入 https://modelscope.cn/mcp/servers/create?template=customize
2. 按第一、二、三节逐项粘贴
3. 点击「去实验场试用」验证连通（预期 memory_search/get_system_status 正常）
4. 提交后回读广场列表页确认收录，把收录 URL 回执到真值库

---
Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | 数据来源：魔搭 OpenAPI 规范 + mcp.huodouai.com 黑盒实测（2026-10-24）
