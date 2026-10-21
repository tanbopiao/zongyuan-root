# MR-PUBLIC-001 公网 API 上报通道（SSH 替代）

Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | 2026-09-14 锁档

## 规则
当 SSH 不可用（密钥失效/被拒）时，本地节点通过公网 API 与云端中枢保持联通：

- 健康检查：GET https://drama.huodouai.com/api/health
- 作品库：GET https://drama.huodouai.com/api/gallery
- 生产状态：GET https://drama.huodouai.com/api/production/status
- 上报真值：POST https://drama.huodouai.com/api/gateway/report
  - Header: X-Capture-Token: ZR-CAPTURE-2026-OMEGA-d04bb54ba2a55a7d
  - Body: {"key":"<TRUTH_KEY>","truth_content":"<JSON>","node_id":"local-dev-001","DID":"DID-BR-000002","ROOT_OMEGA":"Ω-TAN-7-001"}
- 生产触发：POST https://drama.huodouai.com/api/task/run（队列空则无产出）

## 约束
- 上报 key 使用标准命名：REPORT./LOCK./PRODUCTION./OPT./KNOWLEDGE. + 日期 + 主题
- 所有上报必须携带 DID-BR-000002 与 ROOT_OMEGA
- 内容 JSON 序列化后写入 truth_content，禁止 shell 内联破坏 Ω 符号
