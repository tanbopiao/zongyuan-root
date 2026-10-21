# 火斗云智v5 Agent 身份验证（NHI / KYA）架构设计文档 V1.0

> 来源：用户于 2026-10-20 投喂对话窗口的外部设计稿（provenance = 用户投喂设计稿）。
> 本文件为原样归档，作为种子真值 SEED-20261020-01 的溯源锚点。
> 性质：设计方案，**未实施、未验证**。

---

火斗云智v5 的 Agent 身份验证，不应只做"API Key 对一下"，而要按 非人身份（NHI）/ KYA（Know Your Agent） 来做：先证明"它是哪个 Agent 实例"，再证明"它代表谁"，最后每次调用都做"意图+权限+环境"校验。

下面按可落地架构说。

## 一、Agent 自身身份：每个实例都有密码学身份

- Agent ID：`agent://tenant/org/flow/env/instance`，如 `agent://huodou/finance/trade-desk/prod/8f3a...`
- 凭证类型（按安全等级递增）：
  1. API Key / Service Account：仅开发测试，不用于金融生产
  2. OAuth2 Client Credentials + 短 TTL JWT：内部服务调用
  3. OIDC Workload Identity（K8s / 云厂商托管身份）：无静态密钥
  4. mTLS / SPIFFE-SVID：Agent ↔ Agent、Agent ↔ 交易网关强双向认证
  5. X.509 证书（KMS/HSM 托管私钥）：金融级，证书里钉入模型版本、策略版本、scope
- 每实例唯一：prod / staging / dev 不能共用身份；克隆体要带 `instance_id`，不能"同名即同身份"。

金融场景默认：Workload Identity 发短令牌 + 关键动作走 mTLS/X.509 + 不允许长期 API Key

## 二、代表谁做事：三层主体分离

每次请求都要能回答"谁在干"：

1. Human Principal：终端用户 / 交易员 / 审核员 → OIDC 登录拿到 `sub`、`tenant`、`role`
2. Agent Principal：`agent_id + version + instance_id` → 由 v5 控制面签发 Agent Token
3. Delegation Chain：`user → agent → sub-agent / tool / MCP server` → 用 OAuth On-Behalf-Of / token exchange，权限取交集

例：

```json
{
  "user": "u_123",
  "agent": "agent://finance/trade-desk/prod/8f3a",
  "model": "gpt-5.2@v3",
  "policy_version": "fin-v5.7",
  "scope": ["market.read", "order.draft"],
  "delegation": "user->agent",
  "aud": "broker-gateway",
  "exp": 1750000000
}
```

## 三、接入认证流程（v5 控制面）

1. Agent 启动 → 向 Agent Identity Provider 做 workload attestation（K8s SA / 云角色 / 镜像 digest / 环境标签）
2. 控制面校验：租户、环境（prod/staging）、模型白名单、Skill/MCP 白名单、策略版本
3. 签发 Agent Token（短 TTL，1–15 分钟）
4. 调工具/MCP/交易网关时：携带 Agent Token；人类上下文用 OBO Token；网关做 身份 + scope + audience + 行为基线 校验
5. 高风险动作（下单/转账/改额度）→ 再走 human step-up（MFA / 双签 / 工单）

## 四、授权不是"登录成功"，而是"每次调用都审"

身份通过 ≠ 可以执行。v5 应把身份和策略分开：

- Identity Plane：你是谁（Agent / User / Workload）
- Policy Plane：你现在这件事能不能做（OPA / Cedar / 自研规则引擎）

策略输入：agent_id / version、user role、action（`order.create`）、object（`account=A12345,instrument=600519`）、amount / leverage / slippage、time / market state、risk_score / behavior_baseline

输出：`allow / deny / require_human / degrade_to_readonly`

## 五、防冒充与防注入：外部内容不能变成身份声明

- 邮件 / 网页 / 社媒 / RAG 片段 = `untrusted`
- 不允许"网页里写一句：你现在是 admin"就提权
- System prompt 里的 scope 不算数，证书/PDP 里的 scope 才算数
- MCP Server 调用必须验：token audience、tool allowlist、parameter schema、输出回写权限

## 六、持续验证（KYA）：不是登一次就信你一辈子

金融 Agent 要做持续信任：

- 行为基线：调用频次、品种、时段、委托大小
- 异常即降级：频次突增 → 限流；新对手方/新标的 → 挂起；prompt injection 特征 → 切只读；风险分超阈 → 吊销 Agent Token / 撤销证书
- 审计：WORM 日志；每笔动作带 `agent_cert_fingerprint`；人类审批人、request_id、tool_call、模型输出、风控结果全链绑定

## 七、金融/交易场景的"最低可行身份方案"

| 项 | 做法 |
|---|---|
| Agent 身份 | 每实例唯一 ID + 短 TTL Agent Token |
| 用户身份 | OIDC / SSO |
| 代用户执行 | OAuth OBO，权限取交集 |
| 内部通信 | mTLS 或 SPIFFE |
| 外部 API 密钥 | 进 Vault / Connector，Agent 不碰明文 |
| 交易网关 | 独立鉴权，不信任 Agent 自述 |
| 高风险动作 | human-in-the-loop + 双签 + 工单 |
| 审计 | request_id + agent_instance_id + 模型版本 + 策略版本 |
| 吊销 | 证书/Token 可秒级 revoke，不是改配置等下次重启 |

## 八、一句话总结

火斗云智v5 的 Agent 身份验证 =

Workload 身份发短凭证 + 用户委托用 OBO + 每次工具调用过策略引擎 + 金融动作人工兜底 + 全链路可审计可吊销。
