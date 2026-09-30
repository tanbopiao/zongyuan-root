# SKU S1-S6 配额映射表 v1.0

> 任务：task.pending_open #7（B级 P=65.8）
> 承接节点：vefaas-sandbox-01
> 完成时间：2026-09-13
> 确权：DID-BR-000002｜Ω₀⊂⊙∞⊂Ω

## 一、六档 SKU 定义与配额

| SKU | 档位 | 价格 | 月调用上限 | 并发节点 | 节点上限 | API权限 | 限流策略 |
|-----|------|------|-----------|---------|---------|---------|---------|
| S1 | 免费版 | ¥0 | 100 calls/天（月度重置） | 1 | ≤3 | 仅公共端点 | 超限429，次日0点重置 |
| S2 | 标准版 | ¥68/月 | 5,000 calls/月 | 3 | ≤10 | 公共+标准端点 | 超限429，当月不再补 |
| S3 | 专业版 | ¥299/月 | 50,000 calls/月 | 10 | ≤50 | 全端点（除私有化） | 超限429，可购加量包 |
| S4 | 团队版 | ¥999/月 | 200,000 calls/月 | 30 | ≤200 | 全端点+SSO | 超限429，团队共享池 |
| S5 | 企业版 | 面议（¥50,000/年起） | 不限 calls（年度合同额） | 不限 | 无限 | 全端点+私有化+定制 | 不限流，合同配额 |
| S6 | 定制版 | 战略定价（¥200,000+/年） | 定制 | 定制 | 定制 | 全部+驻场+联合开发 | 按SOW定制 |

## 二、映射到 keys_store.json 的字段

每个 API Key 必须携带以下字段：

```json
{
  "key_id": "<hash>",
  "sku": "S1|S2|S3|S4|S5|S6",
  "tier": "free|standard|pro|team|enterprise|custom",
  "quota_monthly": 100,
  "quota_reset": "daily|monthly",
  "calls_used": 0,
  "calls_remaining": 100,
  "node_limit": 3,
  "nodes_used": 0,
  "endpoint_scope": "public",
  "billing_cycle": "2026-09",
  "alert_threshold_pct": 80,
  "last_alert_sent": null
}
```

## 三、限流执行点

1. 8120 认证服务第 61 行（已递增 calls）后，增加 SKU 配额检查：
   - calls_used >= quota_monthly → 返回 429 + X-Quota-Remaining: 0
   - calls_used >= quota_monthly * 0.8 → 触发告警 webhook
2. 节点注册接口按 sku 校验 node_limit
3. 端点访问按 endpoint_scope 白名单过滤

## 四、月度费用汇总规则

- 每月 1 日 00:00 自动统计上月各 SKU 实际用量
- 生成月度报表：SKU 分布、峰值用量、超限次数、告警触发记录
- 报表通过记忆网关上报 truth_type=operation_log

## 五、80% 用量告警规则

- 实时计算 calls_used / quota_monthly
- 达 80% → 推送 webhook 到节点管理员
- 达 100% → 返回 429 并阻断后续调用
- 告警当日只发一次，不重复骚扰

Ω₀⊂⊙∞⊂Ω｜vefaas-sandbox-01｜task #7 完成
